"""
Ma no Kuni - Input Handler

Translates the raw language of keys and buttons into the vocabulary of the game.
A pressed arrow key becomes a step through Tokyo's streets.
A held spacebar becomes a moment of stillness, gathering ma.
"""

from __future__ import annotations

import time
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Protocol, Set, Tuple

import pygame

from src.engine.events import EventBus, EventType, GameEvent


class GameAction(Enum):
    """Every meaningful thing a player can express through input."""
    # Movement
    MOVE_UP = auto()
    MOVE_DOWN = auto()
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()

    # Interaction
    CONFIRM = auto()
    CANCEL = auto()
    INTERACT = auto()

    # Spirit
    SPIRIT_VISION = auto()

    # Ma
    WAIT_ACCUMULATE_MA = auto()

    # Menu
    PAUSE_MENU = auto()
    MAP = auto()
    INVENTORY = auto()
    BESTIARY = auto()

    # Combat quick abilities
    ABILITY_1 = auto()
    ABILITY_2 = auto()
    ABILITY_3 = auto()
    ABILITY_4 = auto()


# Actions that are meaningful when held continuously
_HOLDABLE_ACTIONS: frozenset[GameAction] = frozenset({
    GameAction.MOVE_UP,
    GameAction.MOVE_DOWN,
    GameAction.MOVE_LEFT,
    GameAction.MOVE_RIGHT,
    GameAction.WAIT_ACCUMULATE_MA,
})

# Map from GameAction to the EventType that should fire
_ACTION_EVENT_MAP: Dict[GameAction, EventType] = {
    GameAction.MOVE_UP: EventType.PLAYER_MOVE,
    GameAction.MOVE_DOWN: EventType.PLAYER_MOVE,
    GameAction.MOVE_LEFT: EventType.PLAYER_MOVE,
    GameAction.MOVE_RIGHT: EventType.PLAYER_MOVE,
    GameAction.CONFIRM: EventType.PLAYER_INTERACT,
    GameAction.CANCEL: EventType.PLAYER_INTERACT,
    GameAction.INTERACT: EventType.PLAYER_INTERACT,
    GameAction.SPIRIT_VISION: EventType.PLAYER_SPIRIT_SIGHT_TOGGLE,
    GameAction.WAIT_ACCUMULATE_MA: EventType.MA_ACCUMULATE,
    GameAction.PAUSE_MENU: EventType.STATE_CHANGE,
    GameAction.MAP: EventType.STATE_CHANGE,
    GameAction.INVENTORY: EventType.STATE_CHANGE,
    GameAction.BESTIARY: EventType.STATE_CHANGE,
    GameAction.ABILITY_1: EventType.BATTLE_ACTION,
    GameAction.ABILITY_2: EventType.BATTLE_ACTION,
    GameAction.ABILITY_3: EventType.BATTLE_ACTION,
    GameAction.ABILITY_4: EventType.BATTLE_ACTION,
}


def _default_bindings() -> Dict[int, GameAction]:
    """Return the default key-to-action mapping."""
    return {
        # Arrow keys
        pygame.K_UP: GameAction.MOVE_UP,
        pygame.K_DOWN: GameAction.MOVE_DOWN,
        pygame.K_LEFT: GameAction.MOVE_LEFT,
        pygame.K_RIGHT: GameAction.MOVE_RIGHT,
        # WASD
        pygame.K_w: GameAction.MOVE_UP,
        pygame.K_s: GameAction.MOVE_DOWN,
        pygame.K_a: GameAction.MOVE_LEFT,
        pygame.K_d: GameAction.MOVE_RIGHT,
        # Confirm / interact
        pygame.K_z: GameAction.CONFIRM,
        pygame.K_RETURN: GameAction.CONFIRM,
        # Cancel / back
        pygame.K_x: GameAction.CANCEL,
        pygame.K_BACKSPACE: GameAction.CANCEL,
        # Spirit vision
        pygame.K_c: GameAction.SPIRIT_VISION,
        # Pause
        pygame.K_TAB: GameAction.PAUSE_MENU,
        # Ma accumulation
        pygame.K_SPACE: GameAction.WAIT_ACCUMULATE_MA,
        # Combat abilities
        pygame.K_1: GameAction.ABILITY_1,
        pygame.K_2: GameAction.ABILITY_2,
        pygame.K_3: GameAction.ABILITY_3,
        pygame.K_4: GameAction.ABILITY_4,
        # Menus
        pygame.K_m: GameAction.MAP,
        pygame.K_i: GameAction.INVENTORY,
        pygame.K_b: GameAction.BESTIARY,
    }


class InputHandler:
    """
    Translates raw pygame input into game actions and events.

    Maintains two distinct sets per frame:
      - *pressed*: actions whose key went down THIS frame (edge-triggered).
      - *held*: actions whose key is currently down (level-triggered).

    Call ``begin_frame`` at the start of each tick, feed pygame events via
    ``handle_event``, then query with ``is_action_pressed`` / ``is_action_held``.
    """

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self._event_bus: Optional[EventBus] = event_bus
        self._bindings: Dict[int, GameAction] = _default_bindings()

        # Per-frame edge-triggered set (key went down this frame)
        self._pressed: Set[GameAction] = set()
        # Per-frame edge-triggered set (key went up this frame)
        self._released: Set[GameAction] = set()
        # Persistent level-triggered set (key is physically held)
        self._held: Set[GameAction] = set()

        # Optional callbacks keyed by action for quick custom hooks
        self._action_callbacks: Dict[GameAction, List[Callable[[GameAction], None]]] = {}

        # Whether input processing is enabled (disabled during focus loss, etc.)
        self._enabled: bool = True

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    @property
    def event_bus(self) -> Optional[EventBus]:
        return self._event_bus

    @event_bus.setter
    def event_bus(self, bus: EventBus) -> None:
        self._event_bus = bus

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        if not value:
            # Clear all held state when disabling so nothing sticks
            self._held.clear()
            self._pressed.clear()
            self._released.clear()
        self._enabled = value

    def bind_key(self, key: int, action: GameAction) -> None:
        """Bind a pygame key constant to a game action. Overwrites any existing binding for that key."""
        self._bindings[key] = action

    def unbind_key(self, key: int) -> None:
        """Remove the binding for a specific key."""
        self._bindings.pop(key, None)

    def get_keys_for_action(self, action: GameAction) -> List[int]:
        """Return all pygame key constants currently bound to *action*."""
        return [k for k, a in self._bindings.items() if a == action]

    def get_action_for_key(self, key: int) -> Optional[GameAction]:
        """Return the action bound to *key*, or ``None``."""
        return self._bindings.get(key)

    def get_all_bindings(self) -> Dict[int, GameAction]:
        """Return a copy of the full binding table."""
        return dict(self._bindings)

    def set_bindings(self, bindings: Dict[int, GameAction]) -> None:
        """Replace the entire binding table."""
        self._bindings = dict(bindings)

    def reset_bindings(self) -> None:
        """Restore the default key bindings."""
        self._bindings = _default_bindings()

    def on_action(self, action: GameAction, callback: Callable[[GameAction], None]) -> None:
        """Register a callback that fires whenever *action* is pressed (edge-triggered)."""
        self._action_callbacks.setdefault(action, []).append(callback)

    # ------------------------------------------------------------------
    # Per-frame lifecycle
    # ------------------------------------------------------------------

    def begin_frame(self) -> None:
        """Clear edge-triggered state. Call once at the start of each tick BEFORE processing events."""
        self._pressed.clear()
        self._released.clear()

    def handle_event(self, event: pygame.event.Event) -> None:
        """Process a single pygame event. Call for every KEYDOWN / KEYUP each frame."""
        if not self._enabled:
            return

        if event.type == pygame.KEYDOWN:
            action = self._bindings.get(event.key)
            if action is not None:
                self._pressed.add(action)
                self._held.add(action)
                self._emit_action_event(action, pressed=True)
                # Fire registered callbacks
                for cb in self._action_callbacks.get(action, ()):
                    cb(action)

        elif event.type == pygame.KEYUP:
            action = self._bindings.get(event.key)
            if action is not None:
                self._released.add(action)
                # Only remove from held if NO other key maps to the same action and is still down
                keys_for_action = self.get_keys_for_action(action)
                still_down = any(pygame.key.get_pressed()[k] for k in keys_for_action)
                if not still_down:
                    self._held.discard(action)
                self._emit_action_event(action, pressed=False)

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def is_action_pressed(self, action: GameAction | str) -> bool:
        """Return ``True`` if *action* was pressed THIS frame (edge-triggered)."""
        action = self._resolve_action(action)
        return action in self._pressed

    def is_action_released(self, action: GameAction | str) -> bool:
        """Return ``True`` if *action* was released THIS frame (edge-triggered)."""
        action = self._resolve_action(action)
        return action in self._released

    def is_action_held(self, action: GameAction | str) -> bool:
        """Return ``True`` if *action*'s key is currently held down (level-triggered)."""
        action = self._resolve_action(action)
        return action in self._held

    def get_movement_vector(self) -> Tuple[float, float]:
        """
        Return a normalized (dx, dy) movement vector from the currently held
        directional actions. (0, 0) when nothing is held.
        """
        dx = 0.0
        dy = 0.0
        if GameAction.MOVE_LEFT in self._held:
            dx -= 1.0
        if GameAction.MOVE_RIGHT in self._held:
            dx += 1.0
        if GameAction.MOVE_UP in self._held:
            dy -= 1.0
        if GameAction.MOVE_DOWN in self._held:
            dy += 1.0
        # Normalize diagonal movement
        if dx != 0.0 and dy != 0.0:
            length = (dx * dx + dy * dy) ** 0.5
            dx /= length
            dy /= length
        return (dx, dy)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_action(action: GameAction | str) -> GameAction:
        """Accept either a ``GameAction`` enum member or its name as a string."""
        if isinstance(action, str):
            try:
                return GameAction[action.upper()]
            except KeyError:
                raise ValueError(f"Unknown game action: {action!r}") from None
        return action

    def _emit_action_event(self, action: GameAction, *, pressed: bool) -> None:
        """Emit a ``GameEvent`` on the bus for this action, if a bus is attached."""
        if self._event_bus is None:
            return

        event_type = _ACTION_EVENT_MAP.get(action)
        if event_type is None:
            return

        data = {
            "action": action.name,
            "pressed": pressed,
        }

        # Enrich movement events with direction info
        if action in (
            GameAction.MOVE_UP,
            GameAction.MOVE_DOWN,
            GameAction.MOVE_LEFT,
            GameAction.MOVE_RIGHT,
        ):
            data["direction"] = action.name.removeprefix("MOVE_").lower()

        self._event_bus.emit(GameEvent(
            event_type=event_type,
            data=data,
            source="input_handler",
        ))
