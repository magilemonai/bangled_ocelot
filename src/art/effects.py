"""Ma no Kuni (間の国) - Visual Effects System.

Implements the atmospheric effects that bring the dual-realm world to life:

 - **Spirit Shimmer**: A rippling luminance overlay on spirit-realm entities.
 - **Veil Transitions**: Animated tear/dissolve when shifting between
   Material and Spirit vision.
 - **Ma Glow**: A pulsing aura whose frequency slows as ma accumulates,
   visualising the stretching of subjective time.
 - **Memory Fragments**: Floating particles of gold light representing
   echoes of past events.
 - **Corruption Spread**: An oil-slick, creeping visual that consumes
   healthy tiles when balance is disrupted.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from src.art.palette import Color, Palette, PaletteManager, PaletteMode
from src.art.sprites import (
    AnimationPlayback,
    AnimationSequence,
    BreathingParams,
    PixelGrid,
    SpriteCategory,
    SpriteDefinition,
    SpriteFrame,
    ma_glow_alpha,
    ma_glow_pulse_period_ms,
)
from src.art.pixel_art import RenderTarget


# ---------------------------------------------------------------------------
# Effect lifecycle
# ---------------------------------------------------------------------------

class EffectState(Enum):
    """Lifecycle stage of a visual effect instance."""
    PENDING = auto()     # Created but not yet started
    ACTIVE = auto()      # Currently running
    FADING = auto()      # In exit transition
    FINISHED = auto()    # Complete; can be reclaimed


# ---------------------------------------------------------------------------
# Base effect
# ---------------------------------------------------------------------------

@dataclass
class VisualEffect:
    """Abstract base for all visual effects.

    Subclasses implement ``update`` to advance state and ``apply`` to
    composite their visuals onto a ``RenderTarget``.

    Attributes:
        name: Effect identifier.
        state: Current lifecycle stage.
        elapsed_ms: Time since activation.
        duration_ms: Total runtime (0 = infinite).
        x: World x-position of the effect origin.
        y: World y-position of the effect origin.
        layer: Which render layer this effect targets.
    """
    name: str
    state: EffectState = EffectState.PENDING
    elapsed_ms: float = 0.0
    duration_ms: float = 0.0
    x: float = 0.0
    y: float = 0.0
    layer: PaletteMode = PaletteMode.SPIRIT

    def start(self) -> None:
        """Activate the effect."""
        self.state = EffectState.ACTIVE
        self.elapsed_ms = 0.0

    def update(self, dt_ms: float) -> None:
        """Advance the effect clock; manage lifecycle transitions."""
        if self.state is not EffectState.ACTIVE:
            return
        self.elapsed_ms += dt_ms
        if 0 < self.duration_ms <= self.elapsed_ms:
            self.state = EffectState.FADING

    def apply(self, target: RenderTarget) -> None:
        """Composite this effect onto a render target.  Override in subclass."""
        pass

    @property
    def is_alive(self) -> bool:
        return self.state not in (EffectState.FINISHED,)


# ---------------------------------------------------------------------------
# Spirit Shimmer
# ---------------------------------------------------------------------------

@dataclass
class SpiritShimmerEffect(VisualEffect):
    """A rippling luminance overlay that makes spirits look ethereal.

    Creates scanline-like horizontal bands of increased brightness that
    scroll vertically through the affected region, producing a gentle
    shimmer reminiscent of heat haze or refracted light.

    Attributes:
        width: Pixel width of the shimmer region.
        height: Pixel height of the shimmer region.
        band_height: Height of each luminance band in pixels.
        scroll_speed: Vertical scroll speed in pixels per second.
        intensity: Peak alpha of the shimmer overlay [0, 255].
        color: Tint color for the shimmer bands.
    """
    width: int = 32
    height: int = 32
    band_height: int = 3
    scroll_speed: float = 20.0
    intensity: int = 80
    color: Color = field(default_factory=lambda: Color.hex("#FFFFFF40"))

    def __post_init__(self) -> None:
        self.name = self.name or "spirit_shimmer"
        self.layer = PaletteMode.SPIRIT

    def apply(self, target: RenderTarget) -> None:
        if self.state is not EffectState.ACTIVE:
            return
        scroll_offset = (self.elapsed_ms / 1000.0) * self.scroll_speed
        ox = int(self.x)
        oy = int(self.y)

        for ly in range(self.height):
            # Determine if this row falls within a bright band
            world_y = ly + scroll_offset
            band_pos = world_y % (self.band_height * 2)
            if band_pos < self.band_height:
                # Inside a bright band; intensity fades toward edges
                center_dist = abs(band_pos - self.band_height / 2.0)
                falloff = 1.0 - (center_dist / (self.band_height / 2.0))
                alpha = round(self.intensity * falloff)
                shimmer_color = Color(
                    self.color.r, self.color.g, self.color.b,
                    max(0, min(255, alpha)),
                )
                for lx in range(self.width):
                    target.blend_pixel(ox + lx, oy + ly, shimmer_color)


# ---------------------------------------------------------------------------
# Veil Transition
# ---------------------------------------------------------------------------

@dataclass
class VeilTransitionEffect(VisualEffect):
    """Animated transition when shifting between Material and Spirit vision.

    The veil "tears" open from the center outward, revealing the spirit
    layer underneath.  During the transition, pixels along the tear edge
    emit a bright magenta-white glow.

    Attributes:
        screen_width: Full screen width in pixels.
        screen_height: Full screen height in pixels.
        transition_ms: Duration of the full open/close transition.
        is_opening: True if going Material->Spirit, False for reverse.
        tear_color: Color of the veil tear edge.
        veil_color: Base color of the veil membrane.
    """
    screen_width: int = 256
    screen_height: int = 192
    transition_ms: float = 1500.0
    is_opening: bool = True
    tear_color: Color = field(default_factory=lambda: Color.hex("#FF00FF80"))
    veil_color: Color = field(default_factory=lambda: Color.hex("#FFFFFF20"))

    def __post_init__(self) -> None:
        self.name = self.name or "veil_transition"
        self.duration_ms = self.transition_ms
        self.layer = PaletteMode.BOTH

    @property
    def progress(self) -> float:
        """Transition progress [0.0, 1.0]."""
        if self.transition_ms <= 0:
            return 1.0
        return min(1.0, self.elapsed_ms / self.transition_ms)

    def apply(self, target: RenderTarget) -> None:
        if self.state is not EffectState.ACTIVE:
            return

        p = self.progress
        if not self.is_opening:
            p = 1.0 - p

        # The "tear" expands as an ellipse from center
        cx = self.screen_width / 2.0
        cy = self.screen_height / 2.0
        max_radius = math.sqrt(cx * cx + cy * cy)
        current_radius = max_radius * p

        edge_width = 4.0  # Pixels of glow at the tear edge

        for y in range(min(self.screen_height, target.height)):
            dy = y - cy
            for x in range(min(self.screen_width, target.width)):
                dx = x - cx
                dist = math.sqrt(dx * dx + dy * dy)

                if dist < current_radius - edge_width:
                    # Inside the tear: fully open, no overlay
                    continue
                elif dist < current_radius + edge_width:
                    # On the tear edge: bright glow
                    edge_factor = 1.0 - abs(dist - current_radius) / edge_width
                    alpha = round(self.tear_color.a * edge_factor)
                    glow = Color(
                        self.tear_color.r, self.tear_color.g,
                        self.tear_color.b, max(0, min(255, alpha)),
                    )
                    target.blend_pixel(x, y, glow)
                else:
                    # Outside the tear: veil membrane
                    target.blend_pixel(x, y, self.veil_color)

    def update(self, dt_ms: float) -> None:
        super().update(dt_ms)
        if self.progress >= 1.0 and self.state is EffectState.ACTIVE:
            self.state = EffectState.FADING


# ---------------------------------------------------------------------------
# Ma Glow
# ---------------------------------------------------------------------------

@dataclass
class MaGlowEffect(VisualEffect):
    """Pulsing aura visualising accumulated Ma energy.

    The pulse rate is inversely proportional to ``ma_current``: as ma
    builds, the glow breathes more slowly, creating the impression that
    time is stretching.

    At critical ma levels the glow shifts from soft indigo to bright
    violet-white, warning that the boundary is thinning.

    Attributes:
        ma_current: Current ma energy level.
        ma_max: Upper bound for ma energy.
        radius: Glow radius in pixels.
        color_low: Color at low ma.
        color_mid: Color at mid ma.
        color_high: Color at high ma.
        color_critical: Color at critical ma.
    """
    ma_current: float = 0.0
    ma_max: float = 100.0
    radius: int = 24
    color_low: Color = field(default_factory=lambda: Color.hex("#6644AA60"))
    color_mid: Color = field(default_factory=lambda: Color.hex("#8866CCAA"))
    color_high: Color = field(default_factory=lambda: Color.hex("#AA88EEDD"))
    color_critical: Color = field(default_factory=lambda: Color.hex("#CC99FFFF"))

    def __post_init__(self) -> None:
        self.name = self.name or "ma_glow"
        self.layer = PaletteMode.SPIRIT
        self.duration_ms = 0.0  # Infinite; bound to gameplay

    def set_ma(self, value: float) -> None:
        """Update the current ma level."""
        self.ma_current = max(0.0, min(self.ma_max, value))

    @property
    def _ma_ratio(self) -> float:
        return self.ma_current / self.ma_max if self.ma_max > 0 else 0.0

    def _current_color(self) -> Color:
        """Interpolate the glow color based on ma ratio."""
        ratio = self._ma_ratio
        if ratio < 0.33:
            return self.color_low.lerp(self.color_mid, ratio / 0.33)
        if ratio < 0.66:
            return self.color_mid.lerp(self.color_high, (ratio - 0.33) / 0.33)
        return self.color_high.lerp(self.color_critical, (ratio - 0.66) / 0.34)

    def apply(self, target: RenderTarget) -> None:
        if self.state is not EffectState.ACTIVE:
            return

        alpha_pulse = ma_glow_alpha(self.elapsed_ms, self.ma_current, self.ma_max)
        base_color = self._current_color()
        cx = int(self.x)
        cy = int(self.y)

        for dy in range(-self.radius, self.radius + 1):
            for dx in range(-self.radius, self.radius + 1):
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > self.radius:
                    continue
                # Radial falloff
                falloff = 1.0 - (dist / self.radius)
                effective_alpha = round(
                    base_color.a * falloff * (alpha_pulse / 255.0)
                )
                glow_px = Color(
                    base_color.r, base_color.g, base_color.b,
                    max(0, min(255, effective_alpha)),
                )
                target.blend_pixel(cx + dx, cy + dy, glow_px)


# ---------------------------------------------------------------------------
# Memory Fragment
# ---------------------------------------------------------------------------

@dataclass
class MemoryParticle:
    """A single floating particle of memory-gold light."""
    x: float
    y: float
    vx: float
    vy: float
    life_ms: float
    max_life_ms: float
    size: int = 2

    @property
    def alpha_ratio(self) -> float:
        """Fade in quickly, linger, fade out slowly."""
        if self.max_life_ms <= 0:
            return 0.0
        t = self.life_ms / self.max_life_ms
        if t < 0.1:
            return t / 0.1
        if t > 0.7:
            return (1.0 - t) / 0.3
        return 1.0


@dataclass
class MemoryFragmentEffect(VisualEffect):
    """Floating motes of golden light representing memory echoes.

    Particles drift upward and outward, fading as they go, creating
    the impression of memories literally dissolving into the air.

    Attributes:
        particle_count: Number of concurrent particles.
        spawn_radius: Radius around origin where particles appear.
        particle_life_ms: Lifespan of each particle.
        color: Base color of memory particles.
    """
    particle_count: int = 12
    spawn_radius: float = 16.0
    particle_life_ms: float = 2000.0
    color: Color = field(default_factory=lambda: Color.hex("#FFD700"))
    _particles: List[MemoryParticle] = field(default_factory=list, repr=False)
    _rng: random.Random = field(
        default_factory=lambda: random.Random(42), repr=False,
    )

    def __post_init__(self) -> None:
        self.name = self.name or "memory_fragment"
        self.layer = PaletteMode.SPIRIT

    def start(self) -> None:
        super().start()
        self._spawn_initial()

    def _spawn_initial(self) -> None:
        self._particles.clear()
        for _ in range(self.particle_count):
            self._spawn_particle(stagger=True)

    def _spawn_particle(self, stagger: bool = False) -> None:
        angle = self._rng.uniform(0, 2 * math.pi)
        dist = self._rng.uniform(0, self.spawn_radius)
        speed = self._rng.uniform(5.0, 15.0)
        p = MemoryParticle(
            x=self.x + math.cos(angle) * dist,
            y=self.y + math.sin(angle) * dist,
            vx=math.cos(angle) * speed * 0.3,
            vy=-abs(math.sin(angle) * speed),  # Drift upward
            life_ms=self._rng.uniform(0, self.particle_life_ms) if stagger else 0.0,
            max_life_ms=self.particle_life_ms,
            size=self._rng.choice([1, 2, 2, 3]),
        )
        self._particles.append(p)

    def update(self, dt_ms: float) -> None:
        super().update(dt_ms)
        if self.state is not EffectState.ACTIVE:
            return
        dt_s = dt_ms / 1000.0
        survivors: List[MemoryParticle] = []
        for p in self._particles:
            p.life_ms += dt_ms
            p.x += p.vx * dt_s
            p.y += p.vy * dt_s
            if p.life_ms < p.max_life_ms:
                survivors.append(p)
            else:
                # Respawn at origin
                self._spawn_particle()
        self._particles = survivors

    def apply(self, target: RenderTarget) -> None:
        if self.state is not EffectState.ACTIVE:
            return
        for p in self._particles:
            alpha = round(self.color.a * p.alpha_ratio)
            if alpha <= 0:
                continue
            c = Color(self.color.r, self.color.g, self.color.b, alpha)
            px, py = int(p.x), int(p.y)
            for dy in range(p.size):
                for dx in range(p.size):
                    target.blend_pixel(px + dx, py + dy, c)


# ---------------------------------------------------------------------------
# Corruption Spread
# ---------------------------------------------------------------------------

@dataclass
class CorruptionCell:
    """State of a single tile in the corruption grid."""
    x: int
    y: int
    intensity: float = 0.0        # 0.0 = clean, 1.0 = fully corrupted
    growth_rate: float = 0.001    # Intensity increase per ms
    is_source: bool = False       # True if this cell originates corruption


@dataclass
class CorruptionSpreadEffect(VisualEffect):
    """An oil-slick corruption that creeps across tiles.

    Corruption originates from source cells and spreads to neighbours once
    a cell reaches a threshold intensity.  The visual is a dark, iridescent
    overlay with shifting purple-black tones.

    Attributes:
        grid_width: Number of tiles horizontally.
        grid_height: Number of tiles vertically.
        tile_size: Pixel size of each tile.
        spread_threshold: Intensity at which a cell starts infecting neighbours.
        color_base: Base corruption color (dark).
        color_iridescent: Iridescent accent (shifts over time).
    """
    grid_width: int = 8
    grid_height: int = 8
    tile_size: int = 32
    spread_threshold: float = 0.5
    color_base: Color = field(default_factory=lambda: Color.hex("#0D0D0D"))
    color_iridescent: Color = field(default_factory=lambda: Color.hex("#4A0040"))
    _grid: Dict[Tuple[int, int], CorruptionCell] = field(
        default_factory=dict, repr=False,
    )

    def __post_init__(self) -> None:
        self.name = self.name or "corruption_spread"
        self.layer = PaletteMode.BOTH
        self.duration_ms = 0.0  # Infinite

    def add_source(self, gx: int, gy: int, rate: float = 0.002) -> None:
        """Mark a grid cell as a corruption source."""
        cell = self._get_or_create(gx, gy)
        cell.is_source = True
        cell.growth_rate = rate

    def _get_or_create(self, gx: int, gy: int) -> CorruptionCell:
        key = (gx, gy)
        if key not in self._grid:
            self._grid[key] = CorruptionCell(x=gx, y=gy)
        return self._grid[key]

    def update(self, dt_ms: float) -> None:
        super().update(dt_ms)
        if self.state is not EffectState.ACTIVE:
            return

        # Grow existing cells
        cells_to_spread: List[CorruptionCell] = []
        for cell in list(self._grid.values()):
            if cell.intensity < 1.0:
                cell.intensity = min(1.0, cell.intensity + cell.growth_rate * dt_ms)
            if cell.intensity >= self.spread_threshold:
                cells_to_spread.append(cell)

        # Spread to neighbours
        for cell in cells_to_spread:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cell.x + dx, cell.y + dy
                if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                    neighbour = self._get_or_create(nx, ny)
                    if neighbour.intensity == 0.0:
                        # Infect at a slower rate than the source
                        neighbour.growth_rate = cell.growth_rate * 0.6

    def apply(self, target: RenderTarget) -> None:
        if self.state is not EffectState.ACTIVE:
            return

        # Iridescent hue shift based on time
        hue_shift = math.sin(self.elapsed_ms / 3000.0) * 0.5 + 0.5
        iridescent = self.color_base.lerp(self.color_iridescent, hue_shift)

        for cell in self._grid.values():
            if cell.intensity <= 0.0:
                continue
            alpha = round(200 * cell.intensity)
            corruption_color = Color(
                iridescent.r, iridescent.g, iridescent.b,
                max(0, min(255, alpha)),
            )
            # Fill the tile
            base_x = int(self.x) + cell.x * self.tile_size
            base_y = int(self.y) + cell.y * self.tile_size
            for py in range(self.tile_size):
                for px in range(self.tile_size):
                    # Oil-slick pattern: edges more intense
                    edge_dist = min(px, py, self.tile_size - 1 - px, self.tile_size - 1 - py)
                    edge_factor = 1.0 - min(1.0, edge_dist / (self.tile_size * 0.3))
                    # Creeping tendrils using simple noise
                    noise = math.sin(px * 0.8 + self.elapsed_ms * 0.002) * \
                            math.cos(py * 0.6 + self.elapsed_ms * 0.0015) * 0.5 + 0.5
                    final_alpha = round(
                        corruption_color.a * (0.4 + 0.6 * edge_factor) * (0.5 + 0.5 * noise)
                    )
                    px_color = Color(
                        corruption_color.r, corruption_color.g,
                        corruption_color.b, max(0, min(255, final_alpha)),
                    )
                    target.blend_pixel(base_x + px, base_y + py, px_color)


# ---------------------------------------------------------------------------
# Effect Manager
# ---------------------------------------------------------------------------

class EffectManager:
    """Manages the lifecycle of all active visual effects.

    Call ``update`` each frame with the delta time, then ``apply_all``
    to composite effects onto the appropriate render targets.

    Usage::

        em = EffectManager()
        shimmer = SpiritShimmerEffect(name="shrine_shimmer", x=100, y=50)
        em.add(shimmer)
        shimmer.start()

        # Each frame:
        em.update(dt_ms)
        em.apply_spirit(spirit_target)
        em.apply_material(material_target)
    """

    def __init__(self) -> None:
        self._effects: List[VisualEffect] = []

    def add(self, effect: VisualEffect) -> None:
        """Register a new effect."""
        self._effects.append(effect)

    def remove(self, name: str) -> None:
        """Remove all effects matching a name."""
        self._effects = [e for e in self._effects if e.name != name]

    def update(self, dt_ms: float) -> None:
        """Advance all effects; garbage-collect finished ones."""
        for effect in self._effects:
            effect.update(dt_ms)
        # Promote FADING -> FINISHED after one more frame
        for effect in self._effects:
            if effect.state is EffectState.FADING:
                effect.state = EffectState.FINISHED
        self._effects = [e for e in self._effects if e.is_alive]

    def apply_spirit(self, target: RenderTarget) -> None:
        """Apply all Spirit-layer effects to a render target."""
        for effect in self._effects:
            if effect.layer in (PaletteMode.SPIRIT, PaletteMode.BOTH):
                effect.apply(target)

    def apply_material(self, target: RenderTarget) -> None:
        """Apply all Material-layer effects to a render target."""
        for effect in self._effects:
            if effect.layer in (PaletteMode.MATERIAL, PaletteMode.BOTH):
                effect.apply(target)

    def get_by_name(self, name: str) -> List[VisualEffect]:
        """Return all active effects matching a name."""
        return [e for e in self._effects if e.name == name]

    @property
    def active_count(self) -> int:
        return len(self._effects)

    def clear(self) -> None:
        """Remove all effects immediately."""
        self._effects.clear()
