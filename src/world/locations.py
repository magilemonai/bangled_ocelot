"""
Ma no Kuni - Locations (Points of Interest)

Locations are the named places within a district that the player can
visit, investigate, and return to. They are richer than raw tiles --
they carry descriptions, interaction hooks, inventories, NPCs, and
narrative state.

A Location might be Grandmother's house in Kichijoji, where the
tatami smells of decades of tea and the hallway spirit straightens
shoes that were already straight. Or it might be a back alley behind
an Akihabara maid cafe where discarded figurines have begun to
whisper.

Locations exist at specific tile coordinates but occupy conceptual
space larger than a single tile. Entering a Location's tile triggers
the Location's exploration mode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from src.engine.game import TimeOfDay, Season


# ---------------------------------------------------------------------------
# Location categories
# ---------------------------------------------------------------------------

class LocationCategory(Enum):
    """Broad classification of a point of interest."""
    HOME = "home"                    # Safe havens, residences
    SHRINE = "shrine"                # Shinto shrines, spiritual anchors
    TEMPLE = "temple"                # Buddhist temples
    SHOP = "shop"                    # Retail, from konbini to antiques
    RESTAURANT = "restaurant"        # Ramen shops, cafes, izakaya
    PARK = "park"                    # Green spaces, gardens
    STATION = "station"              # Train and bus stations
    ALLEY = "alley"                  # Back streets, hidden paths
    ROOFTOP = "rooftop"              # High places with wide views
    ARCADE = "arcade"                # Shopping arcades (shotengai)
    LANDMARK = "landmark"            # Famous structures, monuments
    SCHOOL = "school"                # Educational institutions
    BRIDGE = "bridge"                # River crossings, overpasses
    UNDERGROUND = "underground"      # Basements, subway passages
    SPIRITUAL_NEXUS = "spiritual_nexus"  # Convergence points
    HIDDEN = "hidden"                # Secret areas, spirit-only paths


# ---------------------------------------------------------------------------
# Time-sensitive descriptions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TimedDescription:
    """
    A description that changes based on time of day. Locations feel
    different at dawn than at midnight.
    """
    default: str
    by_time: dict[TimeOfDay, str] = field(default_factory=dict)
    by_season: dict[Season, str] = field(default_factory=dict)

    def get(
        self,
        time: Optional[TimeOfDay] = None,
        season: Optional[Season] = None,
    ) -> str:
        """
        Return the most specific description available.
        Priority: season + time > time > season > default.
        """
        # Check time-specific first (most dynamic)
        if time is not None and time in self.by_time:
            return self.by_time[time]
        # Then season
        if season is not None and season in self.by_season:
            return self.by_season[season]
        return self.default


# ---------------------------------------------------------------------------
# Interactions available at a location
# ---------------------------------------------------------------------------

class InteractionType(Enum):
    """Types of things a player can do at a location."""
    EXAMINE = "examine"        # Look closely at something
    TALK = "talk"              # Speak with an NPC or spirit
    REST = "rest"              # Recover, accumulate ma
    SHOP = "shop"              # Buy or sell items
    CRAFT = "craft"            # Create items or ofuda
    PRAY = "pray"              # Interact with shrine/temple
    INVESTIGATE = "investigate"  # Search for clues or hidden things
    SPIRIT_SENSE = "spirit_sense"  # Use Aoi's perception
    ENTER = "enter"            # Go inside a sub-location
    USE_ITEM = "use_item"      # Use a specific item here
    SPIRIT_COMMUNE = "spirit_commune"  # Deep interaction with a spirit
    MEMORY_DIVE = "memory_dive"  # Access a location's stored memories


@dataclass
class Interaction:
    """
    A single available action at a location.
    """
    interaction_type: InteractionType
    label: str                           # Display text, e.g. "Pray at the altar"
    description: str = ""                # Tooltip or flavor
    requires_flag: Optional[str] = None  # Story flag prerequisite
    requires_item: Optional[str] = None  # Item prerequisite
    requires_time: Optional[list[TimeOfDay]] = None  # Time restriction
    requires_permeability: Optional[float] = None  # Min permeability
    grants_flag: Optional[str] = None    # Flag set on completion
    grants_item: Optional[str] = None    # Item received
    grants_ma: float = 0.0              # Ma accumulated
    event_id: Optional[str] = None       # Scripted event triggered
    repeatable: bool = True
    completed: bool = False

    def is_available(
        self,
        flags: dict[str, bool],
        inventory: list[str],
        time: TimeOfDay,
        permeability: float,
    ) -> bool:
        """Check whether this interaction can be performed right now."""
        if not self.repeatable and self.completed:
            return False
        if self.requires_flag and not flags.get(self.requires_flag, False):
            return False
        if self.requires_item and self.requires_item not in inventory:
            return False
        if self.requires_time and time not in self.requires_time:
            return False
        if (
            self.requires_permeability is not None
            and permeability < self.requires_permeability
        ):
            return False
        return True


# ---------------------------------------------------------------------------
# NPC and Spirit presence at a location
# ---------------------------------------------------------------------------

@dataclass
class LocationPresence:
    """
    An NPC or spirit found at a specific location. Their presence
    may be conditional on time, story progress, or permeability.
    """
    entity_id: str                       # Reference to NPC/Spirit data
    name: str
    is_spirit: bool = False
    description: str = ""
    schedule: Optional[dict[TimeOfDay, bool]] = None  # When they're here
    requires_flag: Optional[str] = None
    requires_permeability: Optional[float] = None
    dialogue_tree_id: Optional[str] = None
    idle_text: str = ""                  # What they're doing when you arrive

    def is_present(
        self,
        time: TimeOfDay,
        permeability: float,
        flags: dict[str, bool],
    ) -> bool:
        """Check if this entity is at the location right now."""
        if self.requires_flag and not flags.get(self.requires_flag, False):
            return False
        if (
            self.requires_permeability is not None
            and permeability < self.requires_permeability
        ):
            return False
        if self.schedule is not None:
            return self.schedule.get(time, False)
        return True


# ---------------------------------------------------------------------------
# The Location itself
# ---------------------------------------------------------------------------

@dataclass
class Location:
    """
    A richly described point of interest within a district.

    Locations are where the game's narrative lives. They are the rooms
    in the dungeon, the stops on the journey, the places that accrue
    memory and meaning through play. A location might be visited once
    for a quest or returned to dozens of times as it evolves with the
    story.

    Grandmother's house in Kichijoji is a Location. So is the rain-
    slicked alley behind Senso-ji where Aoi first saw a spirit with
    her own eyes. So is the rooftop of the Shibuya 109 building,
    where the wind carries voices from another century.
    """
    location_id: str
    name: str
    name_jp: str = ""                          # Japanese name
    district_id: str = ""
    category: LocationCategory = LocationCategory.LANDMARK

    # --- Position ---
    tile_x: int = 0
    tile_y: int = 0

    # --- Descriptions ---
    description: Optional[TimedDescription] = None
    spirit_description: Optional[TimedDescription] = None
    first_visit_text: str = ""                 # Special text on first arrival
    return_text: str = ""                      # Text on subsequent visits

    # --- Spirit properties ---
    base_resonance: float = 0.0                # Inherent spirit energy
    is_spiritual_anchor: bool = False          # Stabilizes nearby permeability
    spiritual_affinity: list[str] = field(default_factory=list)  # Spirit types drawn here

    # --- Interactions ---
    interactions: list[Interaction] = field(default_factory=list)

    # --- Presences ---
    presences: list[LocationPresence] = field(default_factory=list)

    # --- Sub-locations ---
    sub_location_ids: list[str] = field(default_factory=list)
    parent_location_id: Optional[str] = None

    # --- State ---
    discovered: bool = False
    visited: bool = False
    visit_count: int = 0
    event_flags: dict[str, bool] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    # --- Access control ---
    requires_flag: Optional[str] = None
    requires_time: Optional[list[TimeOfDay]] = None
    requires_permeability: Optional[float] = None
    hidden: bool = False                       # Not shown on map until found

    # ------------------------------------------------------------------
    # Description access
    # ------------------------------------------------------------------

    def get_description(
        self,
        time: Optional[TimeOfDay] = None,
        season: Optional[Season] = None,
        permeability: float = 0.0,
    ) -> str:
        """
        Get the appropriate description for current conditions.
        If permeability is high enough and a spirit description exists,
        blend both descriptions.
        """
        mat_desc = ""
        if self.description:
            mat_desc = self.description.get(time, season)

        if permeability >= 0.4 and self.spirit_description:
            spi_desc = self.spirit_description.get(time, season)
            return f"{mat_desc}\n\n{spi_desc}"

        return mat_desc

    def get_arrival_text(self) -> str:
        """Return the appropriate text for arriving at this location."""
        if not self.visited and self.first_visit_text:
            return self.first_visit_text
        if self.visited and self.return_text:
            return self.return_text
        return ""

    # ------------------------------------------------------------------
    # Presence queries
    # ------------------------------------------------------------------

    def present_entities(
        self,
        time: TimeOfDay,
        permeability: float,
        flags: dict[str, bool],
    ) -> list[LocationPresence]:
        """Return all entities currently at this location."""
        return [
            p for p in self.presences
            if p.is_present(time, permeability, flags)
        ]

    def present_spirits(
        self,
        time: TimeOfDay,
        permeability: float,
        flags: dict[str, bool],
    ) -> list[LocationPresence]:
        """Return only spirit presences."""
        return [
            p for p in self.present_entities(time, permeability, flags)
            if p.is_spirit
        ]

    # ------------------------------------------------------------------
    # Interaction queries
    # ------------------------------------------------------------------

    def available_interactions(
        self,
        flags: dict[str, bool],
        inventory: list[str],
        time: TimeOfDay,
        permeability: float,
    ) -> list[Interaction]:
        """Return all interactions currently available."""
        return [
            i for i in self.interactions
            if i.is_available(flags, inventory, time, permeability)
        ]

    # ------------------------------------------------------------------
    # Access control
    # ------------------------------------------------------------------

    def is_accessible(
        self,
        flags: dict[str, bool],
        time: TimeOfDay,
        permeability: float,
    ) -> bool:
        """Check if the player can enter this location right now."""
        if self.requires_flag and not flags.get(self.requires_flag, False):
            return False
        if self.requires_time and time not in self.requires_time:
            return False
        if (
            self.requires_permeability is not None
            and permeability < self.requires_permeability
        ):
            return False
        return True

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def visit(self) -> str:
        """
        Mark this location as visited and return arrival text.
        """
        text = self.get_arrival_text()
        if not self.visited:
            self.discovered = True
            self.visited = True
        self.visit_count += 1
        return text


# ---------------------------------------------------------------------------
# Location Registry
# ---------------------------------------------------------------------------

class LocationRegistry:
    """
    Manages all locations across all districts. Provides lookup by ID,
    by district, by category, and spatial queries.
    """

    def __init__(self) -> None:
        self._locations: dict[str, Location] = {}
        self._by_district: dict[str, list[str]] = {}

    def register(self, location: Location) -> None:
        """Add a location to the registry."""
        self._locations[location.location_id] = location
        district_list = self._by_district.setdefault(
            location.district_id, []
        )
        if location.location_id not in district_list:
            district_list.append(location.location_id)

    def get(self, location_id: str) -> Optional[Location]:
        return self._locations.get(location_id)

    def all_locations(self) -> list[Location]:
        return list(self._locations.values())

    def in_district(self, district_id: str) -> list[Location]:
        """Return all locations belonging to a district."""
        ids = self._by_district.get(district_id, [])
        return [
            self._locations[lid] for lid in ids
            if lid in self._locations
        ]

    def of_category(self, category: LocationCategory) -> list[Location]:
        return [
            loc for loc in self._locations.values()
            if loc.category == category
        ]

    def discovered_in_district(self, district_id: str) -> list[Location]:
        return [
            loc for loc in self.in_district(district_id)
            if loc.discovered
        ]

    def spiritual_anchors(self) -> list[Location]:
        """Return all locations that act as spiritual anchors."""
        return [
            loc for loc in self._locations.values()
            if loc.is_spiritual_anchor
        ]

    def hidden_locations(self, district_id: Optional[str] = None) -> list[Location]:
        """Return undiscovered hidden locations, optionally filtered by district."""
        results = [
            loc for loc in self._locations.values()
            if loc.hidden and not loc.discovered
        ]
        if district_id is not None:
            results = [loc for loc in results if loc.district_id == district_id]
        return results

    def find_by_tag(self, tag: str) -> list[Location]:
        return [
            loc for loc in self._locations.values()
            if tag in loc.tags
        ]

    def nearest_to(
        self,
        x: int,
        y: int,
        district_id: str,
        max_distance: float = float("inf"),
    ) -> Optional[Location]:
        """Find the nearest location to a tile coordinate within a district."""
        best: Optional[Location] = None
        best_dist = max_distance
        for loc in self.in_district(district_id):
            dx = loc.tile_x - x
            dy = loc.tile_y - y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < best_dist:
                best = loc
                best_dist = dist
        return best
