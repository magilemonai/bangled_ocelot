"""
Ma no Kuni - Environmental & World Puzzles

Puzzles that arise from Tokyo itself - the city as a living, breathing entity
whose geography warps under spirit influence:
    - Ma (Silence/Timing): the answer is to wait, to do nothing
    - Urban Navigation: the spirit world bends Tokyo's streets and rails

These puzzles are woven into the world. They are not rooms you enter but
realities you inhabit. The city remembers. The silence speaks. The train
that loops through 1987 runs on schedule.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

from ..engine.game import MaState, Season, SpiritTide, TimeOfDay, WorldClock

from .puzzle_engine import (
    BasePuzzle,
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
# Ma (Silence / Timing) Puzzle
# ===================================================================

class MaPhase(Enum):
    """The phases of a ma puzzle's silence cycle."""
    DORMANT = auto()       # Nothing has happened yet
    BUILDING = auto()      # Something is accumulating (sound, light, presence)
    PEAK = auto()          # The moment just before the silence
    SILENCE = auto()       # The ma window - where inaction is the answer
    FADING = auto()        # The window is closing
    PASSED = auto()        # The window closed; cycle restarts or puzzle resets


@dataclass
class SilenceWindow:
    """
    A window of time during which the correct action is inaction.
    The player must recognise the moment and simply... be.
    """
    window_id: str
    trigger_event: str          # What starts the buildup ("bell_rings", "light_fades")
    buildup_duration: float     # Seconds of buildup before silence
    silence_duration: float     # Seconds the silence window is open
    fade_duration: float        # Seconds of grace after the window
    required_stillness: float   # How still the player must be (0.0-1.0)
    description: str = ""
    success_text: str = ""
    failure_text: str = ""


class MaSilencePuzzle(BasePuzzle):
    """
    Puzzles that require the player to WAIT. To do nothing at the right
    moment. Counter-intuitive: the solution is inaction.

    A door that only opens when you stand still for exactly the right
    duration. A spirit that only speaks in the silence after a sound fades.
    A path that only appears when you stop looking for it.

    The puzzle tracks player movement and input. During the 'silence window',
    any action resets the cycle. Only perfect stillness succeeds.
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
        silence_windows: list[SilenceWindow],
        cycle_count: int = 1,
        windows_required: int = 0,
        allows_partial: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            puzzle_id=puzzle_id,
            name=name,
            description=description,
            category=PuzzleCategory.MA_SILENCE,
            difficulty=kwargs.pop("difficulty", PuzzleDifficulty.DEEP),
            location=location,
            district=district,
            conditions=conditions,
            solutions=solutions,
            hints=hints,
            reward=reward,
            **kwargs,
        )
        self.silence_windows = {w.window_id: w for w in silence_windows}
        self.cycle_count = cycle_count
        self.windows_required = windows_required or len(silence_windows)
        self.allows_partial = allows_partial

        # Runtime state
        self.current_phase: MaPhase = MaPhase.DORMANT
        self.phase_timer: float = 0.0
        self.active_window_id: Optional[str] = None
        self.player_stillness: float = 1.0  # 1.0 = perfectly still
        self.windows_completed: set[str] = set()
        self.cycles_completed: int = 0
        self.last_movement_time: float = 0.0

    def on_reset(self) -> None:
        self.current_phase = MaPhase.DORMANT
        self.phase_timer = 0.0
        self.active_window_id = None
        self.player_stillness = 1.0
        self.windows_completed.clear()
        self.cycles_completed = 0

    def evaluate_action(
        self,
        action: PuzzleAction,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> dict[str, Any]:
        events: list[dict[str, Any]] = []

        if action.action_type == "trigger":
            return self._handle_trigger(action, events)

        if action.action_type in ("move", "interact", "speak", "use_item"):
            return self._handle_activity(action, events)

        if action.action_type == "wait":
            return self._handle_wait(action, ma, events)

        return {
            "accepted": True,
            "feedback": "...",
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_trigger(
        self,
        action: PuzzleAction,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Player triggers the event that begins a silence cycle."""
        trigger = action.parameters.get("event", "")
        for wid, window in self.silence_windows.items():
            if window.trigger_event == trigger and wid not in self.windows_completed:
                self.active_window_id = wid
                self.current_phase = MaPhase.BUILDING
                self.phase_timer = 0.0
                events.append({
                    "type": "ma_cycle_started",
                    "window_id": wid,
                    "trigger": trigger,
                })
                return {
                    "accepted": True,
                    "feedback": f"{window.description} The air changes.",
                    "solved": False,
                    "solution": None,
                    "events": events,
                }

        return {
            "accepted": True,
            "feedback": "Nothing responds to that.",
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_activity(
        self,
        action: PuzzleAction,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Any activity during the silence window disrupts it."""
        self.last_movement_time = time.time()

        if self.current_phase == MaPhase.SILENCE:
            window = self.silence_windows.get(self.active_window_id or "")
            self.current_phase = MaPhase.PASSED
            events.append({
                "type": "silence_broken",
                "window_id": self.active_window_id,
            })
            failure_text = (
                window.failure_text if window
                else "The moment shatters like glass."
            )
            return {
                "accepted": True,
                "feedback": failure_text,
                "solved": False,
                "solution": None,
                "events": events,
            }

        if self.current_phase == MaPhase.BUILDING:
            # Activity during buildup is fine - it's before the silence
            self.player_stillness = max(0.0, self.player_stillness - 0.1)
            return {
                "accepted": True,
                "feedback": "You move. Something watches your restlessness.",
                "solved": False,
                "solution": None,
                "events": events,
            }

        return {
            "accepted": True,
            "feedback": "",
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_wait(
        self,
        action: PuzzleAction,
        ma: MaState,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Player explicitly waits - the core mechanic of ma puzzles."""
        duration = action.parameters.get("duration", 1.0)

        # Waiting restores stillness
        self.player_stillness = min(1.0, self.player_stillness + duration * 0.2)

        # Waiting during silence phase is how you solve it
        if self.current_phase == MaPhase.SILENCE:
            window = self.silence_windows.get(self.active_window_id or "")
            if window and self.player_stillness >= window.required_stillness:
                # Accumulate ma while being still
                ma.accumulate(duration * 5.0, "ma_puzzle_silence")
                return {
                    "accepted": True,
                    "feedback": "Stillness. The silence holds you like water.",
                    "solved": False,
                    "solution": None,
                    "events": events,
                }
            return {
                "accepted": True,
                "feedback": "You try to be still, but echoes of your movement linger.",
                "solved": False,
                "solution": None,
                "events": events,
            }

        if self.current_phase == MaPhase.DORMANT:
            return {
                "accepted": True,
                "feedback": "You wait. The world waits with you. But for what?",
                "solved": False,
                "solution": None,
                "events": events,
            }

        return {
            "accepted": True,
            "feedback": "You wait...",
            "solved": False,
            "solution": None,
            "events": events,
        }

    def on_update(
        self,
        delta: float,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Drive the silence cycle forward each tick."""
        events: list[dict[str, Any]] = []

        if self.active_window_id is None:
            return events

        window = self.silence_windows.get(self.active_window_id)
        if window is None:
            return events

        self.phase_timer += delta

        if self.current_phase == MaPhase.BUILDING:
            if self.phase_timer >= window.buildup_duration:
                self.current_phase = MaPhase.PEAK
                self.phase_timer = 0.0
                events.append({
                    "type": "ma_phase_change",
                    "phase": "peak",
                    "window_id": self.active_window_id,
                })

        elif self.current_phase == MaPhase.PEAK:
            # Peak is instantaneous - transition to silence
            self.current_phase = MaPhase.SILENCE
            self.phase_timer = 0.0
            events.append({
                "type": "ma_phase_change",
                "phase": "silence",
                "window_id": self.active_window_id,
            })

        elif self.current_phase == MaPhase.SILENCE:
            if self.phase_timer >= window.silence_duration:
                # Player held still through the entire silence window
                if self.player_stillness >= window.required_stillness:
                    self.windows_completed.add(self.active_window_id)
                    events.append({
                        "type": "silence_window_completed",
                        "window_id": self.active_window_id,
                    })
                    feedback = window.success_text or "The silence speaks."
                    events.append({
                        "type": "puzzle_feedback",
                        "text": feedback,
                    })
                self.current_phase = MaPhase.FADING
                self.phase_timer = 0.0

        elif self.current_phase == MaPhase.FADING:
            if self.phase_timer >= window.fade_duration:
                self.current_phase = MaPhase.PASSED
                self.phase_timer = 0.0
                self.active_window_id = None
                self.cycles_completed += 1

        elif self.current_phase == MaPhase.PASSED:
            # Reset for next cycle
            self.current_phase = MaPhase.DORMANT
            self.phase_timer = 0.0
            self.player_stillness = 1.0

        return events

    def is_solution_met(
        self,
        solution: PuzzleSolution,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> bool:
        return len(self.windows_completed) >= self.windows_required


# ===================================================================
# Urban Navigation Puzzle
# ===================================================================

class NavigationAnomaly(Enum):
    """Types of spatial distortion the spirit world creates."""
    LOOP = "loop"               # Path loops back on itself
    FOLD = "fold"               # Two distant points become adjacent
    INVERSION = "inversion"     # Up is down, left is right
    TEMPORAL = "temporal"       # Path goes through a different time
    LAYERED = "layered"         # Path exists in both layers simultaneously
    PHANTOM = "phantom"         # Path only exists in spirit vision
    CONDITIONAL = "conditional" # Path appears only under certain conditions


@dataclass
class NavigationNode:
    """A node in the spirit-warped navigation graph."""
    node_id: str
    name: str
    description: str
    position: tuple[float, float] = (0.0, 0.0)
    layer: WorldLayer = WorldLayer.MATERIAL
    is_destination: bool = False
    requires_spirit_vision: bool = False
    time_period: Optional[str] = None  # If temporal, what era
    arrival_text: str = ""
    spirit_signs: list[str] = field(default_factory=list)  # Clues visible in spirit world


@dataclass
class NavigationEdge:
    """A connection between navigation nodes, possibly warped."""
    edge_id: str
    from_node: str
    to_node: str
    anomaly: NavigationAnomaly = NavigationAnomaly.FOLD
    description: str = ""
    traversal_cost: float = 1.0
    bidirectional: bool = True
    requires_layer: Optional[WorldLayer] = None
    requires_time: list[TimeOfDay] = field(default_factory=list)
    requires_season: list[Season] = field(default_factory=list)
    requires_permeability: float = 0.0
    requires_flags: list[str] = field(default_factory=list)
    spirit_sign_hint: str = ""  # What spirit signs reveal about this edge

    def is_traversable(
        self,
        clock: WorldClock,
        current_layer: WorldLayer,
        permeability: float,
        flags: dict[str, Any],
    ) -> bool:
        """Check if this edge can currently be traversed."""
        if self.requires_layer and current_layer != self.requires_layer:
            return False
        if self.requires_time and clock.time_of_day not in self.requires_time:
            return False
        if self.requires_season and clock.season not in self.requires_season:
            return False
        if permeability < self.requires_permeability:
            return False
        if not all(flags.get(f, False) for f in self.requires_flags):
            return False
        return True


class UrbanNavigationPuzzle(BasePuzzle):
    """
    The spirit world warps Tokyo's geography. Stairs go sideways. Train lines
    loop through time. Finding the right path requires reading spirit signs
    and understanding the anomalies.

    The puzzle is a navigation graph where edges may be warped, conditional,
    or invisible. The player must find a path from start to destination by
    reading spirit signs, switching layers, and understanding the spatial logic.
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
        nodes: list[NavigationNode],
        edges: list[NavigationEdge],
        start_node: str,
        optimal_path_length: int = 0,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            puzzle_id=puzzle_id,
            name=name,
            description=description,
            category=PuzzleCategory.URBAN_NAVIGATION,
            difficulty=kwargs.pop("difficulty", PuzzleDifficulty.DEEP),
            location=location,
            district=district,
            conditions=conditions,
            solutions=solutions,
            hints=hints,
            reward=reward,
            transforms_with_world=True,
            **kwargs,
        )
        self.nodes = {n.node_id: n for n in nodes}
        self.edges = edges
        self.start_node = start_node
        self.current_node_id: str = start_node
        self.current_layer: WorldLayer = WorldLayer.MATERIAL
        self.path_taken: list[str] = [start_node]
        self.optimal_path_length = optimal_path_length or len(nodes)
        self.spirit_signs_read: set[str] = set()

    def on_reset(self) -> None:
        self.current_node_id = self.start_node
        self.current_layer = WorldLayer.MATERIAL
        self.path_taken = [self.start_node]
        self.spirit_signs_read.clear()

    def evaluate_action(
        self,
        action: PuzzleAction,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> dict[str, Any]:
        events: list[dict[str, Any]] = []

        if action.action_type == "move_to":
            return self._handle_move(action, clock, tide, flags, events)
        if action.action_type == "switch_layer":
            return self._handle_layer_switch(action, events)
        if action.action_type == "read_sign":
            return self._handle_read_sign(action, ma, events)
        if action.action_type == "look_around":
            return self._handle_look(action, clock, ma, tide, flags, events)

        return {
            "accepted": False,
            "feedback": "The warped streets offer no response to that.",
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_move(
        self,
        action: PuzzleAction,
        clock: WorldClock,
        tide: SpiritTide,
        flags: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        target_node_id = action.target
        target_node = self.nodes.get(target_node_id)
        if target_node is None:
            return {
                "accepted": False,
                "feedback": "That place does not exist - or does not exist yet.",
                "solved": False,
                "solution": None,
                "events": events,
            }

        # Find a valid edge
        permeability = clock.spirit_permeability
        valid_edge: Optional[NavigationEdge] = None
        for edge in self.edges:
            from_ok = edge.from_node == self.current_node_id
            to_ok = edge.to_node == target_node_id
            reverse_ok = (
                edge.bidirectional
                and edge.from_node == target_node_id
                and edge.to_node == self.current_node_id
            )
            if (from_ok and to_ok) or reverse_ok:
                if edge.is_traversable(clock, self.current_layer, permeability, flags):
                    valid_edge = edge
                    break

        if valid_edge is None:
            return {
                "accepted": False,
                "feedback": "There is no path from here to there. Not in this layer. Not at this hour.",
                "solved": False,
                "solution": None,
                "events": events,
            }

        # Traverse
        self.current_node_id = target_node_id
        self.path_taken.append(target_node_id)

        # Handle anomaly effects
        anomaly_feedback = self._describe_anomaly(valid_edge)
        arrival_text = target_node.arrival_text or f"You arrive at {target_node.name}."

        events.append({
            "type": "navigation_traversal",
            "from": self.path_taken[-2] if len(self.path_taken) >= 2 else None,
            "to": target_node_id,
            "anomaly": valid_edge.anomaly.value,
            "edge_id": valid_edge.edge_id,
        })

        if target_node.is_destination:
            events.append({
                "type": "destination_reached",
                "node_id": target_node_id,
                "path_length": len(self.path_taken),
            })

        feedback = f"{anomaly_feedback} {arrival_text}"
        return {
            "accepted": True,
            "feedback": feedback.strip(),
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_layer_switch(
        self,
        action: PuzzleAction,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        new_layer = WorldLayer(action.parameters.get("layer", "material"))
        old_layer = self.current_layer
        self.current_layer = new_layer

        current_node = self.nodes.get(self.current_node_id)
        node_name = current_node.name if current_node else "this place"

        if new_layer == WorldLayer.SPIRIT:
            feedback = (
                f"The spirit world bleeds through. {node_name} shimmers and "
                f"reshapes itself. New paths appear where walls once stood."
            )
        else:
            feedback = (
                f"The material world reasserts itself. {node_name} solidifies. "
                f"Some paths vanish; others reappear."
            )

        events.append({
            "type": "layer_switched",
            "from_layer": old_layer.value,
            "to_layer": new_layer.value,
        })

        return {
            "accepted": True,
            "feedback": feedback,
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_read_sign(
        self,
        action: PuzzleAction,
        ma: MaState,
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Read spirit signs at the current node for navigation clues."""
        node = self.nodes.get(self.current_node_id)
        if node is None:
            return {
                "accepted": False,
                "feedback": "Nothing to read.",
                "solved": False,
                "solution": None,
                "events": events,
            }

        if not node.spirit_signs:
            return {
                "accepted": True,
                "feedback": "No spirit signs are visible here.",
                "solved": False,
                "solution": None,
                "events": events,
            }

        # Spirit signs require some ma to read
        if not ma.can_hear_whispers:
            return {
                "accepted": True,
                "feedback": "Faint markings shimmer on the walls, but you cannot focus on them. You need more stillness.",
                "solved": False,
                "solution": None,
                "events": events,
            }

        signs_text = " ".join(node.spirit_signs)
        self.spirit_signs_read.add(self.current_node_id)

        # Also reveal edge hints for edges from this node
        edge_hints: list[str] = []
        for edge in self.edges:
            if edge.from_node == self.current_node_id and edge.spirit_sign_hint:
                edge_hints.append(edge.spirit_sign_hint)

        feedback = f"The spirit signs read: {signs_text}"
        if edge_hints and ma.can_see_visions:
            feedback += " " + " ".join(edge_hints)

        return {
            "accepted": True,
            "feedback": feedback,
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _handle_look(
        self,
        action: PuzzleAction,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Survey available paths from the current node."""
        node = self.nodes.get(self.current_node_id)
        if node is None:
            return {
                "accepted": False,
                "feedback": "You are nowhere.",
                "solved": False,
                "solution": None,
                "events": events,
            }

        permeability = clock.spirit_permeability
        visible_destinations: list[str] = []
        hidden_count = 0

        for edge in self.edges:
            if edge.from_node != self.current_node_id:
                if not (edge.bidirectional and edge.to_node == self.current_node_id):
                    continue

            dest_id = (
                edge.to_node
                if edge.from_node == self.current_node_id
                else edge.from_node
            )
            dest = self.nodes.get(dest_id)
            if dest is None:
                continue

            if edge.is_traversable(clock, self.current_layer, permeability, flags):
                visible_destinations.append(dest.name)
            else:
                hidden_count += 1

        feedback = f"From {node.name}, you can see paths to: "
        if visible_destinations:
            feedback += ", ".join(visible_destinations) + "."
        else:
            feedback += "nowhere. All paths are closed."

        if hidden_count > 0 and ma.can_hear_whispers:
            feedback += f" You sense {hidden_count} hidden path(s), blocked by the current conditions."

        return {
            "accepted": True,
            "feedback": feedback,
            "solved": False,
            "solution": None,
            "events": events,
        }

    def _describe_anomaly(self, edge: NavigationEdge) -> str:
        """Generate narrative text for a spatial anomaly."""
        descriptions = {
            NavigationAnomaly.LOOP: (
                "The path curves impossibly, and you find yourself arriving "
                "where you started - but everything is subtly different."
            ),
            NavigationAnomaly.FOLD: (
                "Space folds. Two steps carry you across what should be "
                "kilometres. The city compresses like an accordion."
            ),
            NavigationAnomaly.INVERSION: (
                "Up becomes forward. The stairs run sideways. "
                "Gravity is a suggestion the spirit world ignores."
            ),
            NavigationAnomaly.TEMPORAL: (
                "The air tastes different. The advertisements are wrong. "
                "You have stepped not just through space but through time."
            ),
            NavigationAnomaly.LAYERED: (
                "Both worlds overlap here. You walk in the material and "
                "spirit realms simultaneously, each step echoing twice."
            ),
            NavigationAnomaly.PHANTOM: (
                "The path exists only in spirit vision - a ghost road "
                "that your body follows despite your eyes seeing nothing."
            ),
            NavigationAnomaly.CONDITIONAL: (
                "The path was always here, waiting for the right moment "
                "to reveal itself."
            ),
        }
        return edge.description or descriptions.get(edge.anomaly, "")

    def evaluate_transformation(
        self,
        clock: WorldClock,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> bool:
        """
        Navigation puzzles transform when time/season changes make different
        edges available, potentially opening new solutions or closing old ones.
        """
        # Check if any currently traversable edges have changed status
        # This is called by the base class's check_transformation
        return False  # Edges check conditions dynamically; no structural transform needed

    def is_solution_met(
        self,
        solution: PuzzleSolution,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> bool:
        # Check if we reached the destination
        current_node = self.nodes.get(self.current_node_id)
        if current_node is None or not current_node.is_destination:
            return False

        # Check solution-specific requirements
        if solution.required_ma > 0 and ma.current_ma < solution.required_ma:
            return False

        # Check for creative solution (shorter than optimal path)
        if (
            solution.solution_type == SolutionType.CREATIVE
            and len(self.path_taken) >= self.optimal_path_length
        ):
            return False

        return True
