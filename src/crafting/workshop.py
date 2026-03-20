"""
Ma no Kuni - Crafting Workshop

The workshop is not a place. It is a state of being.

Grandmother's kitchen table with its chipped teapot and worn cloth. A park
bench at dusk where the light is just so. The counter of a convenience store
where the night clerk is secretly a tanuki. Any place can become a workshop
when the crafter brings attention and the spirits bring willingness.

This module handles the interface between the player and the crafting system -
validating conditions, consuming materials, resolving outcomes, and narrating
the quiet drama of making things that matter.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional, Protocol

from src.crafting.materials import (
    Material,
    MaterialRegistry,
    MaterialStack,
)
from src.crafting.recipes import (
    CrafterProfile,
    CraftingAttemptResult,
    CraftingCategory,
    CraftingOutcome,
    CuriousItemTemplate,
    Recipe,
    RecipeRegistry,
    calculate_success_chance,
    resolve_crafting_outcome,
    _generate_curious_item_id,
)


class WorldStateProvider(Protocol):
    """
    Protocol for accessing the current world state. The workshop needs to
    know the time, the season, where we are, and how the spirits are feeling.
    """

    @property
    def time_of_day(self) -> str: ...

    @property
    def season(self) -> str: ...

    @property
    def current_location(self) -> str: ...

    @property
    def current_district(self) -> str: ...

    @property
    def spirit_permeability(self) -> float: ...

    @property
    def current_ma(self) -> float: ...

    @property
    def moon_phase(self) -> str: ...

    @property
    def weather(self) -> str: ...

    def check_flag(self, flag: str) -> bool: ...

    @property
    def active_companion(self) -> Optional[str]: ...


@dataclass
class Inventory:
    """
    The player's material inventory. Each material is stored as a stack.
    """
    stacks: dict[str, MaterialStack] = field(default_factory=dict)

    def add_material(self, material: Material, quantity: int = 1) -> None:
        """Add materials to inventory."""
        if material.id in self.stacks:
            existing = self.stacks[material.id]
            new_qty = existing.quantity + quantity
            if material.stackable and new_qty > material.max_stack:
                raise ValueError(
                    f"Adding {quantity} '{material.id}' would exceed "
                    f"max stack of {material.max_stack}"
                )
            self.stacks[material.id] = MaterialStack(material, new_qty)
        else:
            self.stacks[material.id] = MaterialStack(material, quantity)

    def remove_material(self, material_id: str, quantity: int = 1) -> bool:
        """Remove materials from inventory. Returns False if insufficient."""
        stack = self.stacks.get(material_id)
        if stack is None or stack.quantity < quantity:
            return False
        stack.quantity -= quantity
        if stack.is_empty:
            del self.stacks[material_id]
        return True

    def has_material(self, material_id: str, quantity: int = 1) -> bool:
        stack = self.stacks.get(material_id)
        return stack is not None and stack.quantity >= quantity

    def get_quantity(self, material_id: str) -> int:
        stack = self.stacks.get(material_id)
        return stack.quantity if stack else 0

    @property
    def material_ids(self) -> frozenset[str]:
        return frozenset(self.stacks.keys())

    @property
    def total_items(self) -> int:
        return sum(s.quantity for s in self.stacks.values())


@dataclass
class ConditionCheckResult:
    """The result of checking whether crafting conditions are met."""
    satisfied: bool
    missing_materials: list[tuple[str, int, int]] = field(default_factory=list)
    unmet_conditions: list[str] = field(default_factory=list)
    insufficient_skill: bool = False
    required_skill: int = 0
    current_skill: int = 0

    @property
    def summary(self) -> str:
        """A human-readable summary of why conditions aren't met."""
        if self.satisfied:
            return "All conditions are met. The spirits are willing."

        parts = []
        if self.insufficient_skill:
            parts.append(
                f"Spirit affinity too low (need {self.required_skill}, "
                f"have {self.current_skill})"
            )
        for mat_id, needed, have in self.missing_materials:
            parts.append(f"Need {needed} {mat_id} (have {have})")
        for condition in self.unmet_conditions:
            parts.append(condition)
        return "; ".join(parts)


class CraftingWorkshop:
    """
    The crafting workshop - where materials, spirits, and intention converge.

    This is the main interface for all crafting operations. It validates
    conditions, resolves outcomes, manages inventory, and generates the
    narrative of each crafting moment.
    """

    def __init__(
        self,
        material_registry: MaterialRegistry,
        recipe_registry: RecipeRegistry,
        crafter: CrafterProfile,
        inventory: Inventory,
        world: WorldStateProvider,
        rng: Optional[random.Random] = None,
    ) -> None:
        self._materials = material_registry
        self._recipes = recipe_registry
        self._crafter = crafter
        self._inventory = inventory
        self._world = world
        self._rng = rng or random.Random()
        self._curious_seed = 0

    # ------------------------------------------------------------------ #
    # Query methods
    # ------------------------------------------------------------------ #

    def available_recipes(self) -> list[Recipe]:
        """
        Return all recipes the crafter knows and currently has materials for.
        Does not check conditions like time of day - those are checked at
        craft time, because the player should know what they could make
        if circumstances were different.
        """
        results = []
        for recipe_id in sorted(self._crafter.discovered_recipes):
            recipe = self._recipes.get(recipe_id)
            if recipe is None:
                continue
            if self._has_materials_for(recipe):
                results.append(recipe)
        return results

    def all_known_recipes(self) -> list[Recipe]:
        """Return all recipes the crafter has discovered, regardless of materials."""
        results = []
        for recipe_id in sorted(self._crafter.discovered_recipes):
            recipe = self._recipes.get(recipe_id)
            if recipe is not None:
                results.append(recipe)
        return results

    def recipes_by_category(self, category: CraftingCategory) -> list[Recipe]:
        """Return known recipes filtered by category."""
        return [
            r for r in self.all_known_recipes()
            if r.category == category
        ]

    def tea_recipes(self) -> list[Recipe]:
        """
        Grandmother's tea recipes. A special category displayed with
        extra warmth and care in the UI.
        """
        return self.recipes_by_category(CraftingCategory.TEA_BLEND)

    def check_conditions(self, recipe: Recipe) -> ConditionCheckResult:
        """
        Thoroughly check all conditions for a crafting attempt.
        Returns a detailed result explaining what is and isn't met.
        """
        result = ConditionCheckResult(satisfied=True)

        # Check skill level
        if self._crafter.spirit_affinity < recipe.min_spirit_affinity:
            result.satisfied = False
            result.insufficient_skill = True
            result.required_skill = recipe.min_spirit_affinity
            result.current_skill = self._crafter.spirit_affinity

        # Check materials
        for req in recipe.materials:
            have = self._inventory.get_quantity(req.material_id)
            if have < req.quantity:
                result.satisfied = False
                result.missing_materials.append(
                    (req.material_id, req.quantity, have)
                )

        # Check world conditions
        cond = recipe.conditions

        if cond.time_of_day and self._world.time_of_day not in cond.time_of_day:
            result.satisfied = False
            times = ", ".join(cond.time_of_day)
            result.unmet_conditions.append(
                f"Must be crafted during: {times} "
                f"(currently {self._world.time_of_day})"
            )

        if cond.season and self._world.season not in cond.season:
            result.satisfied = False
            seasons = ", ".join(cond.season)
            result.unmet_conditions.append(
                f"Must be crafted during: {seasons} "
                f"(currently {self._world.season})"
            )

        if cond.location and self._world.current_location != cond.location:
            result.satisfied = False
            result.unmet_conditions.append(
                f"Must be crafted at: {cond.location}"
            )

        if cond.required_companion:
            if self._world.active_companion != cond.required_companion:
                result.satisfied = False
                result.unmet_conditions.append(
                    f"Requires companion: {cond.required_companion}"
                )

        if cond.min_ma > 0.0 and self._world.current_ma < cond.min_ma:
            result.satisfied = False
            result.unmet_conditions.append(
                f"Requires ma level of {cond.min_ma:.0f} "
                f"(currently {self._world.current_ma:.0f})"
            )

        if cond.moon_phase and self._world.moon_phase not in cond.moon_phase:
            result.satisfied = False
            phases = ", ".join(cond.moon_phase)
            result.unmet_conditions.append(
                f"Requires moon phase: {phases} "
                f"(currently {self._world.moon_phase})"
            )

        if cond.story_flag and not self._world.check_flag(cond.story_flag):
            result.satisfied = False
            result.unmet_conditions.append(
                "A prerequisite has not yet been fulfilled"
            )

        return result

    def preview_chances(self, recipe: Recipe) -> dict[str, float]:
        """
        Preview the success chances for a recipe without attempting it.
        The crafter can feel the spirits' mood before committing.
        """
        return calculate_success_chance(
            recipe,
            self._crafter,
            current_ma=self._world.current_ma,
            spirit_permeability=self._world.spirit_permeability,
        )

    # ------------------------------------------------------------------ #
    # Crafting execution
    # ------------------------------------------------------------------ #

    def craft(self, recipe_id: str) -> CraftingAttemptResult:
        """
        Attempt to craft a recipe. The main entry point for all crafting.

        On failure, materials are preserved - the spirits are disappointed
        but not vindictive. However, a 'curious' outcome consumes materials
        and produces something unexpected.
        """
        recipe = self._recipes.require(recipe_id)

        # Validate all conditions
        check = self.check_conditions(recipe)
        if not check.satisfied:
            return CraftingAttemptResult(
                outcome=CraftingOutcome.FAILURE,
                recipe=recipe,
                narrative=f"Cannot craft: {check.summary}",
            )

        # Resolve the outcome
        outcome = resolve_crafting_outcome(
            recipe,
            self._crafter,
            current_ma=self._world.current_ma,
            spirit_permeability=self._world.spirit_permeability,
            rng=self._rng,
        )

        # Build the result
        result = self._resolve_outcome(recipe, outcome)

        # Record in crafter profile
        self._crafter.record_crafting(recipe, outcome)

        # Check for recipe chain unlocks
        if result.succeeded and recipe.teaches_recipe:
            self._crafter.discover_recipe(recipe.teaches_recipe)

        return result

    def attempt_experimentation(
        self,
        material_ids: list[str],
    ) -> Optional[CraftingAttemptResult]:
        """
        Try combining materials without a known recipe. If the combination
        matches an undiscovered experimental recipe, discover and attempt it.
        Otherwise, the materials shimmer briefly and settle back down.

        Materials are never consumed by failed experimentation.
        """
        available = frozenset(material_ids)
        candidates = self._recipes.find_discoverable_by_experimentation(
            available, self._crafter
        )

        if not candidates:
            return None

        # If multiple matches, pick the one with the most material overlap
        best = max(
            candidates,
            key=lambda r: len(r.material_ids() & available),
        )

        # Discover the recipe
        self._crafter.discover_recipe(best.id)

        # Attempt the craft
        return self.craft(best.id)

    def perform_tea_ceremony(self, recipe_id: str) -> CraftingAttemptResult:
        """
        A tea ceremony is crafting, but slower. More intimate. The flavor
        text is longer, the ma gain is higher, and grandmother's spirit
        is always nearby even when she is not.

        Mechanically identical to craft(), but with enhanced narrative
        and ma rewards.
        """
        recipe = self._recipes.require(recipe_id)
        if not recipe.is_tea_recipe:
            raise ValueError(
                f"Recipe '{recipe_id}' is not a tea recipe. "
                "The tea ceremony demands tea."
            )

        result = self.craft(recipe_id)

        # Tea ceremonies always grant some ma, even on failure
        if result.outcome == CraftingOutcome.FAILURE:
            result.ma_gained = 5.0
            result.narrative = (
                "The water doesn't quite reach the right temperature, and "
                "the leaves stay closed, keeping their secrets. But the act "
                "of trying - of sitting, of waiting, of hoping - that has "
                "its own quiet value. Grandmother would say: 'The tea that "
                "isn't made teaches as much as the tea that is.'"
            )
        elif result.outcome == CraftingOutcome.CURIOUS:
            result.ma_gained = 10.0
        elif result.outcome == CraftingOutcome.SUCCESS:
            result.ma_gained = 15.0
        elif result.outcome == CraftingOutcome.GREAT_SUCCESS:
            result.ma_gained = 25.0

        return result

    # ------------------------------------------------------------------ #
    # Discovery
    # ------------------------------------------------------------------ #

    def discover_recipe_from_npc(self, recipe_id: str, npc_name: str) -> bool:
        """An NPC or spirit teaches a recipe. Returns True if newly learned."""
        if recipe_id not in self._recipes:
            return False
        return self._crafter.discover_recipe(recipe_id)

    def discover_recipe_from_world(self, recipe_id: str) -> bool:
        """Found a recipe in the world - a scroll, a book, a wall inscription."""
        if recipe_id not in self._recipes:
            return False
        return self._crafter.discover_recipe(recipe_id)

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _has_materials_for(self, recipe: Recipe) -> bool:
        """Check if the inventory has all required materials."""
        return all(
            self._inventory.has_material(req.material_id, req.quantity)
            for req in recipe.materials
        )

    def _consume_materials(self, recipe: Recipe) -> None:
        """Consume all materials required by a recipe."""
        for req in recipe.materials:
            success = self._inventory.remove_material(
                req.material_id, req.quantity
            )
            if not success:
                raise RuntimeError(
                    f"Failed to consume {req.quantity} of '{req.material_id}' "
                    f"- inventory state is inconsistent"
                )

    def _resolve_outcome(
        self,
        recipe: Recipe,
        outcome: CraftingOutcome,
    ) -> CraftingAttemptResult:
        """Build the full result for a crafting outcome."""

        if outcome == CraftingOutcome.GREAT_SUCCESS:
            self._consume_materials(recipe)
            return CraftingAttemptResult(
                outcome=outcome,
                recipe=recipe,
                produced_item_id=recipe.result_item_id,
                produced_quantity=recipe.result_quantity + 1,
                narrative=self._narrate_great_success(recipe),
                spirit_affinity_gained=0.3,
            )

        if outcome == CraftingOutcome.SUCCESS:
            self._consume_materials(recipe)
            return CraftingAttemptResult(
                outcome=outcome,
                recipe=recipe,
                produced_item_id=recipe.result_item_id,
                produced_quantity=recipe.result_quantity,
                narrative=self._narrate_success(recipe),
                spirit_affinity_gained=0.1,
            )

        if outcome == CraftingOutcome.CURIOUS:
            self._consume_materials(recipe)
            self._curious_seed += 1
            curious_id = _generate_curious_item_id(recipe, self._curious_seed)
            template = CuriousItemTemplate()
            effects = tuple(
                self._rng.sample(
                    list(template.possible_effects),
                    k=min(2, len(template.possible_effects)),
                )
            )
            return CraftingAttemptResult(
                outcome=outcome,
                recipe=recipe,
                produced_item_id=curious_id,
                produced_quantity=1,
                curious_effects=effects,
                narrative=self._narrate_curious(recipe, effects),
                spirit_affinity_gained=0.15,
            )

        # FAILURE - materials are preserved
        return CraftingAttemptResult(
            outcome=outcome,
            recipe=recipe,
            narrative=self._narrate_failure(recipe),
            spirit_affinity_gained=0.05,
        )

    # ------------------------------------------------------------------ #
    # Narrative generation
    # ------------------------------------------------------------------ #

    def _narrate_success(self, recipe: Recipe) -> str:
        if recipe.flavor_text:
            return recipe.flavor_text
        return (
            f"The materials settle into their new form. {recipe.name} "
            f"takes shape under your hands, and for a moment you feel the "
            f"spirits within it hum with quiet approval."
        )

    def _narrate_great_success(self, recipe: Recipe) -> str:
        base = recipe.flavor_text or ""
        return (
            f"{base}\n\n"
            f"Something extraordinary happens. The spirits within the "
            f"materials don't just cooperate - they sing. The {recipe.name} "
            f"that emerges carries an extra measure of their blessing, "
            f"as if the space between worlds narrowed just for this moment."
        ).strip()

    def _narrate_curious(
        self, recipe: Recipe, effects: tuple[str, ...]
    ) -> str:
        effect_descriptions = {
            "glows_faintly": "gives off a faint, uncertain light",
            "hums_when_held": "vibrates with a barely audible tone",
            "attracts_small_spirits": "seems to draw tiny spirits to it like moths",
            "changes_color_at_dusk": "shifts color as the sun sets",
            "smells_of_memory": "carries the scent of something you can't quite place",
            "warm_to_touch": "stays warm no matter how cold the air",
            "whispers_in_dreams": "will find its way into your dreams tonight",
            "dissolves_in_moonlight": "seems to thin at the edges under moonlight",
        }
        described = [
            effect_descriptions.get(e, e) for e in effects
        ]
        joined = " and ".join(described)
        return (
            f"The crafting goes sideways - not wrong, exactly, but "
            f"somewhere the spirits took a detour. What emerges isn't "
            f"{recipe.name}, but something else entirely. It {joined}. "
            f"The spirits seem amused."
        )

    def _narrate_failure(self, recipe: Recipe) -> str:
        failure_lines = [
            (
                "The materials resist. Not with hostility, but with the quiet "
                "stubbornness of things that aren't ready to change. "
                "Everything returns to how it was."
            ),
            (
                "You feel the spirits withdraw, like a conversation that "
                "ended before it began. The materials sit unchanged, "
                "patient, waiting for next time."
            ),
            (
                "Something doesn't align. The resonance wavers and fades "
                "like a radio station drifting out of range. Your materials "
                "remain untouched."
            ),
            (
                "The space between intention and creation stays empty this "
                "time. The spirits are quiet - not angry, just... elsewhere. "
                "Your materials are safe."
            ),
        ]
        return self._rng.choice(failure_lines)
