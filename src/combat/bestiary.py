"""
Ma no Kuni - Bestiary Tracking System

The bestiary is not a catalog of monsters. It is a journal of encounters,
a record of relationships, a growing understanding of the beings that
share Tokyo with us - but whom most people can no longer see.

Every spirit encountered gets an entry. But entries do not appear
fully formed. They emerge gradually, like a photograph developing:
first a silhouette, then a basic shape, then details, then behavior,
then the deep lore - the spirit's true story.

This mirrors Aoi's journey: from someone who can barely see the spirits
to someone who truly understands them. The bestiary is a measure of
empathy as much as knowledge.

Categories:
    Tsukumogami  - Object spirits, born from tools and things used with love
    Nature       - Spirits of trees, rivers, mountains, weather
    Place        - Spirits of specific locations, tied to the land
    Emotion      - Spirits born from human feelings, collective or individual
    Corrupted    - Spirits twisted by pollution, despair, or exploitation
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

import yaml

from .abilities import Element


class SpiritCategory(Enum):
    """The fundamental categories of spirit beings."""
    TSUKUMOGAMI = "tsukumogami"   # Object spirits
    NATURE = "nature"             # Nature spirits
    PLACE = "place"               # Place spirits
    EMOTION = "emotion"           # Emotion/concept spirits
    CORRUPTED = "corrupted"       # Corrupted spirits


class RevealLevel(Enum):
    """
    How much of a bestiary entry has been revealed.
    Knowledge grows through encounter, observation, and relationship.
    """
    UNKNOWN = 0       # Not yet encountered
    SILHOUETTE = 1    # Seen but not understood - just a shape in the dark
    BASIC = 2         # Basic form visible - name and element known
    DETAILED = 3      # Full appearance, stats, basic weaknesses
    BEHAVIORAL = 4    # Behavior patterns, personality, negotiation hints
    COMPLETE = 5      # Full lore, deep history, true name


# Knowledge thresholds for each reveal level
REVEAL_THRESHOLDS: dict[RevealLevel, float] = {
    RevealLevel.UNKNOWN: 0.0,
    RevealLevel.SILHOUETTE: 0.05,
    RevealLevel.BASIC: 0.15,
    RevealLevel.DETAILED: 0.35,
    RevealLevel.BEHAVIORAL: 0.60,
    RevealLevel.COMPLETE: 0.90,
}


@dataclass
class SpiritLoreFragment:
    """
    A piece of a spirit's story, unlocked at a specific knowledge level.
    """
    text: str
    reveal_level: RevealLevel
    source: str = ""  # How this lore was discovered


@dataclass
class SpiritStats:
    """Combat statistics for a spirit, as recorded in the bestiary."""
    base_hp: int = 50
    base_sp: int = 30
    attack: int = 8
    defense: int = 8
    spirit_power: int = 10
    spirit_defense: int = 10
    speed: int = 10
    evasion: float = 0.05


@dataclass
class BestiaryEntry:
    """
    A single entry in the bestiary.

    Each entry is a living document that grows as Aoi's understanding
    deepens. It tracks not just what a spirit IS, but how Aoi has
    related to it - how many times they've met, fought, talked,
    and what choices were made.
    """
    id: str
    name: str
    name_jp: str
    category: SpiritCategory
    element: Element
    secondary_element: Optional[Element] = None
    level: int = 1
    stats: SpiritStats = field(default_factory=SpiritStats)

    # Reveal state
    knowledge: float = 0.0        # 0.0 to 1.0
    reveal_level: RevealLevel = RevealLevel.UNKNOWN

    # Descriptions at each reveal level
    silhouette_desc: str = ""     # What you see at first glimpse
    basic_desc: str = ""          # Basic form description
    detailed_desc: str = ""       # Full physical description
    behavioral_desc: str = ""     # How it acts and why
    complete_desc: str = ""       # The full story

    # Encounter tracking
    times_encountered: int = 0
    times_defeated: int = 0
    times_befriended: int = 0
    times_fled_from: int = 0
    times_negotiated: int = 0
    times_purified: int = 0

    # Combat knowledge
    known_weaknesses: list[Element] = field(default_factory=list)
    known_resistances: list[Element] = field(default_factory=list)
    known_abilities: list[str] = field(default_factory=list)
    actual_weaknesses: list[Element] = field(default_factory=list)
    actual_resistances: list[Element] = field(default_factory=list)
    actual_abilities: list[str] = field(default_factory=list)

    # Personality and negotiation
    personality_traits: list[str] = field(default_factory=list)
    desires: list[str] = field(default_factory=list)
    fears: list[str] = field(default_factory=list)
    negotiation_hints: list[str] = field(default_factory=list)
    preferred_negotiation: str = ""  # Best approach type
    known_personality: list[str] = field(default_factory=list)
    known_desires: list[str] = field(default_factory=list)
    known_fears: list[str] = field(default_factory=list)

    # Lore
    lore_fragments: list[SpiritLoreFragment] = field(default_factory=list)
    unlocked_lore: list[str] = field(default_factory=list)

    # Location and conditions
    habitats: list[str] = field(default_factory=list)
    active_times: list[str] = field(default_factory=list)
    appearance_conditions: str = ""

    # Relationship
    bond_level: float = 0.0       # -1.0 (hostile) to 1.0 (bonded)
    is_befriended: bool = False
    is_in_party: bool = False

    # Corruption
    can_be_corrupted: bool = True
    base_corruption: float = 0.0  # Some spirits start partially corrupted

    # Drops and rewards
    loot_table: dict[str, float] = field(default_factory=dict)
    spirit_essence_value: int = 10
    grants_ability: Optional[str] = None

    # Sprite / visual
    sprite_key: str = ""
    silhouette_sprite: str = ""

    def record_encounter(self, result: str = "observed") -> list[str]:
        """
        Record an encounter with this spirit.
        Returns list of newly revealed information.
        """
        self.times_encountered += 1
        revelations = []

        # Each encounter grants some knowledge
        knowledge_gains = {
            "observed": 0.05,
            "defeated": 0.1,
            "befriended": 0.3,
            "fled": 0.02,
            "negotiated": 0.15,
            "purified": 0.25,
        }

        gain = knowledge_gains.get(result, 0.05)
        old_level = self.reveal_level

        self.knowledge = min(1.0, self.knowledge + gain)

        # Update counter
        counter_map = {
            "defeated": "times_defeated",
            "befriended": "times_befriended",
            "fled": "times_fled_from",
            "negotiated": "times_negotiated",
            "purified": "times_purified",
        }
        counter = counter_map.get(result)
        if counter:
            setattr(self, counter, getattr(self, counter) + 1)

        if result == "befriended":
            self.is_befriended = True
            self.bond_level = max(self.bond_level, 0.5)

        # Check for level up in reveal
        new_level = self._calculate_reveal_level()
        if new_level != old_level:
            self.reveal_level = new_level
            revelations.extend(self._reveal_for_level(new_level))

        return revelations

    def _calculate_reveal_level(self) -> RevealLevel:
        """Determine current reveal level based on knowledge."""
        current = RevealLevel.UNKNOWN
        for level, threshold in sorted(
            REVEAL_THRESHOLDS.items(), key=lambda x: x[1]
        ):
            if self.knowledge >= threshold:
                current = level
        return current

    def _reveal_for_level(self, level: RevealLevel) -> list[str]:
        """Reveal information appropriate for this knowledge level."""
        revealed = []

        if level.value >= RevealLevel.BASIC.value:
            # Reveal element
            revealed.append(f"Element: {self.element.value}")

        if level.value >= RevealLevel.DETAILED.value:
            # Reveal weaknesses and resistances
            if self.actual_weaknesses:
                weakness = self.actual_weaknesses[0]
                if weakness not in self.known_weaknesses:
                    self.known_weaknesses.append(weakness)
                    revealed.append(f"Weakness discovered: {weakness.value}")
            if self.actual_resistances:
                resistance = self.actual_resistances[0]
                if resistance not in self.known_resistances:
                    self.known_resistances.append(resistance)
                    revealed.append(f"Resistance discovered: {resistance.value}")

        if level.value >= RevealLevel.BEHAVIORAL.value:
            # Reveal personality and negotiation hints
            for trait in self.personality_traits:
                if trait not in self.known_personality:
                    self.known_personality.append(trait)
                    revealed.append(f"Personality trait: {trait}")
            for desire in self.desires[:2]:
                if desire not in self.known_desires:
                    self.known_desires.append(desire)
                    revealed.append(f"Desire: {desire}")
            if self.negotiation_hints:
                revealed.append(f"Negotiation hint: {self.negotiation_hints[0]}")

        if level.value >= RevealLevel.COMPLETE.value:
            # Full reveal
            self.known_weaknesses = list(self.actual_weaknesses)
            self.known_resistances = list(self.actual_resistances)
            self.known_abilities = list(self.actual_abilities)
            self.known_personality = list(self.personality_traits)
            self.known_desires = list(self.desires)
            self.known_fears = list(self.fears)
            revealed.append("Full lore unlocked!")

        # Check lore fragments
        for fragment in self.lore_fragments:
            if (fragment.reveal_level.value <= level.value
                    and fragment.text not in self.unlocked_lore):
                self.unlocked_lore.append(fragment.text)
                revealed.append(f"Lore: {fragment.text[:50]}...")

        return revealed

    def get_display_description(self) -> str:
        """Get the appropriate description for the current reveal level."""
        descriptions = {
            RevealLevel.UNKNOWN: "???",
            RevealLevel.SILHOUETTE: self.silhouette_desc or "A vague shape in the spiritual haze...",
            RevealLevel.BASIC: self.basic_desc or self.silhouette_desc,
            RevealLevel.DETAILED: self.detailed_desc or self.basic_desc,
            RevealLevel.BEHAVIORAL: self.behavioral_desc or self.detailed_desc,
            RevealLevel.COMPLETE: self.complete_desc or self.behavioral_desc,
        }
        return descriptions.get(self.reveal_level, "???")

    def get_display_name(self) -> str:
        """Get the appropriate name for the current reveal level."""
        if self.reveal_level == RevealLevel.UNKNOWN:
            return "???"
        elif self.reveal_level == RevealLevel.SILHOUETTE:
            return f"??? ({self.category.value})"
        else:
            return f"{self.name} ({self.name_jp})"

    def add_knowledge(self, amount: float, source: str = "") -> list[str]:
        """
        Add knowledge from any source (observation, items, NPC dialogue).
        Returns list of revelations.
        """
        old_level = self.reveal_level
        self.knowledge = min(1.0, self.knowledge + amount)
        new_level = self._calculate_reveal_level()

        revelations = []
        if new_level != old_level:
            self.reveal_level = new_level
            revelations = self._reveal_for_level(new_level)

        return revelations


# ---------------------------------------------------------------------------
# Bestiary - the full collection
# ---------------------------------------------------------------------------

class Bestiary:
    """
    The complete bestiary - Aoi's growing encyclopedia of the spirit world.

    The bestiary persists across the game. Every encounter, every
    conversation, every choice adds to it. It is the physical
    manifestation of Aoi's understanding of the world between worlds.
    """

    def __init__(self):
        self.entries: dict[str, BestiaryEntry] = {}
        self.total_encountered: int = 0
        self.total_befriended: int = 0
        self.total_defeated: int = 0
        self.total_purified: int = 0
        self.discovery_log: list[dict] = []

    def load_from_yaml(self, filepath: str) -> int:
        """
        Load spirit definitions from a YAML file.
        Returns the number of entries loaded.
        """
        if not os.path.exists(filepath):
            return 0

        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        if not data or 'spirits' not in data:
            return 0

        count = 0
        for spirit_data in data['spirits']:
            entry = self._parse_spirit_data(spirit_data)
            if entry:
                self.entries[entry.id] = entry
                count += 1

        return count

    def _parse_spirit_data(self, data: dict) -> Optional[BestiaryEntry]:
        """Parse a single spirit from YAML data into a BestiaryEntry."""
        try:
            # Parse element
            element_str = data.get('element', 'neutral').lower()
            element = Element(element_str) if element_str in [
                e.value for e in Element
            ] else Element.NEUTRAL

            secondary_str = data.get('secondary_element', '')
            secondary = (
                Element(secondary_str.lower())
                if secondary_str and secondary_str.lower() in [
                    e.value for e in Element
                ]
                else None
            )

            # Parse category
            cat_str = data.get('category', 'nature').lower()
            category = SpiritCategory(cat_str) if cat_str in [
                c.value for c in SpiritCategory
            ] else SpiritCategory.NATURE

            # Parse stats
            stats_data = data.get('stats', {})
            stats = SpiritStats(
                base_hp=stats_data.get('hp', 50),
                base_sp=stats_data.get('sp', 30),
                attack=stats_data.get('attack', 8),
                defense=stats_data.get('defense', 8),
                spirit_power=stats_data.get('spirit_power', 10),
                spirit_defense=stats_data.get('spirit_defense', 10),
                speed=stats_data.get('speed', 10),
                evasion=stats_data.get('evasion', 0.05),
            )

            # Parse weaknesses/resistances
            weaknesses = [
                Element(w.lower()) for w in data.get('weaknesses', [])
                if w.lower() in [e.value for e in Element]
            ]
            resistances = [
                Element(r.lower()) for r in data.get('resistances', [])
                if r.lower() in [e.value for e in Element]
            ]

            # Parse lore fragments
            lore_fragments = []
            for lore_data in data.get('lore_fragments', []):
                level_str = lore_data.get('level', 'basic').upper()
                try:
                    level = RevealLevel[level_str]
                except KeyError:
                    level = RevealLevel.BASIC
                lore_fragments.append(SpiritLoreFragment(
                    text=lore_data.get('text', ''),
                    reveal_level=level,
                    source=lore_data.get('source', ''),
                ))

            entry = BestiaryEntry(
                id=data['id'],
                name=data.get('name', data['id']),
                name_jp=data.get('name_jp', ''),
                category=category,
                element=element,
                secondary_element=secondary,
                level=data.get('level', 1),
                stats=stats,
                silhouette_desc=data.get('silhouette_desc', ''),
                basic_desc=data.get('basic_desc', ''),
                detailed_desc=data.get('detailed_desc', ''),
                behavioral_desc=data.get('behavioral_desc', ''),
                complete_desc=data.get('complete_desc', ''),
                personality_traits=data.get('personality_traits', []),
                desires=data.get('desires', []),
                fears=data.get('fears', []),
                negotiation_hints=data.get('negotiation_hints', []),
                preferred_negotiation=data.get('preferred_negotiation', ''),
                habitats=data.get('habitats', []),
                active_times=data.get('active_times', []),
                appearance_conditions=data.get('appearance_conditions', ''),
                can_be_corrupted=data.get('can_be_corrupted', True),
                base_corruption=data.get('base_corruption', 0.0),
                loot_table=data.get('loot_table', {}),
                spirit_essence_value=data.get('spirit_essence_value', 10),
                grants_ability=data.get('grants_ability'),
                actual_weaknesses=weaknesses,
                actual_resistances=resistances,
                actual_abilities=data.get('abilities', []),
                lore_fragments=lore_fragments,
                sprite_key=data.get('sprite_key', ''),
                silhouette_sprite=data.get('silhouette_sprite', ''),
            )

            return entry

        except (KeyError, ValueError) as e:
            print(f"Warning: Failed to parse spirit data: {e}")
            return None

    def get_entry(self, spirit_id: str) -> Optional[BestiaryEntry]:
        """Get a bestiary entry by ID."""
        return self.entries.get(spirit_id)

    def record_encounter(self, spirit_id: str,
                         result: str = "observed") -> list[str]:
        """Record an encounter and return revelations."""
        entry = self.entries.get(spirit_id)
        if not entry:
            return []

        was_unknown = entry.reveal_level == RevealLevel.UNKNOWN
        revelations = entry.record_encounter(result)

        if was_unknown:
            self.total_encountered += 1
            self.discovery_log.append({
                "spirit_id": spirit_id,
                "name": entry.name,
                "category": entry.category.value,
                "result": result,
            })

        if result == "befriended":
            self.total_befriended += 1
        elif result == "defeated":
            self.total_defeated += 1
        elif result == "purified":
            self.total_purified += 1

        return revelations

    def get_entries_by_category(self,
                                category: SpiritCategory) -> list[BestiaryEntry]:
        """Get all entries of a specific category."""
        return [
            e for e in self.entries.values() if e.category == category
        ]

    def get_discovered_entries(self) -> list[BestiaryEntry]:
        """Get all entries that have been encountered at least once."""
        return [
            e for e in self.entries.values()
            if e.reveal_level != RevealLevel.UNKNOWN
        ]

    def get_completion_percentage(self) -> float:
        """How complete is the bestiary?"""
        if not self.entries:
            return 0.0
        total_knowledge = sum(e.knowledge for e in self.entries.values())
        max_knowledge = len(self.entries)
        return (total_knowledge / max_knowledge) * 100.0

    def get_category_completion(self,
                                category: SpiritCategory) -> tuple[int, int]:
        """Returns (discovered, total) for a category."""
        entries = self.get_entries_by_category(category)
        discovered = sum(
            1 for e in entries if e.reveal_level != RevealLevel.UNKNOWN
        )
        return discovered, len(entries)

    def search(self, query: str) -> list[BestiaryEntry]:
        """Search the bestiary by name or description keyword."""
        query_lower = query.lower()
        results = []
        for entry in self.entries.values():
            if entry.reveal_level == RevealLevel.UNKNOWN:
                continue
            if (query_lower in entry.name.lower()
                    or query_lower in entry.name_jp
                    or query_lower in entry.get_display_description().lower()):
                results.append(entry)
        return results

    def get_statistics(self) -> dict:
        """Get overall bestiary statistics."""
        entries = list(self.entries.values())
        return {
            "total_spirits": len(entries),
            "total_discovered": sum(
                1 for e in entries
                if e.reveal_level != RevealLevel.UNKNOWN
            ),
            "total_complete": sum(
                1 for e in entries
                if e.reveal_level == RevealLevel.COMPLETE
            ),
            "total_befriended": self.total_befriended,
            "total_defeated": self.total_defeated,
            "total_purified": self.total_purified,
            "completion_percentage": self.get_completion_percentage(),
            "category_progress": {
                cat.value: self.get_category_completion(cat)
                for cat in SpiritCategory
            },
        }

    def export_discovered(self) -> dict:
        """Export all discovered entries for save/display."""
        discovered = {}
        for entry in self.get_discovered_entries():
            discovered[entry.id] = {
                "name": entry.get_display_name(),
                "category": entry.category.value,
                "reveal_level": entry.reveal_level.name,
                "knowledge": entry.knowledge,
                "description": entry.get_display_description(),
                "element": entry.element.value if entry.reveal_level.value >= RevealLevel.BASIC.value else "???",
                "times_encountered": entry.times_encountered,
                "times_befriended": entry.times_befriended,
                "is_befriended": entry.is_befriended,
                "bond_level": entry.bond_level,
                "known_weaknesses": [w.value for w in entry.known_weaknesses],
                "unlocked_lore": entry.unlocked_lore,
            }
        return discovered
