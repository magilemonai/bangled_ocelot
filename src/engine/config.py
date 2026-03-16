"""
Ma no Kuni - Game Configuration

The constants that define the world's rules.
Some numbers are chosen for their spiritual significance.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayConfig:
    """Screen and rendering configuration."""
    WINDOW_TITLE: str = "間の国 — Ma no Kuni"
    SCREEN_WIDTH: int = 640
    SCREEN_HEIGHT: int = 480
    TILE_SIZE: int = 32
    SPRITE_SIZE_SMALL: int = 32
    SPRITE_SIZE_MEDIUM: int = 64
    SPRITE_SIZE_LARGE: int = 128
    FPS: int = 60
    FULLSCREEN: bool = False
    VSYNC: bool = True


@dataclass(frozen=True)
class GameplayConfig:
    """Core gameplay parameters."""
    # Movement
    WALK_SPEED: float = 2.0       # Tiles per second
    RUN_SPEED: float = 4.0        # Running scares nearby spirits
    SNEAK_SPEED: float = 1.0      # Better spirit encounters

    # Ma
    MA_MAX: float = 100.0
    MA_DECAY_COMBAT: float = 2.0
    MA_DECAY_MOVEMENT: float = 0.5
    MA_ACCUMULATE_STILL: float = 1.0
    MA_ACCUMULATE_VIGNETTE: float = 3.0
    MA_THRESHOLD_WHISPER: float = 20.0
    MA_THRESHOLD_VISION: float = 40.0
    MA_THRESHOLD_MEMORY: float = 60.0
    MA_THRESHOLD_CROSSING: float = 80.0

    # Spirit
    SPIRIT_SIGHT_DRAIN: float = 0.5  # Per second
    MAX_SPIRIT_BONDS: int = 8
    MAX_ACTIVE_COMPANIONS: int = 2

    # Combat
    BASE_HP: int = 100
    BASE_SP: int = 50  # Spirit Points
    MAX_PARTY_SIZE: int = 3

    # Crafting
    MAX_INVENTORY_SIZE: int = 99

    # Time
    GAME_MINUTES_PER_REAL_SECOND: float = 1.0
    DAY_LENGTH_HOURS: float = 24.0
    SEASON_LENGTH_DAYS: int = 90


@dataclass(frozen=True)
class AudioConfig:
    """Audio system configuration."""
    MUSIC_VOLUME: float = 0.7
    SFX_VOLUME: float = 0.8
    AMBIENT_VOLUME: float = 0.5
    SPIRIT_LAYER_VOLUME: float = 0.4
    CROSSFADE_DURATION: float = 2.0
    SAMPLE_RATE: int = 44100


@dataclass(frozen=True)
class SpiritConfig:
    """Spirit world parameters."""
    # Permeability thresholds
    PERMEABILITY_GIFTED: float = 0.0    # Always visible to the gifted
    PERMEABILITY_FLICKER: float = 0.2   # Flickering glimpses
    PERMEABILITY_VISIBLE: float = 0.4   # Clearly visible to many
    PERMEABILITY_OVERLAP: float = 0.6   # Worlds overlap significantly
    PERMEABILITY_MERGE: float = 0.8     # Near-convergence

    # Corruption
    CORRUPTION_SPREAD_RATE: float = 0.01
    CORRUPTION_PURIFY_THRESHOLD: float = 0.7  # Spirit affinity needed
    MAX_CORRUPTION: float = 1.0

    # Tsukumogami
    TSUKUMOGAMI_AGE_THRESHOLD: int = 100  # Years for natural awakening
    TSUKUMOGAMI_LOVE_THRESHOLD: float = 0.8  # Deep love can awaken sooner
    PERMEATION_AWAKENING_BOOST: float = 0.5  # High permeation speeds awakening


# Singleton instances
DISPLAY = DisplayConfig()
GAMEPLAY = GameplayConfig()
AUDIO = AudioConfig()
SPIRIT = SpiritConfig()
