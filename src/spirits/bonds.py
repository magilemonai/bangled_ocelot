"""
Ma no Kuni - Spirit Bonding and Companionship

A bond between human and spirit is not ownership. It is not a contract.
It is a relationship - as complex, fragile, and rewarding as any other.

Aoi does not capture spirits. She meets them. She listens to them.
She earns their trust, or doesn't. She learns what they need, what they
fear, what makes them laugh. And if both sides choose it, a bond forms.

Bonded spirits are companions, not tools. They have opinions about where
Aoi goes and what she does. They bicker with each other. They remember
kindness and slights. They grow and change alongside her.

The bond system is the emotional core of the game.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.spirits.spirit_world import Spirit, SpiritElement, SpiritDisposition


# ---------------------------------------------------------------------------
# Bond Levels
# ---------------------------------------------------------------------------

class BondLevel(Enum):
    """
    The stages of a bond between Aoi and a spirit.
    Each level unlocks new interactions and deepens the relationship.
    """
    AWARENESS = "awareness"         # They know each other exists
    RECOGNITION = "recognition"     # They acknowledge each other
    TRUST = "trust"                 # Mutual trust established
    PARTNERSHIP = "partnership"     # Active cooperation
    UNITY = "unity"                 # Deep spiritual connection

    @property
    def threshold(self) -> float:
        """Affinity points needed to reach this level."""
        thresholds = {
            BondLevel.AWARENESS: 0.0,
            BondLevel.RECOGNITION: 20.0,
            BondLevel.TRUST: 50.0,
            BondLevel.PARTNERSHIP: 85.0,
            BondLevel.UNITY: 120.0,
        }
        return thresholds[self]

    @property
    def max_affinity(self) -> float:
        """Maximum affinity at this level before needing a breakthrough event."""
        maxes = {
            BondLevel.AWARENESS: 25.0,
            BondLevel.RECOGNITION: 55.0,
            BondLevel.TRUST: 90.0,
            BondLevel.PARTNERSHIP: 125.0,
            BondLevel.UNITY: 200.0,
        }
        return maxes[self]

    @property
    def next_level(self) -> Optional["BondLevel"]:
        levels = list(BondLevel)
        idx = levels.index(self)
        if idx < len(levels) - 1:
            return levels[idx + 1]
        return None


class BondFormationMethod(Enum):
    """How the bond was initially formed. Affects the bond's character."""
    COMBAT_NEGOTIATION = "combat_negotiation"   # Met through battle, chose peace
    QUEST_COMPLETION = "quest_completion"        # Helped the spirit with something
    GIFT_OFFERING = "gift_offering"             # Won over with meaningful gifts
    MA_MOMENT = "ma_moment"                     # Connected through silence and stillness
    RESCUE = "rescue"                           # Saved from corruption or danger
    MUTUAL_CURIOSITY = "mutual_curiosity"       # Both drawn to each other naturally
    ANCESTRAL = "ancestral"                     # Inherited bond from grandmother


class SpiritPersonalityType(Enum):
    """
    The personality archetypes that shape how a bonded spirit interacts.
    Each spirit has a primary and optional secondary personality.
    """
    PLAYFUL = "playful"            # Loves games, pranks, lighthearted
    SOLEMN = "solemn"              # Serious, thoughtful, speaks in riddles
    PROTECTIVE = "protective"      # Fiercely guards those they care about
    SCHOLARLY = "scholarly"        # Fascinated by knowledge, loves to teach
    MISCHIEVOUS = "mischievous"   # Trouble-maker, but well-meaning (usually)
    MELANCHOLIC = "melancholic"    # Touched by sadness, deeply empathetic
    FIERCE = "fierce"              # Bold, confrontational, honest to a fault
    GENTLE = "gentle"              # Soft-spoken, patient, nurturing
    UNPREDICTABLE = "unpredictable"  # Changes mood rapidly, keeps you guessing
    ANCIENT = "ancient"            # Speaks from vast experience, occasionally cryptic


# ---------------------------------------------------------------------------
# Bond Interaction Types
# ---------------------------------------------------------------------------

class BondInteraction(Enum):
    """Ways a bonded spirit can assist or interact."""
    COMBAT_ASSIST = "combat_assist"       # Fight alongside Aoi
    PUZZLE_HINT = "puzzle_hint"           # Help solve puzzles
    PASSIVE_BUFF = "passive_buff"         # Ongoing stat enhancement
    TEACH_ABILITY = "teach_ability"       # Teach Aoi a new skill
    SHARE_MEMORY = "share_memory"         # Share a piece of their past
    CRAFT_ASSIST = "craft_assist"         # Help with crafting
    WORLD_COMMENT = "world_comment"       # Comment on surroundings
    SPIRIT_TRANSLATE = "spirit_translate" # Translate for other spirits
    TERRITORY_GUIDE = "territory_guide"   # Navigate spirit territories
    EMOTIONAL_SUPPORT = "emotional_support"  # Help during difficult moments
    DETECT_CORRUPTION = "detect_corruption"  # Sense corruption nearby
    OPEN_PATH = "open_path"               # Open spirit world passages


# ---------------------------------------------------------------------------
# Core Bond Data
# ---------------------------------------------------------------------------

@dataclass
class BondMemory:
    """
    A shared memory between Aoi and a bonded spirit. Memories are the
    substance of bonds - they define what the relationship IS.
    """
    memory_id: str
    description: str
    emotion: str                        # The dominant feeling
    affinity_gained: float = 0.0        # How much this memory strengthened the bond
    day_formed: int = 0                 # Game day when this happened
    location: str = ""                  # Where it happened
    is_milestone: bool = False          # Is this a bond-level breakthrough memory?
    tags: list[str] = field(default_factory=list)


@dataclass
class SpiritPreferences:
    """
    What a bonded spirit likes and dislikes. Attending to these
    deepens the bond. Ignoring them strains it.
    """
    # Gifts
    loved_gifts: list[str] = field(default_factory=list)
    liked_gifts: list[str] = field(default_factory=list)
    disliked_gifts: list[str] = field(default_factory=list)
    hated_gifts: list[str] = field(default_factory=list)

    # Activities
    enjoyed_activities: list[str] = field(default_factory=list)
    disliked_activities: list[str] = field(default_factory=list)

    # Environments
    preferred_locations: list[str] = field(default_factory=list)
    avoided_locations: list[str] = field(default_factory=list)
    preferred_weather: list[str] = field(default_factory=list)

    # Social
    spirit_friends: list[str] = field(default_factory=list)  # Spirit IDs they like
    spirit_rivals: list[str] = field(default_factory=list)    # Spirit IDs they dislike

    # Conversational
    favorite_topics: list[str] = field(default_factory=list)
    sensitive_topics: list[str] = field(default_factory=list)

    def evaluate_gift(self, item_id: str) -> tuple[float, str]:
        """Evaluate a gift. Returns (affinity_change, reaction_key)."""
        if item_id in self.loved_gifts:
            return (5.0, "gift_loved")
        elif item_id in self.liked_gifts:
            return (2.0, "gift_liked")
        elif item_id in self.disliked_gifts:
            return (-2.0, "gift_disliked")
        elif item_id in self.hated_gifts:
            return (-5.0, "gift_hated")
        return (0.5, "gift_neutral")


@dataclass
class CompanionDialogue:
    """
    A pool of context-sensitive dialogue lines for a bonded spirit.
    Spirits comment on the world, react to events, and converse with
    Aoi based on their personality and current bond level.
    """
    # Context -> list of (line, minimum_bond_level) tuples
    idle_lines: list[tuple[str, BondLevel]] = field(default_factory=list)
    combat_start_lines: list[tuple[str, BondLevel]] = field(default_factory=list)
    combat_victory_lines: list[tuple[str, BondLevel]] = field(default_factory=list)
    combat_defeat_lines: list[tuple[str, BondLevel]] = field(default_factory=list)
    exploration_lines: list[tuple[str, BondLevel]] = field(default_factory=list)
    corruption_lines: list[tuple[str, BondLevel]] = field(default_factory=list)
    other_spirit_lines: dict[str, list[tuple[str, BondLevel]]] = field(
        default_factory=dict
    )

    # Location-specific comments
    location_lines: dict[str, list[tuple[str, BondLevel]]] = field(
        default_factory=dict
    )

    # Mood-based lines
    happy_lines: list[tuple[str, BondLevel]] = field(default_factory=list)
    sad_lines: list[tuple[str, BondLevel]] = field(default_factory=list)
    angry_lines: list[tuple[str, BondLevel]] = field(default_factory=list)
    contemplative_lines: list[tuple[str, BondLevel]] = field(default_factory=list)

    def get_line(self, context: str, bond_level: BondLevel,
                 location: str = "", other_spirit_id: str = "") -> Optional[str]:
        """
        Get an appropriate dialogue line for the current context.
        Only returns lines the current bond level qualifies for.
        """
        bond_levels = list(BondLevel)
        current_idx = bond_levels.index(bond_level)

        pool: list[tuple[str, BondLevel]] = []

        # Select the right pool
        context_map = {
            "idle": self.idle_lines,
            "combat_start": self.combat_start_lines,
            "combat_victory": self.combat_victory_lines,
            "combat_defeat": self.combat_defeat_lines,
            "exploration": self.exploration_lines,
            "corruption": self.corruption_lines,
            "happy": self.happy_lines,
            "sad": self.sad_lines,
            "angry": self.angry_lines,
            "contemplative": self.contemplative_lines,
        }

        if context in context_map:
            pool = context_map[context]
        elif context == "location" and location in self.location_lines:
            pool = self.location_lines[location]
        elif context == "other_spirit" and other_spirit_id in self.other_spirit_lines:
            pool = self.other_spirit_lines[other_spirit_id]

        # Filter by bond level
        eligible = [
            line for line, min_level in pool
            if bond_levels.index(min_level) <= current_idx
        ]

        if eligible:
            return random.choice(eligible)
        return None


@dataclass
class SpiritMood:
    """
    A bonded spirit's current emotional state. Moods affect dialogue,
    combat performance, and willingness to cooperate.
    """
    happiness: float = 0.5          # 0.0 = miserable, 1.0 = overjoyed
    energy: float = 0.5             # 0.0 = exhausted, 1.0 = energetic
    trust_feeling: float = 0.5      # 0.0 = suspicious, 1.0 = complete trust
    comfort: float = 0.5            # 0.0 = very uncomfortable, 1.0 = at home

    # Temporary mood effects
    mood_effects: list[dict] = field(default_factory=list)

    @property
    def overall(self) -> float:
        """Composite mood score."""
        return (
            self.happiness * 0.3
            + self.energy * 0.2
            + self.trust_feeling * 0.3
            + self.comfort * 0.2
        )

    @property
    def mood_label(self) -> str:
        """Get a human-readable mood description."""
        score = self.overall
        if score >= 0.8:
            return "radiant"
        elif score >= 0.6:
            return "content"
        elif score >= 0.4:
            return "neutral"
        elif score >= 0.2:
            return "uneasy"
        else:
            return "distressed"

    def apply_effect(self, effect: dict) -> None:
        """
        Apply a mood effect. Effect dict should contain:
        - target: which mood axis (happiness, energy, trust_feeling, comfort)
        - amount: how much to change
        - duration: how many ticks it lasts (-1 = permanent shift)
        """
        target = effect.get("target", "happiness")
        amount = effect.get("amount", 0.0)
        duration = effect.get("duration", -1)

        current = getattr(self, target, 0.5)
        setattr(self, target, max(0.0, min(1.0, current + amount)))

        if duration > 0:
            self.mood_effects.append({
                "target": target,
                "amount": -amount,  # Will be reversed when expired
                "remaining": duration,
            })

    def update(self, delta: float) -> list[str]:
        """
        Tick mood effects. Returns list of expired effect descriptions.
        Moods naturally drift toward 0.5 over time (regression to mean).
        """
        expired: list[str] = []

        # Process temporary effects
        still_active: list[dict] = []
        for effect in self.mood_effects:
            effect["remaining"] -= 1
            if effect["remaining"] <= 0:
                # Reverse the effect
                target = effect["target"]
                current = getattr(self, target, 0.5)
                setattr(self, target, max(0.0, min(1.0, current + effect["amount"])))
                expired.append(f"mood_effect_expired_{target}")
            else:
                still_active.append(effect)
        self.mood_effects = still_active

        # Natural regression toward baseline
        regression_rate = 0.002 * delta
        for attr in ("happiness", "energy", "trust_feeling", "comfort"):
            current = getattr(self, attr)
            if current > 0.5:
                setattr(self, attr, max(0.5, current - regression_rate))
            elif current < 0.5:
                setattr(self, attr, min(0.5, current + regression_rate))

        return expired


# ---------------------------------------------------------------------------
# The Bond
# ---------------------------------------------------------------------------

@dataclass
class SpiritBond:
    """
    A bond between Aoi and a spirit. This is the core relationship object.

    A bond is not a number. It is the accumulation of shared experiences,
    gifts given and received, battles fought together, silences shared.
    The affinity score is just the shadow of something deeper.
    """
    bond_id: str
    spirit_id: str
    spirit_name: str

    # Bond state
    level: BondLevel = BondLevel.AWARENESS
    affinity: float = 0.0               # Raw affinity points
    formation_method: BondFormationMethod = BondFormationMethod.MUTUAL_CURIOSITY
    day_formed: int = 0                  # Game day bond was initiated

    # Spirit personality in this bond
    primary_personality: SpiritPersonalityType = SpiritPersonalityType.GENTLE
    secondary_personality: Optional[SpiritPersonalityType] = None
    preferences: SpiritPreferences = field(default_factory=SpiritPreferences)
    mood: SpiritMood = field(default_factory=SpiritMood)
    dialogue: CompanionDialogue = field(default_factory=CompanionDialogue)

    # Interaction capabilities (unlocked by bond level)
    available_interactions: list[BondInteraction] = field(default_factory=list)

    # Memories
    memories: list[BondMemory] = field(default_factory=list)
    total_interactions: int = 0

    # Combat stats when assisting
    combat_power_bonus: float = 0.0
    combat_defense_bonus: float = 0.0
    combat_special_ability: Optional[str] = None

    # Passive buffs
    passive_buffs: dict[str, float] = field(default_factory=dict)

    # Abilities taught
    taught_abilities: list[str] = field(default_factory=list)

    # Active state
    is_active: bool = False              # Currently summoned / accompanying
    is_available: bool = True            # Can be summoned
    cooldown_remaining: int = 0          # Turns until available after dismissal
    summoning_cost: float = 5.0          # Ma cost to summon

    # Relationship dynamics
    trust_events: int = 0                # Times Aoi kept a promise
    betrayal_events: int = 0             # Times Aoi broke trust
    gifts_given: int = 0
    battles_together: int = 0
    silences_shared: int = 0             # Ma moments together
    secrets_shared: int = 0              # Memories exchanged

    # Breakthrough tracking
    breakthrough_available: bool = False  # Ready to advance to next level
    breakthrough_quest_id: Optional[str] = None
    breakthrough_conditions: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.available_interactions:
            self._update_available_interactions()

    @property
    def affinity_to_next_level(self) -> float:
        """How much more affinity is needed to unlock breakthrough."""
        next_lvl = self.level.next_level
        if next_lvl is None:
            return 0.0
        return max(0.0, next_lvl.threshold - self.affinity)

    @property
    def affinity_percentage(self) -> float:
        """Progress toward next level as a percentage."""
        next_lvl = self.level.next_level
        if next_lvl is None:
            return 1.0
        current_threshold = self.level.threshold
        next_threshold = next_lvl.threshold
        progress = self.affinity - current_threshold
        total = next_threshold - current_threshold
        if total <= 0:
            return 1.0
        return min(1.0, progress / total)

    @property
    def relationship_quality(self) -> str:
        """A qualitative description of the bond's health."""
        mood_score = self.mood.overall
        affinity_pct = self.affinity_percentage

        if mood_score >= 0.7 and affinity_pct >= 0.7:
            return "flourishing"
        elif mood_score >= 0.5 and affinity_pct >= 0.5:
            return "healthy"
        elif mood_score >= 0.3:
            return "strained"
        else:
            return "troubled"

    def add_affinity(self, amount: float, source: str = "") -> dict:
        """
        Add affinity to the bond. Returns a dict of events triggered.
        Mood affects affinity gain - a happy spirit bonds faster.
        """
        result: dict = {"events": [], "amount_gained": 0.0}

        # Mood multiplier
        mood_mult = 0.7 + self.mood.overall * 0.6  # 0.7 to 1.3
        actual = amount * mood_mult
        result["amount_gained"] = actual

        old_affinity = self.affinity
        self.affinity = min(self.level.max_affinity, self.affinity + actual)
        self.total_interactions += 1

        # Check if we've capped at current level
        next_lvl = self.level.next_level
        if next_lvl and self.affinity >= next_lvl.threshold:
            if not self.breakthrough_available:
                self.breakthrough_available = True
                result["events"].append("breakthrough_available")
                result["next_level"] = next_lvl.value

        # Small mood boost from positive interaction
        if amount > 0:
            self.mood.apply_effect({
                "target": "happiness",
                "amount": min(0.05, amount * 0.01),
                "duration": -1,
            })
            self.mood.apply_effect({
                "target": "trust_feeling",
                "amount": min(0.03, amount * 0.005),
                "duration": -1,
            })

        return result

    def reduce_affinity(self, amount: float, source: str = "") -> dict:
        """
        Reduce affinity. This hurts. Returns events triggered.
        """
        result: dict = {"events": [], "amount_lost": 0.0}

        actual = amount
        self.affinity = max(self.level.threshold, self.affinity - actual)
        result["amount_lost"] = actual

        # Mood hit
        self.mood.apply_effect({
            "target": "happiness",
            "amount": -min(0.15, amount * 0.03),
            "duration": -1,
        })
        self.mood.apply_effect({
            "target": "trust_feeling",
            "amount": -min(0.1, amount * 0.02),
            "duration": -1,
        })

        if self.affinity <= self.level.threshold and self.level != BondLevel.AWARENESS:
            result["events"].append("bond_strained")

        return result

    def give_gift(self, item_id: str) -> dict:
        """
        Give a gift to the bonded spirit. The spirit's reaction depends
        on their preferences and current mood.
        """
        self.gifts_given += 1
        affinity_change, reaction = self.preferences.evaluate_gift(item_id)

        result: dict = {"reaction": reaction, "events": []}

        if affinity_change > 0:
            add_result = self.add_affinity(affinity_change, f"gift_{item_id}")
            result["events"].extend(add_result["events"])
            result["affinity_gained"] = add_result["amount_gained"]
        elif affinity_change < 0:
            red_result = self.reduce_affinity(abs(affinity_change), f"gift_{item_id}")
            result["events"].extend(red_result["events"])
            result["affinity_lost"] = red_result["amount_lost"]

        return result

    def share_silence(self, ma_amount: float) -> dict:
        """
        Share a moment of ma with the spirit. This is the deepest form
        of connection - doing nothing together.
        """
        self.silences_shared += 1
        result: dict = {"events": []}

        # Ma moments are especially effective for certain personalities
        personality_mult = 1.0
        if self.primary_personality in (
            SpiritPersonalityType.SOLEMN,
            SpiritPersonalityType.GENTLE,
            SpiritPersonalityType.MELANCHOLIC,
            SpiritPersonalityType.ANCIENT,
        ):
            personality_mult = 1.5
        elif self.primary_personality in (
            SpiritPersonalityType.PLAYFUL,
            SpiritPersonalityType.FIERCE,
        ):
            personality_mult = 0.7  # These spirits get restless in silence

        affinity_gain = ma_amount * 0.1 * personality_mult
        add_result = self.add_affinity(affinity_gain, "shared_silence")
        result["events"].extend(add_result["events"])
        result["affinity_gained"] = add_result["amount_gained"]

        # Comfort boost from shared silence
        self.mood.apply_effect({
            "target": "comfort",
            "amount": 0.05 * personality_mult,
            "duration": -1,
        })

        return result

    def complete_battle_together(self, won: bool) -> dict:
        """Record a battle fought together. Shared combat builds bonds."""
        self.battles_together += 1
        result: dict = {"events": []}

        if won:
            gain = 3.0
            if self.primary_personality in (
                SpiritPersonalityType.FIERCE,
                SpiritPersonalityType.PROTECTIVE,
            ):
                gain *= 1.3
            add_result = self.add_affinity(gain, "battle_victory")
            result["events"].extend(add_result["events"])
            self.mood.apply_effect({
                "target": "energy", "amount": -0.05, "duration": 10,
            })
            self.mood.apply_effect({
                "target": "happiness", "amount": 0.1, "duration": -1,
            })
        else:
            # Losing together can strain or strengthen depending on personality
            if self.primary_personality == SpiritPersonalityType.PROTECTIVE:
                self.mood.apply_effect({
                    "target": "happiness", "amount": -0.15, "duration": -1,
                })
                result["events"].append("spirit_feels_failed_to_protect")
            else:
                # Shared adversity builds trust
                add_result = self.add_affinity(1.0, "battle_defeat_together")
                result["events"].extend(add_result["events"])

        return result

    def attempt_breakthrough(self, quest_complete: bool = False,
                              special_item: Optional[str] = None) -> dict:
        """
        Attempt to advance to the next bond level. This requires both
        sufficient affinity AND a specific breakthrough event.
        """
        result: dict = {"success": False, "events": []}

        if not self.breakthrough_available:
            result["events"].append("not_ready")
            return result

        next_lvl = self.level.next_level
        if next_lvl is None:
            result["events"].append("max_level")
            return result

        # Check conditions
        conditions_met = True
        if self.breakthrough_quest_id and not quest_complete:
            conditions_met = False
            result["events"].append("quest_incomplete")

        if not conditions_met:
            return result

        # Breakthrough succeeds
        old_level = self.level
        self.level = next_lvl
        self.breakthrough_available = False
        self.breakthrough_quest_id = None
        self.breakthrough_conditions.clear()
        self._update_available_interactions()

        result["success"] = True
        result["old_level"] = old_level.value
        result["new_level"] = next_lvl.value
        result["events"].append("bond_level_up")

        # Create a milestone memory
        memory = BondMemory(
            memory_id=f"breakthrough_{self.bond_id}_{next_lvl.value}",
            description=f"The bond deepened to {next_lvl.value}",
            emotion="connection",
            affinity_gained=0.0,
            is_milestone=True,
            tags=["breakthrough", next_lvl.value],
        )
        self.memories.append(memory)

        # Major mood boost
        self.mood.apply_effect({
            "target": "happiness", "amount": 0.3, "duration": -1,
        })
        self.mood.apply_effect({
            "target": "trust_feeling", "amount": 0.2, "duration": -1,
        })

        # Unlock new capabilities
        result["new_interactions"] = [
            i.value for i in self.available_interactions
        ]

        return result

    def _update_available_interactions(self) -> None:
        """Update available interactions based on current bond level."""
        level_unlocks = {
            BondLevel.AWARENESS: [
                BondInteraction.WORLD_COMMENT,
            ],
            BondLevel.RECOGNITION: [
                BondInteraction.WORLD_COMMENT,
                BondInteraction.PUZZLE_HINT,
                BondInteraction.DETECT_CORRUPTION,
            ],
            BondLevel.TRUST: [
                BondInteraction.WORLD_COMMENT,
                BondInteraction.PUZZLE_HINT,
                BondInteraction.DETECT_CORRUPTION,
                BondInteraction.COMBAT_ASSIST,
                BondInteraction.PASSIVE_BUFF,
                BondInteraction.SPIRIT_TRANSLATE,
                BondInteraction.EMOTIONAL_SUPPORT,
            ],
            BondLevel.PARTNERSHIP: [
                BondInteraction.WORLD_COMMENT,
                BondInteraction.PUZZLE_HINT,
                BondInteraction.DETECT_CORRUPTION,
                BondInteraction.COMBAT_ASSIST,
                BondInteraction.PASSIVE_BUFF,
                BondInteraction.SPIRIT_TRANSLATE,
                BondInteraction.EMOTIONAL_SUPPORT,
                BondInteraction.TEACH_ABILITY,
                BondInteraction.SHARE_MEMORY,
                BondInteraction.CRAFT_ASSIST,
                BondInteraction.TERRITORY_GUIDE,
            ],
            BondLevel.UNITY: [
                interaction for interaction in BondInteraction
            ],
        }
        self.available_interactions = level_unlocks.get(self.level, [])

    def update(self, delta: float, location: str = "",
               nearby_spirit_ids: Optional[list[str]] = None) -> list[dict]:
        """
        Tick the bond forward. Handles mood updates, cooldowns,
        and generates contextual dialogue.
        """
        events: list[dict] = []

        # Update mood
        mood_events = self.mood.update(delta)
        for me in mood_events:
            events.append({"type": "mood_change", "detail": me})

        # Cooldown
        if self.cooldown_remaining > 0:
            self.cooldown_remaining -= 1
            if self.cooldown_remaining == 0:
                self.is_available = True
                events.append({"type": "spirit_available", "spirit_id": self.spirit_id})

        # Contextual commentary (if active)
        if self.is_active and random.random() < 0.05 * delta:
            context = "exploration"
            line = self.dialogue.get_line(context, self.level, location=location)
            if line:
                events.append({
                    "type": "companion_dialogue",
                    "spirit_id": self.spirit_id,
                    "line": line,
                    "context": context,
                })

            # React to nearby spirits
            if nearby_spirit_ids:
                for sid in nearby_spirit_ids:
                    if sid in self.preferences.spirit_friends:
                        events.append({
                            "type": "companion_spirit_reaction",
                            "spirit_id": self.spirit_id,
                            "other_id": sid,
                            "reaction": "friendly",
                        })
                    elif sid in self.preferences.spirit_rivals:
                        events.append({
                            "type": "companion_spirit_reaction",
                            "spirit_id": self.spirit_id,
                            "other_id": sid,
                            "reaction": "hostile",
                        })

        return events

    def summon(self, current_ma: float) -> dict:
        """
        Summon this bonded spirit. Requires ma and availability.
        """
        result: dict = {"success": False, "events": []}

        if not self.is_available:
            result["events"].append("not_available")
            return result

        if current_ma < self.summoning_cost:
            result["events"].append("insufficient_ma")
            return result

        self.is_active = True
        result["success"] = True
        result["ma_cost"] = self.summoning_cost
        result["events"].append("spirit_summoned")

        # Mood effect based on conditions
        self.mood.apply_effect({
            "target": "energy", "amount": -0.05, "duration": -1,
        })

        return result

    def dismiss(self) -> dict:
        """Dismiss the spirit back to the spirit world."""
        self.is_active = False
        self.is_available = False
        self.cooldown_remaining = 3  # Brief cooldown

        result: dict = {"events": ["spirit_dismissed"]}

        # Personality affects reaction to dismissal
        if self.primary_personality == SpiritPersonalityType.PLAYFUL:
            result["reaction"] = "playful_farewell"
        elif self.primary_personality == SpiritPersonalityType.PROTECTIVE:
            result["reaction"] = "reluctant_departure"
            self.mood.apply_effect({
                "target": "comfort", "amount": -0.05, "duration": -1,
            })
        else:
            result["reaction"] = "graceful_departure"

        return result


# ---------------------------------------------------------------------------
# Bond Manager - Tracks all of Aoi's bonds
# ---------------------------------------------------------------------------

@dataclass
class BondManager:
    """
    Manages all of Aoi's spirit bonds. Enforces active bond limits,
    handles inter-spirit dynamics among bonded spirits, and provides
    the interface between the bond system and the rest of the game.
    """
    bonds: dict[str, SpiritBond] = field(default_factory=dict)

    # Limits
    max_active_bonds: int = 3            # How many spirits can be active at once
    spirit_affinity_stat: int = 10       # Aoi's spirit affinity (limits total bonds)

    # Cross-bond dynamics
    active_spirit_synergies: dict[str, float] = field(default_factory=dict)

    @property
    def total_bonds(self) -> int:
        return len(self.bonds)

    @property
    def max_total_bonds(self) -> int:
        """Maximum bonds Aoi can maintain, based on spirit affinity."""
        return 3 + (self.spirit_affinity_stat // 5)

    @property
    def active_bonds(self) -> list[SpiritBond]:
        """Currently active (summoned) bonds."""
        return [b for b in self.bonds.values() if b.is_active]

    @property
    def active_count(self) -> int:
        return len(self.active_bonds)

    @property
    def can_form_new_bond(self) -> bool:
        return self.total_bonds < self.max_total_bonds

    @property
    def can_summon(self) -> bool:
        return self.active_count < self.max_active_bonds

    def form_bond(self, spirit_id: str, spirit_name: str,
                  method: BondFormationMethod,
                  personality: SpiritPersonalityType,
                  preferences: Optional[SpiritPreferences] = None,
                  day: int = 0) -> dict:
        """
        Form a new bond with a spirit. This is a significant moment.
        """
        result: dict = {"success": False, "events": []}

        if not self.can_form_new_bond:
            result["events"].append("max_bonds_reached")
            return result

        if spirit_id in self.bonds:
            result["events"].append("already_bonded")
            return result

        bond_id = f"bond_{spirit_id}"
        bond = SpiritBond(
            bond_id=bond_id,
            spirit_id=spirit_id,
            spirit_name=spirit_name,
            formation_method=method,
            primary_personality=personality,
            preferences=preferences or SpiritPreferences(),
            day_formed=day,
        )

        # Formation method affects starting affinity and mood
        method_bonuses = {
            BondFormationMethod.COMBAT_NEGOTIATION: {
                "affinity": 5.0, "trust": -0.1, "energy": -0.1,
            },
            BondFormationMethod.QUEST_COMPLETION: {
                "affinity": 8.0, "trust": 0.1, "energy": 0.0,
            },
            BondFormationMethod.GIFT_OFFERING: {
                "affinity": 3.0, "trust": 0.0, "energy": 0.0,
            },
            BondFormationMethod.MA_MOMENT: {
                "affinity": 6.0, "trust": 0.15, "energy": 0.0,
            },
            BondFormationMethod.RESCUE: {
                "affinity": 10.0, "trust": 0.2, "energy": -0.15,
            },
            BondFormationMethod.MUTUAL_CURIOSITY: {
                "affinity": 4.0, "trust": 0.05, "energy": 0.05,
            },
            BondFormationMethod.ANCESTRAL: {
                "affinity": 15.0, "trust": 0.25, "energy": 0.0,
            },
        }

        bonus = method_bonuses.get(method, {"affinity": 5.0})
        bond.affinity = bonus.get("affinity", 5.0)
        if "trust" in bonus:
            bond.mood.trust_feeling += bonus["trust"]
        if "energy" in bonus:
            bond.mood.energy += bonus["energy"]

        # Create formation memory
        memory = BondMemory(
            memory_id=f"formation_{bond_id}",
            description=f"First meeting through {method.value}",
            emotion="wonder",
            affinity_gained=bond.affinity,
            day_formed=day,
            is_milestone=True,
            tags=["formation", method.value],
        )
        bond.memories.append(memory)

        self.bonds[bond_id] = bond
        result["success"] = True
        result["bond_id"] = bond_id
        result["events"].append("bond_formed")

        return result

    def dissolve_bond(self, bond_id: str) -> dict:
        """
        Dissolve a bond. This is painful for both sides and should
        be a significant story moment.
        """
        result: dict = {"success": False, "events": []}

        bond = self.bonds.get(bond_id)
        if not bond:
            result["events"].append("bond_not_found")
            return result

        if bond.is_active:
            bond.dismiss()

        del self.bonds[bond_id]
        result["success"] = True
        result["events"].append("bond_dissolved")
        result["spirit_id"] = bond.spirit_id
        result["spirit_name"] = bond.spirit_name
        result["bond_level"] = bond.level.value
        result["total_memories"] = len(bond.memories)

        return result

    def get_bond_for_spirit(self, spirit_id: str) -> Optional[SpiritBond]:
        """Get the bond for a specific spirit, if one exists."""
        bond_id = f"bond_{spirit_id}"
        return self.bonds.get(bond_id)

    def summon_spirit(self, bond_id: str, current_ma: float) -> dict:
        """Attempt to summon a bonded spirit."""
        result: dict = {"success": False, "events": []}

        if not self.can_summon:
            result["events"].append("max_active_reached")
            return result

        bond = self.bonds.get(bond_id)
        if not bond:
            result["events"].append("bond_not_found")
            return result

        summon_result = bond.summon(current_ma)
        result.update(summon_result)

        if summon_result["success"]:
            self._calculate_synergies()

        return result

    def dismiss_spirit(self, bond_id: str) -> dict:
        """Dismiss a summoned spirit."""
        bond = self.bonds.get(bond_id)
        if not bond:
            return {"events": ["bond_not_found"]}

        result = bond.dismiss()
        self._calculate_synergies()
        return result

    def _calculate_synergies(self) -> None:
        """
        Calculate synergies and conflicts between active bonded spirits.
        Some spirits empower each other. Others clash.
        """
        self.active_spirit_synergies.clear()
        active = self.active_bonds

        for i, bond_a in enumerate(active):
            for bond_b in active[i + 1:]:
                key = f"{bond_a.spirit_id}_{bond_b.spirit_id}"

                # Check if they're friends or rivals
                synergy = 0.0
                if bond_b.spirit_id in bond_a.preferences.spirit_friends:
                    synergy += 0.2
                if bond_a.spirit_id in bond_b.preferences.spirit_friends:
                    synergy += 0.2
                if bond_b.spirit_id in bond_a.preferences.spirit_rivals:
                    synergy -= 0.3
                if bond_a.spirit_id in bond_b.preferences.spirit_rivals:
                    synergy -= 0.3

                if synergy != 0.0:
                    self.active_spirit_synergies[key] = synergy

    def update(self, delta: float, location: str = "",
               nearby_spirit_ids: Optional[list[str]] = None) -> list[dict]:
        """Update all bonds. Returns accumulated events."""
        all_events: list[dict] = []

        for bond in self.bonds.values():
            events = bond.update(delta, location, nearby_spirit_ids)
            all_events.extend(events)

        return all_events

    def get_active_passive_buffs(self) -> dict[str, float]:
        """Collect all passive buffs from active bonded spirits."""
        combined: dict[str, float] = {}

        for bond in self.active_bonds:
            for buff_name, buff_value in bond.passive_buffs.items():
                # Synergy modifier
                synergy_mod = 1.0
                for key, syn in self.active_spirit_synergies.items():
                    if bond.spirit_id in key:
                        synergy_mod += syn

                effective = buff_value * synergy_mod
                if buff_name in combined:
                    combined[buff_name] += effective
                else:
                    combined[buff_name] = effective

        return combined

    def get_combat_bonuses(self) -> dict[str, float]:
        """Get combined combat bonuses from all active bonds."""
        power = 0.0
        defense = 0.0

        for bond in self.active_bonds:
            mood_mult = 0.5 + bond.mood.overall * 0.5
            power += bond.combat_power_bonus * mood_mult
            defense += bond.combat_defense_bonus * mood_mult

        return {"power": power, "defense": defense}
