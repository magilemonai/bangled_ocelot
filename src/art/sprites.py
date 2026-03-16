"""Ma no Kuni (間の国) - Sprite Definition and Animation System.

Handles sprite sheets, frame-based animation with variable timing,
directional states, and the dual-layer Material/Spirit rendering model.

Spirits have a constant subtle "breathing" animation overlaid on top of
their normal animation cycle.  The ma_glow effect pulse rate is inversely
proportional to accumulated ma, visualising the slowing of time.
"""

from __future__ import annotations

import math
import copy
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Sequence, Tuple

from src.art.palette import Color, Palette, PaletteMode


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Direction(Enum):
    """Cardinal facing direction for walk cycles and idle frames."""
    DOWN = auto()   # Toward camera (default front-facing)
    UP = auto()
    LEFT = auto()
    RIGHT = auto()


class SpriteCategory(Enum):
    """High-level classification of a sprite's purpose."""
    PLAYER = auto()
    NPC = auto()
    SPIRIT = auto()
    ENVIRONMENT = auto()
    EFFECT = auto()
    UI = auto()


class AnimationPlayback(Enum):
    """How an animation sequence is iterated."""
    LOOP = auto()            # 1-2-3-1-2-3-...
    PING_PONG = auto()       # 1-2-3-2-1-2-3-...
    ONCE = auto()            # 1-2-3 then hold last frame
    ONCE_AND_HIDE = auto()   # 1-2-3 then invisible


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------

PixelGrid = List[List[int]]
"""2-D array of palette indices.  ``grid[y][x]`` gives the color index."""


@dataclass
class SpriteFrame:
    """A single frame of pixel data within a sprite animation.

    Attributes:
        pixels: 2-D list of palette indices (row-major, ``pixels[y][x]``).
        duration_ms: How long this frame displays before advancing.
        offset_x: Optional per-frame horizontal offset (for bounce, etc.).
        offset_y: Optional per-frame vertical offset.
    """
    pixels: PixelGrid
    duration_ms: int = 150
    offset_x: int = 0
    offset_y: int = 0

    @property
    def height(self) -> int:
        return len(self.pixels)

    @property
    def width(self) -> int:
        return len(self.pixels[0]) if self.pixels else 0

    def get_pixel(self, x: int, y: int) -> int:
        """Return the palette index at (x, y), or 0 (transparent) if OOB."""
        if 0 <= y < self.height and 0 <= x < self.width:
            return self.pixels[y][x]
        return 0


@dataclass
class AnimationSequence:
    """An ordered sequence of frames that form a single animation.

    Examples: ``idle_down``, ``walk_left``, ``spirit_sight_active``.
    """
    name: str
    frames: List[SpriteFrame] = field(default_factory=list)
    playback: AnimationPlayback = AnimationPlayback.LOOP
    base_speed: float = 1.0

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def total_duration_ms(self) -> int:
        return sum(f.duration_ms for f in self.frames)

    def frame_at_time(self, elapsed_ms: float, speed_mult: float = 1.0) -> SpriteFrame:
        """Return the frame visible at *elapsed_ms* (affected by speed)."""
        if not self.frames:
            raise ValueError(f"Animation '{self.name}' has no frames")

        effective_speed = self.base_speed * speed_mult
        if effective_speed <= 0:
            return self.frames[0]

        adj_elapsed = elapsed_ms * effective_speed

        if self.playback is AnimationPlayback.ONCE:
            return self._frame_at_once(adj_elapsed)
        if self.playback is AnimationPlayback.ONCE_AND_HIDE:
            return self._frame_at_once(adj_elapsed)
        if self.playback is AnimationPlayback.PING_PONG:
            return self._frame_at_ping_pong(adj_elapsed)
        return self._frame_at_loop(adj_elapsed)

    # -- internal playback ----------------------------------------------------

    def _frame_at_loop(self, ms: float) -> SpriteFrame:
        total = self.total_duration_ms
        if total == 0:
            return self.frames[0]
        ms = ms % total
        return self._scan_frames(ms)

    def _frame_at_once(self, ms: float) -> SpriteFrame:
        total = self.total_duration_ms
        if ms >= total:
            return self.frames[-1]
        return self._scan_frames(ms)

    def _frame_at_ping_pong(self, ms: float) -> SpriteFrame:
        if len(self.frames) < 2:
            return self.frames[0]
        # Forward + reverse (excluding endpoints to avoid double-display)
        forward_dur = self.total_duration_ms
        reverse_frames = list(reversed(self.frames[1:-1]))
        reverse_dur = sum(f.duration_ms for f in reverse_frames)
        cycle = forward_dur + reverse_dur
        if cycle == 0:
            return self.frames[0]
        ms = ms % cycle
        if ms < forward_dur:
            return self._scan_frames(ms)
        ms -= forward_dur
        return self._scan_frames_list(ms, reverse_frames)

    def _scan_frames(self, ms: float) -> SpriteFrame:
        return self._scan_frames_list(ms, self.frames)

    @staticmethod
    def _scan_frames_list(ms: float, frames: List[SpriteFrame]) -> SpriteFrame:
        accum = 0.0
        for frame in frames:
            accum += frame.duration_ms
            if ms < accum:
                return frame
        return frames[-1]


# ---------------------------------------------------------------------------
# Breathing overlay for spirit entities
# ---------------------------------------------------------------------------

@dataclass
class BreathingParams:
    """Parameters for the spirit "breathing" ambient animation.

    The breathing effect modulates alpha and a slight vertical offset
    with a sine wave, giving spirits a hovering, pulsing appearance.
    """
    alpha_min: int = 180
    alpha_max: int = 255
    offset_min: float = -1.0
    offset_max: float = 1.0
    cycle_ms: float = 2000.0   # One full breath cycle

    def alpha_at(self, elapsed_ms: float) -> int:
        """Compute current alpha based on a sinusoidal breath cycle."""
        t = math.sin(2 * math.pi * elapsed_ms / self.cycle_ms)
        norm = (t + 1.0) / 2.0  # 0..1
        return round(self.alpha_min + (self.alpha_max - self.alpha_min) * norm)

    def y_offset_at(self, elapsed_ms: float) -> float:
        """Compute current vertical offset (gentle hover)."""
        t = math.sin(2 * math.pi * elapsed_ms / self.cycle_ms)
        norm = (t + 1.0) / 2.0
        return self.offset_min + (self.offset_max - self.offset_min) * norm


# ---------------------------------------------------------------------------
# Sprite Definition
# ---------------------------------------------------------------------------

@dataclass
class SpriteDefinition:
    """Complete definition of a game sprite.

    Holds every animation, the palette mode, dimensions, and optional
    spirit-breathing parameters.

    Attributes:
        name: Unique identifier (e.g. ``aoi``, ``kodama``, ``road_tile``).
        category: Classification for rendering pipeline routing.
        width: Width in pixels of each frame.
        height: Height in pixels of each frame.
        palette_mode: Which palette layer(s) this sprite uses.
        animations: Mapping of animation name to ``AnimationSequence``.
        breathing: If set, spirit-breathing is applied on top of animation.
        z_order: Rendering depth; higher values draw later (on top).
        origin_x: Horizontal anchor point within the frame.
        origin_y: Vertical anchor point within the frame.
        tags: Arbitrary metadata tags (e.g. ``["interactable", "quest"]``).
    """
    name: str
    category: SpriteCategory
    width: int
    height: int
    palette_mode: PaletteMode = PaletteMode.MATERIAL
    animations: Dict[str, AnimationSequence] = field(default_factory=dict)
    breathing: Optional[BreathingParams] = None
    z_order: int = 0
    origin_x: int = 0
    origin_y: int = 0
    tags: List[str] = field(default_factory=list)

    # -- convenience ----------------------------------------------------------

    @property
    def is_spirit(self) -> bool:
        return self.category is SpriteCategory.SPIRIT

    @property
    def animation_names(self) -> List[str]:
        return list(self.animations.keys())

    def get_animation(self, name: str) -> AnimationSequence:
        """Retrieve an animation by name, raising ``KeyError`` if missing."""
        return self.animations[name]

    def add_animation(self, anim: AnimationSequence) -> None:
        """Register an animation sequence."""
        self.animations[anim.name] = anim

    def get_frame(
        self,
        animation_name: str,
        elapsed_ms: float,
        speed_mult: float = 1.0,
    ) -> SpriteFrame:
        """Convenience: get the current frame from a named animation."""
        return self.animations[animation_name].frame_at_time(elapsed_ms, speed_mult)


# ---------------------------------------------------------------------------
# Sprite Instance  -  runtime state for an on-screen sprite
# ---------------------------------------------------------------------------

@dataclass
class SpriteInstance:
    """A live, on-screen instance of a ``SpriteDefinition``.

    Tracks position, current animation, elapsed time, and overlay effects.
    Multiple instances can share the same definition.
    """
    definition: SpriteDefinition
    x: float = 0.0
    y: float = 0.0
    current_animation: str = ""
    elapsed_ms: float = 0.0
    speed_multiplier: float = 1.0
    visible: bool = True
    flip_h: bool = False
    flip_v: bool = False
    alpha_override: Optional[int] = None
    direction: Direction = Direction.DOWN

    def __post_init__(self) -> None:
        if not self.current_animation and self.definition.animations:
            self.current_animation = next(iter(self.definition.animations))

    def update(self, dt_ms: float) -> None:
        """Advance the animation clock by *dt_ms* milliseconds."""
        self.elapsed_ms += dt_ms

    def set_animation(self, name: str, reset: bool = True) -> None:
        """Switch to a different animation, optionally resetting the clock."""
        if name not in self.definition.animations:
            raise KeyError(
                f"Animation '{name}' not found in sprite '{self.definition.name}'"
            )
        if self.current_animation != name:
            self.current_animation = name
            if reset:
                self.elapsed_ms = 0.0

    def current_frame(self) -> SpriteFrame:
        """Return the current animation frame."""
        return self.definition.get_frame(
            self.current_animation,
            self.elapsed_ms,
            self.speed_multiplier,
        )

    def breathing_alpha(self) -> int:
        """Current breathing-modulated alpha (255 if no breathing)."""
        if self.definition.breathing is None:
            return self.alpha_override if self.alpha_override is not None else 255
        base_alpha = self.definition.breathing.alpha_at(self.elapsed_ms)
        if self.alpha_override is not None:
            return round(base_alpha * self.alpha_override / 255)
        return base_alpha

    def breathing_y_offset(self) -> float:
        """Current breathing vertical offset (0 if no breathing)."""
        if self.definition.breathing is None:
            return 0.0
        return self.definition.breathing.y_offset_at(self.elapsed_ms)

    def render_position(self) -> Tuple[float, float]:
        """Screen position accounting for origin offset and breathing."""
        bx = 0.0
        by = self.breathing_y_offset()
        return (
            self.x - self.definition.origin_x + bx,
            self.y - self.definition.origin_y + by,
        )


# ---------------------------------------------------------------------------
# Sprite Sheet / Atlas
# ---------------------------------------------------------------------------

@dataclass
class SpriteSheet:
    """A collection of ``SpriteDefinition`` objects forming a sprite atlas.

    Used for batch loading and lookup by name.
    """
    name: str
    sprites: Dict[str, SpriteDefinition] = field(default_factory=dict)

    def add(self, sprite: SpriteDefinition) -> None:
        self.sprites[sprite.name] = sprite

    def get(self, name: str) -> SpriteDefinition:
        return self.sprites[name]

    def __contains__(self, name: str) -> bool:
        return name in self.sprites

    def __len__(self) -> int:
        return len(self.sprites)

    def by_category(self, category: SpriteCategory) -> List[SpriteDefinition]:
        """Return all sprites matching a given category."""
        return [s for s in self.sprites.values() if s.category is category]


# ---------------------------------------------------------------------------
# Ma-Glow Pulse Rate Calculation
# ---------------------------------------------------------------------------

def ma_glow_pulse_period_ms(ma_accumulated: float, ma_max: float = 100.0) -> float:
    """Calculate the ma_glow pulse period based on accumulated ma.

    As ma accumulates, the pulse slows -- visualising the sensation that
    time is stretching.  At zero ma the pulse is rapid (400 ms); at max
    it stretches to 4000 ms.

    Args:
        ma_accumulated: Current ma energy level.
        ma_max: The upper bound for ma energy.

    Returns:
        Pulse period in milliseconds.
    """
    MIN_PERIOD = 400.0
    MAX_PERIOD = 4000.0
    ratio = max(0.0, min(1.0, ma_accumulated / ma_max))
    return MIN_PERIOD + (MAX_PERIOD - MIN_PERIOD) * ratio


def ma_glow_alpha(
    elapsed_ms: float,
    ma_accumulated: float,
    ma_max: float = 100.0,
) -> int:
    """Compute the current ma-glow alpha for a pulsing overlay.

    Returns a value in [60, 255] that oscillates with the period
    determined by ``ma_glow_pulse_period_ms``.
    """
    period = ma_glow_pulse_period_ms(ma_accumulated, ma_max)
    t = math.sin(2 * math.pi * elapsed_ms / period)
    norm = (t + 1.0) / 2.0
    return round(60 + (255 - 60) * norm)
