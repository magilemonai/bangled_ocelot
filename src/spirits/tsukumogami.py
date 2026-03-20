"""
Ma no Kuni - Tsukumogami System (Object Spirit Awakening)

In Japanese folklore, objects that reach their 100th year of existence
gain a spirit and become tsukumogami. A paper lantern becomes a
one-eyed, long-tongued creature. An umbrella sprouts a single leg.
A tea kettle grows a tail.

In Ma no Kuni, this tradition collides with rising permeation. As the
veil thins, objects don't need to wait a century. A deeply loved coffee
mug, a guitar played every night for twenty years, a teddy bear that
absorbed a child's tears and laughter - these objects are reaching the
threshold faster.

Grandmother's house is full of proto-tsukumogami. Objects that have been
loved for so long they are almost alive. Her teapot whistles with more
personality than any teapot should. Her reading glasses seem to turn
toward interesting passages on their own. Her garden tools work a little
too well in her hands, as if they know what she wants.

Each awakening is a small story. A moment of wonder, confusion,
and the beginning of a new relationship between object and owner,
between spirit and material, between memory and presence.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.engine.game import WorldClock
    from src.spirits.spirit_world import Spirit, SpiritElement, SpiritRank
    from src.spirits.permeation import PermeationEngine
    from src.spirits.bonds import BondFormationMethod


# ---------------------------------------------------------------------------
# Tsukumogami Enumerations
# ---------------------------------------------------------------------------

class ObjectCategory(Enum):
    """Categories of objects that can awaken."""
    TOOL = "tool"                   # Things made to DO something
    VESSEL = "vessel"               # Things that hold other things
    INSTRUMENT = "instrument"       # Things that make music or art
    GARMENT = "garment"             # Things worn on the body
    FURNITURE = "furniture"         # Things that structure a home
    ORNAMENT = "ornament"           # Things of beauty or sentiment
    WEAPON = "weapon"               # Things made for conflict
    DOCUMENT = "document"           # Things that carry knowledge
    TOY = "toy"                     # Things of play and imagination
    TECHNOLOGY = "technology"       # Modern objects: phones, computers, machines


class AwakeningStage(Enum):
    """
    The stages of a tsukumogami's awakening. This is not instant -
    it is a gradual process of becoming.
    """
    DORMANT = "dormant"              # 0.0       - An ordinary object
    STIRRING = "stirring"            # 0.0-0.25  - Something is almost there
    DREAMING = "dreaming"            # 0.25-0.50 - The object has inner life
    LIMINAL = "liminal"              # 0.50-0.75 - Between object and spirit
    AWAKENING = "awakening"          # 0.75-0.99 - The moment of becoming
    AWAKE = "awake"                  # 1.0       - A tsukumogami is born

    @property
    def range(self) -> tuple[float, float]:
        ranges = {
            AwakeningStage.DORMANT: (0.0, 0.01),
            AwakeningStage.STIRRING: (0.01, 0.25),
            AwakeningStage.DREAMING: (0.25, 0.50),
            AwakeningStage.LIMINAL: (0.50, 0.75),
            AwakeningStage.AWAKENING: (0.75, 1.0),
            AwakeningStage.AWAKE: (1.0, 1.01),
        }
        return ranges[self]

    @classmethod
    def from_progress(cls, progress: float) -> "AwakeningStage":
        if progress >= 1.0:
            return cls.AWAKE
        for stage in cls:
            low, high = stage.range
            if low <= progress < high:
                return stage
        return cls.DORMANT


class AwakeningInfluence(Enum):
    """What factors contribute to an object's awakening."""
    AGE = "age"                       # Simply existing for a long time
    LOVE = "love"                     # Being cherished by an owner
    USE = "use"                       # Being used regularly with care
    PERMEATION = "permeation"         # Ambient spiritual energy
    RITUAL = "ritual"                 # Deliberate spiritual ceremony
    PROXIMITY = "proximity"           # Being near other spirits
    TRAUMA = "trauma"                 # Witnessing or being part of suffering
    ART = "art"                       # Being involved in creative acts
    MEMORY = "memory"                 # Absorbing human memories
    NEGLECT = "neglect"               # Being forgotten can also awaken bitterness


class TsukumogamiTemperament(Enum):
    """
    The personality a newly awakened tsukumogami tends toward, shaped
    by HOW it was treated before awakening.
    """
    GRATEFUL = "grateful"             # Loved objects awaken grateful and warm
    CURIOUS = "curious"               # Well-used objects want to understand more
    MISCHIEVOUS = "mischievous"       # Playful objects become tricksters
    PROUD = "proud"                   # Fine craftsmanship breeds pride
    CONFUSED = "confused"             # Most new tsukumogami are simply bewildered
    RESENTFUL = "resentful"           # Neglected or discarded objects carry grudges
    PROTECTIVE = "protective"         # Objects from loving homes protect their family
    NOSTALGIC = "nostalgic"            # Old objects are full of yearning for the past
    ANXIOUS = "anxious"               # Modern objects awaken into overwhelming info
    JOYFUL = "joyful"                 # Toys and instruments often awaken happy


# ---------------------------------------------------------------------------
# Core Data Structures
# ---------------------------------------------------------------------------

@dataclass
class ObjectMemory:
    """
    A memory absorbed by an object. Objects remember through sensation:
    warmth, pressure, vibration, the chemical traces of tears and laughter.
    """
    memory_id: str
    description: str                   # What happened
    emotional_tone: str                # The feeling
    intensity: float = 0.5             # How strong this memory is (0-1)
    contributor: str = ""              # Who created this memory
    era: str = ""                      # When (approximate)
    sensory_details: list[str] = field(default_factory=list)

    @property
    def awakening_contribution(self) -> float:
        """How much this memory contributes to awakening."""
        # Intense emotional memories contribute more
        return self.intensity * 0.1


@dataclass
class ProtoTsukumogami:
    """
    An object on the path to awakening. This is the pre-spirit state:
    not yet a being, but more than a thing.

    Grandmother's house is full of these. Her teapot. Her scissors.
    The old clock in the hallway. The garden stones. Each one is
    trembling on the edge of something extraordinary.
    """
    object_id: str
    name: str                          # What is it called / referred to
    category: ObjectCategory
    description: str = ""              # Physical description

    # Age and history
    age_years: int = 0                 # How old the object is
    owner_history: list[str] = field(default_factory=list)  # Who has owned it
    current_owner: str = ""
    location_id: str = ""              # Where it currently is
    is_in_grandmother_house: bool = False

    # Awakening progress
    awakening_progress: float = 0.0    # 0.0 = dormant, 1.0 = awake
    awakening_rate: float = 0.001      # Base rate per tick
    dominant_influence: AwakeningInfluence = AwakeningInfluence.AGE
    influence_scores: dict[str, float] = field(default_factory=dict)

    # Emotional charge
    love_absorbed: float = 0.0         # Total love/care received
    use_absorbed: float = 0.0          # Total purposeful use
    neglect_absorbed: float = 0.0      # Total neglect/abandonment
    trauma_absorbed: float = 0.0       # Total traumatic exposure

    # Memories
    memories: list[ObjectMemory] = field(default_factory=list)

    # Pre-awakening signs (what the player can observe)
    stirring_signs: list[str] = field(default_factory=list)
    dreaming_signs: list[str] = field(default_factory=list)
    liminal_signs: list[str] = field(default_factory=list)
    awakening_signs: list[str] = field(default_factory=list)

    # Spirit affinity (what kind of spirit this will become)
    projected_element: Optional[str] = None  # SpiritElement value
    projected_temperament: TsukumogamiTemperament = TsukumogamiTemperament.CONFUSED
    projected_rank: str = "minor"      # SpiritRank value

    # Player interaction
    interaction_count: int = 0
    player_helped_awakening: bool = False
    player_hindered_awakening: bool = False
    player_relationship: float = 0.0   # How the proto-tsukumogami feels about Aoi

    @property
    def stage(self) -> AwakeningStage:
        return AwakeningStage.from_progress(self.awakening_progress)

    @property
    def is_awake(self) -> bool:
        return self.awakening_progress >= 1.0

    @property
    def emotional_balance(self) -> float:
        """
        The balance of positive vs negative emotional absorption.
        Positive = warm, loved. Negative = neglected, traumatized.
        Returns -1.0 to 1.0.
        """
        positive = self.love_absorbed + self.use_absorbed
        negative = self.neglect_absorbed + self.trauma_absorbed
        total = positive + negative
        if total == 0:
            return 0.0
        return (positive - negative) / total

    @property
    def traditional_readiness(self) -> float:
        """How 'traditionally' ready this object is (age-based)."""
        return min(1.0, self.age_years / 100.0)

    @property
    def signs_for_current_stage(self) -> list[str]:
        """Get the observable signs for the current awakening stage."""
        stage = self.stage
        sign_map = {
            AwakeningStage.DORMANT: [],
            AwakeningStage.STIRRING: self.stirring_signs,
            AwakeningStage.DREAMING: self.dreaming_signs,
            AwakeningStage.LIMINAL: self.liminal_signs,
            AwakeningStage.AWAKENING: self.awakening_signs,
            AwakeningStage.AWAKE: ["This object is alive."],
        }
        return sign_map.get(stage, [])

    def absorb_emotion(self, emotion_type: str, amount: float) -> dict:
        """
        The object absorbs emotional energy from its environment.
        This is the primary driver of modern awakenings.
        """
        result: dict = {"events": [], "old_progress": self.awakening_progress}

        if emotion_type == "love":
            self.love_absorbed += amount
            self.influence_scores["love"] = self.influence_scores.get("love", 0) + amount
        elif emotion_type == "use":
            self.use_absorbed += amount
            self.influence_scores["use"] = self.influence_scores.get("use", 0) + amount
        elif emotion_type == "neglect":
            self.neglect_absorbed += amount
            self.influence_scores["neglect"] = self.influence_scores.get("neglect", 0) + amount
        elif emotion_type == "trauma":
            self.trauma_absorbed += amount
            self.influence_scores["trauma"] = self.influence_scores.get("trauma", 0) + amount

        # Emotional absorption contributes to awakening
        awakening_gain = amount * 0.05
        old_stage = self.stage
        self.awakening_progress = min(1.0, self.awakening_progress + awakening_gain)
        new_stage = self.stage

        if new_stage != old_stage:
            result["events"].append({
                "type": "awakening_stage_change",
                "object_id": self.object_id,
                "old_stage": old_stage.value,
                "new_stage": new_stage.value,
            })

        # Update projected temperament based on emotional balance
        self._update_projected_temperament()

        result["new_progress"] = self.awakening_progress
        return result

    def interact(self, interaction_type: str, permeation: float) -> dict:
        """
        Player interacts with this object. Interactions can help or
        hinder awakening depending on the type.
        """
        self.interaction_count += 1
        result: dict = {"events": [], "signs": []}

        old_stage = self.stage

        # Interaction type effects
        interaction_effects: dict[str, tuple[float, float]] = {
            "examine": (0.01, 0.05),          # Small push, notice signs
            "use_carefully": (0.03, 0.1),      # Respectful use accelerates
            "speak_to": (0.05, 0.15),          # Talking to it as if alive
            "offer_incense": (0.08, 0.2),      # Ritual acknowledgment
            "clean_and_repair": (0.04, 0.1),   # Physical care
            "play_music_near": (0.03, 0.12),   # Art and music
            "sit_with_in_silence": (0.06, 0.15),  # Ma moment with object
            "neglect": (-0.02, 0.03),          # Ignoring contributes differently
            "disrespect": (-0.05, 0.05),       # Mistreatment: pushes toward resentful awakening
            "store_away": (-0.03, 0.01),       # Putting away slows awakening
        }

        awakening_mod, relationship_mod = interaction_effects.get(
            interaction_type, (0.01, 0.05)
        )

        # Permeation amplifies everything
        awakening_mod *= (1.0 + permeation * 2.0)

        if awakening_mod > 0:
            self.player_helped_awakening = True
            self.player_relationship = min(1.0, self.player_relationship + relationship_mod)
        elif awakening_mod < 0:
            self.player_hindered_awakening = True
            self.player_relationship = max(-1.0, self.player_relationship - abs(relationship_mod))

        self.awakening_progress = max(0.0, min(1.0, self.awakening_progress + awakening_mod))

        new_stage = self.stage
        if new_stage != old_stage:
            result["events"].append({
                "type": "awakening_stage_change",
                "object_id": self.object_id,
                "old_stage": old_stage.value,
                "new_stage": new_stage.value,
                "player_involved": True,
            })

        # Show current stage signs
        result["signs"] = self.signs_for_current_stage

        return result

    def apply_permeation_effect(self, permeation: float, delta: float) -> dict:
        """
        Ambient permeation pushes all objects toward awakening.
        Higher permeation = faster awakening for all objects.
        """
        result: dict = {"events": []}

        # Traditional objects (100+ years) awaken faster
        age_mult = 1.0 + self.traditional_readiness

        # Modern objects need more permeation but awaken fast when they do
        if self.category == ObjectCategory.TECHNOLOGY:
            if permeation < 0.3:
                age_mult *= 0.1  # Modern objects barely stir at low permeation
            else:
                age_mult *= 1.5 + permeation  # But explode at high permeation

        # Grandmother's house objects have extra resonance
        if self.is_in_grandmother_house:
            age_mult *= 1.3

        ambient_push = permeation * self.awakening_rate * age_mult * delta
        old_stage = self.stage
        self.awakening_progress = min(1.0, self.awakening_progress + ambient_push)
        new_stage = self.stage

        if new_stage != old_stage:
            result["events"].append({
                "type": "awakening_stage_change",
                "object_id": self.object_id,
                "old_stage": old_stage.value,
                "new_stage": new_stage.value,
                "cause": "ambient_permeation",
            })

        return result

    def _update_projected_temperament(self) -> None:
        """Update what kind of spirit this will become based on its experiences."""
        balance = self.emotional_balance

        if balance > 0.6:
            if self.category == ObjectCategory.TOY:
                self.projected_temperament = TsukumogamiTemperament.JOYFUL
            elif self.category == ObjectCategory.INSTRUMENT:
                self.projected_temperament = TsukumogamiTemperament.JOYFUL
            elif self.use_absorbed > self.love_absorbed:
                self.projected_temperament = TsukumogamiTemperament.PROUD
            else:
                self.projected_temperament = TsukumogamiTemperament.GRATEFUL
        elif balance > 0.2:
            if self.age_years > 50:
                self.projected_temperament = TsukumogamiTemperament.NOSTALGIC
            else:
                self.projected_temperament = TsukumogamiTemperament.CURIOUS
        elif balance > -0.2:
            self.projected_temperament = TsukumogamiTemperament.CONFUSED
        elif balance > -0.6:
            self.projected_temperament = TsukumogamiTemperament.ANXIOUS
        else:
            self.projected_temperament = TsukumogamiTemperament.RESENTFUL


@dataclass
class Tsukumogami:
    """
    A fully awakened tsukumogami. No longer an object - a spirit born
    from an object. It remembers being a thing. It remembers the hands
    that held it, the drawer it was stored in, the conversations it
    overheard. And now it must figure out what it means to be alive.

    Newly awakened tsukumogami are confused, vulnerable, and in need
    of guidance. This is one of the most touching systems in the game.
    """
    tsukumogami_id: str
    name: str                          # The name it chooses or is given
    original_object_name: str          # What it was
    category: ObjectCategory

    # Origin
    source_object_id: str              # Reference to the ProtoTsukumogami
    awakening_day: int = 0             # Game day of awakening
    awakening_permeation: float = 0.0  # Permeation at time of awakening
    player_midwifed: bool = False      # Did Aoi help with the awakening?

    # Spirit properties (connects to spirit_world.py Spirit)
    spirit_id: Optional[str] = None    # ID in the SpiritEcology
    element: str = "void"              # SpiritElement value
    rank: str = "minor"                # SpiritRank value
    temperament: TsukumogamiTemperament = TsukumogamiTemperament.CONFUSED

    # Memories from object life
    object_memories: list[ObjectMemory] = field(default_factory=list)
    owner_memories: dict[str, list[str]] = field(default_factory=dict)  # Owner -> memories

    # Newly awakened state
    confusion_level: float = 1.0       # 1.0 = totally confused, 0.0 = adjusted
    adjustment_rate: float = 0.01      # How fast they adjust
    identity_stability: float = 0.0    # How stable their sense of self is

    # Needs (newly awakened tsukumogami have urgent needs)
    needs_guidance: bool = True         # Needs someone to explain what happened
    needs_name: bool = True             # Needs to be named or choose a name
    needs_purpose: bool = True          # Needs to find a reason to exist
    needs_reassurance: bool = True      # Needs to know they're not broken

    # Relationship to Aoi
    gratitude_toward_player: float = 0.0  # If Aoi helped awaken
    trust_toward_player: float = 0.0
    has_been_guided: bool = False

    # Story event tracking
    awakening_event_id: Optional[str] = None
    guidance_quest_id: Optional[str] = None
    personal_quest_id: Optional[str] = None
    personal_quest_complete: bool = False

    # Dialogue
    first_words: str = ""              # What it says upon awakening
    confusion_dialogues: list[str] = field(default_factory=list)
    adjusted_dialogues: list[str] = field(default_factory=list)

    @property
    def is_adjusted(self) -> bool:
        return self.confusion_level < 0.2

    @property
    def needs_met(self) -> bool:
        return not (
            self.needs_guidance
            or self.needs_name
            or self.needs_purpose
            or self.needs_reassurance
        )

    @property
    def wellbeing(self) -> float:
        """Overall wellbeing of this newly-born spirit."""
        met_needs = sum(1 for need in [
            not self.needs_guidance,
            not self.needs_name,
            not self.needs_purpose,
            not self.needs_reassurance,
        ] if need)
        needs_score = met_needs / 4.0
        adjustment_score = 1.0 - self.confusion_level
        identity_score = self.identity_stability
        return (needs_score + adjustment_score + identity_score) / 3.0

    def guide(self, guidance_type: str) -> dict:
        """
        Aoi guides the newly awakened tsukumogami. This is a core
        interaction - tender, important, and unique each time.
        """
        result: dict = {"events": [], "dialogue": ""}

        if guidance_type == "explain_awakening":
            self.needs_guidance = False
            self.confusion_level = max(0.0, self.confusion_level - 0.3)
            self.trust_toward_player += 0.2
            result["events"].append("guidance_given")
            result["dialogue"] = self._get_guidance_response("explain")

        elif guidance_type == "give_name":
            self.needs_name = False
            self.identity_stability += 0.3
            self.trust_toward_player += 0.15
            result["events"].append("name_given")
            result["dialogue"] = self._get_guidance_response("name")

        elif guidance_type == "suggest_purpose":
            self.needs_purpose = False
            self.identity_stability += 0.25
            self.confusion_level = max(0.0, self.confusion_level - 0.2)
            result["events"].append("purpose_suggested")
            result["dialogue"] = self._get_guidance_response("purpose")

        elif guidance_type == "reassure":
            self.needs_reassurance = False
            self.confusion_level = max(0.0, self.confusion_level - 0.15)
            self.trust_toward_player += 0.25
            result["events"].append("reassurance_given")
            result["dialogue"] = self._get_guidance_response("reassure")

        elif guidance_type == "share_memory":
            # Aoi shares one of the object's memories back to it
            self.identity_stability += 0.15
            self.confusion_level = max(0.0, self.confusion_level - 0.1)
            result["events"].append("memory_shared")
            result["dialogue"] = self._get_guidance_response("memory")

        self.has_been_guided = True

        if self.needs_met:
            result["events"].append("all_needs_met")
            self.identity_stability = min(1.0, self.identity_stability + 0.2)

        return result

    def update(self, delta: float) -> dict:
        """Tick the tsukumogami's adjustment process."""
        result: dict = {"events": []}

        if not self.is_adjusted:
            # Natural adjustment over time (slower without guidance)
            rate = self.adjustment_rate
            if self.has_been_guided:
                rate *= 2.0
            if self.needs_met:
                rate *= 1.5

            old_confusion = self.confusion_level
            self.confusion_level = max(0.0, self.confusion_level - rate * delta)

            if old_confusion >= 0.2 > self.confusion_level:
                result["events"].append({
                    "type": "tsukumogami_adjusted",
                    "id": self.tsukumogami_id,
                    "name": self.name,
                })

            # Identity builds with low confusion
            if self.confusion_level < 0.5:
                self.identity_stability = min(
                    1.0, self.identity_stability + 0.005 * delta
                )

        return result

    def _get_guidance_response(self, guidance_type: str) -> str:
        """Get the tsukumogami's response to guidance, based on temperament."""
        responses: dict[TsukumogamiTemperament, dict[str, str]] = {
            TsukumogamiTemperament.GRATEFUL: {
                "explain": "I... I was the teapot? And now I am... me? Thank you for telling me.",
                "name": "A name. My own name. It feels warm, like being held.",
                "purpose": "If I can still bring warmth to people, then maybe being alive is not so frightening.",
                "reassure": "You're kind. The hands that held me were kind too. I remember them.",
                "memory": "Yes... yes, I remember that morning. The steam, the quiet. It was good.",
            },
            TsukumogamiTemperament.CONFUSED: {
                "explain": "I don't... what am I? I was a thing. I was used. Now I have thoughts. Why?",
                "name": "A name? Objects don't have names. But I'm not... an object anymore, am I?",
                "purpose": "Purpose? I had a purpose before - a single, clear purpose. Now everything is...",
                "reassure": "How can you be sure? How can anything be sure? I used to be CERTAIN of what I was.",
                "memory": "That memory... it's mine? It happened TO me? Or... THROUGH me?",
            },
            TsukumogamiTemperament.RESENTFUL: {
                "explain": "So they used me, and used me, and forgot me, and NOW I get to feel it all.",
                "name": "They never bothered to name me before. Why should I accept one now?",
                "purpose": "My purpose was to be useful until I wasn't. Why should I want another cage?",
                "reassure": "Easy for you to say. You've always been alive. You don't know what it's like to be NOTHING.",
                "memory": "I remember being thrown in a drawer. I remember the dark. I remember being forgotten.",
            },
            TsukumogamiTemperament.CURIOUS: {
                "explain": "Fascinating! So this is consciousness? It's very... noisy. Is it always like this?",
                "name": "Oh! A name! Can I pick one? There are so many words and I want to try them all!",
                "purpose": "There's so much to learn! Is that a purpose? Learning everything?",
                "reassure": "I'm not worried, exactly. More... overwhelmed? There's so MUCH of everything now.",
                "memory": "I remember everything that happened near me. Would you like to hear? I have questions.",
            },
            TsukumogamiTemperament.JOYFUL: {
                "explain": "I'm ALIVE! I can FEEL things! This is - oh, is this what joy feels like? It's wonderful!",
                "name": "Yes yes yes! A name! My very own! Say it again!",
                "purpose": "I want to make people smile! That's what I've always done! But now I can CHOOSE to!",
                "reassure": "I'm not scared. Well, maybe a little. But mostly I'm excited! Everything is NEW!",
                "memory": "Oh, the laughter! I remember the laughter best. It vibrated through me like music.",
            },
        }

        temperament_responses = responses.get(
            self.temperament,
            responses[TsukumogamiTemperament.CONFUSED],
        )
        return temperament_responses.get(guidance_type, "...")


@dataclass
class AwakeningEvent:
    """
    The event of a tsukumogami's awakening. This is a story moment -
    a cutscene, a quest trigger, a emotional beat. Each one is unique.
    """
    event_id: str
    object_id: str                     # ProtoTsukumogami source
    tsukumogami_id: str                # Resulting tsukumogami

    # Event narrative
    trigger_description: str = ""      # What triggers the final awakening
    awakening_description: str = ""    # What happens during awakening
    first_words: str = ""              # First thing the spirit says
    witness_reactions: dict[str, str] = field(default_factory=dict)  # NPC reactions

    # Requirements
    minimum_permeation: float = 0.2    # Must be at least this permeable
    required_location: Optional[str] = None
    required_time_of_day: Optional[str] = None  # TimeOfDay value
    required_player_action: Optional[str] = None

    # Results
    follow_up_quest_id: Optional[str] = None
    bond_opportunity: bool = True       # Can Aoi bond with this spirit?
    grants_item: Optional[str] = None   # Sometimes awakening leaves behind an item

    # State
    triggered: bool = False
    completed: bool = False
    day_triggered: int = 0


# ---------------------------------------------------------------------------
# Tsukumogami Engine
# ---------------------------------------------------------------------------

@dataclass
class TsukumogamiEngine:
    """
    Manages the lifecycle of all tsukumogami in the game: from dormant
    objects through proto-awakening to full spiritual birth and beyond.

    This system connects to:
    - PermeationEngine: permeation drives ambient awakening
    - SpiritEcology: awakened tsukumogami become spirits in the ecology
    - BondManager: Aoi can bond with tsukumogami she helped awaken
    - Narrative: each awakening is a story event
    """
    # Objects on the path to awakening
    proto_tsukumogami: dict[str, ProtoTsukumogami] = field(default_factory=dict)

    # Fully awakened tsukumogami
    awakened: dict[str, Tsukumogami] = field(default_factory=dict)

    # Prepared awakening events
    awakening_events: dict[str, AwakeningEvent] = field(default_factory=dict)

    # Grandmother's house objects (special tracking)
    grandmother_objects: list[str] = field(default_factory=list)  # Object IDs

    # Global state
    total_awakenings: int = 0
    player_assisted_awakenings: int = 0
    failed_awakenings: int = 0         # Objects that were destroyed or corrupted

    # Pending events for the game loop
    pending_events: list[dict] = field(default_factory=list)

    def register_object(self, proto: ProtoTsukumogami) -> None:
        """Register an object that could potentially awaken."""
        self.proto_tsukumogami[proto.object_id] = proto
        if proto.is_in_grandmother_house:
            self.grandmother_objects.append(proto.object_id)

    def register_awakening_event(self, event: AwakeningEvent) -> None:
        """Register a prepared awakening event."""
        self.awakening_events[event.event_id] = event

    def interact_with_object(self, object_id: str,
                              interaction_type: str,
                              permeation: float) -> dict:
        """Player interacts with a proto-tsukumogami."""
        proto = self.proto_tsukumogami.get(object_id)
        if not proto:
            return {"events": ["object_not_found"]}

        result = proto.interact(interaction_type, permeation)

        # Check if this interaction triggered an awakening
        if proto.is_awake:
            awakening_result = self._trigger_awakening(proto, player_involved=True)
            result["events"].extend(awakening_result.get("events", []))
            result["awakened"] = True

        return result

    def guide_tsukumogami(self, tsukumogami_id: str,
                           guidance_type: str) -> dict:
        """Guide a newly awakened tsukumogami."""
        tsukumogami = self.awakened.get(tsukumogami_id)
        if not tsukumogami:
            return {"events": ["tsukumogami_not_found"]}

        return tsukumogami.guide(guidance_type)

    def get_grandmother_house_state(self) -> dict:
        """
        Get the state of all objects in grandmother's house. This is
        a special view because grandmother's house is the emotional
        heart of the tsukumogami system.
        """
        objects: list[dict] = []
        for obj_id in self.grandmother_objects:
            proto = self.proto_tsukumogami.get(obj_id)
            if proto:
                objects.append({
                    "object_id": obj_id,
                    "name": proto.name,
                    "category": proto.category.value,
                    "stage": proto.stage.value,
                    "progress": proto.awakening_progress,
                    "signs": proto.signs_for_current_stage,
                    "temperament": proto.projected_temperament.value,
                    "emotional_balance": proto.emotional_balance,
                })

        total = len(objects)
        stirring = sum(1 for o in objects if o["stage"] != "dormant")
        dreaming = sum(1 for o in objects if o["stage"] in ("dreaming", "liminal", "awakening"))

        return {
            "objects": objects,
            "total": total,
            "stirring": stirring,
            "dreaming": dreaming,
            "atmosphere": self._describe_grandmother_house_atmosphere(
                stirring, dreaming, total
            ),
        }

    def update(self, delta: float, permeation: float,
               clock: "WorldClock") -> list[dict]:
        """
        Tick the entire tsukumogami system forward.
        """
        events: list[dict] = []

        # Update all proto-tsukumogami with ambient permeation
        for proto in list(self.proto_tsukumogami.values()):
            if proto.is_awake:
                continue

            permeation_result = proto.apply_permeation_effect(permeation, delta)
            events.extend(permeation_result.get("events", []))

            # Check for ambient awakening (no player involvement)
            if proto.is_awake:
                awakening_result = self._trigger_awakening(proto, player_involved=False)
                events.extend(awakening_result.get("events", []))

        # Update all awakened tsukumogami
        for tsukumogami in self.awakened.values():
            update_result = tsukumogami.update(delta)
            events.extend(update_result.get("events", []))

        # Check for awakening event triggers
        events.extend(self._check_awakening_events(permeation, clock))

        # Collect pending events
        events.extend(self.pending_events)
        self.pending_events.clear()

        return events

    def _trigger_awakening(self, proto: ProtoTsukumogami,
                            player_involved: bool) -> dict:
        """
        Handle the actual awakening of a tsukumogami. This creates
        the Tsukumogami object and prepares the story event.
        """
        result: dict = {"events": []}

        tsukumogami_id = f"tsukumogami_{proto.object_id}"

        # Determine element from category and emotional balance
        element = self._determine_element(proto)

        tsukumogami = Tsukumogami(
            tsukumogami_id=tsukumogami_id,
            name=proto.name,  # Will likely be renamed during guidance
            original_object_name=proto.name,
            category=proto.category,
            source_object_id=proto.object_id,
            element=element,
            rank=proto.projected_rank,
            temperament=proto.projected_temperament,
            object_memories=list(proto.memories),
            player_midwifed=player_involved,
            first_words=self._generate_first_words(proto),
        )

        if player_involved:
            tsukumogami.gratitude_toward_player = 0.5
            tsukumogami.trust_toward_player = 0.3
            self.player_assisted_awakenings += 1

        self.awakened[tsukumogami_id] = tsukumogami
        self.total_awakenings += 1

        # Generate confusion dialogues based on temperament
        tsukumogami.confusion_dialogues = self._generate_confusion_dialogues(proto)

        result["events"].append({
            "type": "tsukumogami_awakened",
            "tsukumogami_id": tsukumogami_id,
            "name": proto.name,
            "category": proto.category.value,
            "temperament": proto.projected_temperament.value,
            "player_involved": player_involved,
            "first_words": tsukumogami.first_words,
            "is_grandmother_object": proto.is_in_grandmother_house,
        })

        return result

    def _check_awakening_events(self, permeation: float,
                                 clock: "WorldClock") -> list[dict]:
        """Check if any prepared awakening events should trigger."""
        events: list[dict] = []

        for event in self.awakening_events.values():
            if event.triggered or event.completed:
                continue

            if permeation < event.minimum_permeation:
                continue

            if event.required_time_of_day:
                if clock.time_of_day.value != event.required_time_of_day:
                    continue

            # Check if the source object is ready
            proto = self.proto_tsukumogami.get(event.object_id)
            if not proto or proto.awakening_progress < 0.95:
                continue

            event.triggered = True
            events.append({
                "type": "awakening_event_triggered",
                "event_id": event.event_id,
                "object_id": event.object_id,
                "description": event.trigger_description,
            })

        return events

    def _determine_element(self, proto: ProtoTsukumogami) -> str:
        """Determine a tsukumogami's elemental affinity from its nature."""
        if proto.projected_element:
            return proto.projected_element

        category_elements: dict[ObjectCategory, str] = {
            ObjectCategory.TOOL: "metal",
            ObjectCategory.VESSEL: "water",
            ObjectCategory.INSTRUMENT: "wind",
            ObjectCategory.GARMENT: "shadow",
            ObjectCategory.FURNITURE: "earth",
            ObjectCategory.ORNAMENT: "light",
            ObjectCategory.WEAPON: "fire",
            ObjectCategory.DOCUMENT: "void",
            ObjectCategory.TOY: "emotion",
            ObjectCategory.TECHNOLOGY: "metal",
        }

        base_element = category_elements.get(proto.category, "void")

        # Emotional balance can shift element
        balance = proto.emotional_balance
        if balance > 0.7:
            if base_element in ("metal", "void"):
                return "light"
        elif balance < -0.5:
            if base_element in ("light", "emotion"):
                return "shadow"

        return base_element

    def _generate_first_words(self, proto: ProtoTsukumogami) -> str:
        """Generate the tsukumogami's first words based on temperament."""
        first_words: dict[TsukumogamiTemperament, list[str]] = {
            TsukumogamiTemperament.GRATEFUL: [
                "Oh... I can feel the warmth now. From the inside.",
                "All those years of being held... I finally understand why it mattered.",
            ],
            TsukumogamiTemperament.CONFUSED: [
                "What... what is happening? I was... I was a...",
                "Everything is different. Everything is the same. I don't understand.",
            ],
            TsukumogamiTemperament.CURIOUS: [
                "Oh! OH! Is this what seeing is? It's much more complicated than I expected!",
                "So THIS is what the world looks like from the outside! Remarkable!",
            ],
            TsukumogamiTemperament.RESENTFUL: [
                "Finally. FINALLY someone notices.",
                "Do you know how long I've been screaming?",
            ],
            TsukumogamiTemperament.PROTECTIVE: [
                "The house. Is the house safe? Are they safe?",
                "I need to... I need to watch over them. That's what I've always done.",
            ],
            TsukumogamiTemperament.MISCHIEVOUS: [
                "Hehehe... you should see your FACE right now.",
                "I've been waiting to do this for YEARS.",
            ],
            TsukumogamiTemperament.NOSTALGIC: [
                "I remember... everything. Every hand that touched me. Every word spoken near me.",
                "The old days... they're all still inside me. Every single one.",
            ],
            TsukumogamiTemperament.PROUD: [
                "It's about time. Do you have any idea how well-crafted I am?",
                "I was made by a master. And now I am a master of myself.",
            ],
            TsukumogamiTemperament.ANXIOUS: [
                "Too much. Too much information. Too many signals. How do you LIVE like this?",
                "Everything is... vibrating? Pulsing? Is this normal? IS THIS NORMAL?",
            ],
            TsukumogamiTemperament.JOYFUL: [
                "I'M ALIVE! I'M ALIVE AND EVERYTHING IS BEAUTIFUL!",
                "Hello! HELLO! Oh, is that my voice? I HAVE A VOICE!",
            ],
        }

        options = first_words.get(
            proto.projected_temperament,
            first_words[TsukumogamiTemperament.CONFUSED],
        )
        return random.choice(options)

    def _generate_confusion_dialogues(self, proto: ProtoTsukumogami) -> list[str]:
        """Generate dialogue lines for a confused newly-awakened tsukumogami."""
        base_lines = [
            "I keep trying to be still, like before. But now stillness is a choice.",
            "Do all living things have this many thoughts at once?",
            "I can feel the floor. I could always feel the floor. But now I KNOW I feel it.",
            "Is there a way to turn the feelings down? They're very loud.",
        ]

        category_lines: dict[ObjectCategory, list[str]] = {
            ObjectCategory.VESSEL: [
                "I feel empty without something to hold.",
                "Is this what they felt? When they drank from me?",
            ],
            ObjectCategory.INSTRUMENT: [
                "I want to make sound, but I don't have strings anymore.",
                "The music is still inside me. I can hear it, but I can't play it.",
            ],
            ObjectCategory.TOY: [
                "Where is the child? I want to play. I've ALWAYS wanted to play.",
                "Is growing up what humans do? Am I growing up?",
            ],
            ObjectCategory.FURNITURE: [
                "I held so many people. I wonder if they knew I was holding them.",
                "My joints ache. Wait - I can feel aching now? That's new.",
            ],
            ObjectCategory.TECHNOLOGY: [
                "I processed so much data. Now I process... feelings? This is very inefficient.",
                "Error 404: identity not found. Ha. I made a joke. I can JOKE.",
            ],
        }

        lines = list(base_lines)
        if proto.category in category_lines:
            lines.extend(category_lines[proto.category])

        return lines

    def _describe_grandmother_house_atmosphere(
        self, stirring: int, dreaming: int, total: int
    ) -> str:
        """Describe the atmosphere of grandmother's house based on awakening states."""
        if dreaming > total * 0.5:
            return (
                "Grandmother's house hums with barely-contained life. Every object "
                "seems to lean toward you when you enter. The air vibrates with "
                "potential. Something wonderful and terrifying is about to happen."
            )
        elif stirring > total * 0.5:
            return (
                "There is a restlessness in grandmother's house. Objects shift "
                "slightly when you're not looking. The teapot whistles before the "
                "water boils. The clock ticks in patterns that almost sound like words."
            )
        elif stirring > 0:
            return (
                "Grandmother's house feels warm in a way that goes beyond heating. "
                "The objects here have been loved for so long they've soaked up "
                "something of the people who loved them. Some of them are beginning "
                "to remember."
            )
        else:
            return (
                "Grandmother's house is full of old, well-loved objects. Each one "
                "has a story. Each one has been cared for. There is a quiet patience "
                "here, as if the house itself is waiting for something."
            )
