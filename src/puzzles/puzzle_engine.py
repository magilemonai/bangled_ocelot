"""
Ma no Kuni - Core Puzzle Engine

The engine that holds all puzzle logic together. Puzzles are living things here:
they breathe with the world clock, shift with the spirit tide, and remember
what the player has tried before.

A puzzle is not a lock. It is a question the world is asking.

Design principles:
    - Multiple solutions are always valid. Creative approaches are rewarded.
    - Hints emerge organically from the world: spirit companions whisper,
      the environment shifts, ma accumulates clues in silence.
    - Puzzles transform with time of day, season, and spirit permeability.
    - Difficulty is progressive but never punitive. The world is patient.
    - Every puzzle state is saved. The world does not forget your attempts.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Optional

# ---------------------------------------------------------------------------
# Relative imports from the engine module
# ---------------------------------------------------------------------------
from ..engine.game import (
    MaState,
    MoonPhase,
    Season,
    SpiritTide,
    TimeOfDay,
    WorldClock,
)


# ===================================================================
# Enumerations
# ===================================================================

class PuzzleCategory(Enum):
    """The seven families of puzzles in Ma no Kuni."""
    DUAL_LAYER = "dual_layer"
    MA_SILENCE = "ma_silence"
    RESONANCE = "resonance"
    MEMORY = "memory"
    EMPATHY = "empathy"
    CALLIGRAPHY = "calligraphy"
    URBAN_NAVIGATION = "urban_navigation"


class PuzzleStatus(Enum):
    """Lifecycle of a puzzle instance."""
    UNDISCOVERED = auto()   # Player has not encountered this puzzle yet
    DISCOVERED = auto()     # Player has seen the puzzle but not engaged
    ACTIVE = auto()         # Player is currently working on the puzzle
    PAUSED = auto()         # Player stepped away; state preserved
    SOLVED = auto()         # At least one solution found
    MASTERED = auto()       # All solutions found or creative solution achieved
    FAILED = auto()         # Timed puzzle expired (rare - most puzzles are patient)
    TRANSFORMED = auto()    # Puzzle changed due to world state; old state archived


class PuzzleDifficulty(Enum):
    """
    Difficulty is not about punishment. It is about depth.
    A 'hard' puzzle simply requires deeper listening.
    """
    GENTLE = 1      # Tutorial-adjacent, forgiving
    MODERATE = 2    # Requires observation and thought
    DEEP = 3        # Requires connecting ideas across worlds
    PROFOUND = 4    # Requires mastery of a puzzle family's core concept
    TRANSCENDENT = 5  # Requires understanding ma itself


class HintTier(Enum):
    """Hints unfold gradually, like a flower opening."""
    AMBIENT = auto()       # Environmental cue - a flicker, a sound, a scent
    COMPANION = auto()     # Spirit companion offers a nudge
    OBSERVATION = auto()   # Direct observation hint ("The lantern flickers when...")
    GUIDANCE = auto()      # Clear directional hint ("Try standing still here")
    REVELATION = auto()    # Near-solution ("The door responds to silence, not force")


class SolutionType(Enum):
    """How the player arrived at the answer."""
    STANDARD = "standard"           # The intended primary solution
    ALTERNATE = "alternate"         # A valid alternate path
    CREATIVE = "creative"           # Unexpected but valid - emergent
    BRUTE_FORCE = "brute_force"     # Solved by exhaustion, not insight
    SPIRIT_AIDED = "spirit_aided"   # Spirit companion provided crucial help
    MA_REVEALED = "ma_revealed"     # Solved through accumulated ma / stillness


class WorldLayer(Enum):
    """The two layers of reality and the crossing between them."""
    MATERIAL = "material"
    SPIRIT = "spirit"
    LIMINAL = "liminal"   # The crossing space - neither and both


# ===================================================================
# Data classes
# ===================================================================

@dataclass
class PuzzleHint:
    """
    A single hint. Hints are gated by ma level, spirit companions present,
    number of failed attempts, and time spent.
    """
    hint_id: str
    tier: HintTier
    text: str
    spirit_text: str = ""               # How a spirit companion phrases it
    ma_threshold: float = 0.0           # Minimum ma to receive this hint
    attempts_threshold: int = 0         # Minimum failed attempts before showing
    time_threshold_seconds: float = 0.0 # Minimum time spent on puzzle
    requires_companion: Optional[str] = None  # Specific companion required
    requires_permeability: float = 0.0  # Minimum spirit permeability
    revealed: bool = False

    def is_available(
        self,
        ma: float,
        attempts: int,
        elapsed: float,
        companion: Optional[str],
        permeability: float,
    ) -> bool:
        """Check whether this hint should be revealed to the player."""
        if self.revealed:
            return True
        if ma < self.ma_threshold:
            return False
        if attempts < self.attempts_threshold:
            return False
        if elapsed < self.time_threshold_seconds:
            return False
        if self.requires_companion and companion != self.requires_companion:
            return False
        if permeability < self.requires_permeability:
            return False
        return True


@dataclass
class PuzzleSolution:
    """
    A single valid way to solve a puzzle. Puzzles always have at least one
    standard solution and may have several alternate or creative ones.
    """
    solution_id: str
    solution_type: SolutionType
    description: str
    required_actions: list[str] = field(default_factory=list)
    required_items: list[str] = field(default_factory=list)
    required_flags: list[str] = field(default_factory=list)
    required_layer: Optional[WorldLayer] = None
    required_ma: float = 0.0
    required_permeability: float = 0.0
    reward_multiplier: float = 1.0       # Creative solutions give bonus rewards
    narrative_text: str = ""             # What happens narratively when solved this way
    unlocks_flags: list[str] = field(default_factory=list)

    def is_achievable(
        self,
        available_items: list[str],
        flags: dict[str, Any],
        current_layer: WorldLayer,
        ma: float,
        permeability: float,
    ) -> bool:
        """Check whether the player currently *could* achieve this solution."""
        if self.required_layer and current_layer != self.required_layer:
            return False
        if ma < self.required_ma:
            return False
        if permeability < self.required_permeability:
            return False
        if not all(item in available_items for item in self.required_items):
            return False
        if not all(flags.get(f, False) for f in self.required_flags):
            return False
        return True


@dataclass
class PuzzleAction:
    """A single action the player takes while engaging with a puzzle."""
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    action_type: str = ""       # e.g. "move_object", "wait", "draw_kanji", "speak"
    target: str = ""            # What the action targets
    parameters: dict[str, Any] = field(default_factory=dict)
    layer: WorldLayer = WorldLayer.MATERIAL
    timestamp: float = field(default_factory=time.time)


@dataclass
class PuzzleReward:
    """What the player gains for solving a puzzle."""
    experience: int = 0
    ma_bonus: float = 0.0
    items: list[str] = field(default_factory=list)
    spirit_affinity: dict[str, float] = field(default_factory=dict)
    unlocked_flags: list[str] = field(default_factory=list)
    narrative_key: str = ""     # Key into the narrative system for post-solve story
    secret_revealed: str = ""   # A secret about the world


@dataclass
class PuzzleConditions:
    """
    World conditions that affect a puzzle's availability and behaviour.
    A puzzle might only appear at dusk, or change its nature in winter.
    """
    valid_times: list[TimeOfDay] = field(default_factory=list)       # Empty = any time
    valid_seasons: list[Season] = field(default_factory=list)        # Empty = any season
    valid_moon_phases: list[MoonPhase] = field(default_factory=list) # Empty = any phase
    min_permeability: float = 0.0
    max_permeability: float = 1.0
    required_flags: list[str] = field(default_factory=list)
    forbidden_flags: list[str] = field(default_factory=list)
    required_district: Optional[str] = None

    def is_met(
        self,
        clock: WorldClock,
        tide: SpiritTide,
        flags: dict[str, Any],
        district: Optional[str] = None,
    ) -> bool:
        """Return True if all world conditions are currently satisfied."""
        if self.valid_times and clock.time_of_day not in self.valid_times:
            return False
        if self.valid_seasons and clock.season not in self.valid_seasons:
            return False
        if self.valid_moon_phases and clock.moon_phase not in self.valid_moon_phases:
            return False

        permeability = clock.spirit_permeability
        if not (self.min_permeability <= permeability <= self.max_permeability):
            return False

        if self.required_district and district != self.required_district:
            return False
        if not all(flags.get(f, False) for f in self.required_flags):
            return False
        if any(flags.get(f, False) for f in self.forbidden_flags):
            return False

        return True


@dataclass
class PuzzleState:
    """
    The full mutable state of a puzzle instance. Serialisable for save games.
    The world remembers every attempt, every pause, every moment of silence.
    """
    puzzle_id: str
    status: PuzzleStatus = PuzzleStatus.UNDISCOVERED
    actions_taken: list[dict[str, Any]] = field(default_factory=list)
    attempts: int = 0
    time_spent_seconds: float = 0.0
    started_at: Optional[float] = None
    solved_at: Optional[float] = None
    solution_used: Optional[str] = None
    solution_type_used: Optional[SolutionType] = None
    hints_revealed: list[str] = field(default_factory=list)
    layer_state: dict[str, dict[str, Any]] = field(default_factory=lambda: {
        "material": {},
        "spirit": {},
    })
    custom_state: dict[str, Any] = field(default_factory=dict)
    transformation_history: list[dict[str, Any]] = field(default_factory=list)

    def record_action(self, action: PuzzleAction) -> None:
        """Record a player action in the puzzle history."""
        self.actions_taken.append({
            "action_id": action.action_id,
            "type": action.action_type,
            "target": action.target,
            "parameters": action.parameters,
            "layer": action.layer.value,
            "timestamp": action.timestamp,
        })

    def to_save_data(self) -> dict[str, Any]:
        """Serialise to a plain dict for saving."""
        return {
            "puzzle_id": self.puzzle_id,
            "status": self.status.name,
            "actions_taken": self.actions_taken,
            "attempts": self.attempts,
            "time_spent_seconds": self.time_spent_seconds,
            "started_at": self.started_at,
            "solved_at": self.solved_at,
            "solution_used": self.solution_used,
            "solution_type_used": (
                self.solution_type_used.value if self.solution_type_used else None
            ),
            "hints_revealed": self.hints_revealed,
            "layer_state": self.layer_state,
            "custom_state": self.custom_state,
            "transformation_history": self.transformation_history,
        }

    @classmethod
    def from_save_data(cls, data: dict[str, Any]) -> PuzzleState:
        """Reconstruct from saved data."""
        state = cls(puzzle_id=data["puzzle_id"])
        state.status = PuzzleStatus[data["status"]]
        state.actions_taken = data.get("actions_taken", [])
        state.attempts = data.get("attempts", 0)
        state.time_spent_seconds = data.get("time_spent_seconds", 0.0)
        state.started_at = data.get("started_at")
        state.solved_at = data.get("solved_at")
        state.solution_used = data.get("solution_used")
        raw_type = data.get("solution_type_used")
        state.solution_type_used = SolutionType(raw_type) if raw_type else None
        state.hints_revealed = data.get("hints_revealed", [])
        state.layer_state = data.get("layer_state", {"material": {}, "spirit": {}})
        state.custom_state = data.get("custom_state", {})
        state.transformation_history = data.get("transformation_history", [])
        return state


# ===================================================================
# Abstract base puzzle
# ===================================================================

class BasePuzzle(ABC):
    """
    The abstract heart of every puzzle in Ma no Kuni.

    Subclasses implement the seven puzzle families. The base provides:
        - Lifecycle management (discover, activate, pause, solve, transform)
        - Hint evaluation and delivery
        - Multi-solution validation
        - World-condition gating
        - State persistence
        - Action processing pipeline
    """

    def __init__(
        self,
        puzzle_id: str,
        name: str,
        description: str,
        category: PuzzleCategory,
        difficulty: PuzzleDifficulty,
        location: str,
        district: str,
        conditions: PuzzleConditions,
        solutions: list[PuzzleSolution],
        hints: list[PuzzleHint],
        reward: PuzzleReward,
        *,
        spirit_description: str = "",
        flavour_text: str = "",
        max_attempts: int = 0,          # 0 = unlimited (most puzzles are patient)
        time_limit_seconds: float = 0,  # 0 = no time limit
        transforms_with_world: bool = False,
    ) -> None:
        self.puzzle_id = puzzle_id
        self.name = name
        self.description = description
        self.spirit_description = spirit_description
        self.flavour_text = flavour_text
        self.category = category
        self.difficulty = difficulty
        self.location = location
        self.district = district
        self.conditions = conditions
        self.solutions = solutions
        self.hints = hints
        self.reward = reward
        self.max_attempts = max_attempts
        self.time_limit_seconds = time_limit_seconds
        self.transforms_with_world = transforms_with_world

        self.state = PuzzleState(puzzle_id=puzzle_id)

        # Callback hooks for game system integration
        self._on_solve_callbacks: list[Callable[[BasePuzzle, PuzzleSolution], None]] = []
        self._on_hint_callbacks: list[Callable[[BasePuzzle, PuzzleHint], None]] = []
        self._on_transform_callbacks: list[Callable[[BasePuzzle], None]] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def discover(self) -> None:
        """Player encounters the puzzle for the first time."""
        if self.state.status == PuzzleStatus.UNDISCOVERED:
            self.state.status = PuzzleStatus.DISCOVERED

    def activate(self) -> None:
        """Player engages with the puzzle."""
        if self.state.status in (PuzzleStatus.DISCOVERED, PuzzleStatus.PAUSED):
            self.state.status = PuzzleStatus.ACTIVE
            if self.state.started_at is None:
                self.state.started_at = time.time()

    def pause(self) -> None:
        """Player steps away. State is preserved."""
        if self.state.status == PuzzleStatus.ACTIVE:
            self.state.status = PuzzleStatus.PAUSED

    def reset(self) -> None:
        """Allow the player to restart a puzzle, preserving attempt count."""
        if self.state.status in (PuzzleStatus.ACTIVE, PuzzleStatus.PAUSED):
            self.state.attempts += 1
            self.state.actions_taken.clear()
            self.state.layer_state = {"material": {}, "spirit": {}}
            self.state.custom_state.clear()
            self.on_reset()

    @abstractmethod
    def on_reset(self) -> None:
        """Subclass-specific reset logic."""

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    def is_available(
        self,
        clock: WorldClock,
        tide: SpiritTide,
        flags: dict[str, Any],
        district: Optional[str] = None,
    ) -> bool:
        """Check whether this puzzle should be present in the current world state."""
        return self.conditions.is_met(clock, tide, flags, district)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def process_action(
        self,
        action: PuzzleAction,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Process a player action and return a result dict.

        The result always contains:
            - "accepted": bool - was the action valid
            - "feedback": str  - narrative feedback text
            - "solved": bool   - did this action solve the puzzle
            - "solution": optional PuzzleSolution if solved
            - "events": list of triggered events
        """
        if self.state.status != PuzzleStatus.ACTIVE:
            return {
                "accepted": False,
                "feedback": "This puzzle is not active.",
                "solved": False,
                "solution": None,
                "events": [],
            }

        # Record the action
        self.state.record_action(action)

        # Delegate to subclass
        result = self.evaluate_action(action, clock, ma, tide, flags)

        # Check for solution after the action
        if not result.get("solved", False):
            solution = self._check_solutions(clock, ma, tide, flags)
            if solution is not None:
                result["solved"] = True
                result["solution"] = solution

        # If solved, update state
        if result.get("solved", False):
            solution = result.get("solution")
            self._mark_solved(solution)

        return result

    @abstractmethod
    def evaluate_action(
        self,
        action: PuzzleAction,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Subclass-specific action evaluation.
        Return the same result dict shape as process_action.
        """

    def _check_solutions(
        self,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> Optional[PuzzleSolution]:
        """Check all solutions against the current puzzle state."""
        for solution in self.solutions:
            if self.is_solution_met(solution, clock, ma, tide, flags):
                return solution
        return None

    @abstractmethod
    def is_solution_met(
        self,
        solution: PuzzleSolution,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> bool:
        """Check whether a specific solution's conditions are currently satisfied."""

    def _mark_solved(self, solution: Optional[PuzzleSolution]) -> None:
        """Transition to solved state and fire callbacks."""
        self.state.status = PuzzleStatus.SOLVED
        self.state.solved_at = time.time()
        if solution:
            self.state.solution_used = solution.solution_id
            self.state.solution_type_used = solution.solution_type
            for cb in self._on_solve_callbacks:
                cb(self, solution)

    # ------------------------------------------------------------------
    # Hints
    # ------------------------------------------------------------------

    def get_available_hints(
        self,
        ma: MaState,
        companion: Optional[str],
        permeability: float,
    ) -> list[PuzzleHint]:
        """Return all hints the player currently qualifies for."""
        elapsed = 0.0
        if self.state.started_at is not None:
            elapsed = time.time() - self.state.started_at

        available: list[PuzzleHint] = []
        for hint in self.hints:
            if hint.is_available(
                ma=ma.current_ma,
                attempts=self.state.attempts,
                elapsed=elapsed,
                companion=companion,
                permeability=permeability,
            ):
                available.append(hint)
        return available

    def reveal_next_hint(
        self,
        ma: MaState,
        companion: Optional[str],
        permeability: float,
    ) -> Optional[PuzzleHint]:
        """Reveal the next unrevealed hint, if any are available."""
        available = self.get_available_hints(ma, companion, permeability)
        for hint in available:
            if hint.hint_id not in self.state.hints_revealed:
                hint.revealed = True
                self.state.hints_revealed.append(hint.hint_id)
                for cb in self._on_hint_callbacks:
                    cb(self, hint)
                return hint
        return None

    # ------------------------------------------------------------------
    # World transformation
    # ------------------------------------------------------------------

    def check_transformation(
        self,
        clock: WorldClock,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> bool:
        """
        Check if the puzzle should transform based on changed world state.
        Returns True if a transformation occurred.
        """
        if not self.transforms_with_world:
            return False
        if self.state.status in (PuzzleStatus.SOLVED, PuzzleStatus.MASTERED):
            return False

        did_transform = self.evaluate_transformation(clock, tide, flags)
        if did_transform:
            self.state.transformation_history.append({
                "timestamp": time.time(),
                "time_of_day": clock.time_of_day.value,
                "season": clock.season.value,
                "permeability": clock.spirit_permeability,
            })
            self.state.status = PuzzleStatus.TRANSFORMED
            for cb in self._on_transform_callbacks:
                cb(self)
        return did_transform

    def evaluate_transformation(
        self,
        clock: WorldClock,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> bool:
        """
        Override in subclasses that transform.
        Return True if the puzzle changed form.
        """
        return False

    # ------------------------------------------------------------------
    # Update (per-tick)
    # ------------------------------------------------------------------

    def update(
        self,
        delta: float,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Per-tick update. Handles time tracking, time limits, and subclass logic.
        Returns a list of events generated this tick.
        """
        events: list[dict[str, Any]] = []

        if self.state.status != PuzzleStatus.ACTIVE:
            return events

        self.state.time_spent_seconds += delta

        # Time limit enforcement (rare - most puzzles are patient)
        if (
            self.time_limit_seconds > 0
            and self.state.time_spent_seconds >= self.time_limit_seconds
        ):
            self.state.status = PuzzleStatus.FAILED
            events.append({
                "type": "puzzle_time_expired",
                "puzzle_id": self.puzzle_id,
            })
            return events

        # Subclass tick
        sub_events = self.on_update(delta, clock, ma, tide, flags)
        events.extend(sub_events)

        # World transformation check
        if self.transforms_with_world:
            self.check_transformation(clock, tide, flags)

        return events

    def on_update(
        self,
        delta: float,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Override for per-tick subclass behaviour. Return events list."""
        return []

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> dict[str, Any]:
        """Full serialisation for save games."""
        return {
            "puzzle_id": self.puzzle_id,
            "category": self.category.value,
            "state": self.state.to_save_data(),
        }

    def load_state(self, data: dict[str, Any]) -> None:
        """Restore puzzle state from save data."""
        self.state = PuzzleState.from_save_data(data["state"])
        # Restore hint revealed flags
        for hint in self.hints:
            if hint.hint_id in self.state.hints_revealed:
                hint.revealed = True

    # ------------------------------------------------------------------
    # Callback registration
    # ------------------------------------------------------------------

    def on_solve(self, callback: Callable[[BasePuzzle, PuzzleSolution], None]) -> None:
        self._on_solve_callbacks.append(callback)

    def on_hint_revealed(self, callback: Callable[[BasePuzzle, PuzzleHint], None]) -> None:
        self._on_hint_callbacks.append(callback)

    def on_transformed(self, callback: Callable[[BasePuzzle], None]) -> None:
        self._on_transform_callbacks.append(callback)


# ===================================================================
# Puzzle Registry & Manager
# ===================================================================

class PuzzleRegistry:
    """
    Central registry for all puzzle definitions.
    Puzzles register themselves here so the engine can look them up by id,
    category, location, or any combination of filters.
    """

    def __init__(self) -> None:
        self._puzzles: dict[str, BasePuzzle] = {}
        self._by_category: dict[PuzzleCategory, list[str]] = {
            cat: [] for cat in PuzzleCategory
        }
        self._by_district: dict[str, list[str]] = {}

    def register(self, puzzle: BasePuzzle) -> None:
        """Add a puzzle to the registry."""
        self._puzzles[puzzle.puzzle_id] = puzzle
        self._by_category[puzzle.category].append(puzzle.puzzle_id)
        district_list = self._by_district.setdefault(puzzle.district, [])
        district_list.append(puzzle.puzzle_id)

    def get(self, puzzle_id: str) -> Optional[BasePuzzle]:
        return self._puzzles.get(puzzle_id)

    def get_by_category(self, category: PuzzleCategory) -> list[BasePuzzle]:
        return [
            self._puzzles[pid]
            for pid in self._by_category.get(category, [])
            if pid in self._puzzles
        ]

    def get_by_district(self, district: str) -> list[BasePuzzle]:
        return [
            self._puzzles[pid]
            for pid in self._by_district.get(district, [])
            if pid in self._puzzles
        ]

    def get_available(
        self,
        clock: WorldClock,
        tide: SpiritTide,
        flags: dict[str, Any],
        district: Optional[str] = None,
    ) -> list[BasePuzzle]:
        """Return all puzzles whose world conditions are currently met."""
        source = (
            self.get_by_district(district) if district
            else list(self._puzzles.values())
        )
        return [p for p in source if p.is_available(clock, tide, flags, district)]

    @property
    def all_puzzles(self) -> list[BasePuzzle]:
        return list(self._puzzles.values())


class PuzzleManager:
    """
    Runtime manager that sits inside the game loop.

    Responsibilities:
        - Tick all active puzzles each frame
        - Manage puzzle discovery based on player position
        - Coordinate hint delivery with the UI/narrative systems
        - Handle puzzle save/load
        - Track global puzzle statistics
    """

    def __init__(self, registry: PuzzleRegistry) -> None:
        self.registry = registry
        self.active_puzzle_id: Optional[str] = None
        self.statistics: dict[str, Any] = {
            "total_solved": 0,
            "total_mastered": 0,
            "total_attempts": 0,
            "creative_solutions": 0,
            "hints_used": 0,
            "time_in_puzzles": 0.0,
            "category_solved": {cat.value: 0 for cat in PuzzleCategory},
        }

    @property
    def active_puzzle(self) -> Optional[BasePuzzle]:
        if self.active_puzzle_id is None:
            return None
        return self.registry.get(self.active_puzzle_id)

    def engage(self, puzzle_id: str) -> Optional[BasePuzzle]:
        """Player engages with a puzzle. Returns the puzzle or None."""
        puzzle = self.registry.get(puzzle_id)
        if puzzle is None:
            return None

        # Pause any currently active puzzle
        if self.active_puzzle is not None:
            self.active_puzzle.pause()

        puzzle.activate()
        self.active_puzzle_id = puzzle_id
        return puzzle

    def disengage(self) -> None:
        """Player steps away from the current puzzle."""
        if self.active_puzzle is not None:
            self.active_puzzle.pause()
            self.active_puzzle_id = None

    def submit_action(
        self,
        action: PuzzleAction,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> dict[str, Any]:
        """Submit a player action to the active puzzle."""
        puzzle = self.active_puzzle
        if puzzle is None:
            return {
                "accepted": False,
                "feedback": "No active puzzle.",
                "solved": False,
                "solution": None,
                "events": [],
            }

        result = puzzle.process_action(action, clock, ma, tide, flags)

        if result.get("solved", False):
            self._record_solve(puzzle, result.get("solution"))

        return result

    def request_hint(
        self,
        ma: MaState,
        companion: Optional[str],
        permeability: float,
    ) -> Optional[PuzzleHint]:
        """Request the next available hint for the active puzzle."""
        puzzle = self.active_puzzle
        if puzzle is None:
            return None
        hint = puzzle.reveal_next_hint(ma, companion, permeability)
        if hint is not None:
            self.statistics["hints_used"] += 1
        return hint

    def update(
        self,
        delta: float,
        clock: WorldClock,
        ma: MaState,
        tide: SpiritTide,
        flags: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Per-tick update for all active puzzles. Returns events."""
        events: list[dict[str, Any]] = []
        self.statistics["time_in_puzzles"] += delta

        # Update the engaged puzzle
        puzzle = self.active_puzzle
        if puzzle is not None:
            puzzle_events = puzzle.update(delta, clock, ma, tide, flags)
            events.extend(puzzle_events)

        return events

    def discover_puzzles(
        self,
        clock: WorldClock,
        tide: SpiritTide,
        flags: dict[str, Any],
        district: str,
    ) -> list[BasePuzzle]:
        """
        Check for newly discoverable puzzles in the current district.
        Returns list of puzzles that were just discovered.
        """
        newly_discovered: list[BasePuzzle] = []
        available = self.registry.get_available(clock, tide, flags, district)
        for puzzle in available:
            if puzzle.state.status == PuzzleStatus.UNDISCOVERED:
                puzzle.discover()
                newly_discovered.append(puzzle)
        return newly_discovered

    def _record_solve(
        self, puzzle: BasePuzzle, solution: Optional[PuzzleSolution]
    ) -> None:
        """Update statistics after a puzzle solve."""
        self.statistics["total_solved"] += 1
        self.statistics["category_solved"][puzzle.category.value] += 1
        if solution and solution.solution_type == SolutionType.CREATIVE:
            self.statistics["creative_solutions"] += 1
        self.active_puzzle_id = None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_all(self) -> dict[str, Any]:
        """Serialise all puzzle states and manager statistics."""
        return {
            "puzzle_states": {
                pid: p.save() for pid, p in self.registry._puzzles.items()
            },
            "active_puzzle_id": self.active_puzzle_id,
            "statistics": self.statistics,
        }

    def load_all(self, data: dict[str, Any]) -> None:
        """Restore puzzle states from save data."""
        self.active_puzzle_id = data.get("active_puzzle_id")
        self.statistics = data.get("statistics", self.statistics)
        for pid, pdata in data.get("puzzle_states", {}).items():
            puzzle = self.registry.get(pid)
            if puzzle is not None:
                puzzle.load_state(pdata)
