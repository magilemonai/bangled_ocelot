"""
Ma no Kuni - Core Game Engine

The heartbeat of the game. Manages the central loop, coordinates all subsystems,
and maintains the delicate balance between the material and spirit worlds.

The concept of 'ma' (間) - the pregnant pause, the space between - is encoded
into the engine itself. Time flows differently. Silence has weight.
"""

import time
from enum import Enum, auto
from typing import Optional
from dataclasses import dataclass, field


class GameState(Enum):
    """The states of being, like the states of the world."""
    TITLE = auto()
    EXPLORATION = auto()
    DIALOGUE = auto()
    COMBAT = auto()
    PUZZLE = auto()
    CRAFTING = auto()
    BESTIARY = auto()
    INVENTORY = auto()
    SPIRIT_VISION = auto()
    VIGNETTE = auto()        # Quiet narrative moments - ma
    TRANSITION = auto()       # The space between states
    SAVE_MENU = auto()
    GAME_OVER = auto()


class TimeOfDay(Enum):
    """Tokyo's rhythms shape the spirit world's presence."""
    DAWN = "dawn"             # 5:00-7:00  - Spirits begin to fade
    MORNING = "morning"       # 7:00-11:00 - Material world dominant
    MIDDAY = "midday"         # 11:00-13:00 - Brief equilibrium
    AFTERNOON = "afternoon"   # 13:00-17:00 - Shadows lengthen
    DUSK = "dusk"             # 17:00-19:00 - The veil thins
    EVENING = "evening"       # 19:00-22:00 - Spirits grow bold
    MIDNIGHT = "midnight"     # 22:00-2:00  - The spirit world peaks
    WITCHING = "witching"     # 2:00-5:00   - The deepest crossing


class Season(Enum):
    """Each season shifts the balance of the permeation."""
    SPRING = "spring"         # Cherry blossoms carry messages between worlds
    SUMMER = "summer"         # Heat shimmers become spirit doorways
    AUTUMN = "autumn"         # The dying leaves remember everything
    WINTER = "winter"         # The cold makes the veil brittle and thin


class MoonPhase(Enum):
    """The moon pulls at the spirit tide."""
    NEW = "new"
    WAXING_CRESCENT = "waxing_crescent"
    FIRST_QUARTER = "first_quarter"
    WAXING_GIBBOUS = "waxing_gibbous"
    FULL = "full"
    WANING_GIBBOUS = "waning_gibbous"
    LAST_QUARTER = "last_quarter"
    WANING_CRESCENT = "waning_crescent"


@dataclass
class WorldClock:
    """
    Time in Ma no Kuni flows like water - sometimes rushing, sometimes still.
    The 'ma' between moments is where the spirits live.
    """
    day: int = 1
    hour: float = 6.0  # Start at dawn
    season: Season = Season.SPRING
    moon_day: int = 0  # 0-29 lunar cycle
    time_scale: float = 1.0  # Can slow during ma moments

    def advance(self, real_delta: float) -> None:
        """Advance the world clock. During moments of ma, time stretches."""
        game_minutes = real_delta * 60 * self.time_scale
        self.hour += game_minutes / 60.0

        if self.hour >= 24.0:
            self.hour -= 24.0
            self.day += 1
            self.moon_day = (self.moon_day + 1) % 30

            if self.day % 90 == 0:
                seasons = list(Season)
                current_idx = seasons.index(self.season)
                self.season = seasons[(current_idx + 1) % 4]

    @property
    def time_of_day(self) -> TimeOfDay:
        if 5.0 <= self.hour < 7.0:
            return TimeOfDay.DAWN
        elif 7.0 <= self.hour < 11.0:
            return TimeOfDay.MORNING
        elif 11.0 <= self.hour < 13.0:
            return TimeOfDay.MIDDAY
        elif 13.0 <= self.hour < 17.0:
            return TimeOfDay.AFTERNOON
        elif 17.0 <= self.hour < 19.0:
            return TimeOfDay.DUSK
        elif 19.0 <= self.hour < 22.0:
            return TimeOfDay.EVENING
        elif 22.0 <= self.hour or self.hour < 2.0:
            return TimeOfDay.MIDNIGHT
        else:
            return TimeOfDay.WITCHING

    @property
    def moon_phase(self) -> MoonPhase:
        phase_idx = int(self.moon_day / 3.75)
        return list(MoonPhase)[min(phase_idx, 7)]

    @property
    def spirit_permeability(self) -> float:
        """
        How thin is the veil right now? 0.0 = solid barrier, 1.0 = fully open.
        Affected by time, season, and moon phase.
        """
        # Base permeability from time of day
        time_values = {
            TimeOfDay.DAWN: 0.3,
            TimeOfDay.MORNING: 0.1,
            TimeOfDay.MIDDAY: 0.15,
            TimeOfDay.AFTERNOON: 0.2,
            TimeOfDay.DUSK: 0.5,
            TimeOfDay.EVENING: 0.6,
            TimeOfDay.MIDNIGHT: 0.8,
            TimeOfDay.WITCHING: 0.95,
        }
        base = time_values[self.time_of_day]

        # Season modifier
        season_mod = {
            Season.SPRING: 0.1,   # Renewal brings spirits close
            Season.SUMMER: 0.05,  # Heat creates mirages, thins veil slightly
            Season.AUTUMN: 0.15,  # The dying season opens doors
            Season.WINTER: 0.2,   # Cold cracks the barrier
        }
        base += season_mod[self.season]

        # Moon modifier - full moon is strongest
        if self.moon_phase == MoonPhase.FULL:
            base += 0.2
        elif self.moon_phase in (MoonPhase.WAXING_GIBBOUS, MoonPhase.WANING_GIBBOUS):
            base += 0.1
        elif self.moon_phase == MoonPhase.NEW:
            base -= 0.1  # New moon suppresses

        return max(0.0, min(1.0, base))


@dataclass
class SpiritTide:
    """
    The spirit tide ebbs and flows through Tokyo's districts.
    When it surges, the impossible becomes commonplace.
    When it recedes, only echoes remain.
    """
    global_level: float = 0.3  # The world is newly permeable
    district_modifiers: dict = field(default_factory=dict)
    surge_events: list = field(default_factory=list)
    tide_memory: list = field(default_factory=list)  # Past surge locations

    def get_local_level(self, district: str, clock: WorldClock) -> float:
        """Calculate spirit presence in a specific district."""
        base = self.global_level + clock.spirit_permeability
        modifier = self.district_modifiers.get(district, 0.0)
        return max(0.0, min(1.0, base + modifier))

    def surge(self, district: str, intensity: float, duration: int) -> None:
        """A spirit surge - the veil tears open briefly."""
        self.surge_events.append({
            "district": district,
            "intensity": intensity,
            "duration": duration,
            "remaining": duration,
        })
        self.tide_memory.append(district)

    def update(self) -> list:
        """Update surge events, return list of expired surges."""
        expired = []
        active = []
        for surge in self.surge_events:
            surge["remaining"] -= 1
            if surge["remaining"] <= 0:
                expired.append(surge)
            else:
                active.append(surge)
        self.surge_events = active
        return expired


@dataclass
class MaState:
    """
    Ma (間) - the space between. The pause that gives meaning.

    This system tracks the quality of silence and stillness in the game.
    When Aoi pauses, when the player waits, when nothing happens -
    that's when the deepest things occur.

    Ma accumulates during:
    - Standing still in meaningful places
    - Listening to spirits without responding
    - Watching the city at dawn or dusk
    - Sitting with grandmother in silence

    High ma unlocks:
    - Hidden dialogue options
    - Spirit whispers
    - Memory vignettes
    - Secret paths between worlds
    """
    current_ma: float = 0.0
    max_ma: float = 100.0
    ma_threshold_whisper: float = 20.0
    ma_threshold_vision: float = 40.0
    ma_threshold_memory: float = 60.0
    ma_threshold_crossing: float = 80.0
    decay_rate: float = 0.5  # Ma fades when you rush
    accumulation_rate: float = 1.0
    lifetime_ma: float = 0.0  # Total ma ever accumulated

    def accumulate(self, amount: float, context: str = "") -> list:
        """
        Gather ma. Returns list of thresholds crossed.
        """
        old_ma = self.current_ma
        self.current_ma = min(self.max_ma, self.current_ma + amount * self.accumulation_rate)
        self.lifetime_ma += amount * self.accumulation_rate

        thresholds_crossed = []
        thresholds = [
            (self.ma_threshold_whisper, "whisper"),
            (self.ma_threshold_vision, "vision"),
            (self.ma_threshold_memory, "memory"),
            (self.ma_threshold_crossing, "crossing"),
        ]
        for threshold, name in thresholds:
            if old_ma < threshold <= self.current_ma:
                thresholds_crossed.append(name)

        return thresholds_crossed

    def decay(self, delta: float) -> None:
        """Ma fades when you move too fast, fight, or speak carelessly."""
        self.current_ma = max(0.0, self.current_ma - self.decay_rate * delta)

    @property
    def can_hear_whispers(self) -> bool:
        return self.current_ma >= self.ma_threshold_whisper

    @property
    def can_see_visions(self) -> bool:
        return self.current_ma >= self.ma_threshold_vision

    @property
    def can_access_memories(self) -> bool:
        return self.current_ma >= self.ma_threshold_memory

    @property
    def can_cross_over(self) -> bool:
        return self.current_ma >= self.ma_threshold_crossing


class Game:
    """
    The game itself. A world engine that breathes.
    """

    def __init__(self):
        self.state = GameState.TITLE
        self.previous_state: Optional[GameState] = None
        self.clock = WorldClock()
        self.spirit_tide = SpiritTide()
        self.ma = MaState()
        self.player = None
        self.current_map = None
        self.current_district = None
        self.running = False
        self.systems = {}
        self.event_queue = []
        self.flags = {}  # Story flags
        self.statistics = {
            "steps_taken": 0,
            "spirits_befriended": 0,
            "spirits_banished": 0,
            "items_crafted": 0,
            "puzzles_solved": 0,
            "vignettes_witnessed": 0,
            "ma_moments": 0,
            "battles_won": 0,
            "battles_fled": 0,
            "secrets_found": 0,
        }

    def register_system(self, name: str, system) -> None:
        """Register a game subsystem."""
        self.systems[name] = system

    def transition_to(self, new_state: GameState) -> None:
        """
        State transitions pass through TRANSITION first.
        The space between states is itself a state - ma.
        """
        self.previous_state = self.state
        self.state = GameState.TRANSITION
        self.event_queue.append({
            "type": "state_transition",
            "from": self.previous_state,
            "to": new_state,
        })
        # After transition processing, move to new state
        self.state = new_state

    def set_flag(self, flag: str, value=True) -> None:
        """Set a story flag. The world remembers."""
        self.flags[flag] = value

    def check_flag(self, flag: str) -> bool:
        """Check if the world remembers something."""
        return self.flags.get(flag, False)

    def update(self, delta: float) -> None:
        """
        The main update tick. Everything breathes together.
        """
        # Advance the world clock
        self.clock.advance(delta)

        # Update spirit tide
        expired_surges = self.spirit_tide.update()
        for surge in expired_surges:
            self.event_queue.append({
                "type": "surge_expired",
                "district": surge["district"],
            })

        # Ma naturally decays during action, accumulates during stillness
        if self.state in (GameState.COMBAT, GameState.PUZZLE):
            self.ma.decay(delta * 2.0)
        elif self.state == GameState.EXPLORATION:
            self.ma.decay(delta * 0.5)
        elif self.state == GameState.VIGNETTE:
            thresholds = self.ma.accumulate(delta * 3.0, "vignette")
            for t in thresholds:
                self.event_queue.append({"type": "ma_threshold", "threshold": t})

        # Update all registered systems
        for name, system in self.systems.items():
            if hasattr(system, 'update'):
                system.update(delta)

    def process_events(self) -> list:
        """Process and return pending events."""
        events = self.event_queue.copy()
        self.event_queue.clear()
        return events
