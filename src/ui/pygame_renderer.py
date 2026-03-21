"""Ma no Kuni (間の国) - Pygame Rendering Backend.

The actual drawing code that paints both worlds onto one screen.
Converts palette-indexed pixel art into pygame surfaces, composites
Material and Spirit layers with permeability blending, and renders
all UI elements, effects, and transitions using real pygame calls.
"""

from __future__ import annotations

import math
import time
from typing import Dict, List, Optional, Sequence, Tuple

import pygame

from src.art.palette import (
    Color,
    Palette,
    PaletteManager,
    PaletteMode,
    Season,
    TimeOfDay,
)
from src.art.sprites import (
    AnimationPlayback,
    BreathingParams,
    Direction,
    PixelGrid,
    SpriteCategory,
    SpriteDefinition,
    SpriteFrame,
    SpriteInstance,
    ma_glow_alpha,
    ma_glow_pulse_period_ms,
)
from src.art.pixel_art import (
    build_all_builtin_sprites,
    build_tile_sprites,
)
from src.art.effects import (
    EffectManager,
    EffectState,
    MaGlowEffect,
    SpiritShimmerEffect,
)
from src.ui.renderer import (
    Camera,
    MaVisualEffect,
    RenderLayer,
    Renderer,
    SpiritVisionEffect,
    TransitionEffect,
)
from src.engine.config import DISPLAY, GAMEPLAY


# ---------------------------------------------------------------------------
# Helper functions (module-level)
# ---------------------------------------------------------------------------

def palette_to_surface(pixel_data: PixelGrid, palette: Palette) -> pygame.Surface:
    """Convert a 2-D palette-index array into a 32-bit RGBA pygame.Surface.

    Args:
        pixel_data: Row-major list of lists, where each int is a palette index.
            Index 0 is treated as fully transparent.
        palette: The ``Palette`` to resolve indices into ``Color`` objects.

    Returns:
        A pygame.Surface with per-pixel alpha matching the source data.
    """
    if not pixel_data or not pixel_data[0]:
        return pygame.Surface((1, 1), pygame.SRCALPHA)

    h = len(pixel_data)
    w = len(pixel_data[0])
    surface = pygame.Surface((w, h), pygame.SRCALPHA)

    for y in range(h):
        row = pixel_data[y]
        for x in range(min(w, len(row))):
            idx = row[x]
            if idx == 0:
                continue  # transparent - surface is already zeroed
            color = palette.color_at(idx)
            surface.set_at((x, y), (color.r, color.g, color.b, color.a))

    return surface


def create_tile_cache(
    tile_sprites: List[SpriteDefinition],
    palette: Palette,
) -> Dict[str, pygame.Surface]:
    """Pre-render all tile types as pygame surfaces for fast blitting.

    Each tile sprite is expected to have a single-frame ``"static"``
    animation.  The resulting dict maps tile name to surface.

    Args:
        tile_sprites: List of ``SpriteDefinition`` objects with
            ``SpriteCategory.ENVIRONMENT``.
        palette: The material palette used to resolve tile colours.

    Returns:
        Dict mapping tile name (e.g. ``"road_tile"``) to pre-rendered
        ``pygame.Surface``.
    """
    cache: Dict[str, pygame.Surface] = {}
    for tile_def in tile_sprites:
        if "static" in tile_def.animations:
            frame = tile_def.animations["static"].frames[0]
            cache[tile_def.name] = palette_to_surface(frame.pixels, palette)
    return cache


def _find_cjk_font() -> Optional[str]:
    """Find a system font that supports CJK (Japanese/Chinese/Korean) characters."""
    candidates = [
        "yugothic", "yu gothic", "msgothic", "ms gothic",
        "meiryo", "hiragino sans", "hiragino kaku gothic pro",
        "noto sans cjk", "noto sans jp", "arial unicode ms",
    ]
    available = pygame.font.get_fonts()
    for candidate in candidates:
        normalized = candidate.replace(" ", "").lower()
        for avail in available:
            if normalized in avail.lower():
                return avail
    return None


_cjk_font_name: Optional[str] = None
_cjk_font_searched: bool = False


def draw_text(
    surface: pygame.Surface,
    text: str,
    x: int,
    y: int,
    color: Tuple[int, int, int, int] = (255, 255, 255, 255),
    size: int = 16,
    font_name: Optional[str] = None,
    antialias: bool = True,
) -> pygame.Rect:
    """Render text onto a surface using pygame's built-in font system.

    Args:
        surface: Target surface to draw on.
        text: The string to render.
        x: Left edge in pixels.
        y: Top edge in pixels.
        color: RGBA tuple.  Alpha is applied via surface blending.
        size: Font size in points.
        font_name: Optional system font name; ``None`` uses the default.
        antialias: Whether to antialias the text.

    Returns:
        The bounding ``pygame.Rect`` of the rendered text.
    """
    global _cjk_font_name, _cjk_font_searched
    if font_name is None and not _cjk_font_searched:
        _cjk_font_name = _find_cjk_font()
        _cjk_font_searched = True
    effective_font = font_name if font_name is not None else _cjk_font_name
    font = pygame.font.SysFont(effective_font, size)
    rgb = color[:3]
    alpha = color[3] if len(color) > 3 else 255
    text_surface = font.render(text, antialias, rgb)
    if alpha < 255:
        text_surface.set_alpha(alpha)
    rect = surface.blit(text_surface, (x, y))
    return rect


def create_gradient_surface(
    w: int,
    h: int,
    color1: Tuple[int, int, int, int],
    color2: Tuple[int, int, int, int],
    vertical: bool = True,
) -> pygame.Surface:
    """Create a linear gradient surface between two RGBA colors.

    Args:
        w: Width in pixels.
        h: Height in pixels.
        color1: Start color (top or left).
        color2: End color (bottom or right).
        vertical: ``True`` for top-to-bottom, ``False`` for left-to-right.

    Returns:
        A new ``pygame.Surface`` with per-pixel alpha.
    """
    surface = pygame.Surface((w, h), pygame.SRCALPHA)
    steps = h if vertical else w

    for i in range(steps):
        t = i / max(1, steps - 1)
        r = int(color1[0] + (color2[0] - color1[0]) * t)
        g = int(color1[1] + (color2[1] - color1[1]) * t)
        b = int(color1[2] + (color2[2] - color1[2]) * t)
        a = int(color1[3] + (color2[3] - color1[3]) * t)
        if vertical:
            pygame.draw.line(surface, (r, g, b, a), (0, i), (w - 1, i))
        else:
            pygame.draw.line(surface, (r, g, b, a), (i, 0), (i, h - 1))

    return surface


# ---------------------------------------------------------------------------
# Main Pygame Renderer
# ---------------------------------------------------------------------------

class PygameRenderer:
    """Production pygame rendering backend for Ma no Kuni.

    Owns the main screen surface and all cached assets.  Each frame it
    receives a ``game_state`` dict describing the world and draws
    everything: tile map, sprites, spirit overlay, HUD, effects, and
    transitions.

    Args:
        screen: The primary ``pygame.Surface`` returned by
            ``pygame.display.set_mode``.
        camera: A ``Camera`` instance from the renderer module.
    """

    # -- constants -----------------------------------------------------------
    TILE_SIZE: int = DISPLAY.TILE_SIZE
    SCREEN_W: int = DISPLAY.SCREEN_WIDTH
    SCREEN_H: int = DISPLAY.SCREEN_HEIGHT
    FPS: int = DISPLAY.FPS

    # HUD layout
    _HUD_BAR_X: int = 10
    _HUD_BAR_Y: int = 10
    _HUD_BAR_W: int = 160
    _HUD_BAR_H: int = 14
    _HUD_BAR_GAP: int = 6
    _HUD_FONT_SIZE: int = 12

    # Dialogue box layout
    _DLG_MARGIN: int = 24
    _DLG_HEIGHT: int = 120
    _DLG_PADDING: int = 16
    _DLG_FONT_SIZE: int = 18
    _DLG_NAME_FONT_SIZE: int = 14

    # Toast
    _TOAST_FONT_SIZE: int = 14
    _TOAST_PADDING: int = 8
    _TOAST_Y_OFFSET: int = 60

    # Colors (RGBA tuples for pygame)
    _CLR_BG: Tuple[int, int, int] = (20, 20, 30)
    _CLR_WHITE: Tuple[int, int, int, int] = (255, 255, 255, 255)
    _CLR_BLACK: Tuple[int, int, int, int] = (0, 0, 0, 255)
    _CLR_HP: Tuple[int, int, int] = (192, 57, 43)
    _CLR_SP: Tuple[int, int, int] = (74, 63, 255)
    _CLR_MA: Tuple[int, int, int] = (136, 102, 204)
    _CLR_BAR_BG: Tuple[int, int, int] = (40, 40, 50)
    _CLR_DLG_BG: Tuple[int, int, int, int] = (15, 10, 25, 220)
    _CLR_DLG_BORDER: Tuple[int, int, int, int] = (120, 100, 160, 255)

    def __init__(self, screen: pygame.Surface, camera: Camera) -> None:
        self.screen: pygame.Surface = screen
        self.camera: Camera = camera

        # Palette system
        self._palette_mgr: PaletteManager = PaletteManager()
        self._material_palette: Palette = self._palette_mgr.material
        self._spirit_palette: Palette = self._palette_mgr.spirit

        # Off-screen layers
        self._material_layer: pygame.Surface = pygame.Surface(
            (self.SCREEN_W, self.SCREEN_H), pygame.SRCALPHA,
        )
        self._spirit_layer: pygame.Surface = pygame.Surface(
            (self.SCREEN_W, self.SCREEN_H), pygame.SRCALPHA,
        )
        self._ui_layer: pygame.Surface = pygame.Surface(
            (self.SCREEN_W, self.SCREEN_H), pygame.SRCALPHA,
        )
        self._effect_layer: pygame.Surface = pygame.Surface(
            (self.SCREEN_W, self.SCREEN_H), pygame.SRCALPHA,
        )

        # Tile cache: name -> pygame.Surface
        self._tile_cache: Dict[str, pygame.Surface] = {}
        # Sprite surface cache: (sprite_name, anim_name, frame_index, flip_h) -> Surface
        self._sprite_cache: Dict[Tuple[str, str, int, bool], pygame.Surface] = {}

        # Transition surfaces
        self._transition_overlay: pygame.Surface = pygame.Surface(
            (self.SCREEN_W, self.SCREEN_H), pygame.SRCALPHA,
        )

        # Vignette (pre-rendered once, then just blitted)
        self._vignette_surface: Optional[pygame.Surface] = None

        # Toast queue: list of (text, expire_time_ms)
        self._toasts: List[Tuple[str, float]] = []

        # Frame timing
        self._elapsed_ms: float = 0.0

        # Build caches on init
        self._build_initial_caches()

    # -- initialisation ------------------------------------------------------

    def _build_initial_caches(self) -> None:
        """Pre-render tile surfaces and the vignette overlay."""
        from src.art.pixel_art import build_tile_sprites

        tile_defs = build_tile_sprites()
        self._tile_cache = create_tile_cache(tile_defs, self._material_palette)

        # Also cache spirit-palette versions for the spirit layer
        for tile_def in tile_defs:
            if "static" in tile_def.animations:
                frame = tile_def.animations["static"].frames[0]
                spirit_name = tile_def.name + "_spirit"
                self._tile_cache[spirit_name] = palette_to_surface(
                    frame.pixels, self._spirit_palette,
                )

        self._vignette_surface = self._create_vignette()

    def _create_vignette(self) -> pygame.Surface:
        """Build a radial vignette overlay: dark corners, clear center."""
        surf = pygame.Surface((self.SCREEN_W, self.SCREEN_H), pygame.SRCALPHA)
        cx = self.SCREEN_W / 2.0
        cy = self.SCREEN_H / 2.0
        max_dist = math.sqrt(cx * cx + cy * cy)

        # Render in low-res then scale up for performance
        scale = 4
        small_w = self.SCREEN_W // scale
        small_h = self.SCREEN_H // scale
        small = pygame.Surface((small_w, small_h), pygame.SRCALPHA)
        s_cx = small_w / 2.0
        s_cy = small_h / 2.0
        s_max = math.sqrt(s_cx * s_cx + s_cy * s_cy)

        for y in range(small_h):
            for x in range(small_w):
                dx = x - s_cx
                dy = y - s_cy
                dist = math.sqrt(dx * dx + dy * dy)
                # Vignette starts at 60% of the way to the corner
                ratio = max(0.0, (dist / s_max - 0.6) / 0.4)
                ratio = min(1.0, ratio)
                alpha = int(180 * ratio * ratio)
                small.set_at((x, y), (0, 0, 0, alpha))

        pygame.transform.smoothscale(small, (self.SCREEN_W, self.SCREEN_H), surf)
        return surf

    # -- sprite surface caching ----------------------------------------------

    def _get_sprite_surface(
        self,
        sprite: SpriteInstance,
        palette: Palette,
    ) -> pygame.Surface:
        """Retrieve or create a cached surface for the current sprite frame.

        Caching is keyed by (sprite_name, animation_name, frame_index, flip_h)
        to avoid re-rendering identical pixel data every frame.
        """
        definition = sprite.definition
        anim_name = sprite.current_animation
        anim = definition.animations.get(anim_name)
        if anim is None:
            return pygame.Surface((1, 1), pygame.SRCALPHA)

        frame = sprite.current_frame()
        # Determine frame index for cache key
        try:
            frame_idx = anim.frames.index(frame)
        except ValueError:
            frame_idx = 0

        palette_key = palette.name
        cache_key = (definition.name, anim_name, frame_idx, sprite.flip_h, palette_key)

        if cache_key not in self._sprite_cache:
            surf = palette_to_surface(frame.pixels, palette)
            if sprite.flip_h:
                surf = pygame.transform.flip(surf, True, False)
            self._sprite_cache[cache_key] = surf

        base = self._sprite_cache[cache_key]

        # If flip state changed after caching for the non-flipped variant,
        # we may need the flipped version which is already keyed separately.
        return base

    def _get_flipped_sprite_surface(
        self,
        definition: SpriteDefinition,
        frame: SpriteFrame,
        anim_name: str,
        frame_idx: int,
        flip_h: bool,
        palette: Palette,
    ) -> pygame.Surface:
        """Low-level cache lookup with explicit parameters."""
        cache_key = (definition.name, anim_name, frame_idx, flip_h, palette.name)
        if cache_key not in self._sprite_cache:
            surf = palette_to_surface(frame.pixels, palette)
            if flip_h:
                surf = pygame.transform.flip(surf, True, False)
            self._sprite_cache[cache_key] = surf
        return self._sprite_cache[cache_key]

    # -----------------------------------------------------------------------
    # Main entry point
    # -----------------------------------------------------------------------

    def render_frame(self, game_state: dict) -> None:
        """Draw a complete frame based on the provided game state.

        Expected ``game_state`` keys:

        - ``"mode"``: ``"exploration"`` | ``"dialogue"`` | ``"combat"`` | ``"menu"``
        - ``"tile_map"``: 2-D list of tile name strings
        - ``"sprites"``: list of ``SpriteInstance`` objects
        - ``"player"``: ``SpriteInstance`` for Aoi
        - ``"permeability"``: float 0-1
        - ``"spirit_vision"``: bool
        - ``"ma"``: float (current ma level)
        - ``"ma_max"``: float
        - ``"hp"``: int, ``"hp_max"``: int
        - ``"sp"``: int, ``"sp_max"``: int
        - ``"time_of_day"``: ``TimeOfDay`` enum or string
        - ``"elapsed_ms"``: float (total game time for animations)
        - ``"dt_ms"``: float (delta time this frame)
        - ``"dialogue"``: optional dict with ``"speaker"``, ``"text"``, ``"portrait"``
        - ``"transition"``: optional dict with ``"type"``, ``"progress"``
        - ``"toasts"``: optional list of str
        - ``"menu"``: optional dict with menu data
        - ``"combat"``: optional dict with combat state
        - ``"effects"``: optional ``EffectManager``
        - ``"season"``: optional ``Season`` enum
        """
        dt_ms = game_state.get("dt_ms", 16.67)
        self._elapsed_ms += dt_ms

        # Clear everything
        self.screen.fill(self._CLR_BG)
        self._material_layer.fill((0, 0, 0, 0))
        self._spirit_layer.fill((0, 0, 0, 0))
        self._ui_layer.fill((0, 0, 0, 0))
        self._effect_layer.fill((0, 0, 0, 0))

        mode = game_state.get("mode", "exploration")

        if mode == "exploration":
            self.render_exploration(game_state)
        elif mode == "combat":
            self.render_combat(game_state)
        elif mode == "menu":
            self.render_menu(game_state)
        elif mode == "dialogue":
            # Exploration is visible behind dialogue
            self.render_exploration(game_state)

        # Spirit layer compositing
        permeability = game_state.get("permeability", 0.0)
        spirit_vision = game_state.get("spirit_vision", False)
        if spirit_vision or permeability > 0.0:
            self._composite_spirit_layer(permeability, spirit_vision)

        # Effects layer
        self._render_effects(game_state)

        # Ma visual overlay
        ma = game_state.get("ma", 0.0)
        ma_max = game_state.get("ma_max", GAMEPLAY.MA_MAX)
        if ma > 0:
            self._render_ma_glow(ma, ma_max)

        # Vignette (always on, intensity varies with ma)
        if self._vignette_surface is not None:
            vignette_alpha = int(80 + 120 * min(1.0, ma / ma_max) if ma_max > 0 else 80)
            vig_copy = self._vignette_surface.copy()
            vig_copy.set_alpha(vignette_alpha)
            self.screen.blit(vig_copy, (0, 0))

        # HUD
        self.render_hud(game_state)

        # Dialogue overlay
        dialogue = game_state.get("dialogue")
        if dialogue or mode == "dialogue":
            self.render_dialogue(game_state)

        # Toast notifications
        self._render_toasts(game_state)

        # Screen transitions (drawn last, on top of everything)
        transition = game_state.get("transition")
        if transition:
            self.render_transition(game_state)

    # -----------------------------------------------------------------------
    # Exploration rendering (map + characters + spirits)
    # -----------------------------------------------------------------------

    def render_exploration(self, game_state: dict) -> None:
        """Render the exploration mode: tile map, NPCs, spirits, player.

        Draws tiles with camera culling, then sprites sorted by y-position
        (painter's algorithm) onto the material layer.  Spirit-realm
        sprites are drawn onto the spirit layer instead.
        """
        tile_map = game_state.get("tile_map")
        sprites: List[SpriteInstance] = game_state.get("sprites", [])
        player: Optional[SpriteInstance] = game_state.get("player")
        permeability = game_state.get("permeability", 0.0)
        spirit_vision = game_state.get("spirit_vision", False)

        # -- tiles -----------------------------------------------------------
        if tile_map is not None:
            self._render_tile_map(tile_map, self._material_layer)
            if spirit_vision or permeability > 0.0:
                self._render_tile_map_spirit(tile_map, self._spirit_layer)

        # -- collect all drawable sprites ------------------------------------
        all_sprites: List[SpriteInstance] = list(sprites)
        if player is not None:
            all_sprites.append(player)

        # Sort by z_order then y for painter's algorithm
        all_sprites.sort(key=lambda s: (s.definition.z_order, s.y))

        for sprite in all_sprites:
            if not sprite.visible:
                continue

            is_spirit = sprite.definition.is_spirit
            target_layer = self._spirit_layer if is_spirit else self._material_layer
            palette = self._spirit_palette if is_spirit else self._material_palette

            self._render_sprite(sprite, target_layer, palette)

        # Blit material layer to screen
        self.screen.blit(self._material_layer, (0, 0))

    # -- tile map drawing ----------------------------------------------------

    def _render_tile_map(
        self,
        tile_map: List[List[str]],
        target: pygame.Surface,
    ) -> None:
        """Draw visible tiles from the map onto the target surface.

        Performs viewport culling: only tiles overlapping the camera's
        visible rectangle are drawn.
        """
        ts = self.TILE_SIZE
        cam_x = self.camera.x
        cam_y = self.camera.y
        zoom = self.camera.zoom

        # Determine visible tile range (with 1-tile margin for partial visibility)
        start_col = max(0, int(cam_x / ts) - 1)
        start_row = max(0, int(cam_y / ts) - 1)
        end_col = int((cam_x + self.SCREEN_W / zoom) / ts) + 2
        end_row = int((cam_y + self.SCREEN_H / zoom) / ts) + 2

        map_rows = len(tile_map)
        map_cols = len(tile_map[0]) if map_rows > 0 else 0

        end_row = min(end_row, map_rows)
        end_col = min(end_col, map_cols)

        shake_x, shake_y = self.camera.get_shake_offset()

        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                tile_name = tile_map[row][col]
                tile_surf = self._tile_cache.get(tile_name)
                if tile_surf is None:
                    continue

                world_x = col * ts
                world_y = row * ts
                screen_x = int((world_x - cam_x) * zoom + shake_x)
                screen_y = int((world_y - cam_y) * zoom + shake_y)

                if zoom != 1.0:
                    scaled_size = int(ts * zoom) + 1  # +1 to avoid seams
                    scaled = pygame.transform.scale(tile_surf, (scaled_size, scaled_size))
                    target.blit(scaled, (screen_x, screen_y))
                else:
                    target.blit(tile_surf, (screen_x, screen_y))

    def _render_tile_map_spirit(
        self,
        tile_map: List[List[str]],
        target: pygame.Surface,
    ) -> None:
        """Draw the spirit-palette version of visible tiles."""
        ts = self.TILE_SIZE
        cam_x = self.camera.x
        cam_y = self.camera.y
        zoom = self.camera.zoom

        start_col = max(0, int(cam_x / ts) - 1)
        start_row = max(0, int(cam_y / ts) - 1)
        end_col = int((cam_x + self.SCREEN_W / zoom) / ts) + 2
        end_row = int((cam_y + self.SCREEN_H / zoom) / ts) + 2

        map_rows = len(tile_map)
        map_cols = len(tile_map[0]) if map_rows > 0 else 0
        end_row = min(end_row, map_rows)
        end_col = min(end_col, map_cols)

        shake_x, shake_y = self.camera.get_shake_offset()

        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                tile_name = tile_map[row][col]
                spirit_name = tile_name + "_spirit"
                tile_surf = self._tile_cache.get(spirit_name)
                if tile_surf is None:
                    continue

                world_x = col * ts
                world_y = row * ts
                screen_x = int((world_x - cam_x) * zoom + shake_x)
                screen_y = int((world_y - cam_y) * zoom + shake_y)

                if zoom != 1.0:
                    scaled_size = int(ts * zoom) + 1
                    scaled = pygame.transform.scale(tile_surf, (scaled_size, scaled_size))
                    target.blit(scaled, (screen_x, screen_y))
                else:
                    target.blit(tile_surf, (screen_x, screen_y))

    # -- sprite drawing ------------------------------------------------------

    def _render_sprite(
        self,
        sprite: SpriteInstance,
        target: pygame.Surface,
        palette: Palette,
    ) -> None:
        """Draw a single sprite instance onto a layer surface.

        Handles animation frame lookup, directional flipping, breathing
        offset, and alpha blending.
        """
        definition = sprite.definition
        anim = definition.animations.get(sprite.current_animation)
        if anim is None:
            return

        frame = sprite.current_frame()

        # Determine frame index
        try:
            frame_idx = anim.frames.index(frame)
        except ValueError:
            frame_idx = 0

        # Flip based on direction or explicit flag
        flip_h = sprite.flip_h
        if sprite.direction == Direction.LEFT:
            flip_h = True
        elif sprite.direction == Direction.RIGHT:
            flip_h = False

        surf = self._get_flipped_sprite_surface(
            definition, frame, sprite.current_animation,
            frame_idx, flip_h, palette,
        )

        # Apply breathing alpha and override alpha
        alpha = sprite.breathing_alpha()
        if alpha < 255:
            surf = surf.copy()
            surf.set_alpha(alpha)

        # World-to-screen position
        render_x, render_y = sprite.render_position()
        screen_x, screen_y = self.camera.world_to_screen(render_x, render_y)

        # Per-frame offset
        screen_x += frame.offset_x
        screen_y += frame.offset_y

        # Zoom scaling
        if self.camera.zoom != 1.0:
            new_w = max(1, int(surf.get_width() * self.camera.zoom))
            new_h = max(1, int(surf.get_height() * self.camera.zoom))
            surf = pygame.transform.scale(surf, (new_w, new_h))

        target.blit(surf, (screen_x, screen_y))

    # -----------------------------------------------------------------------
    # Spirit layer compositing
    # -----------------------------------------------------------------------

    def _composite_spirit_layer(
        self,
        permeability: float,
        spirit_vision: bool,
    ) -> None:
        """Blend the spirit layer onto the screen based on permeability.

        When spirit vision is active the base opacity is boosted.
        The spirit shimmer effect (scanline bands) is applied at high
        permeability for the characteristic double-exposure look.
        """
        base_alpha = permeability
        if spirit_vision:
            base_alpha = max(base_alpha, 0.6)
        base_alpha = min(1.0, base_alpha)

        if base_alpha <= 0.0:
            return

        # Spirit shimmer: alternating scanline bands at high permeability
        if permeability > 0.5:
            self._apply_spirit_shimmer(self._spirit_layer, permeability)

        # Set overall spirit layer opacity
        spirit_alpha_byte = int(base_alpha * 255)
        self._spirit_layer.set_alpha(spirit_alpha_byte)
        self.screen.blit(self._spirit_layer, (0, 0))
        # Reset alpha for next frame
        self._spirit_layer.set_alpha(255)

    def _apply_spirit_shimmer(
        self,
        spirit_surface: pygame.Surface,
        permeability: float,
    ) -> None:
        """Apply scanline-like shimmer bands to the spirit layer.

        Horizontal bands scroll slowly downward, modulating the alpha
        of alternate rows to produce a subtle CRT / ethereal shimmer.
        """
        band_height = 3
        scroll = int(self._elapsed_ms / 80.0)  # Slow scroll
        intensity = min(1.0, (permeability - 0.5) * 2.0)  # 0 at 0.5, 1 at 1.0

        # We darken certain bands rather than modifying per-pixel for performance.
        # Create a mask surface with horizontal bands.
        mask = pygame.Surface(
            (spirit_surface.get_width(), spirit_surface.get_height()),
            pygame.SRCALPHA,
        )
        darken_alpha = int(60 * intensity)

        for y in range(spirit_surface.get_height()):
            band_pos = (y + scroll) % (band_height * 2)
            if band_pos >= band_height:
                pygame.draw.line(
                    mask,
                    (0, 0, 0, darken_alpha),
                    (0, y),
                    (spirit_surface.get_width() - 1, y),
                )

        spirit_surface.blit(mask, (0, 0))

    # -----------------------------------------------------------------------
    # Effects rendering
    # -----------------------------------------------------------------------

    def _render_effects(self, game_state: dict) -> None:
        """Draw visual effects from the EffectManager onto the effect layer."""
        effect_manager: Optional[EffectManager] = game_state.get("effects")
        if effect_manager is None:
            return

        # The EffectManager works with RenderTarget, but we need to draw
        # pygame primitives.  For lightweight integration we render shimmer
        # and glow effects directly using pygame shapes.
        for effect in effect_manager._effects:
            if effect.state is not EffectState.ACTIVE:
                continue
            if isinstance(effect, SpiritShimmerEffect):
                self._draw_shimmer_effect(effect)
            elif isinstance(effect, MaGlowEffect):
                self._draw_ma_glow_effect(effect)

        self.screen.blit(self._effect_layer, (0, 0))

    def _draw_shimmer_effect(self, effect: SpiritShimmerEffect) -> None:
        """Draw a spirit shimmer as translucent scrolling bands."""
        sx, sy = self.camera.world_to_screen(effect.x, effect.y)
        scroll = int(effect.elapsed_ms / 1000.0 * effect.scroll_speed)
        color = (effect.color.r, effect.color.g, effect.color.b)

        for ly in range(effect.height):
            world_y = ly + scroll
            band_pos = world_y % (effect.band_height * 2)
            if band_pos < effect.band_height:
                center_dist = abs(band_pos - effect.band_height / 2.0)
                falloff = 1.0 - (center_dist / max(1, effect.band_height / 2.0))
                alpha = int(effect.intensity * falloff)
                pygame.draw.line(
                    self._effect_layer,
                    (*color, max(0, min(255, alpha))),
                    (sx, sy + ly),
                    (sx + effect.width - 1, sy + ly),
                )

    def _draw_ma_glow_effect(self, effect: MaGlowEffect) -> None:
        """Draw a radial ma glow as concentric translucent circles."""
        sx, sy = self.camera.world_to_screen(effect.x, effect.y)
        alpha_pulse = ma_glow_alpha(
            effect.elapsed_ms, effect.ma_current, effect.ma_max,
        )
        base = effect._current_color()

        # Draw concentric rings from outside in for correct blending
        num_rings = max(1, effect.radius // 3)
        for i in range(num_rings):
            t = i / max(1, num_rings - 1)  # 0 = outermost, 1 = center
            radius = int(effect.radius * (1.0 - t))
            if radius <= 0:
                continue
            falloff = t  # brighter toward center
            alpha = int(base.a * falloff * alpha_pulse / 255.0)
            alpha = max(0, min(255, alpha))
            glow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                glow_surf,
                (base.r, base.g, base.b, alpha),
                (radius, radius),
                radius,
            )
            self._effect_layer.blit(
                glow_surf,
                (sx - radius, sy - radius),
            )

    # -----------------------------------------------------------------------
    # Ma Glow (screen-level pulsing overlay)
    # -----------------------------------------------------------------------

    def _render_ma_glow(self, ma: float, ma_max: float) -> None:
        """Draw a fullscreen radial gradient pulse representing ma energy.

        The pulse period slows as ma accumulates, visualising the
        stretching of subjective time.
        """
        period = ma_glow_pulse_period_ms(ma, ma_max)
        t = math.sin(2.0 * math.pi * self._elapsed_ms / period)
        norm = (t + 1.0) / 2.0
        ma_ratio = ma / ma_max if ma_max > 0 else 0.0

        # Base alpha scales with ma level and pulse
        base_alpha = int(15 + 40 * ma_ratio * norm)

        # Color shifts from soft indigo toward bright violet at high ma
        r = int(100 + 100 * ma_ratio)
        g = int(70 + 30 * ma_ratio)
        b = int(170 + 60 * ma_ratio)

        overlay = pygame.Surface((self.SCREEN_W, self.SCREEN_H), pygame.SRCALPHA)

        cx = self.SCREEN_W // 2
        cy = self.SCREEN_H // 2
        max_radius = int(math.sqrt(cx * cx + cy * cy))

        # Draw a handful of concentric ellipses for the radial gradient
        steps = 12
        for i in range(steps, 0, -1):
            frac = i / steps
            radius_x = int(max_radius * frac)
            radius_y = int(max_radius * frac)
            # Alpha fades toward center (inverse vignette)
            ring_alpha = int(base_alpha * (1.0 - frac * 0.6))
            ring_alpha = max(0, min(255, ring_alpha))
            pygame.draw.ellipse(
                overlay,
                (r, g, b, ring_alpha),
                (cx - radius_x, cy - radius_y, radius_x * 2, radius_y * 2),
            )

        self.screen.blit(overlay, (0, 0))

    # -----------------------------------------------------------------------
    # HUD rendering
    # -----------------------------------------------------------------------

    def render_hud(self, game_state: Any) -> None:
        """Draw the always-on HUD: HP bar, SP bar, Ma gauge, time indicator.

        Accepts either a dict or a Game object.
        """
        self._ui_layer.fill((0, 0, 0, 0))

        # Support both dict and Game object
        if isinstance(game_state, dict):
            hp = game_state.get("hp", GAMEPLAY.BASE_HP)
            hp_max = game_state.get("hp_max", GAMEPLAY.BASE_HP)
            sp = game_state.get("sp", GAMEPLAY.BASE_SP)
            sp_max = game_state.get("sp_max", GAMEPLAY.BASE_SP)
            ma = game_state.get("ma", 0.0)
            ma_max = game_state.get("ma_max", GAMEPLAY.MA_MAX)
            time_of_day = game_state.get("time_of_day")
        else:
            # Game object
            player = getattr(game_state, "player", None)
            hp = getattr(player, "hp", GAMEPLAY.BASE_HP) if player else GAMEPLAY.BASE_HP
            hp_max = getattr(player, "max_hp", GAMEPLAY.BASE_HP) if player else GAMEPLAY.BASE_HP
            sp = getattr(player, "sp", GAMEPLAY.BASE_SP) if player else GAMEPLAY.BASE_SP
            sp_max = getattr(player, "max_sp", GAMEPLAY.BASE_SP) if player else GAMEPLAY.BASE_SP
            ma_state = getattr(game_state, "ma", None)
            ma = getattr(ma_state, "current_ma", 0.0) if ma_state else 0.0
            ma_max = getattr(ma_state, "max_ma", GAMEPLAY.MA_MAX) if ma_state else GAMEPLAY.MA_MAX
            clock = getattr(game_state, "clock", None)
            time_of_day = getattr(clock, "time_of_day", None) if clock else None

        x = self._HUD_BAR_X
        y = self._HUD_BAR_Y

        # HP bar
        self._draw_bar(self._ui_layer, x, y, self._HUD_BAR_W, self._HUD_BAR_H,
                        hp / hp_max if hp_max > 0 else 0, self._CLR_HP, "HP")
        y += self._HUD_BAR_H + self._HUD_BAR_GAP

        # SP bar
        self._draw_bar(self._ui_layer, x, y, self._HUD_BAR_W, self._HUD_BAR_H,
                        sp / sp_max if sp_max > 0 else 0, self._CLR_SP, "SP")
        y += self._HUD_BAR_H + self._HUD_BAR_GAP

        # Ma gauge (circular / arc style drawn as a filled bar for consistency)
        self._draw_bar(self._ui_layer, x, y, self._HUD_BAR_W, self._HUD_BAR_H,
                        ma / ma_max if ma_max > 0 else 0, self._CLR_MA, "Ma")
        y += self._HUD_BAR_H + self._HUD_BAR_GAP

        # Time of day indicator (top right)
        if time_of_day is not None:
            tod_str = time_of_day.name if hasattr(time_of_day, "name") else str(time_of_day)
            self._draw_time_indicator(self._ui_layer, tod_str)

        self.screen.blit(self._ui_layer, (0, 0))

    def _draw_bar(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        w: int,
        h: int,
        fill_ratio: float,
        color: Tuple[int, int, int],
        label: str,
    ) -> None:
        """Draw a labelled status bar with background, fill, and text."""
        fill_ratio = max(0.0, min(1.0, fill_ratio))

        # Background
        pygame.draw.rect(surface, self._CLR_BAR_BG, (x, y, w, h))
        # Fill
        fill_w = int(w * fill_ratio)
        if fill_w > 0:
            pygame.draw.rect(surface, color, (x, y, fill_w, h))
        # Border
        pygame.draw.rect(surface, (80, 80, 100), (x, y, w, h), 1)
        # Label
        draw_text(surface, label, x + 4, y, self._CLR_WHITE, self._HUD_FONT_SIZE)

    def _draw_time_indicator(
        self,
        surface: pygame.Surface,
        time_str: str,
    ) -> None:
        """Draw a time-of-day label in the top-right corner."""
        font = pygame.font.SysFont(None, self._HUD_FONT_SIZE)
        text_surf = font.render(time_str, True, (200, 200, 220))
        tx = self.SCREEN_W - text_surf.get_width() - 12
        ty = 12

        # Semi-transparent background pill
        bg_rect = pygame.Rect(tx - 6, ty - 2, text_surf.get_width() + 12,
                              text_surf.get_height() + 4)
        bg = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg.fill((20, 15, 30, 160))
        surface.blit(bg, bg_rect.topleft)
        surface.blit(text_surf, (tx, ty))

    # -----------------------------------------------------------------------
    # Dialogue rendering
    # -----------------------------------------------------------------------

    def render_dialogue(self, game_state: dict) -> None:
        """Draw a dialogue box at the bottom of the screen.

        Expected ``game_state["dialogue"]`` keys:
        - ``"speaker"``: str (character name)
        - ``"text"``: str (dialogue text, may contain newlines)
        - ``"portrait"``: optional ``SpriteInstance`` for speaker portrait
        """
        dialogue = game_state.get("dialogue")
        if dialogue is None:
            return

        speaker = dialogue.get("speaker", "")
        text = dialogue.get("text", "")

        margin = self._DLG_MARGIN
        box_w = self.SCREEN_W - margin * 2
        box_h = self._DLG_HEIGHT
        box_x = margin
        box_y = self.SCREEN_H - margin - box_h

        # Semi-transparent box
        dlg_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        dlg_surf.fill(self._CLR_DLG_BG)

        # Border
        pygame.draw.rect(dlg_surf, self._CLR_DLG_BORDER, (0, 0, box_w, box_h), 2)

        # Speaker name tab
        if speaker:
            name_font = pygame.font.SysFont(None, self._DLG_NAME_FONT_SIZE)
            name_surf = name_font.render(speaker, True, (220, 200, 255))
            tab_w = name_surf.get_width() + 16
            tab_h = name_surf.get_height() + 8
            tab_surf = pygame.Surface((tab_w, tab_h), pygame.SRCALPHA)
            tab_surf.fill(self._CLR_DLG_BG)
            pygame.draw.rect(tab_surf, self._CLR_DLG_BORDER, (0, 0, tab_w, tab_h), 2)
            tab_surf.blit(name_surf, (8, 4))
            self.screen.blit(tab_surf, (box_x + 16, box_y - tab_h + 2))

        # Dialogue text with word wrapping
        padding = self._DLG_PADDING
        text_font = pygame.font.SysFont(None, self._DLG_FONT_SIZE)
        self._draw_wrapped_text(
            dlg_surf, text, text_font,
            padding, padding,
            box_w - padding * 2, box_h - padding * 2,
            (230, 230, 240),
        )

        self.screen.blit(dlg_surf, (box_x, box_y))

    def _draw_wrapped_text(
        self,
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        x: int,
        y: int,
        max_w: int,
        max_h: int,
        color: Tuple[int, int, int],
    ) -> None:
        """Render text with simple word-wrapping within a bounding box."""
        words = text.split(" ")
        line = ""
        line_y = y
        line_height = font.get_linesize()

        for word in words:
            # Handle explicit newlines within words
            parts = word.split("\n")
            for i, part in enumerate(parts):
                test_line = f"{line} {part}".strip() if line else part
                test_w = font.size(test_line)[0]
                if test_w > max_w and line:
                    rendered = font.render(line, True, color)
                    surface.blit(rendered, (x, line_y))
                    line_y += line_height
                    if line_y + line_height > y + max_h:
                        return
                    line = part
                else:
                    line = test_line

                if i < len(parts) - 1:
                    # Explicit newline
                    if line:
                        rendered = font.render(line, True, color)
                        surface.blit(rendered, (x, line_y))
                        line_y += line_height
                        if line_y + line_height > y + max_h:
                            return
                    line = ""

        if line:
            rendered = font.render(line, True, color)
            surface.blit(rendered, (x, line_y))

    # -----------------------------------------------------------------------
    # Combat rendering
    # -----------------------------------------------------------------------

    def render_combat(self, game_state: dict) -> None:
        """Render the combat / battle screen.

        Expected ``game_state["combat"]`` keys:
        - ``"player_party"``: list of dicts with ``"sprite"``, ``"hp"``,
          ``"hp_max"``, ``"sp"``, ``"sp_max"``, ``"name"``
        - ``"enemies"``: list of dicts with ``"sprite"``, ``"hp"``,
          ``"hp_max"``, ``"name"``
        - ``"turn_indicator"``: str (name of active combatant)
        - ``"action_menu"``: optional list of str (available actions)
        - ``"message"``: optional str (combat log line)
        """
        combat = game_state.get("combat")
        if combat is None:
            self.screen.fill(self._CLR_BG)
            return

        # Dark combat background
        self.screen.fill((12, 8, 20))

        # Draw a subtle gradient floor
        floor_surf = create_gradient_surface(
            self.SCREEN_W, self.SCREEN_H // 3,
            (25, 20, 40, 255), (12, 8, 20, 255),
            vertical=True,
        )
        self.screen.blit(floor_surf, (0, self.SCREEN_H * 2 // 3))

        # -- enemies (top half) --
        enemies = combat.get("enemies", [])
        enemy_spacing = self.SCREEN_W // (len(enemies) + 1) if enemies else 0
        for i, enemy in enumerate(enemies):
            ex = enemy_spacing * (i + 1)
            ey = self.SCREEN_H // 4
            sprite_inst: Optional[SpriteInstance] = enemy.get("sprite")
            if sprite_inst is not None:
                palette = (
                    self._spirit_palette
                    if sprite_inst.definition.is_spirit
                    else self._material_palette
                )
                frame = sprite_inst.current_frame()
                surf = palette_to_surface(frame.pixels, palette)
                self.screen.blit(
                    surf,
                    (ex - surf.get_width() // 2, ey - surf.get_height() // 2),
                )
            # Enemy name and HP
            name = enemy.get("name", "???")
            e_hp = enemy.get("hp", 0)
            e_hp_max = enemy.get("hp_max", 1)
            draw_text(self.screen, name, ex - 30, ey + 40, self._CLR_WHITE, 14)
            self._draw_bar(
                self.screen, ex - 40, ey + 56, 80, 8,
                e_hp / e_hp_max if e_hp_max > 0 else 0,
                self._CLR_HP, "",
            )

        # -- player party (bottom half) --
        party = combat.get("player_party", [])
        party_spacing = self.SCREEN_W // (len(party) + 1) if party else 0
        for i, member in enumerate(party):
            px = party_spacing * (i + 1)
            py = self.SCREEN_H * 3 // 5
            sprite_inst = member.get("sprite")
            if sprite_inst is not None:
                palette = self._material_palette
                frame = sprite_inst.current_frame()
                surf = palette_to_surface(frame.pixels, palette)
                self.screen.blit(
                    surf,
                    (px - surf.get_width() // 2, py - surf.get_height() // 2),
                )
            # Status
            name = member.get("name", "???")
            m_hp = member.get("hp", 0)
            m_hp_max = member.get("hp_max", 1)
            m_sp = member.get("sp", 0)
            m_sp_max = member.get("sp_max", 1)
            draw_text(self.screen, name, px - 30, py + 44, self._CLR_WHITE, 14)
            self._draw_bar(
                self.screen, px - 40, py + 60, 80, 8,
                m_hp / m_hp_max if m_hp_max > 0 else 0,
                self._CLR_HP, "",
            )
            self._draw_bar(
                self.screen, px - 40, py + 72, 80, 8,
                m_sp / m_sp_max if m_sp_max > 0 else 0,
                self._CLR_SP, "",
            )

        # -- turn indicator --
        turn = combat.get("turn_indicator", "")
        if turn:
            draw_text(
                self.screen, f"> {turn}'s turn",
                self.SCREEN_W // 2 - 60, 12,
                (255, 220, 140, 255), 16,
            )

        # -- action menu --
        actions = combat.get("action_menu")
        if actions:
            menu_x = self.SCREEN_W - 180
            menu_y = self.SCREEN_H - 40 - len(actions) * 24
            bg = pygame.Surface((160, len(actions) * 24 + 16), pygame.SRCALPHA)
            bg.fill((20, 15, 35, 200))
            pygame.draw.rect(
                bg, (100, 80, 140), (0, 0, bg.get_width(), bg.get_height()), 1,
            )
            self.screen.blit(bg, (menu_x - 8, menu_y - 8))
            selected = combat.get("selected_action", 0)
            for j, action in enumerate(actions):
                prefix = "> " if j == selected else "  "
                text_color = (255, 255, 200) if j == selected else (180, 180, 200)
                draw_text(
                    self.screen, f"{prefix}{action}",
                    menu_x, menu_y + j * 24,
                    (*text_color, 255), 16,
                )

        # -- combat message --
        message = combat.get("message", "")
        if message:
            msg_y = self.SCREEN_H // 2 - 10
            draw_text(
                self.screen, message,
                self.SCREEN_W // 2 - len(message) * 4, msg_y,
                (220, 220, 255, 255), 16,
            )

    # -----------------------------------------------------------------------
    # Menu rendering
    # -----------------------------------------------------------------------

    def render_menu(self, game_state: dict) -> None:
        """Render a fullscreen menu overlay.

        Expected ``game_state["menu"]`` keys:
        - ``"title"``: str
        - ``"items"``: list of str
        - ``"selected"``: int (index of highlighted item)
        - ``"description"``: optional str (description of selected item)
        """
        menu = game_state.get("menu")
        if menu is None:
            return

        # Dim the background
        dim = pygame.Surface((self.SCREEN_W, self.SCREEN_H), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 180))
        self.screen.blit(dim, (0, 0))

        title = menu.get("title", "Menu")
        items = menu.get("items", [])
        selected = menu.get("selected", 0)
        description = menu.get("description", "")

        # Title
        draw_text(
            self.screen, title,
            self.SCREEN_W // 2 - len(title) * 6, 40,
            (220, 200, 255, 255), 28,
        )

        # Divider line
        pygame.draw.line(
            self.screen, (100, 80, 140),
            (self.SCREEN_W // 4, 72),
            (self.SCREEN_W * 3 // 4, 72),
        )

        # Menu items
        item_x = self.SCREEN_W // 3
        item_y_start = 100
        item_h = 32

        for i, item in enumerate(items):
            iy = item_y_start + i * item_h
            is_sel = i == selected

            if is_sel:
                # Highlight background
                sel_bg = pygame.Surface((self.SCREEN_W // 3, item_h - 4), pygame.SRCALPHA)
                sel_bg.fill((80, 60, 120, 120))
                self.screen.blit(sel_bg, (item_x - 8, iy - 2))

            prefix = "> " if is_sel else "   "
            text_color = (255, 255, 230) if is_sel else (160, 160, 180)
            draw_text(
                self.screen, f"{prefix}{item}",
                item_x, iy,
                (*text_color, 255), 20,
            )

        # Description pane
        if description:
            desc_y = item_y_start + len(items) * item_h + 20
            pygame.draw.line(
                self.screen, (60, 50, 80),
                (self.SCREEN_W // 4, desc_y - 8),
                (self.SCREEN_W * 3 // 4, desc_y - 8),
            )
            draw_text(
                self.screen, description,
                item_x, desc_y,
                (180, 180, 200, 255), 14,
            )

    # -----------------------------------------------------------------------
    # Toast notifications
    # -----------------------------------------------------------------------

    def _render_toasts(self, game_state: dict) -> None:
        """Draw ephemeral notification toasts near the top of screen.

        New toasts are taken from ``game_state["toasts"]`` (list of str).
        Each toast fades out after 3 seconds.
        """
        new_toasts = game_state.get("toasts", [])
        now = self._elapsed_ms
        toast_duration = 3000.0

        for text in new_toasts:
            self._toasts.append((text, now + toast_duration))

        # Remove expired
        self._toasts = [(t, exp) for t, exp in self._toasts if exp > now]

        if not self._toasts:
            return

        ty = self._TOAST_Y_OFFSET
        for text, expire_at in self._toasts:
            remaining = expire_at - now
            alpha = min(255, int(255 * remaining / 500.0)) if remaining < 500 else 255

            font = pygame.font.SysFont(None, self._TOAST_FONT_SIZE)
            text_surf = font.render(text, True, (230, 230, 240))

            tw = text_surf.get_width() + self._TOAST_PADDING * 2
            th = text_surf.get_height() + self._TOAST_PADDING
            tx = (self.SCREEN_W - tw) // 2

            bg = pygame.Surface((tw, th), pygame.SRCALPHA)
            bg.fill((25, 20, 40, min(200, alpha)))
            pygame.draw.rect(bg, (120, 100, 160, min(200, alpha)), (0, 0, tw, th), 1)

            self.screen.blit(bg, (tx, ty))
            text_surf.set_alpha(alpha)
            self.screen.blit(text_surf, (tx + self._TOAST_PADDING, ty + self._TOAST_PADDING // 2))

            ty += th + 4

    # -----------------------------------------------------------------------
    # Screen transitions
    # -----------------------------------------------------------------------

    def render_transition(self, game_state: dict) -> None:
        """Draw screen transitions: fade, dissolve, spirit_tear.

        Expected ``game_state["transition"]`` keys:
        - ``"type"``: ``"fade"`` | ``"dissolve"`` | ``"spirit_tear"``
        - ``"progress"``: float 0-1 (0=start, 0.5=peak, 1=done)
        """
        transition = game_state.get("transition")
        if transition is None or not transition.get("active", True):
            return

        t_type = transition.get("type", "fade")
        progress = transition.get("progress", 0.0)

        # Convert progress to alpha: peak darkness at 0.5
        if progress <= 0.5:
            intensity = progress * 2.0  # 0 -> 1
        else:
            intensity = (1.0 - progress) * 2.0  # 1 -> 0

        self._transition_overlay.fill((0, 0, 0, 0))

        if t_type == "fade":
            self._transition_fade(intensity)
        elif t_type == "dissolve":
            self._transition_dissolve(intensity)
        elif t_type == "spirit_tear":
            self._transition_spirit_tear(intensity, progress)
        else:
            self._transition_fade(intensity)

        self.screen.blit(self._transition_overlay, (0, 0))

    def _transition_fade(self, intensity: float) -> None:
        """Simple fade to black."""
        alpha = int(255 * intensity)
        self._transition_overlay.fill((0, 0, 0, max(0, min(255, alpha))))

    def _transition_dissolve(self, intensity: float) -> None:
        """Dissolve effect using a pseudo-random pixel threshold.

        Pixels are revealed/hidden based on a deterministic hash of their
        position compared to the intensity threshold.
        """
        alpha_base = int(255 * intensity)
        # For performance, draw blocks rather than individual pixels
        block_size = 8
        cols = self.SCREEN_W // block_size + 1
        rows = self.SCREEN_H // block_size + 1

        for by in range(rows):
            for bx in range(cols):
                # Deterministic hash for this block
                h = ((bx * 7 + by * 13 + bx * by * 3) % 100) / 100.0
                if h < intensity:
                    px = bx * block_size
                    py = by * block_size
                    pygame.draw.rect(
                        self._transition_overlay,
                        (0, 0, 0, alpha_base),
                        (px, py, block_size, block_size),
                    )

    def _transition_spirit_tear(self, intensity: float, progress: float) -> None:
        """Spirit veil tear transition.

        A radial tear opens from center, with a magenta-white edge glow.
        """
        cx = self.SCREEN_W // 2
        cy = self.SCREEN_H // 2
        max_radius = int(math.sqrt(cx * cx + cy * cy))

        if progress <= 0.5:
            # Opening: tear expands
            radius = int(max_radius * (progress * 2.0))
        else:
            # Closing: tear contracts
            radius = int(max_radius * ((1.0 - progress) * 2.0))

        # Fill everything with black, then cut a transparent circle
        self._transition_overlay.fill((0, 0, 0, int(255 * intensity)))

        if radius > 0:
            # Clear the center area
            pygame.draw.circle(
                self._transition_overlay,
                (0, 0, 0, 0),
                (cx, cy),
                radius,
            )

            # Glowing edge ring
            edge_width = max(2, radius // 8)
            for ring in range(edge_width):
                ring_radius = radius + ring - edge_width // 2
                if ring_radius <= 0:
                    continue
                edge_alpha = int(180 * (1.0 - abs(ring - edge_width // 2) / max(1, edge_width // 2)))
                pygame.draw.circle(
                    self._transition_overlay,
                    (255, 0, 255, max(0, min(255, edge_alpha))),
                    (cx, cy),
                    ring_radius,
                    1,
                )

    # -----------------------------------------------------------------------
    # Cache management
    # -----------------------------------------------------------------------

    def cache_sprite_definition(
        self,
        definition: SpriteDefinition,
        palette: Optional[Palette] = None,
    ) -> None:
        """Pre-render all frames of a sprite definition into the cache.

        This is useful during loading screens to avoid frame hitches.

        Args:
            definition: The sprite to pre-cache.
            palette: Palette to use; defaults based on ``palette_mode``.
        """
        if palette is None:
            palette = self._palette_mgr.palette_for_mode(definition.palette_mode)

        for anim_name, anim in definition.animations.items():
            for frame_idx, frame in enumerate(anim.frames):
                for flip_h in (False, True):
                    self._get_flipped_sprite_surface(
                        definition, frame, anim_name, frame_idx, flip_h, palette,
                    )

    def clear_sprite_cache(self) -> None:
        """Discard all cached sprite surfaces to free memory."""
        self._sprite_cache.clear()

    def rebuild_tile_cache(
        self,
        tile_sprites: Optional[List[SpriteDefinition]] = None,
    ) -> None:
        """Rebuild the tile cache, optionally with new tile definitions.

        Call this when the season changes and tile colours need to shift.
        """
        if tile_sprites is None:
            tile_sprites = build_tile_sprites()
        self._tile_cache = create_tile_cache(tile_sprites, self._material_palette)
        # Spirit variants
        for tile_def in tile_sprites:
            if "static" in tile_def.animations:
                frame = tile_def.animations["static"].frames[0]
                spirit_name = tile_def.name + "_spirit"
                self._tile_cache[spirit_name] = palette_to_surface(
                    frame.pixels, self._spirit_palette,
                )

    def update_palettes(self, season: Optional[Season] = None) -> None:
        """Refresh palette references, optionally applying seasonal shifts.

        After calling this, ``rebuild_tile_cache`` should be called to
        reflect the new colours.
        """
        self._material_palette = self._palette_mgr.material
        self._spirit_palette = self._palette_mgr.spirit

    # -----------------------------------------------------------------------
    # Scene-facing render methods
    # -----------------------------------------------------------------------
    # These are called by the Scene subclasses (via hasattr checks) and
    # bridge between the game-object API and the internal rendering calls.

    # TileType -> tile cache name mapping
    _TILE_TYPE_MAP: Dict[str, str] = {
        "FLOOR": "road_tile",
        "WALL": "shrine_tile",
        "DOOR": "road_tile",
        "STAIRS": "road_tile",
        "WATER": "park_tile",
        "SPIRIT_FLOOR": "road_tile",
        "SPIRIT_WALL": "shrine_tile",
        "INTERACTIVE": "road_tile",
        "NPC": "road_tile",
        "HAZARD": "park_tile",
        "TORII_GATE": "shrine_tile",
        "SAVE_POINT": "shrine_tile",
    }

    def render_map(self, tile_map: Any, spirit_active: bool = False) -> None:
        """Render a TileMap object (from exploration.movement) onto screen."""
        self._material_layer.fill((0, 0, 0, 0))

        ts = self.TILE_SIZE
        cam_x = self.camera.x
        cam_y = self.camera.y
        zoom = self.camera.zoom
        shake_x, shake_y = self.camera.get_shake_offset()

        width = getattr(tile_map, "width", 0)
        height = getattr(tile_map, "height", 0)
        tiles = getattr(tile_map, "tiles", {})

        start_col = max(0, int(cam_x / ts) - 1)
        start_row = max(0, int(cam_y / ts) - 1)
        end_col = min(width, int((cam_x + self.SCREEN_W / zoom) / ts) + 2)
        end_row = min(height, int((cam_y + self.SCREEN_H / zoom) / ts) + 2)

        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                tile = tiles.get((col, row))
                if tile is None:
                    continue

                tile_type_name = tile.tile_type.name if hasattr(tile, "tile_type") else "FLOOR"
                tile_sprite_name = self._TILE_TYPE_MAP.get(tile_type_name, "road_tile")

                # Use spirit variant if spirit vision is active
                if spirit_active and tile_type_name.startswith("SPIRIT"):
                    tile_sprite_name = tile_sprite_name + "_spirit"

                tile_surf = self._tile_cache.get(tile_sprite_name)
                if tile_surf is None:
                    # Fallback: draw a colored rectangle
                    tile_surf = self._make_fallback_tile(tile_type_name)

                world_x = col * ts
                world_y = row * ts
                screen_x = int((world_x - cam_x) * zoom + shake_x)
                screen_y = int((world_y - cam_y) * zoom + shake_y)

                if zoom != 1.0:
                    scaled_size = int(ts * zoom) + 1
                    scaled = pygame.transform.scale(tile_surf, (scaled_size, scaled_size))
                    self._material_layer.blit(scaled, (screen_x, screen_y))
                else:
                    self._material_layer.blit(tile_surf, (screen_x, screen_y))

        self.screen.blit(self._material_layer, (0, 0))

    def _make_fallback_tile(self, tile_type_name: str) -> pygame.Surface:
        """Create a detailed tile surface with patterns for visual distinction."""
        ts = self.TILE_SIZE
        surf = pygame.Surface((ts, ts), pygame.SRCALPHA)

        if tile_type_name == "FLOOR":
            # Earthy ground with subtle texture
            surf.fill((95, 82, 68))
            for i in range(0, ts, 4):
                c = 90 + (i * 7 % 15)
                pygame.draw.line(surf, (c, c - 8, c - 15), (0, i), (ts, i))
            # Subtle stone dots
            for dx in (4, 12):
                for dy in (4, 12):
                    if (dx + dy) % 8 == 0:
                        pygame.draw.circle(surf, (80, 72, 58), (dx, dy), 1)

        elif tile_type_name == "WALL":
            # Dark brick-like wall
            surf.fill((55, 48, 58))
            for row in range(0, ts, 4):
                offset = 4 if (row // 4) % 2 else 0
                for col in range(offset, ts, 8):
                    w = min(7, ts - col)
                    pygame.draw.rect(surf, (62, 55, 65), (col, row, w, 3))
                    pygame.draw.rect(surf, (48, 42, 50), (col, row, w, 3), 1)

        elif tile_type_name == "DOOR":
            # Wooden door with frame
            surf.fill((95, 82, 68))
            pygame.draw.rect(surf, (140, 95, 50), (2, 0, ts - 4, ts))
            pygame.draw.rect(surf, (110, 75, 40), (2, 0, ts - 4, ts), 1)
            # Wood grain
            for i in range(3, ts - 3, 3):
                pygame.draw.line(surf, (125, 85, 45), (4, i), (ts - 4, i))
            # Handle
            pygame.draw.circle(surf, (180, 160, 80), (ts - 5, ts // 2), 2)

        elif tile_type_name == "INTERACTIVE":
            # Glowing ochre with sparkle
            surf.fill((100, 88, 55))
            pygame.draw.rect(surf, (120, 105, 65), (1, 1, ts - 2, ts - 2))
            # Sparkle indicator
            cx, cy = ts // 2, ts // 2
            for angle_offset in range(4):
                dx = [0, 3, 0, -3][angle_offset]
                dy = [-3, 0, 3, 0][angle_offset]
                pygame.draw.line(surf, (200, 180, 120),
                                 (cx, cy), (cx + dx, cy + dy))

        elif tile_type_name == "NPC":
            # Character tile - person-shaped on ground
            surf.fill((95, 82, 68))
            cx, cy = ts // 2, ts // 2
            # Head
            pygame.draw.circle(surf, (200, 160, 130), (cx, cy - 3), 3)
            # Body
            pygame.draw.rect(surf, (140, 100, 80), (cx - 3, cy, 6, 5))
            # Feet
            pygame.draw.rect(surf, (80, 60, 50), (cx - 3, cy + 5, 2, 2))
            pygame.draw.rect(surf, (80, 60, 50), (cx + 1, cy + 5, 2, 2))

        elif tile_type_name == "SAVE_POINT":
            # Stone jizo statue
            surf.fill((95, 82, 68))
            cx = ts // 2
            # Base
            pygame.draw.rect(surf, (130, 130, 140), (cx - 4, ts - 4, 8, 4))
            # Body
            pygame.draw.rect(surf, (150, 150, 160), (cx - 3, ts - 10, 6, 6))
            # Head
            pygame.draw.circle(surf, (160, 160, 170), (cx, ts - 12), 3)
            # Soft glow
            glow = pygame.Surface((ts, ts), pygame.SRCALPHA)
            pygame.draw.circle(glow, (140, 120, 180, 40), (cx, ts - 8), 7)
            surf.blit(glow, (0, 0))

        elif tile_type_name == "WATER":
            surf.fill((35, 55, 110))
            # Wave pattern
            for i in range(0, ts, 3):
                y_off = 1 if i % 6 < 3 else 0
                pygame.draw.line(surf, (50, 75, 140),
                                 (0, i + y_off), (ts, i + y_off))

        elif tile_type_name == "SPIRIT_FLOOR":
            surf.fill((50, 40, 80))
            # Ethereal shimmer dots
            for dx in range(2, ts, 5):
                for dy in range(2, ts, 5):
                    pygame.draw.circle(surf, (100, 80, 160, 100), (dx, dy), 1)

        elif tile_type_name == "TORII_GATE":
            surf.fill((95, 82, 68))
            # Red torii columns and beam
            pygame.draw.rect(surf, (180, 40, 30), (2, 2, 3, ts - 2))
            pygame.draw.rect(surf, (180, 40, 30), (ts - 5, 2, 3, ts - 2))
            pygame.draw.rect(surf, (180, 40, 30), (0, 2, ts, 3))
            pygame.draw.rect(surf, (180, 40, 30), (1, 6, ts - 2, 2))

        elif tile_type_name == "HAZARD":
            surf.fill((100, 35, 35))
            # Warning pattern
            pygame.draw.line(surf, (140, 50, 50), (0, 0), (ts, ts))
            pygame.draw.line(surf, (140, 50, 50), (ts, 0), (0, ts))

        else:
            surf.fill((60, 60, 60))
            pygame.draw.rect(surf, (70, 70, 70), (0, 0, ts, ts), 1)

        self._tile_cache[tile_type_name + "_fallback"] = surf
        return surf

    def render_player(self, x: float, y: float, facing: Any) -> None:
        """Render the player character at grid position (x, y)."""
        ts = self.TILE_SIZE
        cam_x = self.camera.x
        cam_y = self.camera.y
        zoom = self.camera.zoom
        shake_x, shake_y = self.camera.get_shake_offset()

        screen_x = int((x * ts - cam_x) * zoom + shake_x)
        screen_y = int((y * ts - cam_y) * zoom + shake_y)

        size = int(ts * zoom)

        # Draw a simple character sprite (colored rectangle with direction indicator)
        player_surf = pygame.Surface((size, size), pygame.SRCALPHA)

        # Body
        body_color = (100, 140, 200)
        margin = max(1, size // 8)
        pygame.draw.rect(player_surf, body_color,
                         (margin, margin, size - margin * 2, size - margin * 2))

        # Direction indicator (small triangle)
        facing_name = facing.name if hasattr(facing, "name") else str(facing)
        indicator_color = (220, 200, 160)
        cx, cy = size // 2, size // 2
        tri_size = max(2, size // 5)
        if facing_name == "NORTH":
            points = [(cx, cy - tri_size), (cx - tri_size, cy), (cx + tri_size, cy)]
        elif facing_name == "SOUTH":
            points = [(cx, cy + tri_size), (cx - tri_size, cy), (cx + tri_size, cy)]
        elif facing_name == "EAST":
            points = [(cx + tri_size, cy), (cx, cy - tri_size), (cx, cy + tri_size)]
        else:  # WEST
            points = [(cx - tri_size, cy), (cx, cy - tri_size), (cx, cy + tri_size)]
        pygame.draw.polygon(player_surf, indicator_color, points)

        self.screen.blit(player_surf, (screen_x, screen_y))

    def render_npcs(self, npcs: Any) -> None:
        """Render NPC markers on the map."""
        if not npcs:
            return
        ts = self.TILE_SIZE
        cam_x = self.camera.x
        cam_y = self.camera.y
        zoom = self.camera.zoom
        shake_x, shake_y = self.camera.get_shake_offset()

        for npc in npcs:
            nx = getattr(npc, "x", 0)
            ny = getattr(npc, "y", 0)
            screen_x = int((nx * ts - cam_x) * zoom + shake_x)
            screen_y = int((ny * ts - cam_y) * zoom + shake_y)
            size = int(ts * zoom)

            npc_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.rect(npc_surf, (180, 120, 80),
                             (size // 6, size // 6, size * 2 // 3, size * 2 // 3))
            self.screen.blit(npc_surf, (screen_x, screen_y))

    def render_title_screen(self, title_screen: Any) -> None:
        """Render the title screen with game name and menu."""
        self.screen.fill(self._CLR_BG)

        # Title text
        title_opacity = getattr(title_screen, "title_opacity", 1.0)
        if title_opacity > 0:
            alpha = int(255 * title_opacity)
            # Main title
            draw_text(
                self.screen,
                "間の国",
                self.SCREEN_W // 2 - 60,
                self.SCREEN_H // 4 - 20,
                (200, 180, 220, alpha),
                size=48,
            )
            # Subtitle
            sub_opacity = getattr(title_screen, "subtitle_opacity", title_opacity)
            if sub_opacity > 0:
                sub_alpha = int(255 * sub_opacity)
                draw_text(
                    self.screen,
                    "Ma no Kuni — The Country Between",
                    self.SCREEN_W // 2 - 150,
                    self.SCREEN_H // 4 + 40,
                    (160, 140, 180, sub_alpha),
                    size=16,
                )

        # Menu
        menu_opacity = getattr(title_screen, "menu_opacity", 1.0)
        menu = getattr(title_screen, "menu", None)
        if menu is not None and menu_opacity > 0:
            items = getattr(menu, "items", [])
            selected_idx = getattr(menu, "selected_index", 0)
            alpha = int(255 * menu_opacity)
            start_y = self.SCREEN_H // 2 + 20

            for i, item in enumerate(items):
                label = getattr(item, "label", str(item))
                enabled = getattr(item, "enabled", True)
                is_selected = (i == selected_idx)

                if is_selected:
                    color = (255, 240, 200, alpha)
                    prefix = "▸ "
                elif not enabled:
                    color = (80, 70, 90, alpha)
                    prefix = "  "
                else:
                    color = (160, 150, 170, alpha)
                    prefix = "  "

                draw_text(
                    self.screen,
                    prefix + label,
                    self.SCREEN_W // 2 - 60,
                    start_y + i * 28,
                    color,
                    size=18,
                )

        # Decorative spirit particles
        t = time.time()
        for i in range(5):
            px = int(self.SCREEN_W * 0.2 + math.sin(t * 0.3 + i * 1.3) * self.SCREEN_W * 0.3)
            py = int(self.SCREEN_H * 0.3 + math.cos(t * 0.2 + i * 0.9) * self.SCREEN_H * 0.2)
            pa = int(40 + 30 * math.sin(t * 0.5 + i))
            pygame.draw.circle(self.screen, (140, 120, 180, pa), (px, py), 3)

    def render_dialogue_box(self, dialogue_box: Any) -> None:
        """Render a dialogue box overlay."""
        margin = self._DLG_MARGIN
        box_h = self._DLG_HEIGHT
        box_y = self.SCREEN_H - box_h - margin
        box_w = self.SCREEN_W - margin * 2

        # Semi-transparent background
        overlay = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        overlay.fill(self._CLR_DLG_BG)
        pygame.draw.rect(overlay, self._CLR_DLG_BORDER, (0, 0, box_w, box_h), 2)
        self.screen.blit(overlay, (margin, box_y))

        # Speaker name
        speaker = getattr(dialogue_box, "speaker", "")
        if speaker:
            draw_text(
                self.screen, speaker,
                margin + self._DLG_PADDING,
                box_y + 6,
                (200, 180, 220, 255),
                size=self._DLG_NAME_FONT_SIZE,
            )

        # Text content
        text = getattr(dialogue_box, "text", "")
        if text:
            draw_text(
                self.screen, text,
                margin + self._DLG_PADDING,
                box_y + 24,
                self._CLR_WHITE,
                size=self._DLG_FONT_SIZE,
            )

        # Choices
        choices = getattr(dialogue_box, "choices", [])
        if choices:
            choice_y = box_y + 50
            selected = getattr(dialogue_box, "selected_choice_index", 0)
            for i, choice in enumerate(choices):
                choice_text = choice.get("text", "") if isinstance(choice, dict) else str(choice)
                is_sel = (i == selected)
                prefix = "▸ " if is_sel else "  "
                color = (255, 240, 200, 255) if is_sel else (160, 150, 170, 255)
                draw_text(
                    self.screen, prefix + choice_text,
                    margin + self._DLG_PADDING + 10,
                    choice_y + i * 22,
                    color,
                    size=self._DLG_FONT_SIZE - 2,
                )

    def render_battle(self, battle_state: Any = None, **kwargs: Any) -> None:
        """Render combat scene (placeholder)."""
        self.screen.fill((15, 10, 20))
        draw_text(self.screen, "— COMBAT —", self.SCREEN_W // 2 - 50,
                  20, self._CLR_WHITE, size=24)

    def render_menu(self, menu: Any) -> None:
        """Render a menu overlay."""
        overlay = pygame.Surface((self.SCREEN_W, self.SCREEN_H), pygame.SRCALPHA)
        overlay.fill((10, 8, 20, 200))
        self.screen.blit(overlay, (0, 0))

        items = getattr(menu, "items", [])
        selected_idx = getattr(menu, "selected_index", 0)
        start_y = 60

        draw_text(self.screen, "— Menu —", self.SCREEN_W // 2 - 40,
                  20, (200, 180, 220, 255), size=22)

        for i, item in enumerate(items):
            label = getattr(item, "label", str(item))
            is_sel = (i == selected_idx)
            prefix = "▸ " if is_sel else "  "
            color = (255, 240, 200, 255) if is_sel else (160, 150, 170, 255)
            draw_text(self.screen, prefix + label,
                      self.SCREEN_W // 2 - 80, start_y + i * 28,
                      color, size=18)

    def render_crafting(self, crafting_state: Any = None, **kwargs: Any) -> None:
        """Render crafting scene with recipe list and details."""
        recipes = kwargs.get("recipes", [])
        selected = kwargs.get("selected", 0)

        # Semi-transparent overlay
        overlay = pygame.Surface((self.SCREEN_W, self.SCREEN_H), pygame.SRCALPHA)
        overlay.fill((20, 15, 10, 200))
        self.screen.blit(overlay, (0, 0))

        # Title
        draw_text(self.screen, "— Kitchen Table —",
                  self.SCREEN_W // 2 - 80, 16, self._CLR_WHITE, size=20)

        if not recipes:
            draw_text(self.screen, "No recipes available.",
                      40, 60, (180, 170, 150, 255), size=16)
            draw_text(self.screen, "[X] Close",
                      40, self.SCREEN_H - 30, (140, 130, 120, 255), size=14)
            return

        # Recipe list
        y = 50
        for i, recipe in enumerate(recipes):
            name = getattr(recipe, "name", str(recipe))
            if i == selected:
                # Highlight bar
                pygame.draw.rect(self.screen, (60, 50, 40),
                                 (30, y - 2, self.SCREEN_W // 2 - 40, 20))
                color = (255, 240, 200, 255)
                draw_text(self.screen, ">", 20, y, color, size=16)
            else:
                color = (180, 170, 150, 255)
            draw_text(self.screen, name, 40, y, color, size=16)
            y += 22
            if y > self.SCREEN_H - 80:
                break

        # Selected recipe details (right panel)
        if 0 <= selected < len(recipes):
            recipe = recipes[selected]
            rx = self.SCREEN_W // 2 + 10
            ry = 50
            desc = getattr(recipe, "description", "")
            if desc:
                # Word-wrap description
                words = desc.split()
                line = ""
                for word in words:
                    test = f"{line} {word}".strip()
                    if len(test) > 30:
                        draw_text(self.screen, line, rx, ry,
                                  (200, 190, 170, 255), size=14)
                        ry += 18
                        line = word
                    else:
                        line = test
                if line:
                    draw_text(self.screen, line, rx, ry,
                              (200, 190, 170, 255), size=14)
                    ry += 24

            # Materials required
            materials = getattr(recipe, "materials", [])
            if materials:
                draw_text(self.screen, "Materials:", rx, ry,
                          (160, 150, 130, 255), size=14)
                ry += 18
                for mat in materials:
                    mat_id = getattr(mat, "material_id", str(mat))
                    qty = getattr(mat, "quantity", 1)
                    draw_text(self.screen, f"  {mat_id} x{qty}", rx, ry,
                              (140, 130, 110, 255), size=14)
                    ry += 16

        # Controls
        draw_text(self.screen, "[Z] Craft   [X] Close",
                  40, self.SCREEN_H - 30, (140, 130, 120, 255), size=14)

    def render_vignette_beat(self, beat: Any, vignette: Any, ma: Any) -> None:
        """Render a vignette narrative beat (placeholder)."""
        self.screen.fill((10, 10, 15))
        text = getattr(beat, "text", "...")
        draw_text(self.screen, text, 40, self.SCREEN_H // 3,
                  (180, 170, 200, 255), size=18)

    def render_intro(
        self,
        heading: str,
        body: str,
        char_index: int,
        fade_alpha: float,
        fully_revealed: bool,
    ) -> None:
        """Render the opening narrative intro screen."""
        self.screen.fill((12, 10, 18))

        alpha = int(255 * fade_alpha)

        # Heading (always fully visible once we start)
        heading_len = len(heading)
        visible_heading = heading[:min(char_index, heading_len)]
        if visible_heading:
            draw_text(
                self.screen, visible_heading,
                self.SCREEN_W // 2 - len(heading) * 5,
                self.SCREEN_H // 3 - 40,
                (220, 200, 240, alpha),
                size=24,
            )

        # Body text (revealed character by character)
        body_chars = max(0, char_index - heading_len)
        visible_body = body[:body_chars]
        if visible_body:
            lines = visible_body.split("\n")
            for i, line in enumerate(lines):
                if line:
                    draw_text(
                        self.screen, line,
                        self.SCREEN_W // 2 - 180,
                        self.SCREEN_H // 3 + 10 + i * 22,
                        (180, 170, 195, alpha),
                        size=16,
                    )

        # "Press Z to continue" prompt when fully revealed
        if fully_revealed:
            pulse = int(120 + 80 * math.sin(time.time() * 3.0))
            draw_text(
                self.screen, "[ Z / Enter ]",
                self.SCREEN_W // 2 - 45,
                self.SCREEN_H - 60,
                (pulse, pulse - 20, pulse + 20, 200),
                size=14,
            )

        # Decorative side particles
        t = time.time()
        for i in range(8):
            px = int(self.SCREEN_W * 0.1 + math.sin(t * 0.2 + i * 0.8) * 30)
            py = int(self.SCREEN_H * 0.2 + i * self.SCREEN_H * 0.08)
            pa = int(30 + 20 * math.sin(t * 0.4 + i))
            pygame.draw.circle(self.screen, (120, 100, 160, pa), (px, py), 2)
            # Mirror on right side
            px2 = self.SCREEN_W - px
            pygame.draw.circle(self.screen, (120, 100, 160, pa), (px2, py), 2)

    def render_interaction_labels(self, tile_map: Any, movement: Any) -> None:
        """Draw floating labels above interactive tiles near the player."""
        if movement is None or tile_map is None:
            return

        ts = self.TILE_SIZE
        cam_x = self.camera.x
        cam_y = self.camera.y
        zoom = self.camera.zoom
        shake_x, shake_y = self.camera.get_shake_offset()

        player_x = movement.position.x
        player_y = movement.position.y

        tiles = getattr(tile_map, "tiles", {})
        facing = movement.facing

        for (tx, ty), tile in tiles.items():
            if tile.interaction is None:
                continue

            # Only show labels for tiles within 3 tiles of the player
            dist = abs(tx - player_x) + abs(ty - player_y)
            if dist > 3:
                continue

            name = tile.metadata.get("name", "")
            if not name:
                continue

            screen_x = int((tx * ts - cam_x) * zoom + shake_x)
            screen_y = int((ty * ts - cam_y) * zoom + shake_y)

            tile_center_x = screen_x + int(ts * zoom) // 2
            label_y = screen_y - 12

            # Highlight if player is facing this tile
            facing_target = movement.position.offset(facing)
            is_facing = (tx == facing_target.x and ty == facing_target.y)

            if is_facing:
                color = (255, 240, 200, 255)
                # Show action hint
                action_hint = self._interaction_hint(tile.interaction)
                draw_text(
                    self.screen, f"[Z] {action_hint}",
                    tile_center_x - len(action_hint) * 3 - 8,
                    label_y - 14,
                    (255, 220, 140, 220),
                    size=11,
                )
            else:
                color = (180, 170, 190, 160)

            # Draw name label
            draw_text(
                self.screen, name,
                tile_center_x - len(name) * 3,
                label_y,
                color,
                size=11,
            )

    @staticmethod
    def _interaction_hint(interaction_type: Any) -> str:
        """Get a short action hint for an interaction type."""
        name = interaction_type.name if hasattr(interaction_type, "name") else str(interaction_type)
        hints = {
            "TALK": "Talk",
            "EXAMINE": "Examine",
            "OPEN": "Open",
            "PRAY": "Pray",
            "SIT": "Sit",
            "LISTEN": "Listen",
            "PICK_UP": "Pick up",
            "USE": "Use",
        }
        return hints.get(name, "Interact")
