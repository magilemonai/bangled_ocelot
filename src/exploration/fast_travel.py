"""
Ma no Kuni - Fast Travel System

Tokyo's train network is the circulatory system of the city - and now
the spirit world pulses through it too. The Yamanote Line carries more
than commuters: spirits ride between stops, announcements name stations
that don't exist on any map, and sometimes a train arrives that hasn't
run since 1964.

Travel is never instant. Every ride is a liminal space where the material
and spirit worlds overlap, compressed into the rattling intimacy of a
train car. Things happen between stations.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ---------------------------------------------------------------------------
# Train line classification
# ---------------------------------------------------------------------------

class TrainLineType(Enum):
    """The kinds of rail that cross Tokyo, material and otherwise."""
    JR = "jr"                       # JR East lines (Yamanote, Chuo, etc.)
    METRO = "metro"                 # Tokyo Metro (Ginza, Marunouchi, etc.)
    TOEI = "toei"                   # Toei Subway
    PRIVATE = "private"             # Private railways (Keio, Odakyu, etc.)
    SPIRIT_LINE = "spirit_line"     # Spirit-world train lines


class StationType(Enum):
    """What kind of station is this?"""
    MAJOR_HUB = "major_hub"         # Shinjuku, Shibuya, Tokyo, Ikebukuro
    TRANSFER = "transfer"           # Multi-line transfer stations
    LOCAL = "local"                 # Single-line stops
    SPIRIT_STATION = "spirit_station"  # Exists only in the spirit world
    HIDDEN = "hidden"               # Abandoned or concealed stations


class TravelStatus(Enum):
    """Current state of a travel attempt."""
    WAITING = auto()            # At the platform
    BOARDING = auto()           # Getting on
    IN_TRANSIT = auto()         # Between stations
    ARRIVING = auto()           # Pulling into a station
    DELAYED = auto()            # Spirit interference
    REROUTED = auto()           # Sent to a different destination
    COMPLETED = auto()          # Arrived
    CANCELLED = auto()          # Travel aborted


# ---------------------------------------------------------------------------
# Station and line data
# ---------------------------------------------------------------------------

@dataclass
class Station:
    """
    A train station - the nodes of Tokyo's web. Major stations are
    worlds unto themselves, with spirit ecosystems in their lower levels
    and forgotten platforms where ghost trains still stop.
    """
    station_id: str
    name: str
    name_jp: str                              # Japanese name
    spirit_name: Optional[str] = None         # Spirit-world name (if different)
    district: str = ""
    station_type: StationType = StationType.LOCAL
    map_id: Optional[str] = None              # Map to load when arriving
    entry_x: int = 0
    entry_y: int = 0
    lines: list[str] = field(default_factory=list)   # Line IDs this station serves
    connections: list[str] = field(default_factory=list)  # Adjacent station IDs
    unlocked: bool = True
    spirit_station: bool = False              # Only accessible via spirit means
    discovery_id: Optional[str] = None        # Associated discovery
    ambient_permeability: float = 0.0         # Some stations are thin spots
    description: str = ""
    platform_events: list[str] = field(default_factory=list)  # Event IDs


@dataclass
class TrainLine:
    """
    A train line connecting stations. Spirit lines overlay material
    ones - sometimes they share tracks, sometimes they diverge into
    impossible geometries.
    """
    line_id: str
    name: str
    name_jp: str
    line_type: TrainLineType
    color: str = "#000000"                    # Line color for UI
    stations: list[str] = field(default_factory=list)   # Ordered station IDs
    is_loop: bool = False                     # Circular line (like Yamanote)
    spirit_overlay: bool = False              # Has a spirit-world variant
    spirit_stations: list[str] = field(default_factory=list)  # Extra spirit stops
    base_travel_time: float = 2.0             # Minutes per station (game time)
    reliability: float = 1.0                  # 1.0 = always on time
    description: str = ""

    def get_route(self, from_station: str, to_station: str) -> Optional[list[str]]:
        """
        Get the ordered list of stations between origin and destination.
        For loop lines, chooses the shorter direction.
        """
        if from_station not in self.stations or to_station not in self.stations:
            return None

        from_idx = self.stations.index(from_station)
        to_idx = self.stations.index(to_station)

        if self.is_loop:
            # Try both directions, pick shorter
            forward = self._slice_loop(from_idx, to_idx)
            backward = self._slice_loop(to_idx, from_idx)
            backward.reverse()
            return forward if len(forward) <= len(backward) else backward
        else:
            if from_idx <= to_idx:
                return self.stations[from_idx : to_idx + 1]
            else:
                route = self.stations[to_idx : from_idx + 1]
                route.reverse()
                return route

    def _slice_loop(self, from_idx: int, to_idx: int) -> list[str]:
        """Slice a loop line in the forward direction."""
        if from_idx <= to_idx:
            return self.stations[from_idx : to_idx + 1]
        return self.stations[from_idx:] + self.stations[: to_idx + 1]

    def station_count_between(self, from_station: str, to_station: str) -> int:
        """Number of stops between two stations (exclusive of origin)."""
        route = self.get_route(from_station, to_station)
        return len(route) - 1 if route else 0


# ---------------------------------------------------------------------------
# Travel events (things that happen on the train)
# ---------------------------------------------------------------------------

@dataclass
class TrainEvent:
    """
    Something that happens during a train ride. The liminal space of
    transit is fertile ground for the uncanny.
    """
    event_id: str
    name: str
    text: str
    text_variants: list[str] = field(default_factory=list)
    spirit_vision_text: Optional[str] = None

    # Conditions
    line_types: Optional[list[TrainLineType]] = None  # Which line types
    min_permeability: float = 0.0
    time_of_day: Optional[list[str]] = None
    required_flags: list[str] = field(default_factory=list)
    chance: float = 0.3

    # Effects
    delay_stops: int = 0               # Extra stops added to journey
    reroute_station: Optional[str] = None  # Divert to this station
    ma_change: float = 0.0
    spirit_energy_change: float = 0.0
    items: list[tuple[str, int]] = field(default_factory=list)
    trigger_encounter: Optional[str] = None
    trigger_dialogue: Optional[str] = None

    def get_text(self, spirit_vision: bool = False) -> str:
        if spirit_vision and self.spirit_vision_text:
            return self.spirit_vision_text
        if self.text_variants:
            return random.choice([self.text] + self.text_variants)
        return self.text


# ---------------------------------------------------------------------------
# Torii gate network (spirit shortcuts)
# ---------------------------------------------------------------------------

@dataclass
class ToriiGate:
    """
    A torii gate that serves as a spirit-world fast-travel node.
    These ancient gates connect sacred spaces across Tokyo, forming
    a network that predates the train system by centuries. Walking
    through one is walking through folded space.

    Gates must be discovered and activated before they can be used.
    Some require offerings.
    """
    gate_id: str
    name: str
    name_jp: str
    district: str
    map_id: str
    tile_x: int
    tile_y: int
    connected_gates: list[str] = field(default_factory=list)
    unlocked: bool = False
    activated: bool = False
    required_offering: Optional[str] = None   # Item ID needed to activate
    min_permeability: float = 0.3             # Minimum to use
    min_ma: float = 20.0                      # Minimum ma to travel
    ma_cost: float = 10.0                     # Ma spent per use
    spirit_energy_cost: float = 15.0
    description: str = ""
    travel_text: str = ""                     # Flavor text during travel


# ---------------------------------------------------------------------------
# Route planning
# ---------------------------------------------------------------------------

@dataclass
class PlannedRoute:
    """A planned journey through Tokyo's train network."""
    segments: list[RouteSegment] = field(default_factory=list)
    total_stops: int = 0
    total_transfers: int = 0
    estimated_time: float = 0.0    # Game minutes
    requires_spirit_access: bool = False

    @property
    def origin(self) -> Optional[str]:
        return self.segments[0].from_station if self.segments else None

    @property
    def destination(self) -> Optional[str]:
        return self.segments[-1].to_station if self.segments else None


@dataclass
class RouteSegment:
    """One leg of a multi-line journey."""
    line_id: str
    from_station: str
    to_station: str
    stops: list[str] = field(default_factory=list)
    travel_time: float = 0.0


# ---------------------------------------------------------------------------
# Travel session (active journey)
# ---------------------------------------------------------------------------

@dataclass
class TravelSession:
    """
    An active train journey. Not a loading screen - a scene.
    The player watches stations pass, encounters occur between stops,
    and the spirit world occasionally bleeds through the windows.
    """
    route: PlannedRoute
    status: TravelStatus = TravelStatus.WAITING
    current_segment_idx: int = 0
    current_stop_idx: int = 0
    elapsed_time: float = 0.0
    events_triggered: list[TrainEvent] = field(default_factory=list)
    delay_accumulated: float = 0.0
    rerouted: bool = False
    reroute_destination: Optional[str] = None

    @property
    def current_segment(self) -> Optional[RouteSegment]:
        if 0 <= self.current_segment_idx < len(self.route.segments):
            return self.route.segments[self.current_segment_idx]
        return None

    @property
    def current_station_id(self) -> Optional[str]:
        seg = self.current_segment
        if seg is None:
            return None
        if 0 <= self.current_stop_idx < len(seg.stops):
            return seg.stops[self.current_stop_idx]
        return None

    @property
    def progress(self) -> float:
        """Overall journey progress from 0.0 to 1.0."""
        if self.route.total_stops == 0:
            return 0.0
        completed = sum(
            len(seg.stops) - 1
            for seg in self.route.segments[: self.current_segment_idx]
        )
        completed += self.current_stop_idx
        return completed / self.route.total_stops

    @property
    def is_complete(self) -> bool:
        return self.status in (TravelStatus.COMPLETED, TravelStatus.CANCELLED)


# ---------------------------------------------------------------------------
# Fast travel controller
# ---------------------------------------------------------------------------

class FastTravelController:
    """
    Manages Tokyo's interconnected transit systems: the material train
    network, the spirit train lines, and the torii gate shortcuts.

    Travel is never just a menu selection. It's an experience - the
    compression of urban space into the rocking intimacy of a train
    carriage, where spirits press close and the city streams past
    like a film reel of overlapping realities.
    """

    def __init__(self, rng_seed: Optional[int] = None) -> None:
        self._stations: dict[str, Station] = {}
        self._lines: dict[str, TrainLine] = {}
        self._torii_gates: dict[str, ToriiGate] = {}
        self._train_events: list[TrainEvent] = []
        self._rng = random.Random(rng_seed)

    # -- Registration --

    def register_station(self, station: Station) -> None:
        self._stations[station.station_id] = station

    def register_line(self, line: TrainLine) -> None:
        self._lines[line.line_id] = line

    def register_torii_gate(self, gate: ToriiGate) -> None:
        self._torii_gates[gate.gate_id] = gate

    def register_train_event(self, event: TrainEvent) -> None:
        self._train_events.append(event)

    # -- Station queries --

    def get_station(self, station_id: str) -> Optional[Station]:
        return self._stations.get(station_id)

    def get_stations_in_district(self, district: str) -> list[Station]:
        return [s for s in self._stations.values() if s.district == district]

    def get_unlocked_stations(self) -> list[Station]:
        return [s for s in self._stations.values() if s.unlocked]

    def get_lines_at_station(self, station_id: str) -> list[TrainLine]:
        return [
            line
            for line in self._lines.values()
            if station_id in line.stations
        ]

    def unlock_station(self, station_id: str) -> bool:
        station = self._stations.get(station_id)
        if station is None:
            return False
        station.unlocked = True
        return True

    # -- Torii gate operations --

    def get_torii_gate(self, gate_id: str) -> Optional[ToriiGate]:
        return self._torii_gates.get(gate_id)

    def get_unlocked_gates(self) -> list[ToriiGate]:
        return [g for g in self._torii_gates.values() if g.unlocked and g.activated]

    def activate_gate(
        self,
        gate_id: str,
        offering_item: Optional[str] = None,
    ) -> tuple[bool, str]:
        """
        Activate a torii gate. Returns (success, message).
        """
        gate = self._torii_gates.get(gate_id)
        if gate is None:
            return False, "No gate found."

        if gate.activated:
            return False, "This gate is already active."

        if not gate.unlocked:
            return False, "This gate has not been discovered yet."

        if gate.required_offering:
            if offering_item != gate.required_offering:
                return False, (
                    f"This gate requires an offering of {gate.required_offering}."
                )

        gate.activated = True
        return True, gate.description or "The torii gate hums with ancient power."

    def can_use_gate(
        self,
        gate_id: str,
        current_ma: float,
        current_spirit_energy: float,
        permeability: float,
    ) -> tuple[bool, str]:
        """Check if the player can travel through a torii gate right now."""
        gate = self._torii_gates.get(gate_id)
        if gate is None:
            return False, "Gate not found."
        if not gate.activated:
            return False, "This gate is not active."
        if current_ma < gate.min_ma:
            return False, "You haven't gathered enough stillness to pass through."
        if current_spirit_energy < gate.spirit_energy_cost:
            return False, "Not enough spirit energy to traverse the gate."
        if permeability < gate.min_permeability:
            return False, "The veil is too thick here right now."
        return True, ""

    def get_gate_destinations(self, gate_id: str) -> list[ToriiGate]:
        """Get all reachable gates from a given gate."""
        gate = self._torii_gates.get(gate_id)
        if gate is None:
            return []
        return [
            self._torii_gates[gid]
            for gid in gate.connected_gates
            if gid in self._torii_gates
            and self._torii_gates[gid].activated
        ]

    # -- Route planning --

    def plan_route(
        self,
        from_station: str,
        to_station: str,
        allow_spirit_lines: bool = False,
    ) -> Optional[PlannedRoute]:
        """
        Plan a route between two stations using BFS across lines.
        Returns the route with fewest transfers.
        """
        if from_station not in self._stations or to_station not in self._stations:
            return None

        if from_station == to_station:
            return PlannedRoute()

        # BFS over (station, line) pairs to find shortest transfer path
        from collections import deque

        # State: (current_station, current_line_or_none, path_of_segments)
        queue: deque[tuple[str, Optional[str], list[RouteSegment]]] = deque()
        visited: set[tuple[str, Optional[str]]] = set()

        # Seed with all lines from the origin station
        for line in self.get_lines_at_station(from_station):
            if line.line_type == TrainLineType.SPIRIT_LINE and not allow_spirit_lines:
                continue
            queue.append((from_station, line.line_id, []))
            visited.add((from_station, line.line_id))

        while queue:
            current_station, current_line_id, path = queue.popleft()

            if current_line_id is None:
                continue

            line = self._lines[current_line_id]
            route_on_line = line.get_route(current_station, to_station)

            # Direct route on this line
            if route_on_line is not None and to_station in route_on_line:
                segment = RouteSegment(
                    line_id=current_line_id,
                    from_station=current_station,
                    to_station=to_station,
                    stops=route_on_line,
                    travel_time=line.base_travel_time * (len(route_on_line) - 1),
                )
                complete_path = path + [segment]
                return self._build_planned_route(complete_path, allow_spirit_lines)

            # Explore transfers at reachable stations on this line
            for station_id in line.stations:
                if station_id == current_station:
                    continue

                # Build segment to this transfer point
                transfer_route = line.get_route(current_station, station_id)
                if transfer_route is None:
                    continue

                segment = RouteSegment(
                    line_id=current_line_id,
                    from_station=current_station,
                    to_station=station_id,
                    stops=transfer_route,
                    travel_time=line.base_travel_time * (len(transfer_route) - 1),
                )

                # Try transferring to other lines at this station
                for other_line in self.get_lines_at_station(station_id):
                    if other_line.line_id == current_line_id:
                        continue
                    if other_line.line_type == TrainLineType.SPIRIT_LINE and not allow_spirit_lines:
                        continue
                    state_key = (station_id, other_line.line_id)
                    if state_key not in visited:
                        visited.add(state_key)
                        queue.append(
                            (station_id, other_line.line_id, path + [segment])
                        )

        return None  # No route found

    def _build_planned_route(
        self,
        segments: list[RouteSegment],
        has_spirit_access: bool,
    ) -> PlannedRoute:
        total_stops = sum(len(seg.stops) - 1 for seg in segments)
        total_time = sum(seg.travel_time for seg in segments)
        requires_spirit = any(
            self._lines[seg.line_id].line_type == TrainLineType.SPIRIT_LINE
            for seg in segments
        )
        return PlannedRoute(
            segments=segments,
            total_stops=total_stops,
            total_transfers=max(0, len(segments) - 1),
            estimated_time=total_time,
            requires_spirit_access=requires_spirit,
        )

    # -- Active travel --

    def begin_travel(self, route: PlannedRoute) -> TravelSession:
        """Start a journey along a planned route."""
        return TravelSession(route=route, status=TravelStatus.BOARDING)

    def advance_travel(
        self,
        session: TravelSession,
        delta: float,
        permeability: float = 0.0,
        time_of_day: str = "",
        flags: Optional[dict] = None,
    ) -> list[TrainEvent]:
        """
        Advance the travel session by delta game-minutes.
        Returns any events triggered during this segment.
        """
        if session.is_complete:
            return []

        flags = flags or {}
        session.elapsed_time += delta
        triggered_events: list[TrainEvent] = []

        segment = session.current_segment
        if segment is None:
            session.status = TravelStatus.COMPLETED
            return []

        line = self._lines.get(segment.line_id)
        if line is None:
            session.status = TravelStatus.COMPLETED
            return []

        # Check for travel events each segment
        time_per_stop = line.base_travel_time
        stops_to_advance = int(delta / time_per_stop) if time_per_stop > 0 else 1

        for _ in range(max(1, stops_to_advance)):
            # Roll for events between stops
            event = self._roll_train_event(
                line=line,
                permeability=permeability,
                time_of_day=time_of_day,
                flags=flags,
            )
            if event is not None:
                triggered_events.append(event)
                session.events_triggered.append(event)

                # Handle delays
                if event.delay_stops > 0:
                    session.delay_accumulated += event.delay_stops * time_per_stop
                    session.status = TravelStatus.DELAYED

                # Handle reroutes
                if event.reroute_station:
                    session.rerouted = True
                    session.reroute_destination = event.reroute_station
                    session.status = TravelStatus.REROUTED

            # Advance to next stop
            session.current_stop_idx += 1
            session.status = TravelStatus.IN_TRANSIT

            # Check if segment is complete
            if session.current_stop_idx >= len(segment.stops):
                session.current_segment_idx += 1
                session.current_stop_idx = 0

                if session.current_segment_idx >= len(session.route.segments):
                    session.status = TravelStatus.COMPLETED
                    return triggered_events
                else:
                    session.status = TravelStatus.ARRIVING

        return triggered_events

    def _roll_train_event(
        self,
        line: TrainLine,
        permeability: float,
        time_of_day: str,
        flags: dict,
    ) -> Optional[TrainEvent]:
        """Roll for a random event between train stops."""
        eligible = []
        for event in self._train_events:
            # Line type filter
            if event.line_types and line.line_type not in event.line_types:
                continue
            # Permeability filter
            if permeability < event.min_permeability:
                continue
            # Time filter
            if event.time_of_day and time_of_day not in event.time_of_day:
                continue
            # Flag filter
            if event.required_flags:
                if not all(flags.get(f, False) for f in event.required_flags):
                    continue
            eligible.append(event)

        if not eligible:
            return None

        # Weight by chance, then pick
        roll = self._rng.random()
        cumulative = 0.0
        self._rng.shuffle(eligible)
        for event in eligible:
            cumulative += event.chance
            if roll <= cumulative:
                return event

        return None

    # -- Convenience --

    def get_nearest_station(self, district: str) -> Optional[Station]:
        """Get the primary station for a district."""
        stations = self.get_stations_in_district(district)
        if not stations:
            return None
        # Prefer major hubs, then transfer stations
        stations.sort(key=lambda s: s.station_type.value)
        return stations[0]

    def get_all_reachable(
        self,
        from_station: str,
        allow_spirit_lines: bool = False,
    ) -> set[str]:
        """Return all station IDs reachable from a given station."""
        reachable: set[str] = set()
        stack = [from_station]

        while stack:
            current = stack.pop()
            if current in reachable:
                continue
            reachable.add(current)

            for line in self.get_lines_at_station(current):
                if line.line_type == TrainLineType.SPIRIT_LINE and not allow_spirit_lines:
                    continue
                for sid in line.stations:
                    if sid not in reachable:
                        stack.append(sid)

        return reachable
