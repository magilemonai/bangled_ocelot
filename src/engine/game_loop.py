"""
Ma no Kuni - Game Loop

The rhythm of the world. Sixty beats per second, each one a tiny universe:
sense the player, advance time, let the spirits move, paint the frame.
Between each beat, the space where everything becomes possible.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional, Protocol

import pygame

from src.engine.config import DISPLAY
from src.engine.events import EventBus, EventType, GameEvent
from src.engine.game import Game, GameState
from src.engine.input_handler import InputHandler

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pluggable handler protocols
# ---------------------------------------------------------------------------

class SceneManagerProtocol(Protocol):
    """Minimal interface for a scene manager that the loop can drive."""

    def update(self, delta: float, game: Game) -> None:
        """Advance the current scene by *delta* seconds."""
        ...

    def render(self, surface: pygame.Surface, game: Game) -> None:
        """Draw the current scene onto *surface*."""
        ...


class RendererProtocol(Protocol):
    """Minimal interface for a pluggable renderer."""

    def render(self, surface: pygame.Surface, game: Game) -> None:
        """Compose and blit the current frame onto *surface*."""
        ...


# ---------------------------------------------------------------------------
# GameLoop
# ---------------------------------------------------------------------------

class GameLoop:
    """
    The beating heart of Ma no Kuni.

    Owns the pygame display surface, clock, and orchestration of every
    frame.  All game-specific behaviour is injected through pluggable
    handlers so the loop itself stays engine-level and reusable.

    Usage::

        loop = GameLoop()
        loop.register_input_handler(my_input_handler)
        loop.register_renderer(my_renderer)
        loop.register_scene_manager(my_scene_manager)
        loop.run()
    """

    def __init__(self) -> None:
        # --- pygame bootstrap ------------------------------------------------
        pygame.init()

        flags = 0
        if DISPLAY.FULLSCREEN:
            flags |= pygame.FULLSCREEN

        vsync_flag = 1 if DISPLAY.VSYNC else 0
        self._surface: pygame.Surface = pygame.display.set_mode(
            (DISPLAY.SCREEN_WIDTH, DISPLAY.SCREEN_HEIGHT),
            flags,
            vsync=vsync_flag,
        )
        pygame.display.set_caption(DISPLAY.WINDOW_TITLE)

        self._clock: pygame.time.Clock = pygame.time.Clock()

        # --- core systems ----------------------------------------------------
        self._event_bus: EventBus = EventBus()
        self._game: Game = Game()
        self._game.running = True

        # --- pluggable handlers ----------------------------------------------
        self._input_handler: Optional[InputHandler] = None
        self._renderer: Optional[RendererProtocol] = None
        self._scene_manager: Optional[SceneManagerProtocol] = None

        # --- loop state ------------------------------------------------------
        self._running: bool = False
        self._paused: bool = False
        self._has_focus: bool = True
        self._fps: float = 0.0
        self._frame_count: int = 0
        self._target_fps: int = DISPLAY.FPS

        # User-supplied hooks that run once per frame (lightweight extension point)
        self._pre_update_hooks: list[Callable[[float], None]] = []
        self._post_render_hooks: list[Callable[[pygame.Surface], None]] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def surface(self) -> pygame.Surface:
        """The main display surface."""
        return self._surface

    @property
    def game(self) -> Game:
        """The ``Game`` instance managed by this loop."""
        return self._game

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def fps(self) -> float:
        """Smoothed frames-per-second reported by pygame's clock."""
        return self._fps

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def paused(self) -> bool:
        return self._paused

    @paused.setter
    def paused(self, value: bool) -> None:
        was_paused = self._paused
        self._paused = value
        if value and not was_paused:
            self._event_bus.emit(GameEvent(
                event_type=EventType.STATE_CHANGE,
                data={"paused": True},
                source="game_loop",
            ))
        elif not value and was_paused:
            self._event_bus.emit(GameEvent(
                event_type=EventType.STATE_CHANGE,
                data={"paused": False},
                source="game_loop",
            ))

    @property
    def has_focus(self) -> bool:
        return self._has_focus

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_input_handler(self, handler: InputHandler) -> None:
        """Set the input handler that will receive pygame key events."""
        self._input_handler = handler
        # Ensure the handler can reach the event bus
        if handler.event_bus is None:
            handler.event_bus = self._event_bus

    def register_renderer(self, renderer: RendererProtocol) -> None:
        """Set the renderer responsible for drawing each frame."""
        self._renderer = renderer

    def register_scene_manager(self, scene_manager: SceneManagerProtocol) -> None:
        """Set the scene manager that routes update/render per game state."""
        self._scene_manager = scene_manager

    def add_pre_update_hook(self, hook: Callable[[float], None]) -> None:
        """Add a callable invoked with *delta* before the main update step."""
        self._pre_update_hooks.append(hook)

    def add_post_render_hook(self, hook: Callable[[pygame.Surface], None]) -> None:
        """Add a callable invoked with the surface after rendering."""
        self._post_render_hooks.append(hook)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Enter the main loop. Blocks until the game exits.

        Frame order:
          1. Calculate delta time
          2. Process pygame / OS events
          3. Feed key events to the input handler
          4. Pre-update hooks
          5. Update game world (delta = 0 when paused)
          6. Update scene manager
          7. Process event bus queue
          8. Render
          9. Post-render hooks
         10. Flip display & cap FPS
        """
        self._running = True
        logger.info("Game loop started  (%dx%d @ %d FPS target)",
                     DISPLAY.SCREEN_WIDTH, DISPLAY.SCREEN_HEIGHT, self._target_fps)

        try:
            while self._running:
                # 1 -- Delta time (seconds) -----------------------------------
                raw_delta = self._clock.tick(self._target_fps) / 1000.0
                # Clamp to avoid spiral-of-death on long hitches
                raw_delta = min(raw_delta, 0.1)
                self._fps = self._clock.get_fps()

                # 2/3 -- Events & input ---------------------------------------
                self._process_events()

                # Forward input actions to scene manager
                self._forward_input_to_scenes()

                # Effective delta: zero when paused so the game world freezes
                delta = 0.0 if self._paused else raw_delta

                # 4 -- Pre-update hooks ---------------------------------------
                for hook in self._pre_update_hooks:
                    hook(delta)

                # 5 -- Game world update --------------------------------------
                self._game.update(delta)

                # 6 -- Scene manager update -----------------------------------
                if self._scene_manager is not None:
                    self._scene_manager.update(delta, self._game)

                # 7 -- Drain the event bus ------------------------------------
                self._event_bus.process_queue()

                # 8 -- Render -------------------------------------------------
                self._render()

                # 9 -- Post-render hooks --------------------------------------
                for hook in self._post_render_hooks:
                    hook(self._surface)

                # 10 -- Present -----------------------------------------------
                pygame.display.flip()
                self._frame_count += 1

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self._shutdown()

    def stop(self) -> None:
        """Request the loop to exit after the current frame."""
        self._running = False

    # ------------------------------------------------------------------
    # Internal: event processing
    # ------------------------------------------------------------------

    def _process_events(self) -> None:
        """Pump the pygame event queue and dispatch to the input handler."""
        if self._input_handler is not None:
            self._input_handler.begin_frame()

        for event in pygame.event.get():
            # Window / OS-level events
            if event.type == pygame.QUIT:
                self._running = False
                continue

            if event.type == pygame.ACTIVEEVENT:
                self._handle_focus(event)
                continue

            if event.type == pygame.WINDOWFOCUSGAINED:
                self._has_focus = True
                if self._input_handler is not None:
                    self._input_handler.enabled = True
                continue

            if event.type == pygame.WINDOWFOCUSLOST:
                self._has_focus = False
                if self._input_handler is not None:
                    self._input_handler.enabled = False
                continue

            # Key events -> input handler
            if event.type in (pygame.KEYDOWN, pygame.KEYUP):
                if self._input_handler is not None:
                    self._input_handler.handle_event(event)

    def _handle_focus(self, event: pygame.event.Event) -> None:
        """Handle legacy ACTIVEEVENT for focus gain/loss."""
        if hasattr(event, "gain") and hasattr(event, "state"):
            # state & 1 == mouse focus, state & 2 == keyboard focus
            if event.state & 2:
                self._has_focus = bool(event.gain)
                if self._input_handler is not None:
                    self._input_handler.enabled = self._has_focus

    # ------------------------------------------------------------------
    # Internal: input-to-scene forwarding
    # ------------------------------------------------------------------

    # Map GameAction enum names to scene action strings
    _ACTION_NAME_MAP: dict[str, str] = {
        "MOVE_UP": "move_up",
        "MOVE_DOWN": "move_down",
        "MOVE_LEFT": "move_left",
        "MOVE_RIGHT": "move_right",
        "CONFIRM": "confirm",
        "CANCEL": "cancel",
        "INTERACT": "interact",
        "SPIRIT_VISION": "spirit_vision",
        "WAIT_ACCUMULATE_MA": "wait",
        "PAUSE_MENU": "menu",
        "MAP": "map",
        "INVENTORY": "inventory",
        "BESTIARY": "bestiary",
        "ABILITY_1": "ability_1",
        "ABILITY_2": "ability_2",
        "ABILITY_3": "ability_3",
        "ABILITY_4": "ability_4",
    }

    def _forward_input_to_scenes(self) -> None:
        """Forward pressed/released actions from the input handler to the scene manager."""
        if self._input_handler is None or self._scene_manager is None:
            return

        from src.engine.input_handler import GameAction

        for action in GameAction:
            action_name = self._ACTION_NAME_MAP.get(action.name, action.name.lower())
            if self._input_handler.is_action_pressed(action):
                self._scene_manager.handle_input(action_name, True)
            if self._input_handler.is_action_released(action):
                self._scene_manager.handle_input(action_name, False)

    # ------------------------------------------------------------------
    # Internal: rendering
    # ------------------------------------------------------------------

    def _render(self) -> None:
        """Clear the surface and delegate to the renderer / scene manager."""
        self._surface.fill((0, 0, 0))

        if self._scene_manager is not None:
            self._scene_manager.render(self._surface, self._game)
        elif self._renderer is not None:
            self._renderer.render(self._surface, self._game)

    # ------------------------------------------------------------------
    # Internal: shutdown
    # ------------------------------------------------------------------

    def _shutdown(self) -> None:
        """Clean up pygame and any other resources."""
        logger.info("Shutting down after %d frames", self._frame_count)
        self._game.running = False
        pygame.quit()
