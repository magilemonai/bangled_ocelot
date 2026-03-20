"""
Ma no Kuni - Vignette System

The vignettes are the heart of the game.

They are not cutscenes. They are not quests. They are moments -
the kind you carry with you for years after without quite knowing why.
A cup of tea growing cold. Rain on stone. The weight of a cat on your lap
while the room fills with things you cannot see.

Vignettes trigger when conditions align: location, time, weather,
spirit presence, relationship depth, ma level. They cannot be forced.
They arrive like weather. The player's role is to be present.

Some vignettes are wordless. Some are a single line of dialogue
followed by silence. The silence is the point.

Technical notes:
    - Vignettes pause normal gameplay systems
    - Time slows (ma accumulates faster)
    - The camera may shift perspective
    - Music transitions to ambient/silence
    - Player input is minimal: advance, observe, leave
    - Leaving early is always an option. The game never holds you captive.
      But what you miss is real.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class VignetteCategory(Enum):
    """The colors of stillness."""
    DOMESTIC = "domestic"       # Home life - tea, cooking, the cat
    URBAN = "urban"             # The city's quiet moments
    SPIRITUAL = "spiritual"     # Encounters with the spirit world
    MEMORY = "memory"           # The past surfacing
    RELATIONSHIP = "relationship"  # Between Aoi and someone they love
    LIMINAL = "liminal"         # In-between spaces - trains, doorways, dusk
    SEASONAL = "seasonal"       # Moments tied to the turning year


class VignetteMood(Enum):
    """Not emotions. Atmospheres."""
    TENDER = "tender"
    MELANCHOLY = "melancholy"
    LUMINOUS = "luminous"
    ACHING = "aching"
    PEACEFUL = "peaceful"
    UNCANNY = "uncanny"
    BITTERSWEET = "bittersweet"
    HUSHED = "hushed"


class VignetteInputMode(Enum):
    """How the player participates in stillness."""
    OBSERVE = "observe"         # Watch only. The moment unfolds.
    GENTLE = "gentle"           # Minimal choices - stay/go, speak/silence
    CONTEMPLATIVE = "contemplative"  # Choose what to focus on
    INTERACTIVE = "interactive"  # Small meaningful actions (pour tea, pet cat)


@dataclass
class VignetteBeat:
    """
    A single beat within a vignette. A sentence. A silence.
    A change in what the camera sees. A sound.

    Beats are the atoms of vignettes. Most are text.
    Some are pure atmosphere - a sound, a shift in light.
    """
    id: str
    content_type: str = "text"  # "text", "silence", "sound", "visual", "choice"

    # Text content
    text: Optional[str] = None
    speaker: Optional[str] = None        # None = narration
    inner_thought: bool = False           # Aoi's internal voice

    # Atmosphere
    sound: Optional[str] = None          # Sound effect or ambient change
    music_shift: Optional[str] = None    # Music transition cue
    visual_direction: Optional[str] = None  # Camera/visual instruction
    lighting: Optional[str] = None

    # Timing
    duration: float = 0.0                # Seconds of pause (0 = wait for input)
    auto_advance: bool = False           # Advance without input after duration
    ma_accumulation: float = 1.0         # Ma gained during this beat

    # Choice (when content_type == "choice")
    choices: list[VignetteChoice] = field(default_factory=list)

    # Conditional display
    condition_flag: Optional[str] = None  # Only show if this flag is set
    condition_value: object = True
    min_relationship: Optional[dict] = None  # {character_id: min_level}


@dataclass
class VignetteChoice:
    """
    A choice within a vignette. These are not plot choices.
    They are choices of attention: what do you look at?
    What do you say, or choose not to say?
    """
    id: str
    text: str
    next_beat: str                       # Beat ID to go to
    flags_set: dict = field(default_factory=dict)
    relationship_changes: dict[str, int] = field(default_factory=dict)
    ma_bonus: float = 0.0
    # The silent option - choosing not to speak - often gives the most ma
    is_silence: bool = False


@dataclass
class VignetteCondition:
    """When does a vignette become possible?"""
    # Location
    location: Optional[str] = None
    locations: list[str] = field(default_factory=list)  # Any of these

    # Time
    time_of_day: Optional[str] = None
    times_of_day: list[str] = field(default_factory=list)
    season: Optional[str] = None

    # Spirit world
    min_permeability: float = 0.0
    max_permeability: float = 1.0

    # Ma
    min_ma: float = 0.0
    min_lifetime_ma: float = 0.0

    # Story progress
    required_flags: dict = field(default_factory=dict)
    forbidden_flags: list[str] = field(default_factory=list)
    required_chapter: Optional[int] = None
    min_relationship: dict[str, int] = field(default_factory=dict)

    # Meta conditions
    not_seen_in_days: int = 0           # Cooldown in game days
    max_times_seen: Optional[int] = None  # Some vignettes only happen once
    requires_stillness: float = 0.0      # Seconds of player inactivity

    def evaluate(self, game_state, vignette_history: dict) -> bool:
        """Can this vignette occur right now?"""
        # Location check
        if self.location and game_state.current_district != self.location:
            return False
        if self.locations and game_state.current_district not in self.locations:
            return False

        # Time check
        current_time = game_state.clock.time_of_day.value
        if self.time_of_day and current_time != self.time_of_day:
            return False
        if self.times_of_day and current_time not in self.times_of_day:
            return False

        # Season
        if self.season and game_state.clock.season.value != self.season:
            return False

        # Permeability
        if game_state.current_district:
            perm = game_state.spirit_tide.get_local_level(
                game_state.current_district, game_state.clock
            )
        else:
            perm = game_state.clock.spirit_permeability
        if perm < self.min_permeability or perm > self.max_permeability:
            return False

        # Ma
        if game_state.ma.current_ma < self.min_ma:
            return False
        if game_state.ma.lifetime_ma < self.min_lifetime_ma:
            return False

        # Flags
        for flag, value in self.required_flags.items():
            if game_state.flags.get(flag) != value:
                return False
        for flag in self.forbidden_flags:
            if game_state.flags.get(flag):
                return False

        # Chapter
        if self.required_chapter is not None:
            if game_state.flags.get("current_chapter", 1) < self.required_chapter:
                return False

        # Relationships
        for char_id, min_level in self.min_relationship.items():
            actual = game_state.flags.get(f"relationship_{char_id}", 0)
            if actual < min_level:
                return False

        # Cooldown and max views
        if vignette_history:
            times_seen = vignette_history.get("times_seen", 0)
            if self.max_times_seen is not None and times_seen >= self.max_times_seen:
                return False
            last_seen_day = vignette_history.get("last_seen_day", -999)
            if game_state.clock.day - last_seen_day < self.not_seen_in_days:
                return False

        return True


@dataclass
class Vignette:
    """
    A vignette. A moment held in amber.

    Not every vignette will be seen by every player. That is by design.
    The ones you happen upon feel like they happened only for you.
    Because they did.
    """
    id: str
    title: str
    category: VignetteCategory
    mood: VignetteMood
    input_mode: VignetteInputMode = VignetteInputMode.OBSERVE

    # Description (for internal use / journal)
    description: str = ""
    journal_entry: Optional[str] = None  # Written after experiencing

    # The content
    beats: list[VignetteBeat] = field(default_factory=list)

    # When this can happen
    conditions: VignetteCondition = field(default_factory=VignetteCondition)

    # Atmosphere
    ambient_sound: Optional[str] = None
    music_track: Optional[str] = None
    weather_override: Optional[str] = None
    time_scale: float = 0.3             # Time slows during vignettes

    # Rewards (subtle - the player may not notice)
    ma_reward: float = 5.0
    relationship_rewards: dict[str, int] = field(default_factory=dict)
    flags_on_complete: dict = field(default_factory=dict)
    flags_on_skip: dict = field(default_factory=dict)  # If player leaves early
    unlocks_quest: Optional[str] = None

    # Priority (when multiple vignettes could trigger)
    priority: int = 0                    # Higher = more important
    weight: float = 1.0                  # Random selection weight

    # Connections
    leads_to: Optional[str] = None       # Another vignette that follows
    blocks: list[str] = field(default_factory=list)  # Vignettes this prevents


@dataclass
class VignetteState:
    """Runtime state for a vignette in progress."""
    vignette: Vignette
    current_beat_index: int = 0
    beats_seen: list[str] = field(default_factory=list)
    choices_made: list[dict] = field(default_factory=list)
    total_ma_accumulated: float = 0.0
    time_spent: float = 0.0
    completed: bool = False
    skipped: bool = False

    @property
    def current_beat(self) -> Optional[VignetteBeat]:
        """The beat currently being experienced."""
        if self.current_beat_index < len(self.vignette.beats):
            return self.vignette.beats[self.current_beat_index]
        return None

    def advance(self) -> Optional[VignetteBeat]:
        """Move to the next beat. Returns it, or None if finished."""
        if self.current_beat:
            self.beats_seen.append(self.current_beat.id)
        self.current_beat_index += 1
        if self.current_beat_index >= len(self.vignette.beats):
            self.completed = True
            return None
        return self.current_beat

    def jump_to_beat(self, beat_id: str) -> Optional[VignetteBeat]:
        """Jump to a specific beat (used after choices)."""
        for i, beat in enumerate(self.vignette.beats):
            if beat.id == beat_id:
                self.current_beat_index = i
                return beat
        return None

    def make_choice(self, choice: VignetteChoice, game_state) -> None:
        """Record a choice and apply its effects."""
        self.choices_made.append({
            "beat_id": self.current_beat.id if self.current_beat else None,
            "choice_id": choice.id,
            "is_silence": choice.is_silence,
        })
        # Apply flags
        for flag, value in choice.flags_set.items():
            game_state.set_flag(flag, value)
        # Apply relationship changes
        for char_id, change in choice.relationship_changes.items():
            current = game_state.flags.get(f"relationship_{char_id}", 0)
            game_state.set_flag(f"relationship_{char_id}", current + change)
        # Ma bonus
        if choice.ma_bonus > 0:
            game_state.ma.accumulate(choice.ma_bonus, f"vignette_choice:{choice.id}")
        self.total_ma_accumulated += choice.ma_bonus
        # Navigate
        self.jump_to_beat(choice.next_beat)


@dataclass
class VignetteHistory:
    """The record of moments witnessed."""
    seen: dict[str, dict] = field(default_factory=dict)
    # Each entry: {times_seen: int, last_seen_day: int, choices: list}

    def record(self, vignette_id: str, day: int, choices: list[dict]) -> None:
        """Remember this moment."""
        if vignette_id not in self.seen:
            self.seen[vignette_id] = {
                "times_seen": 0,
                "last_seen_day": 0,
                "first_seen_day": day,
                "choices_history": [],
            }
        entry = self.seen[vignette_id]
        entry["times_seen"] += 1
        entry["last_seen_day"] = day
        entry["choices_history"].append(choices)

    def get_history(self, vignette_id: str) -> dict:
        """Recall what happened."""
        return self.seen.get(vignette_id, {})

    @property
    def total_witnessed(self) -> int:
        return len(self.seen)

    @property
    def unique_categories_seen(self) -> set[str]:
        """Which kinds of moments have been experienced."""
        # This would need vignette metadata; tracked by the manager
        return set()


class VignetteManager:
    """
    Watches the world. Waits. When the conditions align -
    location, time, ma, story progress, the shape of silence -
    offers a moment.

    The player can always say no. But the moment will not wait.
    """

    def __init__(self):
        self.vignettes: dict[str, Vignette] = {}
        self.history: VignetteHistory = VignetteHistory()
        self.active_state: Optional[VignetteState] = None
        self.blocked_ids: set[str] = set()
        self._stillness_timer: float = 0.0
        self._last_player_input_time: float = 0.0

    def register_vignette(self, vignette: Vignette) -> None:
        """Add a vignette to the possible moments."""
        self.vignettes[vignette.id] = vignette

    def update(self, delta: float, game_state, player_idle: bool = False) -> Optional[Vignette]:
        """
        Check if a vignette should trigger. Called each frame during exploration.
        Returns a Vignette if one should begin, None otherwise.

        Does not trigger during combat, menus, or other vignettes.
        """
        if self.active_state is not None:
            return None

        # Track stillness
        if player_idle:
            self._stillness_timer += delta
        else:
            self._stillness_timer = 0.0

        # Find eligible vignettes
        candidates = []
        for vignette in self.vignettes.values():
            if vignette.id in self.blocked_ids:
                continue
            history = self.history.get_history(vignette.id)

            # Check stillness requirement
            if vignette.conditions.requires_stillness > 0:
                if self._stillness_timer < vignette.conditions.requires_stillness:
                    continue

            if vignette.conditions.evaluate(game_state, history):
                candidates.append(vignette)

        if not candidates:
            return None

        # Sort by priority, then select by weight
        candidates.sort(key=lambda v: v.priority, reverse=True)
        top_priority = candidates[0].priority
        top_candidates = [v for v in candidates if v.priority == top_priority]

        # Weighted random selection among equal-priority candidates
        if len(top_candidates) == 1:
            chosen = top_candidates[0]
        else:
            import random
            weights = [v.weight for v in top_candidates]
            chosen = random.choices(top_candidates, weights=weights, k=1)[0]

        return chosen

    def begin_vignette(self, vignette: Vignette) -> VignetteState:
        """Start experiencing a vignette."""
        self.active_state = VignetteState(vignette=vignette)
        self._stillness_timer = 0.0

        # Block any vignettes this one prevents
        for blocked_id in vignette.blocks:
            self.blocked_ids.add(blocked_id)

        return self.active_state

    def end_vignette(self, game_state, skipped: bool = False) -> dict:
        """
        Finish the current vignette. Apply rewards.
        Returns summary of what happened.
        """
        if self.active_state is None:
            return {}

        state = self.active_state
        vignette = state.vignette

        # Record in history
        self.history.record(
            vignette.id,
            game_state.clock.day,
            state.choices_made,
        )

        summary = {
            "vignette_id": vignette.id,
            "title": vignette.title,
            "completed": not skipped,
            "beats_seen": len(state.beats_seen),
            "total_beats": len(vignette.beats),
            "choices_made": state.choices_made,
            "ma_accumulated": state.total_ma_accumulated,
            "time_spent": state.time_spent,
        }

        # Apply rewards
        if skipped:
            for flag, value in vignette.flags_on_skip.items():
                game_state.set_flag(flag, value)
        else:
            # Full completion rewards
            game_state.ma.accumulate(vignette.ma_reward, f"vignette:{vignette.id}")
            for flag, value in vignette.flags_on_complete.items():
                game_state.set_flag(flag, value)
            for char_id, change in vignette.relationship_rewards.items():
                current = game_state.flags.get(f"relationship_{char_id}", 0)
                game_state.set_flag(f"relationship_{char_id}", current + change)

            # Track in game statistics
            game_state.statistics["vignettes_witnessed"] += 1

            # Check for quest unlock
            if vignette.unlocks_quest:
                game_state.set_flag(
                    f"quest_unlocked_{vignette.unlocks_quest}", True
                )

        # Check for follow-up vignette
        if vignette.leads_to and not skipped:
            summary["next_vignette"] = vignette.leads_to

        self.active_state = None
        return summary

    def get_journal_entries(self) -> list[dict]:
        """
        Get all vignette journal entries for the player's journal.
        Only includes witnessed vignettes.
        """
        entries = []
        for vid, history in self.history.seen.items():
            vignette = self.vignettes.get(vid)
            if vignette and vignette.journal_entry:
                entries.append({
                    "vignette_id": vid,
                    "title": vignette.title,
                    "category": vignette.category.value,
                    "journal_entry": vignette.journal_entry,
                    "day_first_seen": history["first_seen_day"],
                    "times_seen": history["times_seen"],
                })
        entries.sort(key=lambda e: e["day_first_seen"])
        return entries
