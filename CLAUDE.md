# Ma no Kuni (間の国) — Development Handoff

## What This Project Is

A narrative-driven RPG puzzle game set in Tokyo where the barrier between the material and spirit worlds is thinning. The player is **Aoi**, a young person living with their grandmother in Kichijoji who is beginning to perceive spirits. The central mechanic is **Ma (間)** — silence, stillness, and the spaces between — which accumulates through contemplative actions and unlocks perception of the spirit world.

## Tech Stack

- **Python 3.14** with **pygame-ce** (not standard pygame — needed for Python 3.14 compatibility)
- Grid-based tile engine (32x32 tiles, 800x600 window)
- Scene stack architecture with event bus
- All game content in YAML data files under `data/`

## Architecture Overview

```
main.py                    → Entry point, logging setup, launches game loop
src/engine/
  bootstrap.py             → Loads all systems from YAML, builds initial map, creates player
  game.py                  → Game state container (clock, ma, flags, current map)
  game_loop.py             → Pygame loop (input → update → render at 60 FPS)
  scene_manager.py         → Scene stack + all scene classes (~1770 lines, largest file)
  events.py                → EventBus and EventType enum
  input_handler.py         → Key mapping → semantic actions
  config.py                → DisplayConfig, GameplayConfig, AudioConfig, SpiritConfig
src/exploration/movement.py → TileMap, Tile, TileType, MovementController, collision, interaction
src/characters/dialogue.py  → DialogueTree, DialogueNode, DialogueManager, conversation state
src/characters/npc.py       → NPC registry, schedules, moods
src/characters/player.py    → PlayerCharacter, stats, inventory, spirit sight
src/ui/pygame_renderer.py   → All rendering (tiles, player, HUD, dialogue box, intro, labels)
src/ui/menus.py             → DialogueBox, menu widgets
```

## Scene Flow

```
TitleScene → IntroScene (3 narrative passages) → ExplorationScene
                                                      ↕
                                                DialogueScene (transparent overlay)
                                                CombatScene (replaces exploration)
                                                VignetteScene (narrative moments)
                                                MenuScene (pause menu)
                                                CraftingScene
```

## Current State of the Game (What Works)

### Playable
- **Title screen** with "New Journey" / "Continue" / "Quit"
- **Intro sequence**: Three text passages introduce Aoi, the thinning veil, and the starting scene. Player presses Z/Enter to advance.
- **Exploration**: Player walks a 20x15 Kichijoji map with grandmother's house, garden, stone path, jizo statue, spirit path, and gate to arcade
- **NPC interaction**: Grandmother Haruki (tile 9,4) and Mikan the cat (tile 6,5) are on the map as TALK-able NPC tiles
- **Dialogue system**: Full branching dialogue with character-by-character text reveal, player choices, silence mechanic (waiting builds Ma), spirit whispers
- **Grandmother's dialogue**: Morning garden conversation with 3 branches (ask about visions, comment on garden, sit in silence — silence gives most Ma)
- **Mikan's dialogue**: Short atmospheric cat interaction
- **Ma accumulation**: Praying at jizo (+2), sitting on bench (+5), listening to earth (+3), dialogue silence
- **Spirit vision toggle**: Shows hidden SPIRIT_FLOOR tiles
- **Interaction labels**: Floating name labels near interactive tiles, "[Z] Talk/Pray/etc" hints when facing them
- **Toast feedback**: Messages like "You prayed at small jizo statue. Ma +2"
- **Map transition system**: Gate at (10,13) connects to arcade (but arcade map doesn't exist yet)

### Visual State
- Fallback tile rendering with distinct patterns: brick walls, wood-grain doors, person silhouettes for NPCs, glowing jizo statue, sparkle for interactables, wave pattern for water, torii gate columns
- No real sprite sheets loaded yet — everything uses `_make_fallback_tile()` in pygame_renderer.py
- Japanese text renders via CJK-capable system font detection (see `_find_cjk_font()`)

### Not Yet Working / Incomplete
- **Kichijoji arcade map** — referenced by gate connection but not implemented
- **Combat** — CombatScene exists but no encounters are triggered on the starting map
- **Crafting** — CraftingScene exists, materials/recipes loaded, but no workshop accessible
- **Vignettes** — "Evening Tea" vignette data exists but triggering conditions (evening + kichijoji) haven't been tested
- **Music/audio** — Engine exists but 0 tracks loaded (YAML parsing fails on all entries: `'id'` key error)
- **Sprites** — 0 sprite definitions loaded (same parsing issue)
- **Districts** — 0 districts loaded from YAML (parsing fails: `'district_id'` key error)
- **Bestiary** — 0 spirits loaded from YAML
- **Save/load** — System exists in `src/saves/` but not wired into menu

## Known Parse Failures (Bootstrap Warnings)

These are logged on every startup and need investigation:
```
Failed to parse district 'unknown': 'district_id'    (×10)
Failed to parse track 'unknown': 'id'                 (×17)
Loaded 0 spirits, 0 districts, 0 music tracks, 0 sprites
```

The YAML files exist and have content, but the bootstrap parsers expect keys that don't match the YAML structure. This blocks music, sprites, districts, and bestiary from loading.

## Key Files Modified in Recent Session

| File | What Changed |
|------|-------------|
| `src/engine/scene_manager.py` | Added `IntroScene`, `start_exploration` state, interaction toasts, `render_interaction_labels` call, robust `_build_dialogue_context`, fixed IndexError in intro render |
| `src/engine/bootstrap.py` | Added NPC tiles (grandmother at 9,4 and Mikan at 6,5) to the Kichijoji map |
| `src/ui/pygame_renderer.py` | Rewrote `_make_fallback_tile` with detailed patterns, added `render_intro()`, `render_interaction_labels()`, `_interaction_hint()` |
| `src/engine/config.py` | Screen size 640x480 → 800x600 |
| `data/dialogues/main_characters.yaml` | Added `mikan_interact` and `obaa_chan_garden` dialogue trees |

## Git History (Recent → Old)

```
0b7eeba Fix IndexError in IntroScene render when passage index exceeds list
8179dc8 Add opening narrative, NPC interactions, and improved visuals
397c963 Fix Japanese text rendering by finding CJK-capable system font
e3ab7e0 Switch requirements from pygame to pygame-ce for Python 3.14 compat
61f071b Fix movement controls and title screen visibility
9b6d98d chore: Remove __pycache__ bytecode files from git tracking
2b87199 chore: Add .gitignore for Python bytecode and cache files
ee32c1a feat: Wire pygame rendering pipeline - game loop runs with title and exploration scenes
fcbaba9 feat: Create Ma no Kuni (間の国) RPG - complete game foundation
f617f45 Create README.md
```

## Branch

All work is on `claude/rpg-game-development-ENG42`.

## Suggested Next Steps (Based on User Feedback Direction)

1. **Fix YAML parsing** — Districts, bestiary, music tracks, and sprites all fail to load. Investigating and fixing the key mismatches would unlock music, real sprites, combat encounters, and district data.
2. **Build the arcade map** — The gate exists but leads nowhere. A second map would give the player somewhere to go.
3. **Add more NPCs** — Ren (shrine keeper), Yuki (konbini worker), and the Archivist all have dialogue trees written but aren't placed on any map.
4. **Trigger combat encounters** — Corrupted spirits could appear on the spirit path or in the arcade.
5. **Wire up save/load** — The save system exists but isn't connected to the menu scene.
6. **Real sprite art** — Replace fallback tiles with actual pixel art from `src/art/pixel_art.py`'s `build_tile_sprites()`.
7. **Vignette triggering** — Test and fix the Evening Tea vignette trigger conditions.

## Testing

Only one test file exists: `tests/test_engine.py` (tests WorldClock, MaState, SpiritTide, EventBus, GameState). Run with `pytest`.

## How to Run

```bash
pip install -r requirements.txt   # installs pygame-ce
python main.py
```

Controls: Arrow keys to move, Z/Enter to confirm/interact, X/Escape to cancel/back, S to toggle spirit vision.
