"""
Ma no Kuni - Game Bootstrap

The creation ritual. This module takes inert YAML data files and isolated
subsystems and weaves them into a living world: districts breathe with
spirit energy, NPCs settle into their routines, the bestiary waits to
be discovered, and Aoi wakes up in grandmother's house in Kichijoji
on the first morning of everything changing.

Every initialization step is deliberately ordered. The world must exist
before creatures can inhabit it. Characters must exist before they can
speak. The story must be loaded before the first chapter can begin.

Missing data files are handled gracefully -- the game can start even
if the world is incomplete. Warnings are logged, defaults are used,
and life finds a way.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Safe YAML loading helper
# ---------------------------------------------------------------------------

def _load_yaml(filepath: str | Path) -> Optional[dict]:
    """
    Load a YAML file and return its parsed content.
    Returns None if the file is missing or malformed, logging a warning.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        logger.warning("YAML file not found: %s", filepath)
        return None
    try:
        import yaml
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            logger.warning("YAML file is empty: %s", filepath)
            return None
        return data
    except Exception as exc:
        logger.warning("Failed to load YAML file %s: %s", filepath, exc)
        return None


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

class GameBootstrap:
    """
    Initialize the entire game world from data files.

    This is the single entry point for turning a collection of YAML
    definitions and Python subsystems into a playable game. It returns
    a dictionary of every initialized system so the caller can register
    them with the Game object and wire up the EventBus.

    Usage
    -----
    >>> from src.engine.bootstrap import GameBootstrap
    >>> bootstrap = GameBootstrap()
    >>> systems = bootstrap.initialize()
    >>> game = systems["game"]
    >>> scene_manager = systems["scene_manager"]
    """

    def __init__(self, data_root: str | Path | None = None) -> None:
        # Resolve the data directory relative to the project root
        if data_root is not None:
            self._data_root = Path(data_root)
        else:
            # Assume the project root is two directories up from this file
            self._data_root = Path(__file__).resolve().parent.parent.parent / "data"

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def initialize(self) -> dict[str, Any]:
        """
        Execute the full initialization sequence and return a dict of
        all initialized systems ready to be registered with the Game.

        Returns
        -------
        dict with keys:
            game, event_bus, scene_manager, player, npc_registry,
            district_registry, map_registry, bestiary, story_manager,
            dialogue_manager, material_registry, recipe_registry,
            music_engine, movement
        """
        logger.info("=== Ma no Kuni bootstrap starting ===")
        logger.info("Data root: %s", self._data_root)

        # 1. Core engine objects
        game, event_bus = self._init_core()

        # 2. World geography
        district_registry = self._load_districts()
        map_registry, kichijoji_map = self._create_initial_map()

        # 3. Bestiary (spirits must exist before encounters)
        bestiary = self._load_bestiary()

        # 4. NPCs
        npc_registry = self._create_npcs()

        # 5. Crafting registries
        material_registry, recipe_registry = self._load_crafting()

        # 6. Narrative (quests, vignettes, chapters)
        story_manager = self._load_narrative()

        # 7. Dialogue trees
        dialogue_manager = self._load_dialogues()

        # 8. Music engine
        music_engine = self._load_music()

        # 9. Sprite definitions
        sprite_data = self._load_sprites()

        # 10. Player character
        player = self._create_player()

        # 11. Movement controller on the initial map
        movement = self._create_movement(kichijoji_map)

        # 12. Wire everything into the Game object
        game.player = player
        game.current_map = kichijoji_map
        game.current_district = "kichijoji"
        game.running = True

        game.register_system("npc_registry", npc_registry)
        game.register_system("district_registry", district_registry)
        game.register_system("map_registry", map_registry)
        game.register_system("bestiary", bestiary)
        game.register_system("story_manager", story_manager)
        game.register_system("dialogue_manager", dialogue_manager)
        game.register_system("material_registry", material_registry)
        game.register_system("recipe_registry", recipe_registry)
        game.register_system("movement", movement)
        if music_engine is not None:
            game.register_system("music_engine", music_engine)

        # 13. Scene manager
        scene_manager = self._create_scene_manager(game, event_bus)

        # 14. Set initial story flags for Chapter 1
        self._set_initial_flags(game, story_manager)

        # 15. Place NPCs at their starting positions
        self._place_npcs(npc_registry, game.clock.hour, game.clock.day)

        logger.info("=== Ma no Kuni bootstrap complete ===")

        return {
            "game": game,
            "event_bus": event_bus,
            "scene_manager": scene_manager,
            "player": player,
            "npc_registry": npc_registry,
            "district_registry": district_registry,
            "map_registry": map_registry,
            "bestiary": bestiary,
            "story_manager": story_manager,
            "dialogue_manager": dialogue_manager,
            "material_registry": material_registry,
            "recipe_registry": recipe_registry,
            "music_engine": music_engine,
            "movement": movement,
            "sprite_data": sprite_data,
        }

    # ------------------------------------------------------------------ #
    # Step 1: Core engine
    # ------------------------------------------------------------------ #

    def _init_core(self) -> tuple[Any, Any]:
        """Create the Game and EventBus instances."""
        from src.engine.game import Game
        from src.engine.events import EventBus

        game = Game()
        event_bus = EventBus()

        logger.info("Core engine initialized")
        return game, event_bus

    # ------------------------------------------------------------------ #
    # Step 2: Districts
    # ------------------------------------------------------------------ #

    def _load_districts(self) -> Any:
        """Load districts from YAML and build the DistrictRegistry."""
        from src.world.districts import District, DistrictRegistry

        registry = DistrictRegistry()

        yaml_path = self._data_root / "maps" / "tokyo_districts.yaml"
        data = _load_yaml(yaml_path)

        if data is not None:
            for district_data in data.get("districts", []):
                try:
                    district = self._parse_district(district_data)
                    registry.register(district)
                except Exception as exc:
                    logger.warning(
                        "Failed to parse district '%s': %s",
                        district_data.get("id", "unknown"),
                        exc,
                    )
            logger.info(
                "Loaded %d districts from YAML",
                len(registry.all_districts()),
            )
        else:
            logger.warning("No district data; creating default Kichijoji")

        # Ensure Kichijoji always exists (Aoi's home)
        if registry.get("kichijoji") is None:
            registry.register(self._default_kichijoji())

        return registry

    def _parse_district(self, data: dict) -> Any:
        """Parse a single district from YAML data."""
        from src.world.districts import (
            District,
            DistrictAtmosphere,
            DistrictConnection,
            ConnectionType,
            SpiritDomain,
            SpiritEffect,
            SpiritEffectCategory,
        )

        # YAML uses "id", District dataclass uses "district_id"
        district_id = data["id"]

        # Build connections from connected_districts list (simple string
        # references) or structured connection objects if present
        connections = []
        for conn_data in data.get("connections", []):
            conn_type = ConnectionType.WALK
            raw_type = conn_data.get("type", "walk").lower()
            for ct in ConnectionType:
                if ct.value == raw_type:
                    conn_type = ct
                    break
            connections.append(DistrictConnection(
                target_district_id=conn_data["target"],
                connection_type=conn_type,
                base_travel_minutes=conn_data.get("travel_minutes", 15),
                line_name=conn_data.get("line_name", ""),
                spirit_delay_factor=conn_data.get("spirit_delay_factor", 1.0),
                description=conn_data.get("description", ""),
                requires_flag=conn_data.get("requires_flag"),
            ))
        # Also support the simple "connected_districts" string list from YAML
        for target_id in data.get("connected_districts", []):
            if not any(c.target_district_id == target_id for c in connections):
                connections.append(DistrictConnection(
                    target_district_id=target_id,
                    connection_type=ConnectionType.WALK,
                    base_travel_minutes=15,
                ))

        # YAML uses "dominant_spirit_types" (string list); map to SpiritDomain
        dominant_spirits = []
        for domain_str in data.get("dominant_spirit_types", data.get("dominant_spirits", [])):
            try:
                dominant_spirits.append(SpiritDomain(domain_str.lower()))
            except ValueError:
                pass

        # YAML atmosphere is a dict of time-of-day strings, not mood/lore
        atmosphere = None
        atm_data = data.get("atmosphere")
        if atm_data:
            if isinstance(atm_data, dict):
                # Build mood from description or first atmosphere entry
                mood = data.get("description", "")
                permeation_lore = ""
                # Gather permeation effects if present
                effects = data.get("permeation_effects", [])
                if effects:
                    permeation_lore = "; ".join(effects)
                atmosphere = DistrictAtmosphere(
                    mood=mood,
                    permeation_lore=permeation_lore,
                )

        # Extract location IDs from key_locations list
        location_ids = data.get("location_ids", [])
        if not location_ids:
            for loc in data.get("key_locations", []):
                if isinstance(loc, dict) and "id" in loc:
                    location_ids.append(loc["id"])

        return District(
            district_id=district_id,
            name=data.get("name", district_id),
            name_kanji=data.get("japanese_name", data.get("name_kanji", "")),
            subtitle=data.get("subtitle", ""),
            base_permeability=data.get("base_permeability",
                                       data.get("spirit_permeability_modifier", 0.3)),
            dominant_spirits=dominant_spirits,
            connections=connections,
            location_ids=location_ids,
            atmosphere=atmosphere,
            discovered=data.get("discovered", False),
            visited=data.get("visited", False),
        )

    def _default_kichijoji(self) -> Any:
        """Create the default Kichijoji district -- Aoi's starting location."""
        from src.world.districts import (
            District,
            DistrictAtmosphere,
            SpiritDomain,
        )

        return District(
            district_id="kichijoji",
            name="Kichijoji",
            name_kanji="吉祥寺",
            subtitle="Where the Hollyhock Grows",
            base_permeability=0.25,
            dominant_spirits=[SpiritDomain.NATURE, SpiritDomain.DOMESTIC],
            location_ids=[
                "grandmother_house",
                "garden",
                "shopping_arcade",
                "inokashira_park",
            ],
            atmosphere=DistrictAtmosphere(
                mood=(
                    "A quiet neighborhood where old trees line the streets and "
                    "the shops still know your name. Inokashira Park anchors "
                    "the spirit world here -- its ancient trees hold the veil "
                    "steady, even as it frays everywhere else."
                ),
                permeation_lore=(
                    "The park's grove acts as a stabilizer. Spirits pass through "
                    "but rarely linger. Grandmother's garden is an exception -- "
                    "something in the soil remembers."
                ),
            ),
            discovered=True,
            visited=True,
        )

    # ------------------------------------------------------------------ #
    # Step 2b: Initial tile map
    # ------------------------------------------------------------------ #

    def _create_initial_map(self) -> tuple[Any, Any]:
        """
        Create the initial Kichijoji map -- a 20x15 tile grid with
        grandmother's house, a garden path, the garden, and a gate
        leading to the shopping arcade.

        Returns (MapRegistry, initial_TileMap).
        """
        from src.exploration.movement import Tile, TileType, TileMap, TileCoord, InteractionType, MapConnection

        kichijoji = TileMap(
            map_id="kichijoji_start",
            name="Grandmother's Neighborhood",
            district="kichijoji",
            width=20,
            height=15,
            description=(
                "The quiet streets around grandmother's house. The garden "
                "hums with something that isn't quite wind."
            ),
        )

        # Fill with walkable ground
        for y in range(15):
            for x in range(20):
                kichijoji.set_tile(x, y, Tile(tile_type=TileType.FLOOR))

        # -- Grandmother's house (building block, upper-left area) --
        for y in range(1, 5):
            for x in range(1, 7):
                kichijoji.set_tile(x, y, Tile(
                    tile_type=TileType.WALL,
                    walkable=False,
                ))
        # House entrance
        kichijoji.set_tile(4, 5, Tile(
            tile_type=TileType.DOOR,
            walkable=True,
            interaction=InteractionType.OPEN,
            interaction_id="grandmother_house_door",
            metadata={"name": "grandmother's house"},
        ))
        # Interior floor (accessible through door, separate map in future)
        kichijoji.set_tile(4, 4, Tile(
            tile_type=TileType.FLOOR,
            walkable=True,
            event_trigger="location_grandmother_house",
            metadata={"name": "grandmother's house interior"},
        ))

        # -- Garden (right of the house) --
        for y in range(2, 7):
            for x in range(8, 14):
                kichijoji.set_tile(x, y, Tile(
                    tile_type=TileType.FLOOR,
                    walkable=True,
                    spirit_energy=0.3,
                    metadata={"name": "garden"},
                ))
        # Garden special tiles
        kichijoji.set_tile(10, 3, Tile(
            tile_type=TileType.INTERACTIVE,
            walkable=False,
            interaction=InteractionType.SIT,
            interaction_id="garden_bench",
            spirit_energy=0.5,
            metadata={"name": "garden bench", "ma_gain": 5.0},
        ))
        kichijoji.set_tile(11, 4, Tile(
            tile_type=TileType.INTERACTIVE,
            walkable=False,
            interaction=InteractionType.EXAMINE,
            interaction_id="grandmother_flowers",
            spirit_energy=0.4,
            metadata={"name": "grandmother's flowers"},
        ))
        kichijoji.set_tile(12, 5, Tile(
            tile_type=TileType.INTERACTIVE,
            walkable=False,
            interaction=InteractionType.LISTEN,
            interaction_id="garden_spirit_spot",
            spirit_energy=0.6,
            metadata={
                "name": "a humming patch of earth",
                "ma_gain": 3.0,
                "requires_spirit_vision": False,
            },
        ))

        # -- NPCs on the map --
        # Grandmother Haruki in the garden
        kichijoji.set_tile(9, 4, Tile(
            tile_type=TileType.NPC,
            walkable=False,
            interaction=InteractionType.TALK,
            interaction_id="obaa_chan",
            spirit_energy=0.3,
            metadata={"name": "Grandmother Haruki", "npc_id": "obaa_chan"},
        ))
        # Mikan the cat on the engawa (porch)
        kichijoji.set_tile(6, 5, Tile(
            tile_type=TileType.NPC,
            walkable=False,
            interaction=InteractionType.TALK,
            interaction_id="mikan",
            spirit_energy=0.2,
            metadata={"name": "Mikan", "npc_id": "mikan"},
        ))

        # -- Path from house to garden and down to the gate --
        for x in range(4, 14):
            kichijoji.set_tile(x, 7, Tile(
                tile_type=TileType.FLOOR,
                walkable=True,
                metadata={"name": "stone path"},
            ))

        # Vertical path south to the gate
        for y in range(7, 13):
            kichijoji.set_tile(10, y, Tile(
                tile_type=TileType.FLOOR,
                walkable=True,
                metadata={"name": "lane"},
            ))

        # -- Gate to the shopping arcade (southern edge) --
        kichijoji.set_tile(10, 13, Tile(
            tile_type=TileType.DOOR,
            walkable=True,
            interaction=InteractionType.OPEN,
            interaction_id="arcade_gate",
            event_trigger="district_transition_arcade",
            metadata={"name": "gate to the shopping arcade"},
        ))

        # Map connection at the gate
        kichijoji.connections.append(MapConnection(
            source_coord=TileCoord(10, 14),
            target_map_id="kichijoji_arcade",
            target_coord=TileCoord(5, 0),
            transition_text=(
                "The gate opens onto the covered shopping arcade. "
                "The smell of fresh taiyaki drifts from somewhere ahead."
            ),
        ))

        # -- Walls / boundaries along the edges --
        for x in range(20):
            kichijoji.set_tile(x, 0, Tile(tile_type=TileType.WALL, walkable=False))
            kichijoji.set_tile(x, 14, Tile(tile_type=TileType.WALL, walkable=False))
        for y in range(15):
            kichijoji.set_tile(0, y, Tile(tile_type=TileType.WALL, walkable=False))
            kichijoji.set_tile(19, y, Tile(tile_type=TileType.WALL, walkable=False))
        # Re-open the gate tile (overwritten by boundary)
        kichijoji.set_tile(10, 14, Tile(
            tile_type=TileType.FLOOR,
            walkable=True,
            event_trigger="map_transition",
        ))

        # -- Jizo statue save point near the house --
        kichijoji.set_tile(2, 7, Tile(
            tile_type=TileType.SAVE_POINT,
            walkable=False,
            interaction=InteractionType.PRAY,
            interaction_id="jizo_home",
            spirit_energy=0.4,
            metadata={"name": "small jizo statue", "ma_gain": 2.0},
        ))

        # -- Spirit-only path (visible only with spirit vision) --
        for y in range(3, 7):
            kichijoji.set_tile(15, y, Tile(
                tile_type=TileType.SPIRIT_FLOOR,
                walkable=False,
                spirit_walkable=True,
                spirit_energy=0.7,
                discovery_id="kichijoji_spirit_path",
                metadata={"name": "a shimmering trail only you can see"},
            ))

        # Build map registry
        try:
            from src.world.maps import MapRegistry as WorldMapRegistry
            map_registry = WorldMapRegistry()
        except ImportError:
            map_registry = _SimpleMapRegistry()

        # Store using a simple dict-based registry for the movement map
        map_registry._movement_maps = {"kichijoji_start": kichijoji}

        logger.info(
            "Created initial Kichijoji map: %dx%d tiles",
            kichijoji.width,
            kichijoji.height,
        )
        return map_registry, kichijoji

    # ------------------------------------------------------------------ #
    # Step 3: Bestiary
    # ------------------------------------------------------------------ #

    def _load_bestiary(self) -> Any:
        """Load spirit definitions into the Bestiary."""
        from src.combat.bestiary import Bestiary

        bestiary = Bestiary()
        total = 0

        spirit_files = [
            self._data_root / "bestiary" / "spirits.yaml",
            self._data_root / "bestiary" / "corrupted.yaml",
        ]
        for filepath in spirit_files:
            if filepath.exists():
                count = bestiary.load_from_yaml(str(filepath))
                total += count
                logger.info("Loaded %d spirits from %s", count, filepath.name)
            else:
                logger.warning("Bestiary file not found: %s", filepath)

        logger.info("Bestiary initialized with %d total entries", total)
        return bestiary

    # ------------------------------------------------------------------ #
    # Step 4: NPCs
    # ------------------------------------------------------------------ #

    def _create_npcs(self) -> Any:
        """Create all main NPCs using factory functions."""
        try:
            from src.characters.npc import create_all_main_npcs
            registry = create_all_main_npcs()
            logger.info(
                "NPC registry created with %d characters",
                len(registry.get_all()),
            )
            return registry
        except ImportError as exc:
            logger.warning("Could not import NPC factories: %s", exc)
            from src.characters.npc import NPCRegistry
            return NPCRegistry()

    def _place_npcs(self, npc_registry: Any, hour: float, day: int) -> None:
        """Update all NPC positions according to their schedules."""
        if hasattr(npc_registry, "update_all"):
            npc_registry.update_all(hour, day)
            logger.info("NPCs placed at starting positions (hour=%.1f)", hour)

    # ------------------------------------------------------------------ #
    # Step 5: Crafting
    # ------------------------------------------------------------------ #

    def _load_crafting(self) -> tuple[Any, Any]:
        """Load materials and recipes from YAML."""
        material_registry = None
        recipe_registry = None

        # Materials
        materials_path = self._data_root / "items" / "materials.yaml"
        try:
            from src.crafting.materials import MaterialRegistry, load_materials_from_yaml
            if materials_path.exists():
                material_registry = load_materials_from_yaml(str(materials_path))
                logger.info("Loaded materials from %s", materials_path.name)
            else:
                logger.warning("Materials file not found: %s", materials_path)
                material_registry = MaterialRegistry()
        except ImportError as exc:
            logger.warning("Could not import crafting materials: %s", exc)

        if material_registry is None:
            try:
                from src.crafting.materials import MaterialRegistry
                material_registry = MaterialRegistry()
            except ImportError:
                material_registry = _EmptyRegistry()

        # Recipes
        recipes_path = self._data_root / "items" / "recipes.yaml"
        try:
            from src.crafting.recipes import RecipeRegistry, load_recipes_from_yaml
            if recipes_path.exists():
                recipe_registry = load_recipes_from_yaml(str(recipes_path))
                logger.info("Loaded recipes from %s", recipes_path.name)
            else:
                logger.warning("Recipes file not found: %s", recipes_path)
                recipe_registry = RecipeRegistry()
        except ImportError as exc:
            logger.warning("Could not import crafting recipes: %s", exc)

        if recipe_registry is None:
            try:
                from src.crafting.recipes import RecipeRegistry
                recipe_registry = RecipeRegistry()
            except ImportError:
                recipe_registry = _EmptyRegistry()

        return material_registry, recipe_registry

    # ------------------------------------------------------------------ #
    # Step 6: Narrative
    # ------------------------------------------------------------------ #

    def _load_narrative(self) -> Any:
        """Load quests, vignettes, and chapters into the StoryManager."""
        from src.narrative.story_manager import StoryManager

        story_manager = StoryManager()

        # Main story quests
        main_story_path = self._data_root / "quests" / "main_story.yaml"
        data = _load_yaml(main_story_path)
        if data is not None:
            count = story_manager.load_quests_from_yaml(data)
            chapters = story_manager.load_chapters_from_yaml(data)
            logger.info(
                "Loaded %d main quests and %d chapters", count, chapters,
            )

        # Side quests
        side_path = self._data_root / "quests" / "side_quests.yaml"
        data = _load_yaml(side_path)
        if data is not None:
            count = story_manager.load_quests_from_yaml(data)
            logger.info("Loaded %d side quests", count)

        # Vignettes
        vignettes_path = self._data_root / "quests" / "vignettes.yaml"
        data = _load_yaml(vignettes_path)
        if data is not None:
            count = story_manager.load_vignettes_from_yaml(data)
            logger.info("Loaded %d vignettes", count)

        # Initialize character relationships
        story_manager.initialize_relationships()
        logger.info("Story manager initialized with relationships")

        return story_manager

    # ------------------------------------------------------------------ #
    # Step 7: Dialogues
    # ------------------------------------------------------------------ #

    def _load_dialogues(self) -> Any:
        """Load dialogue trees into the DialogueManager."""
        from src.characters.dialogue import DialogueManager, load_dialogue_trees_from_yaml

        dialogue_manager = DialogueManager()

        dialogue_path = self._data_root / "dialogues" / "main_characters.yaml"
        data = _load_yaml(dialogue_path)
        if data is not None:
            trees = load_dialogue_trees_from_yaml(data)
            dialogue_manager.register_trees(trees)
            logger.info("Loaded %d dialogue trees", len(trees))
        else:
            logger.warning("No dialogue data found")

        return dialogue_manager

    # ------------------------------------------------------------------ #
    # Step 8: Music
    # ------------------------------------------------------------------ #

    def _load_music(self) -> Optional[Any]:
        """Load soundtrack definitions and configure the MusicEngine."""
        try:
            from src.audio.music_engine import MusicEngine, TrackDefinition
        except ImportError as exc:
            logger.warning("Could not import MusicEngine: %s", exc)
            return None

        engine = MusicEngine()

        soundtrack_path = self._data_root / "music" / "soundtrack.yaml"
        data = _load_yaml(soundtrack_path)
        if data is not None:
            for track_data in data.get("tracks", []):
                try:
                    tid = track_data.get("track_id", track_data.get("id"))
                    track = TrackDefinition(
                        track_id=tid,
                        name=track_data.get("name", tid),
                        tempo_bpm=track_data.get("tempo_bpm", 120.0),
                        key=track_data.get("key", "C"),
                        time_signature=track_data.get("time_signature", "4/4"),
                        base_layer_asset=track_data.get("base_layer_asset"),
                        melodic_layer_asset=track_data.get("melodic_layer_asset"),
                        harmonic_layer_asset=track_data.get("harmonic_layer_asset"),
                        spirit_layer_asset=track_data.get("spirit_layer_asset"),
                        base_volume=track_data.get("base_volume", 0.7),
                        melodic_volume=track_data.get("melodic_volume", 0.8),
                        harmonic_volume=track_data.get("harmonic_volume", 0.6),
                        spirit_volume=track_data.get("spirit_volume", 0.5),
                        spirit_permeability_threshold=track_data.get(
                            "spirit_permeability_threshold", 0.3
                        ),
                        loop=track_data.get("loop", True),
                        intro_beats=track_data.get("intro_beats", 0),
                        tags=track_data.get("tags", []),
                    )
                    engine.load_track(track)
                except (KeyError, TypeError) as exc:
                    logger.warning(
                        "Failed to parse track '%s': %s",
                        track_data.get("track_id", track_data.get("id", "unknown")),
                        exc,
                    )
            logger.info("Loaded %d music tracks", len(engine.tracks))
        else:
            logger.warning("No soundtrack data found")

        return engine

    # ------------------------------------------------------------------ #
    # Step 9: Sprites
    # ------------------------------------------------------------------ #

    def _load_sprites(self) -> Optional[dict]:
        """
        Load sprite definitions from YAML. Returns the raw parsed data
        for the rendering system to consume during its own initialization.
        """
        sprite_path = self._data_root / "sprites" / "sprite_definitions.yaml"
        data = _load_yaml(sprite_path)
        if data is not None:
            # Sprite defs are at root level keyed by sprite name (aoi, mikan, etc.)
            # If there's a "sprites" wrapper, use it; otherwise count all dict keys
            if "sprites" in data:
                count = len(data["sprites"])
            else:
                count = len([k for k in data if isinstance(data[k], dict)])
            logger.info("Loaded %d sprite definitions", count)
        else:
            logger.warning("No sprite definitions found")
        return data

    # ------------------------------------------------------------------ #
    # Step 10: Player character
    # ------------------------------------------------------------------ #

    def _create_player(self) -> Any:
        """
        Create Aoi with starting stats, inventory, and location.

        Starting stats:
            Empathy: 5, Perception: 4, Resolve: 3,
            Spirit_Affinity: 3, Craft_Skill: 2, Knowledge: 3

        Starting location: Kichijoji, grandmother's house

        Starting inventory:
            - grandmother's handkerchief (keepsake)
            - house key
            - small coin purse
        """
        from src.characters.player import (
            PlayerCharacter,
            StatBlock,
            Stat,
            SpiritSight,
            SpiritSightLevel,
            Item,
            ItemCategory,
        )

        stats = StatBlock(
            empathy=Stat(base=5),
            perception=Stat(base=4),
            resolve=Stat(base=3),
            spirit_affinity=Stat(base=3),
            craft_skill=Stat(base=2),
            knowledge=Stat(base=3),
        )

        player = PlayerCharacter(
            name="Aoi",
            pronouns=("they", "them", "their"),
            stats=stats,
            spirit_sight=SpiritSight(
                level=SpiritSightLevel.FLICKERING,
                experience=0.0,
            ),
            level=1,
            chapter=1,
            current_district="kichijoji",
            current_location="grandmother_house",
        )

        # Starting inventory
        handkerchief = Item(
            id="grandmothers_handkerchief",
            name="Grandmother's Handkerchief",
            description=(
                "A soft cotton handkerchief, faintly scented with lavender "
                "and something older. Grandmother pressed it into your hands "
                "the morning everything started. 'Keep this close,' she said, "
                "and didn't explain why."
            ),
            category=ItemCategory.KEY,
            spirit_resonance=0.3,
            tags={"keepsake", "grandmother", "chapter_1"},
            lore=(
                "The handkerchief has been washed a thousand times but the "
                "scent never fades. It belonged to someone before grandmother. "
                "The embroidered hollyhock in the corner is older than the cloth."
            ),
        )

        house_key = Item(
            id="house_key",
            name="House Key",
            description=(
                "The key to grandmother's house. The metal is warm, always, "
                "as if the house itself is alive and breathing."
            ),
            category=ItemCategory.KEY,
            spirit_resonance=0.1,
            tags={"key", "grandmother"},
        )

        coin_purse = Item(
            id="small_coin_purse",
            name="Small Coin Purse",
            description=(
                "A modest purse with enough for a few trips to the konbini "
                "and maybe a can of coffee from the vending machine outside "
                "the station."
            ),
            category=ItemCategory.MATERIAL,
            tags={"money"},
        )

        player.inventory.add(handkerchief)
        player.inventory.add(house_key)
        player.inventory.add(coin_purse)

        logger.info(
            "Player created: %s (E:%d P:%d R:%d SA:%d CS:%d K:%d) at %s/%s",
            player.name,
            stats.empathy.base,
            stats.perception.base,
            stats.resolve.base,
            stats.spirit_affinity.base,
            stats.craft_skill.base,
            stats.knowledge.base,
            player.current_district,
            player.current_location,
        )

        return player

    # ------------------------------------------------------------------ #
    # Step 11: Movement controller
    # ------------------------------------------------------------------ #

    def _create_movement(self, tile_map: Any) -> Any:
        """Create the MovementController positioned at grandmother's house."""
        from src.exploration.movement import MovementController, TileCoord

        # Start in front of the house door
        start = TileCoord(x=4, y=6)
        controller = MovementController(
            tile_map=tile_map,
            start_position=start,
        )
        logger.info("Movement controller created at (%d, %d)", start.x, start.y)
        return controller

    # ------------------------------------------------------------------ #
    # Step 13: Scene manager
    # ------------------------------------------------------------------ #

    def _create_scene_manager(self, game: Any, event_bus: Any) -> Any:
        """Create the SceneManager and subscribe it to events."""
        from src.engine.scene_manager import SceneManager, TitleScene

        scene_manager = SceneManager(game, event_bus)

        # Start on the title screen
        title = TitleScene(game, event_bus)
        scene_manager.push_scene(title)

        logger.info("Scene manager created; title scene active")
        return scene_manager

    # ------------------------------------------------------------------ #
    # Step 14: Story flags
    # ------------------------------------------------------------------ #

    def _set_initial_flags(self, game: Any, story_manager: Any) -> None:
        """
        Set the initial story flags for Chapter 1.

        These flags establish the narrative starting point:
        - The permeation has begun but is not widely acknowledged
        - Aoi lives with grandmother Haruki
        - Spirit sight is newly awakened (flickering stage)
        - The shopping arcade and Inokashira Park are accessible
        - Grandmother's garden is a safe haven
        """
        initial_flags = {
            # Chapter progression
            "current_chapter": True,
            "chapter_1_started": True,
            "chapter_1_introduction": True,

            # World state
            "permeation_begun": True,
            "permeation_public_knowledge": False,

            # Aoi's situation
            "lives_with_grandmother": True,
            "spirit_sight_awakened": True,
            "parents_estranged": True,

            # Locations
            "kichijoji_discovered": True,
            "grandmother_house_accessible": True,
            "shopping_arcade_accessible": True,
            "inokashira_park_accessible": True,

            # NPCs
            "grandmother_met": True,
            "mikan_met": True,
            "ren_met": False,
            "yuki_met": False,
            "kaito_met": False,
            "hinata_met": False,
            "archivist_met": False,

            # Tutorial / early game
            "tutorial_movement_complete": False,
            "tutorial_spirit_vision_complete": False,
            "tutorial_dialogue_complete": False,
            "first_spirit_encountered": False,
            "garden_explored": False,
        }

        for flag, value in initial_flags.items():
            game.set_flag(flag, value)

        # Initialize chapter 1 in the story manager
        if hasattr(story_manager, "chapters"):
            chapter = story_manager.chapters.get(1)
            if chapter is not None:
                from src.narrative.story_manager import ChapterState
                chapter.state = ChapterState.INTRODUCTION

        story_manager.current_chapter = 1

        logger.info("Set %d initial story flags for Chapter 1", len(initial_flags))


# ---------------------------------------------------------------------------
# Fallback types for when optional imports fail
# ---------------------------------------------------------------------------

class _EmptyRegistry:
    """Placeholder registry when a subsystem cannot be imported."""
    pass


class _SimpleMapRegistry:
    """Minimal map registry fallback."""

    def __init__(self) -> None:
        self._maps: dict[str, Any] = {}
        self._movement_maps: dict[str, Any] = {}

    def register(self, dual_map: Any) -> None:
        self._maps[getattr(dual_map, "district_id", "")] = dual_map

    def get(self, district_id: str) -> Optional[Any]:
        return self._maps.get(district_id)
