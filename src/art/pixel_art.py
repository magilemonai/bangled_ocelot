"""Ma no Kuni (間の国) - Pixel Art Generation and Rendering Utilities.

Provides functions to:
 - generate pixel art as 2-D arrays of palette indices,
 - composite Material and Spirit layers with permeability blending,
 - produce actual pixel data for key sprites,
 - export to flat RGBA buffers suitable for texture upload.

Includes hand-crafted pixel data for:
 - Aoi (front-facing idle, 64x64)
 - Kodama spirit (32x32)
 - Road / shrine / park tile samples (32x32 each)
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from src.art.palette import (
    Color,
    Palette,
    PaletteManager,
    PaletteMode,
)
from src.art.sprites import (
    AnimationPlayback,
    AnimationSequence,
    BreathingParams,
    Direction,
    PixelGrid,
    SpriteCategory,
    SpriteDefinition,
    SpriteFrame,
)


# ---------------------------------------------------------------------------
# Palette index aliases (Material)
# ---------------------------------------------------------------------------
# These short constants match ``create_material_palette()`` index order
# so pixel data below is readable.  Index 0 is always transparent.

_M = {
    "_": 0,   # transparent
    "Cd": 1,  # concrete_dark
    "Cm": 2,  # concrete_mid
    "Cl": 3,  # concrete_light
    "As": 4,  # asphalt
    "Lw": 5,  # lamp_warm
    "Lh": 6,  # lamp_hot
    "Ld": 7,  # lamp_dim
    "Np": 8,  # neon_pink
    "Ng": 9,  # neon_green
    "Nb": 10, # neon_blue
    "No": 11, # neon_orange
    "Wd": 12, # wood_dark
    "Wm": 13, # wood_mid
    "Wl": 14, # wood_light
    "Ww": 15, # wood_weathered
    "Sd": 16, # sky_day
    "Ss": 17, # sky_sunset
    "Sn": 18, # sky_night
    "Lg": 19, # leaf_green
    "Lk": 20, # leaf_dark
    "Ms": 21, # moss
    "Sl": 22, # skin_light
    "Sm": 23, # skin_mid
    "Sh": 24, # skin_shadow
    "Cw": 25, # cloth_white
    "Cr": 26, # cloth_red
    "Ci": 27, # cloth_indigo
    "Cb": 28, # cloth_black
    "Ws": 29, # water_surface
    "Wp": 30, # water_deep
    "Ru": 31, # rust
    "Tw": 32, # tile_white
    "Tb": 33, # tile_blue
    "Bk": 34, # black
    "Wh": 35, # white
}

# Spirit palette index aliases
_S = {
    "_": 0,   # transparent
    "Di": 1,  # deep_indigo
    "Im": 2,  # indigo_mid
    "Sb": 3,  # spirit_blue
    "Sl": 4,  # spirit_blue_light
    "Gw": 5,  # ghost_white
    "Gd": 6,  # ghost_dim
    "Gb": 7,  # ghost_bright
    "Fg": 8,  # foxfire_green
    "Fd": 9,  # foxfire_dim
    "Fb": 10, # foxfire_bright
    "Mg": 11, # memory_gold
    "Mw": 12, # memory_warm
    "Mf": 13, # memory_faded
    "Vb": 14, # void_black
    "Vd": 15, # void_deep
    "Sp": 16, # sakura_pink
    "Sd": 17, # sakura_deep
    "Sl2": 18, # sakura_pale
    "Cb": 19, # corruption_black
    "Cp": 20, # corruption_purple
    "Ci": 21, # corruption_iridescent
    "Co": 22, # corruption_oil
    "Ac": 23, # aura_calm
    "Aa": 24, # aura_alert
    "An": 25, # aura_ancient
    "Vs": 26, # veil_shimmer
    "Vt": 27, # veil_tear
    "Vst": 28, # veil_stable
    "Ml": 29, # ma_glow_low
    "Mm": 30, # ma_glow_mid
    "Mh": 31, # ma_glow_high
    "Mc": 32, # ma_glow_critical
}

# Shorthand helper
_ = 0


# ---------------------------------------------------------------------------
# Hand-crafted pixel data
# ---------------------------------------------------------------------------

def _aoi_front_idle_pixels() -> PixelGrid:
    """64x64 front-facing idle frame of Aoi.

    A teenage girl in a school uniform with a red scarf, dark hair.
    Simplified pixel representation using material palette indices.
    Uses index aliases from _M.

    Layout: Each row is 64 pixels wide. Transparent (0) is background.
    Key palette entries used:
      Cb(28)=cloth_black/hair, Sl(22)=skin_light, Sm(23)=skin_mid,
      Sh(24)=skin_shadow, Cw(25)=cloth_white, Cr(26)=cloth_red,
      Ci(27)=cloth_indigo, Bk(34)=black, Wh(35)=white
    """
    T = 0    # transparent
    H = 28   # hair (cloth_black)
    S = 22   # skin_light
    Sm = 23  # skin_mid
    Sh = 24  # skin_shadow
    W = 25   # cloth_white (shirt)
    R = 26   # cloth_red (scarf)
    I = 27   # cloth_indigo (skirt)
    B = 34   # black (eyes/outlines)
    E = 35   # white (eye highlight)
    Wd = 12  # wood_dark (shoes)

    # fmt: off
    return [
        # Rows 0-7: empty above head
        [T]*64,
        [T]*64,
        [T]*64,
        [T]*64,
        [T]*64,
        # Row 5-10: top of hair
        [T]*24 + [H]*16 + [T]*24,
        [T]*22 + [H]*20 + [T]*22,
        [T]*21 + [H]*22 + [T]*21,
        [T]*20 + [H]*24 + [T]*20,
        [T]*19 + [H]*26 + [T]*19,
        # Row 10-14: hair with face opening
        [T]*19 + [H]*26 + [T]*19,
        [T]*18 + [H]*4 + [S]*20 + [H]*4 + [T]*18,
        [T]*18 + [H]*3 + [S]*22 + [H]*3 + [T]*18,
        [T]*18 + [H]*2 + [S]*24 + [H]*2 + [T]*18,
        [T]*18 + [H]*2 + [S]*24 + [H]*2 + [T]*18,
        # Row 15-19: face with eyes
        [T]*18 + [H]*2 + [S]*5 + [B]*3 + [S]*8 + [B]*3 + [S]*5 + [H]*2 + [T]*18,
        [T]*18 + [H]*2 + [S]*5 + [B]*1 + [E]*1 + [B]*1 + [S]*8 + [B]*1 + [E]*1 + [B]*1 + [S]*5 + [H]*2 + [T]*18,
        [T]*18 + [H]*2 + [S]*24 + [H]*2 + [T]*18,
        [T]*18 + [H]*2 + [S]*10 + [Sm]*4 + [S]*10 + [H]*2 + [T]*18,  # nose
        [T]*18 + [H]*2 + [S]*9 + [R]*6 + [S]*9 + [H]*2 + [T]*18,  # mouth area (rosy)
        # Row 20-22: chin, hair sides
        [T]*19 + [H]*2 + [S]*22 + [H]*2 + [T]*19,
        [T]*19 + [H]*3 + [S]*18 + [H]*3 + [T]*21,
        [T]*20 + [H]*4 + [Sm]*14 + [H]*4 + [T]*22,
        # Row 23-25: neck + scarf
        [T]*25 + [S]*4 + [Sm]*4 + [S]*4 + [T]*27,
        [T]*23 + [R]*18 + [T]*23,
        [T]*22 + [R]*20 + [T]*22,
        # Row 26-35: torso (white shirt)
        [T]*22 + [W]*20 + [T]*22,
        [T]*21 + [W]*22 + [T]*21,
        [T]*20 + [W]*24 + [T]*20,
        [T]*19 + [S]*2 + [W]*22 + [S]*2 + [T]*19,  # arms show skin at sides
        [T]*18 + [S]*3 + [W]*22 + [S]*3 + [T]*18,
        [T]*18 + [S]*3 + [W]*22 + [S]*3 + [T]*18,
        [T]*18 + [Sm]*3 + [W]*22 + [Sm]*3 + [T]*18,
        [T]*19 + [Sm]*2 + [W]*22 + [Sm]*2 + [T]*19,
        [T]*20 + [S]*1 + [W]*22 + [S]*1 + [T]*20,
        [T]*21 + [W]*22 + [T]*21,
        # Row 36-38: belt area
        [T]*21 + [B]*22 + [T]*21,
        [T]*21 + [I]*22 + [T]*21,
        [T]*21 + [I]*22 + [T]*21,
        # Row 39-48: skirt (indigo)
        [T]*21 + [I]*22 + [T]*21,
        [T]*20 + [I]*24 + [T]*20,
        [T]*20 + [I]*24 + [T]*20,
        [T]*20 + [I]*24 + [T]*20,
        [T]*19 + [I]*26 + [T]*19,
        [T]*19 + [I]*26 + [T]*19,
        [T]*19 + [I]*26 + [T]*19,
        [T]*19 + [I]*26 + [T]*19,
        [T]*20 + [I]*24 + [T]*20,
        [T]*20 + [I]*24 + [T]*20,
        # Row 49-54: legs (skin)
        [T]*23 + [Sm]*8 + [T]*4 + [Sm]*8 + [T]*21,
        [T]*23 + [S]*8 + [T]*4 + [S]*8 + [T]*21,
        [T]*23 + [S]*8 + [T]*4 + [S]*8 + [T]*21,
        [T]*23 + [S]*8 + [T]*4 + [S]*8 + [T]*21,
        [T]*23 + [S]*8 + [T]*4 + [S]*8 + [T]*21,
        [T]*23 + [Sm]*8 + [T]*4 + [Sm]*8 + [T]*21,
        # Row 55-58: shoes
        [T]*22 + [Wd]*10 + [T]*4 + [Wd]*10 + [T]*18,
        [T]*22 + [Wd]*10 + [T]*4 + [Wd]*10 + [T]*18,
        [T]*22 + [B]*10 + [T]*4 + [B]*10 + [T]*18,
        [T]*64,
        # Row 59-63: padding
        [T]*64,
        [T]*64,
        [T]*64,
        [T]*64,
        [T]*64,
    ]
    # fmt: on


def _kodama_idle_pixels() -> PixelGrid:
    """32x32 Kodama (tree spirit) idle frame.

    A small, round, ghostly white figure with dark eye-holes, glowing
    faintly.  Uses the Spirit palette.

    Key indices: Gw(5)=ghost_white, Gd(6)=ghost_dim, Gb(7)=ghost_bright,
    Di(1)=deep_indigo (eye holes), Fg(8)=foxfire_green (inner glow).
    """
    T = 0
    G = 5   # ghost_white
    Gd = 6  # ghost_dim
    Gb = 7  # ghost_bright
    D = 1   # deep_indigo (eyes)
    F = 8   # foxfire_green (inner glow)

    # fmt: off
    return [
        [T]*32,
        [T]*32,
        [T]*32,
        [T]*32,
        [T]*12 + [Gd]*8 + [T]*12,
        [T]*10 + [Gd]*2 + [G]*8 + [Gd]*2 + [T]*10,
        [T]*9 + [Gd]*1 + [G]*12 + [Gd]*1 + [T]*9,
        [T]*8 + [G]*16 + [T]*8,
        [T]*7 + [G]*18 + [T]*7,
        [T]*7 + [G]*18 + [T]*7,
        # Eyes
        [T]*7 + [G]*4 + [D]*3 + [G]*4 + [D]*3 + [G]*4 + [T]*7,
        [T]*7 + [G]*4 + [D]*3 + [G]*4 + [D]*3 + [G]*4 + [T]*7,
        [T]*7 + [G]*18 + [T]*7,
        # Mouth
        [T]*7 + [G]*6 + [D]*6 + [G]*6 + [T]*7,
        [T]*7 + [G]*18 + [T]*7,
        [T]*7 + [G]*18 + [T]*7,
        # Body widens with inner glow
        [T]*7 + [G]*4 + [Gb]*10 + [G]*4 + [T]*7,
        [T]*7 + [G]*3 + [Gb]*12 + [G]*3 + [T]*7,
        [T]*7 + [G]*3 + [F]*2 + [Gb]*8 + [F]*2 + [G]*3 + [T]*7,
        [T]*7 + [G]*3 + [Gb]*12 + [G]*3 + [T]*7,
        [T]*7 + [G]*3 + [Gb]*12 + [G]*3 + [T]*7,
        [T]*7 + [G]*4 + [Gb]*10 + [G]*4 + [T]*7,
        [T]*8 + [G]*16 + [T]*8,
        [T]*8 + [G]*16 + [T]*8,
        [T]*9 + [G]*14 + [T]*9,
        [T]*9 + [Gd]*2 + [G]*10 + [Gd]*2 + [T]*9,
        [T]*10 + [Gd]*12 + [T]*10,
        # Little feet / root tendrils
        [T]*11 + [Gd]*3 + [T]*4 + [Gd]*3 + [T]*11,
        [T]*11 + [Gd]*2 + [T]*6 + [Gd]*2 + [T]*11,
        [T]*32,
        [T]*32,
        [T]*32,
    ]
    # fmt: on


def _road_tile_pixels() -> PixelGrid:
    """32x32 asphalt road tile with lane markings.

    Uses Material palette. Primarily asphalt(4) with concrete markings.
    """
    A = 4   # asphalt
    C = 3   # concrete_light (lane marking)
    Cd = 1  # concrete_dark (texture variation)
    T = 0

    base_row = [A]*32
    marked_row = [A]*14 + [C]*4 + [A]*14
    textured_row = [A]*5 + [Cd]*1 + [A]*10 + [Cd]*1 + [A]*8 + [Cd]*1 + [A]*5

    rows: PixelGrid = []
    for i in range(32):
        if 13 <= i <= 18:
            rows.append(marked_row[:])
        elif i % 7 == 3:
            rows.append(textured_row[:])
        else:
            rows.append(base_row[:])
    return rows


def _shrine_tile_pixels() -> PixelGrid:
    """32x32 shrine ground tile with stone paving pattern.

    Material palette. Stone gray with mossy edges.
    """
    Cl = 3   # concrete_light (stone)
    Cm = 2   # concrete_mid (grout)
    M = 21   # moss
    Wd = 12  # wood_dark (torii accent)

    rows: PixelGrid = []
    for y in range(32):
        row = []
        for x in range(32):
            # Grout lines every 8 pixels
            if x % 8 == 0 or y % 8 == 0:
                row.append(Cm)
            # Moss in corners
            elif (x % 8 <= 1 and y % 8 <= 1):
                row.append(M)
            else:
                row.append(Cl)
        rows.append(row)
    return rows


def _park_tile_pixels() -> PixelGrid:
    """32x32 park grass tile with subtle variation.

    Material palette. Green tones with occasional flowers.
    """
    Lg = 19  # leaf_green
    Lk = 20  # leaf_dark
    Ms = 21  # moss

    rows: PixelGrid = []
    for y in range(32):
        row = []
        for x in range(32):
            # Pseudo-random texture using simple hash
            h = ((x * 7 + y * 13 + x * y) % 17)
            if h < 2:
                row.append(Lk)
            elif h < 4:
                row.append(Ms)
            else:
                row.append(Lg)
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Sprite builders  -  create full SpriteDefinition objects
# ---------------------------------------------------------------------------

def build_aoi_sprite() -> SpriteDefinition:
    """Build the complete Aoi sprite definition with front-facing idle frame."""
    pixels = _aoi_front_idle_pixels()
    idle_frame = SpriteFrame(pixels=pixels, duration_ms=500)

    # Walking frame is a slight modification (arm/leg shift)
    walk_pixels = _aoi_walk_variant(pixels)
    walk_frame_1 = SpriteFrame(pixels=pixels, duration_ms=200)
    walk_frame_2 = SpriteFrame(pixels=walk_pixels, duration_ms=200, offset_y=-1)
    walk_frame_3 = SpriteFrame(pixels=pixels, duration_ms=200)
    walk_frame_4 = SpriteFrame(
        pixels=_mirror_horizontal(walk_pixels), duration_ms=200, offset_y=-1,
    )

    sprite = SpriteDefinition(
        name="aoi",
        category=SpriteCategory.PLAYER,
        width=64,
        height=64,
        palette_mode=PaletteMode.MATERIAL,
        z_order=10,
        origin_x=32,
        origin_y=56,
    )

    sprite.add_animation(AnimationSequence(
        name="idle_down",
        frames=[idle_frame],
        playback=AnimationPlayback.LOOP,
    ))

    sprite.add_animation(AnimationSequence(
        name="walk_down",
        frames=[walk_frame_1, walk_frame_2, walk_frame_3, walk_frame_4],
        playback=AnimationPlayback.LOOP,
        base_speed=1.0,
    ))

    return sprite


def build_kodama_sprite() -> SpriteDefinition:
    """Build the Kodama spirit sprite with breathing animation."""
    pixels = _kodama_idle_pixels()
    frame_1 = SpriteFrame(pixels=pixels, duration_ms=600)
    frame_2 = SpriteFrame(pixels=_kodama_breathe_variant(pixels), duration_ms=600)

    sprite = SpriteDefinition(
        name="kodama",
        category=SpriteCategory.SPIRIT,
        width=32,
        height=32,
        palette_mode=PaletteMode.SPIRIT,
        z_order=8,
        origin_x=16,
        origin_y=28,
        breathing=BreathingParams(
            alpha_min=160,
            alpha_max=240,
            offset_min=-0.5,
            offset_max=0.5,
            cycle_ms=2500.0,
        ),
    )

    sprite.add_animation(AnimationSequence(
        name="idle",
        frames=[frame_1, frame_2],
        playback=AnimationPlayback.PING_PONG,
    ))

    return sprite


def build_tile_sprites() -> List[SpriteDefinition]:
    """Build environment tile sprites: road, shrine, park."""
    tiles = []

    for name, generator in [
        ("road_tile", _road_tile_pixels),
        ("shrine_tile", _shrine_tile_pixels),
        ("park_tile", _park_tile_pixels),
    ]:
        pixels = generator()
        frame = SpriteFrame(pixels=pixels, duration_ms=0)  # static
        sprite = SpriteDefinition(
            name=name,
            category=SpriteCategory.ENVIRONMENT,
            width=32,
            height=32,
            palette_mode=PaletteMode.MATERIAL,
            z_order=0,
            origin_x=0,
            origin_y=0,
        )
        sprite.add_animation(AnimationSequence(
            name="static",
            frames=[frame],
            playback=AnimationPlayback.LOOP,
        ))
        tiles.append(sprite)

    return tiles


# ---------------------------------------------------------------------------
# Pixel manipulation helpers
# ---------------------------------------------------------------------------

def _aoi_walk_variant(base: PixelGrid) -> PixelGrid:
    """Create a walk-cycle variant by shifting leg rows slightly.

    Shifts the lower body by 1 pixel to simulate a step.
    """
    result = [row[:] for row in base]
    # Shift leg rows (49-54) right by 1 pixel
    for y in range(49, min(55, len(result))):
        row = result[y]
        result[y] = [0] + row[:-1]
    return result


def _mirror_horizontal(grid: PixelGrid) -> PixelGrid:
    """Flip a pixel grid horizontally."""
    return [row[::-1] for row in grid]


def _kodama_breathe_variant(base: PixelGrid) -> PixelGrid:
    """Create a breathing variant by slightly expanding the mid-body."""
    result = [row[:] for row in base]
    # Expand rows 16-21 by replacing edge transparent with ghost_dim
    Gd = 6
    for y in range(16, min(22, len(result))):
        row = result[y]
        if len(row) >= 32:
            if row[6] == 0:
                row[6] = Gd
            if row[25] == 0:
                row[25] = Gd
    return result


# ---------------------------------------------------------------------------
# Rendering utilities
# ---------------------------------------------------------------------------

@dataclass
class RenderTarget:
    """A flat RGBA pixel buffer for compositing.

    ``buffer[y][x]`` is a ``Color``.  Initialised to fully transparent.
    """
    width: int
    height: int
    buffer: List[List[Color]] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if not self.buffer:
            transparent = Color(0, 0, 0, 0)
            self.buffer = [
                [transparent for _ in range(self.width)]
                for _ in range(self.height)
            ]

    def set_pixel(self, x: int, y: int, color: Color) -> None:
        """Set a pixel, ignoring out-of-bounds coordinates."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.buffer[y][x] = color

    def get_pixel(self, x: int, y: int) -> Color:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.buffer[y][x]
        return Color(0, 0, 0, 0)

    def blend_pixel(self, x: int, y: int, src: Color) -> None:
        """Alpha-composite *src* over the existing pixel at (x, y)."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        if src.a == 0:
            return
        if src.a == 255:
            self.buffer[y][x] = src
            return
        dst = self.buffer[y][x]
        sa = src.a / 255.0
        da = dst.a / 255.0
        out_a = sa + da * (1 - sa)
        if out_a == 0:
            return
        out_r = round((src.r * sa + dst.r * da * (1 - sa)) / out_a)
        out_g = round((src.g * sa + dst.g * da * (1 - sa)) / out_a)
        out_b = round((src.b * sa + dst.b * da * (1 - sa)) / out_a)
        self.buffer[y][x] = Color(out_r, out_g, out_b, round(out_a * 255))

    def to_flat_rgba(self) -> bytes:
        """Export as a flat RGBA byte string (row-major, top-to-bottom)."""
        data = bytearray()
        for row in self.buffer:
            for c in row:
                data.extend([c.r, c.g, c.b, c.a])
        return bytes(data)


def render_sprite_frame(
    frame: SpriteFrame,
    palette: Palette,
    target: RenderTarget,
    dest_x: int,
    dest_y: int,
    alpha_mod: int = 255,
    flip_h: bool = False,
    flip_v: bool = False,
) -> None:
    """Draw a ``SpriteFrame`` onto a ``RenderTarget`` using a palette.

    Respects the frame's per-pixel palette indices, applies alpha
    modulation, and handles horizontal/vertical flipping.
    """
    for py in range(frame.height):
        for px in range(frame.width):
            idx = frame.get_pixel(px, py)
            if idx == 0:
                continue  # transparent
            color = palette.color_at(idx)
            if alpha_mod < 255:
                color = color.with_alpha(round(color.a * alpha_mod / 255))
            draw_x = px if not flip_h else (frame.width - 1 - px)
            draw_y = py if not flip_v else (frame.height - 1 - py)
            target.blend_pixel(
                dest_x + draw_x + frame.offset_x,
                dest_y + draw_y + frame.offset_y,
                color,
            )


def composite_layers(
    material_target: RenderTarget,
    spirit_target: RenderTarget,
    permeability: float,
    output: Optional[RenderTarget] = None,
) -> RenderTarget:
    """Composite Material and Spirit layers into a final image.

    At *permeability* = 0 only the material layer is visible.
    At 1.0 both layers are fully overlaid in a shimmering double-exposure.
    Between 0.8 and 1.0 additional shimmer is applied (slight alpha
    oscillation per pixel row to create scan-line shimmer).

    Args:
        material_target: The rendered Material layer.
        spirit_target: The rendered Spirit layer.
        permeability: Veil permeability [0.0, 1.0].
        output: Optional pre-allocated output buffer.

    Returns:
        Composited ``RenderTarget``.
    """
    w = material_target.width
    h = material_target.height
    if output is None:
        output = RenderTarget(width=w, height=h)

    spirit_alpha_base = max(0.0, min(1.0, permeability))
    shimmer = permeability > 0.8

    for y in range(h):
        # Scan-line shimmer: rows alternate slightly in alpha at high permeability
        row_alpha_mod = 1.0
        if shimmer:
            row_alpha_mod = 0.85 + 0.15 * ((y % 3) / 2.0)

        for x in range(w):
            mat = material_target.get_pixel(x, y)
            spr = spirit_target.get_pixel(x, y)

            # Modulate spirit alpha by permeability and shimmer
            effective_spirit_alpha = round(
                spr.a * spirit_alpha_base * row_alpha_mod
            )
            spr_mod = Color(spr.r, spr.g, spr.b, max(0, min(255, effective_spirit_alpha)))

            # Start with material, blend spirit on top
            output.set_pixel(x, y, mat)
            output.blend_pixel(x, y, spr_mod)

    return output


# ---------------------------------------------------------------------------
# Convenience: build all built-in sprites
# ---------------------------------------------------------------------------

def build_all_builtin_sprites() -> Dict[str, SpriteDefinition]:
    """Create and return all hand-crafted sprite definitions.

    Returns a dict keyed by sprite name.
    """
    sprites: Dict[str, SpriteDefinition] = {}

    aoi = build_aoi_sprite()
    sprites[aoi.name] = aoi

    kodama = build_kodama_sprite()
    sprites[kodama.name] = kodama

    for tile in build_tile_sprites():
        sprites[tile.name] = tile

    return sprites
