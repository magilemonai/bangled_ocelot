"""
Ma no Kuni - Recipe and Crafting System

A recipe is not a formula. It is a conversation between the crafter and the
materials, mediated by the spirits that dwell within. Grandmother says: "You
don't make tea. You invite the leaves to share their story."

Every recipe has a spirit negotiation phase. The outcome depends not only on
the materials and skill, but on the quality of attention the crafter brings.
This is where ma - the quality of the pause, the depth of the listening -
determines whether you create something transcendent or something merely useful.
"""

from __future__ import annotations

import enum
import hashlib
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from src.crafting.materials import (
    ElementAffinity,
    Material,
    MaterialRegistry,
    MaterialStack,
    Rarity,
)


class CraftingCategory(enum.Enum):
    """The branches of making in Ma no Kuni."""
    OFUDA = "ofuda"                # Spirit talismans
    SPIRIT_CHARM = "spirit_charm"  # Accessories with spirit power
    TEA_BLEND = "tea_blend"        # Grandmother's art
    INK_BRUSHWORK = "ink_brushwork"  # Spirit calligraphy
    REPAIR = "repair"              # Mending the broken
    GIFT = "gift"                  # For building bonds


class DiscoveryMethod(enum.Enum):
    """How Aoi learns a recipe."""
    WORLD_FIND = "world_find"          # Found written somewhere in the world
    NPC_TAUGHT = "npc_taught"          # An NPC teaches it directly
    SPIRIT_TAUGHT = "spirit_taught"    # A spirit shares the knowledge
    EXPERIMENTATION = "experimentation"  # Discovered by combining materials
    QUEST_REWARD = "quest_reward"      # Earned through a quest
    INNATE = "innate"                  # Known from the start


class CraftingOutcome(enum.Enum):
    """The possible results of a crafting attempt."""
    SUCCESS = "success"
    GREAT_SUCCESS = "great_success"  # Exceptional result, bonus effects
    CURIOUS = "curious"              # Failed, but produced something unexpected
    FAILURE = "failure"              # Nothing produced, materials preserved


@dataclass(frozen=True)
class MaterialRequirement:
    """A single material requirement for a recipe."""
    material_id: str
    quantity: int = 1

    def is_satisfied_by(self, stacks: dict[str, MaterialStack]) -> bool:
        """Check if this requirement is met by available materials."""
        stack = stacks.get(self.material_id)
        if stack is None:
            return False
        return stack.quantity >= self.quantity


@dataclass(frozen=True)
class CraftingCondition:
    """
    An optional condition that must be met for a recipe to be attempted.
    These represent the spiritual requirements of crafting - the right time,
    the right place, the right company.
    """
    time_of_day: Optional[tuple[str, ...]] = None
    season: Optional[tuple[str, ...]] = None
    location: Optional[str] = None
    required_companion: Optional[str] = None
    min_ma: float = 0.0
    moon_phase: Optional[tuple[str, ...]] = None
    weather: Optional[str] = None
    story_flag: Optional[str] = None


@dataclass(frozen=True)
class CuriousItemTemplate:
    """
    When crafting fails, the spirits sometimes leave surprises. A curious item
    is unpredictable - it might be useless, or it might be extraordinary.
    """
    name_prefix: str = "Curious"
    possible_effects: tuple[str, ...] = (
        "glows_faintly",
        "hums_when_held",
        "attracts_small_spirits",
        "changes_color_at_dusk",
        "smells_of_memory",
        "warm_to_touch",
        "whispers_in_dreams",
        "dissolves_in_moonlight",
    )


@dataclass(frozen=True)
class Recipe:
    """
    A crafting recipe. The instructions are guidelines; the spirits decide
    the rest.
    """
    id: str
    name: str
    description: str
    category: CraftingCategory
    materials: tuple[MaterialRequirement, ...]
    min_spirit_affinity: int  # Minimum skill level required
    result_item_id: str
    result_quantity: int = 1
    crafting_time: float = 1.0  # In-game time cost (hours)
    flavor_text: str = ""  # What happens during the crafting process
    discovery_method: DiscoveryMethod = DiscoveryMethod.WORLD_FIND
    conditions: CraftingCondition = field(default_factory=CraftingCondition)
    base_success_rate: float = 0.85
    great_success_rate: float = 0.10
    curious_item_rate: float = 0.60  # Chance of curious item on failure
    teaches_recipe: Optional[str] = None  # Learning this unlocks another
    lore: str = ""
    tags: tuple[str, ...] = ()

    @property
    def is_tea_recipe(self) -> bool:
        return self.category == CraftingCategory.TEA_BLEND

    @property
    def requires_companion(self) -> bool:
        return self.conditions.required_companion is not None

    @property
    def is_conditional(self) -> bool:
        """Does this recipe have any special conditions beyond materials?"""
        c = self.conditions
        return any([
            c.time_of_day,
            c.season,
            c.location,
            c.required_companion,
            c.min_ma > 0.0,
            c.moon_phase,
            c.weather,
            c.story_flag,
        ])

    def material_ids(self) -> frozenset[str]:
        """Return the set of material IDs used in this recipe."""
        return frozenset(req.material_id for req in self.materials)


@dataclass
class CraftingAttemptResult:
    """The result of attempting to craft something."""
    outcome: CraftingOutcome
    recipe: Recipe
    produced_item_id: Optional[str] = None
    produced_quantity: int = 0
    curious_effects: tuple[str, ...] = ()
    narrative: str = ""  # The story of what happened during crafting
    ma_gained: float = 0.0
    spirit_affinity_gained: float = 0.0

    @property
    def succeeded(self) -> bool:
        return self.outcome in (CraftingOutcome.SUCCESS, CraftingOutcome.GREAT_SUCCESS)


@dataclass
class CrafterProfile:
    """
    The crafter's skill and knowledge. Aoi grows as a crafter not by
    grinding, but by paying attention.
    """
    spirit_affinity: int = 1  # Skill level, grows with practice and story
    discovered_recipes: set[str] = field(default_factory=set)
    crafting_history: list[str] = field(default_factory=list)  # Recipe IDs
    total_crafted: int = 0
    total_great_successes: int = 0
    total_curious_items: int = 0
    tea_ceremonies_performed: int = 0
    favorite_materials: dict[str, int] = field(default_factory=dict)  # usage count

    def has_recipe(self, recipe_id: str) -> bool:
        return recipe_id in self.discovered_recipes

    def discover_recipe(self, recipe_id: str) -> bool:
        """Learn a new recipe. Returns True if it was actually new."""
        if recipe_id in self.discovered_recipes:
            return False
        self.discovered_recipes.add(recipe_id)
        return True

    def record_crafting(self, recipe: Recipe, outcome: CraftingOutcome) -> None:
        """Record a crafting attempt in history."""
        self.crafting_history.append(recipe.id)
        self.total_crafted += 1

        if outcome == CraftingOutcome.GREAT_SUCCESS:
            self.total_great_successes += 1
        elif outcome == CraftingOutcome.CURIOUS:
            self.total_curious_items += 1

        if recipe.is_tea_recipe:
            self.tea_ceremonies_performed += 1

        for req in recipe.materials:
            count = self.favorite_materials.get(req.material_id, 0)
            self.favorite_materials[req.material_id] = count + req.quantity

    def affinity_bonus(self, recipe: Recipe) -> float:
        """
        Bonus from over-leveling a recipe. Experience brings grace.
        Caps at 0.15 so there's always a whisper of uncertainty.
        """
        level_diff = self.spirit_affinity - recipe.min_spirit_affinity
        if level_diff <= 0:
            return 0.0
        return min(0.15, level_diff * 0.03)

    def familiarity_bonus(self, recipe: Recipe) -> float:
        """
        Repeated crafting builds familiarity. The spirits remember
        a respectful crafter.
        """
        times_crafted = self.crafting_history.count(recipe.id)
        if times_crafted == 0:
            return 0.0
        return min(0.10, times_crafted * 0.02)


class RecipeRegistry:
    """The collection of all known recipes in the game."""

    def __init__(self) -> None:
        self._recipes: dict[str, Recipe] = {}

    def register(self, recipe: Recipe) -> None:
        if recipe.id in self._recipes:
            raise ValueError(f"Recipe '{recipe.id}' is already registered")
        self._recipes[recipe.id] = recipe

    def get(self, recipe_id: str) -> Optional[Recipe]:
        return self._recipes.get(recipe_id)

    def require(self, recipe_id: str) -> Recipe:
        recipe = self._recipes.get(recipe_id)
        if recipe is None:
            raise KeyError(f"Unknown recipe: '{recipe_id}'")
        return recipe

    def find_by_category(self, category: CraftingCategory) -> list[Recipe]:
        return [r for r in self._recipes.values() if r.category == category]

    def find_by_material(self, material_id: str) -> list[Recipe]:
        """Find all recipes that use a specific material."""
        return [
            r for r in self._recipes.values()
            if any(req.material_id == material_id for req in r.materials)
        ]

    def find_discoverable_by_experimentation(
        self,
        available_material_ids: frozenset[str],
        crafter: CrafterProfile,
    ) -> list[Recipe]:
        """
        Find recipes that could be discovered by experimenting with
        currently held materials. Only returns undiscovered recipes
        whose discovery method is experimentation.
        """
        results = []
        for recipe in self._recipes.values():
            if recipe.id in crafter.discovered_recipes:
                continue
            if recipe.discovery_method != DiscoveryMethod.EXPERIMENTATION:
                continue
            if recipe.material_ids().issubset(available_material_ids):
                results.append(recipe)
        return results

    @property
    def tea_recipes(self) -> list[Recipe]:
        return self.find_by_category(CraftingCategory.TEA_BLEND)

    @property
    def all_recipes(self) -> list[Recipe]:
        return list(self._recipes.values())

    def __len__(self) -> int:
        return len(self._recipes)

    def __contains__(self, recipe_id: str) -> bool:
        return recipe_id in self._recipes


def _generate_curious_item_id(recipe: Recipe, seed: int) -> str:
    """Generate a deterministic but unpredictable curious item ID."""
    h = hashlib.sha256(f"{recipe.id}:{seed}".encode()).hexdigest()[:8]
    return f"curious_{recipe.category.value}_{h}"


def calculate_success_chance(
    recipe: Recipe,
    crafter: CrafterProfile,
    current_ma: float = 0.0,
    spirit_permeability: float = 0.3,
) -> dict[str, float]:
    """
    Calculate the probability distribution for crafting outcomes.

    Ma level and spirit permeability shift the odds. A crafter who is
    present and attentive in a spiritually active moment will produce
    extraordinary results.
    """
    if crafter.spirit_affinity < recipe.min_spirit_affinity:
        return {
            "success": 0.0,
            "great_success": 0.0,
            "curious": recipe.curious_item_rate,
            "failure": 1.0,
        }

    base = recipe.base_success_rate
    base += crafter.affinity_bonus(recipe)
    base += crafter.familiarity_bonus(recipe)

    # Ma bonus: being present and attentive helps crafting
    ma_bonus = min(0.10, current_ma / 1000.0)
    base += ma_bonus

    # Spirit permeability affects spiritual recipes more
    if recipe.category in (
        CraftingCategory.OFUDA,
        CraftingCategory.SPIRIT_CHARM,
        CraftingCategory.INK_BRUSHWORK,
    ):
        spirit_bonus = spirit_permeability * 0.05
        base += spirit_bonus

    # Tea recipes benefit from calm and practice
    if recipe.is_tea_recipe:
        tea_bonus = min(0.10, crafter.tea_ceremonies_performed * 0.005)
        base += tea_bonus

    success_rate = min(0.98, base)  # Never 100% - spirits are unpredictable
    great_rate = recipe.great_success_rate + (ma_bonus * 0.5)
    great_rate = min(great_rate, success_rate * 0.3)
    normal_success = success_rate - great_rate
    failure_rate = 1.0 - success_rate
    curious_rate = failure_rate * recipe.curious_item_rate

    return {
        "success": round(normal_success, 4),
        "great_success": round(great_rate, 4),
        "curious": round(curious_rate, 4),
        "failure": round(failure_rate - curious_rate, 4),
    }


def resolve_crafting_outcome(
    recipe: Recipe,
    crafter: CrafterProfile,
    current_ma: float = 0.0,
    spirit_permeability: float = 0.3,
    rng: Optional[random.Random] = None,
) -> CraftingOutcome:
    """
    Roll the dice. But the dice are spirit bones, and they have opinions.
    """
    if rng is None:
        rng = random.Random()

    chances = calculate_success_chance(
        recipe, crafter, current_ma, spirit_permeability
    )

    roll = rng.random()
    cumulative = 0.0

    for outcome_name, probability in [
        ("great_success", chances["great_success"]),
        ("success", chances["success"]),
        ("curious", chances["curious"]),
        ("failure", chances["failure"]),
    ]:
        cumulative += probability
        if roll < cumulative:
            return CraftingOutcome(outcome_name)

    # Floating point edge case - default to normal success
    return CraftingOutcome.SUCCESS


def _parse_category(raw: str) -> CraftingCategory:
    return CraftingCategory(raw.lower())


def _parse_discovery(raw: str) -> DiscoveryMethod:
    return DiscoveryMethod(raw.lower())


def _parse_conditions(raw: dict) -> CraftingCondition:
    if not raw:
        return CraftingCondition()
    return CraftingCondition(
        time_of_day=tuple(raw["time_of_day"]) if raw.get("time_of_day") else None,
        season=tuple(raw["season"]) if raw.get("season") else None,
        location=raw.get("location"),
        required_companion=raw.get("required_companion"),
        min_ma=float(raw.get("min_ma", 0.0)),
        moon_phase=tuple(raw["moon_phase"]) if raw.get("moon_phase") else None,
        weather=raw.get("weather"),
        story_flag=raw.get("story_flag"),
    )


def load_recipes_from_yaml(path: str | Path) -> RecipeRegistry:
    """
    Load recipe definitions from a YAML file.

    The YAML file should contain a top-level 'recipes' key with a list
    of recipe definitions.
    """
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    registry = RecipeRegistry()

    for entry in data.get("recipes", []):
        materials = tuple(
            MaterialRequirement(
                material_id=m["material_id"],
                quantity=int(m.get("quantity", 1)),
            )
            for m in entry.get("materials", [])
        )

        conditions = _parse_conditions(entry.get("conditions", {}))

        recipe = Recipe(
            id=entry["id"],
            name=entry["name"],
            description=entry["description"],
            category=_parse_category(entry["category"]),
            materials=materials,
            min_spirit_affinity=int(entry.get("min_spirit_affinity", 1)),
            result_item_id=entry["result_item_id"],
            result_quantity=int(entry.get("result_quantity", 1)),
            crafting_time=float(entry.get("crafting_time", 1.0)),
            flavor_text=entry.get("flavor_text", ""),
            discovery_method=_parse_discovery(
                entry.get("discovery_method", "world_find")
            ),
            conditions=conditions,
            base_success_rate=float(entry.get("base_success_rate", 0.85)),
            great_success_rate=float(entry.get("great_success_rate", 0.10)),
            curious_item_rate=float(entry.get("curious_item_rate", 0.60)),
            teaches_recipe=entry.get("teaches_recipe"),
            lore=entry.get("lore", ""),
            tags=tuple(entry.get("tags", [])),
        )
        registry.register(recipe)

    return registry
