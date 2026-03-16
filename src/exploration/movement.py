"""
Ma no Kuni - Movement and Collision System

Grid-based traversal through Tokyo's layered reality. Every step matters:
running scares the spirits and burns away your stillness, while sneaking
draws them close. And in Spirit Vision, the city peels open to show
what has always been there, waiting in the spaces between.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MovementMode(Enum):
    """How the player moves shapes what the world reveals."""
    WALKING = "walking"       # Normal pace - balanced encounters
    RUNNING = "running"       # Fast - scares spirits, decays ma quickly
    SNEAKING = "sneaking"     # Slow - better spirit encounters, builds ma

    @property
    def speed_multiplier(self) -> float:
        return _MODE_SPEED[self]

    @property
    def ma_decay_multiplier(self) -> float:
        return _MODE_MA_DECAY[self]

    @property
    def spirit_encounter_modifier(self) -> float:
        """Positive means more/better encounters, negative means fewer."""
        return _MODE_SPIRIT_MOD[self]

    @property
    def noise_level(self) -> float:
        """0.0 = silent, 1.0 = very loud. Spirits flee from noise."""
        return _MODE_NOISE[self]


_MODE_SPEED: dict[MovementMode, float] = {
    MovementMode.WALKING: 1.0,
    MovementMode.RUNNING: 2.0,
    MovementMode.SNEAKING: 0.5,
}

_MODE_MA_DECAY: dict[MovementMode, float] = {
    MovementMode.WALKING: 1.0,
    MovementMode.RUNNING: 3.0,
    MovementMode.SNEAKING: 0.3,
}

_MODE_SPIRIT_MOD: dict[MovementMode, float] = {
    MovementMode.WALKING: 0.0,
    MovementMode.RUNNING: -0.4,
    MovementMode.SNEAKING: 0.3,
}

_MODE_NOISE: dict[MovementMode, float] = {
    MovementMode.WALKING: 0.3,
    MovementMode.RUNNING: 0.9,
    MovementMode.SNEAKING: 0.05,
}


class Direction(Enum):
    """Cardinal and ordinal directions on the tile grid."""
    NORTH = (0, -1)
    SOUTH = (0, 1)
    EAST = (1, 0)
    WEST = (-1, 0)
    NORTHEAST = (1, -1)
    NORTHWEST = (-1, -1)
    SOUTHEAST = (1, 1)
    SOUTHWEST = (-1, 1)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]

    @property
    def opposite(self) -> Direction:
        return _OPPOSITES[self]

    @property
    def is_diagonal(self) -> bool:
        return abs(self.value[0]) + abs(self.value[1]) == 2


_OPPOSITES: dict[Direction, Direction] = {}  # populated after class definition


def _build_opposites() -> None:
    pairs = [
        (Direction.NORTH, Direction.SOUTH),
        (Direction.EAST, Direction.WEST),
        (Direction.NORTHEAST, Direction.SOUTHWEST),
        (Direction.NORTHWEST, Direction.SOUTHEAST),
    ]
    for a, b in pairs:
        _OPPOSITES[a] = b
        _OPPOSITES[b] = a


_build_opposites()


class TileType(Enum):
    """What occupies a tile affects movement and interactions."""
    FLOOR = auto()            # Normal walkable ground
    WALL = auto()             # Impassable barrier
    WATER = auto()            # Impassable (unless spirit ability)
    SPIRIT_FLOOR = auto()     # Only visible/walkable in Spirit Vision
    SPIRIT_WALL = auto()      # Only blocks movement in Spirit Vision
    DOOR = auto()             # Transition between areas
    STAIRS = auto()           # Transition between floors
    INTERACTIVE = auto()      # Object that can be examined/used
    NPC = auto()              # A character occupying a tile
    HAZARD = auto()           # Damaging tile (spiritual or physical)
    TORII_GATE = auto()       # Spirit fast-travel node
    SAVE_POINT = auto()       # Jizo statue save points


class InteractionType(Enum):
    """What can the player do with nearby objects?"""
    EXAMINE = "examine"
    TALK = "talk"
    PICK_UP = "pick_up"
    USE = "use"
    OPEN = "open"
    PUSH = "push"
    PRAY = "pray"             # At shrines and jizo statues
    LISTEN = "listen"         # Hear spirit whispers, accumulates ma
    SIT = "sit"               # Rest, accumulate ma, trigger vignettes


# ---------------------------------------------------------------------------
# Core data structures
# ---------------------------------------------------------------------------

@dataclass
class TileCoord:
    """A position on the tile grid."""
    x: int
    y: int

    def offset(self, direction: Direction) -> TileCoord:
        return TileCoord(self.x + direction.dx, self.y + direction.dy)

    def manhattan_distance(self, other: TileCoord) -> int:
        return abs(self.x - other.x) + abs(self.y - other.y)

    def chebyshev_distance(self, other: TileCoord) -> int:
        return max(abs(self.x - other.x), abs(self.y - other.y))

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TileCoord):
            return NotImplemented
        return self.x == other.x and self.y == other.y


@dataclass
class Tile:
    """
    A single cell in the world grid. Tiles exist in both the material
    and spirit layers simultaneously.
    """
    tile_type: TileType = TileType.FLOOR
    spirit_tile_type: Optional[TileType] = None  # Overlay in Spirit Vision
    walkable: bool = True
    spirit_walkable: Optional[bool] = None       # None = same as walkable
    interaction: Optional[InteractionType] = None
    interaction_id: Optional[str] = None          # Links to game data
    discovery_id: Optional[str] = None            # Hidden discovery on this tile
    event_trigger: Optional[str] = None           # Event ID triggered on step
    elevation: int = 0                            # For vertical layering
    spirit_energy: float = 0.0                    # Ambient spirit energy
    metadata: dict = field(default_factory=dict)

    @property
    def effective_spirit_walkable(self) -> bool:
        if self.spirit_walkable is not None:
            return self.spirit_walkable
        return self.walkable


@dataclass
class TileMap:
    """
    A 2D grid of tiles representing one area of Tokyo. Each map has
    both a material layer and a spirit layer that can diverge.
    """
    map_id: str
    name: str
    district: str
    width: int
    height: int
    tiles: dict[tuple[int, int], Tile] = field(default_factory=dict)
    connections: list[MapConnection] = field(default_factory=list)
    ambient_spirit_energy: float = 0.0
    indoor: bool = False
    description: str = ""

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        return self.tiles.get((x, y))

    def set_tile(self, x: int, y: int, tile: Tile) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[(x, y)] = tile

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x: int, y: int, spirit_vision: bool = False) -> bool:
        """Check if a tile can be walked on, considering spirit vision state."""
        if not self.in_bounds(x, y):
            return False
        tile = self.get_tile(x, y)
        if tile is None:
            return False
        if spirit_vision:
            # Spirit vision reveals spirit floors but spirit walls block
            if tile.spirit_tile_type == TileType.SPIRIT_FLOOR:
                return True
            if tile.spirit_tile_type == TileType.SPIRIT_WALL:
                return False
            return tile.effective_spirit_walkable
        # Material world: spirit-only floors are walls
        if tile.tile_type == TileType.SPIRIT_FLOOR:
            return False
        return tile.walkable

    def get_interactables_near(
        self, coord: TileCoord, radius: int = 1
    ) -> list[tuple[TileCoord, Tile]]:
        """Find all interactive tiles within radius of a position."""
        results = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = coord.x + dx, coord.y + dy
                tile = self.get_tile(nx, ny)
                if tile is not None and tile.interaction is not None:
                    results.append((TileCoord(nx, ny), tile))
        return results

    def get_tiles_by_type(self, tile_type: TileType) -> list[tuple[TileCoord, Tile]]:
        """Return all tiles of a specific type."""
        results = []
        for (x, y), tile in self.tiles.items():
            if tile.tile_type == tile_type:
                results.append((TileCoord(x, y), tile))
        return results


@dataclass
class MapConnection:
    """A link between two maps - doors, stairs, zone boundaries."""
    source_coord: TileCoord
    target_map_id: str
    target_coord: TileCoord
    requires_spirit_vision: bool = False
    required_flag: Optional[str] = None    # Story flag needed to pass
    transition_text: Optional[str] = None  # Flavor text during transition
    bidirectional: bool = True


# ---------------------------------------------------------------------------
# Spirit Vision
# ---------------------------------------------------------------------------

@dataclass
class SpiritVisionState:
    """
    Spirit Vision peels back the material veneer to reveal the spirit world
    overlaid on Tokyo. Buildings become ancient trees, crosswalks become
    rivers, and the hidden paths between worlds become visible.

    It drains spirit energy continuously and reveals things both wondrous
    and unsettling.
    """
    active: bool = False
    energy: float = 100.0
    max_energy: float = 100.0
    drain_rate: float = 2.0        # Energy per second while active
    recharge_rate: float = 0.5     # Energy per second while inactive
    recharge_delay: float = 3.0    # Seconds after deactivation before recharging
    time_since_deactivation: float = 0.0
    total_time_used: float = 0.0   # Lifetime stat

    def toggle(self) -> bool:
        """Toggle spirit vision on/off. Returns new active state."""
        if self.active:
            self.active = False
            self.time_since_deactivation = 0.0
            return False
        if self.energy > 0:
            self.active = True
            return True
        return False

    def update(self, delta: float) -> list[str]:
        """
        Update energy drain/recharge. Returns list of events
        (e.g., 'depleted', 'recharged', 'low_energy').
        """
        events: list[str] = []

        if self.active:
            self.energy -= self.drain_rate * delta
            self.total_time_used += delta
            if self.energy <= self.max_energy * 0.2 and self.energy + self.drain_rate * delta > self.max_energy * 0.2:
                events.append("low_energy")
            if self.energy <= 0:
                self.energy = 0.0
                self.active = False
                self.time_since_deactivation = 0.0
                events.append("depleted")
        else:
            self.time_since_deactivation += delta
            if self.time_since_deactivation >= self.recharge_delay:
                old_energy = self.energy
                self.energy = min(
                    self.max_energy,
                    self.energy + self.recharge_rate * delta,
                )
                if old_energy < self.max_energy and self.energy >= self.max_energy:
                    events.append("recharged")

        return events

    @property
    def energy_fraction(self) -> float:
        return self.energy / self.max_energy if self.max_energy > 0 else 0.0


# ---------------------------------------------------------------------------
# Context-sensitive actions
# ---------------------------------------------------------------------------

@dataclass
class ContextAction:
    """An action available to the player based on their surroundings."""
    interaction_type: InteractionType
    target_coord: TileCoord
    target_tile: Tile
    label: str                      # Display text, e.g., "Examine vending machine"
    priority: int = 0               # Higher = shown first
    requires_spirit_vision: bool = False
    requires_item: Optional[str] = None
    ma_gain: float = 0.0            # Ma accumulated by performing this action
    spirit_energy_cost: float = 0.0


def _build_action_label(interaction: InteractionType, tile: Tile) -> str:
    """Generate a context-sensitive label for an interaction."""
    subject = tile.metadata.get("name", "object")
    verbs = {
        InteractionType.EXAMINE: f"Examine {subject}",
        InteractionType.TALK: f"Talk to {subject}",
        InteractionType.PICK_UP: f"Pick up {subject}",
        InteractionType.USE: f"Use {subject}",
        InteractionType.OPEN: f"Open {subject}",
        InteractionType.PUSH: f"Push {subject}",
        InteractionType.PRAY: f"Pray at {subject}",
        InteractionType.LISTEN: f"Listen to {subject}",
        InteractionType.SIT: f"Sit at {subject}",
    }
    return verbs.get(interaction, f"Interact with {subject}")


# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------

@runtime_checkable
class CollisionProvider(Protocol):
    """Interface for anything that can block movement."""

    def blocks_movement(self, x: int, y: int, spirit_vision: bool) -> bool:
        ...


# ---------------------------------------------------------------------------
# Movement controller
# ---------------------------------------------------------------------------

@dataclass
class MovementResult:
    """The outcome of an attempted move."""
    success: bool
    new_position: TileCoord
    tile_entered: Optional[Tile] = None
    map_transition: Optional[MapConnection] = None
    events_triggered: list[str] = field(default_factory=list)
    discoveries: list[str] = field(default_factory=list)
    ma_change: float = 0.0
    noise_generated: float = 0.0


class MovementController:
    """
    Manages player position and movement on the tile grid. Every step
    checks collision, triggers events, and reports what the player
    discovers. The way you move shapes the world's response.
    """

    def __init__(
        self,
        tile_map: TileMap,
        start_position: TileCoord,
        collision_providers: Optional[list[CollisionProvider]] = None,
    ) -> None:
        self.tile_map = tile_map
        self.position = start_position
        self.facing: Direction = Direction.SOUTH
        self.mode: MovementMode = MovementMode.WALKING
        self.spirit_vision = SpiritVisionState()
        self.collision_providers: list[CollisionProvider] = collision_providers or []
        self.steps_taken: int = 0
        self.tiles_visited: set[tuple[int, int]] = {
            (start_position.x, start_position.y)
        }
        self._movement_locked: bool = False
        self._lock_reason: Optional[str] = None

    # -- Movement modes --

    def set_mode(self, mode: MovementMode) -> None:
        self.mode = mode

    def toggle_spirit_vision(self) -> bool:
        return self.spirit_vision.toggle()

    # -- Locking --

    def lock_movement(self, reason: str = "") -> None:
        """Prevent movement (during cutscenes, dialogue, etc.)."""
        self._movement_locked = True
        self._lock_reason = reason

    def unlock_movement(self) -> None:
        self._movement_locked = False
        self._lock_reason = None

    @property
    def is_locked(self) -> bool:
        return self._movement_locked

    # -- Core movement --

    def try_move(self, direction: Direction) -> MovementResult:
        """
        Attempt to move one tile in the given direction. Returns a result
        describing what happened - success or failure, events triggered,
        discoveries made.
        """
        self.facing = direction

        if self._movement_locked:
            return MovementResult(
                success=False,
                new_position=self.position,
                events_triggered=[f"movement_locked:{self._lock_reason}"],
            )

        target = self.position.offset(direction)
        sv_active = self.spirit_vision.active

        # Check tile map collision
        if not self.tile_map.is_walkable(target.x, target.y, spirit_vision=sv_active):
            return MovementResult(success=False, new_position=self.position)

        # Check additional collision providers (NPCs, dynamic obstacles)
        for provider in self.collision_providers:
            if provider.blocks_movement(target.x, target.y, sv_active):
                return MovementResult(success=False, new_position=self.position)

        # Movement succeeds
        old_position = self.position
        self.position = target
        self.steps_taken += 1
        first_visit = (target.x, target.y) not in self.tiles_visited
        self.tiles_visited.add((target.x, target.y))

        tile = self.tile_map.get_tile(target.x, target.y)
        result = MovementResult(
            success=True,
            new_position=target,
            tile_entered=tile,
            noise_generated=self.mode.noise_level,
        )

        if tile is None:
            return result

        # Ma change based on movement mode
        result.ma_change = -self.mode.ma_decay_multiplier * 0.1

        # Check for map transition
        for conn in self.tile_map.connections:
            if conn.source_coord == target:
                if conn.requires_spirit_vision and not sv_active:
                    continue
                result.map_transition = conn
                result.events_triggered.append("map_transition")
                break

        # Check for event trigger
        if tile.event_trigger:
            result.events_triggered.append(f"tile_event:{tile.event_trigger}")

        # Check for discovery on first visit
        if first_visit and tile.discovery_id:
            result.discoveries.append(tile.discovery_id)
            result.events_triggered.append(f"discovery:{tile.discovery_id}")

        # Spirit floor discovery
        if sv_active and tile.spirit_tile_type == TileType.SPIRIT_FLOOR and first_visit:
            result.events_triggered.append("spirit_path_found")

        return result

    def try_interact(self) -> Optional[ContextAction]:
        """
        Attempt to interact with the tile the player is facing.
        Returns the action if one is available, None otherwise.
        """
        target = self.position.offset(self.facing)
        tile = self.tile_map.get_tile(target.x, target.y)
        if tile is None or tile.interaction is None:
            return None

        if tile.metadata.get("requires_spirit_vision") and not self.spirit_vision.active:
            return None

        return ContextAction(
            interaction_type=tile.interaction,
            target_coord=target,
            target_tile=tile,
            label=_build_action_label(tile.interaction, tile),
            requires_spirit_vision=tile.metadata.get("requires_spirit_vision", False),
            requires_item=tile.metadata.get("requires_item"),
            ma_gain=tile.metadata.get("ma_gain", 0.0),
            spirit_energy_cost=tile.metadata.get("spirit_energy_cost", 0.0),
        )

    def get_available_actions(self, radius: int = 1) -> list[ContextAction]:
        """
        Scan surrounding tiles for all available interactions.
        Returns them sorted by priority (highest first).
        """
        actions: list[ContextAction] = []
        sv_active = self.spirit_vision.active

        for coord, tile in self.tile_map.get_interactables_near(self.position, radius):
            if tile.metadata.get("requires_spirit_vision") and not sv_active:
                continue

            action = ContextAction(
                interaction_type=tile.interaction,
                target_coord=coord,
                target_tile=tile,
                label=_build_action_label(tile.interaction, tile),
                requires_spirit_vision=tile.metadata.get(
                    "requires_spirit_vision", False
                ),
                requires_item=tile.metadata.get("requires_item"),
                ma_gain=tile.metadata.get("ma_gain", 0.0),
                spirit_energy_cost=tile.metadata.get("spirit_energy_cost", 0.0),
            )
            # Prioritize what the player is facing
            if coord == self.position.offset(self.facing):
                action.priority = 10
            actions.append(action)

        actions.sort(key=lambda a: a.priority, reverse=True)
        return actions

    def update(self, delta: float) -> list[str]:
        """
        Per-frame update. Handles spirit vision energy and idle ma gain.
        Returns list of events.
        """
        events = self.spirit_vision.update(delta)

        # Standing still in sneaking mode slowly accumulates ma
        # (the actual accumulation is handled by the game loop;
        # we just signal the opportunity)
        if self.mode == MovementMode.SNEAKING:
            events.append("sneaking_idle")

        return events

    @property
    def exploration_coverage(self) -> float:
        """Fraction of the current map's walkable tiles visited."""
        total_walkable = sum(
            1 for tile in self.tile_map.tiles.values() if tile.walkable
        )
        if total_walkable == 0:
            return 0.0
        visited_walkable = sum(
            1
            for (x, y) in self.tiles_visited
            if (tile := self.tile_map.get_tile(x, y)) is not None and tile.walkable
        )
        return visited_walkable / total_walkable

    def change_map(self, new_map: TileMap, entry_coord: TileCoord) -> None:
        """Transition to a new map at the given position."""
        self.tile_map = new_map
        self.position = entry_coord
        self.tiles_visited = {(entry_coord.x, entry_coord.y)}
