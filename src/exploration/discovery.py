"""
Ma no Kuni - Discovery and Secrets System

Tokyo is layered with hidden things: spirit nests tucked into alley corners,
echoes of memories imprinted on park benches, shortcuts through the spirit
world that fold the city like origami. This module tracks what the player
has found and what still waits in the spaces between.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ---------------------------------------------------------------------------
# Discovery taxonomy
# ---------------------------------------------------------------------------

class DiscoveryType(Enum):
    """The kinds of secrets woven into Tokyo's fabric."""
    SPIRIT_NEST = "spirit_nest"
    """Small spirit gathering spots - a cluster of kodama in a potted plant,
    a family of tsukumogami living in a forgotten umbrella stand."""

    MEMORY_ECHO = "memory_echo"
    """Past events imprinted on locations. Stand still long enough and the
    echo replays: a couple's first meeting at this bench, a child losing
    a balloon, a grandmother feeding pigeons for forty years."""

    HIDDEN_PATH = "hidden_path"
    """Spirit shortcuts between areas. A gap in a hedge that opens into
    a shrine three districts away. A manhole that descends into a
    spirit-world subway platform."""

    URBAN_LEGEND = "urban_legend"
    """Special encounters tied to real Tokyo urban legends, reimagined
    through the permeation. The woman at the crosswalk who asks if
    she's beautiful. The taxi that drives itself."""

    MA_SPOT = "ma_spot"
    """Places of deep stillness where ma accumulates rapidly. A courtyard
    where the city noise falls away. A rooftop where time seems to pause.
    The corner seat of a late-night ramen shop."""

    LORE_FRAGMENT = "lore_fragment"
    """Pieces of world-building: old letters, spirit-touched graffiti,
    shrine records, grandmother's stories remembered by objects."""

    ITEM_CACHE = "item_cache"
    """Hidden items - crafting materials, spirit charms, consumables
    tucked away in the gaps between worlds."""

    VISTA_POINT = "vista_point"
    """Scenic overlooks that reveal both the material and spirit geography.
    Seeing the spirit-world Tokyo skyline for the first time."""


class DiscoveryRarity(Enum):
    """How well-hidden a discovery is."""
    COMMON = "common"           # Found by normal exploration
    UNCOMMON = "uncommon"       # Requires some searching
    RARE = "rare"               # Requires Spirit Vision or special timing
    LEGENDARY = "legendary"     # Requires specific conditions to align


# ---------------------------------------------------------------------------
# Visibility conditions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VisibilityCondition:
    """
    Conditions that must be met for a discovery to be visible.
    All specified fields must match; unspecified fields are ignored.
    """
    min_permeability: Optional[float] = None
    max_permeability: Optional[float] = None
    required_time_of_day: Optional[tuple[str, ...]] = None  # TimeOfDay values
    required_season: Optional[str] = None                    # Season value
    required_moon_phase: Optional[str] = None                # MoonPhase value
    requires_spirit_vision: bool = False
    requires_sneaking: bool = False
    min_ma: Optional[float] = None
    required_flag: Optional[str] = None                      # Story flag
    required_item: Optional[str] = None
    weather: Optional[str] = None                            # rain, snow, clear, etc.

    def evaluate(
        self,
        permeability: float = 0.0,
        time_of_day: str = "",
        season: str = "",
        moon_phase: str = "",
        spirit_vision: bool = False,
        sneaking: bool = False,
        current_ma: float = 0.0,
        flags: Optional[dict] = None,
        inventory: Optional[set[str]] = None,
        current_weather: str = "",
    ) -> bool:
        """Check whether all specified conditions are satisfied."""
        flags = flags or {}
        inventory = inventory or set()

        if self.min_permeability is not None and permeability < self.min_permeability:
            return False
        if self.max_permeability is not None and permeability > self.max_permeability:
            return False
        if self.required_time_of_day is not None and time_of_day not in self.required_time_of_day:
            return False
        if self.required_season is not None and season != self.required_season:
            return False
        if self.required_moon_phase is not None and moon_phase != self.required_moon_phase:
            return False
        if self.requires_spirit_vision and not spirit_vision:
            return False
        if self.requires_sneaking and not sneaking:
            return False
        if self.min_ma is not None and current_ma < self.min_ma:
            return False
        if self.required_flag is not None and not flags.get(self.required_flag, False):
            return False
        if self.required_item is not None and self.required_item not in inventory:
            return False
        if self.weather is not None and current_weather != self.weather:
            return False

        return True


# ---------------------------------------------------------------------------
# Discovery definition and record
# ---------------------------------------------------------------------------

@dataclass
class Discovery:
    """
    A discoverable secret in the world. Defined in data, placed on the map,
    waiting for the right moment and the right kind of attention.
    """
    discovery_id: str
    name: str
    discovery_type: DiscoveryType
    rarity: DiscoveryRarity
    district: str
    description: str                              # Shown on discovery
    journal_entry: str                             # Longer text for the journal
    map_id: Optional[str] = None
    tile_x: Optional[int] = None
    tile_y: Optional[int] = None
    visibility: VisibilityCondition = field(default_factory=VisibilityCondition)
    rewards: list[DiscoveryReward] = field(default_factory=list)
    related_discoveries: list[str] = field(default_factory=list)
    repeatable: bool = False                       # Can be experienced again?
    spirit_lore_id: Optional[str] = None           # Links to bestiary
    sound_cue: Optional[str] = None                # Audio to play on discovery
    vignette_id: Optional[str] = None              # Triggers a vignette scene


@dataclass
class DiscoveryReward:
    """What the player receives for making a discovery."""
    reward_type: str    # "item", "ma", "spirit_energy", "flag", "lore", "exp"
    value: str          # Item ID, amount, or flag name
    quantity: int = 1


@dataclass
class DiscoveryRecord:
    """A record of a discovery the player has made."""
    discovery_id: str
    timestamp: float = field(default_factory=time.time)
    discovery_count: int = 1     # For repeatables
    location_map: str = ""
    location_x: int = 0
    location_y: int = 0
    conditions_at_discovery: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Discovery journal
# ---------------------------------------------------------------------------

class DiscoveryJournal:
    """
    Aoi's journal of discoveries. Tracks what has been found, computes
    completion percentages, and reveals connections between discoveries.

    The journal itself is a spirit-touched object - entries sometimes
    write themselves, and illustrations move when you're not looking.
    """

    def __init__(self) -> None:
        self._records: dict[str, DiscoveryRecord] = {}
        self._all_discoveries: dict[str, Discovery] = {}
        self._district_discoveries: dict[str, list[str]] = {}

    def register_discovery(self, discovery: Discovery) -> None:
        """Register a discovery definition (from game data)."""
        self._all_discoveries[discovery.discovery_id] = discovery
        district_list = self._district_discoveries.setdefault(discovery.district, [])
        if discovery.discovery_id not in district_list:
            district_list.append(discovery.discovery_id)

    def register_discoveries(self, discoveries: list[Discovery]) -> None:
        for d in discoveries:
            self.register_discovery(d)

    def record(
        self,
        discovery_id: str,
        map_id: str = "",
        x: int = 0,
        y: int = 0,
        conditions: Optional[dict] = None,
    ) -> tuple[bool, Optional[Discovery]]:
        """
        Record that the player found a discovery. Returns (is_new, discovery).
        For repeatable discoveries, increments the count.
        """
        discovery = self._all_discoveries.get(discovery_id)
        if discovery is None:
            return False, None

        existing = self._records.get(discovery_id)
        if existing is not None:
            if discovery.repeatable:
                existing.discovery_count += 1
                return False, discovery
            return False, discovery

        self._records[discovery_id] = DiscoveryRecord(
            discovery_id=discovery_id,
            location_map=map_id,
            location_x=x,
            location_y=y,
            conditions_at_discovery=conditions or {},
        )
        return True, discovery

    def has_found(self, discovery_id: str) -> bool:
        return discovery_id in self._records

    def get_record(self, discovery_id: str) -> Optional[DiscoveryRecord]:
        return self._records.get(discovery_id)

    def get_discovery(self, discovery_id: str) -> Optional[Discovery]:
        return self._all_discoveries.get(discovery_id)

    # -- Completion tracking --

    def district_completion(self, district: str) -> float:
        """Percentage of discoveries found in a district (0.0 - 1.0)."""
        district_ids = self._district_discoveries.get(district, [])
        if not district_ids:
            return 0.0
        found = sum(1 for did in district_ids if did in self._records)
        return found / len(district_ids)

    def type_completion(self, discovery_type: DiscoveryType) -> float:
        """Percentage of discoveries found of a given type (0.0 - 1.0)."""
        matching = [
            d
            for d in self._all_discoveries.values()
            if d.discovery_type == discovery_type
        ]
        if not matching:
            return 0.0
        found = sum(1 for d in matching if d.discovery_id in self._records)
        return found / len(matching)

    def overall_completion(self) -> float:
        """Overall discovery completion percentage (0.0 - 1.0)."""
        total = len(self._all_discoveries)
        if total == 0:
            return 0.0
        return len(self._records) / total

    # -- Queries --

    def found_in_district(self, district: str) -> list[Discovery]:
        """Return all discoveries found in a district."""
        district_ids = self._district_discoveries.get(district, [])
        return [
            self._all_discoveries[did]
            for did in district_ids
            if did in self._records and did in self._all_discoveries
        ]

    def unfound_in_district(self, district: str) -> list[Discovery]:
        """Return all undiscovered entries in a district (for hint system)."""
        district_ids = self._district_discoveries.get(district, [])
        return [
            self._all_discoveries[did]
            for did in district_ids
            if did not in self._records and did in self._all_discoveries
        ]

    def by_type(self, discovery_type: DiscoveryType) -> list[Discovery]:
        """Return all found discoveries of a given type."""
        return [
            self._all_discoveries[did]
            for did, record in self._records.items()
            if did in self._all_discoveries
            and self._all_discoveries[did].discovery_type == discovery_type
        ]

    def related_to(self, discovery_id: str) -> list[Discovery]:
        """Return discoveries related to the given one (for chains/clusters)."""
        discovery = self._all_discoveries.get(discovery_id)
        if discovery is None:
            return []
        return [
            self._all_discoveries[rid]
            for rid in discovery.related_discoveries
            if rid in self._all_discoveries
        ]

    def recent(self, count: int = 10) -> list[tuple[DiscoveryRecord, Discovery]]:
        """Return the most recently found discoveries."""
        sorted_records = sorted(
            self._records.values(),
            key=lambda r: r.timestamp,
            reverse=True,
        )
        results = []
        for record in sorted_records[:count]:
            discovery = self._all_discoveries.get(record.discovery_id)
            if discovery is not None:
                results.append((record, discovery))
        return results

    # -- Stats --

    @property
    def total_found(self) -> int:
        return len(self._records)

    @property
    def total_available(self) -> int:
        return len(self._all_discoveries)

    def stats_by_type(self) -> dict[DiscoveryType, tuple[int, int]]:
        """Return (found, total) counts for each discovery type."""
        result: dict[DiscoveryType, tuple[int, int]] = {}
        for dtype in DiscoveryType:
            matching = [
                d
                for d in self._all_discoveries.values()
                if d.discovery_type == dtype
            ]
            found = sum(1 for d in matching if d.discovery_id in self._records)
            result[dtype] = (found, len(matching))
        return result

    def stats_by_district(self) -> dict[str, tuple[int, int]]:
        """Return (found, total) counts for each district."""
        result: dict[str, tuple[int, int]] = {}
        for district, ids in self._district_discoveries.items():
            found = sum(1 for did in ids if did in self._records)
            result[district] = (found, len(ids))
        return result


# ---------------------------------------------------------------------------
# Discovery scanner - checks the world for visible discoveries
# ---------------------------------------------------------------------------

class DiscoveryScanner:
    """
    Scans the player's surroundings for discoverable secrets, applying
    visibility conditions against the current world state. Used by the
    exploration loop to check if the player has stepped near something
    they can perceive right now.
    """

    def __init__(self, journal: DiscoveryJournal) -> None:
        self.journal = journal

    def scan_tile(
        self,
        discovery_id: str,
        *,
        permeability: float = 0.0,
        time_of_day: str = "",
        season: str = "",
        moon_phase: str = "",
        spirit_vision: bool = False,
        sneaking: bool = False,
        current_ma: float = 0.0,
        flags: Optional[dict] = None,
        inventory: Optional[set[str]] = None,
        weather: str = "",
    ) -> Optional[Discovery]:
        """
        Check if a discovery on the current tile is visible under
        current conditions. Returns the Discovery if visible and not
        yet found (or repeatable), None otherwise.
        """
        discovery = self.journal.get_discovery(discovery_id)
        if discovery is None:
            return None

        # Already found and not repeatable
        if self.journal.has_found(discovery_id) and not discovery.repeatable:
            return None

        if not discovery.visibility.evaluate(
            permeability=permeability,
            time_of_day=time_of_day,
            season=season,
            moon_phase=moon_phase,
            spirit_vision=spirit_vision,
            sneaking=sneaking,
            current_ma=current_ma,
            flags=flags,
            inventory=inventory,
            current_weather=weather,
        ):
            return None

        return discovery

    def scan_area(
        self,
        discovery_ids: list[str],
        **conditions: object,
    ) -> list[Discovery]:
        """Scan multiple tiles and return all visible discoveries."""
        visible: list[Discovery] = []
        for did in discovery_ids:
            result = self.scan_tile(did, **conditions)  # type: ignore[arg-type]
            if result is not None:
                visible.append(result)
        return visible
