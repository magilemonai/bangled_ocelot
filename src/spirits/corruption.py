"""
Ma no Kuni - Spirit Corruption Mechanics

MIRAIKAN Corporation extracts spirit energy to power their technologies.
They call it "spiritual resource management." It is, in truth, a violence
so fundamental that the spirit world itself screams in response.

Corruption is what happens when spirit energy is torn from its source.
It is not evil in the simple sense - it is pain made manifest. A corrupted
spirit is not a villain. It is a victim whose suffering has become
contagious.

But corruption has a deeper cause than MIRAIKAN. The corporation is
exploiting a wound that already existed. Something ancient is wrong.
Something beneath the foundations of Tokyo, beneath the bedrock,
beneath even the oldest memories. The corruption feeds on it.
That is the fourth-order truth the player must eventually discover.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.engine.game import WorldClock
    from src.spirits.spirit_world import (
        Spirit, SpiritTerritory, SpiritEcology, SpiritElement,
    )
    from src.spirits.permeation import PermeationEngine
    from src.spirits.bonds import SpiritBond


# ---------------------------------------------------------------------------
# Corruption Enumerations
# ---------------------------------------------------------------------------

class CorruptionStage(Enum):
    """
    Stages of corruption, each with distinct visual and behavioral markers.
    These are not just gameplay states - they are stories of suffering.
    """
    CLEAN = "clean"                  # 0.0       - No corruption
    TAINTED = "tainted"              # 0.01-0.25 - Faint wrongness
    DISTORTED = "distorted"          # 0.25-0.50 - Visible corruption
    TWISTED = "twisted"              # 0.50-0.75 - Fundamental change
    CONSUMED = "consumed"            # 0.75-1.00 - Nearly lost

    @property
    def range(self) -> tuple[float, float]:
        ranges = {
            CorruptionStage.CLEAN: (0.0, 0.01),
            CorruptionStage.TAINTED: (0.01, 0.25),
            CorruptionStage.DISTORTED: (0.25, 0.50),
            CorruptionStage.TWISTED: (0.50, 0.75),
            CorruptionStage.CONSUMED: (0.75, 1.01),
        }
        return ranges[self]

    @classmethod
    def from_level(cls, level: float) -> "CorruptionStage":
        for stage in cls:
            low, high = stage.range
            if low <= level < high:
                return stage
        return cls.CONSUMED


class CorruptionSource(Enum):
    """What is causing the corruption."""
    MIRAIKAN_EXTRACTION = "miraikan_extraction"     # Direct corporate activity
    CORRUPTION_SPREAD = "corruption_spread"          # Spread from nearby corruption
    EMOTIONAL_TRAUMA = "emotional_trauma"             # Human suffering concentrated
    SPIRITUAL_WOUND = "spiritual_wound"               # Ancient damage to the veil
    ENVIRONMENTAL_DAMAGE = "environmental_damage"     # Buried rivers, paved shrines
    DEEPER_CAUSE = "deeper_cause"                     # The thing beneath everything


class PurificationMethod(Enum):
    """How corruption can be addressed. Not all methods work on all corruption."""
    COMBAT = "combat"                    # Fight and defeat - temporary, doesn't heal
    RITUAL_PURIFICATION = "ritual"       # Shrine-based cleansing
    ITEM_PURIFICATION = "item"           # Specific items that cleanse
    NEGOTIATION = "negotiation"          # Understand the pain, help process it
    MA_PURIFICATION = "ma"               # Pure stillness and presence
    BOND_PURIFICATION = "bond"           # A bonded spirit helps cleanse
    ENVIRONMENTAL = "environmental"      # Restore the physical environment
    DEEP_PURIFICATION = "deep"           # Address the root cause


class EnvironmentalCorruptionEffect(Enum):
    """How corruption manifests in the material world."""
    DYING_PLANTS = "dying_plants"                # Vegetation wilts and browns
    GLITCHING_ELECTRONICS = "glitching_electronics"  # Screens flicker, data corrupts
    EMOTIONAL_MALAISE = "emotional_malaise"       # Humans feel heavy, tired, sad
    ANIMAL_FLIGHT = "animal_flight"               # Animals avoid the area
    TEMPORAL_STUTTER = "temporal_stutter"          # Time seems to skip or repeat
    COLOR_DRAIN = "color_drain"                   # World looks desaturated
    SOUND_DISTORTION = "sound_distortion"         # Audio warps, echoes wrongly
    REALITY_FLICKER = "reality_flicker"           # Brief glimpses of wrong things
    TEMPERATURE_ANOMALY = "temperature_anomaly"   # Inexplicable cold or heat
    MEMORY_EROSION = "memory_erosion"             # People forget things about the area


# ---------------------------------------------------------------------------
# Corruption Data Structures
# ---------------------------------------------------------------------------

@dataclass
class CorruptionVisuals:
    """
    Visual manifestations of corruption at each stage. These describe
    what the player SEES, both in the material and spirit worlds.
    """
    stage: CorruptionStage

    # Material world visuals
    material_ambient: str = ""          # Background visual change
    material_objects: str = ""          # How objects look
    material_npcs: str = ""             # How humans are affected visually
    material_sky: str = ""              # Sky and atmosphere

    # Spirit world visuals
    spirit_ambient: str = ""
    spirit_terrain: str = ""
    spirit_entities: str = ""

    # Audio
    ambient_sound: str = ""
    music_distortion: str = ""


def build_corruption_visuals() -> dict[CorruptionStage, CorruptionVisuals]:
    """Build the visual language of corruption for each stage."""
    visuals: dict[CorruptionStage, CorruptionVisuals] = {}

    visuals[CorruptionStage.CLEAN] = CorruptionVisuals(
        stage=CorruptionStage.CLEAN,
        material_ambient="Normal. The world as it should be.",
        spirit_ambient="The spirit world in its natural state, vibrant and alive.",
    )

    visuals[CorruptionStage.TAINTED] = CorruptionVisuals(
        stage=CorruptionStage.TAINTED,
        material_ambient="A faint wrongness. Colors slightly off. Shadows a degree too dark.",
        material_objects="Electronics occasionally glitch. Plants droop slightly.",
        material_npcs="People seem tired. Conversations trail off. Smiles don't reach eyes.",
        material_sky="Sky seems slightly overcast even on clear days.",
        spirit_ambient="Faint dark veins visible at edges of vision, like cracks in glass.",
        spirit_terrain="Terrain has subtle discoloration, as if stained by old ink.",
        spirit_entities="Spirits are restless, movements slightly jerky.",
        ambient_sound="A barely audible low hum, felt more than heard.",
        music_distortion="Occasional notes sustain a half-beat too long.",
    )

    visuals[CorruptionStage.DISTORTED] = CorruptionVisuals(
        stage=CorruptionStage.DISTORTED,
        material_ambient="Clearly wrong. Colors desaturated. Geometry feels unstable.",
        material_objects="Electronics malfunction regularly. Plants die. Metal corrodes faster.",
        material_npcs="Irritability, headaches, insomnia. Arguments break out over nothing.",
        material_sky="Unnatural cloud formations. Light has a sickly quality.",
        spirit_ambient="Dark tendrils visibly pulse through the air. Corruption has form.",
        spirit_terrain="Ground is cracked, seeping dark energy. Pools of corruption form.",
        spirit_entities="Corrupted spirits show visible distortion: fragmented edges, "
                        "wrong colors, movements that stutter and skip.",
        ambient_sound="A grinding, discordant hum. Occasional sharp static bursts.",
        music_distortion="Notes clash. Rhythms break. The music struggles.",
    )

    visuals[CorruptionStage.TWISTED] = CorruptionVisuals(
        stage=CorruptionStage.TWISTED,
        material_ambient="The world is breaking. Walls crack in impossible patterns. "
                         "Shadows move independently of their sources.",
        material_objects="Technology is unreliable. Plants are dead or mutated. "
                         "Objects slowly move when not observed.",
        material_npcs="Depression, paranoia, rage. People avoid the area. Those who stay "
                      "change. Memories of the place become confused.",
        material_sky="Sky is wrong. Colors that don't exist in nature. The light hurts.",
        spirit_ambient="Corruption dominates. The original spirit landscape is barely visible "
                        "beneath writhing dark energy.",
        spirit_terrain="Terrain is actively hostile. Ground shifts. Paths change. "
                        "The corruption has its own geography.",
        spirit_entities="Corrupted spirits are barely recognizable. Their original forms "
                        "are entombed in dark shells. They attack on sight.",
        ambient_sound="A scream just below hearing. Constant. Like the land itself in agony.",
        music_distortion="Music is almost gone. What remains is inverted, minor, wrong.",
    )

    visuals[CorruptionStage.CONSUMED] = CorruptionVisuals(
        stage=CorruptionStage.CONSUMED,
        material_ambient="Reality has failed here. The material world is a thin shell "
                         "over a wound. Things are and are not simultaneously.",
        material_objects="Objects exist in superposition. A chair is a chair and also "
                         "a memory of a chair and also something that was never a chair.",
        material_npcs="No one comes here anymore. Those who do don't come back the same. "
                      "Or don't come back.",
        material_sky="There is no sky. There is an absence where the sky should be.",
        spirit_ambient="This is no longer the spirit world. It is the wound itself. "
                        "The corruption IS the landscape.",
        spirit_terrain="There is no terrain. There is corruption with shape. "
                        "It mimics ground, walls, sky, but it is all the same thing.",
        spirit_entities="There are no individual spirits here. They have been absorbed. "
                        "The corruption moves with stolen faces.",
        ambient_sound="Silence. But a silence that screams.",
        music_distortion="No music. The void.",
    )

    return visuals


@dataclass
class CorruptionNode:
    """
    A specific point of corruption in the world. Corruption spreads from
    nodes, which can be natural wounds or MIRAIKAN extraction sites.
    """
    node_id: str
    location_id: str
    district_id: str
    source: CorruptionSource

    # Corruption state
    level: float = 0.0                  # 0.0 = clean, 1.0 = consumed
    growth_rate: float = 0.01           # How fast corruption grows per tick
    spread_radius: float = 0.0         # How far it spreads (in arbitrary units)
    max_radius: float = 5.0

    # The pain behind the corruption
    underlying_cause: str = ""          # What's really wrong here
    manifestation: str = ""             # How it appears
    affected_spirit_ids: list[str] = field(default_factory=list)

    # Purification tracking
    purification_attempts: int = 0
    successful_purifications: int = 0
    required_method: Optional[PurificationMethod] = None  # Some nodes need specific methods
    purification_resistance: float = 0.0  # Builds up if only partially purified

    # Environmental effects
    active_effects: list[EnvironmentalCorruptionEffect] = field(default_factory=list)

    # MIRAIKAN specific
    is_extraction_site: bool = False
    extraction_rate: float = 0.0        # How fast MIRAIKAN is draining
    extraction_device_active: bool = False

    @property
    def stage(self) -> CorruptionStage:
        return CorruptionStage.from_level(self.level)

    @property
    def is_active(self) -> bool:
        return self.level > 0.01

    @property
    def is_critical(self) -> bool:
        """Has this node reached a dangerous level?"""
        return self.level >= 0.5

    @property
    def effective_growth_rate(self) -> float:
        """Actual growth rate, modified by extraction and resistance."""
        rate = self.growth_rate
        if self.extraction_device_active:
            rate += self.extraction_rate
        # Corruption accelerates as it deepens
        rate *= (1.0 + self.level * 0.5)
        return rate

    def grow(self, delta: float) -> dict:
        """
        Grow the corruption. Returns events for stage transitions.
        """
        result: dict = {"events": [], "old_level": self.level}

        old_stage = self.stage
        self.level = min(1.0, self.level + self.effective_growth_rate * delta)

        # Update spread radius
        self.spread_radius = self.max_radius * self.level

        # Update environmental effects
        self._update_environmental_effects()

        new_stage = self.stage
        if new_stage != old_stage:
            result["events"].append({
                "type": "corruption_stage_change",
                "node_id": self.node_id,
                "old_stage": old_stage.value,
                "new_stage": new_stage.value,
                "level": self.level,
            })

        result["new_level"] = self.level
        return result

    def attempt_purification(self, method: PurificationMethod,
                              power: float) -> dict:
        """
        Attempt to purify this corruption node.

        Different methods have different effectiveness. Combat only
        suppresses. Negotiation only works if you understand the cause.
        True purification requires addressing the underlying wound.
        """
        result: dict = {
            "success": False,
            "events": [],
            "purified_amount": 0.0,
        }
        self.purification_attempts += 1

        # Method effectiveness
        effectiveness = self._get_method_effectiveness(method)

        # Required method check
        if self.required_method and method != self.required_method:
            effectiveness *= 0.3
            result["events"].append("wrong_method")

        # Resistance reduces effectiveness
        effective_power = power * effectiveness * (1.0 - self.purification_resistance * 0.5)

        if effective_power <= 0:
            result["events"].append("purification_failed")
            return result

        old_level = self.level
        old_stage = self.stage
        self.level = max(0.0, self.level - effective_power)
        result["purified_amount"] = old_level - self.level

        new_stage = self.stage
        if new_stage != old_stage:
            result["events"].append({
                "type": "corruption_stage_reduced",
                "old_stage": old_stage.value,
                "new_stage": new_stage.value,
            })

        if self.level <= 0.01:
            self.level = 0.0
            self.active_effects.clear()
            self.spread_radius = 0.0
            self.successful_purifications += 1
            result["success"] = True
            result["events"].append("corruption_purified")
        else:
            # Partial purification builds resistance
            self.purification_resistance = min(
                0.5, self.purification_resistance + 0.05
            )
            result["events"].append("corruption_reduced")

        # Combat is a temporary fix
        if method == PurificationMethod.COMBAT:
            result["events"].append("combat_suppression_only")

        self._update_environmental_effects()
        return result

    def disable_extraction(self) -> dict:
        """Disable the MIRAIKAN extraction device at this node."""
        result: dict = {"events": []}

        if self.extraction_device_active:
            self.extraction_device_active = False
            self.extraction_rate = 0.0
            self.growth_rate = max(0.001, self.growth_rate * 0.5)
            result["events"].append("extraction_disabled")
        else:
            result["events"].append("no_extraction_device")

        return result

    def _get_method_effectiveness(self, method: PurificationMethod) -> float:
        """How effective a purification method is against this node's source."""
        # Base effectiveness by method
        base = {
            PurificationMethod.COMBAT: 0.2,         # Barely works, temporary
            PurificationMethod.RITUAL_PURIFICATION: 0.6,
            PurificationMethod.ITEM_PURIFICATION: 0.5,
            PurificationMethod.NEGOTIATION: 0.7,
            PurificationMethod.MA_PURIFICATION: 0.8,
            PurificationMethod.BOND_PURIFICATION: 0.7,
            PurificationMethod.ENVIRONMENTAL: 0.5,
            PurificationMethod.DEEP_PURIFICATION: 1.0,
        }

        effectiveness = base.get(method, 0.3)

        # Source-method affinity
        source_bonuses: dict[CorruptionSource, dict[PurificationMethod, float]] = {
            CorruptionSource.MIRAIKAN_EXTRACTION: {
                PurificationMethod.ENVIRONMENTAL: 0.3,
                PurificationMethod.NEGOTIATION: 0.2,
            },
            CorruptionSource.EMOTIONAL_TRAUMA: {
                PurificationMethod.NEGOTIATION: 0.4,
                PurificationMethod.MA_PURIFICATION: 0.3,
            },
            CorruptionSource.SPIRITUAL_WOUND: {
                PurificationMethod.RITUAL_PURIFICATION: 0.3,
                PurificationMethod.BOND_PURIFICATION: 0.2,
            },
            CorruptionSource.ENVIRONMENTAL_DAMAGE: {
                PurificationMethod.ENVIRONMENTAL: 0.4,
            },
            CorruptionSource.DEEPER_CAUSE: {
                PurificationMethod.DEEP_PURIFICATION: 0.5,
                PurificationMethod.COMBAT: -0.15,  # Combat makes it worse
            },
        }

        bonuses = source_bonuses.get(self.source, {})
        effectiveness += bonuses.get(method, 0.0)

        return max(0.0, min(1.5, effectiveness))

    def _update_environmental_effects(self) -> None:
        """Update which environmental effects are active based on corruption level."""
        self.active_effects.clear()

        if self.level >= 0.05:
            self.active_effects.append(EnvironmentalCorruptionEffect.EMOTIONAL_MALAISE)
        if self.level >= 0.15:
            self.active_effects.append(EnvironmentalCorruptionEffect.DYING_PLANTS)
            self.active_effects.append(EnvironmentalCorruptionEffect.ANIMAL_FLIGHT)
        if self.level >= 0.25:
            self.active_effects.append(EnvironmentalCorruptionEffect.GLITCHING_ELECTRONICS)
            self.active_effects.append(EnvironmentalCorruptionEffect.COLOR_DRAIN)
        if self.level >= 0.4:
            self.active_effects.append(EnvironmentalCorruptionEffect.SOUND_DISTORTION)
            self.active_effects.append(EnvironmentalCorruptionEffect.TEMPERATURE_ANOMALY)
        if self.level >= 0.6:
            self.active_effects.append(EnvironmentalCorruptionEffect.REALITY_FLICKER)
            self.active_effects.append(EnvironmentalCorruptionEffect.MEMORY_EROSION)
        if self.level >= 0.8:
            self.active_effects.append(EnvironmentalCorruptionEffect.TEMPORAL_STUTTER)


@dataclass
class CorruptedArea:
    """
    An area on the map affected by corruption. This is the spatial
    representation - the corruption has claimed ground.
    """
    area_id: str
    center_location_id: str
    district_id: str
    radius: float = 0.0
    corruption_nodes: list[str] = field(default_factory=list)  # Node IDs
    average_corruption: float = 0.0

    # NPCs affected
    affected_npc_ids: list[str] = field(default_factory=list)
    evacuated: bool = False

    # Visual overlay
    material_description: str = ""
    spirit_description: str = ""

    @property
    def stage(self) -> CorruptionStage:
        return CorruptionStage.from_level(self.average_corruption)

    @property
    def is_dangerous(self) -> bool:
        return self.average_corruption >= 0.5

    @property
    def is_lethal(self) -> bool:
        return self.average_corruption >= 0.8

    def contains_location(self, location_id: str, distance: float) -> bool:
        """Check if a location falls within this corrupted area."""
        return distance <= self.radius


@dataclass
class SpiritCorruptionProfile:
    """
    How corruption specifically affects an individual spirit. Corruption
    is personal - it twists what was beautiful, inverts what was kind,
    breaks what was whole.
    """
    spirit_id: str
    original_disposition: str = ""      # What they were before
    original_memories: list[str] = field(default_factory=list)

    # Corruption manifestation
    visual_corruption: str = ""         # How their appearance changes
    behavioral_changes: list[str] = field(default_factory=list)
    lost_memories: list[str] = field(default_factory=list)
    corrupted_abilities: list[str] = field(default_factory=list)

    # The spirit's pain
    pain_source: str = ""               # What hurt them
    pain_expression: str = ""           # How they express it
    what_they_cry_for: str = ""         # What they want, deep down
    negotiation_key: str = ""           # What you need to say or do to reach them

    # Recovery potential
    recovery_difficulty: float = 0.5    # 0.0 = easy, 1.0 = nearly impossible
    requires_specific_bond: Optional[str] = None  # Specific spirit bond needed
    requires_specific_item: Optional[str] = None   # Specific item needed
    requires_memory_trigger: Optional[str] = None  # A memory that could wake them


@dataclass
class MiraikanExtractionSite:
    """
    A MIRAIKAN Corporation spirit energy extraction facility.
    These are the direct cause of much of the corruption in Tokyo.

    The corporation sees spirits as a resource. They have developed
    technology to siphon spiritual energy and convert it into a form
    that powers their devices, their profit, their ambition.

    What they don't tell the shareholders: every extraction tears
    the veil a little more, corrupts the spirits a little more,
    and feeds the deeper wound beneath Tokyo.
    """
    site_id: str
    location_id: str
    district_id: str
    site_name: str

    # Operational state
    is_active: bool = True
    extraction_power: float = 0.5       # How aggressively they extract
    efficiency: float = 0.3             # How much energy vs waste
    daily_extraction: float = 0.0       # Energy extracted per day
    cumulative_extraction: float = 0.0  # Total energy ever extracted

    # Corruption output
    corruption_output: float = 0.0      # How much corruption this generates
    corruption_node_id: Optional[str] = None  # Connected corruption node

    # Security
    security_level: int = 1             # 1-5, affects infiltration difficulty
    personnel_count: int = 5
    has_spirit_barrier: bool = False     # Prevents spirit interference
    is_concealed: bool = True           # Hidden from public

    # Story progression
    discoverable: bool = False          # Can Aoi find this yet?
    discovered: bool = False
    sabotaged: bool = False
    destroyed: bool = False

    # Connected spirits
    captured_spirit_ids: list[str] = field(default_factory=list)
    target_spirit_ids: list[str] = field(default_factory=list)

    @property
    def corruption_rate(self) -> float:
        """How much corruption this site produces per tick."""
        if not self.is_active or self.sabotaged:
            return 0.0
        waste = self.extraction_power * (1.0 - self.efficiency)
        return waste * 0.1

    def extract(self, delta: float) -> dict:
        """
        Perform one tick of extraction. Returns energy gained and
        corruption produced.
        """
        result: dict = {
            "energy_extracted": 0.0,
            "corruption_produced": 0.0,
            "events": [],
        }

        if not self.is_active or self.sabotaged:
            return result

        energy = self.extraction_power * self.efficiency * delta
        corruption = self.corruption_rate * delta

        self.daily_extraction += energy
        self.cumulative_extraction += energy

        result["energy_extracted"] = energy
        result["corruption_produced"] = corruption

        # Captured spirits suffer
        for spirit_id in self.captured_spirit_ids:
            result["events"].append({
                "type": "spirit_drained",
                "spirit_id": spirit_id,
                "amount": energy * 0.1,
            })

        return result

    def sabotage(self) -> dict:
        """Aoi sabotages the extraction equipment."""
        result: dict = {"events": []}

        if self.sabotaged:
            result["events"].append("already_sabotaged")
            return result

        self.sabotaged = True
        self.is_active = False
        result["events"].append("site_sabotaged")

        # Release captured spirits
        for spirit_id in self.captured_spirit_ids:
            result["events"].append({
                "type": "spirit_freed",
                "spirit_id": spirit_id,
            })

        return result

    def repair(self) -> None:
        """MIRAIKAN repairs the site (story event, happens over time)."""
        self.sabotaged = False
        self.is_active = True


# ---------------------------------------------------------------------------
# The Deeper Cause
# ---------------------------------------------------------------------------

@dataclass
class DeeperCorruption:
    """
    The corruption beneath the corruption. MIRAIKAN is the proximate cause,
    but they are exploiting something that was already there.

    Beneath Tokyo, beneath the concrete and steel, beneath the buried rivers
    and forgotten shrines, there is a wound in the boundary between worlds.
    It has been there for a very long time. Perhaps since the city first
    grew large enough to forget what it was built on.

    This system tracks the player's discovery of the deeper truth.
    """
    awareness_level: float = 0.0        # How much Aoi knows (0-1)
    investigation_stage: int = 0        # Quest progression stage

    # Clues discovered
    clues_found: list[str] = field(default_factory=list)
    total_clues: int = 12               # Total clues in the game

    # The wound itself
    wound_activity: float = 0.1         # How active the deeper corruption is
    wound_growth_rate: float = 0.001    # How fast it grows
    wound_location_hints: list[str] = field(default_factory=list)

    # Story thresholds
    threshold_events: dict[float, str] = field(default_factory=lambda: {
        0.1: "first_hint",              # Something is wrong beyond MIRAIKAN
        0.25: "pattern_recognized",     # The corruption has a pattern
        0.4: "historical_connection",   # This has happened before, long ago
        0.55: "ancient_records",        # Old spirits remember the wound
        0.7: "location_narrowed",       # The source is beneath specific place
        0.85: "the_wound_revealed",     # Aoi sees the wound directly
        1.0: "understanding_achieved",  # The full truth, and what must be done
    })

    triggered_thresholds: list[float] = field(default_factory=list)

    def discover_clue(self, clue_id: str) -> dict:
        """Discover a clue about the deeper corruption."""
        result: dict = {"events": []}

        if clue_id in self.clues_found:
            result["events"].append("clue_already_known")
            return result

        self.clues_found.append(clue_id)
        old_awareness = self.awareness_level
        self.awareness_level = len(self.clues_found) / self.total_clues

        # Check thresholds
        for threshold, event_name in sorted(self.threshold_events.items()):
            if old_awareness < threshold <= self.awareness_level:
                if threshold not in self.triggered_thresholds:
                    self.triggered_thresholds.append(threshold)
                    result["events"].append({
                        "type": "deeper_corruption_threshold",
                        "threshold": threshold,
                        "event": event_name,
                    })

        result["awareness"] = self.awareness_level
        result["clues_found"] = len(self.clues_found)
        result["clues_total"] = self.total_clues
        return result

    def update(self, delta: float, global_corruption: float) -> dict:
        """
        The deeper wound grows regardless of what anyone does. But its growth
        rate is affected by surface corruption - MIRAIKAN's extraction feeds it.
        """
        result: dict = {"events": []}

        # Surface corruption accelerates the wound
        amplified_rate = self.wound_growth_rate * (1.0 + global_corruption * 2.0)
        self.wound_activity = min(1.0, self.wound_activity + amplified_rate * delta)

        # The wound pulses, and each pulse can cause surface effects
        if random.random() < self.wound_activity * 0.05:
            result["events"].append({
                "type": "wound_pulse",
                "intensity": self.wound_activity,
            })

        return result


# ---------------------------------------------------------------------------
# Corruption Engine - Master System
# ---------------------------------------------------------------------------

@dataclass
class CorruptionEngine:
    """
    The master corruption system. Tracks all corruption across Tokyo,
    manages MIRAIKAN operations, handles purification, and governs
    the deeper truth.

    This system interconnects with:
    - SpiritEcology: corrupted spirits, damaged territories
    - PermeationEngine: corruption destabilizes the veil
    - BondManager: bonds help resist and purify corruption
    - Narrative: the deeper cause is the game's central mystery
    """
    # Corruption nodes
    nodes: dict[str, CorruptionNode] = field(default_factory=dict)
    corrupted_areas: dict[str, CorruptedArea] = field(default_factory=dict)

    # MIRAIKAN operations
    extraction_sites: dict[str, MiraikanExtractionSite] = field(default_factory=dict)
    total_energy_extracted: float = 0.0

    # Spirit corruption profiles
    spirit_profiles: dict[str, SpiritCorruptionProfile] = field(default_factory=dict)

    # The deeper truth
    deeper_corruption: DeeperCorruption = field(default_factory=DeeperCorruption)

    # Global metrics
    global_corruption: float = 0.0     # Average across all tracked areas
    peak_corruption: float = 0.0       # Highest corruption ever reached
    total_purified: float = 0.0        # Total corruption ever purified

    # Corruption visual table
    _visuals: dict[CorruptionStage, CorruptionVisuals] = field(default_factory=dict)

    # Event log
    pending_events: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self._visuals:
            self._visuals = build_corruption_visuals()

    def register_node(self, node: CorruptionNode) -> None:
        """Register a corruption node."""
        self.nodes[node.node_id] = node

    def register_extraction_site(self, site: MiraikanExtractionSite) -> None:
        """Register a MIRAIKAN extraction site."""
        self.extraction_sites[site.site_id] = site

    def register_spirit_profile(self, profile: SpiritCorruptionProfile) -> None:
        """Register a spirit's corruption profile."""
        self.spirit_profiles[profile.spirit_id] = profile

    def get_corruption_at(self, location_id: str,
                           district_id: str) -> float:
        """Get the corruption level at a specific location."""
        max_corruption = 0.0
        for node in self.nodes.values():
            if node.location_id == location_id and node.district_id == district_id:
                max_corruption = max(max_corruption, node.level)
        return max_corruption

    def get_district_corruption(self, district_id: str) -> float:
        """Get average corruption for a district."""
        relevant = [
            n.level for n in self.nodes.values()
            if n.district_id == district_id and n.is_active
        ]
        if not relevant:
            return 0.0
        return sum(relevant) / len(relevant)

    def get_visuals_for(self, level: float) -> CorruptionVisuals:
        """Get corruption visuals for a given corruption level."""
        stage = CorruptionStage.from_level(level)
        return self._visuals.get(stage, self._visuals[CorruptionStage.CLEAN])

    def get_environmental_effects(self, district_id: str) -> list[EnvironmentalCorruptionEffect]:
        """Get all environmental effects active in a district."""
        effects: list[EnvironmentalCorruptionEffect] = []
        for node in self.nodes.values():
            if node.district_id == district_id and node.is_active:
                for effect in node.active_effects:
                    if effect not in effects:
                        effects.append(effect)
        return effects

    def corrupt_spirit(self, spirit_id: str, amount: float,
                        source: CorruptionSource) -> dict:
        """
        Apply corruption to a spirit. Creates or updates their
        corruption profile.
        """
        result: dict = {"events": []}

        if spirit_id not in self.spirit_profiles:
            self.spirit_profiles[spirit_id] = SpiritCorruptionProfile(
                spirit_id=spirit_id
            )

        profile = self.spirit_profiles[spirit_id]

        # The spirit's own resistance is handled by the Spirit.apply_corruption
        # method. This tracks the narrative/profile side.
        result["profile"] = profile
        result["source"] = source.value

        return result

    def attempt_purification(self, node_id: str,
                              method: PurificationMethod,
                              power: float,
                              bond: Optional["SpiritBond"] = None) -> dict:
        """
        Attempt to purify a corruption node.

        If using bond purification, the bonded spirit's element and
        mood affect effectiveness.
        """
        node = self.nodes.get(node_id)
        if not node:
            return {"success": False, "events": ["node_not_found"]}

        # Bond enhancement
        effective_power = power
        if bond and method == PurificationMethod.BOND_PURIFICATION:
            mood_mult = 0.5 + bond.mood.overall * 0.5
            level_mult = {
                "awareness": 0.3,
                "recognition": 0.5,
                "trust": 0.8,
                "partnership": 1.0,
                "unity": 1.5,
            }.get(bond.level.value, 0.5)
            effective_power *= mood_mult * level_mult

        result = node.attempt_purification(method, effective_power)
        self.total_purified += result.get("purified_amount", 0.0)

        # Update global metrics
        self._update_global_corruption()

        return result

    def update(self, delta: float, clock: "WorldClock") -> list[dict]:
        """
        Tick the entire corruption system forward.
        """
        events: list[dict] = []

        # Grow corruption nodes
        for node in self.nodes.values():
            if node.is_active:
                grow_result = node.grow(delta)
                events.extend(grow_result["events"])

        # MIRAIKAN extraction
        for site in self.extraction_sites.values():
            extract_result = site.extract(delta)
            self.total_energy_extracted += extract_result["energy_extracted"]

            # Feed corruption to connected node
            if site.corruption_node_id and extract_result["corruption_produced"] > 0:
                node = self.nodes.get(site.corruption_node_id)
                if node:
                    node.level = min(1.0, node.level + extract_result["corruption_produced"])

            events.extend(extract_result["events"])

        # Corruption spread between nodes
        events.extend(self._process_corruption_spread(delta))

        # Update the deeper wound
        deeper_result = self.deeper_corruption.update(delta, self.global_corruption)
        events.extend(deeper_result["events"])

        # Update global metrics
        self._update_global_corruption()

        # Update corrupted areas
        self._update_corrupted_areas()

        # Collect pending events
        events.extend(self.pending_events)
        self.pending_events.clear()

        return events

    def _process_corruption_spread(self, delta: float) -> list[dict]:
        """Corruption spreads from high-level nodes to nearby lower-level nodes."""
        events: list[dict] = []

        high_nodes = [n for n in self.nodes.values() if n.level >= 0.4]
        for source in high_nodes:
            for target in self.nodes.values():
                if target.node_id == source.node_id:
                    continue
                if target.district_id != source.district_id:
                    continue
                if target.level >= source.level:
                    continue

                spread_amount = source.level * 0.005 * delta
                old_stage = target.stage
                target.level = min(source.level * 0.8, target.level + spread_amount)
                new_stage = target.stage

                if new_stage != old_stage:
                    events.append({
                        "type": "corruption_spread_stage",
                        "from_node": source.node_id,
                        "to_node": target.node_id,
                        "new_stage": new_stage.value,
                    })

        return events

    def _update_global_corruption(self) -> None:
        """Recalculate global corruption metrics."""
        if not self.nodes:
            self.global_corruption = 0.0
            return

        active_nodes = [n for n in self.nodes.values() if n.is_active]
        if active_nodes:
            self.global_corruption = sum(n.level for n in active_nodes) / len(active_nodes)
        else:
            self.global_corruption = 0.0

        self.peak_corruption = max(self.peak_corruption, self.global_corruption)

    def _update_corrupted_areas(self) -> None:
        """Update the spatial representation of corrupted areas."""
        # Group active nodes by district
        by_district: dict[str, list[CorruptionNode]] = {}
        for node in self.nodes.values():
            if node.is_active:
                by_district.setdefault(node.district_id, []).append(node)

        for district_id, nodes in by_district.items():
            area_id = f"area_{district_id}"
            if area_id not in self.corrupted_areas:
                self.corrupted_areas[area_id] = CorruptedArea(
                    area_id=area_id,
                    center_location_id=nodes[0].location_id,
                    district_id=district_id,
                )

            area = self.corrupted_areas[area_id]
            area.corruption_nodes = [n.node_id for n in nodes]
            area.average_corruption = sum(n.level for n in nodes) / len(nodes)
            area.radius = max(n.spread_radius for n in nodes)

            # Update descriptions based on stage
            visuals = self.get_visuals_for(area.average_corruption)
            area.material_description = visuals.material_ambient
            area.spirit_description = visuals.spirit_ambient
