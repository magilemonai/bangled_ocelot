"""
Ma no Kuni - Rendering Engine

Draws two worlds on one screen. The material world is crisp, warm, grounded.
The spirit world shimmers, glows, breathes. When both overlap,
Tokyo becomes something no one has ever seen before.
"""

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Tuple, List, Dict


class RenderLayer(Enum):
    """Rendering layers, back to front."""
    BACKGROUND = 0
    TERRAIN = 1
    SPIRIT_TERRAIN = 2
    OBJECTS = 3
    SPIRIT_OBJECTS = 4
    NPCS = 5
    SPIRITS = 6
    PLAYER = 7
    WEATHER = 8
    SPIRIT_WEATHER = 9
    EFFECTS = 10
    UI_WORLD = 11      # Health bars, interaction prompts
    UI_OVERLAY = 12     # Menus, dialogue
    TRANSITION = 13     # Screen transitions
    MA_OVERLAY = 14     # The ma effect - the stillness made visible


@dataclass
class Camera:
    """
    The eye through which we see both worlds.
    Smooth following with configurable lead and lag.
    """
    x: float = 0.0
    y: float = 0.0
    target_x: float = 0.0
    target_y: float = 0.0
    zoom: float = 1.0
    target_zoom: float = 1.0
    viewport_width: int = 320
    viewport_height: int = 240
    follow_speed: float = 0.08
    zoom_speed: float = 0.05
    shake_intensity: float = 0.0
    shake_decay: float = 0.9

    def update(self, delta: float) -> None:
        """Smooth camera following with optional shake."""
        self.x += (self.target_x - self.x) * self.follow_speed
        self.y += (self.target_y - self.y) * self.follow_speed
        self.zoom += (self.target_zoom - self.zoom) * self.zoom_speed

        if self.shake_intensity > 0.01:
            self.shake_intensity *= self.shake_decay
        else:
            self.shake_intensity = 0.0

    def follow(self, entity_x: float, entity_y: float) -> None:
        """Set camera to follow an entity (usually Aoi)."""
        self.target_x = entity_x - self.viewport_width / 2
        self.target_y = entity_y - self.viewport_height / 2

    def shake(self, intensity: float) -> None:
        """Screen shake for impacts, spirit surges, emotional moments."""
        self.shake_intensity = max(self.shake_intensity, intensity)

    def get_shake_offset(self) -> Tuple[float, float]:
        """Get current shake displacement."""
        if self.shake_intensity <= 0:
            return (0.0, 0.0)
        import random
        return (
            random.uniform(-self.shake_intensity, self.shake_intensity),
            random.uniform(-self.shake_intensity, self.shake_intensity),
        )

    def world_to_screen(self, wx: float, wy: float) -> Tuple[int, int]:
        """Convert world coordinates to screen coordinates."""
        sx = int((wx - self.x) * self.zoom)
        sy = int((wy - self.y) * self.zoom)
        shake_x, shake_y = self.get_shake_offset()
        return (int(sx + shake_x), int(sy + shake_y))

    def screen_to_world(self, sx: int, sy: int) -> Tuple[float, float]:
        """Convert screen coordinates to world coordinates."""
        wx = sx / self.zoom + self.x
        wy = sy / self.zoom + self.y
        return (wx, wy)


@dataclass
class SpiritVisionEffect:
    """
    The visual transformation when Aoi activates spirit sight.
    The world doesn't change - your perception of it does.
    """
    active: bool = False
    intensity: float = 0.0
    target_intensity: float = 0.0
    transition_speed: float = 0.03
    pulse_phase: float = 0.0
    pulse_speed: float = 0.5
    edge_shimmer: float = 0.0

    # Visual parameters
    material_desaturation: float = 0.0   # How much the real world fades
    spirit_opacity: float = 0.0          # How visible spirits become
    veil_distortion: float = 0.0         # Warping at world boundaries
    memory_bleed: float = 0.0            # Past images showing through

    def activate(self) -> None:
        self.active = True
        self.target_intensity = 1.0

    def deactivate(self) -> None:
        self.active = False
        self.target_intensity = 0.0

    def update(self, delta: float, permeability: float) -> None:
        """Update spirit vision effect. Permeability affects the intensity."""
        self.intensity += (self.target_intensity - self.intensity) * self.transition_speed
        self.pulse_phase += self.pulse_speed * delta
        pulse = (math.sin(self.pulse_phase) + 1.0) / 2.0

        effective = self.intensity * (0.5 + 0.5 * permeability)

        self.material_desaturation = effective * 0.6
        self.spirit_opacity = effective * 0.8 + pulse * 0.2 * effective
        self.veil_distortion = effective * 0.3 * permeability
        self.memory_bleed = max(0, effective - 0.7) * permeability
        self.edge_shimmer = effective * pulse * 0.5


@dataclass
class MaVisualEffect:
    """
    When ma accumulates, the world itself seems to slow.
    Colors deepen. Edges soften. Time stretches visibly.
    """
    ma_level: float = 0.0
    color_deepening: float = 0.0
    edge_softness: float = 0.0
    time_dilation_visual: float = 0.0
    particle_slowdown: float = 1.0
    vignette_intensity: float = 0.0
    breath_phase: float = 0.0

    def update(self, ma: float, delta: float) -> None:
        """Update ma visual effect based on current ma level."""
        self.ma_level = ma / 100.0  # Normalize to 0-1
        self.color_deepening = self.ma_level * 0.4
        self.edge_softness = self.ma_level * 0.3
        self.time_dilation_visual = self.ma_level * 0.5
        self.particle_slowdown = 1.0 - (self.ma_level * 0.7)
        self.vignette_intensity = self.ma_level * 0.2

        # The world breathes slower as ma increases
        breath_speed = 1.0 - (self.ma_level * 0.8)
        self.breath_phase += breath_speed * delta


@dataclass
class TransitionEffect:
    """Screen transitions - the space between scenes is itself a scene."""
    active: bool = False
    progress: float = 0.0
    duration: float = 1.0
    transition_type: str = "fade"  # fade, dissolve, spirit_tear, memory_wash, ma_still
    halfway_callback: Optional[object] = None
    callback_fired: bool = False

    def start(self, transition_type: str = "fade", duration: float = 1.0,
              on_halfway=None) -> None:
        self.active = True
        self.progress = 0.0
        self.duration = duration
        self.transition_type = transition_type
        self.halfway_callback = on_halfway
        self.callback_fired = False

    def update(self, delta: float) -> bool:
        """Update transition. Returns True when complete."""
        if not self.active:
            return False

        self.progress += delta / self.duration

        if self.progress >= 0.5 and not self.callback_fired:
            if self.halfway_callback:
                self.halfway_callback()
            self.callback_fired = True

        if self.progress >= 1.0:
            self.active = False
            self.progress = 0.0
            return True

        return False


class Renderer:
    """
    The renderer sees all layers and composes them into a single image.
    Material and spirit, past and present, silence and sound.
    """

    def __init__(self, screen_width: int = 640, screen_height: int = 480):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.camera = Camera(
            viewport_width=screen_width,
            viewport_height=screen_height,
        )
        self.spirit_vision = SpiritVisionEffect()
        self.ma_effect = MaVisualEffect()
        self.transition = TransitionEffect()
        self.render_layers: Dict[RenderLayer, list] = {
            layer: [] for layer in RenderLayer
        }
        self.ambient_particles: List[dict] = []
        self.spirit_particles: List[dict] = []
        self.frame_count: int = 0

    def clear_layers(self) -> None:
        """Clear all render layers for new frame."""
        for layer in self.render_layers:
            self.render_layers[layer].clear()

    def add_to_layer(self, layer: RenderLayer, drawable: dict) -> None:
        """Add a drawable item to a render layer."""
        self.render_layers[layer].append(drawable)

    def update(self, delta: float, permeability: float, ma_level: float) -> None:
        """Update all visual systems."""
        self.camera.update(delta)
        self.spirit_vision.update(delta, permeability)
        self.ma_effect.update(ma_level, delta)
        self.transition.update(delta)
        self.frame_count += 1

        self._update_ambient_particles(delta, permeability)

    def _update_ambient_particles(self, delta: float, permeability: float) -> None:
        """
        Ambient particles that make the world feel alive.
        Material: dust motes, rain, leaves, city light reflections.
        Spirit: floating orbs, memory fragments, spirit dust.
        """
        # Update existing particles
        for particle in self.ambient_particles:
            particle["life"] -= delta
            particle["x"] += particle["vx"] * delta
            particle["y"] += particle["vy"] * delta

        for particle in self.spirit_particles:
            particle["life"] -= delta
            particle["x"] += particle["vx"] * delta * self.ma_effect.particle_slowdown
            particle["y"] += particle["vy"] * delta * self.ma_effect.particle_slowdown

        # Remove dead particles
        self.ambient_particles = [p for p in self.ambient_particles if p["life"] > 0]
        self.spirit_particles = [p for p in self.spirit_particles if p["life"] > 0]

    def spawn_ambient_particle(self, x: float, y: float, particle_type: str) -> None:
        """Spawn a material-world ambient particle."""
        import random
        self.ambient_particles.append({
            "x": x, "y": y,
            "vx": random.uniform(-5, 5),
            "vy": random.uniform(-10, -2),
            "life": random.uniform(1.0, 4.0),
            "type": particle_type,
        })

    def spawn_spirit_particle(self, x: float, y: float, particle_type: str) -> None:
        """Spawn a spirit-world particle. These move slower during ma."""
        import random
        self.spirit_particles.append({
            "x": x, "y": y,
            "vx": random.uniform(-2, 2),
            "vy": random.uniform(-5, 0),
            "life": random.uniform(2.0, 8.0),
            "type": particle_type,
            "glow": random.uniform(0.3, 1.0),
        })

    def get_render_state(self) -> dict:
        """
        Return the complete render state for the current frame.
        This would be consumed by the actual rendering backend (pygame, etc).
        """
        return {
            "frame": self.frame_count,
            "camera": {
                "x": self.camera.x,
                "y": self.camera.y,
                "zoom": self.camera.zoom,
                "shake": self.camera.get_shake_offset(),
            },
            "spirit_vision": {
                "active": self.spirit_vision.active,
                "material_desat": self.spirit_vision.material_desaturation,
                "spirit_opacity": self.spirit_vision.spirit_opacity,
                "veil_distortion": self.spirit_vision.veil_distortion,
                "memory_bleed": self.spirit_vision.memory_bleed,
                "edge_shimmer": self.spirit_vision.edge_shimmer,
            },
            "ma_effect": {
                "level": self.ma_effect.ma_level,
                "color_deepening": self.ma_effect.color_deepening,
                "edge_softness": self.ma_effect.edge_softness,
                "vignette": self.ma_effect.vignette_intensity,
                "particle_slowdown": self.ma_effect.particle_slowdown,
            },
            "transition": {
                "active": self.transition.active,
                "progress": self.transition.progress,
                "type": self.transition.transition_type,
            },
            "layers": {
                layer.name: items
                for layer, items in self.render_layers.items()
            },
            "ambient_particles": len(self.ambient_particles),
            "spirit_particles": len(self.spirit_particles),
        }
