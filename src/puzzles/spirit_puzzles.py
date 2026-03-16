"""
Ma no Kuni - Spirit-Specific Puzzle Types

Puzzles that arise from the nature of spirits themselves:
    - Dual-Layer: two worlds, one problem
    - Empathy: what does the spirit truly need?
    - Memory: the past is alive in spirit memory
    - Resonance: tune the harmony between realms
    - Calligraphy: draw meaning with intention

Spirits are not obstacles. They are beings with their own logic, their own
grief, their own joy. To solve a spirit puzzle is to understand a life.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..engine.game import MaState, SpiritTide, WorldClock

from .puzzle_engine import (
    BasePuzzle,
    HintTier,
    PuzzleAction,
    PuzzleCategory,
    PuzzleConditions,
    PuzzleDifficulty,
    PuzzleHint,
    PuzzleReward,
    PuzzleSolution,
    PuzzleStatus,
    SolutionType,
    WorldLayer,
)


# ===================================================================
# Dual-Layer Puzzle
# ===================================================================

@dataclass
class LayerObject:
    """An object that exists in one or both world layers."""
    object_id: str
    name: str
    layer: WorldLayer
    position: tuple[float, float] = (0.0, 0.0)
    properties: dict[str, Any] = field(default_factory=dict)
    linked_object_id: Optional[str] = None  # Counterpart in the other layer
    movable: bool = True
    interactable: bool = True


@dataclass
class LayerLink:
    """
    A causal link between objects in different layers.
    Moving the material object affects the spirit object, and vice versa.
    """
    material_object_id: str
    spirit_object_id: str
    link_type: str = "mirror"  # mirror, inverse, delayed, conditional
    transform: dict[str, Any] = field(default_factory=dict)
    bidirectional: bool = True


class DualLayerPuzzle(BasePuzzle):
    """
    The player must manipulate objects in BOTH the material and spirit world
    simultaneously. A bench moved in the material world unblocks a spirit path.
    A lantern lit in the spirit world reveals hidden text in the material world.

    The player switches between layers (or uses spirit vision to see both)
    and must reason about cross-layer causality.
    """

    def __init__(
        self,
        puzzle_id: str,
        name: str,
        description: str,
        location: str,
        district: str,
        conditions: PuzzleConditions,
        solutions: list[PuzzleSolution],
        hints: list[PuzzleHint],
        reward: PuzzleReward,
        material_objects: list[LayerObject],
        spirit_objects: list[LayerObject],
        layer_links: list[LayerLink],
        goal_state: dict[str, dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        super().__init__(
            puzzle_id=puzzle_id,
            name=name,
            description=description,
            category=PuzzleCategory.DUAL_LAYER,
            difficulty=kwargs.pop("difficulty", PuzzleDifficulty.DEEP),
            location=location,
            district=district,
            conditions=conditions,
            solutions=solutions,
            hints=hints,
            reward=reward,
            **kwargs,
        )
        self.material_objects = {obj.object_id: obj for obj in material_objects}
        self.spirit_objects = {obj.object_id: obj for obj in spirit_objects}
        self.layer_links = layer_links
        self.goal_state = goal_state  # {object_id: {property: value}}
        self.current_layer: WorldLayer = WorldLayer.MATERIAL

    def on_reset(self) -> None:
        # Restore original positions from state snapshot if available
        pass

    def evaluate_action(
        self,
        action: PuzzleAction,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> dict[str, Any]:
        events: list[dict[str, Any]] = []

        if action.action_type == "switch_layer":
            new_layer = WorldLayer(action.parameters.get("layer", "material"))
            self.current_layer = new_layer
            return {
                "accepted": True,
                "feedback": f"You shift your perception to the {new_layer.value} world.",
                "solved": False,
                "solution": None,
                "events": [],
            }

        if action.action_type == "move_object":
            return self._handle_move(action, events)

        if action.action_type == "interact":
            return self._handle_interact(action, events)

        return {
            "accepted": False,
            "feedback": "That action has no effect here.",
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _get_objects_for_layer(
        self, layer: WorldLayer
    ) -> dict[str, LayerObject]:
        if layer == WorldLayer.MATERIAL:
            return self.material_objects
        return self.spirit_objects

    def _handle_move(
        self, action: PuzzleAction, events: list[dict[str, Any]]
    ) -> dict[str, Any]:
        target_id = action.target
        new_pos = action.parameters.get("position", (0.0, 0.0))

        objects = self._get_objects_for_layer(action.layer)
        obj = objects.get(target_id)
        if obj is None or not obj.movable:
            return {
                "accepted": False,
                "feedback": "Nothing to move there.",
                "solved": False,
                "solution": None,
                "events": events,
            }

        old_pos = obj.position
        obj.position = tuple(new_pos)

        # Propagate through layer links
        cross_effects = self._propagate_links(target_id, action.layer, events)

        feedback = f"You move the {obj.name}."
        if cross_effects:
            feedback += f" Something shifts in the other world..."

        return {
            "accepted": True,
            "feedback": feedback,
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_interact(
        self, action: PuzzleAction, events: list[dict[str, Any]]
    ) -> dict[str, Any]:
        target_id = action.target
        interaction = action.parameters.get("interaction", "use")

        objects = self._get_objects_for_layer(action.layer)
        obj = objects.get(target_id)
        if obj is None or not obj.interactable:
            return {
                "accepted": False,
                "feedback": "Nothing responds.",
                "solved": False,
                "solution": None,
                "events": events,
            }

        obj.properties[interaction] = True
        cross_effects = self._propagate_links(target_id, action.layer, events)

        feedback = f"You {interaction} the {obj.name}."
        if cross_effects:
            feedback += " A resonance ripples across the veil..."

        return {
            "accepted": True,
            "feedback": feedback,
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _propagate_links(
        self,
        object_id: str,
        source_layer: WorldLayer,
        events: list[dict[str, Any]],
    ) -> list[str]:
        """Propagate changes through layer links. Returns list of affected object ids."""
        affected: list[str] = []
        for link in self.layer_links:
            source_id = (
                link.material_object_id
                if source_layer == WorldLayer.MATERIAL
                else link.spirit_object_id
            )
            target_id = (
                link.spirit_object_id
                if source_layer == WorldLayer.MATERIAL
                else link.material_object_id
            )

            if source_id != object_id:
                continue
            if not link.bidirectional and source_layer == WorldLayer.SPIRIT:
                continue

            target_objects = self._get_objects_for_layer(
                WorldLayer.SPIRIT
                if source_layer == WorldLayer.MATERIAL
                else WorldLayer.MATERIAL
            )
            target_obj = target_objects.get(target_id)
            if target_obj is None:
                continue

            source_objects = self._get_objects_for_layer(source_layer)
            source_obj = source_objects.get(source_id)
            if source_obj is None:
                continue

            if link.link_type == "mirror":
                target_obj.position = source_obj.position
                target_obj.properties.update(source_obj.properties)
            elif link.link_type == "inverse":
                x, y = source_obj.position
                target_obj.position = (-x, -y)
            elif link.link_type == "conditional":
                condition_key = link.transform.get("condition_key", "")
                if source_obj.properties.get(condition_key, False):
                    for k, v in link.transform.get("apply", {}).items():
                        target_obj.properties[k] = v

            affected.append(target_id)
            events.append({
                "type": "cross_layer_effect",
                "source": source_id,
                "target": target_id,
                "link_type": link.link_type,
            })

        return affected

    def is_solution_met(
        self,
        solution: PuzzleSolution,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> bool:
        all_objects = {**self.material_objects, **self.spirit_objects}
        for obj_id, required_props in self.goal_state.items():
            obj = all_objects.get(obj_id)
            if obj is None:
                return False
            for key, value in required_props.items():
                if key == "position":
                    # Fuzzy position matching
                    ox, oy = obj.position
                    vx, vy = value
                    if abs(ox - vx) > 0.5 or abs(oy - vy) > 0.5:
                        return False
                elif obj.properties.get(key) != value:
                    return False
        return True


# ===================================================================
# Empathy Puzzle
# ===================================================================

@dataclass
class SpiritEmotion:
    """A spirit's emotional state and what it truly needs."""
    name: str
    surface_need: str           # What the spirit seems to want
    true_need: str              # What the spirit actually needs
    current_trust: float = 0.0  # -1.0 (hostile) to 1.0 (complete trust)
    emotional_state: str = "guarded"
    memory_fragments: list[str] = field(default_factory=list)
    dialogue_keys: dict[str, str] = field(default_factory=dict)
    trust_thresholds: dict[float, str] = field(default_factory=dict)


class EmpathyPuzzle(BasePuzzle):
    """
    Understanding a spirit's emotional state to help them. The 'solution'
    is not mechanical but emotional. A crying lantern spirit does not need
    to be lit - it needs to be told it is okay to go dark. A vending machine
    spirit overwhelmed by choices needs help choosing one drink to be.

    Wrong approaches (trying the obvious) do not fail - they simply do not
    resonate. The spirit remains unmoved. Only genuine understanding works.
    """

    def __init__(
        self,
        puzzle_id: str,
        name: str,
        description: str,
        location: str,
        district: str,
        conditions: PuzzleConditions,
        solutions: list[PuzzleSolution],
        hints: list[PuzzleHint],
        reward: PuzzleReward,
        spirit_emotion: SpiritEmotion,
        dialogue_tree: dict[str, dict[str, Any]],
        trust_actions: dict[str, float],
        distrust_actions: dict[str, float],
        **kwargs: Any,
    ) -> None:
        super().__init__(
            puzzle_id=puzzle_id,
            name=name,
            description=description,
            category=PuzzleCategory.EMPATHY,
            difficulty=kwargs.pop("difficulty", PuzzleDifficulty.DEEP),
            location=location,
            district=district,
            conditions=conditions,
            solutions=solutions,
            hints=hints,
            reward=reward,
            **kwargs,
        )
        self.spirit_emotion = spirit_emotion
        self.dialogue_tree = dialogue_tree
        self.trust_actions = trust_actions      # {action: trust_delta}
        self.distrust_actions = distrust_actions
        self.current_dialogue_node: str = "root"

    def on_reset(self) -> None:
        self.spirit_emotion.current_trust = 0.0
        self.spirit_emotion.emotional_state = "guarded"
        self.current_dialogue_node = "root"

    def evaluate_action(
        self,
        action: PuzzleAction,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> dict[str, Any]:
        events: list[dict[str, Any]] = []

        if action.action_type == "speak":
            return self._handle_dialogue(action, ma, events)
        if action.action_type == "offer_item":
            return self._handle_offering(action, events)
        if action.action_type == "gesture":
            return self._handle_gesture(action, ma, events)
        if action.action_type == "wait":
            return self._handle_patience(action, ma, events)

        return {
            "accepted": True,
            "feedback": "The spirit watches you, unmoved.",
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_dialogue(
        self,
        action: PuzzleAction,
        ma: MaState,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        choice = action.parameters.get("choice", "")
        node = self.dialogue_tree.get(self.current_dialogue_node, {})
        options = node.get("options", {})

        if choice not in options:
            return {
                "accepted": True,
                "feedback": "The spirit tilts its head, uncomprehending.",
                "solved": False,
                "solution": None,
                "events": events,
            }

        option_data = options[choice]
        response_text = option_data.get("response", "...")
        trust_change = option_data.get("trust", 0.0)
        next_node = option_data.get("next", self.current_dialogue_node)
        new_emotion = option_data.get("emotion", None)

        # Ma level affects empathy. High ma makes trust gains stronger
        if trust_change > 0 and ma.can_hear_whispers:
            trust_change *= 1.5

        self.spirit_emotion.current_trust = max(
            -1.0, min(1.0, self.spirit_emotion.current_trust + trust_change)
        )
        self.current_dialogue_node = next_node

        if new_emotion:
            self.spirit_emotion.emotional_state = new_emotion
            events.append({
                "type": "spirit_emotion_changed",
                "spirit": self.spirit_emotion.name,
                "emotion": new_emotion,
            })

        # Check trust thresholds
        for threshold, event_name in self.spirit_emotion.trust_thresholds.items():
            if (
                self.spirit_emotion.current_trust >= threshold
                and event_name not in [e.get("threshold") for e in events]
            ):
                events.append({
                    "type": "trust_threshold_crossed",
                    "spirit": self.spirit_emotion.name,
                    "threshold": event_name,
                })

        return {
            "accepted": True,
            "feedback": response_text,
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_offering(
        self,
        action: PuzzleAction,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        item = action.parameters.get("item", "")
        trust_delta = self.trust_actions.get(f"offer_{item}", 0.0)
        distrust_delta = self.distrust_actions.get(f"offer_{item}", 0.0)

        total_delta = trust_delta + distrust_delta
        self.spirit_emotion.current_trust = max(
            -1.0, min(1.0, self.spirit_emotion.current_trust + total_delta)
        )

        if total_delta > 0:
            feedback = f"The spirit regards your offering of {item} with interest."
        elif total_delta < 0:
            feedback = f"The spirit recoils. The {item} was not what it needed."
        else:
            feedback = f"The spirit ignores the {item}."

        return {
            "accepted": True,
            "feedback": feedback,
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_gesture(
        self,
        action: PuzzleAction,
        ma: MaState,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        gesture = action.parameters.get("gesture", "")
        trust_delta = self.trust_actions.get(f"gesture_{gesture}", 0.0)

        # Gestures are more effective with high ma
        if ma.can_see_visions:
            trust_delta *= 1.3

        self.spirit_emotion.current_trust = max(
            -1.0, min(1.0, self.spirit_emotion.current_trust + trust_delta)
        )

        responses = {
            "bow": "You bow respectfully. The spirit's tension eases slightly.",
            "sit": "You sit down beside it. No rush. No demands.",
            "cry": "You let yourself feel. The spirit watches, startled by the honesty.",
            "smile": "You smile gently. The spirit's glow flickers - confusion? Hope?",
            "turn_away": "You turn your back, trusting. A dangerous gift.",
        }
        feedback = responses.get(
            gesture, "The spirit watches your gesture with ancient eyes."
        )

        return {
            "accepted": True,
            "feedback": feedback,
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_patience(
        self,
        action: PuzzleAction,
        ma: MaState,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Waiting - doing nothing - is sometimes the most empathetic act."""
        wait_seconds = action.parameters.get("duration", 0.0)
        trust_delta = 0.05 * (wait_seconds / 10.0)
        if ma.can_hear_whispers:
            trust_delta *= 2.0

        self.spirit_emotion.current_trust = max(
            -1.0, min(1.0, self.spirit_emotion.current_trust + trust_delta)
        )

        if self.spirit_emotion.current_trust > 0.5:
            feedback = "In the silence between you, something softens."
        elif self.spirit_emotion.current_trust > 0.0:
            feedback = "You wait. The spirit watches you wait. Time stretches."
        else:
            feedback = "You stand in silence. The spirit endures your presence."

        return {
            "accepted": True,
            "feedback": feedback,
            "solved": False,
            "solution": None,
            "events": events,
        }

    def is_solution_met(
        self,
        solution: PuzzleSolution,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> bool:
        # Empathy puzzles are solved when trust reaches the required threshold
        required_trust = 0.8  # Default high trust
        if solution.solution_type == SolutionType.CREATIVE:
            required_trust = 0.6  # Creative solutions need less raw trust
        if solution.solution_type == SolutionType.MA_REVEALED:
            required_trust = 0.5  # Ma-based solutions bypass some barriers

        if self.spirit_emotion.current_trust < required_trust:
            return False

        # Check that we're at the right dialogue node for this solution
        required_node = None
        for act in solution.required_actions:
            if act.startswith("at_node:"):
                required_node = act.split(":", 1)[1]
                break
        if required_node and self.current_dialogue_node != required_node:
            return False

        return True


# ===================================================================
# Memory Puzzle
# ===================================================================

@dataclass
class MemoryFragment:
    """
    A fragment of a spirit's memory. Spirits remember the past, and a location
    puzzle might require reconstructing how a place looked decades ago.
    """
    fragment_id: str
    description: str
    era: str                    # "1960s", "edo_period", "last_summer", etc.
    visual_key: str             # Key for the rendering system
    position: tuple[float, float] = (0.0, 0.0)
    correct_position: tuple[float, float] = (0.0, 0.0)
    rotation: float = 0.0
    correct_rotation: float = 0.0
    placed: bool = False
    locked: bool = False        # Locked fragments cannot be moved once placed correctly
    discovery_hint: str = ""    # Where/how to find this fragment
    emotional_resonance: str = ""  # What emotion this fragment carries


class MemoryPuzzle(BasePuzzle):
    """
    Spirits remember the past. A demolished building's spirit still holds
    every brick in its memory. To help it, reconstruct what was.

    The player finds memory fragments scattered through the world and must
    place them correctly to rebuild a spirit's memory of a place, a person,
    or a moment. Fragments shimmer with emotional resonance - placing them
    triggers vignettes of the past.
    """

    def __init__(
        self,
        puzzle_id: str,
        name: str,
        description: str,
        location: str,
        district: str,
        conditions: PuzzleConditions,
        solutions: list[PuzzleSolution],
        hints: list[PuzzleHint],
        reward: PuzzleReward,
        fragments: list[MemoryFragment],
        completion_threshold: float = 1.0,
        era: str = "",
        spirit_name: str = "",
        memory_narrative: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            puzzle_id=puzzle_id,
            name=name,
            description=description,
            category=PuzzleCategory.MEMORY,
            difficulty=kwargs.pop("difficulty", PuzzleDifficulty.MODERATE),
            location=location,
            district=district,
            conditions=conditions,
            solutions=solutions,
            hints=hints,
            reward=reward,
            **kwargs,
        )
        self.fragments = {f.fragment_id: f for f in fragments}
        self.completion_threshold = completion_threshold  # 0.0-1.0, how much is needed
        self.era = era
        self.spirit_name = spirit_name
        self.memory_narrative = memory_narrative

    def on_reset(self) -> None:
        for frag in self.fragments.values():
            frag.placed = False
            frag.locked = False
            frag.position = (0.0, 0.0)
            frag.rotation = 0.0

    def evaluate_action(
        self,
        action: PuzzleAction,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> dict[str, Any]:
        events: list[dict[str, Any]] = []

        if action.action_type == "place_fragment":
            return self._handle_place(action, ma, events)
        if action.action_type == "rotate_fragment":
            return self._handle_rotate(action, events)
        if action.action_type == "examine_fragment":
            return self._handle_examine(action, ma, events)

        return {
            "accepted": False,
            "feedback": "The memory shimmers, waiting.",
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_place(
        self,
        action: PuzzleAction,
        ma: MaState,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        frag_id = action.target
        frag = self.fragments.get(frag_id)
        if frag is None:
            return {
                "accepted": False,
                "feedback": "That memory fragment does not exist.",
                "solved": False,
                "solution": None,
                "events": events,
            }
        if frag.locked:
            return {
                "accepted": False,
                "feedback": "This memory has already found its place.",
                "solved": False,
                "solution": None,
                "events": events,
            }

        position = tuple(action.parameters.get("position", (0.0, 0.0)))
        frag.position = position
        frag.placed = True

        # Check if correctly placed (with tolerance)
        cx, cy = frag.correct_position
        px, py = position
        distance = math.sqrt((cx - px) ** 2 + (cy - py) ** 2)
        position_tolerance = 1.5 if ma.can_see_visions else 1.0

        rotation_diff = abs(frag.rotation - frag.correct_rotation) % 360
        rotation_ok = rotation_diff < 15.0

        if distance <= position_tolerance and rotation_ok:
            frag.locked = True
            events.append({
                "type": "memory_fragment_locked",
                "fragment_id": frag_id,
                "era": self.era,
                "resonance": frag.emotional_resonance,
            })
            feedback = (
                f"The {frag.description} slides into place. "
                f"A flash of the past: {frag.emotional_resonance}"
            )
        else:
            feedback = f"You place the {frag.description}, but it does not quite fit."
            if distance <= position_tolerance * 2:
                feedback += " It trembles - close, but not right."

        return {
            "accepted": True,
            "feedback": feedback,
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_rotate(
        self,
        action: PuzzleAction,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        frag_id = action.target
        frag = self.fragments.get(frag_id)
        if frag is None or frag.locked:
            return {
                "accepted": False,
                "feedback": "Nothing to rotate.",
                "solved": False,
                "solution": None,
                "events": events,
            }

        angle = action.parameters.get("angle", 0.0)
        frag.rotation = (frag.rotation + angle) % 360

        return {
            "accepted": True,
            "feedback": f"You turn the {frag.description}. The light catches it differently.",
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_examine(
        self,
        action: PuzzleAction,
        ma: MaState,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        frag_id = action.target
        frag = self.fragments.get(frag_id)
        if frag is None:
            return {
                "accepted": False,
                "feedback": "Nothing to examine.",
                "solved": False,
                "solution": None,
                "events": events,
            }

        feedback = f"{frag.description} - from the {frag.era}."
        if ma.can_access_memories and frag.emotional_resonance:
            feedback += f" You feel: {frag.emotional_resonance}"
        if ma.can_see_visions and frag.discovery_hint:
            feedback += f" A vision whispers: {frag.discovery_hint}"

        return {
            "accepted": True,
            "feedback": feedback,
            "solved": False,
            "solution": None,
            "events": events,
        }

    @property
    def completion_ratio(self) -> float:
        """How much of the memory has been reconstructed."""
        total = len(self.fragments)
        if total == 0:
            return 0.0
        locked = sum(1 for f in self.fragments.values() if f.locked)
        return locked / total

    def is_solution_met(
        self,
        solution: PuzzleSolution,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> bool:
        return self.completion_ratio >= self.completion_threshold


# ===================================================================
# Resonance Puzzle
# ===================================================================

@dataclass
class ResonanceElement:
    """An element that contributes to the resonance frequency."""
    element_id: str
    name: str
    element_type: str           # "sound", "light", "object", "scent"
    current_frequency: float = 0.0
    target_frequency: float = 1.0
    tolerance: float = 0.1      # How close is close enough
    adjustable: bool = True
    layer: WorldLayer = WorldLayer.MATERIAL


class ResonancePuzzle(BasePuzzle):
    """
    Match spirit frequencies by arranging objects, playing sounds, or aligning
    elements. Like tuning an instrument - the player must feel the harmony
    between worlds.

    Each element has a frequency. The goal is to bring all elements into
    harmony (matching target frequencies within tolerance). Elements in
    different layers may interfere with each other - the spirit world's
    resonance can amplify or dampen the material world's.
    """

    def __init__(
        self,
        puzzle_id: str,
        name: str,
        description: str,
        location: str,
        district: str,
        conditions: PuzzleConditions,
        solutions: list[PuzzleSolution],
        hints: list[PuzzleHint],
        reward: PuzzleReward,
        elements: list[ResonanceElement],
        harmony_threshold: float = 0.85,
        interference_rules: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            puzzle_id=puzzle_id,
            name=name,
            description=description,
            category=PuzzleCategory.RESONANCE,
            difficulty=kwargs.pop("difficulty", PuzzleDifficulty.MODERATE),
            location=location,
            district=district,
            conditions=conditions,
            solutions=solutions,
            hints=hints,
            reward=reward,
            **kwargs,
        )
        self.elements = {e.element_id: e for e in elements}
        self.harmony_threshold = harmony_threshold
        self.interference_rules = interference_rules or []

    def on_reset(self) -> None:
        for elem in self.elements.values():
            elem.current_frequency = 0.0

    def evaluate_action(
        self,
        action: PuzzleAction,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> dict[str, Any]:
        events: list[dict[str, Any]] = []

        if action.action_type == "tune":
            return self._handle_tune(action, events)
        if action.action_type == "strike":
            return self._handle_strike(action, ma, events)
        if action.action_type == "listen":
            return self._handle_listen(action, ma, events)

        return {
            "accepted": False,
            "feedback": "The resonance remains unchanged.",
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_tune(
        self,
        action: PuzzleAction,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        elem_id = action.target
        elem = self.elements.get(elem_id)
        if elem is None or not elem.adjustable:
            return {
                "accepted": False,
                "feedback": "Nothing to tune.",
                "solved": False,
                "solution": None,
                "events": events,
            }

        adjustment = action.parameters.get("adjustment", 0.0)
        elem.current_frequency += adjustment
        self._apply_interference()

        harmony = self.current_harmony
        if harmony > 0.9:
            feedback = "The resonance sings. Almost perfect harmony."
        elif harmony > 0.6:
            feedback = "The elements hum in near-accord. Close."
        elif harmony > 0.3:
            feedback = "A rough harmony emerges, fighting against dissonance."
        else:
            feedback = "Dissonance grates against the space between worlds."

        return {
            "accepted": True,
            "feedback": feedback,
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_strike(
        self,
        action: PuzzleAction,
        ma: MaState,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Strike an element to hear its current frequency."""
        elem_id = action.target
        elem = self.elements.get(elem_id)
        if elem is None:
            return {
                "accepted": False,
                "feedback": "Nothing resonates.",
                "solved": False,
                "solution": None,
                "events": events,
            }

        diff = abs(elem.current_frequency - elem.target_frequency)
        if diff <= elem.tolerance:
            feedback = f"The {elem.name} rings true. It is in harmony."
        elif diff < elem.tolerance * 3:
            direction = "higher" if elem.current_frequency < elem.target_frequency else "lower"
            feedback = f"The {elem.name} rings slightly off. It wants to go {direction}."
        else:
            feedback = f"The {elem.name} produces a harsh, discordant tone."

        # With high ma, the player can feel the exact dissonance
        if ma.can_hear_whispers:
            feedback += f" You sense its frequency: {elem.current_frequency:.2f}."

        return {
            "accepted": True,
            "feedback": feedback,
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_listen(
        self,
        action: PuzzleAction,
        ma: MaState,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Listen to the overall harmony."""
        harmony = self.current_harmony
        feedback = f"Overall harmony: {harmony:.0%}."
        if ma.can_see_visions:
            # Reveal which elements are most off
            worst = max(
                self.elements.values(),
                key=lambda e: abs(e.current_frequency - e.target_frequency),
            )
            feedback += f" The {worst.name} is most discordant."

        return {
            "accepted": True,
            "feedback": feedback,
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _apply_interference(self) -> None:
        """Apply interference rules between elements."""
        for rule in self.interference_rules:
            source_id = rule.get("source")
            target_id = rule.get("target")
            mode = rule.get("mode", "additive")
            factor = rule.get("factor", 0.1)

            source = self.elements.get(source_id)
            target = self.elements.get(target_id)
            if source is None or target is None:
                continue

            if mode == "additive":
                target.current_frequency += source.current_frequency * factor
            elif mode == "dampen":
                target.current_frequency *= (1.0 - factor)

    @property
    def current_harmony(self) -> float:
        """Calculate overall harmony (0.0 to 1.0)."""
        if not self.elements:
            return 0.0
        scores: list[float] = []
        for elem in self.elements.values():
            diff = abs(elem.current_frequency - elem.target_frequency)
            score = max(0.0, 1.0 - (diff / max(elem.tolerance * 5, 0.01)))
            scores.append(score)
        return sum(scores) / len(scores)

    def is_solution_met(
        self,
        solution: PuzzleSolution,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> bool:
        return self.current_harmony >= self.harmony_threshold


# ===================================================================
# Calligraphy Puzzle
# ===================================================================

@dataclass
class StrokeData:
    """A single brush stroke in a calligraphy attempt."""
    points: list[tuple[float, float]] = field(default_factory=list)
    pressure: list[float] = field(default_factory=list)
    speed: list[float] = field(default_factory=list)
    timestamp: float = 0.0


@dataclass
class KanjiTemplate:
    """A kanji or spiritual symbol to be drawn."""
    symbol_id: str
    kanji: str                  # The actual character, e.g. "間"
    meaning: str
    stroke_order: list[list[tuple[float, float]]] = field(default_factory=list)
    stroke_count: int = 0
    spiritual_effect: str = ""  # What happens when drawn correctly
    anger_effect: str = ""      # What happens when drawn with anger
    peace_effect: str = ""      # What happens when drawn with peace
    accuracy_threshold: float = 0.7


class CalligraphyPuzzle(BasePuzzle):
    """
    Draw kanji or spiritual symbols to create effects. The accuracy AND
    the intention matter - the same symbol drawn in anger vs. peace has
    different effects.

    Intention is derived from stroke speed, pressure variation, and rhythm.
    Fast, hard strokes = anger. Slow, even strokes = peace. The game reads
    the player's emotional state through their drawing.
    """

    def __init__(
        self,
        puzzle_id: str,
        name: str,
        description: str,
        location: str,
        district: str,
        conditions: PuzzleConditions,
        solutions: list[PuzzleSolution],
        hints: list[PuzzleHint],
        reward: PuzzleReward,
        target_kanji: KanjiTemplate,
        required_intention: str = "peace",
        allow_multiple_intentions: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            puzzle_id=puzzle_id,
            name=name,
            description=description,
            category=PuzzleCategory.CALLIGRAPHY,
            difficulty=kwargs.pop("difficulty", PuzzleDifficulty.MODERATE),
            location=location,
            district=district,
            conditions=conditions,
            solutions=solutions,
            hints=hints,
            reward=reward,
            **kwargs,
        )
        self.target_kanji = target_kanji
        self.required_intention = required_intention
        self.allow_multiple_intentions = allow_multiple_intentions
        self.current_strokes: list[StrokeData] = []
        self.last_accuracy: float = 0.0
        self.last_intention: str = "neutral"

    def on_reset(self) -> None:
        self.current_strokes.clear()
        self.last_accuracy = 0.0
        self.last_intention = "neutral"

    def evaluate_action(
        self,
        action: PuzzleAction,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> dict[str, Any]:
        events: list[dict[str, Any]] = []

        if action.action_type == "draw_stroke":
            return self._handle_stroke(action, events)
        if action.action_type == "complete_drawing":
            return self._handle_complete(action, ma, tide, events)
        if action.action_type == "clear_canvas":
            self.current_strokes.clear()
            return {
                "accepted": True,
                "feedback": "The ink fades. The surface is clean.",
                "solved": False,
                "solution": None,
                "events": events,
            }

        return {
            "accepted": False,
            "feedback": "The brush waits.",
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_stroke(
        self,
        action: PuzzleAction,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        points = action.parameters.get("points", [])
        pressure = action.parameters.get("pressure", [])
        speed = action.parameters.get("speed", [])

        stroke = StrokeData(
            points=[tuple(p) for p in points],
            pressure=pressure,
            speed=speed,
            timestamp=action.timestamp,
        )
        self.current_strokes.append(stroke)

        stroke_num = len(self.current_strokes)
        expected = self.target_kanji.stroke_count

        if stroke_num < expected:
            feedback = f"Stroke {stroke_num} of {expected}. The ink flows."
        elif stroke_num == expected:
            feedback = "The final stroke. The character awaits completion."
        else:
            feedback = "Extra strokes cloud the meaning."

        return {
            "accepted": True,
            "feedback": feedback,
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_complete(
        self,
        action: PuzzleAction,
        ma: MaState,
        tide: SpiritTide,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        accuracy = self._calculate_accuracy()
        intention = self._read_intention()
        self.last_accuracy = accuracy
        self.last_intention = intention

        events.append({
            "type": "calligraphy_completed",
            "kanji": self.target_kanji.kanji,
            "meaning": self.target_kanji.meaning,
            "accuracy": accuracy,
            "intention": intention,
        })

        if accuracy < self.target_kanji.accuracy_threshold:
            feedback = (
                f"The character '{self.target_kanji.kanji}' ({self.target_kanji.meaning}) "
                f"is recognisable but imprecise. The spirits cannot read it clearly."
            )
        elif intention == "anger" and self.target_kanji.anger_effect:
            feedback = (
                f"'{self.target_kanji.kanji}' blazes with frustrated energy. "
                f"{self.target_kanji.anger_effect}"
            )
        elif intention == "peace" and self.target_kanji.peace_effect:
            feedback = (
                f"'{self.target_kanji.kanji}' glows with serene power. "
                f"{self.target_kanji.peace_effect}"
            )
        else:
            feedback = (
                f"'{self.target_kanji.kanji}' takes form. "
                f"{self.target_kanji.spiritual_effect}"
            )

        return {
            "accepted": True,
            "feedback": feedback,
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _calculate_accuracy(self) -> float:
        """
        Compare drawn strokes against the template. Returns 0.0-1.0.
        In a full implementation this would use stroke recognition algorithms.
        Here we use stroke count matching and basic shape comparison.
        """
        if not self.current_strokes:
            return 0.0

        expected_count = self.target_kanji.stroke_count
        actual_count = len(self.current_strokes)

        # Stroke count accuracy
        count_score = 1.0 - abs(expected_count - actual_count) / max(expected_count, 1)
        count_score = max(0.0, count_score)

        # Stroke shape accuracy (simplified - compare against template paths)
        shape_scores: list[float] = []
        template_strokes = self.target_kanji.stroke_order
        for i, stroke in enumerate(self.current_strokes):
            if i < len(template_strokes) and stroke.points and template_strokes[i]:
                # Simple bounding-box overlap as a proxy for shape matching
                drawn_xs = [p[0] for p in stroke.points]
                drawn_ys = [p[1] for p in stroke.points]
                tmpl_xs = [p[0] for p in template_strokes[i]]
                tmpl_ys = [p[1] for p in template_strokes[i]]

                if drawn_xs and tmpl_xs and drawn_ys and tmpl_ys:
                    x_overlap = max(
                        0.0,
                        min(max(drawn_xs), max(tmpl_xs))
                        - max(min(drawn_xs), min(tmpl_xs)),
                    )
                    y_overlap = max(
                        0.0,
                        min(max(drawn_ys), max(tmpl_ys))
                        - max(min(drawn_ys), min(tmpl_ys)),
                    )
                    tmpl_width = max(tmpl_xs) - min(tmpl_xs) or 1.0
                    tmpl_height = max(tmpl_ys) - min(tmpl_ys) or 1.0
                    shape_scores.append(
                        min(1.0, (x_overlap / tmpl_width + y_overlap / tmpl_height) / 2)
                    )
                else:
                    shape_scores.append(0.5)
            else:
                shape_scores.append(0.0)

        shape_score = sum(shape_scores) / max(len(shape_scores), 1)
        return count_score * 0.4 + shape_score * 0.6

    def _read_intention(self) -> str:
        """
        Derive the drawer's intention from stroke characteristics.
        Fast + high pressure = anger.  Slow + even pressure = peace.
        """
        if not self.current_strokes:
            return "neutral"

        all_speeds: list[float] = []
        all_pressures: list[float] = []
        for stroke in self.current_strokes:
            all_speeds.extend(stroke.speed)
            all_pressures.extend(stroke.pressure)

        if not all_speeds or not all_pressures:
            return "neutral"

        avg_speed = sum(all_speeds) / len(all_speeds)
        avg_pressure = sum(all_pressures) / len(all_pressures)
        pressure_variance = sum(
            (p - avg_pressure) ** 2 for p in all_pressures
        ) / len(all_pressures)

        # High speed + high pressure variance = anger
        if avg_speed > 0.7 and pressure_variance > 0.1:
            return "anger"
        # Low speed + low pressure variance = peace
        if avg_speed < 0.4 and pressure_variance < 0.05:
            return "peace"
        return "neutral"

    def is_solution_met(
        self,
        solution: PuzzleSolution,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> bool:
        if self.last_accuracy < self.target_kanji.accuracy_threshold:
            return False

        # Check intention requirement
        if self.required_intention == "any" or self.allow_multiple_intentions:
            return True
        return self.last_intention == self.required_intention
