"""
Ma no Kuni - Event System

Everything that happens in the world is an event.
Some events are thunder. Some are the silence after thunder.
The event system treats both with equal importance.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class EventType(Enum):
    """All the things that can happen between two worlds."""
    # Game state
    STATE_CHANGE = auto()
    GAME_SAVE = auto()
    GAME_LOAD = auto()

    # Player
    PLAYER_MOVE = auto()
    PLAYER_INTERACT = auto()
    PLAYER_SPIRIT_SIGHT_TOGGLE = auto()
    PLAYER_STAT_CHANGE = auto()
    PLAYER_LEVEL_UP = auto()

    # World
    TIME_ADVANCE = auto()
    SEASON_CHANGE = auto()
    PERMEABILITY_CHANGE = auto()
    SPIRIT_SURGE = auto()
    WEATHER_CHANGE = auto()
    DISTRICT_ENTER = auto()
    LOCATION_ENTER = auto()

    # Ma
    MA_ACCUMULATE = auto()
    MA_THRESHOLD_CROSSED = auto()
    MA_DECAY = auto()
    MA_MOMENT_START = auto()
    MA_MOMENT_END = auto()

    # Spirit
    SPIRIT_ENCOUNTER = auto()
    SPIRIT_BOND_FORMED = auto()
    SPIRIT_BOND_LEVEL_UP = auto()
    SPIRIT_CORRUPTION_DETECTED = auto()
    SPIRIT_PURIFIED = auto()
    TSUKUMOGAMI_AWAKENING = auto()

    # Combat
    BATTLE_START = auto()
    BATTLE_END = auto()
    BATTLE_ACTION = auto()
    NEGOTIATION_START = auto()
    NEGOTIATION_SUCCESS = auto()

    # Dialogue
    DIALOGUE_START = auto()
    DIALOGUE_CHOICE = auto()
    DIALOGUE_END = auto()
    SILENCE_CHOSEN = auto()       # The player chose to say nothing

    # Narrative
    QUEST_STARTED = auto()
    QUEST_UPDATED = auto()
    QUEST_COMPLETED = auto()
    QUEST_FAILED = auto()
    VIGNETTE_START = auto()
    VIGNETTE_END = auto()
    CHAPTER_START = auto()
    MEMORY_UNLOCKED = auto()

    # Discovery
    ITEM_FOUND = auto()
    SECRET_DISCOVERED = auto()
    LORE_FRAGMENT_FOUND = auto()
    BESTIARY_UPDATED = auto()
    RECIPE_LEARNED = auto()
    MA_SPOT_FOUND = auto()

    # Crafting
    CRAFT_START = auto()
    CRAFT_SUCCESS = auto()
    CRAFT_CURIOUS = auto()       # Failed craft produces curious item

    # Relationship
    RELATIONSHIP_CHANGE = auto()
    RELATIONSHIP_MILESTONE = auto()

    # Audio
    MUSIC_CHANGE = auto()
    AMBIENT_CHANGE = auto()
    SOUND_EFFECT = auto()

    # Visual
    SCREEN_TRANSITION = auto()
    CAMERA_SHAKE = auto()
    PARTICLE_SPAWN = auto()


@dataclass
class GameEvent:
    """A single event in the world."""
    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = ""           # What system generated this event
    priority: int = 0          # Higher = processed first
    consumed: bool = False     # Set to True to prevent further handling
    timestamp: float = 0.0

    def consume(self) -> None:
        """Mark this event as handled."""
        self.consumed = True


class EventBus:
    """
    The nervous system of the game. Events flow through here
    like spirit energy through ley lines.

    Systems subscribe to events they care about.
    The order of delivery matters - some events cascade.
    """

    def __init__(self):
        self._subscribers: Dict[EventType, List[dict]] = {}
        self._global_subscribers: List[dict] = []
        self._event_queue: List[GameEvent] = []
        self._event_history: List[GameEvent] = []
        self._history_limit: int = 1000

    def subscribe(self, event_type: EventType, callback: Callable,
                  priority: int = 0, name: str = "") -> None:
        """Subscribe to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append({
            "callback": callback,
            "priority": priority,
            "name": name,
        })
        # Sort by priority (highest first)
        self._subscribers[event_type].sort(
            key=lambda s: s["priority"], reverse=True
        )

    def subscribe_all(self, callback: Callable, name: str = "") -> None:
        """Subscribe to ALL events. Use sparingly."""
        self._global_subscribers.append({
            "callback": callback,
            "name": name,
        })

    def emit(self, event: GameEvent) -> None:
        """Add an event to the queue."""
        self._event_queue.append(event)

    def emit_immediate(self, event: GameEvent) -> None:
        """Process an event immediately, bypassing the queue."""
        self._dispatch(event)

    def process_queue(self) -> List[GameEvent]:
        """Process all queued events. Returns list of processed events."""
        # Sort by priority
        self._event_queue.sort(key=lambda e: e.priority, reverse=True)

        processed = []
        while self._event_queue:
            event = self._event_queue.pop(0)
            self._dispatch(event)
            processed.append(event)

            # Keep history
            self._event_history.append(event)
            if len(self._event_history) > self._history_limit:
                self._event_history.pop(0)

        return processed

    def _dispatch(self, event: GameEvent) -> None:
        """Dispatch an event to all relevant subscribers."""
        # Type-specific subscribers first
        if event.event_type in self._subscribers:
            for subscriber in self._subscribers[event.event_type]:
                if not event.consumed:
                    subscriber["callback"](event)

        # Then global subscribers
        for subscriber in self._global_subscribers:
            if not event.consumed:
                subscriber["callback"](event)

    def recent_events(self, event_type: Optional[EventType] = None,
                      count: int = 10) -> List[GameEvent]:
        """Get recent events, optionally filtered by type."""
        if event_type is None:
            return self._event_history[-count:]
        return [
            e for e in self._event_history
            if e.event_type == event_type
        ][-count:]

    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()
