"""
Ma no Kuni - Scene Manager

The stage director. Every moment of the game exists within a scene,
and scenes stack like layers of meaning: exploration beneath dialogue,
dialogue beneath menu, each one still breathing underneath.

The scene stack is the game's consciousness. Push a scene to focus
attention. Pop it to return to what was always there, waiting.
Combat replaces exploration -- you cannot walk away from a reckoning.
But dialogue overlays it -- the world holds still while you speak.

Transitions between scenes pass through the event bus. Nothing happens
in isolation. The battle that starts, the conversation that begins,
the vignette that unfolds -- all of it ripples through every system.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Protocol, runtime_checkable

from src.engine.events import EventBus, EventType, GameEvent
from src.engine.game import Game, GameState, MaState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Renderer protocol -- scenes render through this interface
# ---------------------------------------------------------------------------

@runtime_checkable
class Renderer(Protocol):
    """Minimal rendering interface that scenes target."""

    def clear(self) -> None: ...
    def present(self) -> None: ...


# ---------------------------------------------------------------------------
# Scene base class
# ---------------------------------------------------------------------------

class Scene(ABC):
    """
    A discrete mode of play. Scenes own their own state and update/render
    independently. They receive input, advance their logic each tick,
    and draw themselves to a renderer.

    Scenes can be *transparent* -- meaning the scene below them on the
    stack should also render (useful for dialogue overlaying exploration,
    or menus overlaying anything). Opaque scenes occlude everything
    beneath them.
    """

    def __init__(self, game: Game, event_bus: EventBus) -> None:
        self.game = game
        self.event_bus = event_bus
        self.transparent: bool = False
        self.accepts_input: bool = True
        self._active: bool = False

    @property
    def is_active(self) -> bool:
        return self._active

    def enter(self) -> None:
        """Called when this scene becomes the top of the stack."""
        self._active = True

    def exit(self) -> None:
        """Called when this scene is removed from the stack."""
        self._active = False

    def pause(self) -> None:
        """Called when another scene is pushed on top of this one."""
        pass

    def resume(self) -> None:
        """Called when the scene above this one is popped."""
        pass

    @abstractmethod
    def update(self, delta: float) -> None:
        """Advance scene logic by *delta* seconds."""
        ...

    @abstractmethod
    def handle_input(self, action: str, pressed: bool) -> None:
        """
        Process an input action.

        Parameters
        ----------
        action:
            Semantic action name (e.g. "move_north", "confirm", "cancel",
            "spirit_vision", "menu").
        pressed:
            True on key-down, False on key-up.
        """
        ...

    @abstractmethod
    def render(self, renderer: Any) -> None:
        """Draw the scene to the given renderer."""
        ...


# ---------------------------------------------------------------------------
# Exploration scene
# ---------------------------------------------------------------------------

class ExplorationScene(Scene):
    """
    The heartbeat mode. Aoi walks through Tokyo, material and spirit
    worlds layered beneath their feet. NPCs go about their lives.
    Spirits flicker at the edge of sight.

    This scene owns:
    - Grid-based movement via the MovementController
    - Spirit vision toggle
    - NPC proximity detection and interaction
    - Event triggers embedded in tiles (dialogue, combat, vignettes)
    - Ambient spirit encounter checks
    - Ma accumulation when the player stands still
    """

    def __init__(self, game: Game, event_bus: EventBus) -> None:
        super().__init__(game, event_bus)
        self.transparent = False
        self._idle_timer: float = 0.0
        self._idle_ma_threshold: float = 3.0  # seconds still before ma accrues
        self._encounter_cooldown: float = 0.0
        self._input_buffer: dict[str, bool] = {}
        self._last_toast: Optional[str] = None

    # -- lifecycle --

    def enter(self) -> None:
        super().enter()
        self.game.transition_to(GameState.EXPLORATION)
        self._idle_timer = 0.0
        logger.info("Entered exploration scene in %s", self.game.current_district)

    def exit(self) -> None:
        super().exit()
        self._input_buffer.clear()

    # -- update --

    def update(self, delta: float) -> None:
        movement = self.game.systems.get("movement")
        if movement is not None and hasattr(movement, "update"):
            movement.update(delta)

        # Idle ma accumulation
        self._idle_timer += delta
        if self._idle_timer >= self._idle_ma_threshold:
            excess = self._idle_timer - self._idle_ma_threshold
            thresholds = self.game.ma.accumulate(
                excess * 0.5, context="exploration_stillness"
            )
            for t in thresholds:
                self.event_bus.emit(GameEvent(
                    event_type=EventType.MA_THRESHOLD_CROSSED,
                    data={"threshold": t},
                    source="exploration_scene",
                ))

        # Spirit encounter cooldown
        if self._encounter_cooldown > 0.0:
            self._encounter_cooldown = max(0.0, self._encounter_cooldown - delta)

        # NPC proximity check
        self._check_npc_proximity()

        # Vignette trigger check
        self._check_vignettes(delta)

    # -- input --

    def handle_input(self, action: str, pressed: bool) -> None:
        if not pressed:
            self._input_buffer.pop(action, None)
            return

        self._input_buffer[action] = True
        self._idle_timer = 0.0  # any input resets idle

        movement = self.game.systems.get("movement")

        # Directional movement (accept both cardinal and screen-relative names)
        direction_map = {
            "move_north": "NORTH",
            "move_south": "SOUTH",
            "move_east": "EAST",
            "move_west": "WEST",
            "move_up": "NORTH",
            "move_down": "SOUTH",
            "move_left": "WEST",
            "move_right": "EAST",
        }
        if action in direction_map and movement is not None:
            from src.exploration.movement import Direction
            direction = Direction[direction_map[action]]
            result = movement.try_move(direction)
            if result.success:
                self.game.statistics["steps_taken"] += 1
                self.event_bus.emit(GameEvent(
                    event_type=EventType.PLAYER_MOVE,
                    data={
                        "x": result.new_position.x,
                        "y": result.new_position.y,
                        "noise": result.noise_generated,
                    },
                    source="exploration_scene",
                ))
                # Process tile events
                for event_id in result.events_triggered:
                    self._process_tile_event(event_id)
                for discovery in result.discoveries:
                    self.event_bus.emit(GameEvent(
                        event_type=EventType.SECRET_DISCOVERED,
                        data={"discovery_id": discovery},
                        source="exploration_scene",
                    ))
                # Map transitions
                if result.map_transition is not None:
                    self._handle_map_transition(result.map_transition)
            return

        if action == "spirit_vision":
            self._toggle_spirit_vision()
            return

        if action == "interact":
            self._try_interact()
            return

        if action == "menu":
            self.event_bus.emit(GameEvent(
                event_type=EventType.STATE_CHANGE,
                data={"target_state": "menu"},
                source="exploration_scene",
            ))
            return

        if action == "run":
            if movement is not None:
                from src.exploration.movement import MovementMode
                movement.set_mode(MovementMode.RUNNING)
            return

        if action == "sneak":
            if movement is not None:
                from src.exploration.movement import MovementMode
                movement.set_mode(MovementMode.SNEAKING)
            return

        if action == "walk":
            if movement is not None:
                from src.exploration.movement import MovementMode
                movement.set_mode(MovementMode.WALKING)
            return

    # -- render --

    def render(self, renderer: Any) -> None:
        tile_map = self.game.current_map
        player = self.game.player
        movement = self.game.systems.get("movement")

        if hasattr(renderer, "render_map") and tile_map is not None:
            spirit_active = (
                movement.spirit_vision.active
                if movement is not None and hasattr(movement, "spirit_vision")
                else False
            )
            renderer.render_map(tile_map, spirit_active)

        if hasattr(renderer, "render_player") and player is not None and movement is not None:
            renderer.render_player(
                movement.position.x,
                movement.position.y,
                movement.facing,
            )

        # Interaction labels for nearby objects
        if hasattr(renderer, "render_interaction_labels") and tile_map is not None:
            renderer.render_interaction_labels(tile_map, movement)

        if hasattr(renderer, "render_hud"):
            renderer.render_hud(self.game)

        # Show toast for recent interactions
        if self._last_toast and hasattr(renderer, "_toasts"):
            renderer._toasts.append((self._last_toast, renderer._elapsed_ms + 2500))
            self._last_toast = None

    # -- internal helpers --

    def _toggle_spirit_vision(self) -> None:
        player = self.game.player
        if player is None:
            return
        success, flavor = player.spirit_sight.activate()
        if player.spirit_sight.active:
            player.spirit_sight.deactivate()
            self.event_bus.emit(GameEvent(
                event_type=EventType.PLAYER_SPIRIT_SIGHT_TOGGLE,
                data={"active": False},
                source="exploration_scene",
            ))
        elif success:
            self.event_bus.emit(GameEvent(
                event_type=EventType.PLAYER_SPIRIT_SIGHT_TOGGLE,
                data={"active": True, "flavor": flavor},
                source="exploration_scene",
            ))

    def _try_interact(self) -> None:
        movement = self.game.systems.get("movement")
        if movement is None:
            return

        action = movement.try_interact()
        if action is None:
            return

        from src.exploration.movement import InteractionType

        if action.interaction_type == InteractionType.TALK:
            npc_id = action.target_tile.interaction_id
            if npc_id:
                self.event_bus.emit(GameEvent(
                    event_type=EventType.DIALOGUE_START,
                    data={"npc_id": npc_id},
                    source="exploration_scene",
                ))

        elif action.interaction_type in (
            InteractionType.EXAMINE,
            InteractionType.PICK_UP,
            InteractionType.USE,
            InteractionType.OPEN,
        ):
            name = action.target_tile.metadata.get("name", "")
            verbs = {
                InteractionType.EXAMINE: "examine",
                InteractionType.PICK_UP: "pick up",
                InteractionType.USE: "use",
                InteractionType.OPEN: "open",
            }
            verb = verbs.get(action.interaction_type, "interact with")
            self._last_toast = f"You {verb} {name}."
            self.event_bus.emit(GameEvent(
                event_type=EventType.PLAYER_INTERACT,
                data={
                    "interaction": action.interaction_type.value,
                    "target_id": action.target_tile.interaction_id,
                    "coord_x": action.target_coord.x,
                    "coord_y": action.target_coord.y,
                },
                source="exploration_scene",
            ))

        elif action.interaction_type in (
            InteractionType.PRAY,
            InteractionType.LISTEN,
            InteractionType.SIT,
        ):
            # Show feedback toast
            name = action.target_tile.metadata.get("name", "")
            verbs = {
                InteractionType.PRAY: "prayed at",
                InteractionType.LISTEN: "listened to",
                InteractionType.SIT: "sat on",
            }
            verb = verbs.get(action.interaction_type, "interacted with")
            if action.ma_gain > 0.0:
                self._last_toast = f"You {verb} {name}. Ma +{action.ma_gain:.0f}"
                thresholds = self.game.ma.accumulate(
                    action.ma_gain, context=action.interaction_type.value
                )
                for t in thresholds:
                    self.event_bus.emit(GameEvent(
                        event_type=EventType.MA_THRESHOLD_CROSSED,
                        data={"threshold": t},
                        source="exploration_scene",
                    ))
            else:
                self._last_toast = f"You {verb} {name}."


    def _check_npc_proximity(self) -> None:
        """Emit events when NPCs are nearby for contextual awareness."""
        npc_registry = self.game.systems.get("npc_registry")
        movement = self.game.systems.get("movement")
        if npc_registry is None or movement is None:
            return

        current_location = self.game.current_district
        nearby_npcs = npc_registry.npcs_at_location(current_location)
        for npc in nearby_npcs:
            if not npc.state.has_been_met:
                self.event_bus.emit(GameEvent(
                    event_type=EventType.SPIRIT_ENCOUNTER
                    if npc.npc_type.value == "spirit"
                    else EventType.LOCATION_ENTER,
                    data={"npc_id": npc.id, "npc_name": npc.display_name},
                    source="exploration_scene",
                    priority=-1,
                ))

    def _process_tile_event(self, event_id: str) -> None:
        """Dispatch a tile-embedded event to the appropriate system."""
        if event_id.startswith("tile_event:"):
            trigger = event_id.split(":", 1)[1]
            if trigger.startswith("battle_"):
                self.event_bus.emit(GameEvent(
                    event_type=EventType.BATTLE_START,
                    data={"encounter_id": trigger},
                    source="exploration_scene",
                ))
            elif trigger.startswith("dialogue_"):
                self.event_bus.emit(GameEvent(
                    event_type=EventType.DIALOGUE_START,
                    data={"tree_id": trigger},
                    source="exploration_scene",
                ))
            elif trigger.startswith("vignette_"):
                self.event_bus.emit(GameEvent(
                    event_type=EventType.VIGNETTE_START,
                    data={"vignette_id": trigger},
                    source="exploration_scene",
                ))
        elif event_id == "map_transition":
            pass  # handled separately
        elif event_id.startswith("discovery:"):
            pass  # already emitted as SECRET_DISCOVERED

    def _check_vignettes(self, delta: float) -> None:
        """Poll the StoryManager for vignettes whose conditions are met."""
        story_manager = self.game.systems.get("story_manager")
        if story_manager is None:
            return
        if not hasattr(story_manager, "check_for_vignette"):
            return

        # Increment the pacing counter
        if hasattr(story_manager, "_beats_since_vignette"):
            story_manager._beats_since_vignette += 1

        # Player is idle if they haven't moved recently
        player_idle = self._idle_timer >= 1.0

        vignette = story_manager.check_for_vignette(
            self.game, player_idle=player_idle, delta=delta,
        )
        if vignette is not None:
            logger.info("Vignette triggered: %s", vignette.id)
            self.event_bus.emit(GameEvent(
                event_type=EventType.VIGNETTE_START,
                data={"vignette_id": vignette.id, "vignette": vignette},
                source="exploration_scene",
            ))

    def _handle_map_transition(self, connection: Any) -> None:
        """Transition to a new map via a MapConnection."""
        movement = self.game.systems.get("movement")
        if movement is None:
            return
        self.event_bus.emit(GameEvent(
            event_type=EventType.SCREEN_TRANSITION,
            data={
                "target_map": connection.target_map_id,
                "target_x": connection.target_coord.x,
                "target_y": connection.target_coord.y,
                "text": connection.transition_text or "",
            },
            source="exploration_scene",
        ))


# ---------------------------------------------------------------------------
# Dialogue scene
# ---------------------------------------------------------------------------

class DialogueScene(Scene):
    """
    Conversation mode. Pushes on top of exploration so the world
    remains visible beneath the dialogue box.

    Handles:
    - Text display with character-by-character reveal
    - Player choice selection (including the silence option)
    - Spirit whispers that appear at perception thresholds
    - Ma accumulation when the player chooses silence
    - Dialogue tree advancement
    - Effect application through the DialogueManager
    """

    def __init__(self, game: Game, event_bus: EventBus) -> None:
        super().__init__(game, event_bus)
        self.transparent = True  # exploration visible underneath
        self._npc_id: str = ""
        self._tree_id: str = ""
        self._dialogue_box: Optional[Any] = None
        self._waiting_for_choice: bool = False
        self._silence_timer: float = 0.0
        self._silence_ma_rate: float = 2.0  # ma per second of silence

    def enter(self) -> None:
        super().enter()
        self.game.transition_to(GameState.DIALOGUE)
        movement = self.game.systems.get("movement")
        if movement is not None and hasattr(movement, "lock_movement"):
            movement.lock_movement("dialogue")
        logger.info("Dialogue scene entered with NPC %s", self._npc_id)

    def exit(self) -> None:
        super().exit()
        movement = self.game.systems.get("movement")
        if movement is not None and hasattr(movement, "unlock_movement"):
            movement.unlock_movement()
        dialogue_mgr = self.game.systems.get("dialogue_manager")
        if dialogue_mgr is not None and dialogue_mgr.is_in_conversation:
            dialogue_mgr.end_conversation()
        self.event_bus.emit(GameEvent(
            event_type=EventType.DIALOGUE_END,
            data={"npc_id": self._npc_id},
            source="dialogue_scene",
        ))

    def configure(self, npc_id: str = "", tree_id: str = "") -> None:
        """Set conversation target before entering."""
        self._npc_id = npc_id
        self._tree_id = tree_id

    def update(self, delta: float) -> None:
        # Advance dialogue box text reveal
        if self._dialogue_box is not None and hasattr(self._dialogue_box, "update"):
            self._dialogue_box.update(delta)

        # Silence timer -- waiting without selecting accumulates ma
        if self._waiting_for_choice:
            self._silence_timer += delta
            if self._silence_timer >= 2.0:
                thresholds = self.game.ma.accumulate(
                    self._silence_ma_rate * delta,
                    context="dialogue_silence",
                )
                for t in thresholds:
                    self.event_bus.emit(GameEvent(
                        event_type=EventType.MA_THRESHOLD_CROSSED,
                        data={"threshold": t, "source": "dialogue_silence"},
                        source="dialogue_scene",
                    ))

    def handle_input(self, action: str, pressed: bool) -> None:
        if not pressed:
            return

        dialogue_mgr = self.game.systems.get("dialogue_manager")
        if dialogue_mgr is None:
            return

        if action == "confirm":
            if self._dialogue_box is not None and not self._dialogue_box.is_complete:
                self._dialogue_box.skip_to_end()
                return

            if self._waiting_for_choice:
                choices = dialogue_mgr.get_current_choices()
                if choices and self._dialogue_box is not None:
                    selected = self._dialogue_box.selected_choice
                    if 0 <= selected < len(choices):
                        choice = choices[selected]
                        if choice.is_silence:
                            self.event_bus.emit(GameEvent(
                                event_type=EventType.SILENCE_CHOSEN,
                                data={"npc_id": self._npc_id},
                                source="dialogue_scene",
                            ))
                        else:
                            self.event_bus.emit(GameEvent(
                                event_type=EventType.DIALOGUE_CHOICE,
                                data={
                                    "choice_id": choice.id,
                                    "npc_id": self._npc_id,
                                },
                                source="dialogue_scene",
                            ))
                        next_node = dialogue_mgr.make_choice(choice.id)
                        self._waiting_for_choice = False
                        self._silence_timer = 0.0
                        if next_node is None or not dialogue_mgr.is_in_conversation:
                            # Conversation has ended
                            self.event_bus.emit(GameEvent(
                                event_type=EventType.STATE_CHANGE,
                                data={"target_state": "pop_scene"},
                                source="dialogue_scene",
                            ))
                            return
                        self._advance_to_current_node(dialogue_mgr)
                return

            # Auto-advance node (no choices)
            node = dialogue_mgr.advance_auto()
            if node is None or not dialogue_mgr.is_in_conversation:
                self.event_bus.emit(GameEvent(
                    event_type=EventType.STATE_CHANGE,
                    data={"target_state": "pop_scene"},
                    source="dialogue_scene",
                ))
                return
            self._advance_to_current_node(dialogue_mgr)
            return

        if action == "cancel":
            self.event_bus.emit(GameEvent(
                event_type=EventType.STATE_CHANGE,
                data={"target_state": "pop_scene"},
                source="dialogue_scene",
            ))
            return

        if action in ("move_up", "choice_up"):
            if self._dialogue_box is not None and self._waiting_for_choice:
                self._dialogue_box.select_prev_choice()
                self._silence_timer = 0.0
            return

        if action in ("move_down", "choice_down"):
            if self._dialogue_box is not None and self._waiting_for_choice:
                self._dialogue_box.select_next_choice()
                self._silence_timer = 0.0
            return

    def render(self, renderer: Any) -> None:
        if hasattr(renderer, "render_dialogue_box") and self._dialogue_box is not None:
            renderer.render_dialogue_box(self._dialogue_box)

    # -- helpers --

    def _advance_to_current_node(self, dialogue_mgr: Any) -> None:
        """Display lines for the current node and prepare choices."""
        lines = dialogue_mgr.get_current_lines()
        choices = dialogue_mgr.get_current_choices()

        if lines and self._dialogue_box is not None:
            line = lines[0]
            self._dialogue_box.set_text(
                speaker=line.speaker,
                text=line.text,
                is_spirit=line.speaker_type.value == "spirit_whisper",
                emotion=line.tone.value,
            )

        if choices:
            self._waiting_for_choice = True
            self._silence_timer = 0.0
            if self._dialogue_box is not None:
                self._dialogue_box.set_choices([
                    {
                        "id": c.id,
                        "text": c.display_text or c.text or "...",
                        "is_silence": c.is_silence,
                        "tooltip": c.tooltip,
                    }
                    for c in choices
                ])
        else:
            self._waiting_for_choice = False

    def set_dialogue_box(self, dialogue_box: Any) -> None:
        """Inject a DialogueBox instance for rendering."""
        self._dialogue_box = dialogue_box


# ---------------------------------------------------------------------------
# Combat scene
# ---------------------------------------------------------------------------

class CombatScene(Scene):
    """
    Turn-based combat. Replaces exploration entirely -- you cannot
    walk away from what confronts you. But you can always negotiate.

    Handles:
    - Turn order via the BattleSystem
    - Action selection (attack, defend, ability, negotiate, wait, flee)
    - Ma gauge integration (waiting at the right moment builds ma)
    - Negotiation flow
    - Battle resolution and return to exploration
    """

    def __init__(self, game: Game, event_bus: EventBus) -> None:
        super().__init__(game, event_bus)
        self.transparent = False
        self._encounter_id: str = ""
        self._battle_active: bool = False
        self._selected_action: int = 0
        self._action_list: list[str] = [
            "attack", "defend", "ability", "negotiate", "wait", "flee"
        ]

    def configure(self, encounter_id: str = "", enemy_ids: Optional[list[str]] = None) -> None:
        """Set the encounter before entering."""
        self._encounter_id = encounter_id
        self._enemy_ids = enemy_ids or []

    def enter(self) -> None:
        super().enter()
        self.game.transition_to(GameState.COMBAT)
        self._battle_active = True
        self._selected_action = 0
        self.event_bus.emit(GameEvent(
            event_type=EventType.MUSIC_CHANGE,
            data={"track": "battle", "transition": "hard_cut"},
            source="combat_scene",
        ))
        logger.info("Combat scene entered: encounter=%s", self._encounter_id)

    def exit(self) -> None:
        super().exit()
        self._battle_active = False
        self.event_bus.emit(GameEvent(
            event_type=EventType.BATTLE_END,
            data={"encounter_id": self._encounter_id},
            source="combat_scene",
        ))
        self.event_bus.emit(GameEvent(
            event_type=EventType.MUSIC_CHANGE,
            data={"track": "exploration", "transition": "crossfade"},
            source="combat_scene",
        ))

    def update(self, delta: float) -> None:
        if not self._battle_active:
            return

        battle = self.game.systems.get("battle")
        if battle is not None and hasattr(battle, "update"):
            battle.update(delta)

        # Check for battle end
        if battle is not None and hasattr(battle, "is_battle_over"):
            if battle.is_battle_over:
                result = getattr(battle, "result", "victory")
                self._resolve_battle(result)

    def handle_input(self, action: str, pressed: bool) -> None:
        if not pressed or not self._battle_active:
            return

        battle = self.game.systems.get("battle")

        if action in ("move_up", "choice_up"):
            self._selected_action = (
                (self._selected_action - 1) % len(self._action_list)
            )
            return

        if action in ("move_down", "choice_down"):
            self._selected_action = (
                (self._selected_action + 1) % len(self._action_list)
            )
            return

        if action == "confirm":
            chosen = self._action_list[self._selected_action]
            self._execute_action(chosen, battle)
            return

        if action == "cancel":
            # Cancel goes back to action select from sub-menus
            self._selected_action = 0
            return

    def render(self, renderer: Any) -> None:
        battle = self.game.systems.get("battle")

        if hasattr(renderer, "render_battle"):
            renderer.render_battle(
                battle=battle,
                selected_action=self._selected_action,
                action_list=self._action_list,
                ma_state=self.game.ma,
            )

    # -- internal --

    def _execute_action(self, action_name: str, battle: Any) -> None:
        """Submit the selected action to the battle system."""
        if battle is None:
            return

        self.event_bus.emit(GameEvent(
            event_type=EventType.BATTLE_ACTION,
            data={"action": action_name, "encounter_id": self._encounter_id},
            source="combat_scene",
        ))

        if action_name == "wait":
            # Waiting in combat accumulates ma -- the tactical pause
            thresholds = self.game.ma.accumulate(5.0, context="combat_wait")
            for t in thresholds:
                self.event_bus.emit(GameEvent(
                    event_type=EventType.MA_THRESHOLD_CROSSED,
                    data={"threshold": t},
                    source="combat_scene",
                ))

        if action_name == "negotiate":
            self.event_bus.emit(GameEvent(
                event_type=EventType.NEGOTIATION_START,
                data={"encounter_id": self._encounter_id},
                source="combat_scene",
            ))

        if action_name == "flee":
            self.game.statistics["battles_fled"] += 1
            self._battle_active = False
            self.event_bus.emit(GameEvent(
                event_type=EventType.STATE_CHANGE,
                data={"target_state": "pop_scene"},
                source="combat_scene",
            ))

    def _resolve_battle(self, result: str) -> None:
        """Handle the aftermath of a battle ending."""
        self._battle_active = False

        if result == "victory":
            self.game.statistics["battles_won"] += 1
        elif result == "negotiation_success":
            self.game.statistics["spirits_befriended"] += 1
            self.event_bus.emit(GameEvent(
                event_type=EventType.NEGOTIATION_SUCCESS,
                data={"encounter_id": self._encounter_id},
                source="combat_scene",
            ))

        self.event_bus.emit(GameEvent(
            event_type=EventType.STATE_CHANGE,
            data={"target_state": "pop_scene", "battle_result": result},
            source="combat_scene",
        ))


# ---------------------------------------------------------------------------
# Menu scene
# ---------------------------------------------------------------------------

class MenuScene(Scene):
    """
    Pause and menu overlay. The world blurs beneath it but does not
    vanish. Even paused, the spirit world is faintly visible.

    Handles navigation through the pause menu, sub-menus (inventory,
    bestiary, quest log, map, crafting, settings, save/load), and
    returning to play.
    """

    def __init__(self, game: Game, event_bus: EventBus) -> None:
        super().__init__(game, event_bus)
        self.transparent = True
        self._menu_stack: list[Any] = []
        self._current_menu: Optional[Any] = None

    def configure(self, initial_menu: Optional[Any] = None) -> None:
        """Optionally set the initial menu state."""
        self._current_menu = initial_menu

    def enter(self) -> None:
        super().enter()
        if self._current_menu is None:
            try:
                from src.ui.menus import PauseMenu
                self._current_menu = PauseMenu().menu
            except ImportError:
                logger.warning("Could not import PauseMenu; menu scene has no menu")
        logger.info("Menu scene entered")

    def exit(self) -> None:
        super().exit()
        self._menu_stack.clear()
        self._current_menu = None

    def update(self, delta: float) -> None:
        pass  # Menus are static until input

    def handle_input(self, action: str, pressed: bool) -> None:
        if not pressed or self._current_menu is None:
            return

        if action in ("move_up", "choice_up"):
            self._current_menu.move_up()
            return

        if action in ("move_down", "choice_down"):
            self._current_menu.move_down()
            return

        if action == "confirm":
            selected = self._current_menu.selected_item
            if selected is not None and selected.enabled and selected.action:
                self._handle_menu_action(selected.action)
            return

        if action in ("cancel", "menu"):
            if self._menu_stack:
                self._current_menu = self._menu_stack.pop()
            else:
                self.event_bus.emit(GameEvent(
                    event_type=EventType.STATE_CHANGE,
                    data={"target_state": "pop_scene"},
                    source="menu_scene",
                ))
            return

    def render(self, renderer: Any) -> None:
        if hasattr(renderer, "render_menu") and self._current_menu is not None:
            renderer.render_menu(self._current_menu)

    def _handle_menu_action(self, action: str) -> None:
        """Dispatch a menu action to the appropriate handler."""
        if action == "resume":
            self.event_bus.emit(GameEvent(
                event_type=EventType.STATE_CHANGE,
                data={"target_state": "pop_scene"},
                source="menu_scene",
            ))

        elif action == "title":
            self.event_bus.emit(GameEvent(
                event_type=EventType.STATE_CHANGE,
                data={"target_state": "title"},
                source="menu_scene",
            ))

        elif action == "save":
            self.event_bus.emit(GameEvent(
                event_type=EventType.GAME_SAVE,
                data={},
                source="menu_scene",
            ))

        elif action in ("inventory", "bestiary", "quests", "map",
                        "crafting", "spirit_bonds", "settings"):
            self.event_bus.emit(GameEvent(
                event_type=EventType.STATE_CHANGE,
                data={"target_state": action},
                source="menu_scene",
            ))

        elif action == "quit":
            self.event_bus.emit(GameEvent(
                event_type=EventType.STATE_CHANGE,
                data={"target_state": "quit"},
                source="menu_scene",
            ))

        elif action.startswith("save_slot_"):
            try:
                slot = int(action.split("_")[-1])
                self.event_bus.emit(GameEvent(
                    event_type=EventType.GAME_SAVE,
                    data={"slot": slot},
                    source="menu_scene",
                ))
            except ValueError:
                pass

        elif action.startswith("load_slot_"):
            try:
                slot = int(action.split("_")[-1])
                self.event_bus.emit(GameEvent(
                    event_type=EventType.GAME_LOAD,
                    data={"slot": slot},
                    source="menu_scene",
                ))
            except ValueError:
                pass


# ---------------------------------------------------------------------------
# Crafting scene
# ---------------------------------------------------------------------------

class CraftingScene(Scene):
    """
    The workshop. Can be a kitchen table, a park bench, or a
    convenience store counter at midnight. Overlays exploration.

    Handles recipe browsing, condition checks, crafting execution,
    and the narrative of making things that matter.
    """

    def __init__(self, game: Game, event_bus: EventBus) -> None:
        super().__init__(game, event_bus)
        self.transparent = True
        self._selected_recipe: int = 0
        self._available_recipes: list[Any] = []
        self._preview_mode: bool = False

    def enter(self) -> None:
        super().enter()
        self.game.transition_to(GameState.CRAFTING)
        workshop = self.game.systems.get("workshop")
        if workshop is not None and hasattr(workshop, "available_recipes"):
            self._available_recipes = workshop.available_recipes()
        self._selected_recipe = 0
        logger.info("Crafting scene entered with %d recipes", len(self._available_recipes))

    def exit(self) -> None:
        super().exit()
        self._available_recipes.clear()

    def update(self, delta: float) -> None:
        pass  # Crafting is input-driven

    def handle_input(self, action: str, pressed: bool) -> None:
        if not pressed:
            return

        if action in ("move_up", "choice_up"):
            if self._available_recipes:
                self._selected_recipe = (
                    (self._selected_recipe - 1) % len(self._available_recipes)
                )
            return

        if action in ("move_down", "choice_down"):
            if self._available_recipes:
                self._selected_recipe = (
                    (self._selected_recipe + 1) % len(self._available_recipes)
                )
            return

        if action == "confirm":
            self._attempt_craft()
            return

        if action in ("cancel", "menu"):
            self.event_bus.emit(GameEvent(
                event_type=EventType.STATE_CHANGE,
                data={"target_state": "pop_scene"},
                source="crafting_scene",
            ))
            return

    def render(self, renderer: Any) -> None:
        if hasattr(renderer, "render_crafting"):
            renderer.render_crafting(
                recipes=self._available_recipes,
                selected=self._selected_recipe,
                game=self.game,
            )

    def _attempt_craft(self) -> None:
        if not self._available_recipes:
            return
        recipe = self._available_recipes[self._selected_recipe]
        workshop = self.game.systems.get("workshop")
        if workshop is None:
            return

        result = workshop.craft(recipe.id)
        if result.outcome.value in ("success", "great_success"):
            self.event_bus.emit(GameEvent(
                event_type=EventType.CRAFT_SUCCESS,
                data={
                    "recipe_id": recipe.id,
                    "item_id": result.produced_item_id,
                    "narrative": result.narrative,
                },
                source="crafting_scene",
            ))
            self.game.statistics["items_crafted"] += 1
        elif result.outcome.value == "curious":
            self.event_bus.emit(GameEvent(
                event_type=EventType.CRAFT_CURIOUS,
                data={
                    "recipe_id": recipe.id,
                    "item_id": result.produced_item_id,
                    "narrative": result.narrative,
                },
                source="crafting_scene",
            ))

        # Refresh available recipes after crafting
        self._available_recipes = workshop.available_recipes()
        if self._selected_recipe >= len(self._available_recipes):
            self._selected_recipe = max(0, len(self._available_recipes) - 1)


# ---------------------------------------------------------------------------
# Vignette scene
# ---------------------------------------------------------------------------

class VignetteScene(Scene):
    """
    The quiet moments. A cat watching rain. Grandmother humming a tune
    she won't explain. The city at 4am when even the spirits are asleep.

    Vignettes are cinematic pauses where the game breathes. Minimal
    input -- mostly observing, with occasional gentle choices. Ma
    accumulates rapidly. The world clock slows. Music strips down.

    This is where the game earns its title.
    """

    def __init__(self, game: Game, event_bus: EventBus) -> None:
        super().__init__(game, event_bus)
        self.transparent = False
        self._vignette_id: str = ""
        self._vignette: Optional[Any] = None
        self._current_beat_index: int = 0
        self._beat_timer: float = 0.0
        self._original_time_scale: float = 1.0
        self._waiting_for_input: bool = False

    def configure(self, vignette_id: str = "", vignette: Optional[Any] = None) -> None:
        """Set the vignette to play."""
        self._vignette_id = vignette_id
        self._vignette = vignette

    def enter(self) -> None:
        super().enter()
        self.game.transition_to(GameState.VIGNETTE)
        self._original_time_scale = self.game.clock.time_scale
        if self._vignette is not None and hasattr(self._vignette, "time_scale"):
            self.game.clock.time_scale = self._vignette.time_scale
        self._current_beat_index = 0
        self._beat_timer = 0.0
        self.event_bus.emit(GameEvent(
            event_type=EventType.VIGNETTE_START,
            data={"vignette_id": self._vignette_id},
            source="vignette_scene",
        ))
        if self._vignette is not None and hasattr(self._vignette, "music_track"):
            if self._vignette.music_track:
                self.event_bus.emit(GameEvent(
                    event_type=EventType.MUSIC_CHANGE,
                    data={
                        "track": self._vignette.music_track,
                        "transition": "ma_transition",
                    },
                    source="vignette_scene",
                ))
        logger.info("Vignette scene entered: %s", self._vignette_id)

    def exit(self) -> None:
        super().exit()
        self.game.clock.time_scale = self._original_time_scale
        self.event_bus.emit(GameEvent(
            event_type=EventType.VIGNETTE_END,
            data={"vignette_id": self._vignette_id},
            source="vignette_scene",
        ))
        self.game.statistics["vignettes_witnessed"] += 1
        self._vignette = None

    def update(self, delta: float) -> None:
        if self._vignette is None:
            return

        beats = getattr(self._vignette, "beats", [])
        if self._current_beat_index >= len(beats):
            # Vignette complete
            self.event_bus.emit(GameEvent(
                event_type=EventType.STATE_CHANGE,
                data={"target_state": "pop_scene"},
                source="vignette_scene",
            ))
            return

        beat = beats[self._current_beat_index]

        # Ma accumulation during vignettes
        ma_rate = getattr(beat, "ma_accumulation", 1.0)
        thresholds = self.game.ma.accumulate(
            ma_rate * delta, context="vignette"
        )
        for t in thresholds:
            self.event_bus.emit(GameEvent(
                event_type=EventType.MA_THRESHOLD_CROSSED,
                data={"threshold": t},
                source="vignette_scene",
            ))

        # Auto-advance beats
        if getattr(beat, "auto_advance", False) and not self._waiting_for_input:
            duration = getattr(beat, "duration", 3.0)
            self._beat_timer += delta
            if self._beat_timer >= duration:
                self._advance_beat()

    def handle_input(self, action: str, pressed: bool) -> None:
        if not pressed:
            return

        if action == "confirm":
            if self._waiting_for_input:
                self._waiting_for_input = False
            self._advance_beat()
            return

        # Choice selection within a vignette beat
        if action in ("move_up", "choice_up", "move_down", "choice_down"):
            # If the current beat has choices, navigate them
            pass  # Visual navigation handled by renderer

        if action == "cancel":
            # Allow skipping vignettes (with a penalty -- lost ma)
            self.event_bus.emit(GameEvent(
                event_type=EventType.STATE_CHANGE,
                data={"target_state": "pop_scene"},
                source="vignette_scene",
            ))

    def render(self, renderer: Any) -> None:
        if self._vignette is None:
            return

        beats = getattr(self._vignette, "beats", [])
        if self._current_beat_index < len(beats):
            beat = beats[self._current_beat_index]
            if hasattr(renderer, "render_vignette_beat"):
                renderer.render_vignette_beat(beat, self._vignette, self.game.ma)

    def _advance_beat(self) -> None:
        """Move to the next beat in the vignette."""
        self._current_beat_index += 1
        self._beat_timer = 0.0
        self._waiting_for_input = False


# ---------------------------------------------------------------------------
# Intro scene - opening narrative before exploration
# ---------------------------------------------------------------------------

class IntroScene(Scene):
    """
    A brief narrative intro that gives the player context before
    dropping them into exploration. Shows text passages that the
    player advances with confirm/any key.
    """

    _PASSAGES = [
        (
            "Something has changed in Tokyo.",
            "The veil between the material world and the spirit world\n"
            "has begun to thin. Most people don't notice.\n"
            "You are not most people.",
        ),
        (
            "Your name is Aoi.",
            "You live with your grandmother in Kichijoji, a quiet\n"
            "neighborhood where the old shrines still remember their\n"
            "purpose. Lately, you've been seeing things at the edges\n"
            "of your vision — shapes that flicker and vanish.",
        ),
        (
            "This morning, you woke to silence.",
            "Grandmother is in the garden, as always.\n"
            "The cat, Mikan, watches from the engawa.\n"
            "The air hums with something that isn't quite wind.\n\n"
            "Perhaps you should go speak with grandmother.",
        ),
    ]

    def __init__(self, game: Game, event_bus: EventBus) -> None:
        super().__init__(game, event_bus)
        self.transparent = False
        self._passage_index: int = 0
        self._char_index: int = 0
        self._char_timer: float = 0.0
        self._chars_per_second: float = 30.0
        self._fully_revealed: bool = False
        self._fade_alpha: float = 0.0

    def enter(self) -> None:
        super().enter()
        self._passage_index = 0
        self._char_index = 0
        self._fully_revealed = False
        self._fade_alpha = 0.0

    def update(self, delta: float) -> None:
        # Fade in
        if self._fade_alpha < 1.0:
            self._fade_alpha = min(1.0, self._fade_alpha + delta * 2.0)

        if not self._fully_revealed:
            self._char_timer += delta
            heading, body = self._PASSAGES[self._passage_index]
            total_chars = len(heading) + len(body)
            chars_to_show = int(self._char_timer * self._chars_per_second)
            if chars_to_show >= total_chars:
                self._fully_revealed = True
                self._char_index = total_chars
            else:
                self._char_index = chars_to_show

    def handle_input(self, action: str, pressed: bool) -> None:
        if not pressed:
            return
        if action not in ("confirm", "cancel", "interact"):
            return

        if not self._fully_revealed:
            # Skip text reveal
            heading, body = self._PASSAGES[self._passage_index]
            self._char_index = len(heading) + len(body)
            self._fully_revealed = True
            return

        # Advance to next passage
        self._passage_index += 1
        if self._passage_index >= len(self._PASSAGES):
            # Done — transition to exploration
            self.event_bus.emit(GameEvent(
                event_type=EventType.STATE_CHANGE,
                data={"target_state": "start_exploration"},
                source="intro_scene",
            ))
            return

        self._char_index = 0
        self._char_timer = 0.0
        self._fully_revealed = False

    def render(self, renderer: Any) -> None:
        if self._passage_index >= len(self._PASSAGES):
            return
        if hasattr(renderer, "render_intro"):
            heading, body = self._PASSAGES[self._passage_index]
            renderer.render_intro(
                heading, body,
                self._char_index, self._fade_alpha,
                self._fully_revealed,
            )


# ---------------------------------------------------------------------------
# Title scene
# ---------------------------------------------------------------------------

class TitleScene(Scene):
    """
    The first thing you see. Cherry blossoms. A shakuhachi. The title
    fading in like a spirit becoming visible. Then the menu: New Journey,
    Continue, Settings, Quit.

    This scene wraps the TitleScreen from menus.py and routes its
    actions into the scene manager.
    """

    def __init__(self, game: Game, event_bus: EventBus) -> None:
        super().__init__(game, event_bus)
        self.transparent = False
        self._title_screen: Optional[Any] = None

    def enter(self) -> None:
        super().enter()
        self.game.transition_to(GameState.TITLE)
        try:
            from src.ui.menus import TitleScreen
            self._title_screen = TitleScreen()
            # Enable "Continue" if saves exist
            save_system = self.game.systems.get("save_system")
            if save_system is not None:
                self._title_screen.check_saves(save_system.any_saves_exist())
        except ImportError:
            logger.warning("Could not import TitleScreen")
        logger.info("Title scene entered")

    def exit(self) -> None:
        super().exit()
        self._title_screen = None

    def update(self, delta: float) -> None:
        if self._title_screen is not None and hasattr(self._title_screen, "update"):
            self._title_screen.update(delta)

    def handle_input(self, action: str, pressed: bool) -> None:
        if not pressed or self._title_screen is None:
            return

        if self._title_screen.state != "menu_ready":
            # Skip to menu
            self._title_screen.state = "menu_ready"
            self._title_screen.title_opacity = 1.0
            self._title_screen.subtitle_opacity = 1.0
            self._title_screen.menu_opacity = 1.0
            return

        menu = self._title_screen.menu

        if action in ("move_up", "choice_up"):
            menu.move_up()
            return

        if action in ("move_down", "choice_down"):
            menu.move_down()
            return

        if action == "confirm":
            selected = menu.selected_item
            if selected is None or not selected.enabled:
                return
            if selected.action == "new_game":
                self.event_bus.emit(GameEvent(
                    event_type=EventType.STATE_CHANGE,
                    data={"target_state": "new_game"},
                    source="title_scene",
                ))
            elif selected.action == "load_game":
                self.event_bus.emit(GameEvent(
                    event_type=EventType.GAME_LOAD,
                    data={},
                    source="title_scene",
                ))
            elif selected.action == "settings":
                self.event_bus.emit(GameEvent(
                    event_type=EventType.STATE_CHANGE,
                    data={"target_state": "settings"},
                    source="title_scene",
                ))
            elif selected.action == "quit":
                self.event_bus.emit(GameEvent(
                    event_type=EventType.STATE_CHANGE,
                    data={"target_state": "quit"},
                    source="title_scene",
                ))
            return

    def render(self, renderer: Any) -> None:
        if hasattr(renderer, "render_title_screen") and self._title_screen is not None:
            renderer.render_title_screen(self._title_screen)


# ---------------------------------------------------------------------------
# Scene Manager
# ---------------------------------------------------------------------------

class SceneManager:
    """
    The stage director. Manages a stack of scenes, routes input
    to the topmost scene, updates and renders the visible stack,
    and subscribes to the event bus for scene transitions.

    The stack model means scenes can overlay each other: dialogue
    on top of exploration, menus on top of anything, combat replacing
    everything. Push to focus, pop to return, replace to transform.
    """

    def __init__(self, game: Game, event_bus: EventBus) -> None:
        self.game = game
        self.event_bus = event_bus
        self._scene_stack: list[Scene] = []
        self._pending_operations: list[tuple[str, Optional[Scene]]] = []
        self._renderer: Any = None  # Lazily created PygameRenderer

        # Subscribe to events that trigger scene changes
        self.event_bus.subscribe(
            EventType.BATTLE_START,
            self._on_battle_start,
            priority=100,
            name="scene_manager",
        )
        self.event_bus.subscribe(
            EventType.DIALOGUE_START,
            self._on_dialogue_start,
            priority=100,
            name="scene_manager",
        )
        self.event_bus.subscribe(
            EventType.VIGNETTE_START,
            self._on_vignette_start,
            priority=100,
            name="scene_manager",
        )
        self.event_bus.subscribe(
            EventType.STATE_CHANGE,
            self._on_state_change,
            priority=50,
            name="scene_manager",
        )
        self.event_bus.subscribe(
            EventType.CRAFT_START,
            self._on_craft_start,
            priority=100,
            name="scene_manager",
        )
        self.event_bus.subscribe(
            EventType.SCREEN_TRANSITION,
            self._on_screen_transition,
            priority=100,
            name="scene_manager",
        )
        self.event_bus.subscribe(
            EventType.GAME_SAVE,
            self._on_game_save,
            priority=100,
            name="scene_manager",
        )
        self.event_bus.subscribe(
            EventType.GAME_LOAD,
            self._on_game_load,
            priority=100,
            name="scene_manager",
        )

    # -- Stack operations --

    def push_scene(self, scene: Scene) -> None:
        """Push a scene onto the stack. The current top is paused."""
        if self._scene_stack:
            self._scene_stack[-1].pause()
        self._scene_stack.append(scene)
        scene.enter()
        logger.debug(
            "Scene pushed: %s (stack depth: %d)",
            type(scene).__name__,
            len(self._scene_stack),
        )

    def pop_scene(self) -> Optional[Scene]:
        """Pop the top scene. The scene beneath resumes."""
        if not self._scene_stack:
            return None
        scene = self._scene_stack.pop()
        scene.exit()
        if self._scene_stack:
            self._scene_stack[-1].resume()
        logger.debug(
            "Scene popped: %s (stack depth: %d)",
            type(scene).__name__,
            len(self._scene_stack),
        )
        return scene

    def replace_scene(self, scene: Scene) -> Optional[Scene]:
        """Replace the top scene. The old scene exits, the new one enters."""
        old = None
        if self._scene_stack:
            old = self._scene_stack.pop()
            old.exit()
        self._scene_stack.append(scene)
        scene.enter()
        logger.debug(
            "Scene replaced: %s -> %s (stack depth: %d)",
            type(old).__name__ if old else "None",
            type(scene).__name__,
            len(self._scene_stack),
        )
        return old

    def clear_to(self, scene: Scene) -> None:
        """Clear the entire stack and set a single scene."""
        while self._scene_stack:
            self._scene_stack.pop().exit()
        self._scene_stack.append(scene)
        scene.enter()
        logger.debug("Scene stack cleared to: %s", type(scene).__name__)

    @property
    def current_scene(self) -> Optional[Scene]:
        """The scene currently on top of the stack."""
        return self._scene_stack[-1] if self._scene_stack else None

    @property
    def stack_depth(self) -> int:
        return len(self._scene_stack)

    # -- Per-frame operations --

    def update(self, delta: float, game: Optional[Game] = None) -> None:
        """Update all active scenes. Only the top scene gets full update."""
        # Process any pending scene operations first
        self._flush_pending()

        if not self._scene_stack:
            return

        # Update the top scene
        self._scene_stack[-1].update(delta)

    def handle_input(self, action: str, pressed: bool) -> None:
        """Route input to the topmost scene that accepts it."""
        for scene in reversed(self._scene_stack):
            if scene.accepts_input:
                scene.handle_input(action, pressed)
                return  # Only the topmost accepting scene gets input

    def render(self, surface_or_renderer: Any, game: Optional[Game] = None) -> None:
        """
        Render the scene stack. Transparent scenes allow scenes beneath
        them to render first, creating overlays.

        Accepts either:
          - render(surface, game) -- called by GameLoop with a pygame.Surface
          - render(renderer)      -- legacy single-arg form
        """
        if not self._scene_stack:
            return

        # Determine the renderer to pass to scenes
        renderer = surface_or_renderer
        try:
            import pygame
            if isinstance(surface_or_renderer, pygame.Surface):
                # Called with (surface, game) -- need a real renderer
                if self._renderer is None:
                    self._renderer = self._create_renderer(surface_or_renderer)
                renderer = self._renderer
        except ImportError:
            pass

        # Find the lowest scene that needs to render
        render_from = len(self._scene_stack) - 1
        for i in range(len(self._scene_stack) - 1, -1, -1):
            if not self._scene_stack[i].transparent:
                render_from = i
                break

        # Render from bottom to top
        for i in range(render_from, len(self._scene_stack)):
            self._scene_stack[i].render(renderer)

    def _create_renderer(self, surface: Any) -> Any:
        """Lazily create a PygameRenderer for the given surface."""
        try:
            from src.ui.pygame_renderer import PygameRenderer
            from src.ui.renderer import Camera
            camera = Camera(
                x=0.0, y=0.0,
                viewport_width=surface.get_width(),
                viewport_height=surface.get_height(),
            )
            return PygameRenderer(screen=surface, camera=camera)
        except Exception as e:
            logger.warning("Could not create PygameRenderer: %s", e)
            return surface  # Fallback: pass the surface directly

    # -- Deferred operations --

    def _schedule(self, operation: str, scene: Optional[Scene] = None) -> None:
        """Schedule a scene operation to execute at the start of the next update."""
        self._pending_operations.append((operation, scene))

    def _flush_pending(self) -> None:
        """Execute all pending scene operations."""
        ops = self._pending_operations.copy()
        self._pending_operations.clear()
        for op, scene in ops:
            if op == "push" and scene is not None:
                self.push_scene(scene)
            elif op == "pop":
                self.pop_scene()
            elif op == "replace" and scene is not None:
                self.replace_scene(scene)
            elif op == "clear_to" and scene is not None:
                self.clear_to(scene)

    # -- Event handlers --

    def _on_battle_start(self, event: GameEvent) -> None:
        """Push a combat scene when a battle begins."""
        combat = CombatScene(self.game, self.event_bus)
        combat.configure(
            encounter_id=event.data.get("encounter_id", ""),
            enemy_ids=event.data.get("enemy_ids"),
        )
        self._schedule("push", combat)

    def _on_dialogue_start(self, event: GameEvent) -> None:
        """Push a dialogue scene when a conversation begins."""
        dialogue = DialogueScene(self.game, self.event_bus)
        npc_id = event.data.get("npc_id", "")
        tree_id = event.data.get("tree_id", "")
        dialogue.configure(npc_id=npc_id, tree_id=tree_id)

        # Create a dialogue box for the scene
        try:
            from src.ui.menus import DialogueBox
            dlg_box = DialogueBox()
            dialogue.set_dialogue_box(dlg_box)
        except ImportError:
            dlg_box = None

        # Try to start the conversation via DialogueManager
        conversation_started = False
        dialogue_mgr = self.game.systems.get("dialogue_manager")
        if dialogue_mgr is not None:
            if not tree_id and npc_id:
                try:
                    context = self._build_dialogue_context(npc_id)
                    trees = dialogue_mgr.get_available_trees(npc_id, context)
                    if trees:
                        tree_id = trees[0].id
                except Exception as e:
                    logger.warning("Failed to find dialogue tree: %s", e)

            if tree_id:
                try:
                    context = self._build_dialogue_context(npc_id)
                    conversation = dialogue_mgr.start_conversation(tree_id, context)
                    if conversation is not None:
                        conversation_started = True
                except Exception as e:
                    logger.warning("Failed to start conversation: %s", e)

        # If no conversation could be started, show fallback text
        if not conversation_started and dlg_box is not None:
            # Look up a friendly name from the tile metadata
            tile_map = self.game.current_map
            name = npc_id.replace("_", " ").title()
            if hasattr(tile_map, "tiles"):
                for tile in tile_map.tiles.values():
                    if (tile.interaction_id == npc_id
                            and tile.metadata.get("name")):
                        name = tile.metadata["name"]
                        break
            dlg_box.set_text(
                speaker=name,
                text="...",
            )

        self._schedule("push", dialogue)

    def _on_vignette_start(self, event: GameEvent) -> None:
        """Push a vignette scene."""
        vignette_scene = VignetteScene(self.game, self.event_bus)
        vignette_scene.configure(
            vignette_id=event.data.get("vignette_id", ""),
            vignette=event.data.get("vignette"),
        )
        self._schedule("push", vignette_scene)

    def _on_craft_start(self, event: GameEvent) -> None:
        """Push a crafting scene."""
        crafting = CraftingScene(self.game, self.event_bus)
        self._schedule("push", crafting)

    def _on_state_change(self, event: GameEvent) -> None:
        """Handle generic state change requests."""
        target = event.data.get("target_state", "")

        if target == "pop_scene":
            self._schedule("pop")

        elif target == "menu":
            menu = MenuScene(self.game, self.event_bus)
            self._schedule("push", menu)

        elif target == "title":
            title = TitleScene(self.game, self.event_bus)
            self._schedule("clear_to", title)

        elif target == "new_game":
            intro = IntroScene(self.game, self.event_bus)
            self._schedule("clear_to", intro)

        elif target == "start_exploration":
            exploration = ExplorationScene(self.game, self.event_bus)
            self._schedule("clear_to", exploration)

        elif target == "quit":
            self.game.running = False

    def _on_screen_transition(self, event: GameEvent) -> None:
        """Load target map and reposition the player."""
        target_map_id = event.data.get("target_map", "")
        target_x = event.data.get("target_x", 0)
        target_y = event.data.get("target_y", 0)
        text = event.data.get("text", "")

        if not target_map_id:
            logger.warning("Screen transition with no target map")
            return

        # Look up the target map in the registry
        map_registry = self.game.systems.get("map_registry")
        if map_registry is None:
            logger.warning("No map registry — cannot transition to %s", target_map_id)
            return

        movement_maps = getattr(map_registry, "_movement_maps", {})
        new_map = movement_maps.get(target_map_id)
        if new_map is None:
            logger.warning("Map '%s' not found in registry", target_map_id)
            return

        # Swap the map on the movement controller and reposition
        movement = self.game.systems.get("movement")
        if movement is not None:
            from src.exploration.movement import TileCoord
            movement.tile_map = new_map
            movement.position = TileCoord(target_x, target_y)
            movement.tiles_visited = {(target_x, target_y)}

        # Update game state
        self.game.current_map = new_map

        logger.info(
            "Map transition: -> %s at (%d, %d)%s",
            target_map_id, target_x, target_y,
            f" — {text}" if text else "",
        )

        # Show transition text as a toast on the exploration scene
        if text:
            for scene in reversed(self._scene_stack):
                if isinstance(scene, ExplorationScene):
                    scene._last_toast = text
                    break

    # -- Save / Load --

    def _on_game_save(self, event: GameEvent) -> None:
        """Handle save request — push a save slot selection menu."""
        slot = event.data.get("slot")
        if slot is not None:
            # Direct save to a specific slot (from save slot menu)
            self._execute_save(slot)
        else:
            # Show save slot selection
            self._push_save_slot_menu(mode="save")

    def _on_game_load(self, event: GameEvent) -> None:
        """Handle load request — push a load slot selection menu."""
        slot = event.data.get("slot")
        if slot is not None:
            self._execute_load(slot)
        else:
            self._push_save_slot_menu(mode="load")

    def _push_save_slot_menu(self, mode: str = "save") -> None:
        """Build and push a save/load slot selection menu."""
        from src.ui.menus import MenuState, MenuItem, MenuType

        save_system = self.game.systems.get("save_system")
        if save_system is None:
            logger.warning("No save system available")
            return

        all_metadata = save_system.get_all_metadata()
        items = []

        for slot in range(1, save_system.MAX_SLOTS + 1):
            meta = all_metadata.get(slot)
            if meta is not None:
                label = (
                    f"Slot {slot}: {meta.location} — "
                    f"Day {meta.day}, {meta.time_of_day} "
                    f"({meta.play_time_formatted})"
                )
                description = f"Chapter {meta.chapter}: {meta.chapter_name}"
            else:
                label = f"Slot {slot}: — Empty —"
                description = ""
            items.append(MenuItem(
                label=label,
                description=description,
                action=f"{mode}_slot_{slot}",
                enabled=(True if mode == "save" else meta is not None),
            ))

        title = "Save Game" if mode == "save" else "Load Game"
        menu = MenuState(
            menu_type=MenuType.SAVE_LOAD,
            title=title,
            items=items,
        )

        save_load_scene = MenuScene(self.game, self.event_bus)
        save_load_scene.configure(initial_menu=menu)
        save_load_scene._save_load_mode = mode
        self._schedule("push", save_load_scene)

    def _execute_save(self, slot: int) -> None:
        """Serialize current game state and write to slot."""
        save_system = self.game.systems.get("save_system")
        if save_system is None:
            return

        save_data = self._build_save_data()
        success = save_system.save(slot, save_data)

        toast = f"Game saved to slot {slot}." if success else "Save failed!"
        logger.info("Save to slot %d: %s", slot, "OK" if success else "FAILED")

        # Pop the save menu, show toast on exploration
        self._schedule("pop")
        for scene in reversed(self._scene_stack):
            if isinstance(scene, ExplorationScene):
                scene._last_toast = toast
                break

    def _execute_load(self, slot: int) -> None:
        """Load game state from slot and restore."""
        save_system = self.game.systems.get("save_system")
        if save_system is None:
            return

        save_data = save_system.load(slot)
        if save_data is None:
            logger.warning("Failed to load slot %d", slot)
            return

        self._restore_save_data(save_data)
        logger.info("Game loaded from slot %d", slot)

        # Clear stack and start exploration at saved location
        exploration = ExplorationScene(self.game, self.event_bus)
        self._schedule("clear_to", exploration)

    def _build_save_data(self) -> "Any":
        """Serialize current Game into a SaveData."""
        from src.saves.save_system import SaveData, SaveMetadata

        movement = self.game.systems.get("movement")
        player = self.game.player
        clock = self.game.clock

        # Build metadata
        metadata = SaveMetadata(
            slot=0,
            save_name="Manual Save",
            timestamp="",  # filled by SaveSystem.save()
            play_time_seconds=self.game.statistics.get("play_time", 0.0),
            chapter=self.game.flags.get("current_chapter", 1),
            chapter_name=self.game.flags.get("current_chapter_name", "The Thinning"),
            location=self.game.current_map.name if self.game.current_map else "Unknown",
            district=self.game.current_district or "kichijoji",
            level=1,
            spirit_bonds=self.game.statistics.get("spirits_befriended", 0),
            day=clock.day,
            season=clock.season.value,
            time_of_day=clock.time_of_day.value,
            ma_total=self.game.ma.lifetime_ma,
        )

        # Player position
        player_data = {}
        if movement is not None:
            player_data["x"] = movement.position.x
            player_data["y"] = movement.position.y
            player_data["map_id"] = (
                movement.tile_map.map_id if movement.tile_map else "kichijoji_start"
            )
        if player is not None:
            try:
                player_data["spirit_sight_level"] = player.spirit_sight.level.value
            except AttributeError:
                pass

        return SaveData(
            metadata=metadata,
            player=player_data,
            clock={
                "day": clock.day,
                "hour": clock.hour,
                "season": clock.season.value,
                "moon_day": clock.moon_day,
                "time_scale": clock.time_scale,
            },
            spirit_tide={
                "global_level": self.game.spirit_tide.global_level,
                "district_modifiers": dict(self.game.spirit_tide.district_modifiers),
            },
            ma_state={
                "current_ma": self.game.ma.current_ma,
                "max_ma": self.game.ma.max_ma,
                "lifetime_ma": self.game.ma.lifetime_ma,
                "accumulation_rate": self.game.ma.accumulation_rate,
                "decay_rate": self.game.ma.decay_rate,
            },
            flags=dict(self.game.flags),
            statistics=dict(self.game.statistics),
            vignettes_seen=list(self.game.flags.get("vignettes_seen", [])),
        )

    def _restore_save_data(self, save_data: "Any") -> None:
        """Restore Game state from a SaveData."""
        from src.engine.game import Season

        # Clock
        clock_data = save_data.clock
        if clock_data:
            self.game.clock.day = clock_data.get("day", 1)
            self.game.clock.hour = clock_data.get("hour", 6.0)
            season_val = clock_data.get("season", "spring")
            try:
                self.game.clock.season = Season(season_val)
            except ValueError:
                pass
            self.game.clock.moon_day = clock_data.get("moon_day", 0)
            self.game.clock.time_scale = clock_data.get("time_scale", 1.0)

        # Ma
        ma_data = save_data.ma_state
        if ma_data:
            self.game.ma.current_ma = ma_data.get("current_ma", 0.0)
            self.game.ma.max_ma = ma_data.get("max_ma", 100.0)
            self.game.ma.lifetime_ma = ma_data.get("lifetime_ma", 0.0)
            self.game.ma.accumulation_rate = ma_data.get("accumulation_rate", 1.0)
            self.game.ma.decay_rate = ma_data.get("decay_rate", 0.5)

        # Spirit tide
        tide_data = save_data.spirit_tide
        if tide_data:
            self.game.spirit_tide.global_level = tide_data.get("global_level", 0.3)
            self.game.spirit_tide.district_modifiers = tide_data.get(
                "district_modifiers", {}
            )

        # Flags and statistics
        if save_data.flags:
            self.game.flags = dict(save_data.flags)
        if save_data.statistics:
            self.game.statistics = dict(save_data.statistics)

        # Restore player position and map
        player_data = save_data.player
        if player_data:
            map_id = player_data.get("map_id", "kichijoji_start")
            px = player_data.get("x", 4)
            py = player_data.get("y", 6)

            map_registry = self.game.systems.get("map_registry")
            movement = self.game.systems.get("movement")
            if map_registry is not None and movement is not None:
                from src.exploration.movement import TileCoord
                movement_maps = getattr(map_registry, "_movement_maps", {})
                target_map = movement_maps.get(map_id)
                if target_map is not None:
                    self.game.current_map = target_map
                    movement.tile_map = target_map
                    movement.position = TileCoord(px, py)

            self.game.current_district = save_data.metadata.district

    # -- Context building --

    def _build_dialogue_context(self, npc_id: str) -> Any:
        """Assemble a DialogueContext from current game state."""
        try:
            from src.characters.dialogue import DialogueContext
        except ImportError:
            return None

        player = self.game.player
        context = DialogueContext()

        context.flags = dict(self.game.flags)
        context.npc_id = npc_id

        if player is not None:
            context.ma_level = self.game.ma.current_ma
            context.time_of_day = self.game.clock.time_of_day.value

            try:
                from src.characters.player import StatType
                context.stats = {
                    st.value: player.stats.get(st).effective
                    for st in StatType
                }
            except (ImportError, AttributeError):
                context.stats = {}

            try:
                context.inventory_ids = set(player.inventory.items.keys())
            except AttributeError:
                context.inventory_ids = set()

            try:
                context.emotional_state = player.emotional_state.primary.value
            except AttributeError:
                context.emotional_state = "neutral"

            try:
                context.memory_ids = set(player.memories.memories.keys())
            except AttributeError:
                context.memory_ids = set()

            try:
                context.spirit_sight_level = player.spirit_sight.level.value
                context.spirit_sight_active = player.spirit_sight.active
            except AttributeError:
                pass

        # NPC mood
        npc_registry = self.game.systems.get("npc_registry")
        if npc_registry is not None:
            try:
                npc = npc_registry.get(npc_id)
                if npc is not None:
                    context.npc_mood = npc.state.mood
            except (AttributeError, TypeError):
                pass

        return context
