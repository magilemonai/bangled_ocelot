"""
Ma no Kuni - Dialogue System

Conversation in this game is not a menu. It is a living exchange
where silence is as valid as speech, where what you don't say
echoes louder than what you do, and where the spirits whisper
truths at the edges of perception.

The dialogue tree system supports:
- Branching paths with conditions (flags, relationships, ma, time, stats)
- Silence as an explicit, powerful choice (the ma option)
- Emotional tone tracking throughout conversations
- Spirit whispers that appear only when perception is high enough
- Stage directions and atmospheric beats woven into the text
- Memory integration -- past choices surface in future conversations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Optional

from src.characters.relationships import RelationshipAxis


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DialogueTone(Enum):
    """The emotional register of a line or response."""
    NEUTRAL = "neutral"
    GENTLE = "gentle"
    FIRM = "firm"
    WARM = "warm"
    COLD = "cold"
    PLAYFUL = "playful"
    SAD = "sad"
    ANGRY = "angry"
    CURIOUS = "curious"
    CRYPTIC = "cryptic"
    VULNERABLE = "vulnerable"
    HOPEFUL = "hopeful"
    RESIGNED = "resigned"
    SILENCE = "silence"         # The ma tone


class SpeakerType(Enum):
    """Who or what is speaking."""
    NPC = "npc"
    PLAYER = "player"
    NARRATOR = "narrator"
    SPIRIT_WHISPER = "spirit_whisper"
    INTERNAL = "internal"       # Aoi's inner thoughts
    ENVIRONMENT = "environment" # The world speaking


class DialogueEffect(Enum):
    """What a dialogue choice causes in the game world."""
    SET_FLAG = "set_flag"
    CLEAR_FLAG = "clear_flag"
    MODIFY_RELATIONSHIP = "modify_relationship"
    MODIFY_EMOTION = "modify_emotion"
    MODIFY_STAT = "modify_stat"
    GIVE_ITEM = "give_item"
    TAKE_ITEM = "take_item"
    RECORD_MEMORY = "record_memory"
    TRIGGER_EVENT = "trigger_event"
    START_QUEST = "start_quest"
    ADVANCE_QUEST = "advance_quest"
    MODIFY_MA = "modify_ma"
    SPIRIT_SIGHT_XP = "spirit_sight_xp"
    CHANGE_NPC_MOOD = "change_npc_mood"
    CHANGE_NPC_SCHEDULE = "change_npc_schedule"


# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------

class ConditionType(Enum):
    """Types of conditions that gate dialogue options."""
    FLAG = "flag"
    FLAG_NOT_SET = "flag_not_set"
    RELATIONSHIP_MIN = "relationship_min"
    RELATIONSHIP_MAX = "relationship_max"
    MA_MIN = "ma_min"
    MA_MAX = "ma_max"
    TIME_OF_DAY = "time_of_day"
    STAT_MIN = "stat_min"
    HAS_ITEM = "has_item"
    EMOTION = "emotion"
    MEMORY = "memory"
    SPIRIT_SIGHT_LEVEL = "spirit_sight_level"
    SPIRIT_SIGHT_ACTIVE = "spirit_sight_active"
    NPC_MOOD = "npc_mood"
    QUEST_STATE = "quest_state"
    RELATIONSHIP_PHASE = "relationship_phase"
    CUSTOM = "custom"


@dataclass
class DialogueCondition:
    """
    A single condition that must be met for a dialogue node or
    option to be available.
    """
    condition_type: ConditionType
    parameters: dict[str, Any] = field(default_factory=dict)

    def evaluate(self, context: DialogueContext) -> bool:
        """Evaluate this condition against the current game context."""
        ct = self.condition_type
        p = self.parameters

        if ct == ConditionType.FLAG:
            return context.flags.get(p.get("flag", ""), False)

        if ct == ConditionType.FLAG_NOT_SET:
            return not context.flags.get(p.get("flag", ""), False)

        if ct == ConditionType.RELATIONSHIP_MIN:
            axis = RelationshipAxis(p.get("axis", "trust"))
            value = context.relationship_values.get(axis, 0.0)
            return value >= p.get("minimum", 0.0)

        if ct == ConditionType.RELATIONSHIP_MAX:
            axis = RelationshipAxis(p.get("axis", "trust"))
            value = context.relationship_values.get(axis, 0.0)
            return value <= p.get("maximum", 1.0)

        if ct == ConditionType.MA_MIN:
            return context.ma_level >= p.get("minimum", 0.0)

        if ct == ConditionType.MA_MAX:
            return context.ma_level <= p.get("maximum", 100.0)

        if ct == ConditionType.TIME_OF_DAY:
            allowed = p.get("times", [])
            return context.time_of_day in allowed

        if ct == ConditionType.STAT_MIN:
            stat_value = context.stats.get(p.get("stat", ""), 0)
            return stat_value >= p.get("minimum", 0)

        if ct == ConditionType.HAS_ITEM:
            return p.get("item_id", "") in context.inventory_ids

        if ct == ConditionType.EMOTION:
            return context.emotional_state == p.get("emotion", "")

        if ct == ConditionType.MEMORY:
            return p.get("memory_id", "") in context.memory_ids

        if ct == ConditionType.SPIRIT_SIGHT_LEVEL:
            return context.spirit_sight_level >= p.get("minimum", 0)

        if ct == ConditionType.SPIRIT_SIGHT_ACTIVE:
            return context.spirit_sight_active == p.get("active", True)

        if ct == ConditionType.NPC_MOOD:
            return context.npc_mood == p.get("mood", "")

        if ct == ConditionType.QUEST_STATE:
            quest_id = p.get("quest_id", "")
            expected = p.get("state", "")
            return context.quest_states.get(quest_id, "") == expected

        if ct == ConditionType.RELATIONSHIP_PHASE:
            return context.relationship_phase == p.get("phase", "")

        if ct == ConditionType.CUSTOM:
            callback = p.get("callback")
            if callable(callback):
                return callback(context)
            return False

        return True


# ---------------------------------------------------------------------------
# Context -- the game state snapshot used for dialogue evaluation
# ---------------------------------------------------------------------------

@dataclass
class DialogueContext:
    """
    A snapshot of the game state relevant to dialogue evaluation.
    Assembled by the game engine before entering a conversation.
    """
    # Story state
    flags: dict[str, bool] = field(default_factory=dict)

    # Relationship with current speaker
    relationship_values: dict[RelationshipAxis, float] = field(default_factory=dict)
    relationship_phase: str = "strangers"

    # Player state
    ma_level: float = 0.0
    time_of_day: str = "morning"
    stats: dict[str, int] = field(default_factory=dict)
    inventory_ids: set[str] = field(default_factory=set)
    emotional_state: str = "calm"
    memory_ids: set[str] = field(default_factory=set)
    spirit_sight_level: int = 0
    spirit_sight_active: bool = False

    # NPC state
    npc_id: str = ""
    npc_mood: str = "neutral"

    # Quest state
    quest_states: dict[str, str] = field(default_factory=dict)

    # Current conversation state
    conversation_tone: DialogueTone = DialogueTone.NEUTRAL
    lines_spoken: int = 0
    silences_chosen: int = 0


# ---------------------------------------------------------------------------
# Dialogue tree nodes
# ---------------------------------------------------------------------------

@dataclass
class EffectDefinition:
    """A single effect that fires when a dialogue choice is made."""
    effect_type: DialogueEffect
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class SpiritWhisper:
    """
    A whisper from the spirit world that appears alongside normal
    dialogue when the player's perception or spirit sight is high enough.

    These are not spoken by the NPC. They are something else --
    fragments of truth bleeding through the veil.
    """
    text: str
    conditions: list[DialogueCondition] = field(default_factory=list)
    tone: DialogueTone = DialogueTone.CRYPTIC

    def is_visible(self, context: DialogueContext) -> bool:
        return all(c.evaluate(context) for c in self.conditions)


@dataclass
class StageDirection:
    """
    Non-spoken beats in a conversation -- gestures, pauses,
    environmental details. These create the rhythm of ma.
    """
    text: str
    pause_duration: float = 0.0   # Seconds of pause after this direction
    conditions: list[DialogueCondition] = field(default_factory=list)

    def is_visible(self, context: DialogueContext) -> bool:
        if not self.conditions:
            return True
        return all(c.evaluate(context) for c in self.conditions)


@dataclass
class DialogueLine:
    """
    A single line of dialogue with its metadata.
    """
    speaker: str                  # NPC id, "aoi", "narrator", etc.
    speaker_type: SpeakerType
    text: str
    tone: DialogueTone = DialogueTone.NEUTRAL
    stage_direction: Optional[StageDirection] = None
    spirit_whisper: Optional[SpiritWhisper] = None
    pause_after: float = 0.0     # Seconds of silence after this line
    conditions: list[DialogueCondition] = field(default_factory=list)

    def is_available(self, context: DialogueContext) -> bool:
        if not self.conditions:
            return True
        return all(c.evaluate(context) for c in self.conditions)


@dataclass
class DialogueChoice:
    """
    A single response option available to the player.
    May be text, silence, or an action.
    """
    id: str
    text: str                     # What the player sees (empty for silence)
    display_text: str = ""        # Optional different display text
    tone: DialogueTone = DialogueTone.NEUTRAL
    is_silence: bool = False      # The ma choice
    conditions: list[DialogueCondition] = field(default_factory=list)
    effects: list[EffectDefinition] = field(default_factory=list)
    next_node_id: str = ""        # Which node to go to after this choice
    stage_direction: Optional[StageDirection] = None
    tooltip: str = ""             # Hint about what this choice might do

    def is_available(self, context: DialogueContext) -> bool:
        if not self.conditions:
            return True
        return all(c.evaluate(context) for c in self.conditions)


@dataclass
class DialogueNode:
    """
    A single node in a dialogue tree. Contains one or more lines
    spoken by an NPC (or narrator), followed by player choices.
    """
    id: str
    lines: list[DialogueLine] = field(default_factory=list)
    choices: list[DialogueChoice] = field(default_factory=list)
    conditions: list[DialogueCondition] = field(default_factory=list)
    effects_on_enter: list[EffectDefinition] = field(default_factory=list)
    is_terminal: bool = False     # Conversation ends after this node
    auto_advance: Optional[str] = None  # Auto-advance to this node (no choices)

    def get_visible_lines(self, context: DialogueContext) -> list[DialogueLine]:
        return [line for line in self.lines if line.is_available(context)]

    def get_available_choices(self, context: DialogueContext) -> list[DialogueChoice]:
        return [choice for choice in self.choices if choice.is_available(context)]

    def is_available(self, context: DialogueContext) -> bool:
        if not self.conditions:
            return True
        return all(c.evaluate(context) for c in self.conditions)


@dataclass
class DialogueTree:
    """
    A complete dialogue tree -- a conversation from beginning to
    possible endings. Trees are identified by ID and associated
    with specific NPCs and situations.
    """
    id: str
    npc_id: str
    title: str = ""               # Internal reference name
    description: str = ""         # What triggers this conversation
    entry_node_id: str = ""       # Where the conversation starts
    nodes: dict[str, DialogueNode] = field(default_factory=dict)
    conditions: list[DialogueCondition] = field(default_factory=list)
    priority: int = 0             # Higher priority trees override lower ones
    one_shot: bool = False        # Can only be triggered once
    has_been_triggered: bool = False
    tags: set[str] = field(default_factory=set)

    def add_node(self, node: DialogueNode) -> None:
        self.nodes[node.id] = node
        if not self.entry_node_id:
            self.entry_node_id = node.id

    def get_node(self, node_id: str) -> Optional[DialogueNode]:
        return self.nodes.get(node_id)

    def is_available(self, context: DialogueContext) -> bool:
        if self.one_shot and self.has_been_triggered:
            return False
        if not self.conditions:
            return True
        return all(c.evaluate(context) for c in self.conditions)


# ---------------------------------------------------------------------------
# Dialogue manager
# ---------------------------------------------------------------------------

@dataclass
class ConversationState:
    """Tracks the state of an active conversation."""
    tree_id: str
    current_node_id: str
    npc_id: str
    context: DialogueContext
    history: list[tuple[str, str]] = field(default_factory=list)  # (speaker, text)
    silences: int = 0
    tone_history: list[DialogueTone] = field(default_factory=list)
    is_active: bool = True

    @property
    def dominant_tone(self) -> DialogueTone:
        """What tone has dominated this conversation?"""
        if not self.tone_history:
            return DialogueTone.NEUTRAL
        tone_counts: dict[DialogueTone, int] = {}
        for tone in self.tone_history:
            tone_counts[tone] = tone_counts.get(tone, 0) + 1
        return max(tone_counts, key=lambda t: tone_counts[t])


class DialogueManager:
    """
    The conductor of conversations. Manages dialogue trees,
    evaluates conditions, applies effects, and maintains
    conversation state.
    """

    def __init__(self) -> None:
        self._trees: dict[str, DialogueTree] = {}
        self._active_conversation: Optional[ConversationState] = None
        self._effect_handlers: dict[DialogueEffect, Callable] = {}

    def register_tree(self, tree: DialogueTree) -> None:
        self._trees[tree.id] = tree

    def register_trees(self, trees: list[DialogueTree]) -> None:
        for tree in trees:
            self.register_tree(tree)

    def register_effect_handler(
        self, effect_type: DialogueEffect, handler: Callable
    ) -> None:
        """
        Register a callback that handles a specific effect type.
        The handler receives (effect_parameters: dict, context: DialogueContext).
        """
        self._effect_handlers[effect_type] = handler

    def get_available_trees(
        self, npc_id: str, context: DialogueContext
    ) -> list[DialogueTree]:
        """Get all dialogue trees available for an NPC given current context."""
        available = [
            tree for tree in self._trees.values()
            if tree.npc_id == npc_id and tree.is_available(context)
        ]
        return sorted(available, key=lambda t: t.priority, reverse=True)

    def start_conversation(
        self, tree_id: str, context: DialogueContext
    ) -> Optional[ConversationState]:
        """
        Begin a conversation. Returns the initial state.
        """
        tree = self._trees.get(tree_id)
        if not tree or not tree.is_available(context):
            return None

        entry = tree.get_node(tree.entry_node_id)
        if not entry:
            return None

        tree.has_been_triggered = True

        self._active_conversation = ConversationState(
            tree_id=tree_id,
            current_node_id=tree.entry_node_id,
            npc_id=tree.npc_id,
            context=context,
        )

        # Apply entry effects
        self._apply_effects(entry.effects_on_enter, context)

        return self._active_conversation

    def get_current_lines(self) -> list[DialogueLine]:
        """Get the lines for the current dialogue node."""
        if not self._active_conversation:
            return []
        tree = self._trees.get(self._active_conversation.tree_id)
        if not tree:
            return []
        node = tree.get_node(self._active_conversation.current_node_id)
        if not node:
            return []
        return node.get_visible_lines(self._active_conversation.context)

    def get_current_choices(self) -> list[DialogueChoice]:
        """Get available choices for the current node."""
        if not self._active_conversation:
            return []
        tree = self._trees.get(self._active_conversation.tree_id)
        if not tree:
            return []
        node = tree.get_node(self._active_conversation.current_node_id)
        if not node:
            return []

        choices = node.get_available_choices(self._active_conversation.context)

        # If the node auto-advances, there are no choices
        if node.auto_advance:
            return []

        return choices

    def make_choice(self, choice_id: str) -> Optional[DialogueNode]:
        """
        Process a player's dialogue choice.
        Returns the next dialogue node, or None if conversation ends.
        """
        if not self._active_conversation:
            return None

        tree = self._trees.get(self._active_conversation.tree_id)
        if not tree:
            return None

        node = tree.get_node(self._active_conversation.current_node_id)
        if not node:
            return None

        # Find the chosen option
        choice = None
        for c in node.choices:
            if c.id == choice_id:
                choice = c
                break

        if not choice:
            return None

        # Record in history
        conv = self._active_conversation
        if choice.is_silence:
            conv.silences += 1
            conv.history.append(("aoi", "[silence]"))
            conv.tone_history.append(DialogueTone.SILENCE)
        else:
            conv.history.append(("aoi", choice.text))
            conv.tone_history.append(choice.tone)

        conv.context.lines_spoken += 1
        if choice.is_silence:
            conv.context.silences_chosen += 1

        # Apply effects
        self._apply_effects(choice.effects, conv.context)

        # Advance to next node
        if not choice.next_node_id:
            conv.is_active = False
            return None

        next_node = tree.get_node(choice.next_node_id)
        if not next_node or next_node.is_terminal:
            conv.is_active = False
            if next_node:
                self._apply_effects(next_node.effects_on_enter, conv.context)
            return next_node

        conv.current_node_id = choice.next_node_id
        self._apply_effects(next_node.effects_on_enter, conv.context)

        return next_node

    def advance_auto(self) -> Optional[DialogueNode]:
        """
        Advance through an auto-advance node.
        Returns the next node.
        """
        if not self._active_conversation:
            return None

        tree = self._trees.get(self._active_conversation.tree_id)
        if not tree:
            return None

        node = tree.get_node(self._active_conversation.current_node_id)
        if not node or not node.auto_advance:
            return None

        next_node = tree.get_node(node.auto_advance)
        if not next_node:
            self._active_conversation.is_active = False
            return None

        self._active_conversation.current_node_id = node.auto_advance
        self._apply_effects(next_node.effects_on_enter, self._active_conversation.context)

        if next_node.is_terminal:
            self._active_conversation.is_active = False

        return next_node

    def end_conversation(self) -> Optional[ConversationState]:
        """End the current conversation and return its final state."""
        if not self._active_conversation:
            return None
        final_state = self._active_conversation
        final_state.is_active = False
        self._active_conversation = None
        return final_state

    @property
    def is_in_conversation(self) -> bool:
        return self._active_conversation is not None and self._active_conversation.is_active

    @property
    def active_conversation(self) -> Optional[ConversationState]:
        return self._active_conversation

    def _apply_effects(
        self, effects: list[EffectDefinition], context: DialogueContext
    ) -> None:
        """Apply a list of effects through registered handlers."""
        for effect in effects:
            handler = self._effect_handlers.get(effect.effect_type)
            if handler:
                handler(effect.parameters, context)


# ---------------------------------------------------------------------------
# YAML dialogue loader
# ---------------------------------------------------------------------------

def _parse_condition(data: dict) -> DialogueCondition:
    """Parse a condition from YAML data."""
    ctype = ConditionType(data.get("type", "flag"))
    params = {k: v for k, v in data.items() if k != "type"}
    return DialogueCondition(condition_type=ctype, parameters=params)


def _safe_tone(value: str) -> DialogueTone:
    """Parse a tone string, falling back to NEUTRAL for unknown values."""
    try:
        return DialogueTone(value)
    except ValueError:
        return DialogueTone.NEUTRAL


def _parse_effect(data: dict) -> EffectDefinition:
    """Parse an effect from YAML data."""
    etype = DialogueEffect(data.get("type", "set_flag"))
    params = {k: v for k, v in data.items() if k != "type"}
    return EffectDefinition(effect_type=etype, parameters=params)


def _parse_spirit_whisper(data: dict) -> SpiritWhisper:
    """Parse a spirit whisper from YAML data."""
    conditions = [_parse_condition(c) for c in data.get("conditions", [])]
    return SpiritWhisper(
        text=data.get("text", ""),
        conditions=conditions,
        tone=_safe_tone(data.get("tone", "cryptic")),
    )


def _parse_stage_direction(data: dict) -> StageDirection:
    """Parse a stage direction from YAML data."""
    conditions = [_parse_condition(c) for c in data.get("conditions", [])]
    return StageDirection(
        text=data.get("text", ""),
        pause_duration=data.get("pause", 0.0),
        conditions=conditions,
    )


def _parse_line(data: dict) -> DialogueLine:
    """Parse a dialogue line from YAML data."""
    whisper = None
    if "spirit_whisper" in data:
        whisper = _parse_spirit_whisper(data["spirit_whisper"])

    direction = None
    if "stage_direction" in data:
        direction = _parse_stage_direction(data["stage_direction"])

    conditions = [_parse_condition(c) for c in data.get("conditions", [])]

    return DialogueLine(
        speaker=data.get("speaker", ""),
        speaker_type=SpeakerType(data.get("speaker_type", "npc")),
        text=data.get("text", ""),
        tone=_safe_tone(data.get("tone", "neutral")),
        stage_direction=direction,
        spirit_whisper=whisper,
        pause_after=data.get("pause_after", 0.0),
        conditions=conditions,
    )


def _parse_choice(data: dict) -> DialogueChoice:
    """Parse a dialogue choice from YAML data."""
    conditions = [_parse_condition(c) for c in data.get("conditions", [])]
    effects = [_parse_effect(e) for e in data.get("effects", [])]

    direction = None
    if "stage_direction" in data:
        direction = _parse_stage_direction(data["stage_direction"])

    return DialogueChoice(
        id=data.get("id", ""),
        text=data.get("text", ""),
        display_text=data.get("display_text", ""),
        tone=_safe_tone(data.get("tone", "neutral")),
        is_silence=data.get("is_silence", False),
        conditions=conditions,
        effects=effects,
        next_node_id=data.get("next_node", ""),
        stage_direction=direction,
        tooltip=data.get("tooltip", ""),
    )


def _parse_node(data: dict) -> DialogueNode:
    """Parse a dialogue node from YAML data."""
    lines = [_parse_line(l) for l in data.get("lines", [])]
    choices = [_parse_choice(c) for c in data.get("choices", [])]
    conditions = [_parse_condition(c) for c in data.get("conditions", [])]
    effects = [_parse_effect(e) for e in data.get("effects_on_enter", [])]

    return DialogueNode(
        id=data.get("id", ""),
        lines=lines,
        choices=choices,
        conditions=conditions,
        effects_on_enter=effects,
        is_terminal=data.get("is_terminal", False),
        auto_advance=data.get("auto_advance"),
    )


def load_dialogue_trees_from_yaml(yaml_data: dict) -> list[DialogueTree]:
    """
    Parse dialogue trees from a YAML data dictionary.
    Expected structure:
      dialogue_trees:
        - id: tree_id
          npc_id: npc_id
          ...
          nodes:
            - id: node_id
              lines: [...]
              choices: [...]
    """
    trees: list[DialogueTree] = []
    for tree_data in yaml_data.get("dialogue_trees", []):
        conditions = [_parse_condition(c) for c in tree_data.get("conditions", [])]
        nodes = {
            n["id"]: _parse_node(n) for n in tree_data.get("nodes", [])
        }

        tree = DialogueTree(
            id=tree_data.get("id", ""),
            npc_id=tree_data.get("npc_id", ""),
            title=tree_data.get("title", ""),
            description=tree_data.get("description", ""),
            entry_node_id=tree_data.get("entry_node", ""),
            nodes=nodes,
            conditions=conditions,
            priority=tree_data.get("priority", 0),
            one_shot=tree_data.get("one_shot", False),
            tags=set(tree_data.get("tags", [])),
        )
        trees.append(tree)

    return trees
