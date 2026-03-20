"""
Ma no Kuni - Material System

Materials in Ma no Kuni are not inert. Every piece of wood remembers the tree
it came from. Every shard of glass holds a sliver of the window's view. Every
thread of spirit essence hums with the memory of what it once was.

To craft is to listen. To listen is to understand. To understand is to create
something that neither world could produce alone.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


class MaterialType(enum.Enum):
    """The four natures of matter in a world where spirits walk."""
    NATURAL = "natural"
    URBAN = "urban"
    SPIRITUAL = "spiritual"
    HYBRID = "hybrid"


class ElementAffinity(enum.Enum):
    """
    Elemental affinities drawn from Shinto cosmology and the reality of
    a living, breathing Tokyo. Not classical elements - these are the
    forces that shape the space between worlds.
    """
    FIRE = "fire"           # Purification, passion, destruction
    WATER = "water"         # Memory, flow, adaptation
    WIND = "wind"           # Change, messages, freedom
    EARTH = "earth"         # Stability, tradition, endurance
    VOID = "void"           # The space between, ma itself
    LIGHT = "light"         # Revelation, truth, dawn
    SHADOW = "shadow"       # Concealment, dreams, dusk
    LIGHTNING = "lightning"  # Shock, connection, the urban pulse


class Rarity(enum.Enum):
    """How rare a material is, and how much the world values it."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    VERY_RARE = "very_rare"
    LEGENDARY = "legendary"


class GatherMethod(enum.Enum):
    """How materials enter the player's hands."""
    EXPLORATION = "exploration"
    COMBAT_DROP = "combat_drop"
    NPC_GIFT = "npc_gift"
    PURCHASE = "purchase"
    SPIRIT_OFFERING = "spirit_offering"
    SEASONAL_EVENT = "seasonal_event"
    QUEST_REWARD = "quest_reward"
    TEA_CEREMONY = "tea_ceremony"


@dataclass(frozen=True)
class Material:
    """
    A single material. Frozen because a material's essence does not change -
    what changes is how you understand it.
    """
    id: str
    name: str
    description: str
    material_type: MaterialType
    spirit_resonance: float  # 0.0 to 1.0 - how well it channels spirit energy
    element_affinity: ElementAffinity
    rarity: Rarity
    source_districts: tuple[str, ...]
    lore: str
    gather_methods: tuple[GatherMethod, ...] = ()
    base_value: int = 10
    stackable: bool = True
    max_stack: int = 99
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.spirit_resonance <= 1.0:
            raise ValueError(
                f"Spirit resonance must be between 0.0 and 1.0, "
                f"got {self.spirit_resonance} for material '{self.id}'"
            )

    @property
    def is_spirit_conductive(self) -> bool:
        """Materials with high resonance can channel spirit energy directly."""
        return self.spirit_resonance >= 0.7

    @property
    def is_spiritually_inert(self) -> bool:
        """Some materials resist spiritual influence entirely."""
        return self.spirit_resonance < 0.1

    def resonance_compatibility(self, other: Material) -> float:
        """
        How well two materials harmonize when combined. Materials of opposing
        elements but similar resonance can produce the most powerful results -
        and the most unpredictable failures.
        """
        resonance_diff = abs(self.spirit_resonance - other.spirit_resonance)
        resonance_avg = (self.spirit_resonance + other.spirit_resonance) / 2.0

        # Similar resonance levels harmonize well
        harmony = 1.0 - resonance_diff

        # Opposing elements create tension that can be channeled
        opposing_pairs = {
            (ElementAffinity.FIRE, ElementAffinity.WATER),
            (ElementAffinity.WIND, ElementAffinity.EARTH),
            (ElementAffinity.LIGHT, ElementAffinity.SHADOW),
            (ElementAffinity.VOID, ElementAffinity.LIGHTNING),
        }
        pair = frozenset((self.element_affinity, other.element_affinity))
        if pair in {frozenset(p) for p in opposing_pairs}:
            # Opposing elements are volatile but powerful
            harmony *= 0.7
            harmony += resonance_avg * 0.4

        return max(0.0, min(1.0, harmony))


@dataclass
class MaterialStack:
    """A stack of materials in inventory. Mutable - quantities change."""
    material: Material
    quantity: int = 1

    def __post_init__(self) -> None:
        if self.quantity < 0:
            raise ValueError("Material quantity cannot be negative")
        if self.material.stackable and self.quantity > self.material.max_stack:
            raise ValueError(
                f"Quantity {self.quantity} exceeds max stack "
                f"{self.material.max_stack} for '{self.material.id}'"
            )

    def consume(self, amount: int) -> bool:
        """Attempt to consume materials. Returns True if sufficient quantity."""
        if amount > self.quantity:
            return False
        self.quantity -= amount
        return True

    @property
    def is_empty(self) -> bool:
        return self.quantity <= 0


class MaterialRegistry:
    """
    The registry of all known materials. In-world, this is Aoi's understanding
    of the substances she encounters - growing as she explores and learns.
    """

    def __init__(self) -> None:
        self._materials: dict[str, Material] = {}

    def register(self, material: Material) -> None:
        """Register a material definition."""
        if material.id in self._materials:
            raise ValueError(f"Material '{material.id}' is already registered")
        self._materials[material.id] = material

    def get(self, material_id: str) -> Optional[Material]:
        """Look up a material by ID."""
        return self._materials.get(material_id)

    def require(self, material_id: str) -> Material:
        """Look up a material by ID, raising if not found."""
        material = self._materials.get(material_id)
        if material is None:
            raise KeyError(f"Unknown material: '{material_id}'")
        return material

    def find_by_type(self, material_type: MaterialType) -> list[Material]:
        """Find all materials of a given type."""
        return [
            m for m in self._materials.values()
            if m.material_type == material_type
        ]

    def find_by_element(self, element: ElementAffinity) -> list[Material]:
        """Find all materials with a given elemental affinity."""
        return [
            m for m in self._materials.values()
            if m.element_affinity == element
        ]

    def find_by_district(self, district: str) -> list[Material]:
        """Find all materials available in a given district."""
        return [
            m for m in self._materials.values()
            if district in m.source_districts
        ]

    def find_by_tag(self, tag: str) -> list[Material]:
        """Find all materials with a given tag."""
        return [
            m for m in self._materials.values()
            if tag in m.tags
        ]

    @property
    def all_materials(self) -> list[Material]:
        return list(self._materials.values())

    def __len__(self) -> int:
        return len(self._materials)

    def __contains__(self, material_id: str) -> bool:
        return material_id in self._materials


def _parse_material_type(raw: str) -> MaterialType:
    return MaterialType(raw.lower())


def _parse_element(raw: str) -> ElementAffinity:
    return ElementAffinity(raw.lower())


def _parse_rarity(raw: str) -> Rarity:
    return Rarity(raw.lower())


def _parse_gather_methods(raw: list[str]) -> tuple[GatherMethod, ...]:
    return tuple(GatherMethod(m.lower()) for m in raw)


def load_materials_from_yaml(path: str | Path) -> MaterialRegistry:
    """
    Load material definitions from a YAML file and populate a registry.

    The YAML file should contain a top-level 'materials' key with a list
    of material definitions.
    """
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    registry = MaterialRegistry()

    for entry in data.get("materials", []):
        material = Material(
            id=entry["id"],
            name=entry["name"],
            description=entry["description"],
            material_type=_parse_material_type(entry["material_type"]),
            spirit_resonance=float(entry["spirit_resonance"]),
            element_affinity=_parse_element(entry["element_affinity"]),
            rarity=_parse_rarity(entry["rarity"]),
            source_districts=tuple(entry.get("source_districts", [])),
            lore=entry.get("lore", ""),
            gather_methods=_parse_gather_methods(entry.get("gather_methods", [])),
            base_value=int(entry.get("base_value", 10)),
            stackable=bool(entry.get("stackable", True)),
            max_stack=int(entry.get("max_stack", 99)),
            tags=tuple(entry.get("tags", [])),
        )
        registry.register(material)

    return registry
