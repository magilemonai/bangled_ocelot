"""
Ma no Kuni - Exploration Events System

The permeation doesn't announce itself with thunder. It seeps in through
the cracks of the ordinary: a traffic light that blinks in a rhythm only
spirits understand, a convenience store where translucent customers browse
the onigiri, a puddle that reflects a sky from another world.

This module handles random encounters, scripted events, and atmospheric
moments that make Tokyo feel alive with hidden magic.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Event classification
# ---------------------------------------------------------------------------

class EventCategory(Enum):
    """The broad types of exploration events."""
    ATMOSPHERIC = "atmospheric"
    """Mood-building moments with no gameplay impact. The world breathing."""

    ENCOUNTER = "encounter"
    """Random encounters with spirits, NPCs, or environmental hazards."""

    SCRIPTED = "scripted"
    """Story-driven events tied to flags and progression."""

    PERMEATION_EFFECT = "permeation_effect"
    """Second and third-order effects of the spirit world bleeding through.
    The mundane infrastructure of Tokyo adapting to the impossible."""

    ENVIRONMENTAL = "environmental"
    """Weather, time-of-day, and seasonal events that reshape the space."""

    DISCOVERY_HINT = "discovery_hint"
    """Subtle clues pointing toward hidden discoveries nearby."""


class EventPriority(Enum):
    """How urgently an event should be presented."""
    BACKGROUND = 0      # Ambient - can be missed without consequence
    LOW = 1             # Worth noticing but not interrupting
    NORMAL = 2          # Standard event presentation
    HIGH = 3            # Demands attention
    CRITICAL = 4        # Cannot be ignored (story events)


class EventPresentation(Enum):
    """How the event is shown to the player."""
    TEXT_OVERLAY = "text_overlay"          # Atmospheric text on screen
    DIALOGUE_BOX = "dialogue_box"         # Standard dialogue presentation
    FULL_SCENE = "full_scene"             # Takes over the screen
    AMBIENT_DETAIL = "ambient_detail"     # Subtle visual/audio cue
    NOTIFICATION = "notification"         # Small pop-up notification
    VIGNETTE = "vignette"                 # Ma-style contemplative scene


# ---------------------------------------------------------------------------
# Event conditions and triggers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EventCondition:
    """
    Conditions that must hold for an event to trigger.
    Unspecified fields are treated as 'any value is fine'.
    """
    # Location
    districts: Optional[tuple[str, ...]] = None
    map_ids: Optional[tuple[str, ...]] = None
    indoor: Optional[bool] = None

    # Time and world state
    times_of_day: Optional[tuple[str, ...]] = None
    seasons: Optional[tuple[str, ...]] = None
    moon_phases: Optional[tuple[str, ...]] = None
    min_permeability: Optional[float] = None
    max_permeability: Optional[float] = None
    weather: Optional[tuple[str, ...]] = None

    # Player state
    min_ma: Optional[float] = None
    max_ma: Optional[float] = None
    movement_mode: Optional[str] = None       # walking, running, sneaking
    spirit_vision_active: Optional[bool] = None
    min_spirit_energy: Optional[float] = None

    # Progression
    required_flags: Optional[tuple[str, ...]] = None
    forbidden_flags: Optional[tuple[str, ...]] = None
    min_story_chapter: Optional[int] = None
    max_story_chapter: Optional[int] = None

    # Cooldowns and limits
    min_steps_since_last_event: int = 0
    max_occurrences: Optional[int] = None      # None = unlimited

    def evaluate(self, context: EventContext) -> bool:
        """Evaluate all conditions against the current world context."""
        if self.districts and context.district not in self.districts:
            return False
        if self.map_ids and context.map_id not in self.map_ids:
            return False
        if self.indoor is not None and context.indoor != self.indoor:
            return False
        if self.times_of_day and context.time_of_day not in self.times_of_day:
            return False
        if self.seasons and context.season not in self.seasons:
            return False
        if self.moon_phases and context.moon_phase not in self.moon_phases:
            return False
        if self.min_permeability is not None and context.permeability < self.min_permeability:
            return False
        if self.max_permeability is not None and context.permeability > self.max_permeability:
            return False
        if self.weather and context.weather not in self.weather:
            return False
        if self.min_ma is not None and context.current_ma < self.min_ma:
            return False
        if self.max_ma is not None and context.current_ma > self.max_ma:
            return False
        if self.movement_mode and context.movement_mode != self.movement_mode:
            return False
        if self.spirit_vision_active is not None and context.spirit_vision != self.spirit_vision_active:
            return False
        if self.min_spirit_energy is not None and context.spirit_energy < self.min_spirit_energy:
            return False
        if self.required_flags:
            for flag in self.required_flags:
                if not context.flags.get(flag, False):
                    return False
        if self.forbidden_flags:
            for flag in self.forbidden_flags:
                if context.flags.get(flag, False):
                    return False
        if self.min_story_chapter is not None and context.story_chapter < self.min_story_chapter:
            return False
        if self.max_story_chapter is not None and context.story_chapter > self.max_story_chapter:
            return False

        return True


@dataclass
class EventContext:
    """Snapshot of the world state when checking event triggers."""
    # Location
    district: str = ""
    map_id: str = ""
    tile_x: int = 0
    tile_y: int = 0
    indoor: bool = False

    # Time
    time_of_day: str = ""
    season: str = ""
    moon_phase: str = ""
    hour: float = 0.0

    # World
    permeability: float = 0.0
    weather: str = "clear"

    # Player
    current_ma: float = 0.0
    movement_mode: str = "walking"
    spirit_vision: bool = False
    spirit_energy: float = 100.0
    steps_taken: int = 0

    # Progression
    flags: dict[str, Any] = field(default_factory=dict)
    story_chapter: int = 1


# ---------------------------------------------------------------------------
# Event definition
# ---------------------------------------------------------------------------

@dataclass
class EventOutcome:
    """What happens as a result of an event."""
    ma_change: float = 0.0
    spirit_energy_change: float = 0.0
    items_given: list[tuple[str, int]] = field(default_factory=list)
    items_taken: list[tuple[str, int]] = field(default_factory=list)
    flags_set: list[str] = field(default_factory=list)
    flags_cleared: list[str] = field(default_factory=list)
    permeability_change: float = 0.0
    trigger_encounter: Optional[str] = None     # Spirit encounter ID
    trigger_dialogue: Optional[str] = None      # Dialogue tree ID
    trigger_vignette: Optional[str] = None      # Vignette scene ID
    teleport_map: Optional[str] = None
    teleport_x: Optional[int] = None
    teleport_y: Optional[int] = None
    unlock_discovery: Optional[str] = None
    sound_effect: Optional[str] = None
    music_change: Optional[str] = None


@dataclass
class ExplorationEvent:
    """
    An event that can occur during exploration. Events range from tiny
    atmospheric details to full narrative scenes.
    """
    event_id: str
    name: str
    category: EventCategory
    priority: EventPriority
    presentation: EventPresentation
    condition: EventCondition

    # Content
    text: str                                     # Primary display text
    text_variants: list[str] = field(default_factory=list)  # Random alternatives
    spirit_vision_text: Optional[str] = None     # Alt text if SV is active
    description: str = ""                         # Internal description

    # Probability
    base_chance: float = 1.0                      # 0.0-1.0 chance when conditions met
    permeability_scaling: float = 0.0             # Bonus chance per permeability point
    ma_scaling: float = 0.0                       # Bonus chance per ma point

    # Outcome
    outcome: EventOutcome = field(default_factory=EventOutcome)

    # Tracking
    repeatable: bool = True
    cooldown_steps: int = 0                       # Min steps before repeating
    chain_event: Optional[str] = None             # Next event in a chain

    def get_display_text(self, spirit_vision: bool = False) -> str:
        """Return the appropriate text for display."""
        if spirit_vision and self.spirit_vision_text:
            return self.spirit_vision_text
        if self.text_variants:
            return random.choice([self.text] + self.text_variants)
        return self.text

    def effective_chance(self, permeability: float = 0.0, ma: float = 0.0) -> float:
        """Calculate the effective trigger chance given world state."""
        chance = self.base_chance
        chance += self.permeability_scaling * permeability
        chance += self.ma_scaling * (ma / 100.0)
        return max(0.0, min(1.0, chance))


# ---------------------------------------------------------------------------
# Event tracking
# ---------------------------------------------------------------------------

@dataclass
class EventRecord:
    """Tracks how many times an event has fired and when."""
    event_id: str
    occurrence_count: int = 0
    last_step: int = 0          # Step count when last triggered
    last_timestamp: float = 0.0


# ---------------------------------------------------------------------------
# Event manager
# ---------------------------------------------------------------------------

class ExplorationEventManager:
    """
    Orchestrates exploration events. Each step the player takes, each
    moment they stand still, the manager checks the world state against
    its catalogue of possible moments and decides what, if anything,
    the city wants to show them.

    The system favors variety and avoids repeating the same event too
    quickly. Scripted events always take priority over random ones.
    """

    def __init__(self, rng_seed: Optional[int] = None) -> None:
        self._events: dict[str, ExplorationEvent] = {}
        self._records: dict[str, EventRecord] = {}
        self._rng = random.Random(rng_seed)
        self._pending_chain: Optional[str] = None
        self._suppressed_until_step: int = 0
        self._last_event_step: int = 0
        self._min_steps_between_events: int = 5

    def register_event(self, event: ExplorationEvent) -> None:
        self._events[event.event_id] = event

    def register_events(self, events: list[ExplorationEvent]) -> None:
        for event in events:
            self.register_event(event)

    def suppress_events(self, until_step: int) -> None:
        """Suppress random events until the given step count."""
        self._suppressed_until_step = until_step

    def force_event(self, event_id: str) -> Optional[ExplorationEvent]:
        """Force a specific event to trigger regardless of conditions."""
        return self._events.get(event_id)

    def check_events(self, context: EventContext) -> list[ExplorationEvent]:
        """
        Evaluate all events against current context and return those
        that trigger. Events are returned in priority order (highest first).

        At most one event per priority level is returned to prevent
        overwhelming the player.
        """
        # Handle event chains first
        if self._pending_chain:
            chain_event = self._events.get(self._pending_chain)
            self._pending_chain = None
            if chain_event is not None:
                return [chain_event]

        # Check suppression
        if context.steps_taken < self._suppressed_until_step:
            return []

        # Minimum spacing between events
        steps_since_last = context.steps_taken - self._last_event_step
        if steps_since_last < self._min_steps_between_events:
            # Still allow critical events
            return self._check_critical_only(context)

        candidates: list[tuple[float, ExplorationEvent]] = []

        for event in self._events.values():
            if not self._can_trigger(event, context):
                continue

            effective_chance = event.effective_chance(
                permeability=context.permeability,
                ma=context.current_ma,
            )

            if self._rng.random() <= effective_chance:
                candidates.append((effective_chance, event))

        if not candidates:
            return []

        # Sort by priority (descending), then by effective chance (descending)
        candidates.sort(
            key=lambda pair: (pair[1].priority.value, pair[0]),
            reverse=True,
        )

        # Take at most one event per priority level
        selected: list[ExplorationEvent] = []
        seen_priorities: set[EventPriority] = set()

        for _, event in candidates:
            if event.priority not in seen_priorities:
                selected.append(event)
                seen_priorities.add(event.priority)

        return selected

    def on_event_triggered(
        self, event: ExplorationEvent, step: int
    ) -> EventOutcome:
        """
        Record that an event has triggered. Returns its outcome.
        Call this after presenting the event to the player.
        """
        record = self._records.setdefault(
            event.event_id,
            EventRecord(event_id=event.event_id),
        )
        record.occurrence_count += 1
        record.last_step = step
        self._last_event_step = step

        if event.chain_event:
            self._pending_chain = event.chain_event

        return event.outcome

    def get_event_history(self) -> dict[str, EventRecord]:
        return dict(self._records)

    def get_occurrence_count(self, event_id: str) -> int:
        record = self._records.get(event_id)
        return record.occurrence_count if record else 0

    # -- Internal helpers --

    def _can_trigger(self, event: ExplorationEvent, context: EventContext) -> bool:
        """Check if an event is eligible to trigger."""
        # Condition check
        if not event.condition.evaluate(context):
            return False

        # Occurrence limit
        record = self._records.get(event.event_id)
        if record is not None:
            if not event.repeatable and record.occurrence_count > 0:
                return False
            if event.condition.max_occurrences is not None:
                if record.occurrence_count >= event.condition.max_occurrences:
                    return False
            # Cooldown
            if event.cooldown_steps > 0:
                steps_since = context.steps_taken - record.last_step
                if steps_since < event.cooldown_steps:
                    return False

        return True

    def _check_critical_only(
        self, context: EventContext
    ) -> list[ExplorationEvent]:
        """Check only critical-priority events (story events, etc.)."""
        results = []
        for event in self._events.values():
            if event.priority != EventPriority.CRITICAL:
                continue
            if not self._can_trigger(event, context):
                continue
            effective_chance = event.effective_chance(
                permeability=context.permeability,
                ma=context.current_ma,
            )
            if self._rng.random() <= effective_chance:
                results.append(event)
        return results


# ---------------------------------------------------------------------------
# YAML loader
# ---------------------------------------------------------------------------

def _parse_string_tuple(value: Any) -> Optional[tuple[str, ...]]:
    """Convert a YAML list to a tuple of strings, or None."""
    if value is None:
        return None
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(v) for v in value)
    return None


def load_events_from_yaml(yaml_data: dict) -> list[ExplorationEvent]:
    """
    Parse exploration events from a YAML dictionary.

    Expected structure:
        events:
          - event_id: ...
            name: ...
            category: atmospheric
            ...
    """
    events_list = yaml_data.get("events", [])
    results: list[ExplorationEvent] = []

    for entry in events_list:
        cond_data = entry.get("condition", {})
        condition = EventCondition(
            districts=_parse_string_tuple(cond_data.get("districts")),
            map_ids=_parse_string_tuple(cond_data.get("map_ids")),
            indoor=cond_data.get("indoor"),
            times_of_day=_parse_string_tuple(cond_data.get("times_of_day")),
            seasons=_parse_string_tuple(cond_data.get("seasons")),
            moon_phases=_parse_string_tuple(cond_data.get("moon_phases")),
            min_permeability=cond_data.get("min_permeability"),
            max_permeability=cond_data.get("max_permeability"),
            weather=_parse_string_tuple(cond_data.get("weather")),
            min_ma=cond_data.get("min_ma"),
            max_ma=cond_data.get("max_ma"),
            movement_mode=cond_data.get("movement_mode"),
            spirit_vision_active=cond_data.get("spirit_vision_active"),
            min_spirit_energy=cond_data.get("min_spirit_energy"),
            required_flags=_parse_string_tuple(cond_data.get("required_flags")),
            forbidden_flags=_parse_string_tuple(cond_data.get("forbidden_flags")),
            min_story_chapter=cond_data.get("min_story_chapter"),
            max_story_chapter=cond_data.get("max_story_chapter"),
            min_steps_since_last_event=cond_data.get("min_steps_since_last_event", 0),
            max_occurrences=cond_data.get("max_occurrences"),
        )

        outcome_data = entry.get("outcome", {})
        items_given = [
            (item["id"], item.get("quantity", 1))
            for item in outcome_data.get("items_given", [])
        ]
        items_taken = [
            (item["id"], item.get("quantity", 1))
            for item in outcome_data.get("items_taken", [])
        ]
        outcome = EventOutcome(
            ma_change=outcome_data.get("ma_change", 0.0),
            spirit_energy_change=outcome_data.get("spirit_energy_change", 0.0),
            items_given=items_given,
            items_taken=items_taken,
            flags_set=outcome_data.get("flags_set", []),
            flags_cleared=outcome_data.get("flags_cleared", []),
            permeability_change=outcome_data.get("permeability_change", 0.0),
            trigger_encounter=outcome_data.get("trigger_encounter"),
            trigger_dialogue=outcome_data.get("trigger_dialogue"),
            trigger_vignette=outcome_data.get("trigger_vignette"),
            teleport_map=outcome_data.get("teleport_map"),
            teleport_x=outcome_data.get("teleport_x"),
            teleport_y=outcome_data.get("teleport_y"),
            unlock_discovery=outcome_data.get("unlock_discovery"),
            sound_effect=outcome_data.get("sound_effect"),
            music_change=outcome_data.get("music_change"),
        )

        event = ExplorationEvent(
            event_id=entry["event_id"],
            name=entry["name"],
            category=EventCategory(entry["category"]),
            priority=EventPriority[entry.get("priority", "NORMAL").upper()]
            if isinstance(entry.get("priority"), str)
            else EventPriority(entry.get("priority", 2)),
            presentation=EventPresentation(
                entry.get("presentation", "text_overlay")
            ),
            condition=condition,
            text=entry["text"],
            text_variants=entry.get("text_variants", []),
            spirit_vision_text=entry.get("spirit_vision_text"),
            description=entry.get("description", ""),
            base_chance=entry.get("base_chance", 1.0),
            permeability_scaling=entry.get("permeability_scaling", 0.0),
            ma_scaling=entry.get("ma_scaling", 0.0),
            outcome=outcome,
            repeatable=entry.get("repeatable", True),
            cooldown_steps=entry.get("cooldown_steps", 0),
            chain_event=entry.get("chain_event"),
        )
        results.append(event)

    return results
