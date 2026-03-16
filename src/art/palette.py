"""Ma no Kuni (間の国) - Color Palette System.

Manages dual-layer palettes for the Material and Spirit visual realms,
including seasonal shifts, time-of-day transitions, and permeability blending.

Each palette is a named collection of semantically-labelled hex colors.
Transition palettes interpolate between Material and Spirit for moments
when the veil between worlds thins.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple


class PaletteMode(Enum):
    """Which visual realm a palette targets."""
    MATERIAL = auto()
    SPIRIT = auto()
    BOTH = auto()


class Season(Enum):
    """Seasonal variants that shift the entire color language."""
    SPRING = auto()   # Cherry blossoms, renewal
    SUMMER = auto()   # Heat haze, cicadas
    AUTUMN = auto()   # Maple red, golden hour
    WINTER = auto()   # Snow blue, bare branches


class TimeOfDay(Enum):
    """Time-of-day lighting conditions."""
    DAWN = auto()
    MORNING = auto()
    MIDDAY = auto()
    AFTERNOON = auto()
    DUSK = auto()
    NIGHT = auto()
    WITCHING_HOUR = auto()  # 2-4 AM, highest natural permeability


@dataclass(frozen=True)
class Color:
    """An RGBA color with semantic meaning.

    Stored as 0-255 integer channels. The ``hex`` class method parses
    standard ``#RRGGBB`` or ``#RRGGBBAA`` strings.
    """
    r: int
    g: int
    b: int
    a: int = 255

    @classmethod
    def hex(cls, value: str) -> Color:
        """Create a Color from a hex string like ``#FF00AA`` or ``#FF00AA80``."""
        value = value.lstrip("#")
        if len(value) == 6:
            return cls(
                r=int(value[0:2], 16),
                g=int(value[2:4], 16),
                b=int(value[4:6], 16),
            )
        if len(value) == 8:
            return cls(
                r=int(value[0:2], 16),
                g=int(value[2:4], 16),
                b=int(value[4:6], 16),
                a=int(value[6:8], 16),
            )
        raise ValueError(f"Invalid hex color: #{value}")

    def to_hex(self) -> str:
        """Return ``#RRGGBB`` (or ``#RRGGBBAA`` when alpha is not 255)."""
        if self.a == 255:
            return f"#{self.r:02X}{self.g:02X}{self.b:02X}"
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}{self.a:02X}"

    def to_tuple(self) -> Tuple[int, int, int, int]:
        return (self.r, self.g, self.b, self.a)

    def lerp(self, other: Color, t: float) -> Color:
        """Linearly interpolate toward *other* by factor *t* in [0, 1]."""
        t = max(0.0, min(1.0, t))
        return Color(
            r=round(self.r + (other.r - self.r) * t),
            g=round(self.g + (other.g - self.g) * t),
            b=round(self.b + (other.b - self.b) * t),
            a=round(self.a + (other.a - self.a) * t),
        )

    def with_alpha(self, alpha: int) -> Color:
        """Return a copy with a different alpha value."""
        return Color(self.r, self.g, self.b, max(0, min(255, alpha)))


# ---------------------------------------------------------------------------
# Semantic color name -> hex mapping for each palette
# ---------------------------------------------------------------------------

@dataclass
class Palette:
    """A named collection of semantically-labelled colors.

    Attributes:
        name: Human-readable palette identifier.
        mode: Whether this palette is for Material, Spirit, or Both layers.
        colors: Mapping of semantic name to ``Color``.
        index_order: Ordered list of semantic names used when converting
            pixel data stored as palette indices.
    """
    name: str
    mode: PaletteMode
    colors: Dict[str, Color] = field(default_factory=dict)
    index_order: List[str] = field(default_factory=list)

    def __getitem__(self, key: str) -> Color:
        return self.colors[key]

    def __contains__(self, key: str) -> bool:
        return key in self.colors

    def index_of(self, name: str) -> int:
        """Return the palette index for a semantic color name."""
        return self.index_order.index(name)

    def color_at(self, index: int) -> Color:
        """Return the ``Color`` at a given palette index."""
        return self.colors[self.index_order[index]]

    def add(self, name: str, hex_value: str) -> None:
        """Add a color by semantic name and hex string."""
        self.colors[name] = Color.hex(hex_value)
        if name not in self.index_order:
            self.index_order.append(name)

    def to_hex_list(self) -> List[str]:
        """Return all colors as a list of hex strings in index order."""
        return [self.colors[n].to_hex() for n in self.index_order]


# ---------------------------------------------------------------------------
# Material Palette  -  Tokyo urban warmth
# ---------------------------------------------------------------------------

def create_material_palette() -> Palette:
    """Build the Material realm base palette.

    Grounded in the textures of modern Tokyo: concrete, warm lamplight,
    neon signage, aged wood, and distant sky.
    """
    p = Palette(name="material_base", mode=PaletteMode.MATERIAL)

    # Transparency / empty
    p.add("transparent", "#00000000")

    # Concrete & asphalt
    p.add("concrete_dark", "#3B3B3B")
    p.add("concrete_mid", "#6B6B6B")
    p.add("concrete_light", "#9E9E9E")
    p.add("asphalt", "#2C2C34")

    # Warm lamplight
    p.add("lamp_warm", "#FFD07A")
    p.add("lamp_hot", "#FFF4D6")
    p.add("lamp_dim", "#C49A3C")

    # Neon signage
    p.add("neon_pink", "#FF2D7C")
    p.add("neon_green", "#39FF14")
    p.add("neon_blue", "#00D4FF")
    p.add("neon_orange", "#FF6B2C")

    # Natural wood
    p.add("wood_dark", "#5C3A1E")
    p.add("wood_mid", "#8B5E3C")
    p.add("wood_light", "#C4956A")
    p.add("wood_weathered", "#A09080")

    # Sky
    p.add("sky_day", "#87CEEB")
    p.add("sky_sunset", "#FF7F50")
    p.add("sky_night", "#1A1A2E")

    # Foliage
    p.add("leaf_green", "#4A7C59")
    p.add("leaf_dark", "#2D5A3D")
    p.add("moss", "#6B8E5A")

    # Skin tones (anime-adjacent pixel art)
    p.add("skin_light", "#FFE0BD")
    p.add("skin_mid", "#F5C6A0")
    p.add("skin_shadow", "#D4A47A")

    # Cloth & accents
    p.add("cloth_white", "#F0EDE8")
    p.add("cloth_red", "#C0392B")
    p.add("cloth_indigo", "#3A4078")
    p.add("cloth_black", "#1C1C24")

    # Water
    p.add("water_surface", "#5B9BD5")
    p.add("water_deep", "#2E5984")

    # Accents
    p.add("rust", "#B7410E")
    p.add("tile_white", "#E8E4DF")
    p.add("tile_blue", "#4A6FA5")

    # Pure utility
    p.add("black", "#000000")
    p.add("white", "#FFFFFF")

    return p


# ---------------------------------------------------------------------------
# Spirit Palette  -  Ethereal, luminous, otherworldly
# ---------------------------------------------------------------------------

def create_spirit_palette() -> Palette:
    """Build the Spirit realm base palette.

    Cool, translucent, and luminous. Everything shimmers with an inner
    light; edges dissolve into soft radiance.
    """
    p = Palette(name="spirit_base", mode=PaletteMode.SPIRIT)

    # Transparency / empty
    p.add("transparent", "#00000000")

    # Core ethereal tones
    p.add("deep_indigo", "#1B0A3C")
    p.add("indigo_mid", "#2E1A5E")
    p.add("spirit_blue", "#4A3AFF")
    p.add("spirit_blue_light", "#7B6FFF")

    # Ghost white
    p.add("ghost_white", "#E8E0F0")
    p.add("ghost_dim", "#B8B0C8")
    p.add("ghost_bright", "#FFFFFF")

    # Fox-fire green (kitsune-bi)
    p.add("foxfire_green", "#00FF88")
    p.add("foxfire_dim", "#00B860")
    p.add("foxfire_bright", "#80FFD0")

    # Memory gold (fragments of the living world)
    p.add("memory_gold", "#FFD700")
    p.add("memory_warm", "#FFE680")
    p.add("memory_faded", "#C8A84080")

    # Void black
    p.add("void_black", "#050010")
    p.add("void_deep", "#0A0020")

    # Cherry blossom pink (sakura - spirit of transience)
    p.add("sakura_pink", "#FFB7C5")
    p.add("sakura_deep", "#FF69B4")
    p.add("sakura_pale", "#FFE4ED")

    # Corruption (when the balance breaks)
    p.add("corruption_black", "#0D0D0D")
    p.add("corruption_purple", "#4A0040")
    p.add("corruption_iridescent", "#2A1A3AE0")
    p.add("corruption_oil", "#1A0A2AC0")

    # Spirit auras
    p.add("aura_calm", "#88CCFF80")
    p.add("aura_alert", "#FF444480")
    p.add("aura_ancient", "#FFD70060")

    # Veil (the boundary itself)
    p.add("veil_shimmer", "#FFFFFF40")
    p.add("veil_tear", "#FF00FF80")
    p.add("veil_stable", "#8080FF30")

    # Ma energy glow
    p.add("ma_glow_low", "#6644AA60")
    p.add("ma_glow_mid", "#8866CCAA")
    p.add("ma_glow_high", "#AA88EEDD")
    p.add("ma_glow_critical", "#CC99FFFF")

    return p


# ---------------------------------------------------------------------------
# Transition & Seasonal Palettes
# ---------------------------------------------------------------------------

def create_dawn_transition_palette() -> Palette:
    """Palette for dawn - the world between night-spirit and day-material."""
    p = Palette(name="transition_dawn", mode=PaletteMode.BOTH)

    p.add("sky_gradient_top", "#2E1A5E")
    p.add("sky_gradient_mid", "#FF8C69")
    p.add("sky_gradient_low", "#FFD07A")
    p.add("mist", "#C8C8D880")
    p.add("first_light", "#FFF8E0")
    p.add("shadow_receding", "#1A1A2E80")
    p.add("dew_sparkle", "#FFFFFF")
    p.add("spirit_fade", "#8866CC60")

    return p


def create_dusk_transition_palette() -> Palette:
    """Palette for dusk - spirits begin to stir, material grows soft."""
    p = Palette(name="transition_dusk", mode=PaletteMode.BOTH)

    p.add("sky_gradient_top", "#1A1A2E")
    p.add("sky_gradient_mid", "#7B2D8E")
    p.add("sky_gradient_low", "#FF7F50")
    p.add("long_shadow", "#1C1C2480")
    p.add("last_light", "#FFD700")
    p.add("spirit_emerge", "#4A3AFFAA")
    p.add("lamp_first", "#FFD07A")
    p.add("neon_waking", "#FF2D7C80")

    return p


def create_high_permeability_palette() -> Palette:
    """Palette for moments when both realms fully overlap.

    Everything shimmers with a double-exposed quality. Material colours
    gain translucent spirit overlays; spirit colours become almost solid.
    """
    p = Palette(name="transition_high_permeability", mode=PaletteMode.BOTH)

    p.add("overlap_white", "#FFFFFFDD")
    p.add("overlap_indigo", "#4A3AFFCC")
    p.add("overlap_gold", "#FFD700CC")
    p.add("overlap_shimmer", "#FF69B4AA")
    p.add("double_exposure_light", "#E8E0F0BB")
    p.add("double_exposure_dark", "#1B0A3CBB")
    p.add("resonance_pulse", "#00FF88AA")
    p.add("veil_dissolve", "#FFFFFF20")

    return p


# ---------------------------------------------------------------------------
# Seasonal colour shifts
# ---------------------------------------------------------------------------

@dataclass
class SeasonalShift:
    """Defines how a base palette is tinted per season.

    ``hue_shift`` is in degrees, ``saturation_scale`` and
    ``brightness_scale`` are multiplicative (1.0 = unchanged).
    Additional ``overlay_colors`` are blended at low opacity.
    """
    season: Season
    hue_shift: float = 0.0
    saturation_scale: float = 1.0
    brightness_scale: float = 1.0
    overlay_colors: Dict[str, Color] = field(default_factory=dict)


SEASONAL_SHIFTS: Dict[Season, SeasonalShift] = {
    Season.SPRING: SeasonalShift(
        season=Season.SPRING,
        hue_shift=-5.0,
        saturation_scale=1.1,
        brightness_scale=1.05,
        overlay_colors={
            "sakura_drift": Color.hex("#FFB7C530"),
            "fresh_green": Color.hex("#90EE9020"),
        },
    ),
    Season.SUMMER: SeasonalShift(
        season=Season.SUMMER,
        hue_shift=5.0,
        saturation_scale=1.15,
        brightness_scale=1.1,
        overlay_colors={
            "heat_haze": Color.hex("#FFD07A18"),
            "cicada_gold": Color.hex("#FFD70010"),
        },
    ),
    Season.AUTUMN: SeasonalShift(
        season=Season.AUTUMN,
        hue_shift=15.0,
        saturation_scale=1.2,
        brightness_scale=0.95,
        overlay_colors={
            "maple_red": Color.hex("#C0392B30"),
            "golden_hour": Color.hex("#FFD07A20"),
        },
    ),
    Season.WINTER: SeasonalShift(
        season=Season.WINTER,
        hue_shift=-10.0,
        saturation_scale=0.8,
        brightness_scale=0.9,
        overlay_colors={
            "snow_blue": Color.hex("#A8C8E820"),
            "bare_branch": Color.hex("#8B7D6B18"),
        },
    ),
}


# ---------------------------------------------------------------------------
# Palette Manager  -  runtime access
# ---------------------------------------------------------------------------

def _rgb_to_hsv(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convert 0-255 RGB to (H 0-360, S 0-1, V 0-1)."""
    r_f, g_f, b_f = r / 255.0, g / 255.0, b / 255.0
    mx = max(r_f, g_f, b_f)
    mn = min(r_f, g_f, b_f)
    diff = mx - mn
    if diff == 0:
        h = 0.0
    elif mx == r_f:
        h = (60 * ((g_f - b_f) / diff) + 360) % 360
    elif mx == g_f:
        h = (60 * ((b_f - r_f) / diff) + 120) % 360
    else:
        h = (60 * ((r_f - g_f) / diff) + 240) % 360
    s = 0.0 if mx == 0 else diff / mx
    return h, s, mx


def _hsv_to_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
    """Convert (H 0-360, S 0-1, V 0-1) back to 0-255 RGB."""
    h = h % 360
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    if h < 60:
        r_f, g_f, b_f = c, x, 0.0
    elif h < 120:
        r_f, g_f, b_f = x, c, 0.0
    elif h < 180:
        r_f, g_f, b_f = 0.0, c, x
    elif h < 240:
        r_f, g_f, b_f = 0.0, x, c
    elif h < 300:
        r_f, g_f, b_f = x, 0.0, c
    else:
        r_f, g_f, b_f = c, 0.0, x
    return (
        round((r_f + m) * 255),
        round((g_f + m) * 255),
        round((b_f + m) * 255),
    )


class PaletteManager:
    """Central registry for all palettes with seasonal/temporal blending.

    Usage::

        pm = PaletteManager()
        material_color = pm.material["lamp_warm"]
        shifted = pm.get_seasonal_color(pm.material, "leaf_green", Season.AUTUMN)
        blended = pm.blend_realms("lamp_warm", "spirit_blue", permeability=0.6)
    """

    def __init__(self) -> None:
        self.material: Palette = create_material_palette()
        self.spirit: Palette = create_spirit_palette()
        self.dawn: Palette = create_dawn_transition_palette()
        self.dusk: Palette = create_dusk_transition_palette()
        self.high_permeability: Palette = create_high_permeability_palette()

        self._palettes: Dict[str, Palette] = {
            self.material.name: self.material,
            self.spirit.name: self.spirit,
            self.dawn.name: self.dawn,
            self.dusk.name: self.dusk,
            self.high_permeability.name: self.high_permeability,
        }

    # -- lookup ---------------------------------------------------------------

    def get_palette(self, name: str) -> Optional[Palette]:
        """Retrieve a palette by its registered name."""
        return self._palettes.get(name)

    def register(self, palette: Palette) -> None:
        """Add or overwrite a palette in the registry."""
        self._palettes[palette.name] = palette

    # -- seasonal shift -------------------------------------------------------

    def get_seasonal_color(
        self,
        palette: Palette,
        color_name: str,
        season: Season,
    ) -> Color:
        """Apply a seasonal hue/saturation/brightness shift to a color."""
        base = palette[color_name]
        shift = SEASONAL_SHIFTS[season]

        h, s, v = _rgb_to_hsv(base.r, base.g, base.b)
        h = (h + shift.hue_shift) % 360
        s = max(0.0, min(1.0, s * shift.saturation_scale))
        v = max(0.0, min(1.0, v * shift.brightness_scale))
        r, g, b = _hsv_to_rgb(h, s, v)
        return Color(r, g, b, base.a)

    # -- realm blending -------------------------------------------------------

    def blend_realms(
        self,
        material_name: str,
        spirit_name: str,
        permeability: float,
    ) -> Color:
        """Blend a Material and Spirit color based on veil permeability.

        *permeability* ranges from 0.0 (fully material) to 1.0 (fully spirit).
        Values above 0.8 trigger the shimmering double-exposure aesthetic.
        """
        mat = self.material[material_name]
        spr = self.spirit[spirit_name]
        return mat.lerp(spr, permeability)

    def get_time_palette(self, time_of_day: TimeOfDay) -> Optional[Palette]:
        """Return the transition palette most appropriate for a time of day."""
        mapping: Dict[TimeOfDay, Optional[Palette]] = {
            TimeOfDay.DAWN: self.dawn,
            TimeOfDay.DUSK: self.dusk,
            TimeOfDay.WITCHING_HOUR: self.high_permeability,
        }
        return mapping.get(time_of_day)

    # -- utility --------------------------------------------------------------

    def palette_for_mode(self, mode: PaletteMode) -> Palette:
        """Return the base palette that matches a ``PaletteMode``."""
        if mode is PaletteMode.MATERIAL:
            return self.material
        if mode is PaletteMode.SPIRIT:
            return self.spirit
        return self.material  # BOTH defaults to material base

    def all_palettes(self) -> List[Palette]:
        """Return every registered palette."""
        return list(self._palettes.values())
