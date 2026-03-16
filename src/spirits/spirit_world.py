"""
Ma no Kuni - Spirit World Mechanics

The spirit world is not another place. It is THIS place, seen truly.

A lonely apartment becomes a vast empty field because that is what it IS.
A beloved ramen shop becomes a warm glowing hearth because decades of
comfort and belonging have soaked into its walls. A corporate tower
becomes a cold crystalline spire draining color from its surroundings
because that is the spiritual truth of what it does.

The spirit world has its own ecology, its own weather, its own politics.
Greater spirits hold territories. Lesser spirits form communities. And
beneath it all, the great kami of the rivers and mountains that Tokyo
was built over still remember what was here before.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.engine.game import WorldClock, MoonPhase, Season, TimeOfDay


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class SpiritRank(Enum):
    """The hierarchy of spiritual beings, from least to greatest."""
    MOTE = "mote"                  # Barely conscious wisps of spiritual energy
    MINOR = "minor"                # Small spirits - kodama, minor yokai
    COMMON = "common"              # Established spirits with identity and territory
    NOTABLE = "notable"            # Spirits known by name, with influence
    GREATER = "greater"            # Powerful spirits commanding regions
    ANCIENT = "ancient"            # Kami of rivers, mountains, old roads
    SOVEREIGN = "sovereign"        # The spirit of Tokyo itself, the mountain gods

    @property
    def power_range(self) -> tuple[int, int]:
        ranges = {
            SpiritRank.MOTE: (1, 5),
            SpiritRank.MINOR: (5, 15),
            SpiritRank.COMMON: (15, 35),
            SpiritRank.NOTABLE: (35, 60),
            SpiritRank.GREATER: (60, 85),
            SpiritRank.ANCIENT: (85, 97),
            SpiritRank.SOVEREIGN: (97, 100),
        }
        return ranges[self]


class SpiritElement(Enum):
    """Elemental affinities, drawn from Japanese tradition and urban reality."""
    FIRE = "fire"             # Hi - passion, destruction, warmth
    WATER = "water"           # Mizu - flow, memory, reflection
    EARTH = "earth"           # Tsuchi - stability, stubbornness, growth
    WIND = "wind"             # Kaze - freedom, change, restlessness
    VOID = "void"             # Ku - emptiness, potential, the unseen
    LIGHT = "light"           # Hikari - truth, exposure, blinding clarity
    SHADOW = "shadow"         # Kage - secrets, protection, the hidden
    METAL = "metal"           # Kin - modernity, industry, endurance
    WOOD = "wood"             # Ki - life, memory, patience
    EMOTION = "emotion"       # Kokoro - human feeling made manifest


class SpiritDisposition(Enum):
    """How a spirit fundamentally relates to the material world and humans."""
    BENEVOLENT = "benevolent"     # Actively helpful, protective
    CURIOUS = "curious"          # Drawn to humans, playful, sometimes mischievous
    INDIFFERENT = "indifferent"  # Concerned with spirit matters, ignores humans
    TERRITORIAL = "territorial"  # Tolerates humans unless boundaries crossed
    WARY = "wary"                # Distrustful, avoids contact, watches from distance
    HOSTILE = "hostile"          # Actively antagonistic (often due to corruption or grievance)
    MOURNING = "mourning"        # Grieving a loss - a destroyed shrine, a forgotten name
    DREAMING = "dreaming"        # Half-asleep, drifting between awareness and oblivion


class SpiritWeatherType(Enum):
    """Weather in the spirit world is emotional and metaphorical."""
    CALM = "calm"                        # Peaceful stillness
    MEMORY_RAIN = "memory_rain"          # Rain that carries fragments of the past
    YEARNING_WIND = "yearning_wind"      # Wind that pulls toward lost things
    SORROW_FOG = "sorrow_fog"            # Dense fog born from collective grief
    JOY_BLOOM = "joy_bloom"              # Flowers erupt from nothing, color intensifies
    ANGER_STORM = "anger_storm"          # Violent spiritual turbulence
    NOSTALGIA_SNOW = "nostalgia_snow"    # Gentle snow that evokes old memories
    VOID_TIDE = "void_tide"              # The void seeps in, muting everything
    RESONANCE_AURORA = "resonance_aurora" # The worlds harmonize, aurora fills the sky
    CORRUPTION_HAZE = "corruption_haze"  # Sickly distortion from MIRAIKAN extraction


class TerritoryStatus(Enum):
    """The state of a spirit's claim over a region."""
    UNCLAIMED = "unclaimed"
    CLAIMED = "claimed"
    CONTESTED = "contested"      # Multiple spirits vying for control
    SHARED = "shared"            # Peaceful coexistence
    CORRUPTED = "corrupted"      # Tainted by extraction
    SEALED = "sealed"            # Deliberately locked away
    AWAKENING = "awakening"      # Territory coming alive for the first time


class SpiritRelationshipType(Enum):
    """How spirits relate to one another in the ecology."""
    SYMBIOTIC = "symbiotic"       # Mutually beneficial
    PREDATORY = "predatory"       # One feeds on the other's energy
    PARASITIC = "parasitic"       # One-sided drain
    COMPETITIVE = "competitive"   # Rivals for territory or resources
    FAMILIAL = "familial"         # Part of the same spiritual lineage
    MENTOR = "mentor"             # Elder guides younger
    SWORN = "sworn"               # Bound by oath or ancient pact
    ADVERSARIAL = "adversarial"   # Deep enmity


# ---------------------------------------------------------------------------
# Core Data Structures
# ---------------------------------------------------------------------------

@dataclass
class SpiritWeather:
    """
    The weather of the spirit world. It does not rain water here.
    It rains memories. The wind carries longing. The fog is made of grief.

    Spirit weather affects spirit behavior, combat modifiers, and which
    spirits are active or dormant.
    """
    current: SpiritWeatherType = SpiritWeatherType.CALM
    intensity: float = 0.5           # 0.0 = barely noticeable, 1.0 = overwhelming
    duration_remaining: int = 0      # Turns until weather shifts
    previous: SpiritWeatherType = SpiritWeatherType.CALM
    forecast: list[SpiritWeatherType] = field(default_factory=list)
    transition_progress: float = 0.0  # 0.0 = old weather, 1.0 = new weather

    # Modifiers that current weather applies
    _element_modifiers: dict[SpiritElement, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self._element_modifiers:
            self._recalculate_modifiers()

    def _recalculate_modifiers(self) -> None:
        """Each weather type strengthens or weakens certain elements."""
        modifier_table: dict[SpiritWeatherType, dict[SpiritElement, float]] = {
            SpiritWeatherType.CALM: {},
            SpiritWeatherType.MEMORY_RAIN: {
                SpiritElement.WATER: 0.3, SpiritElement.EMOTION: 0.2,
                SpiritElement.FIRE: -0.1,
            },
            SpiritWeatherType.YEARNING_WIND: {
                SpiritElement.WIND: 0.3, SpiritElement.EMOTION: 0.15,
                SpiritElement.EARTH: -0.1,
            },
            SpiritWeatherType.SORROW_FOG: {
                SpiritElement.SHADOW: 0.3, SpiritElement.VOID: 0.2,
                SpiritElement.LIGHT: -0.3, SpiritElement.EMOTION: 0.25,
            },
            SpiritWeatherType.JOY_BLOOM: {
                SpiritElement.WOOD: 0.3, SpiritElement.LIGHT: 0.2,
                SpiritElement.EMOTION: 0.3, SpiritElement.SHADOW: -0.2,
            },
            SpiritWeatherType.ANGER_STORM: {
                SpiritElement.FIRE: 0.3, SpiritElement.WIND: 0.2,
                SpiritElement.EMOTION: 0.35, SpiritElement.WATER: -0.1,
            },
            SpiritWeatherType.NOSTALGIA_SNOW: {
                SpiritElement.WATER: 0.15, SpiritElement.VOID: 0.15,
                SpiritElement.EMOTION: 0.2, SpiritElement.METAL: -0.1,
            },
            SpiritWeatherType.VOID_TIDE: {
                SpiritElement.VOID: 0.5, SpiritElement.SHADOW: 0.2,
                SpiritElement.LIGHT: -0.3, SpiritElement.FIRE: -0.2,
                SpiritElement.EMOTION: -0.2,
            },
            SpiritWeatherType.RESONANCE_AURORA: {
                SpiritElement.LIGHT: 0.3, SpiritElement.EMOTION: 0.3,
                SpiritElement.VOID: 0.15,
            },
            SpiritWeatherType.CORRUPTION_HAZE: {
                SpiritElement.METAL: 0.2, SpiritElement.VOID: 0.15,
                SpiritElement.WOOD: -0.3, SpiritElement.WATER: -0.2,
                SpiritElement.EMOTION: -0.15,
            },
        }
        self._element_modifiers = modifier_table.get(self.current, {})

    def get_element_modifier(self, element: SpiritElement) -> float:
        """Get the weather's effect on a specific element, scaled by intensity."""
        base = self._element_modifiers.get(element, 0.0)
        return base * self.intensity

    def transition_to(self, new_weather: SpiritWeatherType,
                      new_intensity: float, duration: int) -> None:
        """Begin transitioning to new weather. Transitions are never instant."""
        self.previous = self.current
        self.current = new_weather
        self.intensity = new_intensity
        self.duration_remaining = duration
        self.transition_progress = 0.0
        self._recalculate_modifiers()

    def update(self, delta: float) -> Optional[SpiritWeatherType]:
        """
        Advance weather. Returns the expired weather type if a transition
        completes, None otherwise.
        """
        if self.transition_progress < 1.0:
            self.transition_progress = min(1.0, self.transition_progress + delta * 0.1)

        if self.duration_remaining > 0:
            self.duration_remaining -= 1
            return None

        # Weather has expired; signal that a new weather should be chosen
        return self.current

    def generate_forecast(self, clock: "WorldClock", permeation_level: float,
                          corruption_level: float) -> list[SpiritWeatherType]:
        """
        Generate upcoming weather based on world state. The spirit world's
        weather is shaped by time, permeation, corruption, and a whisper
        of randomness.
        """
        candidates: list[tuple[SpiritWeatherType, float]] = []

        # Time-based tendencies
        from src.engine.game import TimeOfDay
        time_of_day = clock.time_of_day
        if time_of_day in (TimeOfDay.DAWN, TimeOfDay.DUSK):
            candidates.append((SpiritWeatherType.NOSTALGIA_SNOW, 0.3))
            candidates.append((SpiritWeatherType.MEMORY_RAIN, 0.25))
        elif time_of_day in (TimeOfDay.MIDNIGHT, TimeOfDay.WITCHING):
            candidates.append((SpiritWeatherType.VOID_TIDE, 0.3))
            candidates.append((SpiritWeatherType.ANGER_STORM, 0.15))
        elif time_of_day == TimeOfDay.MORNING:
            candidates.append((SpiritWeatherType.CALM, 0.4))
            candidates.append((SpiritWeatherType.JOY_BLOOM, 0.2))

        # Permeation-driven weather
        if permeation_level > 0.7:
            candidates.append((SpiritWeatherType.RESONANCE_AURORA, 0.35))
            candidates.append((SpiritWeatherType.ANGER_STORM, 0.2))
        elif permeation_level > 0.4:
            candidates.append((SpiritWeatherType.YEARNING_WIND, 0.25))
            candidates.append((SpiritWeatherType.MEMORY_RAIN, 0.2))

        # Corruption drives its own weather
        if corruption_level > 0.5:
            candidates.append((SpiritWeatherType.CORRUPTION_HAZE, 0.4 + corruption_level * 0.3))
            candidates.append((SpiritWeatherType.SORROW_FOG, 0.25))
        elif corruption_level > 0.2:
            candidates.append((SpiritWeatherType.SORROW_FOG, 0.2))

        # Always a chance of calm
        candidates.append((SpiritWeatherType.CALM, 0.15))

        # Weighted selection for forecast
        if not candidates:
            candidates = [(SpiritWeatherType.CALM, 1.0)]

        total_weight = sum(w for _, w in candidates)
        normalized = [(wt, w / total_weight) for wt, w in candidates]

        forecast: list[SpiritWeatherType] = []
        for _ in range(3):
            roll = random.random()
            cumulative = 0.0
            for weather_type, weight in normalized:
                cumulative += weight
                if roll <= cumulative:
                    forecast.append(weather_type)
                    break
            else:
                forecast.append(SpiritWeatherType.CALM)

        self.forecast = forecast
        return forecast


@dataclass
class SpiritTerritory:
    """
    A region of the spirit world claimed by one or more spirits.
    Territories overlap with material-world districts but their
    boundaries are emotional rather than geographic.
    """
    territory_id: str
    name: str
    material_district: str              # Which material district this overlaps
    status: TerritoryStatus = TerritoryStatus.UNCLAIMED
    dominant_element: Optional[SpiritElement] = None
    dominant_spirit_id: Optional[str] = None
    contesting_spirit_ids: list[str] = field(default_factory=list)
    resident_spirit_ids: list[str] = field(default_factory=list)

    # The territory's spiritual character
    emotional_resonance: str = ""       # What emotion soaks this place
    spirit_description: str = ""        # What the player sees in spirit vision
    material_description: str = ""      # What the place looks like normally
    transformation_notes: str = ""      # How material -> spirit translation works

    # Modifiers
    permeation_modifier: float = 0.0    # How much easier/harder to cross here
    corruption_level: float = 0.0       # 0.0 = pure, 1.0 = fully corrupted
    spirit_density: float = 0.5         # How many spirits congregate here
    ambient_power: float = 0.5          # Raw spiritual energy available

    # History
    notable_events: list[str] = field(default_factory=list)
    sealed_since: Optional[int] = None  # Game day when sealed, if applicable

    @property
    def is_habitable(self) -> bool:
        """Can spirits comfortably exist here?"""
        return (
            self.corruption_level < 0.7
            and self.status != TerritoryStatus.SEALED
        )

    @property
    def is_contested(self) -> bool:
        return self.status == TerritoryStatus.CONTESTED

    @property
    def effective_power(self) -> float:
        """Ambient power reduced by corruption."""
        return self.ambient_power * (1.0 - self.corruption_level * 0.7)

    def apply_corruption(self, amount: float) -> float:
        """
        Corrupt this territory. Returns the actual amount applied
        (territories with strong dominant spirits resist).
        """
        resistance = 0.0
        if self.dominant_spirit_id:
            resistance = 0.3
        if self.dominant_element == SpiritElement.WOOD:
            resistance += 0.15
        elif self.dominant_element == SpiritElement.LIGHT:
            resistance += 0.1

        actual = amount * (1.0 - resistance)
        old_level = self.corruption_level
        self.corruption_level = min(1.0, self.corruption_level + actual)

        if old_level < 0.5 <= self.corruption_level:
            self.status = TerritoryStatus.CORRUPTED
            self.notable_events.append("territory_corruption_threshold")

        return actual

    def purify(self, amount: float) -> float:
        """Reduce corruption. Returns amount actually purified."""
        actual = min(self.corruption_level, amount)
        self.corruption_level = max(0.0, self.corruption_level - actual)

        if self.corruption_level < 0.5 and self.status == TerritoryStatus.CORRUPTED:
            self.status = TerritoryStatus.CLAIMED if self.dominant_spirit_id else TerritoryStatus.UNCLAIMED
            self.notable_events.append("territory_purified")

        return actual


@dataclass
class SpiritRelationship:
    """
    A relationship between two spirits. The spirit world has its own
    politics, alliances, feuds, and love stories.
    """
    spirit_a_id: str
    spirit_b_id: str
    relationship_type: SpiritRelationshipType
    strength: float = 0.5              # 0.0 = tenuous, 1.0 = unbreakable
    history: list[str] = field(default_factory=list)
    is_public: bool = True             # Can Aoi discover this through observation?
    tension: float = 0.0               # Accumulated conflict pressure
    cooperation: float = 0.0           # Accumulated cooperative actions

    @property
    def is_positive(self) -> bool:
        return self.relationship_type in (
            SpiritRelationshipType.SYMBIOTIC,
            SpiritRelationshipType.FAMILIAL,
            SpiritRelationshipType.MENTOR,
            SpiritRelationshipType.SWORN,
        )

    @property
    def is_volatile(self) -> bool:
        """Could this relationship shift dramatically?"""
        return self.tension > 0.7 or (
            self.relationship_type == SpiritRelationshipType.COMPETITIVE
            and self.strength > 0.6
        )

    def strain(self, amount: float) -> Optional[str]:
        """
        Apply strain to the relationship. Returns an event string
        if a breaking point is reached.
        """
        self.tension += amount
        self.strength = max(0.0, self.strength - amount * 0.1)

        if self.tension >= 1.0:
            self.tension = 0.0
            if self.is_positive:
                old_type = self.relationship_type
                self.relationship_type = SpiritRelationshipType.COMPETITIVE
                self.history.append(f"relationship_fractured_from_{old_type.value}")
                return "relationship_fractured"
            else:
                self.relationship_type = SpiritRelationshipType.ADVERSARIAL
                self.history.append("relationship_became_adversarial")
                return "relationship_hostile"
        return None

    def strengthen(self, amount: float) -> Optional[str]:
        """
        Strengthen the relationship. Returns event if a milestone
        is reached.
        """
        self.cooperation += amount
        self.strength = min(1.0, self.strength + amount * 0.15)
        self.tension = max(0.0, self.tension - amount * 0.05)

        if self.cooperation >= 1.0 and not self.is_positive:
            self.cooperation = 0.0
            old_type = self.relationship_type
            self.relationship_type = SpiritRelationshipType.SYMBIOTIC
            self.history.append(f"relationship_healed_from_{old_type.value}")
            return "relationship_healed"
        return None


@dataclass
class Spirit:
    """
    A spirit. Not a monster, not an NPC - a being with its own existence,
    its own memories, its own way of understanding the world.

    Some spirits are ancient beyond reckoning. Some awakened yesterday
    from a child's beloved toy. All of them are real.
    """
    spirit_id: str
    name: str
    true_name: Optional[str] = None    # Knowing a spirit's true name grants power
    rank: SpiritRank = SpiritRank.COMMON
    element: SpiritElement = SpiritElement.VOID
    secondary_element: Optional[SpiritElement] = None
    disposition: SpiritDisposition = SpiritDisposition.INDIFFERENT

    # Core stats
    power: int = 20
    resilience: int = 20               # Resistance to corruption, banishment
    awareness: int = 20                # Perception, spiritual sensitivity
    will: int = 20                     # Determination, resistance to control

    # Identity
    origin_story: str = ""             # How this spirit came to be
    appearance_material: str = ""      # What humans see (if anything)
    appearance_spirit: str = ""        # True form in the spirit world
    voice_description: str = ""        # How it communicates
    personality_traits: list[str] = field(default_factory=list)
    memories: list[str] = field(default_factory=list)
    desires: list[str] = field(default_factory=list)
    fears: list[str] = field(default_factory=list)

    # Location and territory
    home_territory_id: Optional[str] = None
    current_territory_id: Optional[str] = None
    wanders: bool = False              # Does this spirit roam?
    wander_range: list[str] = field(default_factory=list)  # Territory IDs

    # State
    is_corrupted: bool = False
    corruption_level: float = 0.0
    is_dormant: bool = False           # Sleeping / inactive
    is_sealed: bool = False            # Deliberately imprisoned
    is_bonded: bool = False            # Bonded to Aoi
    bond_id: Optional[str] = None
    is_visible_material: bool = False  # Can be seen without spirit vision

    # Combat
    abilities: list[str] = field(default_factory=list)
    combat_style: str = ""
    weakness_element: Optional[SpiritElement] = None
    resistance_element: Optional[SpiritElement] = None

    # Behavior
    active_times: list[str] = field(default_factory=list)  # TimeOfDay values
    preferred_weather: list[SpiritWeatherType] = field(default_factory=list)
    dialogue_pool: list[str] = field(default_factory=list)
    idle_behaviors: list[str] = field(default_factory=list)

    # Relationships to other spirits
    relationship_ids: list[str] = field(default_factory=list)

    # Gifts and negotiation
    liked_offerings: list[str] = field(default_factory=list)
    disliked_offerings: list[str] = field(default_factory=list)
    negotiation_traits: list[str] = field(default_factory=list)  # What works in dialogue

    @property
    def effective_power(self) -> float:
        """Power modified by corruption and dormancy."""
        base = float(self.power)
        if self.is_corrupted:
            # Corruption boosts raw power but makes it unstable
            base *= (1.0 + self.corruption_level * 0.5)
        if self.is_dormant:
            base *= 0.2
        return base

    @property
    def corruption_resistance(self) -> float:
        """How well this spirit resists corruption. 0.0 = none, 1.0 = immune."""
        base = self.resilience / 100.0
        if self.element == SpiritElement.LIGHT:
            base += 0.15
        elif self.element == SpiritElement.VOID:
            base -= 0.1
        if self.rank in (SpiritRank.ANCIENT, SpiritRank.SOVEREIGN):
            base += 0.25
        if self.is_bonded:
            base += 0.1  # Bonds protect
        return max(0.0, min(1.0, base))

    def is_active_at(self, time_of_day: "TimeOfDay") -> bool:
        """Check if this spirit is active at a given time."""
        if not self.active_times:
            return True  # No preference means always active
        return time_of_day.value in self.active_times

    def apply_corruption(self, amount: float) -> dict:
        """
        Attempt to corrupt this spirit. Returns a dict describing what happened.

        Corruption is not just damage - it is the twisting of a spirit's
        fundamental nature. A playful spirit becomes cruel. A protective
        spirit becomes possessive. A wise spirit becomes paranoid.
        """
        resisted = amount * self.corruption_resistance
        actual = amount - resisted
        result: dict = {
            "amount_applied": actual,
            "amount_resisted": resisted,
            "events": [],
        }

        if actual <= 0:
            result["events"].append("fully_resisted")
            return result

        old_level = self.corruption_level
        self.corruption_level = min(1.0, self.corruption_level + actual)

        # Threshold events
        if old_level < 0.25 <= self.corruption_level:
            result["events"].append("corruption_visible")
            # Visual distortion begins

        if old_level < 0.5 <= self.corruption_level:
            self.is_corrupted = True
            result["events"].append("corruption_behavioral")
            # Disposition shifts
            if self.disposition == SpiritDisposition.BENEVOLENT:
                self.disposition = SpiritDisposition.WARY
            elif self.disposition == SpiritDisposition.CURIOUS:
                self.disposition = SpiritDisposition.TERRITORIAL

        if old_level < 0.75 <= self.corruption_level:
            result["events"].append("corruption_memory_loss")
            # Memories begin fragmenting
            if self.memories:
                lost = self.memories.pop(random.randint(0, len(self.memories) - 1))
                result["lost_memory"] = lost

        if old_level < 1.0 <= self.corruption_level:
            result["events"].append("corruption_complete")
            self.disposition = SpiritDisposition.HOSTILE
            self.true_name = None  # Forgotten entirely

        return result

    def purify(self, amount: float) -> dict:
        """
        Attempt to purify corruption. This is healing, not violence.
        Returns a dict of what was restored.
        """
        actual = min(self.corruption_level, amount)
        result: dict = {
            "amount_purified": actual,
            "events": [],
        }

        old_level = self.corruption_level
        self.corruption_level = max(0.0, self.corruption_level - actual)

        if old_level >= 0.5 > self.corruption_level:
            self.is_corrupted = False
            result["events"].append("corruption_cleared")

        if self.corruption_level == 0.0 and old_level > 0.0:
            result["events"].append("fully_purified")

        return result


@dataclass
class GreaterSpirit(Spirit):
    """
    Greater spirits: the kami of rivers buried under concrete, the spirit
    of mountains that skyscrapers stand upon, the nascent consciousness
    of Tokyo itself.

    These beings operate on a different scale. Their moods shape the
    spirit weather. Their conflicts reshape territories. Their attention
    is both blessing and catastrophe.
    """
    domain: str = ""                   # What this kami governs
    worshippers: int = 0               # Active human worshippers / awareness
    shrine_ids: list[str] = field(default_factory=list)
    subordinate_spirit_ids: list[str] = field(default_factory=list)
    domain_effects: dict[str, float] = field(default_factory=dict)

    # Greater spirits can influence weather
    preferred_weather: list[SpiritWeatherType] = field(default_factory=list)
    weather_influence: float = 0.0     # How strongly they push the weather

    # Awakening state - some greater spirits are sleeping
    awakening_progress: float = 0.0    # 0.0 = deep sleep, 1.0 = fully awake
    awakening_triggers: list[str] = field(default_factory=list)

    @property
    def influence_radius(self) -> int:
        """How many adjacent territories this spirit's presence affects."""
        base = 1
        if self.rank == SpiritRank.ANCIENT:
            base = 3
        elif self.rank == SpiritRank.SOVEREIGN:
            base = 10  # City-wide
        return int(base * (0.5 + self.awakening_progress * 0.5))

    def awaken_step(self, trigger: str, amount: float) -> dict:
        """
        Progress the awakening of a greater spirit. These are world events.
        """
        result: dict = {"events": [], "old_progress": self.awakening_progress}

        if trigger in self.awakening_triggers:
            amount *= 1.5  # Correct trigger is more effective

        old = self.awakening_progress
        self.awakening_progress = min(1.0, self.awakening_progress + amount)
        result["new_progress"] = self.awakening_progress

        thresholds = [
            (0.25, "stirring"),       # The spirit stirs in its sleep
            (0.5, "dreaming"),        # Its dreams leak into the material world
            (0.75, "half_awake"),     # It can be spoken to, partially
            (1.0, "fully_awake"),     # A kami walks in Tokyo
        ]
        for threshold, event_name in thresholds:
            if old < threshold <= self.awakening_progress:
                result["events"].append(event_name)

        return result


@dataclass
class SpiritLocationOverlay:
    """
    The spirit world version of a material location. This is the
    'transformation' layer - how a place changes when seen with
    spirit vision or entered in spirit form.

    The transformation is not random. It is the TRUTH of a place,
    expressed without the material world's constraints.
    """
    location_id: str
    material_name: str
    spirit_name: str                   # The name in the spirit world

    # The transformation
    visual_description: str = ""       # What the player sees
    sound_description: str = ""        # What the player hears
    feeling_description: str = ""      # What the player feels
    transformation_logic: str = ""     # WHY it looks this way (design note)

    # Emotional resonance
    dominant_emotion: str = ""         # The emotion that shaped this place
    emotion_intensity: float = 0.5
    emotion_sources: list[str] = field(default_factory=list)

    # Interaction points
    spirit_anchors: list[str] = field(default_factory=list)     # Where spirits gather
    crossing_points: list[str] = field(default_factory=list)    # Where worlds thin
    memory_echoes: list[str] = field(default_factory=list)      # Recorded moments

    # Dynamic properties
    stability: float = 1.0            # How stable the overlay is (corruption reduces)
    permeation_modifier: float = 0.0  # Local effect on permeation
    active_spirits: list[str] = field(default_factory=list)     # Spirit IDs present

    def get_visual_at_permeation(self, permeation: float) -> str:
        """
        The overlay becomes more visible as permeation rises.
        At low permeation, only glimpses. At high, full transformation.
        """
        if permeation < 0.2:
            return ""  # Nothing visible to most
        elif permeation < 0.4:
            return f"[Flickering] {self.visual_description[:80]}..."
        elif permeation < 0.6:
            return f"[Overlaid] {self.visual_description}"
        elif permeation < 0.8:
            return f"[Dominant] {self.visual_description} {self.feeling_description}"
        else:
            return (
                f"[Merged] {self.visual_description} "
                f"{self.sound_description} {self.feeling_description}"
            )


# ---------------------------------------------------------------------------
# Spirit Ecology - The Living System
# ---------------------------------------------------------------------------

@dataclass
class SpiritEcology:
    """
    The ecology of the spirit world. Spirits don't just exist in isolation -
    they form ecosystems. Predator and prey, symbiont and host, elder and
    apprentice. The health of the ecology determines the health of the
    spirit world itself.

    When MIRAIKAN extracts spirit energy, it doesn't just hurt individual
    spirits. It collapses food webs, breaks territorial agreements that
    have held for centuries, and forces spirits into behaviors that further
    damage the ecosystem.
    """
    spirits: dict[str, Spirit] = field(default_factory=dict)
    greater_spirits: dict[str, GreaterSpirit] = field(default_factory=dict)
    territories: dict[str, SpiritTerritory] = field(default_factory=dict)
    relationships: dict[str, SpiritRelationship] = field(default_factory=dict)
    overlays: dict[str, SpiritLocationOverlay] = field(default_factory=dict)
    weather: SpiritWeather = field(default_factory=SpiritWeather)

    # Ecosystem health metrics
    total_spirit_population: int = 0
    ecosystem_health: float = 1.0      # 0.0 = collapsed, 1.0 = thriving
    biodiversity_index: float = 1.0    # Variety of spirit types
    territorial_stability: float = 1.0  # How stable territory claims are

    # Event log
    pending_events: list[dict] = field(default_factory=list)

    def register_spirit(self, spirit: Spirit) -> None:
        """Add a spirit to the ecology."""
        if isinstance(spirit, GreaterSpirit):
            self.greater_spirits[spirit.spirit_id] = spirit
        self.spirits[spirit.spirit_id] = spirit
        self.total_spirit_population += 1
        self._update_biodiversity()

    def remove_spirit(self, spirit_id: str) -> Optional[Spirit]:
        """Remove a spirit. This is a significant event."""
        spirit = self.spirits.pop(spirit_id, None)
        self.greater_spirits.pop(spirit_id, None)
        if spirit:
            self.total_spirit_population -= 1
            self._update_biodiversity()

            # Remove from territories
            for territory in self.territories.values():
                if spirit_id in territory.resident_spirit_ids:
                    territory.resident_spirit_ids.remove(spirit_id)
                if territory.dominant_spirit_id == spirit_id:
                    territory.dominant_spirit_id = None
                    territory.status = TerritoryStatus.UNCLAIMED

            self.pending_events.append({
                "type": "spirit_removed",
                "spirit_id": spirit_id,
                "spirit_name": spirit.name,
            })

        return spirit

    def register_territory(self, territory: SpiritTerritory) -> None:
        """Add a territory to the ecology."""
        self.territories[territory.territory_id] = territory

    def register_overlay(self, overlay: SpiritLocationOverlay) -> None:
        """Register a spirit world location overlay."""
        self.overlays[overlay.location_id] = overlay

    def add_relationship(self, relationship: SpiritRelationship) -> None:
        """
        Register a relationship between two spirits. Updates both spirits'
        relationship lists.
        """
        rel_id = f"{relationship.spirit_a_id}_{relationship.spirit_b_id}"
        self.relationships[rel_id] = relationship

        spirit_a = self.spirits.get(relationship.spirit_a_id)
        spirit_b = self.spirits.get(relationship.spirit_b_id)
        if spirit_a and rel_id not in spirit_a.relationship_ids:
            spirit_a.relationship_ids.append(rel_id)
        if spirit_b and rel_id not in spirit_b.relationship_ids:
            spirit_b.relationship_ids.append(rel_id)

    def get_spirits_in_territory(self, territory_id: str) -> list[Spirit]:
        """Get all spirits currently in a territory."""
        territory = self.territories.get(territory_id)
        if not territory:
            return []
        return [
            self.spirits[sid]
            for sid in territory.resident_spirit_ids
            if sid in self.spirits
        ]

    def get_relationships_for(self, spirit_id: str) -> list[SpiritRelationship]:
        """Get all relationships involving a specific spirit."""
        return [
            rel for rel in self.relationships.values()
            if rel.spirit_a_id == spirit_id or rel.spirit_b_id == spirit_id
        ]

    def get_active_spirits(self, time_of_day: "TimeOfDay",
                           weather: SpiritWeatherType) -> list[Spirit]:
        """Get spirits that are active given current conditions."""
        active: list[Spirit] = []
        for spirit in self.spirits.values():
            if spirit.is_dormant or spirit.is_sealed:
                continue
            if not spirit.is_active_at(time_of_day):
                continue
            active.append(spirit)
        return active

    def update(self, delta: float, clock: "WorldClock",
               global_permeation: float, global_corruption: float) -> list[dict]:
        """
        Tick the entire ecology forward. This is where emergent behavior lives.
        """
        events: list[dict] = []

        # Update weather
        expired_weather = self.weather.update(delta)
        if expired_weather is not None:
            forecast = self.weather.generate_forecast(
                clock, global_permeation, global_corruption
            )
            if forecast:
                duration = random.randint(30, 120)
                intensity = 0.3 + random.random() * 0.5
                self.weather.transition_to(forecast[0], intensity, duration)
                events.append({
                    "type": "weather_changed",
                    "new_weather": forecast[0].value,
                    "intensity": intensity,
                })

        # Territorial dynamics
        for territory in self.territories.values():
            if territory.is_contested:
                events.extend(self._resolve_territorial_conflict(territory, delta))

            # Corruption spread
            if territory.corruption_level > 0.6:
                events.extend(
                    self._spread_corruption_from(territory, delta)
                )

        # Spirit wandering
        for spirit in self.spirits.values():
            if spirit.wanders and not spirit.is_dormant and spirit.wander_range:
                if random.random() < 0.02 * delta:  # Small chance each tick
                    new_territory = random.choice(spirit.wander_range)
                    old_territory = spirit.current_territory_id
                    self._move_spirit(spirit, new_territory)
                    if old_territory != new_territory:
                        events.append({
                            "type": "spirit_wandered",
                            "spirit_id": spirit.spirit_id,
                            "from": old_territory,
                            "to": new_territory,
                        })

        # Ecosystem health recalculation
        self._update_ecosystem_health(global_corruption)

        # Greater spirit influence
        for gs in self.greater_spirits.values():
            if gs.awakening_progress > 0.25 and not gs.is_dormant:
                events.extend(self._apply_greater_spirit_influence(gs, delta))

        # Collect pending events from subsystem updates
        events.extend(self.pending_events)
        self.pending_events.clear()

        return events

    def _resolve_territorial_conflict(self, territory: SpiritTerritory,
                                      delta: float) -> list[dict]:
        """Resolve ongoing territorial disputes between spirits."""
        events: list[dict] = []
        if not territory.contesting_spirit_ids or not territory.dominant_spirit_id:
            return events

        dominant = self.spirits.get(territory.dominant_spirit_id)
        if not dominant:
            return events

        for challenger_id in list(territory.contesting_spirit_ids):
            challenger = self.spirits.get(challenger_id)
            if not challenger:
                territory.contesting_spirit_ids.remove(challenger_id)
                continue

            # Power comparison with randomness
            dominant_strength = dominant.effective_power + random.gauss(0, 5)
            challenger_strength = challenger.effective_power + random.gauss(0, 5)

            if challenger_strength > dominant_strength * 1.2:
                # Challenger wins
                territory.dominant_spirit_id = challenger_id
                territory.contesting_spirit_ids.remove(challenger_id)
                territory.contesting_spirit_ids.append(dominant.spirit_id)
                territory.dominant_element = challenger.element
                events.append({
                    "type": "territory_seized",
                    "territory_id": territory.territory_id,
                    "new_dominant": challenger_id,
                    "old_dominant": dominant.spirit_id,
                })
                break
            elif dominant_strength > challenger_strength * 1.5:
                # Challenger driven off
                territory.contesting_spirit_ids.remove(challenger_id)
                events.append({
                    "type": "challenger_repelled",
                    "territory_id": territory.territory_id,
                    "repelled": challenger_id,
                })

        if not territory.contesting_spirit_ids:
            territory.status = TerritoryStatus.CLAIMED
            events.append({
                "type": "territory_conflict_resolved",
                "territory_id": territory.territory_id,
            })

        return events

    def _spread_corruption_from(self, source: SpiritTerritory,
                                delta: float) -> list[dict]:
        """Corruption seeps from heavily corrupted territories to neighbors."""
        events: list[dict] = []
        spread_amount = source.corruption_level * 0.01 * delta

        # Find adjacent territories (simplified: same district prefix)
        for territory in self.territories.values():
            if territory.territory_id == source.territory_id:
                continue
            if territory.material_district == source.material_district:
                actual = territory.apply_corruption(spread_amount * 0.5)
                if actual > 0.01:
                    events.append({
                        "type": "corruption_spread",
                        "from": source.territory_id,
                        "to": territory.territory_id,
                        "amount": actual,
                    })

        return events

    def _move_spirit(self, spirit: Spirit, new_territory_id: str) -> None:
        """Move a spirit from one territory to another."""
        if spirit.current_territory_id:
            old_territory = self.territories.get(spirit.current_territory_id)
            if old_territory and spirit.spirit_id in old_territory.resident_spirit_ids:
                old_territory.resident_spirit_ids.remove(spirit.spirit_id)

        spirit.current_territory_id = new_territory_id
        new_territory = self.territories.get(new_territory_id)
        if new_territory and spirit.spirit_id not in new_territory.resident_spirit_ids:
            new_territory.resident_spirit_ids.append(spirit.spirit_id)

    def _update_biodiversity(self) -> None:
        """Recalculate the biodiversity index based on element and rank variety."""
        if not self.spirits:
            self.biodiversity_index = 0.0
            return

        elements = set()
        ranks = set()
        for spirit in self.spirits.values():
            elements.add(spirit.element)
            ranks.add(spirit.rank)

        element_ratio = len(elements) / len(SpiritElement)
        rank_ratio = len(ranks) / len(SpiritRank)
        self.biodiversity_index = (element_ratio + rank_ratio) / 2.0

    def _update_ecosystem_health(self, global_corruption: float) -> None:
        """
        Ecosystem health is derived from biodiversity, territorial stability,
        spirit population trends, and corruption levels.
        """
        if not self.territories:
            return

        # Average territorial corruption
        avg_corruption = sum(
            t.corruption_level for t in self.territories.values()
        ) / len(self.territories)

        # Territorial stability
        contested = sum(
            1 for t in self.territories.values() if t.is_contested
        )
        total = len(self.territories)
        stability = 1.0 - (contested / max(total, 1))
        self.territorial_stability = stability

        # Composite health
        self.ecosystem_health = max(0.0, min(1.0, (
            self.biodiversity_index * 0.25
            + stability * 0.25
            + (1.0 - avg_corruption) * 0.3
            + (1.0 - global_corruption) * 0.2
        )))

    def _apply_greater_spirit_influence(self, spirit: GreaterSpirit,
                                        delta: float) -> list[dict]:
        """Greater spirits passively influence their surroundings."""
        events: list[dict] = []

        # Weather influence
        if spirit.preferred_weather and spirit.weather_influence > 0.3:
            if random.random() < spirit.weather_influence * 0.05 * delta:
                preferred = random.choice(spirit.preferred_weather)
                if self.weather.current != preferred:
                    events.append({
                        "type": "greater_spirit_weather_influence",
                        "spirit_id": spirit.spirit_id,
                        "weather": preferred.value,
                    })

        # Territory empowerment
        if spirit.home_territory_id:
            territory = self.territories.get(spirit.home_territory_id)
            if territory:
                boost = spirit.awakening_progress * 0.01 * delta
                territory.ambient_power = min(1.0, territory.ambient_power + boost)

                # Greater spirits resist corruption in their home
                if territory.corruption_level > 0 and spirit.awakening_progress > 0.5:
                    purify_amount = spirit.power / 1000.0 * delta
                    territory.purify(purify_amount)

        return events
