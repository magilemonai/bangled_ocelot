"""
Ma no Kuni - Abilities and Spirit Powers

Spirit Arts are the gifts of the in-between. They are not spells cast
by force of will, but harmonies struck between a human soul and the
spirit world. When Aoi channels a Spirit Art, she is not commanding -
she is collaborating. The spirit lends its nature; Aoi lends her intention.

The eight elements reflect not Western classical elements, but Japanese
concepts of how the world breathes:
    Fire (火)     - Passion, transformation, destruction, rebirth
    Water (水)    - Adaptation, persistence, memory, reflection
    Wind (風)     - Freedom, communication, change, breath
    Earth (土)    - Stability, patience, growth, foundation
    Light (光)    - Clarity, truth, hope, exposure
    Shadow (影)   - Concealment, depth, dreams, the subconscious
    Memory (記憶) - The past, nostalgia, identity, connection
    Silence (静寂) - Ma itself, the pause, emptiness, potential
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Callable


class Element(Enum):
    """The eight elemental affinities of the spirit world."""
    FIRE = "fire"         # 火 - hi
    WATER = "water"       # 水 - mizu
    WIND = "wind"         # 風 - kaze
    EARTH = "earth"       # 土 - tsuchi
    LIGHT = "light"       # 光 - hikari
    SHADOW = "shadow"     # 影 - kage
    MEMORY = "memory"     # 記憶 - kioku
    SILENCE = "silence"   # 静寂 - seijaku
    NEUTRAL = "neutral"   # 無 - mu


# Elemental interactions: key is strong against value
ELEMENTAL_STRENGTHS: dict[Element, Element] = {
    Element.FIRE: Element.WIND,       # Fire consumes the air
    Element.WATER: Element.FIRE,      # Water quenches flame
    Element.WIND: Element.EARTH,      # Wind erodes the mountain
    Element.EARTH: Element.WATER,     # Earth absorbs the flood
    Element.LIGHT: Element.SHADOW,    # Light banishes shadow
    Element.SHADOW: Element.MEMORY,   # Shadow obscures the past
    Element.MEMORY: Element.SILENCE,  # Memory fills the void
    Element.SILENCE: Element.LIGHT,   # Silence dims even brilliance
}

# Elemental harmonies: elements that amplify each other when combined
ELEMENTAL_HARMONIES: dict[tuple[Element, Element], str] = {
    (Element.FIRE, Element.MEMORY): "Burning Nostalgia",
    (Element.WATER, Element.SILENCE): "Still Waters",
    (Element.WIND, Element.LIGHT): "Dawn Breeze",
    (Element.EARTH, Element.SHADOW): "Buried Secrets",
    (Element.MEMORY, Element.LIGHT): "Vivid Recollection",
    (Element.SILENCE, Element.SHADOW): "The Deepest Ma",
    (Element.FIRE, Element.EARTH): "Forge Song",
    (Element.WATER, Element.WIND): "Monsoon",
}


class TargetType(Enum):
    """Who or what an ability affects."""
    SINGLE_ENEMY = auto()
    ALL_ENEMIES = auto()
    SINGLE_ALLY = auto()
    ALL_ALLIES = auto()
    SELF = auto()
    FIELD = auto()           # Changes the battlefield itself
    SPIRIT_ONLY = auto()     # Only affects spirit-type entities
    CORRUPTED_ONLY = auto()  # Only affects corrupted spirits


class AbilityCategory(Enum):
    """The nature of the ability."""
    ATTACK = auto()          # Deal damage
    HEALING = auto()         # Restore HP
    SUPPORT = auto()         # Buffs and positive effects
    DEBUFF = auto()          # Weaken enemies
    NEGOTIATION = auto()     # Diplomatic abilities
    OBSERVATION = auto()     # Reveal information
    PURIFICATION = auto()    # Cleanse corruption
    FIELD = auto()           # Alter battle conditions
    MA = auto()              # Manipulate the Ma Gauge


class StatusEffect(Enum):
    """Conditions that linger between turns."""
    # Negative
    BURNING = "burning"           # Fire DOT
    SOAKED = "soaked"             # Water - increased lightning/cold vuln
    WINDSWEPT = "windswept"       # Wind - reduced accuracy
    ROOTED = "rooted"             # Earth - cannot flee or swap
    BLINDED = "blinded"           # Light - reduced accuracy, reveals hidden
    SHADOWED = "shadowed"         # Shadow - hidden but reduced power
    NOSTALGIC = "nostalgic"       # Memory - distracted by past, skip turns
    SILENCED = "silenced"         # Silence - cannot use Spirit Arts
    CORRUPTED = "corrupted"       # Spiritual poison, DOT + stat drain
    CONFUSED = "confused"         # Random target selection
    FRIGHTENED = "frightened"     # May skip turn, reduced attack

    # Positive
    SHIELDED = "shielded"         # Damage reduction
    HASTE = "haste"               # Act sooner
    REGENERATING = "regenerating" # HP recovery over time
    FOCUSED = "focused"           # Increased critical rate
    SPIRIT_LINKED = "spirit_linked"  # Connected to a spirit ally
    MA_ATTUNED = "ma_attuned"     # Ma Gauge charges faster
    WARDED = "warded"             # Resist status effects
    INSPIRED = "inspired"         # Boosted Spirit Art power


@dataclass
class StatusInstance:
    """A specific status effect applied to a combatant."""
    effect: StatusEffect
    duration: int                  # Turns remaining, -1 for permanent
    potency: float = 1.0          # Strength multiplier
    source: Optional[str] = None  # Who or what applied it
    stacks: int = 1               # Some effects stack

    def tick(self) -> bool:
        """Advance one turn. Returns True if effect has expired."""
        if self.duration > 0:
            self.duration -= 1
        return self.duration == 0


@dataclass
class AbilityCost:
    """What it costs to use an ability."""
    sp: int = 0                    # Spirit Points
    hp: int = 0                    # Health sacrifice
    ma: float = 0.0               # Ma Gauge cost (can be negative = generates ma)
    items: dict[str, int] = field(default_factory=dict)  # Consumable components
    relationship: float = 0.0     # Cost to spirit bond strength
    cooldown: int = 0             # Turns before reuse


@dataclass
class AbilityEffect:
    """The mechanical effects of an ability."""
    damage: int = 0               # Base damage (negative = healing)
    element: Element = Element.NEUTRAL
    accuracy: float = 1.0         # Hit chance multiplier
    critical_rate: float = 0.05   # Base crit chance
    status_effects: list[tuple[StatusEffect, float, int]] = field(
        default_factory=list       # (effect, chance, duration)
    )
    ma_generation: float = 0.0    # Ma Gauge generated on use
    ma_bonus_multiplier: float = 1.0  # How much the Ma Gauge amplifies this
    stat_modifiers: dict[str, float] = field(default_factory=dict)
    bestiary_reveal: float = 0.0  # How much bestiary info this reveals
    negotiation_bonus: float = 0.0  # Bonus to negotiation attempts
    purification_power: float = 0.0  # Corruption cleansing strength


@dataclass
class Ability:
    """
    A single ability - attack, spirit art, or special action.

    Every ability in Ma no Kuni carries flavor. These are not just
    mechanics; they are expressions of the relationship between
    the human and spirit worlds.
    """
    id: str
    name: str
    name_jp: str                   # Japanese name
    description: str               # Evocative description
    category: AbilityCategory
    target: TargetType
    cost: AbilityCost
    effect: AbilityEffect
    source_spirit: Optional[str] = None  # Spirit that granted this ability
    requires_level: int = 1
    requires_bond: float = 0.0     # Minimum bond with source spirit
    lore_text: str = ""            # Extended lore, unlocked gradually
    learned: bool = False
    times_used: int = 0
    ma_timing_window: float = 0.5  # Seconds for perfect Ma timing
    animation_key: str = ""

    def can_use(self, user_sp: int, user_hp: int, user_ma: float,
                user_level: int, bond_level: float = 1.0) -> tuple[bool, str]:
        """Check if this ability can be used right now."""
        if not self.learned:
            return False, "You haven't learned this ability yet."
        if user_sp < self.cost.sp:
            return False, "Not enough Spirit Points."
        if user_hp <= self.cost.hp:
            return False, "Using this would cost your life."
        if user_ma < self.cost.ma:
            return False, "The Ma is not deep enough."
        if user_level < self.requires_level:
            return False, f"Requires level {self.requires_level}."
        if bond_level < self.requires_bond:
            return False, "Your bond with this spirit is not strong enough."
        return True, ""

    def calculate_ma_bonus(self, ma_gauge: float, timing_accuracy: float) -> float:
        """
        Calculate the power bonus from Ma Gauge and timing.

        The Ma Gauge rewards patience. A full gauge with perfect timing
        can more than double an ability's power. But a rushed ability
        with an empty gauge still works - just without the resonance.

        timing_accuracy: 0.0 (missed) to 1.0 (perfect)
        """
        # Base ma bonus from gauge level (0-100 gauge -> 1.0-1.5x)
        gauge_bonus = 1.0 + (ma_gauge / 100.0) * 0.5

        # Timing perfection bonus (0.0-1.0 accuracy -> 1.0-2.0x)
        timing_bonus = 1.0 + timing_accuracy

        # Combined, scaled by this ability's ma sensitivity
        total = gauge_bonus * timing_bonus * self.effect.ma_bonus_multiplier

        return total


# ---------------------------------------------------------------------------
# Default abilities available to all party members
# ---------------------------------------------------------------------------

BASIC_ATTACK = Ability(
    id="basic_attack",
    name="Strike",
    name_jp="打つ",
    description="A straightforward physical attack. Simple, honest, "
                "like the tap of a hammer on a bell.",
    category=AbilityCategory.ATTACK,
    target=TargetType.SINGLE_ENEMY,
    cost=AbilityCost(),
    effect=AbilityEffect(damage=10, accuracy=0.95, critical_rate=0.05),
    learned=True,
    ma_timing_window=0.3,
)

DEFEND = Ability(
    id="defend",
    name="Guard",
    name_jp="守る",
    description="Brace yourself against the coming blow. In the space "
                "between breaths, find your center.",
    category=AbilityCategory.SUPPORT,
    target=TargetType.SELF,
    cost=AbilityCost(),
    effect=AbilityEffect(
        ma_generation=5.0,
        status_effects=[(StatusEffect.SHIELDED, 1.0, 1)],
    ),
    learned=True,
    ma_timing_window=0.8,  # Longer window - defending is about patience
)

OBSERVE = Ability(
    id="observe",
    name="Observe",
    name_jp="観る",
    description="Study the spirit before you. Every being has a story written "
                "in its movements, its light, its silence. Read it.",
    category=AbilityCategory.OBSERVATION,
    target=TargetType.SINGLE_ENEMY,
    cost=AbilityCost(sp=3),
    effect=AbilityEffect(
        bestiary_reveal=0.25,
        ma_generation=10.0,
        negotiation_bonus=0.1,
    ),
    learned=True,
    ma_timing_window=1.0,  # Observation rewards the most patience
)

NEGOTIATE = Ability(
    id="negotiate",
    name="Speak",
    name_jp="語る",
    description="Open your mouth, but more importantly, open your heart. "
                "Spirits do not hear words - they hear intentions.",
    category=AbilityCategory.NEGOTIATION,
    target=TargetType.SINGLE_ENEMY,
    cost=AbilityCost(sp=5, ma=10.0),
    effect=AbilityEffect(
        negotiation_bonus=0.3,
        ma_generation=5.0,
    ),
    learned=True,
    ma_timing_window=0.7,
)

WAIT = Ability(
    id="wait",
    name="Wait",
    name_jp="待つ",
    description="Do nothing. But in Ma no Kuni, nothing is never truly nothing. "
                "The pause between notes is what makes the music.",
    category=AbilityCategory.MA,
    target=TargetType.SELF,
    cost=AbilityCost(),
    effect=AbilityEffect(ma_generation=15.0),
    learned=True,
    ma_timing_window=2.0,  # The longest window - waiting IS the skill
)

FLEE = Ability(
    id="flee",
    name="Flee",
    name_jp="逃げる",
    description="Sometimes wisdom is knowing when to leave. "
                "Not every encounter needs a resolution today.",
    category=AbilityCategory.SUPPORT,
    target=TargetType.SELF,
    cost=AbilityCost(),
    effect=AbilityEffect(),
    learned=True,
    ma_timing_window=0.2,
)


# ---------------------------------------------------------------------------
# Spirit Arts - abilities gained from befriended spirits
# ---------------------------------------------------------------------------

def create_spirit_arts() -> dict[str, Ability]:
    """
    Build the catalog of Spirit Arts.

    Each Spirit Art reflects the nature of the spirit that grants it.
    They are not tools to be wielded but relationships to be honored.
    """
    arts: dict[str, Ability] = {}

    # --- Fire Arts (火) ---

    arts["lantern_light"] = Ability(
        id="lantern_light",
        name="Lantern Light",
        name_jp="提灯の灯",
        description="The chochin-obake shares its gentle flame. A warm glow "
                    "that reveals what hides in darkness - not with the "
                    "harshness of a spotlight, but the kindness of a candle.",
        category=AbilityCategory.ATTACK,
        target=TargetType.SINGLE_ENEMY,
        cost=AbilityCost(sp=8),
        effect=AbilityEffect(
            damage=25,
            element=Element.FIRE,
            accuracy=0.9,
            status_effects=[(StatusEffect.BURNING, 0.3, 3)],
            bestiary_reveal=0.1,
        ),
        source_spirit="chochin_obake",
        requires_bond=0.2,
        lore_text="The chochin-obake was a paper lantern once, lit every evening "
                  "by a grandmother who told stories by its light. When she passed, "
                  "the lantern kept burning - fueled now by memory instead of oil.",
        ma_timing_window=0.5,
    )

    arts["vending_blaze"] = Ability(
        id="vending_blaze",
        name="Scalding Dispense",
        name_jp="灼熱販売",
        description="The jidohanbaiki-no-kami launches a superheated can that "
                    "explodes on impact. The vending machine hums with satisfaction.",
        category=AbilityCategory.ATTACK,
        target=TargetType.SINGLE_ENEMY,
        cost=AbilityCost(sp=12),
        effect=AbilityEffect(
            damage=35,
            element=Element.FIRE,
            accuracy=0.85,
            critical_rate=0.15,
            status_effects=[(StatusEffect.BURNING, 0.5, 2)],
        ),
        source_spirit="jidohanbaiki_no_kami",
        requires_bond=0.3,
        ma_timing_window=0.3,
    )

    # --- Water Arts (水) ---

    arts["river_remembrance"] = Ability(
        id="river_remembrance",
        name="River's Remembrance",
        name_jp="川の記憶",
        description="The kappa channels the Sumida River's ancient memory. "
                    "Water that has flowed through Tokyo for centuries carries "
                    "the weight of every reflection it has held.",
        category=AbilityCategory.ATTACK,
        target=TargetType.SINGLE_ENEMY,
        cost=AbilityCost(sp=15),
        effect=AbilityEffect(
            damage=30,
            element=Element.WATER,
            accuracy=0.95,
            status_effects=[(StatusEffect.SOAKED, 0.6, 3)],
            ma_generation=5.0,
        ),
        source_spirit="kappa",
        requires_bond=0.4,
        lore_text="The Sumida River remembers when it was clean. The kappa "
                  "remembers too. This art is equal parts attack and lament.",
        ma_timing_window=0.6,
    )

    arts["rain_of_healing"] = Ability(
        id="rain_of_healing",
        name="Compassionate Rain",
        name_jp="慈雨",
        description="A gentle rain falls on the party, carrying the kappa's "
                    "blessing. Each drop is a small kindness.",
        category=AbilityCategory.HEALING,
        target=TargetType.ALL_ALLIES,
        cost=AbilityCost(sp=20, ma=15.0),
        effect=AbilityEffect(
            damage=-25,  # Negative damage = healing
            element=Element.WATER,
        ),
        source_spirit="kappa",
        requires_bond=0.6,
        ma_timing_window=0.8,
    )

    # --- Wind Arts (風) ---

    arts["echo_voice"] = Ability(
        id="echo_voice",
        name="Echo Voice",
        name_jp="木霊の声",
        description="The kodama lends its voice - an echo that carries truth. "
                    "In the rustling of Inokashira Park's canopy, words spoken "
                    "centuries ago still resonate.",
        category=AbilityCategory.ATTACK,
        target=TargetType.ALL_ENEMIES,
        cost=AbilityCost(sp=18),
        effect=AbilityEffect(
            damage=20,
            element=Element.WIND,
            accuracy=0.9,
            status_effects=[(StatusEffect.CONFUSED, 0.25, 2)],
            ma_generation=8.0,
        ),
        source_spirit="kodama",
        requires_bond=0.3,
        lore_text="The kodama does not create new sounds. It returns what was "
                  "given. Shout anger, and anger returns. Whisper kindness, "
                  "and kindness echoes forever.",
        ma_timing_window=0.7,
    )

    arts["telephone_whisper"] = Ability(
        id="telephone_whisper",
        name="Forgotten Call",
        name_jp="忘れた電話",
        description="The denwa-no-rei dials a number that no longer exists. "
                    "The voice that answers speaks a truth the target forgot - "
                    "or tried to forget.",
        category=AbilityCategory.DEBUFF,
        target=TargetType.SINGLE_ENEMY,
        cost=AbilityCost(sp=14),
        effect=AbilityEffect(
            damage=15,
            element=Element.WIND,
            status_effects=[
                (StatusEffect.NOSTALGIC, 0.4, 2),
                (StatusEffect.CONFUSED, 0.3, 1),
            ],
            bestiary_reveal=0.15,
        ),
        source_spirit="denwa_no_rei",
        requires_bond=0.3,
        ma_timing_window=0.5,
    )

    # --- Earth Arts (土) ---

    arts["tanuki_transformation"] = Ability(
        id="tanuki_transformation",
        name="Tanuki's Trick",
        name_jp="狸の変化",
        description="The tanuki's legendary shapeshifting, shared with an ally. "
                    "For a few precious moments, you are someone else entirely - "
                    "and the spirits cannot find you.",
        category=AbilityCategory.SUPPORT,
        target=TargetType.SINGLE_ALLY,
        cost=AbilityCost(sp=16, ma=10.0),
        effect=AbilityEffect(
            element=Element.EARTH,
            status_effects=[(StatusEffect.SHADOWED, 1.0, 3)],
            stat_modifiers={"evasion": 1.5, "spirit_power": 0.8},
        ),
        source_spirit="tanuki",
        requires_bond=0.5,
        lore_text="The tanuki of Shimokitazawa are the last great tricksters. "
                  "They don't shapeshift to deceive - they do it because "
                  "being one thing forever is unbearably boring.",
        ma_timing_window=0.4,
    )

    # --- Light Arts (光) ---

    arts["dawn_blessing"] = Ability(
        id="dawn_blessing",
        name="First Light",
        name_jp="初光",
        description="The light of Tokyo's first dawn, before the city woke, "
                    "before the concrete covered the earth. A light that "
                    "remembers when all of this was forest.",
        category=AbilityCategory.HEALING,
        target=TargetType.ALL_ALLIES,
        cost=AbilityCost(sp=25, ma=20.0),
        effect=AbilityEffect(
            damage=-40,
            element=Element.LIGHT,
            status_effects=[
                (StatusEffect.REGENERATING, 0.8, 3),
                (StatusEffect.INSPIRED, 0.5, 2),
            ],
        ),
        requires_level=5,
        lore_text="There is a light that predates the city, the roads, even "
                  "the villages. It is the light of the first morning. "
                  "It does not judge. It simply begins.",
        ma_timing_window=1.0,
    )

    arts["spirit_sight"] = Ability(
        id="spirit_sight",
        name="Spirit Sight",
        name_jp="霊視",
        description="See the world as the spirits see it. The material dissolves; "
                    "only essence remains. Every being's true nature laid bare.",
        category=AbilityCategory.OBSERVATION,
        target=TargetType.ALL_ENEMIES,
        cost=AbilityCost(sp=10, ma=15.0),
        effect=AbilityEffect(
            element=Element.LIGHT,
            bestiary_reveal=0.5,
            negotiation_bonus=0.2,
            ma_generation=5.0,
        ),
        requires_level=3,
        learned=True,
        ma_timing_window=1.2,
    )

    # --- Shadow Arts (影) ---

    arts["dream_walk"] = Ability(
        id="dream_walk",
        name="Dream Walk",
        name_jp="夢歩き",
        description="Step into the shadow between waking and dreaming. "
                    "For a moment, you exist in both places and neither. "
                    "Attacks pass through you like whispers through fog.",
        category=AbilityCategory.SUPPORT,
        target=TargetType.SELF,
        cost=AbilityCost(sp=12, ma=10.0),
        effect=AbilityEffect(
            element=Element.SHADOW,
            status_effects=[
                (StatusEffect.SHADOWED, 1.0, 2),
                (StatusEffect.MA_ATTUNED, 1.0, 3),
            ],
            ma_generation=10.0,
        ),
        requires_level=4,
        ma_timing_window=0.9,
    )

    # --- Memory Arts (記憶) ---

    arts["nostalgia_wave"] = Ability(
        id="nostalgia_wave",
        name="Wave of Remembrance",
        name_jp="追憶の波",
        description="The natsukashii spirit opens the floodgates of memory. "
                    "Every combatant is swept into a tide of what was - "
                    "the old neighborhood, the school friend's face, the taste "
                    "of grandmother's cooking. It hurts. It heals.",
        category=AbilityCategory.FIELD,
        target=TargetType.FIELD,
        cost=AbilityCost(sp=22, ma=25.0),
        effect=AbilityEffect(
            damage=20,
            element=Element.MEMORY,
            status_effects=[(StatusEffect.NOSTALGIC, 0.7, 3)],
            ma_generation=15.0,
            negotiation_bonus=0.3,
        ),
        source_spirit="natsukashii",
        requires_bond=0.4,
        lore_text="Natsukashii is not a single memory. It is the ache of all "
                  "memories at once - the recognition that every precious moment "
                  "is already gone. This is its gift and its wound.",
        ma_timing_window=0.8,
    )

    arts["wabi_mend"] = Ability(
        id="wabi_mend",
        name="Kintsugi",
        name_jp="金繕い",
        description="The wabi spirit repairs what is broken with gold. "
                    "Not to hide the damage, but to honor it. "
                    "The mended thing is more beautiful than the whole.",
        category=AbilityCategory.HEALING,
        target=TargetType.SINGLE_ALLY,
        cost=AbilityCost(sp=18, ma=15.0),
        effect=AbilityEffect(
            damage=-50,
            element=Element.MEMORY,
            status_effects=[
                (StatusEffect.WARDED, 0.8, 3),
                (StatusEffect.INSPIRED, 0.6, 2),
            ],
        ),
        source_spirit="wabi",
        requires_bond=0.5,
        lore_text="Wabi sees the crack in the teacup and weeps with joy. "
                  "'Here,' it says, 'here is where the light gets in.'",
        ma_timing_window=1.0,
    )

    # --- Silence Arts (静寂) ---

    arts["deep_stillness"] = Ability(
        id="deep_stillness",
        name="Profound Silence",
        name_jp="深い静寂",
        description="The silence between heartbeats. The pause between breaths. "
                    "The space between words where meaning truly lives. "
                    "In this silence, all spirit arts are muted - "
                    "including your own.",
        category=AbilityCategory.FIELD,
        target=TargetType.FIELD,
        cost=AbilityCost(sp=20, ma=30.0),
        effect=AbilityEffect(
            element=Element.SILENCE,
            status_effects=[(StatusEffect.SILENCED, 0.9, 2)],
            ma_generation=25.0,
        ),
        requires_level=6,
        lore_text="The deepest ma is not empty. It is so full of potential "
                  "that it cannot yet choose a shape. In that fullness, "
                  "nothing else can act.",
        ma_timing_window=2.5,  # The silence art has the longest timing window
    )

    arts["yamanote_loop"] = Ability(
        id="yamanote_loop",
        name="Eternal Circuit",
        name_jp="永遠の環状",
        description="The Yamanote Line spirit shares its endless journey. "
                    "Round and round, station to station, the same route "
                    "forever - and yet each loop is different. Each passenger "
                    "carries a new story. Time resets. The party is refreshed.",
        category=AbilityCategory.HEALING,
        target=TargetType.ALL_ALLIES,
        cost=AbilityCost(sp=30, ma=20.0),
        effect=AbilityEffect(
            damage=-35,
            element=Element.SILENCE,
            status_effects=[
                (StatusEffect.REGENERATING, 1.0, 3),
                (StatusEffect.MA_ATTUNED, 0.8, 2),
            ],
            ma_generation=10.0,
        ),
        source_spirit="densha_no_tamashii",
        requires_bond=0.7,
        lore_text="The Yamanote Line has circled Tokyo 3.2 million times since "
                  "1925. It has carried billions of souls. It remembers every "
                  "one of them. That memory, that continuity, is its power.",
        ma_timing_window=1.5,
    )

    # --- Purification Arts ---

    arts["gentle_cleansing"] = Ability(
        id="gentle_cleansing",
        name="Gentle Cleansing",
        name_jp="優しい浄化",
        description="Not a violent exorcism but a patient washing-away. "
                    "Like rain on old stone. Like time on grief. "
                    "Corruption is not destroyed - it is forgiven.",
        category=AbilityCategory.PURIFICATION,
        target=TargetType.SINGLE_ENEMY,
        cost=AbilityCost(sp=15, ma=20.0),
        effect=AbilityEffect(
            damage=10,
            element=Element.LIGHT,
            purification_power=0.3,
            status_effects=[(StatusEffect.CORRUPTED, 0.0, 0)],  # Removes corruption
            negotiation_bonus=0.2,
        ),
        requires_level=3,
        lore_text="Grandmother taught Aoi this: you do not fight the darkness. "
                  "You sit with it. You listen to its pain. And slowly, slowly, "
                  "it remembers that it was once light.",
        ma_timing_window=1.5,
    )

    arts["purifying_flame"] = Ability(
        id="purifying_flame",
        name="Sacred Fire",
        name_jp="浄火",
        description="A cleansing flame drawn from the oldest shrines. "
                    "It burns away corruption without harming the spirit beneath. "
                    "Painful but necessary - like cauterizing a wound.",
        category=AbilityCategory.PURIFICATION,
        target=TargetType.SINGLE_ENEMY,
        cost=AbilityCost(sp=25, ma=15.0),
        effect=AbilityEffect(
            damage=30,
            element=Element.FIRE,
            purification_power=0.5,
            status_effects=[(StatusEffect.BURNING, 0.4, 2)],
        ),
        requires_level=5,
        ma_timing_window=0.6,
    )

    # --- Negotiation Arts ---

    arts["shared_silence"] = Ability(
        id="shared_silence",
        name="Shared Silence",
        name_jp="共有の沈黙",
        description="Sit with the spirit in silence. Not the uncomfortable silence "
                    "of strangers, but the warm silence of those who understand "
                    "each other beyond words. In the ma between you, "
                    "trust begins to grow.",
        category=AbilityCategory.NEGOTIATION,
        target=TargetType.SINGLE_ENEMY,
        cost=AbilityCost(sp=8, ma=20.0),
        effect=AbilityEffect(
            element=Element.SILENCE,
            negotiation_bonus=0.5,
            ma_generation=10.0,
            bestiary_reveal=0.2,
        ),
        requires_level=2,
        lore_text="In Japanese, there is no word for 'awkward silence.' "
                  "Silence between people who respect each other is natural. "
                  "It is a gift. Aoi learned this from her grandmother.",
        ma_timing_window=2.0,
    )

    arts["lullaby_of_belonging"] = Ability(
        id="lullaby_of_belonging",
        name="Lullaby of Belonging",
        name_jp="帰属の子守唄",
        description="The biwa-bokuboku plays a melody from the spirit's past - "
                    "a song it heard when it first awoke, when the world was new "
                    "and full of wonder. Homesickness is a powerful negotiator.",
        category=AbilityCategory.NEGOTIATION,
        target=TargetType.SINGLE_ENEMY,
        cost=AbilityCost(sp=16, ma=15.0),
        effect=AbilityEffect(
            element=Element.MEMORY,
            negotiation_bonus=0.6,
            ma_generation=12.0,
            status_effects=[(StatusEffect.NOSTALGIC, 0.5, 2)],
        ),
        source_spirit="biwa_bokuboku",
        requires_bond=0.4,
        lore_text="Every spirit remembers its first moment of consciousness. "
                  "For tsukumogami, that moment was being loved - being used, "
                  "being needed. The biwa remembers gentle hands on its strings.",
        ma_timing_window=1.0,
    )

    return arts


# Pre-built catalog
SPIRIT_ARTS: dict[str, Ability] = create_spirit_arts()

# Default abilities available to all party members
DEFAULT_ABILITIES: dict[str, Ability] = {
    "basic_attack": BASIC_ATTACK,
    "defend": DEFEND,
    "observe": OBSERVE,
    "negotiate": NEGOTIATE,
    "wait": WAIT,
    "flee": FLEE,
}
