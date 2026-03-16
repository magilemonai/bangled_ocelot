"""Tests for the core game engine."""

import pytest
from src.engine.game import (
    Game, GameState, WorldClock, SpiritTide, MaState,
    TimeOfDay, Season, MoonPhase
)
from src.engine.events import EventBus, EventType, GameEvent


class TestWorldClock:
    """Test the world clock and time system."""

    def test_initial_state(self):
        clock = WorldClock()
        assert clock.day == 1
        assert clock.hour == 6.0
        assert clock.season == Season.SPRING
        assert clock.time_of_day == TimeOfDay.DAWN

    def test_time_advancement(self):
        clock = WorldClock()
        clock.advance(1.0)  # 1 second of real time = 1 minute game time
        assert clock.hour > 6.0

    def test_day_rollover(self):
        clock = WorldClock(hour=23.5)
        clock.advance(60.0)  # Advance enough to roll over
        assert clock.day >= 2

    def test_spirit_permeability_varies_with_time(self):
        dawn_clock = WorldClock(hour=6.0)
        midnight_clock = WorldClock(hour=23.0)
        assert midnight_clock.spirit_permeability > dawn_clock.spirit_permeability

    def test_moon_phase_cycles(self):
        clock = WorldClock(moon_day=0)
        assert clock.moon_phase == MoonPhase.NEW
        clock.moon_day = 15
        assert clock.moon_phase == MoonPhase.FULL

    def test_full_moon_increases_permeability(self):
        new_moon = WorldClock(moon_day=0, hour=23.0)
        full_moon = WorldClock(moon_day=15, hour=23.0)
        assert full_moon.spirit_permeability > new_moon.spirit_permeability

    def test_permeability_bounded(self):
        clock = WorldClock(hour=3.0, season=Season.WINTER, moon_day=15)
        assert 0.0 <= clock.spirit_permeability <= 1.0


class TestMaState:
    """Test the ma (間) system - the heart of the game."""

    def test_initial_state(self):
        ma = MaState()
        assert ma.current_ma == 0.0
        assert not ma.can_hear_whispers

    def test_accumulation(self):
        ma = MaState()
        ma.accumulate(25.0)
        assert ma.current_ma == 25.0
        assert ma.can_hear_whispers

    def test_threshold_crossing_returns_events(self):
        ma = MaState()
        thresholds = ma.accumulate(25.0)
        assert "whisper" in thresholds

    def test_decay(self):
        ma = MaState(current_ma=50.0)
        ma.decay(10.0)
        assert ma.current_ma < 50.0

    def test_ma_capped_at_max(self):
        ma = MaState()
        ma.accumulate(200.0)
        assert ma.current_ma == ma.max_ma

    def test_all_thresholds(self):
        ma = MaState()
        thresholds = ma.accumulate(85.0)
        assert "whisper" in thresholds
        assert "vision" in thresholds
        assert "memory" in thresholds
        assert "crossing" in thresholds
        assert ma.can_cross_over

    def test_lifetime_tracking(self):
        ma = MaState()
        ma.accumulate(30.0)
        ma.decay(50.0)
        ma.accumulate(20.0)
        assert ma.lifetime_ma == 50.0


class TestSpiritTide:
    """Test the spirit tide system."""

    def test_initial_state(self):
        tide = SpiritTide()
        assert tide.global_level == 0.3

    def test_local_level_calculation(self):
        tide = SpiritTide(district_modifiers={"shibuya": 0.1})
        clock = WorldClock(hour=23.0)
        level = tide.get_local_level("shibuya", clock)
        assert level > tide.global_level

    def test_surge_and_expiry(self):
        tide = SpiritTide()
        tide.surge("asakusa", 0.5, 3)
        assert len(tide.surge_events) == 1

        tide.update()
        assert tide.surge_events[0]["remaining"] == 2

        tide.update()
        expired = tide.update()
        assert len(expired) == 1
        assert len(tide.surge_events) == 0


class TestGame:
    """Test the core game object."""

    def test_initialization(self):
        game = Game()
        assert game.state == GameState.TITLE
        assert game.clock is not None
        assert game.ma is not None

    def test_state_transition(self):
        game = Game()
        game.transition_to(GameState.EXPLORATION)
        assert game.state == GameState.EXPLORATION
        assert game.previous_state == GameState.TITLE

    def test_flag_system(self):
        game = Game()
        assert not game.check_flag("met_ren")
        game.set_flag("met_ren")
        assert game.check_flag("met_ren")

    def test_system_registration(self):
        game = Game()
        game.register_system("test", {"name": "test"})
        assert "test" in game.systems

    def test_update_advances_clock(self):
        game = Game()
        initial_hour = game.clock.hour
        game.update(1.0)
        assert game.clock.hour > initial_hour


class TestEventBus:
    """Test the event system."""

    def test_subscribe_and_emit(self):
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe(EventType.PLAYER_MOVE, handler)
        bus.emit(GameEvent(EventType.PLAYER_MOVE, {"x": 1, "y": 2}))
        bus.process_queue()

        assert len(received) == 1
        assert received[0].data["x"] == 1

    def test_event_consumption(self):
        bus = EventBus()
        results = []

        def handler1(event):
            results.append("first")
            event.consume()

        def handler2(event):
            results.append("second")

        bus.subscribe(EventType.PLAYER_MOVE, handler1, priority=10)
        bus.subscribe(EventType.PLAYER_MOVE, handler2, priority=0)
        bus.emit(GameEvent(EventType.PLAYER_MOVE))
        bus.process_queue()

        assert results == ["first"]  # Second handler not called

    def test_global_subscriber(self):
        bus = EventBus()
        received = []

        bus.subscribe_all(lambda e: received.append(e.event_type))
        bus.emit(GameEvent(EventType.PLAYER_MOVE))
        bus.emit(GameEvent(EventType.MA_ACCUMULATE))
        bus.process_queue()

        assert len(received) == 2

    def test_event_history(self):
        bus = EventBus()
        bus.subscribe(EventType.PLAYER_MOVE, lambda e: None)
        bus.emit(GameEvent(EventType.PLAYER_MOVE))
        bus.process_queue()

        history = bus.recent_events(EventType.PLAYER_MOVE)
        assert len(history) == 1
