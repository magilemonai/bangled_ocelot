"""
Ma no Kuni - Player Character: Aoi (葵)

Aoi -- named for the hollyhock, a flower that turns toward the sun.
Nonbinary, quiet, perceptive. They live with their grandmother Haruki
and her cat Mikan in a small house where the garden hums with
something that isn't quite wind.

After the falling out with their parents, Aoi retreated into the
spaces between -- between worlds, between words, between breaths.
That liminal instinct is what makes them the bridge.

Their spirit sight didn't appear suddenly. It started as a flicker
at the edge of vision, a shape in steam rising from a teacup,
a shadow that moved against the light. It grew.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class StatType(Enum):
    """The six qualities that define Aoi's way of being in the world."""
    EMPATHY = "empathy"                 # Understanding others' feelings -- human and spirit
    PERCEPTION = "perception"           # Noticing what others miss
    RESOLVE = "resolve"                 # Inner strength, will to continue
    SPIRIT_AFFINITY = "spirit_affinity" # Resonance with the spirit world
    CRAFT_SKILL = "craft_skill"         # Ability to make and mend things
    KNOWLEDGE = "knowledge"             # Lore, history, understanding of both worlds


@dataclass
class Stat:
    """A single character stat with base value and modifiers."""
    base: int = 5
    modifier: int = 0
    experience: float = 0.0
    level_thresholds: tuple[float, ...] = (10.0, 25.0, 50.0, 100.0, 200.0, 400.0)

    @property
    def effective(self) -> int:
        return max(0, self.base + self.modifier)

    def gain_experience(self, amount: float) -> bool:
        """
        Gain experience toward the next stat level.
        Returns True if the stat leveled up.
        """
        self.experience += amount
        threshold_idx = min(self.base - 1, len(self.level_thresholds) - 1)
        threshold_idx = max(0, threshold_idx)
        if self.experience >= self.level_thresholds[threshold_idx]:
            self.experience -= self.level_thresholds[threshold_idx]
            self.base += 1
            return True
        return False


@dataclass
class StatBlock:
    """Aoi's complete stat profile."""
    empathy: Stat = field(default_factory=lambda: Stat(base=7))
    perception: Stat = field(default_factory=lambda: Stat(base=6))
    resolve: Stat = field(default_factory=lambda: Stat(base=4))
    spirit_affinity: Stat = field(default_factory=lambda: Stat(base=5))
    craft_skill: Stat = field(default_factory=lambda: Stat(base=3))
    knowledge: Stat = field(default_factory=lambda: Stat(base=5))

    def get(self, stat_type: StatType) -> Stat:
        return getattr(self, stat_type.value)

    def effective(self, stat_type: StatType) -> int:
        return self.get(stat_type).effective


# ---------------------------------------------------------------------------
# Spirit Sight
# ---------------------------------------------------------------------------

class SpiritSightLevel(Enum):
    """
    Spirit sight grows like a muscle, or maybe like a wound that never
    fully closes. Each stage brings more clarity -- and more vulnerability.
    """
    DORMANT = 0         # Before awakening
    FLICKERING = 1      # Fleeting glimpses at the edge of vision
    GLIMMERING = 2      # Spirits visible in reflections, steam, water
    CLARIFYING = 3      # Direct sight of nearby spirits, brief and tiring
    SUSTAINED = 4       # Can maintain spirit vision for extended periods
    DUAL_VISION = 5     # Sees both worlds simultaneously, always


@dataclass
class SpiritSight:
    """
    Aoi's ability to perceive the spirit world. It develops through
    use, exposure, and -- crucially -- through quiet attention.
    Forcing it causes strain. Letting it come naturally builds strength.
    """
    level: SpiritSightLevel = SpiritSightLevel.DORMANT
    experience: float = 0.0
    strain: float = 0.0
    max_strain: float = 100.0
    active: bool = False
    duration_this_session: float = 0.0

    # How much experience is needed to reach each level
    level_thresholds: dict[SpiritSightLevel, float] = field(default_factory=lambda: {
        SpiritSightLevel.DORMANT: 0.0,
        SpiritSightLevel.FLICKERING: 15.0,
        SpiritSightLevel.GLIMMERING: 40.0,
        SpiritSightLevel.CLARIFYING: 80.0,
        SpiritSightLevel.SUSTAINED: 150.0,
        SpiritSightLevel.DUAL_VISION: 300.0,
    })

    def activate(self) -> tuple[bool, str]:
        """
        Attempt to engage spirit sight. Returns (success, flavor_text).
        """
        if self.level == SpiritSightLevel.DORMANT:
            return False, ""

        if self.strain >= self.max_strain * 0.9:
            return False, (
                "Your vision blurs. The strain is too much -- "
                "the world between recedes like a tide pulling away."
            )

        self.active = True
        self.duration_this_session = 0.0

        flavor = {
            SpiritSightLevel.FLICKERING: (
                "The edges of things shimmer. For a moment, just a moment, "
                "you see light where there shouldn't be any."
            ),
            SpiritSightLevel.GLIMMERING: (
                "The world doubles. In every reflection -- windows, puddles, "
                "the dark screen of your phone -- another world looks back."
            ),
            SpiritSightLevel.CLARIFYING: (
                "You open the eye that has no name. The spirit world unfolds "
                "around you like a flower, vivid and close."
            ),
            SpiritSightLevel.SUSTAINED: (
                "The veil parts smoothly now. Both worlds layer over each other, "
                "translucent, breathing together."
            ),
            SpiritSightLevel.DUAL_VISION: (
                "There is no veil. There never was. The two worlds are one world, "
                "and you see it whole."
            ),
        }
        return True, flavor.get(self.level, "")

    def deactivate(self) -> None:
        self.active = False
        self.duration_this_session = 0.0

    def update(self, delta: float, permeability: float) -> Optional[str]:
        """
        Update spirit sight state. High permeability reduces strain.
        Returns a message if the level changes.
        """
        if not self.active:
            # Strain recovers when sight is off
            self.strain = max(0.0, self.strain - delta * 2.0)
            return None

        self.duration_this_session += delta

        # Strain increases while active, reduced by permeability
        strain_rate = max(0.2, 1.0 - permeability * 0.7)
        self.strain += delta * strain_rate

        # Experience gained while actively using sight
        self.experience += delta * 0.5

        # Auto-deactivate if strain is critical
        if self.strain >= self.max_strain:
            self.deactivate()
            return (
                "The strain overwhelms you. Spirit sight snaps shut "
                "like a door slamming in a storm."
            )

        # Check for level advancement
        next_level_value = self.level.value + 1
        try:
            next_level = SpiritSightLevel(next_level_value)
        except ValueError:
            return None  # Already at max level

        threshold = self.level_thresholds.get(next_level, float("inf"))
        if self.experience >= threshold:
            self.level = next_level
            self.experience = 0.0
            return f"Your spirit sight deepens. You have reached: {next_level.name}."

        return None

    @property
    def clarity(self) -> float:
        """
        How clear is the spirit vision right now?  0.0 to 1.0.
        Affected by level, strain, and whether sight is active.
        """
        if not self.active:
            return 0.0
        base = self.level.value / SpiritSightLevel.DUAL_VISION.value
        strain_penalty = (self.strain / self.max_strain) * 0.5
        return max(0.0, min(1.0, base - strain_penalty))


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

class ItemCategory(Enum):
    """Items exist in the material world, the spirit world, or both."""
    MATERIAL = "material"             # Ordinary objects
    SPIRIT_TOUCHED = "spirit_touched" # Material objects with spirit resonance
    SPIRIT = "spirit"                 # Objects that exist only in the spirit world
    CRAFT_COMPONENT = "craft_component"
    KEY = "key"                       # Plot items
    GIFT = "gift"                     # Items meant for giving


@dataclass
class Item:
    """An object that matters enough to carry."""
    id: str
    name: str
    description: str
    category: ItemCategory
    quantity: int = 1
    max_stack: int = 99
    spirit_resonance: float = 0.0     # 0.0 = mundane, 1.0 = pure spirit
    can_gift: bool = False
    gift_preferences: dict[str, float] = field(default_factory=dict)
    tags: set[str] = field(default_factory=set)
    lore: str = ""                    # Hidden description revealed by Knowledge


@dataclass
class Inventory:
    """
    Aoi's belongings -- what they choose to carry says something about them.
    Some items are visible only with spirit sight active.
    """
    items: dict[str, Item] = field(default_factory=dict)
    capacity: int = 30

    def add(self, item: Item) -> tuple[bool, str]:
        """Add an item. Returns (success, message)."""
        if item.id in self.items:
            existing = self.items[item.id]
            space = existing.max_stack - existing.quantity
            if space <= 0:
                return False, f"Cannot carry any more {item.name}."
            added = min(item.quantity, space)
            existing.quantity += added
            return True, f"Received {item.name}" + (f" x{added}" if added > 1 else "") + "."

        if len(self.items) >= self.capacity:
            return False, "Your bag is full. Something must be left behind."

        self.items[item.id] = item
        return True, f"Received {item.name}."

    def remove(self, item_id: str, quantity: int = 1) -> Optional[Item]:
        """Remove quantity of an item. Returns the removed item or None."""
        if item_id not in self.items:
            return None
        item = self.items[item_id]
        if quantity >= item.quantity:
            del self.items[item_id]
            return item
        item.quantity -= quantity
        removed = Item(
            id=item.id, name=item.name, description=item.description,
            category=item.category, quantity=quantity,
            spirit_resonance=item.spirit_resonance,
        )
        return removed

    def has(self, item_id: str, quantity: int = 1) -> bool:
        return item_id in self.items and self.items[item_id].quantity >= quantity

    def get_visible_items(self, spirit_sight_clarity: float) -> list[Item]:
        """
        Return items Aoi can currently perceive.
        Pure spirit items require spirit sight to see.
        """
        visible = []
        for item in self.items.values():
            if item.category == ItemCategory.SPIRIT:
                if spirit_sight_clarity >= 0.3:
                    visible.append(item)
            else:
                visible.append(item)
        return visible

    def get_giftable_items(self) -> list[Item]:
        return [item for item in self.items.values() if item.can_gift]


# ---------------------------------------------------------------------------
# Emotional state
# ---------------------------------------------------------------------------

class Emotion(Enum):
    """
    Not moods but currents -- deep emotional undercurrents that shape
    how Aoi moves through the world.
    """
    CALM = "calm"
    ANXIOUS = "anxious"
    MELANCHOLY = "melancholy"
    HOPEFUL = "hopeful"
    DETERMINED = "determined"
    GRIEVING = "grieving"
    CURIOUS = "curious"
    UNSETTLED = "unsettled"
    CONNECTED = "connected"     # Feeling close to someone or something
    LIMINAL = "liminal"         # Between states, open to anything


@dataclass
class EmotionalState:
    """
    Aoi's inner weather. Affects dialogue options, spirit interactions,
    and how the world responds to them.

    Emotions don't switch instantly -- they blend and shift like
    watercolors bleeding into each other.
    """
    primary: Emotion = Emotion.CALM
    secondary: Optional[Emotion] = None
    intensities: dict[Emotion, float] = field(default_factory=lambda: {
        e: 0.0 for e in Emotion
    })
    history: list[tuple[Emotion, float]] = field(default_factory=list)
    _max_history: int = 50

    def __post_init__(self) -> None:
        self.intensities[self.primary] = 0.6

    def shift(self, emotion: Emotion, intensity: float, source: str = "") -> None:
        """
        Shift emotional state. Emotions blend; they don't replace.
        intensity should be 0.0 to 1.0.
        """
        # Increase the target emotion
        self.intensities[emotion] = min(
            1.0, self.intensities.get(emotion, 0.0) + intensity
        )

        # Decay all other emotions slightly
        for e in Emotion:
            if e != emotion:
                self.intensities[e] = max(
                    0.0, self.intensities.get(e, 0.0) - intensity * 0.15
                )

        # Recalculate primary and secondary
        sorted_emotions = sorted(
            self.intensities.items(), key=lambda x: x[1], reverse=True
        )
        self.primary = sorted_emotions[0][0]
        self.secondary = (
            sorted_emotions[1][0] if sorted_emotions[1][1] > 0.1 else None
        )

        # Record history
        self.history.append((emotion, intensity))
        if len(self.history) > self._max_history:
            self.history = self.history[-self._max_history:]

    def decay(self, delta: float) -> None:
        """All emotions drift toward calm over time."""
        for e in Emotion:
            if e == Emotion.CALM:
                # Calm slowly reasserts itself
                self.intensities[e] = min(
                    0.6, self.intensities[e] + delta * 0.02
                )
            else:
                self.intensities[e] = max(
                    0.0, self.intensities[e] - delta * 0.01
                )

    @property
    def spirit_resonance_modifier(self) -> float:
        """
        How the current emotional state affects spirit interactions.
        Calm and liminal states are most receptive.
        Anxiety repels spirits. Grief draws specific ones.
        """
        modifiers = {
            Emotion.CALM: 0.2,
            Emotion.ANXIOUS: -0.3,
            Emotion.MELANCHOLY: 0.0,
            Emotion.HOPEFUL: 0.1,
            Emotion.DETERMINED: 0.0,
            Emotion.GRIEVING: 0.15,
            Emotion.CURIOUS: 0.1,
            Emotion.UNSETTLED: -0.1,
            Emotion.CONNECTED: 0.25,
            Emotion.LIMINAL: 0.4,
        }
        primary_mod = modifiers.get(self.primary, 0.0)
        secondary_mod = modifiers.get(self.secondary, 0.0) if self.secondary else 0.0
        return primary_mod * 0.7 + secondary_mod * 0.3

    def available_dialogue_tones(self) -> list[str]:
        """
        What conversational tones are available given the current
        emotional state? Not all responses are possible in all moods.
        """
        tones = ["neutral", "silence"]  # Always available

        if self.intensities[Emotion.CALM] > 0.3:
            tones.extend(["gentle", "thoughtful", "reassuring"])
        if self.intensities[Emotion.DETERMINED] > 0.3:
            tones.extend(["firm", "direct", "challenging"])
        if self.intensities[Emotion.CURIOUS] > 0.2:
            tones.extend(["questioning", "probing", "wondering"])
        if self.intensities[Emotion.MELANCHOLY] > 0.3:
            tones.extend(["wistful", "vulnerable"])
        if self.intensities[Emotion.HOPEFUL] > 0.3:
            tones.extend(["encouraging", "optimistic"])
        if self.intensities[Emotion.ANXIOUS] > 0.4:
            tones.extend(["hesitant", "deflecting"])
        if self.intensities[Emotion.CONNECTED] > 0.4:
            tones.extend(["warm", "intimate", "honest"])
        if self.intensities[Emotion.LIMINAL] > 0.3:
            tones.extend(["cryptic", "dreaming"])
        if self.intensities[Emotion.GRIEVING] > 0.3:
            tones.extend(["raw", "withdrawn"])

        return tones


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

class MemorySignificance(Enum):
    """Not all memories weigh the same."""
    FLEETING = 1    # Small moments, may be forgotten
    NOTABLE = 2     # Worth remembering
    IMPORTANT = 3   # Shapes future interactions
    DEFINING = 4    # Changes who Aoi is
    INDELIBLE = 5   # Can never be undone


@dataclass
class Memory:
    """
    A single memory. Aoi carries these, and they shape every
    future interaction. Some memories are shared with others,
    creating bonds that cannot be broken -- or wounds that
    cannot be healed.
    """
    id: str
    description: str
    significance: MemorySignificance
    participants: list[str] = field(default_factory=list)
    location: str = ""
    emotion: Optional[Emotion] = None
    tags: set[str] = field(default_factory=set)
    day_formed: int = 0
    referenced_count: int = 0
    fading: bool = False  # Fleeting memories can fade

    def reference(self) -> None:
        """When a memory is recalled, it strengthens."""
        self.referenced_count += 1
        if self.fading:
            self.fading = False


@dataclass
class MemorySystem:
    """
    Aoi's memory. The past is always present.
    Characters reference shared memories in dialogue.
    Choices echo forward through time.
    """
    memories: dict[str, Memory] = field(default_factory=dict)

    def record(self, memory: Memory) -> None:
        self.memories[memory.id] = memory

    def recall(self, memory_id: str) -> Optional[Memory]:
        mem = self.memories.get(memory_id)
        if mem:
            mem.reference()
        return mem

    def has_memory(self, memory_id: str) -> bool:
        return memory_id in self.memories

    def memories_with(self, participant: str) -> list[Memory]:
        """All memories involving a specific character."""
        return [
            m for m in self.memories.values()
            if participant in m.participants
        ]

    def memories_at(self, location: str) -> list[Memory]:
        return [
            m for m in self.memories.values()
            if m.location == location
        ]

    def memories_tagged(self, tag: str) -> list[Memory]:
        return [m for m in self.memories.values() if tag in m.tags]

    def defining_memories(self) -> list[Memory]:
        return [
            m for m in self.memories.values()
            if m.significance.value >= MemorySignificance.DEFINING.value
        ]

    def fade_old_memories(self, current_day: int, threshold_days: int = 30) -> list[str]:
        """
        Fleeting memories fade if not referenced. Significant ones persist.
        Returns IDs of faded memories.
        """
        faded: list[str] = []
        for mem_id, mem in list(self.memories.items()):
            if mem.significance == MemorySignificance.FLEETING:
                age = current_day - mem.day_formed
                if age > threshold_days and mem.referenced_count == 0:
                    mem.fading = True
                if mem.fading and mem.referenced_count == 0 and age > threshold_days * 2:
                    faded.append(mem_id)
                    del self.memories[mem_id]
        return faded

    def get_relevant_memories(
        self,
        participant: Optional[str] = None,
        location: Optional[str] = None,
        tags: Optional[set[str]] = None,
        min_significance: MemorySignificance = MemorySignificance.FLEETING,
    ) -> list[Memory]:
        """Query memories by multiple criteria. Used by the dialogue system."""
        results = list(self.memories.values())

        if participant:
            results = [m for m in results if participant in m.participants]
        if location:
            results = [m for m in results if m.location == location]
        if tags:
            results = [m for m in results if tags & m.tags]
        results = [
            m for m in results
            if m.significance.value >= min_significance.value
        ]

        return sorted(results, key=lambda m: m.significance.value, reverse=True)


# ---------------------------------------------------------------------------
# Player Character
# ---------------------------------------------------------------------------

@dataclass
class PlayerCharacter:
    """
    Aoi (葵). The hollyhock. The one who stands between.

    They didn't ask for this. They didn't ask for any of it --
    not the silence with their parents, not the spirits in the
    garden, not the way the world keeps splitting open to show
    another world underneath.

    But they're here. And they're paying attention.
    That matters more than they know.
    """
    name: str = "Aoi"
    pronouns: tuple[str, str, str] = ("they", "them", "their")

    stats: StatBlock = field(default_factory=StatBlock)
    spirit_sight: SpiritSight = field(default_factory=SpiritSight)
    inventory: Inventory = field(default_factory=Inventory)
    emotional_state: EmotionalState = field(default_factory=EmotionalState)
    memories: MemorySystem = field(default_factory=MemorySystem)

    # Progression
    level: int = 1
    experience: float = 0.0
    spirit_bonds: dict[str, float] = field(default_factory=dict)

    # Story state
    chapter: int = 1
    active_quests: list[str] = field(default_factory=list)
    completed_quests: list[str] = field(default_factory=list)
    flags: dict[str, bool] = field(default_factory=dict)

    # Location
    current_district: str = "yanaka"
    current_location: str = "grandmother_house"

    # Relationships -- character_id -> relationship_id (managed by RelationshipSystem)
    relationship_ids: dict[str, str] = field(default_factory=dict)

    def update(self, delta: float, permeability: float) -> list[str]:
        """
        Update Aoi's systems. Returns list of notable events.
        """
        events: list[str] = []

        # Update spirit sight
        sight_msg = self.spirit_sight.update(delta, permeability)
        if sight_msg:
            events.append(sight_msg)

        # Emotional decay toward equilibrium
        self.emotional_state.decay(delta)

        return events

    def can_see_spirit(self, spirit_visibility: float) -> bool:
        """Can Aoi perceive a spirit with the given visibility threshold?"""
        if self.spirit_sight.active:
            return self.spirit_sight.clarity >= spirit_visibility
        # Even without active sight, high-level seers catch glimpses
        if self.spirit_sight.level.value >= SpiritSightLevel.SUSTAINED.value:
            return spirit_visibility >= 0.8
        return False

    def gain_stat_experience(
        self, stat_type: StatType, amount: float
    ) -> Optional[str]:
        """Award experience to a stat. Returns message if leveled up."""
        stat = self.stats.get(stat_type)
        if stat.gain_experience(amount):
            return (
                f"Your {stat_type.value.replace('_', ' ')} has deepened. "
                f"It is now {stat.base}."
            )
        return None

    def record_memory(
        self,
        memory_id: str,
        description: str,
        significance: MemorySignificance,
        participants: Optional[list[str]] = None,
        location: Optional[str] = None,
        tags: Optional[set[str]] = None,
        day: int = 0,
    ) -> Memory:
        """Record a new memory. The world remembers through Aoi."""
        memory = Memory(
            id=memory_id,
            description=description,
            significance=significance,
            participants=participants or [],
            location=location or self.current_location,
            emotion=self.emotional_state.primary,
            tags=tags or set(),
            day_formed=day,
        )
        self.memories.record(memory)
        return memory

    def set_flag(self, flag: str, value: bool = True) -> None:
        self.flags[flag] = value

    def check_flag(self, flag: str) -> bool:
        return self.flags.get(flag, False)

    @property
    def spirit_affinity_total(self) -> float:
        """
        Overall spirit affinity combining stat, emotional state,
        and spirit sight level.
        """
        base = self.stats.effective(StatType.SPIRIT_AFFINITY) / 10.0
        emotion_mod = self.emotional_state.spirit_resonance_modifier
        sight_mod = self.spirit_sight.level.value * 0.05
        return min(1.0, base + emotion_mod + sight_mod)
