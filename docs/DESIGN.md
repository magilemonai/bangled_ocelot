# Ma no Kuni (間の国) — Godot Migration Design Document

## Game Vision

Ma no Kuni is a narrative-driven action RPG set in contemporary Tokyo, where the boundary between the material world and the spirit realm is slowly dissolving. You play as Aoi, a young person living with their grandmother in the quiet Kichijoji neighborhood, who is just beginning to realize they can perceive things others cannot — a flicker at the edge of vision, a presence in an empty room, a voice in the space between sounds.

The game's central mechanic is **Ma (間)** — a Japanese concept encompassing silence, stillness, and the meaningful pause between moments. Rather than rewarding constant action, Ma no Kuni asks the player to slow down: sit in a garden, listen to rain, hold a conversation without rushing toward the next objective. These contemplative acts accumulate Ma, which gradually opens Aoi's perception of the spirit world and unlocks abilities, dialogue options, and hidden layers of each environment.

The tonal touchstone is melancholic tenderness — not grimdark, not whimsical. Think of the quiet ache in a Makoto Shinkai film, or the unhurried mood of a Hayao Miyazaki neighborhood scene. There is mystery here, and real stakes, but also warmth, humor in small doses, and an underlying hopefulness about connection across difference.

Gameplay draws from Secret of Mana — smooth real-time movement, action combat, lush pixel art worlds — but filtered through the game's contemplative identity. Combat is a disruption, not a reward loop. The goal is often befriending or purifying spirits, not defeating them.

---

## Why Godot

The existing Python/pygame-ce prototype proved the concept. Godot 4.x is where it grows into a real game.

- **Dedicated 2D engine** with real pixel coordinates, tilemaps, animation trees, and collision shapes — no more hand-coding AABB logic
- **GDScript is Python-like**, keeping the learning curve shallow for anyone familiar with the existing codebase
- **Node-and-scene architecture** maps naturally onto the scene stack we already have
- **Tilemap editor** replaces hand-coded tile grids, making district building dramatically faster
- **Cross-platform export** to desktop, web, and mobile with no licensing fees
- **Free and open source** (MIT), actively maintained, with a large community and plentiful ARPG tutorials

---

## What Changes

| System | Python/Pygame | Godot |
|--------|--------------|-------|
| Movement | Grid-based 32x32 tile stepping | Smooth pixel movement with CharacterBody2D |
| Combat | Turn-based ATB with Ma timing | Real-time action RPG (Secret of Mana style) |
| Rendering | Code-generated fallback tiles | Tilemap editor + pixel art sprite sheets |
| Maps | Python dict tile arrays | TileMap nodes with visual editor |
| Audio | Stub music engine (0 tracks loaded) | AudioStreamPlayer with layered bus mixing |
| UI | Pygame surface blitting | Godot Control nodes and themes |

## What Stays

All YAML content data (7000+ lines) carries over intact: dialogues, bestiary, recipes, quests, maps, music definitions, puzzles. The Ma mechanic stays exactly as designed. The two-layer world model (material + spirit with permeability blending), spirit bonding and corruption, narrative pacing, three-axis relationships, crafting as negotiation — all preserved. Ten Tokyo districts, 23 spirits, a seven-chapter story with multiple endings.

---

## Tech Stack

- **Engine:** Godot 4.3+ (latest stable)
- **Language:** GDScript (primary — Python-like, fastest iteration)
- **Data:** YAML files loaded via GDScript addon or custom parser
- **Resolution:** 320x240 native, scaled 3x to 960x720
- **Target:** 60 FPS
- **Version Control:** Git (existing repo)
## 2. Godot Project Architecture

### Project Structure

```
project.godot
data/                          # Existing YAML content files (kept as-is)
  bestiary/                    # spirits.yaml, corrupted.yaml
  dialogues/                   # main_characters.yaml
  items/                       # materials.yaml, recipes.yaml
  maps/                        # kichijoji_start.yaml, tokyo_districts.yaml, exploration_events.yaml
  music/                       # soundtrack.yaml, compositions.yaml
  puzzles/                     # puzzle_templates.yaml
  quests/                      # main_story.yaml, side_quests.yaml, vignettes.yaml
  sprites/                     # sprite_definitions.yaml
assets/
  sprites/
    characters/                # Aoi, NPCs (sprite sheets)
    spirits/                   # Spirit sprites
    tiles/                     # Tileset textures
    effects/                   # Particle textures, VFX
    ui/                        # UI elements
  audio/
    music/                     # .ogg music tracks
    sfx/                       # Sound effects
    ambient/                   # Environmental loops
  fonts/                       # CJK-capable fonts
scenes/
  main.tscn                   # Entry point
  title/                      # Title screen
  exploration/                # World exploration (main gameplay)
  combat/                     # Action combat encounters
  dialogue/                   # Dialogue overlay
  vignette/                   # Narrative moments
  crafting/                   # Crafting workshop
  menus/                      # Pause, inventory, bestiary, save/load
scripts/
  autoload/                   # Singletons (game state, event bus, etc.)
  exploration/                # Movement, interaction, camera
  combat/                     # Action combat
  spirits/                    # Spirit world, bonds, corruption
  narrative/                  # Story, quests, vignettes
  characters/                 # Player, NPC, dialogue
  crafting/                   # Workshop, recipes, materials
  world/                      # Districts, time, weather
  audio/                      # Music engine, soundscape
  ui/                         # HUD, menus, dialogue box
  data/                       # YAML loader, data classes
resources/                    # Godot .tres resource files
  tilesets/
  themes/
  materials/                  # Shader materials
shaders/
  spirit_blend.gdshader       # Material/spirit layer blending
  corruption.gdshader         # Corruption visual effect
  ma_glow.gdshader            # Ma accumulation glow
  vignette.gdshader           # Screen vignette effect
```

---

### Autoload Singletons

Six autoloads registered in `project.godot`, available globally by name.

**GameState** — The authoritative runtime container. Holds `WorldClock` (in-game hour/day/season/moon), `MaGauge` (current/max/lifetime Ma), story flags dictionary, current chapter, and `permeability` (0.0–1.0). This single float drives the spirit blend shader. Replaces `game.py`.

**EventBus** — Cross-system communication as typed Godot signals. Where Python called `event_bus.emit(EventType.MA_CHANGED, value)`, Godot calls `EventBus.ma_changed.emit(value)`. Static typing enforces signal argument correctness. Systems connect on `_ready()`, disconnect on `_exit_tree()`.

**DataLoader** — Runs before any scene loads. Reads every YAML file under `data/`, validates keys, populates typed `Resource` objects stored in dictionaries keyed by ID. This is where the Python key-mismatch bugs are fixed permanently — the loader matches the YAML as written.

**AudioManager** — Owns four `AudioStreamPlayer` nodes (base, melodic, harmonic, spirit layers). Layer volumes crossfade via `Tween` keyed to `GameState.permeability` and current district. The spirit layer's volume is driven directly by permeability each frame.

**SaveManager** — Nine named slots plus autosave. Serializes `GameState` to JSON via `FileAccess`, appends SHA-256 checksum, writes atomically (temp file then rename). Autosave fires on map transitions and before vignettes.

**StoryManager** — Polls `GameState` each in-game hour tick, checks vignette trigger conditions (district, time, flags, minimum Ma). Tracks quest state and narrative pacing guards so events don't fire out of order.

---

### Scene Tree Architecture

```
Main (Node2D)
├── ExplorationScene (Node2D)
│   ├── MaterialLayer (Node2D, y_sort_enabled)
│   │   ├── TileMap (material world tiles)
│   │   ├── NPCs (CharacterBody2D children)
│   │   └── InteractableObjects
│   ├── SpiritLayer (Node2D, y_sort_enabled)
│   │   ├── TileMap (spirit world tiles, shader-blended)
│   │   ├── SpiritEntities (CharacterBody2D children)
│   │   └── SpiritEffects (GPUParticles2D)
│   ├── Player (CharacterBody2D)
│   ├── Camera2D (smooth follow, map bounds)
│   └── InteractionZones (Area2D children)
├── UILayer (CanvasLayer, layer=10)
│   ├── HUD (Ma bar, spirit sight, clock, toast)
│   ├── DialogueBox (Control)
│   ├── InteractionPrompt ("[Z] Talk")
│   └── Menus (Control, hidden by default)
├── VignetteLayer (CanvasLayer, layer=20)
│   └── VignetteScene
├── CombatLayer (CanvasLayer or scene swap)
│   └── CombatScene
└── TransitionLayer (CanvasLayer, layer=100)
    └── ScreenTransition (fade/wipe via AnimationPlayer)
```

**Dual-layer rendering:** MaterialLayer and SpiritLayer use the same cell size and coordinate space. SpiritLayer has a `ShaderMaterial` (`spirit_blend.gdshader`) with a `permeability` uniform. At 0.0, the spirit layer is invisible. At 1.0, fully present. Intermediate values produce ghostly overlap with chromatic shift and desaturation beneath.

**Y-sorting:** `y_sort_enabled = true` on both layer containers. Characters walk behind walls when heading north, in front when heading south — no manual z_index management needed.

**Camera:** `Camera2D` with `position_smoothing_enabled = true` (speed ~5.0), tracking the player via lerp in `_process`. Limit margins set per-map so the camera never shows void at edges. This produces the locked, buttery scrolling of Secret of Mana.

**UI isolation:** `CanvasLayer` at layer 10 keeps HUD elements unaffected by camera movement or world shaders.

**Transitions:** `TransitionLayer` at layer 100 plays fade-to-black or iris-wipe animations before/after scene changes, ensuring no raw scene swap is visible.
## 3. System-by-System Migration Mapping

### Movement System

**Python:** Integer grid coordinates with discrete 8-directional steps, checking `TileType` on the destination cell before committing movement. Three modes (walk/run/sneak) with different speeds and Ma decay rates.

**Godot:** `CharacterBody2D` with `move_and_slide()` handles collision continuously via `CollisionShape2D` masks on `TileMap` layers. Movement modes are exported variables on `PlayerController`, each defining speed and Ma decay multiplier passed to `GameState` each frame. Interaction detection moves from "check tile ahead" to `Area2D` signals (`interactable_entered` / `interactable_exited`). Animation blending between 8 directions uses `AnimatedSprite2D` with blend-position from normalized velocity.

---

### Ma (間) System

**Python:** `MaState` dataclass mutated in place by scattered calls across `scene_manager.py`.

**Godot:** `Resource` subclass (`MaState.gd`) owned exclusively by `GameState` autoload. Each frame, `_process(delta)` applies decay rate from active movement mode and emits `ma_changed(value, max_value)` signal for HUD subscription. Stillness accumulation: track `player.velocity == Vector2.ZERO` duration; once threshold crossed, accumulation begins. Real physical stillness at the keyboard is a direct input to the mechanic — this works *better* in real-time than it did on a grid.

---

### Spirit World / Dual Layer

**Python:** Boolean toggle re-renders spirit overlay tiles in the same draw pass.

**Godot:** Two `TileMapLayer` nodes rendered by the same TileMap, with `ShaderMaterial` exposing a `permeability` uniform (0.0–1.0). Fragment shader sets spirit alpha to `permeability * spirit_sight_modifier`. Pressing S increments modifier with strain timer that decays it back. Corruption uses a second shader pass with noise-distorted UVs. `GPUParticles2D` on spirit objects handles foxfire, shimmer, void-edge effects.

---

### Dialogue System

**Python:** `DialogueManager` state machine with character-reveal coroutine, choices, silence mechanic.

**Godot:** Custom `DialogueBox.tscn` — `CanvasLayer` with `RichTextLabel` (character reveal via `visible_characters` incremented by `Timer`) and `VBoxContainer` for choice buttons. Silence mechanic: dedicated choice button starts a `Timer`; if undismissed, `GameState.add_ma(reward)` fires and dialogue advances to silence branch. Spirit whispers use a secondary `RichTextLabel` gated by permeability. Custom system preferred over Dialogic 2 because silence-as-input and Ma-during-dialogue require deep `GameState` hooks.

---

### NPC System

**Python:** Registry with schedules, 9 personality traits, dispositions.

**Godot:** Each NPC is a `CharacterBody2D` scene with `AnimatedSprite2D`, `NavigationAgent2D`, personality `Resource`, and `Area2D` interaction trigger. Schedule data evaluated on `GameState.time_changed` signal — NPC's controller sets new navigation target. Personality traits as `Resource` subclass with exported variables. Disposition read from `RelationshipData` to gate dialogue branches.

---

### Crafting System

**Python:** Workshop with recipes, materials, conditions (time/season/moon/weather), curious items.

**Godot:** `CraftingScene` loaded additively over exploration. Ingredient slots use `TextureRect` with `gui_input` for drag-and-drop. Recipe validation calls `GameState` for current time, season, moon, weather. Same outcome logic (success/great success/curious/failure) ported to GDScript.

---

### Narrative / Quest System

**Python:** `StoryManager` with quests (branches/objectives), vignette engine (beats with timing), pacing system.

**Godot:** `StoryManager` autoload tracks quest state as `Dictionary` of objective flags, emitting signals on completion. Vignette system as overlay scene with tween-based timing, `RichTextLabel` for text beats, `Timer` for silence beats. Pacing counter drives content selection.

---

### Relationship System

**Python:** 3-axis model (trust/affinity/understanding), phases, events.

**Godot:** `RelationshipData` as `Resource` per NPC persisted in save files. Trust, affinity, understanding as float properties. Phase thresholds computed from axis values. Updated via `EventBus` signals — no direct coupling.

---

### Puzzle System

**Python:** 7 types, progressive hint system, multiple solutions, Ma silence puzzles.

**Godot:** Puzzles as specialized `Node2D` scenes embedded in district maps. Ma silence puzzles use `Input.is_anything_pressed()` in `_process` to detect complete input stillness. Dual-layer puzzles respond to `permeability` uniform to reveal/hide elements. Hints via progressive `Area2D` triggers.

---

### World / Districts

**Python:** 10 districts, time-of-day atmospherics, permeability modifiers, connections.

**Godot:** Each district is a separate scene. `SceneManager` handles transitions, passing district ID and entry position. `WorldClock` in `GameState` drives time-of-day (modulate lighting via `CanvasModulate`, enable/disable NPCs, shift music). District-specific tileset and ambient audio per scene.

---

### Audio System

**Python:** 4-layer engine (base/melodic/harmonic/spirit), soundscape, transitions — all stubbed (0 tracks loaded).

**Godot:** `AudioManager` autoload with four `AudioStreamPlayer` nodes (one per layer). Crossfade via `Tween`. Spirit layer volume = permeability. Ambient via `AudioStreamPlayer2D` nodes placed in scenes. `AudioBus` routes master/music/sfx/ambient channels.

---

### Save System

**Python:** 9 slots + autosave, JSON with SHA256 checksum, atomic writes — fully implemented but not wired to UI.

**Godot:** `SaveManager` autoload with same slot structure. `FileAccess` for JSON read/write. Checksum verification. Wired to menu UI from Phase 2. Autosave on scene transitions.

---

### Art / Rendering

**Python:** Hand-coded pixel grids, 36-color material palette + 33-color spirit palette, fallback tile patterns.

**Godot:** Proper sprite sheets as textures. `AnimatedSprite2D` for characters. `TileSet` with terrain autotile rules. Palette-swap shader handles material-to-spirit color shift using both palettes as `Texture2D` uniforms.
## 4. Combat Redesign: From Turn-Based to Action RPG

### Design Philosophy

Combat in Ma no Kuni is not a reward loop. It is an interruption — a failure of understanding between Aoi and the spirit world. The ideal outcome of any encounter is rarely a pile of defeated enemies; it is silence restored, a spirit returned to its true nature, or a bond formed where there was hostility.

The Secret of Mana comparison is instructive for pacing and feel, not for tone. Where Mana's combat is joyful and kinetic, Ma no Kuni's combat should feel slightly wrong — like arguing in a library, or running through a temple. The player should always sense that fighting is not the intended path, even when it is the necessary one.

---

### Movement and Basic Attacks

Aoi moves freely through combat using the same exploration controls, with one addition: a **dodge roll** (X button) granting brief invincibility frames on a ~1.5 second cooldown, shown as a small arc beneath Aoi's feet.

Basic attacks chain into a **three-hit light combo** on the Z button. The timing between hits is deliberate — not button-mashing, but rhythm. The third hit has a visual cue (a breath, a glow) signaling a **perfect timing window**: pressing Z at that moment extends the chain and generates a tick of Ma. Missing the window breaks the chain. This single mechanic encodes the game's philosophy into every fight: pay attention, find the rhythm.

**Heavy Strike:** Hold the attack button to charge, release to hit hard and stagger. Costs Ma gauge — spending Ma on offense means not spending it on negotiation or Ma Burst.

---

### The Ma Gauge in Combat

The Ma gauge is the combat system's defining feature and its central strategic tension.

**It fills when Aoi stands completely still** — even mid-fight. A spirit charges toward you. You can dodge, or you can hold your ground, breathe, and let the gauge climb. If you survive (or if the spirit hesitates — some will, in the presence of genuine stillness), you come out ahead. This is not a safe strategy. It is a deliberate one.

**Ma Burst:** When the gauge reaches maximum, pressing the Ma button triggers a **Ma Moment** — time slows to ~20% speed, ambient sound fades to a low resonant tone, screen desaturates at edges. This window lasts ~4 real-time seconds and grants:

- Spirit Arts cost no SP
- Up to 1.5x damage on attacks
- Elevated negotiation effectiveness
- Ability to begin purification rituals

Players who build Ma through stillness use it more often and more strategically than those who fight aggressively. This is intentional.

---

### Negotiation: The Other Combat System

At any point during an encounter, Aoi can open the **negotiation ring menu** (shoulder button). This pauses action and presents four options:

| Option | Effect |
|--------|--------|
| **Speak** | Verbal approach — effectiveness depends on spirit personality |
| **Observe** | Study the spirit — reveals weakness/personality hints |
| **Offer Gift** | Present a crafted item — some spirits respond to specific gifts |
| **Silence** | Say nothing — generates Ma, shows respect, never damages stance |

Each choice moves the spirit along a stance progression:

```
HOSTILE → WARY → CURIOUS → RECEPTIVE → FRIENDLY → TRUSTING
```

Spirits have personalities affecting which approaches work. A mischievous tanuki warms to humor in Speak options; a stone guardian responds to Silence and Observation. The game doesn't telegraph preferences — players learn through failed attempts, environmental context, and journal notes.

**Silence deserves emphasis.** It generates Ma, shows respect, and never damages the relationship. Against the right spirit, it advances stance faster than anything else. Against corrupted spirits, it's often the only non-aggressive option. Silence is not doing nothing. It is the most considered choice.

Successful negotiation ends in: **Bonded** (spirit joins, unlocking their art), **Peaceful Resolution** (spirit withdraws), or **Departure** (spirit leaves, satisfied). Failed negotiation drops stance and may provoke attack. A full Ma Moment during negotiation provides the highest single stance bonus.

---

### Spirit Arts and the Ring Menu

Spirit Arts are accessed through a **radial ring menu** (hold shoulder button, push direction, release to cast). Game pauses during selection, Secret of Mana style. Quick-ring shows four equipped arts.

Arts are learned from bonded spirits. 30+ arts across eight elements organized in two circles:

```
Physical:  FIRE → WIND → EARTH → WATER → FIRE
Spiritual: LIGHT → SHADOW → MEMORY → SILENCE → LIGHT
```

**Harmonies** between circles create combo effects — Fire + Memory = Burning Nostalgia (DoT that also surfaces spirit emotional data in negotiation).

Categories: Attack, Healing, Support, Debuff, Purification, Negotiation. Each costs SP and/or Ma gauge.

Key arts preserved from existing design:
- **Lantern Light** (Fire) — illuminate + damage
- **River's Remembrance** (Water) — heal + surface memories
- **Tanuki's Trick** (Shadow) — create decoy
- **Profound Silence** (Ma) — AoE calm + massive Ma generation
- **Gentle Cleansing** (Purification) — cleanse corruption

---

### Corruption and Purification

Corrupted spirits can't be negotiated with until corruption is reduced. Purification requires:
1. Sustained Ma presence near the spirit
2. A purification art or item
3. Stillness — standing still, close to something hostile, letting silence do its work

As corruption decreases, negotiation options unlock. Full purification restores the spirit's original personality.

---

### Enemy Behavior

**No random encounters.** Every spirit is visible on the exploration map.

- **Territorial spirits:** Hold ground, attack if approached
- **Curious spirits:** Circle at distance, may flee if attacked
- **Corrupted spirits:** Erratic movement, aggress on sight
- **Bosses:** Phase-based behavior tied to story beats, not HP thresholds — a boss's second phase might begin when Aoi opens a negotiation window

Combat areas may be bounded (spirit territory with visible edges, retreat possible) or open (spirits may or may not pursue). Fleeing is always valid.

---

### Status Effects (Real-Time)

Durations in real-time seconds, not turns:

| Effect | Type | Description |
|--------|------|-------------|
| Burning | Negative | Damage over time |
| Soaked | Negative | Increased vulnerability |
| Rooted | Negative | Movement locked |
| Silenced | Negative | Cannot use Spirit Arts |
| Corrupted | Negative | Ma decay accelerates |
| Shielded | Positive | Damage reduction |
| Haste | Positive | Speed boost |
| Regenerating | Positive | Heal over time |
| Spirit Linked | Positive | Bonded spirit assists attacks |

Spirit Linked — earned through negotiation — summons a bonded spirit to assist for a duration. It should feel like being helped by a friend, not activating a cooldown.

---

### Combat UI

- **Health/SP bars** — top-left
- **Ma gauge** — prominent, center-bottom (the most important meter)
- **Ring menu** — radial selection (hold to open)
- **Enemy health** — appears above targeted enemy
- **Negotiation stance** — indicator bar when in negotiation mode
- **Status icons** — small icons near health bars
## 5. Content Pipeline and Data Migration

### Existing Content Inventory

The game carries ~7000+ lines of YAML across 15 files. This content must be preserved in full.

| Category | Files | Content | Python Status |
|----------|-------|---------|---------------|
| Bestiary | spirits.yaml, corrupted.yaml | 17 normal + 6 corrupted spirits | Failed (key mismatch) |
| Dialogues | main_characters.yaml | 5+ dialogue trees, ~16K lines | Partial |
| Maps | kichijoji_start.yaml, tokyo_districts.yaml, exploration_events.yaml | 1 map (30x20), 10 districts, 15+ events | Partial |
| Music | soundtrack.yaml, compositions.yaml | 17 tracks, 4-layer definitions | Failed (key mismatch) |
| Items | materials.yaml, recipes.yaml | 49 materials, 20 recipes | Failed |
| Puzzles | puzzle_templates.yaml | 12+ puzzles, 7 types | Not loaded |
| Quests | main_story.yaml, side_quests.yaml, vignettes.yaml | 7-chapter story, 12+ side quests, 15+ vignettes | Not loaded |
| Sprites | sprite_definitions.yaml | Character/spirit/tile definitions | Failed |

---

### YAML Loading in Godot

Godot 4 has no built-in YAML parser. The project will use a GDScript addon (e.g., "Godot YAML" from the Asset Library). A single `DataLoader` autoload handles all content at startup.

The Python prototype's failures were all key mismatches, not structural YAML problems. The fix: write the Godot loader to match the YAML as it exists. Districts use `id` (not `district_id`). Music tracks use `track_id` (not `id`). Correcting these assumptions unlocks all content categories at once.

```
DataLoader (Autoload)
├── load_bestiary()   → Array[SpiritData]
├── load_dialogues()  → Dictionary[String, DialogueTree]
├── load_districts()  → Array[DistrictData]
├── load_materials()  → Array[MaterialData]
├── load_recipes()    → Array[RecipeData]
├── load_music()      → Array[TrackData]
├── load_puzzles()    → Array[PuzzleData]
├── load_quests()     → Array[QuestData]
├── load_vignettes()  → Array[VignetteData]
└── load_sprites()    → Dictionary[String, SpriteData]
```

Each function parses YAML, validates fields, returns typed `Resource` subclasses. Resources are cached after first load.

---

### Map Migration

The kichijoji_start.yaml defines a 30x20 tile grid with 14 tile types, NPC placements, spirit entities, and interaction points.

**Split approach:**
- **Visual layout** lives in Godot's TileMap editor. Each district is a `.tscn` scene with TileMap node. Editing tiles visually is dramatically faster than YAML coordinate arrays.
- **Gameplay data** (NPC positions, interaction zones, spirit spawns, events) stays in YAML, loaded at runtime by the district scene's `_ready()`. Keeps content portable and editable without touching scene files.

**Tile mapping:**
- YAML tile types (grass, road, shrine, water) → TileSet terrain types
- Spirit resonance values → custom data layer on TileMap
- Passability → collision layer on TileSet
- Spirit-layer TileMap overlays material TileMap per scene

10 planned districts each get their own scene. Connections from `tokyo_districts.yaml` drive fast-travel and scene transitions.

---

### Sprite Asset Pipeline

The Python prototype has hand-coded pixel grids (2D palette-index arrays). Two migration paths:

1. **Convert:** Write a one-time Python script to read existing pixel arrays and export PNG sprite sheets, preserving the 36-color material and 33-color spirit palettes
2. **Redraw:** Create sprites in Aseprite or Pixelorama using the same palettes, which also provides animation frames

Import settings for all sprites: Filter = Nearest, mipmaps disabled.

**Character sprites:**
- 32x32 standard characters, 64x64 bosses
- Minimum: 4-direction walk cycle (4 frames each)
- Required states: idle, walk, run, attack, dodge, interact, ma-meditate
- `AnimatedSprite2D` nodes with named animation sequences

---

### Audio Asset Pipeline

17 tracks defined in YAML with tempo, key, instrumentation, layer descriptions. Zero audio files exist.

**Godot approach:**
- Compose tracks from the detailed YAML specs (enough info for any DAW)
- Format: `.ogg` for looping music, `.wav` for short SFX
- 4 `AudioStreamPlayer` nodes per track (base/melodic/harmonic/spirit)
- Spirit layer volume driven by permeability
- Alternative: procedural generation from `compositions.yaml` note data via `AudioStreamGenerator`

---

### Dialogue Content

`main_characters.yaml` (~16K lines) is the largest content file. Branching trees with choices, silence triggers, Ma values, spirit whispers. `DataLoader.load_dialogues()` parses to `Dictionary[String, DialogueTree]`. No content rewriting needed — only the parser and renderer change.
## 6. Implementation Phases

Each phase produces a playable build that demonstrates progress — not a tech demo, but something that communicates the feeling of the game.

---

### Phase 0: Project Setup (Foundation)

**Goal:** Godot project that runs, opens a window, loads all game data.

- Create Godot 4.3 project: 320x240 native resolution, 3x integer scale, nearest-neighbor filtering
- Establish directory structure: `scenes/`, `scripts/`, `assets/`, `shaders/`, `resources/`, `data/`
- Copy existing `data/` directory unchanged
- Implement three core autoloads: `DataLoader`, `GameState`, `EventBus`
- Fix all YAML key mismatches (district_id → id, etc.)
- **Deliverable:** Console output confirming all content loaded — 23 spirits, 10 districts, 17 tracks, 49 materials, 20 recipes, 12+ puzzles. No warnings.

---

### Phase 1: Walk Around Kichijoji

**Goal:** Aoi walks the starting map. Movement feels good. Ma responds to stillness.

- Build Kichijoji TileMap from YAML tile data (material + spirit layers)
- Create Player scene: `CharacterBody2D`, placeholder sprite, collision shape
- Smooth 8-directional movement with walk/run/sneak speeds
- `Camera2D` with position smoothing and map-bounds clamping
- Basic HUD: Ma bar (fills when still, drains when moving), time-of-day label
- `Area2D` interaction zones on NPCs and objects
- Floating interaction prompts ("[Z] Talk")
- Spirit vision toggle (S key) — spirit TileMapLayer appears
- **Deliverable:** Walk the full Kichijoji map, watch Ma fill at the jizo statue, toggle spirit vision.

---

### Phase 2: Talk to People

**Goal:** Full dialogue system. Grandmother conversation with three branches. Ma earned through silence.

- `DialogueBox` scene: `RichTextLabel` with character-by-character reveal, choice buttons
- Dialogue tree engine: load from YAML, traverse nodes, evaluate conditions
- Silence mechanic: timer runs while dialogue is open and no input pressed; Ma accumulates
- NPC scenes with idle animation and schedule data
- Place Grandmother (9,4) and Mikan (6,5) with interaction zones
- Spirit whisper overlay (faint text when permeability is high)
- Toast notifications ("Ma +5" feedback)
- **Deliverable:** Complete Grandmother's morning conversation (all 3 branches). Sit in silence, watch Ma accumulate. Pet Mikan.

---

### Phase 3: The World Breathes

**Goal:** Day/night cycle. The world responds to time.

- `WorldClock` ticks forward; time-of-day enum drives lighting and NPC behavior
- `CanvasModulate` shifts color temperature (warm amber at dusk, cold blue at witching hour)
- Grandmother moves indoors after dusk (schedule system)
- Atmospheric exploration events (fox at crosswalk, self-folding cranes)
- Environmental audio loops per location and time
- Moon phase tracking, season system
- **Deliverable:** Stand in the garden from morning through nightfall. Lighting shifts, spirits emerge, ambient sound changes. Grandmother goes inside.

---

### Phase 4: Spirit Encounters

**Goal:** Meet spirits. Fight or befriend them.

- Spirit entities on map, visible at permeability thresholds
- Combat initiation on proximity
- Real-time combat: 3-hit combo, dodge roll, charged attack
- Ma Burst mechanic (stillness → time-slow → power)
- Ring menu for Spirit Art selection (3-4 starter arts)
- Negotiation system (speak/observe/silence → stance progression)
- Spirit bond formation on successful negotiation
- Corruption shader, purification mechanic
- **Deliverable:** Find the Kodama in the garden, choose silence over combat, form the first spirit bond.

---

### Phase 5: Crafting and Puzzles

**Goal:** Craft items, solve puzzles, save/load game.

- Crafting workshop UI (material selection, recipe matching, outcomes)
- Material gathering from exploration interactions
- Puzzle scenes (Ma silence puzzles, dual-layer puzzles)
- Place 2-3 puzzles in Kichijoji
- Save/load system (9 slots + autosave)
- Pause menu with save option
- Inventory and Bestiary UIs
- **Deliverable:** Craft Grandmother's tea blend, solve the garden gate puzzle, save and reload.

---

### Phase 6: Expand the World

**Goal:** Travel beyond Kichijoji. Story progresses.

- District travel system (train/walk/spirit path)
- Build 2-3 additional district maps (Shibuya, Asakusa, Shinjuku)
- Main story Chapters 1-2 quest progression
- Side quests with branching outcomes
- Vignette system (Evening Tea, The Last Train)
- Place additional NPCs (Ren, Yuki, Archivist)
- **Deliverable:** Travel to Shibuya, complete Chapter 1, experience first vignette.

---

### Phase 7: Polish and Ship

**Goal:** Complete game experience.

- All 10 districts with maps
- Chapters 3-7 of main story
- All side quests and vignettes
- Boss encounters
- Multiple endings
- Full soundtrack (17 tracks, 4 layers each)
- Complete pixel art
- Title screen, credits, game over
- Testing and balancing

---

### Priority Matrix

| Must Have (Phases 0-2) | Should Have (Phases 3-4) | Nice to Have (Phases 5+) |
|------------------------|-------------------------|--------------------------|
| Smooth movement | Day/night cycle | All 10 districts |
| Ma accumulation | Action combat | Full 17-track soundtrack |
| Dialogue system | Spirit encounters | Moon phase modulation |
| Spirit vision toggle | Negotiation/bonding | Crafting edge cases |
| Kichijoji map | Atmospheric events | Multiple endings |
| Grandmother dialogue | Ambient audio | Bestiary completion |
| Interaction system | Basic Spirit Arts | Curious craft items |

**Phases 0–4 are the critical path.** A game that ends at Phase 4 is a coherent, playable experience. Everything after deepens it.
