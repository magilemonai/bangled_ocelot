"""
Ma no Kuni - Turn-Based Battle System

Combat in Ma no Kuni is a conversation held in the language of action
and silence. The Ma Gauge - the beating heart of every encounter -
rewards those who understand that the space between moments is where
the deepest power lives.

A battle is not a sequence of attacks. It is a negotiation between
worlds. The player who learns to pause, to observe, to listen,
will find that the strongest action is often inaction - and that
the fiercest enemy may become the dearest friend.

Turn order flows like water: each combatant acts when their readiness
fills. Speed determines how quickly readiness accumulates, but the
Wait action and Ma timing can bend this flow.

The Negotiate option is always available. Always. Some spirits cannot
be defeated by force. Some should not be. The bestiary remembers
every choice.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Callable

from .abilities import (
    Ability, AbilityCategory, AbilityCost, AbilityEffect,
    Element, ELEMENTAL_STRENGTHS, ELEMENTAL_HARMONIES,
    StatusEffect, StatusInstance, TargetType,
    DEFAULT_ABILITIES, SPIRIT_ARTS,
)


# ---------------------------------------------------------------------------
# Combat enums
# ---------------------------------------------------------------------------

class BattlePhase(Enum):
    """The phases of an encounter."""
    INITIATIVE = auto()       # Determine turn order
    TURN_START = auto()       # Pre-turn effects (status ticks, etc.)
    ACTION_SELECT = auto()    # Player chooses action
    MA_TIMING = auto()        # The Ma timing window
    ACTION_EXECUTE = auto()   # Action resolves
    TURN_END = auto()         # Post-turn effects
    NEGOTIATION = auto()      # Special negotiation phase
    BATTLE_END = auto()       # Victory, defeat, flee, or befriend
    TRANSITION_OUT = auto()   # Return to exploration


class BattleResult(Enum):
    """How the encounter concluded."""
    VICTORY = auto()          # All enemies defeated
    DEFEAT = auto()           # Party wiped
    FLED = auto()             # Party escaped
    BEFRIENDED = auto()       # Spirit negotiation succeeded
    PURIFIED = auto()         # Corrupted spirit cleansed
    SPARED = auto()           # Enemy left alive, chose to leave
    INTERRUPTED = auto()      # External event interrupted combat


class CombatantType(Enum):
    """What kind of being is fighting."""
    PLAYER = auto()           # Aoi
    HUMAN_ALLY = auto()       # Human party members
    SPIRIT_ALLY = auto()      # Befriended spirit in party
    SPIRIT_ENEMY = auto()     # Hostile or confused spirit
    CORRUPTED_SPIRIT = auto() # Spirit twisted by corruption
    HUMAN_ENEMY = auto()      # Rare - humans who exploit spirits


class NegotiationStance(Enum):
    """The spirit's current attitude toward negotiation."""
    HOSTILE = auto()          # Will not listen
    WARY = auto()             # Might listen if approached correctly
    CURIOUS = auto()          # Interested but cautious
    RECEPTIVE = auto()        # Open to conversation
    FRIENDLY = auto()         # Almost befriended
    TRUSTING = auto()         # Will join / depart peacefully


class MaTimingResult(Enum):
    """How well the player timed their Ma input."""
    MISSED = auto()           # No timing attempt
    POOR = auto()             # Way off
    DECENT = auto()           # Close
    GOOD = auto()             # Solid
    PERFECT = auto()          # Exact center of the window


# ---------------------------------------------------------------------------
# Combatant
# ---------------------------------------------------------------------------

@dataclass
class CombatantStats:
    """The vital statistics of a being in battle."""
    max_hp: int = 100
    current_hp: int = 100
    max_sp: int = 50
    current_sp: int = 50
    attack: int = 10
    defense: int = 10
    spirit_power: int = 10     # Strength of Spirit Arts
    spirit_defense: int = 10   # Resistance to Spirit Arts
    speed: int = 10            # Turn order priority
    evasion: float = 0.05      # Chance to dodge
    critical_rate: float = 0.05
    level: int = 1


@dataclass
class Combatant:
    """
    A participant in battle - human, spirit, or something in between.
    """
    id: str
    name: str
    combatant_type: CombatantType
    stats: CombatantStats
    abilities: list[Ability] = field(default_factory=list)
    status_effects: list[StatusInstance] = field(default_factory=list)
    element: Element = Element.NEUTRAL
    readiness: float = 0.0     # 0-100, acts at 100
    is_alive: bool = True
    negotiation_stance: NegotiationStance = NegotiationStance.HOSTILE
    negotiation_progress: float = 0.0  # 0.0 to 1.0
    corruption_level: float = 0.0      # 0.0 = pure, 1.0 = fully corrupted
    spirit_id: Optional[str] = None    # Link to bestiary entry
    bond_level: float = 0.0            # Relationship with player
    flee_chance: float = 0.5           # Base chance to flee from this enemy
    loot_table: dict[str, float] = field(default_factory=dict)
    dialogue_options: list[str] = field(default_factory=list)
    personality_traits: list[str] = field(default_factory=list)
    preferred_element: Element = Element.NEUTRAL
    feared_element: Element = Element.NEUTRAL

    @property
    def is_spirit(self) -> bool:
        return self.combatant_type in (
            CombatantType.SPIRIT_ENEMY,
            CombatantType.SPIRIT_ALLY,
            CombatantType.CORRUPTED_SPIRIT,
        )

    @property
    def is_corrupted(self) -> bool:
        return self.corruption_level > 0.3

    @property
    def can_negotiate(self) -> bool:
        """Can this combatant be negotiated with?"""
        if self.combatant_type == CombatantType.HUMAN_ENEMY:
            return False
        if self.corruption_level > 0.8:
            return False  # Too far gone for words alone
        return True

    def has_status(self, effect: StatusEffect) -> bool:
        return any(s.effect == effect for s in self.status_effects)

    def apply_status(self, effect: StatusEffect, duration: int,
                     potency: float = 1.0, source: Optional[str] = None) -> bool:
        """Apply a status effect. Returns False if warded."""
        if self.has_status(StatusEffect.WARDED):
            ward = next(s for s in self.status_effects
                        if s.effect == StatusEffect.WARDED)
            if random.random() < 0.7 * ward.potency:
                return False

        existing = next(
            (s for s in self.status_effects if s.effect == effect), None
        )
        if existing:
            existing.duration = max(existing.duration, duration)
            existing.potency = max(existing.potency, potency)
            existing.stacks = min(existing.stacks + 1, 3)
        else:
            self.status_effects.append(
                StatusInstance(effect, duration, potency, source)
            )
        return True

    def remove_status(self, effect: StatusEffect) -> None:
        self.status_effects = [
            s for s in self.status_effects if s.effect != effect
        ]

    def tick_statuses(self) -> list[dict]:
        """Process all status effects for one turn. Returns event log."""
        events = []
        expired = []

        for status in self.status_effects:
            if status.effect == StatusEffect.BURNING:
                dmg = int(5 * status.potency * status.stacks)
                self.stats.current_hp -= dmg
                events.append({
                    "type": "status_damage",
                    "target": self.id,
                    "effect": "burning",
                    "damage": dmg,
                })
            elif status.effect == StatusEffect.CORRUPTED:
                dmg = int(3 * status.potency * status.stacks)
                self.stats.current_hp -= dmg
                self.stats.current_sp -= int(2 * status.potency)
                events.append({
                    "type": "status_damage",
                    "target": self.id,
                    "effect": "corrupted",
                    "damage": dmg,
                })
            elif status.effect == StatusEffect.REGENERATING:
                heal = int(8 * status.potency)
                self.stats.current_hp = min(
                    self.stats.max_hp, self.stats.current_hp + heal
                )
                events.append({
                    "type": "status_heal",
                    "target": self.id,
                    "effect": "regenerating",
                    "healing": heal,
                })

            if status.tick():
                expired.append(status)

        for status in expired:
            self.status_effects.remove(status)
            events.append({
                "type": "status_expired",
                "target": self.id,
                "effect": status.effect.value,
            })

        if self.stats.current_hp <= 0:
            self.is_alive = False
            events.append({"type": "combatant_down", "target": self.id})

        return events

    def calculate_readiness_gain(self) -> float:
        """How much readiness this combatant gains per tick."""
        base = self.stats.speed * 2.0
        if self.has_status(StatusEffect.HASTE):
            base *= 1.5
        if self.has_status(StatusEffect.ROOTED):
            base *= 0.7
        if self.has_status(StatusEffect.NOSTALGIC):
            base *= 0.5
        return base


# ---------------------------------------------------------------------------
# Ma Gauge - the timing mechanic
# ---------------------------------------------------------------------------

@dataclass
class MaGauge:
    """
    The Ma Gauge: the space between action and power.

    In combat, ma accumulates when you Wait, Defend, or Observe.
    It drains when you attack or use aggressive Spirit Arts.
    The gauge level amplifies Spirit Arts and negotiation attempts.

    But the true depth of the Ma system is in timing. When you
    select an action, a timing window appears. Press at the
    exact center of the window - the perfect pause - and the
    action's power is doubled. Miss the window entirely and
    you still act, but without resonance.

    This is the mechanical expression of the game's philosophy:
    the pause matters as much as the action.
    """
    current: float = 0.0
    maximum: float = 100.0
    charge_rate: float = 1.0    # Modified by equipment, abilities, bonds
    decay_rate: float = 0.5     # Ma fades slowly each turn if unused
    combo_counter: int = 0      # Consecutive perfect timings
    max_combo: int = 0          # Best combo this battle

    def charge(self, amount: float) -> None:
        """Accumulate ma."""
        self.current = min(self.maximum, self.current + amount * self.charge_rate)

    def spend(self, amount: float) -> bool:
        """Spend ma. Returns False if insufficient."""
        if self.current < amount:
            return False
        self.current -= amount
        return True

    def decay(self) -> None:
        """Ma fades slightly each turn."""
        self.current = max(0.0, self.current - self.decay_rate)

    def evaluate_timing(self, timing_accuracy: float) -> MaTimingResult:
        """
        Evaluate the player's timing input.

        timing_accuracy: 0.0 (edge of window) to 1.0 (dead center)
        """
        if timing_accuracy >= 0.95:
            self.combo_counter += 1
            self.max_combo = max(self.max_combo, self.combo_counter)
            return MaTimingResult.PERFECT
        elif timing_accuracy >= 0.75:
            self.combo_counter = max(0, self.combo_counter - 1)
            return MaTimingResult.GOOD
        elif timing_accuracy >= 0.5:
            self.combo_counter = 0
            return MaTimingResult.DECENT
        elif timing_accuracy >= 0.2:
            self.combo_counter = 0
            return MaTimingResult.POOR
        else:
            self.combo_counter = 0
            return MaTimingResult.MISSED

    @property
    def combo_bonus(self) -> float:
        """Consecutive perfect timings build a growing bonus."""
        return 1.0 + (self.combo_counter * 0.15)

    @property
    def gauge_percentage(self) -> float:
        return (self.current / self.maximum) * 100.0 if self.maximum > 0 else 0.0


# ---------------------------------------------------------------------------
# Combat rewards
# ---------------------------------------------------------------------------

@dataclass
class BattleRewards:
    """What the party gains from the encounter."""
    spirit_essence: int = 0        # Experience equivalent
    material_drops: list[dict] = field(default_factory=list)
    bestiary_knowledge: dict[str, float] = field(default_factory=dict)
    relationship_changes: dict[str, float] = field(default_factory=dict)
    unlocked_abilities: list[str] = field(default_factory=list)
    lore_fragments: list[str] = field(default_factory=list)
    befriended_spirit: Optional[str] = None
    purified_spirit: Optional[str] = None


# ---------------------------------------------------------------------------
# Negotiation system
# ---------------------------------------------------------------------------

@dataclass
class NegotiationState:
    """
    Tracks the state of a negotiation with a spirit.

    Negotiation is not a minigame bolted onto combat.
    It IS combat - the most important kind. Every spirit has
    a personality, desires, fears, and a story. Understanding
    these is the key to befriending them.

    Some spirits want to be acknowledged.
    Some want to be left alone.
    Some want to play.
    Some want to grieve.
    Some just want someone to use them again.

    The negotiation system tracks emotional resonance, not
    dialogue tree branches. The right feeling matters more
    than the right words.
    """
    target: str                   # Spirit being negotiated with
    progress: float = 0.0        # 0.0 to 1.0 - success threshold
    trust: float = 0.0           # How much the spirit trusts the player
    understanding: float = 0.0   # How well the player understands the spirit
    emotional_resonance: float = 0.0  # Emotional connection strength
    attempts: int = 0            # How many negotiation actions taken
    max_attempts: int = 5        # Spirits lose patience
    stance: NegotiationStance = NegotiationStance.WARY
    mood_modifiers: dict[str, float] = field(default_factory=dict)
    revealed_desires: list[str] = field(default_factory=list)
    revealed_fears: list[str] = field(default_factory=list)
    successful_topics: list[str] = field(default_factory=list)
    failed_topics: list[str] = field(default_factory=list)

    def attempt_negotiation(self, approach: str, ma_bonus: float,
                            bestiary_knowledge: float,
                            personality_match: float) -> tuple[bool, str]:
        """
        Make a negotiation attempt.

        Returns (success, narrative_text).
        """
        self.attempts += 1

        # Base success chance
        base_chance = 0.3

        # Ma bonus (patience is rewarded)
        base_chance += ma_bonus * 0.2

        # Bestiary knowledge bonus (knowing the spirit helps)
        base_chance += bestiary_knowledge * 0.3

        # Personality match (right approach for right spirit)
        base_chance += personality_match * 0.25

        # Trust built from previous successful attempts
        base_chance += self.trust * 0.15

        # Penalty for too many attempts (spirits get annoyed)
        if self.attempts > 3:
            base_chance -= (self.attempts - 3) * 0.1

        success = random.random() < base_chance

        if success:
            self.trust += 0.15
            self.understanding += 0.1
            self.emotional_resonance += 0.12
            self.progress += 0.2 + (personality_match * 0.1)
            self.successful_topics.append(approach)
            self._update_stance()
            return True, self._success_text(approach)
        else:
            self.trust -= 0.05
            self.failed_topics.append(approach)
            self._update_stance()
            return False, self._failure_text(approach)

    def _update_stance(self) -> None:
        """Update the spirit's negotiation stance based on progress."""
        if self.progress >= 0.9:
            self.stance = NegotiationStance.TRUSTING
        elif self.progress >= 0.7:
            self.stance = NegotiationStance.FRIENDLY
        elif self.progress >= 0.5:
            self.stance = NegotiationStance.RECEPTIVE
        elif self.progress >= 0.3:
            self.stance = NegotiationStance.CURIOUS
        elif self.trust > 0:
            self.stance = NegotiationStance.WARY
        else:
            self.stance = NegotiationStance.HOSTILE

    def _success_text(self, approach: str) -> str:
        stance_texts = {
            NegotiationStance.CURIOUS: "The spirit tilts its head, considering you with new eyes.",
            NegotiationStance.RECEPTIVE: "Something softens in the spirit's bearing. It is listening now.",
            NegotiationStance.FRIENDLY: "The spirit draws closer. The hostility is gone, "
                                        "replaced by something fragile and warm.",
            NegotiationStance.TRUSTING: "The spirit reaches out. In the space between you, "
                                        "a bond begins to form - delicate as spider silk, "
                                        "strong as memory.",
        }
        return stance_texts.get(
            self.stance,
            "The spirit pauses. Your words found something."
        )

    def _failure_text(self, approach: str) -> str:
        if self.attempts >= self.max_attempts:
            return ("The spirit turns away. It has heard enough. "
                    "Perhaps another time, with more understanding.")
        return "The spirit recoils. That was not what it needed to hear."

    @property
    def is_complete(self) -> bool:
        """Has the negotiation succeeded?"""
        return self.stance == NegotiationStance.TRUSTING and self.progress >= 0.9

    @property
    def is_failed(self) -> bool:
        """Has the negotiation failed beyond recovery?"""
        return self.attempts >= self.max_attempts and self.progress < 0.5


# ---------------------------------------------------------------------------
# Battle action and resolution
# ---------------------------------------------------------------------------

@dataclass
class BattleAction:
    """A single action taken in combat."""
    actor: str                    # Combatant ID
    ability: Ability
    targets: list[str]            # Target combatant IDs
    ma_timing: float = 0.0       # Timing accuracy (0.0-1.0)
    negotiation_approach: str = ""  # For negotiate actions


@dataclass
class ActionResult:
    """The outcome of a single action."""
    actor: str
    ability_name: str
    targets_hit: list[str] = field(default_factory=list)
    targets_missed: list[str] = field(default_factory=list)
    damage_dealt: dict[str, int] = field(default_factory=dict)
    healing_done: dict[str, int] = field(default_factory=dict)
    statuses_applied: list[dict] = field(default_factory=list)
    statuses_removed: list[dict] = field(default_factory=list)
    ma_timing_result: MaTimingResult = MaTimingResult.MISSED
    ma_bonus: float = 1.0
    bestiary_revealed: dict[str, float] = field(default_factory=dict)
    negotiation_result: Optional[tuple[bool, str]] = None
    narrative_text: str = ""
    critical_hit: bool = False
    elemental_advantage: bool = False
    fled_successfully: bool = False


# ---------------------------------------------------------------------------
# Battle - the main combat encounter
# ---------------------------------------------------------------------------

class Battle:
    """
    A single combat encounter.

    The battle orchestrates the dance between combatants, manages the
    Ma Gauge, resolves actions, handles negotiation, and determines
    outcomes. It is the stage; the combatants are the performers.
    """

    def __init__(
        self,
        party: list[Combatant],
        enemies: list[Combatant],
        environment: str = "urban",
        time_of_day: str = "evening",
        spirit_permeability: float = 0.5,
        ambient_ma: float = 0.0,
        can_flee: bool = True,
        is_boss: bool = False,
    ):
        self.party = party
        self.enemies = enemies
        self.all_combatants: list[Combatant] = party + enemies
        self.environment = environment
        self.time_of_day = time_of_day
        self.spirit_permeability = spirit_permeability
        self.can_flee = can_flee
        self.is_boss = is_boss

        self.phase = BattlePhase.INITIATIVE
        self.turn_count: int = 0
        self.current_actor: Optional[Combatant] = None
        self.ma_gauge = MaGauge(current=ambient_ma)
        self.turn_order: list[Combatant] = []
        self.action_log: list[ActionResult] = []
        self.result: Optional[BattleResult] = None
        self.rewards = BattleRewards()
        self.negotiations: dict[str, NegotiationState] = {}

        # Field effects that apply to the whole battle
        self.field_effects: list[dict] = []

        # Environmental modifiers based on location and time
        self.element_modifiers: dict[Element, float] = (
            self._calculate_element_modifiers()
        )

    def _calculate_element_modifiers(self) -> dict[Element, float]:
        """
        The environment shapes elemental power.
        Tokyo's districts, the time of day, the spirit tide -
        all influence which elements wax and wane.
        """
        mods = {e: 1.0 for e in Element}

        # Time of day modifiers
        time_mods = {
            "dawn": {Element.LIGHT: 1.3, Element.SHADOW: 0.7},
            "morning": {Element.LIGHT: 1.2, Element.FIRE: 1.1},
            "midday": {Element.FIRE: 1.2, Element.LIGHT: 1.1},
            "afternoon": {Element.EARTH: 1.1, Element.WIND: 1.1},
            "dusk": {Element.SHADOW: 1.2, Element.MEMORY: 1.2},
            "evening": {Element.SHADOW: 1.3, Element.SILENCE: 1.1},
            "midnight": {Element.SHADOW: 1.4, Element.SILENCE: 1.3,
                         Element.LIGHT: 0.7},
            "witching": {Element.SILENCE: 1.5, Element.MEMORY: 1.3,
                         Element.SHADOW: 1.3, Element.LIGHT: 0.5},
        }
        for element, mod in time_mods.get(self.time_of_day, {}).items():
            mods[element] *= mod

        # Environment modifiers
        env_mods = {
            "urban": {Element.EARTH: 0.8, Element.MEMORY: 1.1},
            "park": {Element.WIND: 1.2, Element.EARTH: 1.2},
            "shrine": {Element.LIGHT: 1.3, Element.SILENCE: 1.2},
            "river": {Element.WATER: 1.4, Element.MEMORY: 1.1},
            "underground": {Element.EARTH: 1.3, Element.SHADOW: 1.2,
                            Element.LIGHT: 0.8},
            "rooftop": {Element.WIND: 1.4, Element.LIGHT: 1.2},
            "alley": {Element.SHADOW: 1.3, Element.SILENCE: 1.1},
            "station": {Element.SILENCE: 1.1, Element.MEMORY: 1.2},
        }
        for element, mod in env_mods.get(self.environment, {}).items():
            mods[element] *= mod

        # Spirit permeability affects all non-neutral elements
        perm_bonus = self.spirit_permeability * 0.2
        for element in Element:
            if element != Element.NEUTRAL:
                mods[element] *= (1.0 + perm_bonus)

        return mods

    # -------------------------------------------------------------------
    # Turn management
    # -------------------------------------------------------------------

    def determine_turn_order(self) -> list[Combatant]:
        """
        Calculate who acts next based on readiness.
        Readiness fills based on speed; first to 100 acts.
        """
        active = [c for c in self.all_combatants if c.is_alive]

        # Advance readiness until someone hits 100
        while not any(c.readiness >= 100.0 for c in active):
            for combatant in active:
                combatant.readiness += combatant.calculate_readiness_gain()

        # Sort by readiness (highest first), speed as tiebreaker
        ready = [c for c in active if c.readiness >= 100.0]
        ready.sort(key=lambda c: (c.readiness, c.stats.speed), reverse=True)

        self.turn_order = ready
        return ready

    def start_turn(self, combatant: Combatant) -> list[dict]:
        """
        Begin a combatant's turn. Process status effects,
        check for incapacitation, update the field.
        """
        self.turn_count += 1
        self.current_actor = combatant
        self.phase = BattlePhase.TURN_START
        combatant.readiness = 0.0

        events = []

        # Tick status effects
        status_events = combatant.tick_statuses()
        events.extend(status_events)

        # Check if combatant can act
        if not combatant.is_alive:
            events.append({
                "type": "turn_skipped",
                "actor": combatant.id,
                "reason": "defeated",
            })
            return events

        if combatant.has_status(StatusEffect.NOSTALGIC):
            if random.random() < 0.4:
                events.append({
                    "type": "turn_skipped",
                    "actor": combatant.id,
                    "reason": "lost_in_memory",
                    "text": f"{combatant.name} is lost in a memory...",
                })
                return events

        if combatant.has_status(StatusEffect.FRIGHTENED):
            if random.random() < 0.3:
                events.append({
                    "type": "turn_skipped",
                    "actor": combatant.id,
                    "reason": "frightened",
                    "text": f"{combatant.name} is paralyzed with fear.",
                })
                return events

        # Ma gauge natural decay
        self.ma_gauge.decay()

        self.phase = BattlePhase.ACTION_SELECT
        return events

    def get_available_actions(self, combatant: Combatant) -> list[Ability]:
        """Get all abilities this combatant can currently use."""
        available = []

        for ability in combatant.abilities:
            can_use, reason = ability.can_use(
                user_sp=combatant.stats.current_sp,
                user_hp=combatant.stats.current_hp,
                user_ma=self.ma_gauge.current,
                user_level=combatant.stats.level,
                bond_level=combatant.bond_level,
            )
            if can_use:
                # Check if silenced blocks spirit arts
                if (combatant.has_status(StatusEffect.SILENCED)
                        and ability.category in (
                            AbilityCategory.ATTACK,
                            AbilityCategory.HEALING,
                            AbilityCategory.SUPPORT,
                            AbilityCategory.DEBUFF,
                        )
                        and ability.effect.element != Element.NEUTRAL
                        and ability.id not in DEFAULT_ABILITIES):
                    continue
                available.append(ability)

        # Negotiate is always available if there's a valid target
        if any(e.can_negotiate for e in self.enemies if e.is_alive):
            negotiate = DEFAULT_ABILITIES.get("negotiate")
            if negotiate and negotiate not in available:
                available.append(negotiate)

        # Flee check
        if self.can_flee and not self.is_boss:
            flee = DEFAULT_ABILITIES.get("flee")
            if flee and flee not in available:
                available.append(flee)

        return available

    # -------------------------------------------------------------------
    # Action resolution
    # -------------------------------------------------------------------

    def resolve_action(self, action: BattleAction) -> ActionResult:
        """
        Resolve a combat action. This is where numbers meet narrative.
        """
        actor = self._get_combatant(action.actor)
        ability = action.ability
        result = ActionResult(
            actor=action.actor,
            ability_name=ability.name,
        )

        if actor is None or not actor.is_alive:
            result.narrative_text = "The action fades into nothing."
            return result

        # --- Ma Timing ---
        self.phase = BattlePhase.MA_TIMING
        timing_result = self.ma_gauge.evaluate_timing(action.ma_timing)
        result.ma_timing_result = timing_result
        ma_multiplier = ability.calculate_ma_bonus(
            self.ma_gauge.current, action.ma_timing
        )
        result.ma_bonus = ma_multiplier

        # Generate timing narrative
        timing_narratives = {
            MaTimingResult.PERFECT: "The pause is perfect. Power resonates "
                                    "through the space between moments.",
            MaTimingResult.GOOD: "The rhythm is strong. Ma flows smoothly.",
            MaTimingResult.DECENT: "An adequate pause. The ma responds, if weakly.",
            MaTimingResult.POOR: "The timing is off. The moment passes ungrasped.",
            MaTimingResult.MISSED: "No pause. The action carries only brute force.",
        }

        self.phase = BattlePhase.ACTION_EXECUTE

        # --- Handle special action types ---
        if ability.id == "flee":
            return self._resolve_flee(actor, result)

        if ability.id == "wait":
            return self._resolve_wait(actor, ability, result, timing_narratives,
                                      timing_result)

        if ability.category == AbilityCategory.NEGOTIATION:
            return self._resolve_negotiation(actor, action, result, ma_multiplier)

        # --- Cost ---
        actor.stats.current_sp -= ability.cost.sp
        actor.stats.current_hp -= ability.cost.hp
        if ability.cost.ma > 0:
            self.ma_gauge.spend(ability.cost.ma)

        # --- Ma generation ---
        if ability.effect.ma_generation > 0:
            self.ma_gauge.charge(ability.effect.ma_generation)

        # --- Resolve by target type ---
        targets = self._resolve_targets(action.targets, ability.target)

        if ability.category in (AbilityCategory.ATTACK, AbilityCategory.DEBUFF):
            self._resolve_offensive(actor, ability, targets, result,
                                    ma_multiplier, timing_result)
        elif ability.category in (AbilityCategory.HEALING, AbilityCategory.SUPPORT):
            self._resolve_supportive(actor, ability, targets, result,
                                     ma_multiplier, timing_result)
        elif ability.category == AbilityCategory.OBSERVATION:
            self._resolve_observation(actor, ability, targets, result,
                                      ma_multiplier)
        elif ability.category == AbilityCategory.PURIFICATION:
            self._resolve_purification(actor, ability, targets, result,
                                       ma_multiplier, timing_result)
        elif ability.category == AbilityCategory.FIELD:
            self._resolve_field(actor, ability, result, ma_multiplier,
                                timing_result)

        result.narrative_text = (
            timing_narratives.get(timing_result, "") + " " +
            result.narrative_text
        ).strip()

        # Track ability usage
        ability.times_used += 1
        self.action_log.append(result)

        # Check battle end conditions
        self._check_battle_end()

        return result

    def _resolve_flee(self, actor: Combatant,
                      result: ActionResult) -> ActionResult:
        """Attempt to flee from battle."""
        base_chance = 0.5
        # Average flee chance across enemies
        enemy_flee_mod = sum(
            e.flee_chance for e in self.enemies if e.is_alive
        ) / max(1, sum(1 for e in self.enemies if e.is_alive))
        flee_chance = base_chance * enemy_flee_mod

        # Speed advantage helps
        party_speed = max(c.stats.speed for c in self.party if c.is_alive)
        enemy_speed = max(
            (c.stats.speed for c in self.enemies if c.is_alive), default=1
        )
        if party_speed > enemy_speed:
            flee_chance += 0.2

        if random.random() < flee_chance:
            result.fled_successfully = True
            result.narrative_text = (
                "You turn and run. Not every encounter needs a resolution. "
                "Sometimes wisdom is knowing when to leave."
            )
            self.result = BattleResult.FLED
        else:
            result.fled_successfully = False
            result.narrative_text = (
                "The spirit blocks your path. It is not finished with you yet."
            )

        return result

    def _resolve_wait(self, actor: Combatant, ability: Ability,
                      result: ActionResult,
                      timing_narratives: dict, timing_result: MaTimingResult
                      ) -> ActionResult:
        """The Wait action - accumulating ma."""
        ma_gain = ability.effect.ma_generation
        if timing_result == MaTimingResult.PERFECT:
            ma_gain *= 2.0
        elif timing_result == MaTimingResult.GOOD:
            ma_gain *= 1.5

        self.ma_gauge.charge(ma_gain)

        result.narrative_text = (
            f"{timing_narratives.get(timing_result, '')} "
            f"{actor.name} breathes. The ma deepens. "
            f"(+{ma_gain:.0f} Ma)"
        ).strip()

        return result

    def _resolve_negotiation(self, actor: Combatant, action: BattleAction,
                             result: ActionResult,
                             ma_multiplier: float) -> ActionResult:
        """Attempt to negotiate with a spirit."""
        self.phase = BattlePhase.NEGOTIATION

        target = self._get_combatant(
            action.targets[0] if action.targets else ""
        )
        if target is None or not target.can_negotiate:
            result.narrative_text = "There is no one willing to listen."
            return result

        # Pay costs
        actor.stats.current_sp -= action.ability.cost.sp
        if action.ability.cost.ma > 0:
            self.ma_gauge.spend(action.ability.cost.ma)

        # Initialize or retrieve negotiation state
        if target.id not in self.negotiations:
            self.negotiations[target.id] = NegotiationState(target=target.id)

        neg = self.negotiations[target.id]

        # Calculate personality match based on approach and spirit traits
        personality_match = self._calculate_personality_match(
            action.negotiation_approach, target.personality_traits
        )

        # Bestiary knowledge helps negotiation
        bestiary_knowledge = self.rewards.bestiary_knowledge.get(target.id, 0.0)

        success, text = neg.attempt_negotiation(
            approach=action.negotiation_approach,
            ma_bonus=self.ma_gauge.current / self.ma_gauge.maximum,
            bestiary_knowledge=bestiary_knowledge,
            personality_match=personality_match,
        )

        result.negotiation_result = (success, text)
        result.narrative_text = text

        # Update the combatant's stance
        target.negotiation_stance = neg.stance
        target.negotiation_progress = neg.progress

        # Check if negotiation is complete
        if neg.is_complete:
            self.result = BattleResult.BEFRIENDED
            self.rewards.befriended_spirit = target.spirit_id
            self.rewards.relationship_changes[target.id] = 1.0
            result.narrative_text += (
                f"\n\n{target.name} reaches out to you. The battle is over. "
                f"Something better has begun."
            )

        return result

    def _resolve_offensive(self, actor: Combatant, ability: Ability,
                           targets: list[Combatant], result: ActionResult,
                           ma_multiplier: float,
                           timing: MaTimingResult) -> None:
        """Resolve an offensive action against targets."""
        for target in targets:
            if not target.is_alive:
                continue

            # Hit check
            hit_chance = ability.effect.accuracy
            if actor.has_status(StatusEffect.BLINDED):
                hit_chance *= 0.6
            if target.has_status(StatusEffect.WINDSWEPT):
                hit_chance *= 0.8
            if target.has_status(StatusEffect.SHADOWED):
                hit_chance *= 0.7

            hit_roll = random.random()
            evade_roll = random.random()

            if hit_roll > hit_chance or evade_roll < target.stats.evasion:
                result.targets_missed.append(target.id)
                continue

            result.targets_hit.append(target.id)

            # Damage calculation
            base_damage = ability.effect.damage
            attack_stat = (actor.stats.spirit_power
                           if ability.effect.element != Element.NEUTRAL
                           else actor.stats.attack)
            defense_stat = (target.stats.spirit_defense
                            if ability.effect.element != Element.NEUTRAL
                            else target.stats.defense)

            damage = int(
                base_damage
                * (attack_stat / max(1, defense_stat))
                * ma_multiplier
                * self.ma_gauge.combo_bonus
            )

            # Elemental advantage
            element = ability.effect.element
            if element in ELEMENTAL_STRENGTHS:
                if ELEMENTAL_STRENGTHS[element] == target.element:
                    damage = int(damage * 1.5)
                    result.elemental_advantage = True

            # Environmental element modifier
            env_mod = self.element_modifiers.get(element, 1.0)
            damage = int(damage * env_mod)

            # Critical hit
            crit_chance = ability.effect.critical_rate + actor.stats.critical_rate
            if actor.has_status(StatusEffect.FOCUSED):
                crit_chance *= 2.0
            if timing == MaTimingResult.PERFECT:
                crit_chance += 0.15

            if random.random() < crit_chance:
                damage = int(damage * 1.75)
                result.critical_hit = True

            # Shielded defense
            if target.has_status(StatusEffect.SHIELDED):
                damage = int(damage * 0.5)

            # Apply damage
            damage = max(1, damage)
            target.stats.current_hp -= damage
            result.damage_dealt[target.id] = damage

            # Apply status effects
            for effect, chance, duration in ability.effect.status_effects:
                if random.random() < chance * ma_multiplier:
                    applied = target.apply_status(effect, duration)
                    if applied:
                        result.statuses_applied.append({
                            "target": target.id,
                            "effect": effect.value,
                            "duration": duration,
                        })

            # Check if target is down
            if target.stats.current_hp <= 0:
                target.is_alive = False

    def _resolve_supportive(self, actor: Combatant, ability: Ability,
                            targets: list[Combatant], result: ActionResult,
                            ma_multiplier: float,
                            timing: MaTimingResult) -> None:
        """Resolve a healing or support action."""
        for target in targets:
            if not target.is_alive:
                continue

            result.targets_hit.append(target.id)

            # Healing (negative damage = healing)
            if ability.effect.damage < 0:
                heal = int(abs(ability.effect.damage) * ma_multiplier)
                if timing == MaTimingResult.PERFECT:
                    heal = int(heal * 1.5)

                target.stats.current_hp = min(
                    target.stats.max_hp,
                    target.stats.current_hp + heal
                )
                result.healing_done[target.id] = heal

            # Apply status effects (buffs)
            for effect, chance, duration in ability.effect.status_effects:
                if random.random() < chance:
                    target.apply_status(effect, duration)
                    result.statuses_applied.append({
                        "target": target.id,
                        "effect": effect.value,
                        "duration": duration,
                    })

            # Apply stat modifiers
            # (In a full implementation, these would be tracked and reverted)

    def _resolve_observation(self, actor: Combatant, ability: Ability,
                             targets: list[Combatant], result: ActionResult,
                             ma_multiplier: float) -> None:
        """Resolve an observation action - revealing bestiary info."""
        for target in targets:
            if not target.is_alive or not target.spirit_id:
                continue

            result.targets_hit.append(target.id)

            reveal = ability.effect.bestiary_reveal * ma_multiplier
            current = self.rewards.bestiary_knowledge.get(target.spirit_id, 0.0)
            self.rewards.bestiary_knowledge[target.spirit_id] = min(
                1.0, current + reveal
            )
            result.bestiary_revealed[target.spirit_id] = reveal

            result.narrative_text += (
                f"You study {target.name} carefully. "
                f"Details emerge from the blur of battle..."
            )

        # Observation generates ma
        if ability.effect.ma_generation > 0:
            self.ma_gauge.charge(ability.effect.ma_generation * ma_multiplier)

    def _resolve_purification(self, actor: Combatant, ability: Ability,
                              targets: list[Combatant], result: ActionResult,
                              ma_multiplier: float,
                              timing: MaTimingResult) -> None:
        """Resolve a purification action against corrupted spirits."""
        for target in targets:
            if not target.is_alive:
                continue

            result.targets_hit.append(target.id)

            # Damage component
            if ability.effect.damage > 0:
                damage = int(ability.effect.damage * ma_multiplier)
                # Purification does bonus damage to corrupted
                if target.is_corrupted:
                    damage = int(damage * 1.5)
                target.stats.current_hp -= damage
                result.damage_dealt[target.id] = damage

            # Purification component
            if target.is_corrupted and ability.effect.purification_power > 0:
                purify = ability.effect.purification_power * ma_multiplier
                if timing == MaTimingResult.PERFECT:
                    purify *= 1.5

                target.corruption_level = max(
                    0.0, target.corruption_level - purify
                )

                if target.corruption_level <= 0.1:
                    # Spirit is purified!
                    target.remove_status(StatusEffect.CORRUPTED)
                    result.narrative_text += (
                        f"\nThe corruption lifts from {target.name} like "
                        f"morning fog. Beneath the darkness, the true spirit "
                        f"emerges - wounded, confused, but free."
                    )
                    self.result = BattleResult.PURIFIED
                    self.rewards.purified_spirit = target.spirit_id
                else:
                    result.narrative_text += (
                        f"\nThe corruption on {target.name} weakens, "
                        f"but does not break. Keep trying."
                    )

            if target.stats.current_hp <= 0:
                target.is_alive = False

    def _resolve_field(self, actor: Combatant, ability: Ability,
                       result: ActionResult, ma_multiplier: float,
                       timing: MaTimingResult) -> None:
        """Resolve a field-affecting ability."""
        all_targets = [c for c in self.all_combatants if c.is_alive]

        # Apply damage to enemies
        for target in all_targets:
            if target in self.enemies and ability.effect.damage > 0:
                damage = int(ability.effect.damage * ma_multiplier * 0.7)
                target.stats.current_hp -= damage
                result.damage_dealt[target.id] = damage
                result.targets_hit.append(target.id)

            # Apply status effects to all
            for effect, chance, duration in ability.effect.status_effects:
                if random.random() < chance:
                    target.apply_status(effect, duration)
                    result.statuses_applied.append({
                        "target": target.id,
                        "effect": effect.value,
                        "duration": duration,
                    })

        # Ma generation
        if ability.effect.ma_generation > 0:
            self.ma_gauge.charge(ability.effect.ma_generation * ma_multiplier)

        result.narrative_text += (
            f"The battlefield itself shifts. The air changes. "
            f"Something fundamental has been altered."
        )

    # -------------------------------------------------------------------
    # Utility methods
    # -------------------------------------------------------------------

    def _get_combatant(self, combatant_id: str) -> Optional[Combatant]:
        return next(
            (c for c in self.all_combatants if c.id == combatant_id), None
        )

    def _resolve_targets(self, target_ids: list[str],
                         target_type: TargetType) -> list[Combatant]:
        """Resolve target IDs into combatant objects."""
        if target_type == TargetType.ALL_ENEMIES:
            return [e for e in self.enemies if e.is_alive]
        elif target_type == TargetType.ALL_ALLIES:
            return [p for p in self.party if p.is_alive]
        elif target_type == TargetType.SELF:
            return [self.current_actor] if self.current_actor else []
        elif target_type == TargetType.FIELD:
            return [c for c in self.all_combatants if c.is_alive]
        else:
            return [
                c for c in self.all_combatants
                if c.id in target_ids and c.is_alive
            ]

    def _calculate_personality_match(self, approach: str,
                                     traits: list[str]) -> float:
        """
        How well does the negotiation approach match the spirit's personality?

        This is a simplified version. In the full game, this would be
        a rich system of emotional keywords, tonal analysis, and
        relationship history.
        """
        if not traits or not approach:
            return 0.3  # Neutral match

        # Simple keyword matching for the prototype
        approach_lower = approach.lower()
        match_count = sum(
            1 for trait in traits if trait.lower() in approach_lower
        )
        return min(1.0, 0.3 + (match_count * 0.2))

    def _check_battle_end(self) -> None:
        """Check if the battle should end."""
        if self.result is not None:
            self.phase = BattlePhase.BATTLE_END
            return

        # All enemies defeated
        if not any(e.is_alive for e in self.enemies):
            self.result = BattleResult.VICTORY
            self.phase = BattlePhase.BATTLE_END
            return

        # All party members defeated
        if not any(p.is_alive for p in self.party):
            self.result = BattleResult.DEFEAT
            self.phase = BattlePhase.BATTLE_END
            return

    # -------------------------------------------------------------------
    # Battle end
    # -------------------------------------------------------------------

    def calculate_rewards(self) -> BattleRewards:
        """
        Calculate rewards based on how the battle ended.

        Befriending and purifying give BETTER rewards than defeating.
        This is by design. Violence is always an option in Ma no Kuni,
        but it is rarely the best one.
        """
        if self.result == BattleResult.BEFRIENDED:
            self.rewards.spirit_essence = sum(
                e.stats.level * 15 for e in self.enemies
            )
            # Bonus for befriending
            self.rewards.spirit_essence = int(
                self.rewards.spirit_essence * 1.5
            )
            for enemy in self.enemies:
                if enemy.spirit_id:
                    self.rewards.bestiary_knowledge[enemy.spirit_id] = min(
                        1.0,
                        self.rewards.bestiary_knowledge.get(
                            enemy.spirit_id, 0.0
                        ) + 0.5
                    )

        elif self.result == BattleResult.PURIFIED:
            self.rewards.spirit_essence = sum(
                e.stats.level * 20 for e in self.enemies
            )
            for enemy in self.enemies:
                if enemy.spirit_id:
                    self.rewards.bestiary_knowledge[enemy.spirit_id] = min(
                        1.0,
                        self.rewards.bestiary_knowledge.get(
                            enemy.spirit_id, 0.0
                        ) + 0.4
                    )
                    self.rewards.lore_fragments.append(
                        f"purification_lore_{enemy.spirit_id}"
                    )

        elif self.result == BattleResult.VICTORY:
            self.rewards.spirit_essence = sum(
                e.stats.level * 10 for e in self.enemies
            )
            # Material drops from defeated enemies
            for enemy in self.enemies:
                for item, chance in enemy.loot_table.items():
                    if random.random() < chance:
                        self.rewards.material_drops.append({
                            "item": item,
                            "source": enemy.id,
                        })

        elif self.result == BattleResult.FLED:
            # Minimal rewards for fleeing
            self.rewards.spirit_essence = sum(
                e.stats.level * 2 for e in self.enemies
            )

        # Ma combo bonus
        if self.ma_gauge.max_combo >= 3:
            self.rewards.spirit_essence = int(
                self.rewards.spirit_essence * (1.0 + self.ma_gauge.max_combo * 0.1)
            )

        return self.rewards

    def get_battle_summary(self) -> dict:
        """Generate a summary of the battle for display."""
        return {
            "result": self.result.name if self.result else "ONGOING",
            "turns": self.turn_count,
            "ma_gauge_peak": self.ma_gauge.maximum,
            "best_ma_combo": self.ma_gauge.max_combo,
            "total_damage_dealt": sum(
                sum(r.damage_dealt.values()) for r in self.action_log
            ),
            "total_healing_done": sum(
                sum(r.healing_done.values()) for r in self.action_log
            ),
            "spirits_befriended": 1 if self.result == BattleResult.BEFRIENDED else 0,
            "spirits_purified": 1 if self.result == BattleResult.PURIFIED else 0,
            "negotiations_attempted": len(self.negotiations),
            "perfect_timings": sum(
                1 for r in self.action_log
                if r.ma_timing_result == MaTimingResult.PERFECT
            ),
            "rewards": self.rewards,
        }


# ---------------------------------------------------------------------------
# Enemy AI
# ---------------------------------------------------------------------------

class SpiritAI:
    """
    AI for spirit combatants.

    Spirits don't fight like video game enemies. They act according
    to their nature. A lonely spirit clings. A proud spirit postures.
    A frightened spirit lashes out. A curious spirit observes.

    The AI selects actions based on personality traits, current HP,
    the player's behavior, and the spirit's emotional state.
    """

    @staticmethod
    def select_action(spirit: Combatant, battle: Battle) -> BattleAction:
        """Choose an action for a spirit combatant."""
        traits = spirit.personality_traits
        hp_ratio = spirit.stats.current_hp / max(1, spirit.stats.max_hp)

        # Corrupted spirits are more aggressive
        if spirit.is_corrupted:
            return SpiritAI._corrupted_behavior(spirit, battle)

        # Low HP behavior
        if hp_ratio < 0.3:
            return SpiritAI._desperate_behavior(spirit, battle, traits)

        # Personality-driven behavior
        if "lonely" in traits or "sad" in traits:
            return SpiritAI._lonely_behavior(spirit, battle)
        elif "trickster" in traits or "playful" in traits:
            return SpiritAI._trickster_behavior(spirit, battle)
        elif "proud" in traits or "aggressive" in traits:
            return SpiritAI._aggressive_behavior(spirit, battle)
        elif "curious" in traits or "observant" in traits:
            return SpiritAI._curious_behavior(spirit, battle)
        elif "protective" in traits or "guardian" in traits:
            return SpiritAI._guardian_behavior(spirit, battle)
        else:
            return SpiritAI._default_behavior(spirit, battle)

    @staticmethod
    def _pick_target(battle: Battle) -> str:
        """Pick a party member to target."""
        alive = [p for p in battle.party if p.is_alive]
        if not alive:
            return ""
        # Tend to target lowest HP
        if random.random() < 0.6:
            target = min(alive, key=lambda p: p.stats.current_hp)
        else:
            target = random.choice(alive)
        return target.id

    @staticmethod
    def _pick_ability(spirit: Combatant,
                      prefer_categories: list[AbilityCategory]
                      ) -> Ability:
        """Pick an ability, preferring certain categories."""
        for category in prefer_categories:
            options = [
                a for a in spirit.abilities
                if a.category == category and a.learned
                and spirit.stats.current_sp >= a.cost.sp
            ]
            if options:
                return random.choice(options)
        # Fallback to basic attack
        return DEFAULT_ABILITIES["basic_attack"]

    @staticmethod
    def _corrupted_behavior(spirit: Combatant,
                            battle: Battle) -> BattleAction:
        """Corrupted spirits attack relentlessly, driven by pain."""
        ability = SpiritAI._pick_ability(
            spirit, [AbilityCategory.ATTACK, AbilityCategory.DEBUFF]
        )
        return BattleAction(
            actor=spirit.id,
            ability=ability,
            targets=[SpiritAI._pick_target(battle)],
            ma_timing=random.uniform(0.1, 0.4),  # Corruption disrupts timing
        )

    @staticmethod
    def _lonely_behavior(spirit: Combatant,
                         battle: Battle) -> BattleAction:
        """Lonely spirits attack weakly, hoping to be noticed."""
        if random.random() < 0.4:
            # Sometimes they just... wait. Hoping.
            return BattleAction(
                actor=spirit.id,
                ability=DEFAULT_ABILITIES["wait"],
                targets=[spirit.id],
                ma_timing=random.uniform(0.5, 0.9),
            )
        ability = SpiritAI._pick_ability(
            spirit, [AbilityCategory.DEBUFF, AbilityCategory.ATTACK]
        )
        return BattleAction(
            actor=spirit.id,
            ability=ability,
            targets=[SpiritAI._pick_target(battle)],
            ma_timing=random.uniform(0.3, 0.6),
        )

    @staticmethod
    def _trickster_behavior(spirit: Combatant,
                            battle: Battle) -> BattleAction:
        """Trickster spirits use debuffs and unpredictable actions."""
        ability = SpiritAI._pick_ability(
            spirit, [AbilityCategory.DEBUFF, AbilityCategory.FIELD,
                     AbilityCategory.ATTACK]
        )
        return BattleAction(
            actor=spirit.id,
            ability=ability,
            targets=[SpiritAI._pick_target(battle)],
            ma_timing=random.uniform(0.4, 0.95),  # Tricksters have good timing
        )

    @staticmethod
    def _aggressive_behavior(spirit: Combatant,
                             battle: Battle) -> BattleAction:
        """Aggressive spirits hit hard and fast."""
        ability = SpiritAI._pick_ability(
            spirit, [AbilityCategory.ATTACK]
        )
        # Target lowest HP for the kill
        alive = [p for p in battle.party if p.is_alive]
        target = min(alive, key=lambda p: p.stats.current_hp) if alive else None
        return BattleAction(
            actor=spirit.id,
            ability=ability,
            targets=[target.id if target else ""],
            ma_timing=random.uniform(0.5, 0.8),
        )

    @staticmethod
    def _curious_behavior(spirit: Combatant,
                          battle: Battle) -> BattleAction:
        """Curious spirits observe more than attack."""
        if random.random() < 0.5:
            return BattleAction(
                actor=spirit.id,
                ability=DEFAULT_ABILITIES["observe"],
                targets=[SpiritAI._pick_target(battle)],
                ma_timing=random.uniform(0.6, 0.95),
            )
        ability = SpiritAI._pick_ability(
            spirit, [AbilityCategory.OBSERVATION, AbilityCategory.DEBUFF,
                     AbilityCategory.ATTACK]
        )
        return BattleAction(
            actor=spirit.id,
            ability=ability,
            targets=[SpiritAI._pick_target(battle)],
            ma_timing=random.uniform(0.5, 0.85),
        )

    @staticmethod
    def _guardian_behavior(spirit: Combatant,
                           battle: Battle) -> BattleAction:
        """Guardian spirits defend and counter."""
        if random.random() < 0.4:
            return BattleAction(
                actor=spirit.id,
                ability=DEFAULT_ABILITIES["defend"],
                targets=[spirit.id],
                ma_timing=random.uniform(0.6, 0.9),
            )
        ability = SpiritAI._pick_ability(
            spirit, [AbilityCategory.ATTACK, AbilityCategory.SUPPORT]
        )
        return BattleAction(
            actor=spirit.id,
            ability=ability,
            targets=[SpiritAI._pick_target(battle)],
            ma_timing=random.uniform(0.5, 0.8),
        )

    @staticmethod
    def _desperate_behavior(spirit: Combatant, battle: Battle,
                            traits: list[str]) -> BattleAction:
        """Low HP behavior - spirits become unpredictable."""
        roll = random.random()
        if roll < 0.3 and "proud" not in traits:
            # Try to flee
            return BattleAction(
                actor=spirit.id,
                ability=DEFAULT_ABILITIES["flee"],
                targets=[spirit.id],
                ma_timing=0.0,
            )
        elif roll < 0.5:
            # Desperate all-out attack
            ability = SpiritAI._pick_ability(
                spirit, [AbilityCategory.ATTACK]
            )
            return BattleAction(
                actor=spirit.id,
                ability=ability,
                targets=[SpiritAI._pick_target(battle)],
                ma_timing=random.uniform(0.6, 1.0),  # Desperation focus
            )
        else:
            return SpiritAI._default_behavior(spirit, battle)

    @staticmethod
    def _default_behavior(spirit: Combatant,
                          battle: Battle) -> BattleAction:
        """Default spirit behavior - balanced approach."""
        ability = SpiritAI._pick_ability(
            spirit, [AbilityCategory.ATTACK, AbilityCategory.DEBUFF]
        )
        return BattleAction(
            actor=spirit.id,
            ability=ability,
            targets=[SpiritAI._pick_target(battle)],
            ma_timing=random.uniform(0.3, 0.7),
        )
