"""
Ma no Kuni - Tokyo District System

Tokyo is not one city but many, layered atop each other. Each district
has its own character, its own rhythm, its own relationship with the
spirit world. Shibuya's frantic crossing breeds different spirits than
Yanaka's drowsy temple lanes.

The permeation didn't hit everywhere equally. Old places -- where memory
is deep -- tore open first. Asakusa's Senso-ji became a beacon overnight.
Akihabara's electronic hum attracted spirits no one had names for yet.
And Kichijoji, where Aoi lives, sits in a strange equilibrium: Inokashira
Park's ancient trees hold the veil steady, even as it frays everywhere else.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from src.engine.game import TimeOfDay, Season, WorldClock, MoonPhase


# ---------------------------------------------------------------------------
# Spirit taxonomy -- the broad families of spirits a district might attract
# ---------------------------------------------------------------------------

class SpiritDomain(Enum):
    """The domains from which spirits arise."""
    NATURE = "nature"              # Trees, water, wind, stone
    URBAN = "urban"                # Concrete, neon, electricity, glass
    DOMESTIC = "domestic"          # Household objects, kitchens, baths
    TRANSIT = "transit"            # Trains, buses, bicycles, crosswalks
    COMMERCIAL = "commercial"      # Vending machines, shops, money
    SACRED = "sacred"              # Shrine and temple spirits, old kami
    MEMORY = "memory"              # Echoes of people, places, events
    ELECTRONIC = "electronic"      # Screens, signals, data streams
    CULINARY = "culinary"          # Food stalls, restaurant aromas, tea
    ARTISTIC = "artistic"          # Music, graffiti, theater, craft


# ---------------------------------------------------------------------------
# Atmospheric data -- how a district feels at different times
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AmbientDescription:
    """
    A snapshot of atmosphere at a particular time of day.

    These are the ambient text fragments the engine weaves into the
    exploration UI -- the gentle background hum that makes the world
    feel alive.
    """
    material_text: str     # What the normal world looks like right now
    spirit_text: str       # What the spirit layer reveals
    sounds: list[str]      # Ambient sound tags for the audio system
    spirit_density: float  # 0.0-1.0 local modifier on spirit encounters


@dataclass
class DistrictAtmosphere:
    """
    The full atmospheric profile for a district across the day cycle.
    Every district breathes differently.
    """
    mood: str                                          # One-sentence soul
    ambient_by_time: dict[TimeOfDay, AmbientDescription] = field(
        default_factory=dict
    )
    seasonal_notes: dict[Season, str] = field(default_factory=dict)
    permeation_lore: str = ""  # How has the permeation changed daily life?

    def get_ambient(self, time: TimeOfDay) -> Optional[AmbientDescription]:
        """Return the ambient description for a given time, or None."""
        return self.ambient_by_time.get(time)


# ---------------------------------------------------------------------------
# Second/third order effects of spirit permeation on daily life
# ---------------------------------------------------------------------------

class SpiritEffectCategory(Enum):
    """Categories of real-world disruption caused by spirit activity."""
    TRANSIT_DELAY = "transit_delay"
    VENDING_ANOMALY = "vending_anomaly"
    CROSSWALK_GATHERING = "crosswalk_gathering"
    ELECTRONIC_GLITCH = "electronic_glitch"
    WEATHER_DRIFT = "weather_drift"
    SCENT_MEMORY = "scent_memory"
    SOUND_BLEED = "sound_bleed"
    LIGHT_FLICKER = "light_flicker"
    TIME_SLIP = "time_slip"


@dataclass
class SpiritEffect:
    """
    A second- or third-order consequence of the spirit world bleeding
    through. These are the lived details that make the permeation feel
    real -- not grand catastrophes but small, uncanny shifts.

    Examples:
    - The Yamanote Line runs 3 minutes late because a platform spirit
      won't release the doors.
    - A Lawson vending machine dispenses cans of something that tastes
      like nostalgia and smells like your grandmother's garden.
    - Spirits gather at the Shibuya crossing during red lights, drawn
      by the collective pause of hundreds of people. The crossing
      hums with a frequency only Aoi can feel.
    """
    category: SpiritEffectCategory
    description: str
    probability: float = 0.1        # Chance of occurring per game tick
    permeability_threshold: float = 0.3  # Min permeability to trigger
    spirit_domains: list[SpiritDomain] = field(default_factory=list)
    gameplay_effect: Optional[str] = None  # Tag for gameplay system

    def can_trigger(self, permeability: float) -> bool:
        """Check if conditions allow this effect to manifest."""
        return permeability >= self.permeability_threshold


# ---------------------------------------------------------------------------
# District connections -- the routes between neighborhoods
# ---------------------------------------------------------------------------

class ConnectionType(Enum):
    """How two districts are linked."""
    TRAIN = "train"            # JR or Metro line
    WALK = "walk"              # On foot through streets
    BUS = "bus"                # City bus route
    SPIRIT_PATH = "spirit_path"  # A route visible only in the spirit layer


@dataclass(frozen=True)
class DistrictConnection:
    """
    A navigable link between two districts. Travel time can be affected
    by spirit interference -- trains stall, streets loop, buses arrive
    in the wrong decade.
    """
    target_district_id: str
    connection_type: ConnectionType
    base_travel_minutes: int
    line_name: str = ""            # e.g. "Chuo Line", "Ginza Line"
    spirit_delay_factor: float = 1.0  # Multiplier when spirits interfere
    description: str = ""
    requires_flag: Optional[str] = None  # Story flag needed to unlock

    def effective_travel_time(self, permeability: float) -> float:
        """
        Calculate actual travel time accounting for spirit interference.
        Higher permeability means more delays on transit, but spirit paths
        become *faster*.
        """
        if self.connection_type == ConnectionType.SPIRIT_PATH:
            # Spirit paths open wider as permeability rises
            return self.base_travel_minutes * max(0.2, 1.0 - permeability)
        else:
            delay = 1.0 + (permeability * (self.spirit_delay_factor - 1.0))
            return self.base_travel_minutes * delay


# ---------------------------------------------------------------------------
# The District itself
# ---------------------------------------------------------------------------

@dataclass
class District:
    """
    A district of Tokyo -- a coherent neighborhood with its own identity,
    its own spirits, and its own relationship to the permeation.

    Districts are the top-level organizational unit of the game world.
    Each one contains a tile map (Material and Spirit layers), a set of
    named Locations, and atmospheric data that the rendering and audio
    systems consume.
    """
    district_id: str                    # Machine-readable key, e.g. "shibuya"
    name: str                           # Display name, e.g. "Shibuya"
    name_kanji: str                     # Japanese, e.g. "渋谷"
    subtitle: str = ""                  # Flavor, e.g. "The Crossing of Worlds"

    # --- Spirit world parameters ---
    base_permeability: float = 0.3      # 0.0 = sealed, 1.0 = wide open
    dominant_spirits: list[SpiritDomain] = field(default_factory=list)
    spirit_effects: list[SpiritEffect] = field(default_factory=list)

    # --- Geography ---
    connections: list[DistrictConnection] = field(default_factory=list)
    location_ids: list[str] = field(default_factory=list)
    map_material_id: Optional[str] = None  # Reference to Material layer map
    map_spirit_id: Optional[str] = None    # Reference to Spirit layer map

    # --- Atmosphere ---
    atmosphere: Optional[DistrictAtmosphere] = None

    # --- State (mutable, changes during gameplay) ---
    current_permeability_modifier: float = 0.0
    discovered: bool = False
    visited: bool = False
    event_flags: dict[str, bool] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Permeability
    # ------------------------------------------------------------------

    def effective_permeability(self, clock: WorldClock) -> float:
        """
        The actual permeability at this moment, combining the district's
        base value with the global clock and any local modifiers.

        This determines:
        - Whether the Spirit layer is visible
        - Encounter rates for spirits
        - Which spirit effects can trigger
        - How much spirit resonance tiles accumulate
        """
        global_perm = clock.spirit_permeability
        local = self.base_permeability + self.current_permeability_modifier

        # Blend: the district's own character plus the global tide
        combined = (local * 0.6) + (global_perm * 0.4)
        return max(0.0, min(1.0, combined))

    def spirit_layer_visible(self, clock: WorldClock) -> bool:
        """
        The Spirit layer becomes visible when permeability crosses 0.4.
        Below that, only faint echoes appear. Above 0.7, the layers
        fully overlap and navigating requires awareness of both.
        """
        return self.effective_permeability(clock) >= 0.4

    def layers_fully_merged(self, clock: WorldClock) -> bool:
        """When permeability exceeds 0.7, both worlds become one."""
        return self.effective_permeability(clock) >= 0.7

    # ------------------------------------------------------------------
    # Spirit effects
    # ------------------------------------------------------------------

    def active_effects(self, clock: WorldClock) -> list[SpiritEffect]:
        """Return all spirit effects that could trigger right now."""
        perm = self.effective_permeability(clock)
        return [e for e in self.spirit_effects if e.can_trigger(perm)]

    # ------------------------------------------------------------------
    # Connections
    # ------------------------------------------------------------------

    def get_connections(
        self, flags: Optional[dict[str, bool]] = None
    ) -> list[DistrictConnection]:
        """
        Return available connections, filtering out any that require
        unmet story flags.
        """
        if flags is None:
            return list(self.connections)
        return [
            c for c in self.connections
            if c.requires_flag is None or flags.get(c.requires_flag, False)
        ]

    def travel_time_to(
        self,
        target_id: str,
        clock: WorldClock,
        flags: Optional[dict[str, bool]] = None,
    ) -> Optional[float]:
        """
        Calculate travel time to a connected district, accounting for
        spirit interference. Returns None if no connection exists.
        """
        perm = self.effective_permeability(clock)
        for conn in self.get_connections(flags):
            if conn.target_district_id == target_id:
                return conn.effective_travel_time(perm)
        return None


# ---------------------------------------------------------------------------
# District Registry -- the world-level container for all districts
# ---------------------------------------------------------------------------

class DistrictRegistry:
    """
    Manages the complete set of loaded districts. Provides lookup,
    adjacency queries, and bulk operations for the game engine.
    """

    def __init__(self) -> None:
        self._districts: dict[str, District] = {}

    def register(self, district: District) -> None:
        """Add a district to the registry."""
        self._districts[district.district_id] = district

    def get(self, district_id: str) -> Optional[District]:
        """Retrieve a district by ID."""
        return self._districts.get(district_id)

    def all_districts(self) -> list[District]:
        """Return all registered districts."""
        return list(self._districts.values())

    def discovered_districts(self) -> list[District]:
        """Return only districts the player has found."""
        return [d for d in self._districts.values() if d.discovered]

    def neighbors_of(
        self, district_id: str, flags: Optional[dict[str, bool]] = None
    ) -> list[tuple[District, DistrictConnection]]:
        """
        Return all districts reachable from the given one, paired with
        their connection info.
        """
        source = self.get(district_id)
        if source is None:
            return []
        results = []
        for conn in source.get_connections(flags):
            target = self.get(conn.target_district_id)
            if target is not None:
                results.append((target, conn))
        return results

    def find_path(
        self,
        from_id: str,
        to_id: str,
        clock: WorldClock,
        flags: Optional[dict[str, bool]] = None,
    ) -> Optional[list[str]]:
        """
        BFS shortest path between two districts by number of hops.
        Returns the list of district IDs forming the path, or None
        if unreachable.
        """
        if from_id == to_id:
            return [from_id]

        visited: set[str] = {from_id}
        queue: list[list[str]] = [[from_id]]

        while queue:
            path = queue.pop(0)
            current = path[-1]
            source = self.get(current)
            if source is None:
                continue
            for conn in source.get_connections(flags):
                next_id = conn.target_district_id
                if next_id in visited:
                    continue
                new_path = path + [next_id]
                if next_id == to_id:
                    return new_path
                visited.add(next_id)
                queue.append(new_path)

        return None

    def highest_permeability(self, clock: WorldClock) -> Optional[District]:
        """Return the district with the highest current permeability."""
        if not self._districts:
            return None
        return max(
            self._districts.values(),
            key=lambda d: d.effective_permeability(clock),
        )

    def districts_above_permeability(
        self, threshold: float, clock: WorldClock
    ) -> list[District]:
        """Return all districts whose permeability exceeds the threshold."""
        return [
            d for d in self._districts.values()
            if d.effective_permeability(clock) >= threshold
        ]
