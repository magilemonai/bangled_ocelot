"""
Ma no Kuni - Tile-Based Map System

Two maps exist for every place: the Material map and the Spirit map.
Walk through Shibuya on the Material layer and you see neon, crowds,
concrete. Switch to the Spirit layer and the crossing becomes a mandala
of paused intention, the scramble a frozen constellation of nearly-
colliding souls, each crosswalk light a tiny shrine to collective
obedience.

The tile system supports both layers. Each tile carries its physical
type (road, building, shrine...) and a spirit resonance value that
tracks how much otherworldly energy has seeped into that spot. High-
resonance tiles shimmer, hum, or outright tear open during surges.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ---------------------------------------------------------------------------
# Tile taxonomy
# ---------------------------------------------------------------------------

class TileType(Enum):
    """
    The physical character of a map tile.

    Each type interacts differently with spirit energy:
    - Shrines and spiritual nexuses *attract* resonance.
    - Roads and train stations *conduct* it, spreading energy along paths.
    - Buildings *resist* it, unless very old or spiritually significant.
    - Water and parks *store* it, releasing slowly over time.
    """
    ROAD = "road"
    BUILDING = "building"
    SHRINE = "shrine"
    PARK = "park"
    WATER = "water"
    BRIDGE = "bridge"
    TRAIN_STATION = "train_station"
    MARKET = "market"
    RESIDENTIAL = "residential"
    SPIRITUAL_NEXUS = "spiritual_nexus"


# Resonance behavior constants per tile type
_TILE_RESONANCE_PROFILES: dict[TileType, dict[str, float]] = {
    TileType.ROAD: {
        "conductivity": 0.7,   # Spreads energy to neighbors
        "retention": 0.2,      # Doesn't hold energy long
        "attraction": 0.1,     # Doesn't pull energy in
    },
    TileType.BUILDING: {
        "conductivity": 0.1,
        "retention": 0.4,
        "attraction": 0.05,
    },
    TileType.SHRINE: {
        "conductivity": 0.3,
        "retention": 0.9,
        "attraction": 0.8,
    },
    TileType.PARK: {
        "conductivity": 0.4,
        "retention": 0.7,
        "attraction": 0.3,
    },
    TileType.WATER: {
        "conductivity": 0.5,
        "retention": 0.8,
        "attraction": 0.4,
    },
    TileType.BRIDGE: {
        "conductivity": 0.8,
        "retention": 0.15,
        "attraction": 0.2,
    },
    TileType.TRAIN_STATION: {
        "conductivity": 0.9,
        "retention": 0.3,
        "attraction": 0.5,
    },
    TileType.MARKET: {
        "conductivity": 0.5,
        "retention": 0.4,
        "attraction": 0.35,
    },
    TileType.RESIDENTIAL: {
        "conductivity": 0.2,
        "retention": 0.5,
        "attraction": 0.15,
    },
    TileType.SPIRITUAL_NEXUS: {
        "conductivity": 0.6,
        "retention": 0.95,
        "attraction": 1.0,
    },
}


# ---------------------------------------------------------------------------
# Map layers
# ---------------------------------------------------------------------------

class MapLayer(Enum):
    """The two overlapping planes of existence."""
    MATERIAL = "material"    # Concrete Tokyo
    SPIRIT = "spirit"        # The world behind the world


# ---------------------------------------------------------------------------
# Tiles
# ---------------------------------------------------------------------------

@dataclass
class Tile:
    """
    A single cell on the map grid.

    Every tile exists simultaneously in the Material and Spirit layers,
    but its *appearance* and *passability* may differ between them.
    A solid building in the Material layer might be a hollow shell in
    the Spirit layer, its walls replaced by memory. A road might become
    a river of light.
    """
    x: int
    y: int
    tile_type: TileType
    spirit_tile_type: Optional[TileType] = None  # Override for Spirit layer

    # --- Resonance ---
    spirit_resonance: float = 0.0       # 0.0 = dormant, 1.0 = blazing
    resonance_cap: float = 1.0          # Some tiles can hold more
    resonance_locked: bool = False       # Narrative lock: resonance frozen

    # --- Navigation ---
    passable_material: bool = True
    passable_spirit: bool = True
    elevation: int = 0                   # For vertical layering (rooftops)

    # --- Content ---
    location_id: Optional[str] = None   # Link to a Location
    encounter_tag: Optional[str] = None  # Spirit encounter reference
    event_trigger: Optional[str] = None  # Scripted event on entry
    flavor_text: str = ""                # Brief description for exploration

    # --- Spirit layer appearance ---
    spirit_flavor_text: str = ""         # What the tile looks like in Spirit

    # --- Metadata ---
    tags: list[str] = field(default_factory=list)  # Arbitrary tags

    # ------------------------------------------------------------------
    # Resonance profile
    # ------------------------------------------------------------------

    @property
    def resonance_profile(self) -> dict[str, float]:
        """Return the resonance behavior constants for this tile type."""
        return _TILE_RESONANCE_PROFILES.get(
            self.tile_type,
            {"conductivity": 0.3, "retention": 0.3, "attraction": 0.1},
        )

    @property
    def conductivity(self) -> float:
        return self.resonance_profile["conductivity"]

    @property
    def retention(self) -> float:
        return self.resonance_profile["retention"]

    @property
    def attraction(self) -> float:
        return self.resonance_profile["attraction"]

    # ------------------------------------------------------------------
    # Resonance manipulation
    # ------------------------------------------------------------------

    def add_resonance(self, amount: float) -> float:
        """
        Add spirit resonance to this tile. Returns the actual amount
        added (may be less if capped or locked).
        """
        if self.resonance_locked:
            return 0.0
        old = self.spirit_resonance
        self.spirit_resonance = min(
            self.resonance_cap,
            self.spirit_resonance + amount,
        )
        return self.spirit_resonance - old

    def decay_resonance(self, delta: float) -> None:
        """Resonance fades based on the tile's retention property."""
        if self.resonance_locked:
            return
        decay_rate = (1.0 - self.retention) * 0.1  # Slow base decay
        self.spirit_resonance = max(
            0.0,
            self.spirit_resonance - decay_rate * delta,
        )

    def get_type_for_layer(self, layer: MapLayer) -> TileType:
        """Return the appropriate tile type for the given layer."""
        if layer == MapLayer.SPIRIT and self.spirit_tile_type is not None:
            return self.spirit_tile_type
        return self.tile_type

    def is_passable(self, layer: MapLayer) -> bool:
        """Check passability for the given layer."""
        if layer == MapLayer.MATERIAL:
            return self.passable_material
        return self.passable_spirit

    @property
    def is_spiritual_hotspot(self) -> bool:
        """Tiles above 0.6 resonance are considered hotspots."""
        return self.spirit_resonance >= 0.6

    @property
    def is_nexus(self) -> bool:
        return self.tile_type == TileType.SPIRITUAL_NEXUS


# ---------------------------------------------------------------------------
# The Map grid
# ---------------------------------------------------------------------------

@dataclass
class TileMap:
    """
    A 2D grid of tiles representing one district's geography.

    Each district has two TileMaps: one Material, one Spirit. The Spirit
    map may share geometry with the Material map but diverges in tile
    types, passability, flavor text, and encounter data.

    The map also runs a simple resonance simulation each tick: energy
    flows from high-resonance tiles to neighbors via conductivity, and
    decays based on retention. Shrines and nexuses pull energy toward
    themselves via attraction.
    """
    map_id: str
    district_id: str
    layer: MapLayer
    width: int
    height: int
    tiles: list[list[Optional[Tile]]] = field(default_factory=list)
    name: str = ""
    description: str = ""

    def __post_init__(self) -> None:
        """Initialize the grid if not provided."""
        if not self.tiles:
            self.tiles = [
                [None for _ in range(self.width)]
                for _ in range(self.height)
            ]

    # ------------------------------------------------------------------
    # Tile access
    # ------------------------------------------------------------------

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        if not self.in_bounds(x, y):
            return None
        return self.tiles[y][x]

    def set_tile(self, x: int, y: int, tile: Tile) -> None:
        if self.in_bounds(x, y):
            self.tiles[y][x] = tile

    def get_neighbors(self, x: int, y: int) -> list[Tile]:
        """Return the four cardinal neighbors of a position."""
        neighbors = []
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = x + dx, y + dy
            tile = self.get_tile(nx, ny)
            if tile is not None:
                neighbors.append(tile)
        return neighbors

    def get_neighbors_8(self, x: int, y: int) -> list[Tile]:
        """Return all eight surrounding neighbors."""
        neighbors = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                tile = self.get_tile(x + dx, y + dy)
                if tile is not None:
                    neighbors.append(tile)
        return neighbors

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def tiles_of_type(self, tile_type: TileType) -> list[Tile]:
        """Find all tiles of a given type."""
        result = []
        for row in self.tiles:
            for tile in row:
                if tile is not None and tile.tile_type == tile_type:
                    result.append(tile)
        return result

    def tiles_with_tag(self, tag: str) -> list[Tile]:
        """Find all tiles carrying a specific tag."""
        result = []
        for row in self.tiles:
            for tile in row:
                if tile is not None and tag in tile.tags:
                    result.append(tile)
        return result

    def tiles_with_location(self) -> list[Tile]:
        """Find all tiles that reference a Location."""
        result = []
        for row in self.tiles:
            for tile in row:
                if tile is not None and tile.location_id is not None:
                    result.append(tile)
        return result

    def hotspots(self) -> list[Tile]:
        """Return all tiles that are currently spiritual hotspots."""
        result = []
        for row in self.tiles:
            for tile in row:
                if tile is not None and tile.is_spiritual_hotspot:
                    result.append(tile)
        return result

    def highest_resonance_tile(self) -> Optional[Tile]:
        """Return the tile with the highest spirit resonance."""
        best: Optional[Tile] = None
        for row in self.tiles:
            for tile in row:
                if tile is not None:
                    if best is None or tile.spirit_resonance > best.spirit_resonance:
                        best = tile
        return best

    # ------------------------------------------------------------------
    # Resonance simulation
    # ------------------------------------------------------------------

    def simulate_resonance(self, delta: float) -> None:
        """
        Run one tick of the resonance simulation.

        Energy flows through the map like water through a watershed:
        - High-conductivity tiles (roads, bridges, stations) carry
          resonance to their neighbors.
        - High-attraction tiles (shrines, nexuses) pull energy inward.
        - High-retention tiles (water, parks, shrines) hold energy.
        - Low-retention tiles (roads) shed energy quickly.

        The simulation is intentionally simple -- this is a game, not
        a physics engine. But it produces emergent patterns: resonance
        pools around shrines, flows along train lines, and dissipates
        in residential blocks.
        """
        # Build a delta map to avoid order-dependent updates
        deltas: list[list[float]] = [
            [0.0 for _ in range(self.width)]
            for _ in range(self.height)
        ]

        for y in range(self.height):
            for x in range(self.width):
                tile = self.get_tile(x, y)
                if tile is None or tile.resonance_locked:
                    continue

                neighbors = self.get_neighbors(x, y)
                if not neighbors:
                    continue

                # --- Flow: energy moves from this tile to neighbors ---
                if tile.spirit_resonance > 0:
                    flow_out = (
                        tile.spirit_resonance
                        * tile.conductivity
                        * 0.05  # Damping factor
                        * delta
                    )
                    per_neighbor = flow_out / len(neighbors)
                    for nb in neighbors:
                        deltas[nb.y][nb.x] += per_neighbor
                    deltas[y][x] -= flow_out

                # --- Attraction: high-attraction tiles pull from neighbors ---
                if tile.attraction > 0.3:
                    for nb in neighbors:
                        pull = (
                            nb.spirit_resonance
                            * tile.attraction
                            * 0.03
                            * delta
                        )
                        deltas[y][x] += pull
                        deltas[nb.y][nb.x] -= pull

        # Apply deltas
        for y in range(self.height):
            for x in range(self.width):
                tile = self.get_tile(x, y)
                if tile is not None and not tile.resonance_locked:
                    tile.spirit_resonance = max(
                        0.0,
                        min(tile.resonance_cap, tile.spirit_resonance + deltas[y][x]),
                    )

        # Decay
        for y in range(self.height):
            for x in range(self.width):
                tile = self.get_tile(x, y)
                if tile is not None:
                    tile.decay_resonance(delta)

    # ------------------------------------------------------------------
    # Map generation helpers
    # ------------------------------------------------------------------

    def fill(self, tile_type: TileType, **kwargs) -> None:
        """Fill the entire map with a single tile type."""
        for y in range(self.height):
            for x in range(self.width):
                self.tiles[y][x] = Tile(x=x, y=y, tile_type=tile_type, **kwargs)

    def place_rect(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        tile_type: TileType,
        **kwargs,
    ) -> None:
        """Place a rectangle of tiles."""
        for ty in range(y, min(y + h, self.height)):
            for tx in range(x, min(x + w, self.width)):
                self.tiles[ty][tx] = Tile(
                    x=tx, y=ty, tile_type=tile_type, **kwargs
                )

    def place_road(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        **kwargs,
    ) -> None:
        """
        Place a road from start to end using an L-shaped path
        (horizontal then vertical).
        """
        sx, sy = start
        ex, ey = end
        # Horizontal segment
        step_x = 1 if ex >= sx else -1
        for tx in range(sx, ex + step_x, step_x):
            if self.in_bounds(tx, sy):
                self.tiles[sy][tx] = Tile(
                    x=tx, y=sy, tile_type=TileType.ROAD, **kwargs
                )
        # Vertical segment
        step_y = 1 if ey >= sy else -1
        for ty in range(sy, ey + step_y, step_y):
            if self.in_bounds(ex, ty):
                self.tiles[ty][ex] = Tile(
                    x=ex, y=ty, tile_type=TileType.ROAD, **kwargs
                )


# ---------------------------------------------------------------------------
# Dual-layer map wrapper
# ---------------------------------------------------------------------------

@dataclass
class DualLayerMap:
    """
    Pairs the Material and Spirit maps for a single district.

    The engine renders whichever layer the player is currently perceiving,
    or blends them when permeability is high enough. This wrapper provides
    convenience methods for working with both layers simultaneously.
    """
    district_id: str
    material: TileMap
    spirit: TileMap

    def __post_init__(self) -> None:
        if self.material.width != self.spirit.width:
            raise ValueError(
                f"Layer width mismatch: material={self.material.width}, "
                f"spirit={self.spirit.width}"
            )
        if self.material.height != self.spirit.height:
            raise ValueError(
                f"Layer height mismatch: material={self.material.height}, "
                f"spirit={self.spirit.height}"
            )

    @property
    def width(self) -> int:
        return self.material.width

    @property
    def height(self) -> int:
        return self.material.height

    def get_layer(self, layer: MapLayer) -> TileMap:
        if layer == MapLayer.MATERIAL:
            return self.material
        return self.spirit

    def get_tile(self, x: int, y: int, layer: MapLayer) -> Optional[Tile]:
        return self.get_layer(layer).get_tile(x, y)

    def is_passable(self, x: int, y: int, layer: MapLayer) -> bool:
        tile = self.get_tile(x, y, layer)
        if tile is None:
            return False
        return tile.is_passable(layer)

    def get_blended_resonance(self, x: int, y: int) -> float:
        """
        Average the resonance from both layers. Useful when the layers
        are merging during high permeability.
        """
        mat_tile = self.material.get_tile(x, y)
        spi_tile = self.spirit.get_tile(x, y)
        mat_r = mat_tile.spirit_resonance if mat_tile else 0.0
        spi_r = spi_tile.spirit_resonance if spi_tile else 0.0
        return (mat_r + spi_r) / 2.0

    def simulate_resonance(self, delta: float) -> None:
        """Run resonance simulation on both layers."""
        self.material.simulate_resonance(delta)
        self.spirit.simulate_resonance(delta)

    def inject_resonance_at(
        self,
        x: int,
        y: int,
        amount: float,
        layer: MapLayer = MapLayer.SPIRIT,
    ) -> float:
        """
        Inject spirit energy at a point. Defaults to the Spirit layer.
        Returns the actual amount absorbed.
        """
        tile = self.get_tile(x, y, layer)
        if tile is None:
            return 0.0
        return tile.add_resonance(amount)

    def cascade_resonance(
        self,
        x: int,
        y: int,
        amount: float,
        radius: int = 3,
        layer: MapLayer = MapLayer.SPIRIT,
    ) -> float:
        """
        Inject resonance that falls off with distance from the source.
        Used for spirit surges, shrine activations, and nexus pulses.
        Returns the total amount distributed.
        """
        total = 0.0
        tile_map = self.get_layer(layer)
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                dist = (dx * dx + dy * dy) ** 0.5
                if dist > radius:
                    continue
                falloff = max(0.0, 1.0 - (dist / (radius + 1)))
                tile = tile_map.get_tile(x + dx, y + dy)
                if tile is not None:
                    total += tile.add_resonance(amount * falloff)
        return total


# ---------------------------------------------------------------------------
# Map registry
# ---------------------------------------------------------------------------

class MapRegistry:
    """Manages all loaded DualLayerMaps, keyed by district ID."""

    def __init__(self) -> None:
        self._maps: dict[str, DualLayerMap] = {}

    def register(self, dual_map: DualLayerMap) -> None:
        self._maps[dual_map.district_id] = dual_map

    def get(self, district_id: str) -> Optional[DualLayerMap]:
        return self._maps.get(district_id)

    def all_maps(self) -> list[DualLayerMap]:
        return list(self._maps.values())

    def simulate_all(self, delta: float) -> None:
        """Run resonance simulation across every loaded map."""
        for dual_map in self._maps.values():
            dual_map.simulate_resonance(delta)
