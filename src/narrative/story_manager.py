"""
Ma no Kuni - Story Manager

The weaver at the loom. This system coordinates quests, vignettes,
story flags, chapter progression, and the narrative pulse of the game.

It loads story content from YAML, instantiates quest and vignette objects,
tracks the player's journey through the narrative, and decides which
threads to pull at any given moment.

The story manager also maintains the concept of narrative rhythm -
after intense sequences, it favors quiet moments. After stillness,
it allows tension to build. Like breathing. Like ma.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Any

from src.narrative.quests import (
    Quest, QuestType, QuestStatus, QuestUrgency, QuestLog,
    QuestObjective, QuestBranch, QuestBranchOption,
    QuestCondition, QuestReward,
)
from src.narrative.vignettes import (
    Vignette, VignetteCategory, VignetteMood, VignetteInputMode,
    VignetteBeat, VignetteChoice, VignetteCondition,
    VignetteManager, VignetteHistory,
)


class NarrativePace(Enum):
    """The rhythm of storytelling. The game breathes."""
    QUIET = "quiet"           # Favor vignettes, ambient moments
    BUILDING = "building"     # Tension rising, side content available
    INTENSE = "intense"       # Main quest pressure, urgency
    CLIMACTIC = "climactic"   # Chapter climax, focused
    AFTERMATH = "aftermath"   # After a major event, processing time
    REFLECTIVE = "reflective" # Between chapters, open exploration


class ChapterState(Enum):
    """Where we are within a chapter's arc."""
    NOT_STARTED = "not_started"
    INTRODUCTION = "introduction"
    RISING = "rising"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    COMPLETE = "complete"


@dataclass
class Chapter:
    """A chapter of the story. Each one changes the world."""
    number: int
    title: str
    subtitle: str = ""
    description: str = ""
    state: ChapterState = ChapterState.NOT_STARTED

    # Quests belonging to this chapter
    main_quest_ids: list[str] = field(default_factory=list)
    side_quest_ids: list[str] = field(default_factory=list)
    spirit_quest_ids: list[str] = field(default_factory=list)

    # World changes when chapter begins
    on_start_flags: dict = field(default_factory=dict)
    global_permeability_change: float = 0.0
    district_changes: dict[str, float] = field(default_factory=dict)

    # Conditions to start next chapter
    completion_flags: list[str] = field(default_factory=list)

    # Narrative metadata
    estimated_duration_hours: float = 3.0
    vignettes_available: list[str] = field(default_factory=list)


@dataclass
class NarrativeEvent:
    """An event in the narrative timeline."""
    event_type: str           # "quest", "vignette", "chapter", "encounter", "flag"
    event_id: str
    day: int
    description: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class RelationshipState:
    """The state of Aoi's relationship with a character."""
    character_id: str
    character_name: str
    level: int = 0
    max_level: int = 10
    # Key moments in the relationship
    milestones: list[str] = field(default_factory=list)
    # What the relationship means narratively at each level
    level_descriptions: dict[int, str] = field(default_factory=dict)

    @property
    def depth_label(self) -> str:
        """A word for how deep this relationship runs."""
        if self.level <= 0:
            return "stranger"
        elif self.level <= 2:
            return "acquaintance"
        elif self.level <= 4:
            return "companion"
        elif self.level <= 6:
            return "confidant"
        elif self.level <= 8:
            return "kindred"
        else:
            return "bonded"


class StoryManager:
    """
    The narrative engine. It listens to the game state and responds
    with story - not by forcing events, but by creating the conditions
    for them. Like a gardener. Like a grandmother who knows when
    to speak and when to let the silence do the work.
    """

    def __init__(self):
        # Core systems
        self.quest_log: QuestLog = QuestLog()
        self.vignette_manager: VignetteManager = VignetteManager()

        # Chapter tracking
        self.chapters: dict[int, Chapter] = {}
        self.current_chapter: int = 1

        # Narrative state
        self.pace: NarrativePace = NarrativePace.QUIET
        self.timeline: list[NarrativeEvent] = []
        self.relationships: dict[str, RelationshipState] = {}

        # Pacing counters
        self._beats_since_vignette: int = 0
        self._beats_since_combat: int = 0
        self._beats_since_story_event: int = 0
        self._intensity_level: float = 0.0

        # Endings tracking
        self.ending_flags: dict[str, bool] = {}

    # ----------------------------------------------------------------
    # Loading content from YAML
    # ----------------------------------------------------------------

    def load_quests_from_yaml(self, yaml_data: dict) -> int:
        """
        Load quest definitions from parsed YAML data.
        Returns count of quests loaded.
        """
        count = 0
        for quest_data in yaml_data.get("quests", []):
            quest = self._build_quest(quest_data)
            self.quest_log.add_quest(quest)
            count += 1
        return count

    def load_chapters_from_yaml(self, yaml_data: dict) -> int:
        """Load chapter definitions from parsed YAML data."""
        count = 0
        for chapter_data in yaml_data.get("chapters", []):
            chapter = self._build_chapter(chapter_data)
            self.chapters[chapter.number] = chapter
            count += 1
        return count

    def load_vignettes_from_yaml(self, yaml_data: dict) -> int:
        """Load vignette definitions from parsed YAML data."""
        count = 0
        for vig_data in yaml_data.get("vignettes", []):
            vignette = self._build_vignette(vig_data)
            self.vignette_manager.register_vignette(vignette)
            count += 1
        return count

    def _build_quest(self, data: dict) -> Quest:
        """Construct a Quest from YAML data."""
        # Build objectives
        objectives = []
        for obj_data in data.get("objectives", []):
            objectives.append(QuestObjective(
                id=obj_data["id"],
                description=obj_data["description"],
                hint=obj_data.get("hint"),
                optional=obj_data.get("optional", False),
                hidden=obj_data.get("hidden", False),
                requires_ma=obj_data.get("requires_ma"),
                requires_time=obj_data.get("requires_time"),
                requires_location=obj_data.get("requires_location"),
                on_complete_text=obj_data.get("on_complete_text"),
                on_complete_flags=obj_data.get("on_complete_flags", {}),
                conditions_to_complete=[
                    self._build_condition(c)
                    for c in obj_data.get("conditions_to_complete", [])
                ],
                conditions_to_reveal=[
                    self._build_condition(c)
                    for c in obj_data.get("conditions_to_reveal", [])
                ],
            ))

        # Build branches
        branches = []
        for br_data in data.get("branches", []):
            options = []
            for opt_data in br_data.get("options", []):
                options.append(QuestBranchOption(
                    id=opt_data["id"],
                    text=opt_data["text"],
                    description=opt_data.get("description", ""),
                    consequence_text=opt_data.get("consequence_text"),
                    next_objectives=opt_data.get("next_objectives", []),
                    closes_objectives=opt_data.get("closes_objectives", []),
                    on_choose_flags=opt_data.get("on_choose_flags", {}),
                    relationship_changes=opt_data.get("relationship_changes", {}),
                    requires_ma=opt_data.get("requires_ma"),
                    conditions=[
                        self._build_condition(c)
                        for c in opt_data.get("conditions", [])
                    ],
                ))
            branches.append(QuestBranch(
                id=br_data["id"],
                description=br_data["description"],
                options=options,
                requires_ma=br_data.get("requires_ma"),
                time_limit_days=br_data.get("time_limit_days"),
                conditions_to_appear=[
                    self._build_condition(c)
                    for c in br_data.get("conditions_to_appear", [])
                ],
            ))

        # Build prerequisites
        prerequisites = [
            self._build_condition(c)
            for c in data.get("prerequisites", [])
        ]

        # Build rewards
        reward_data = data.get("rewards", {})
        rewards = QuestReward(
            items=reward_data.get("items", []),
            experience=reward_data.get("experience", 0),
            ma_bonus=reward_data.get("ma_bonus", 0.0),
            relationship_changes=reward_data.get("relationship_changes", {}),
            flags=reward_data.get("flags", {}),
            spirit_affinity=reward_data.get("spirit_affinity"),
            unlock_area=reward_data.get("unlock_area"),
            unlock_ability=reward_data.get("unlock_ability"),
            narrative_text=reward_data.get("narrative_text"),
        )

        return Quest(
            id=data["id"],
            title=data["title"],
            quest_type=QuestType(data.get("type", "side")),
            description=data.get("description", ""),
            short_description=data.get("short_description", ""),
            chapter=data.get("chapter"),
            journal_entries=data.get("journal_entries", []),
            objectives=objectives,
            branches=branches,
            prerequisites=prerequisites,
            min_permeability=data.get("min_permeability"),
            required_time=data.get("required_time"),
            required_location=data.get("required_location"),
            required_chapter=data.get("required_chapter"),
            urgency=QuestUrgency(data.get("urgency", "eternal")),
            rewards=rewards,
            requires_ma_to_discover=data.get("requires_ma_to_discover"),
            ma_on_complete=data.get("ma_on_complete", 0.0),
            is_ma_triggered=data.get("is_ma_triggered", False),
            next_quests=data.get("next_quests", []),
            blocks_quests=data.get("blocks_quests", []),
        )

    def _build_chapter(self, data: dict) -> Chapter:
        """Construct a Chapter from YAML data."""
        return Chapter(
            number=data["number"],
            title=data["title"],
            subtitle=data.get("subtitle", ""),
            description=data.get("description", ""),
            main_quest_ids=data.get("main_quest_ids", []),
            side_quest_ids=data.get("side_quest_ids", []),
            spirit_quest_ids=data.get("spirit_quest_ids", []),
            on_start_flags=data.get("on_start_flags", {}),
            global_permeability_change=data.get("global_permeability_change", 0.0),
            district_changes=data.get("district_changes", {}),
            estimated_duration_hours=data.get("estimated_duration_hours", 3.0),
            vignettes_available=data.get("vignettes_available", []),
            completion_flags=data.get("completion_flags", []),
        )

    def _build_vignette(self, data: dict) -> Vignette:
        """Construct a Vignette from YAML data."""
        # Build beats
        beats = []
        for beat_data in data.get("beats", []):
            choices = []
            for ch_data in beat_data.get("choices", []):
                choices.append(VignetteChoice(
                    id=ch_data["id"],
                    text=ch_data["text"],
                    next_beat=ch_data.get("next_beat", ""),
                    flags_set=ch_data.get("flags_set", {}),
                    relationship_changes=ch_data.get("relationship_changes", {}),
                    ma_bonus=ch_data.get("ma_bonus", 0.0),
                    is_silence=ch_data.get("is_silence", False),
                ))
            beats.append(VignetteBeat(
                id=beat_data["id"],
                content_type=beat_data.get("content_type", "text"),
                text=beat_data.get("text"),
                speaker=beat_data.get("speaker"),
                inner_thought=beat_data.get("inner_thought", False),
                sound=beat_data.get("sound"),
                music_shift=beat_data.get("music_shift"),
                visual_direction=beat_data.get("visual_direction"),
                lighting=beat_data.get("lighting"),
                duration=beat_data.get("duration", 0.0),
                auto_advance=beat_data.get("auto_advance", False),
                ma_accumulation=beat_data.get("ma_accumulation", 1.0),
                choices=choices,
                condition_flag=beat_data.get("condition_flag"),
                condition_value=beat_data.get("condition_value", True),
            ))

        # Build conditions
        cond_data = data.get("conditions", {})
        conditions = VignetteCondition(
            location=cond_data.get("location"),
            locations=cond_data.get("locations", []),
            time_of_day=cond_data.get("time_of_day"),
            times_of_day=cond_data.get("times_of_day", []),
            season=cond_data.get("season"),
            min_permeability=cond_data.get("min_permeability", 0.0),
            max_permeability=cond_data.get("max_permeability", 1.0),
            min_ma=cond_data.get("min_ma", 0.0),
            min_lifetime_ma=cond_data.get("min_lifetime_ma", 0.0),
            required_flags=cond_data.get("required_flags", {}),
            forbidden_flags=cond_data.get("forbidden_flags", []),
            required_chapter=cond_data.get("required_chapter"),
            min_relationship=cond_data.get("min_relationship", {}),
            not_seen_in_days=cond_data.get("not_seen_in_days", 0),
            max_times_seen=cond_data.get("max_times_seen"),
            requires_stillness=cond_data.get("requires_stillness", 0.0),
        )

        return Vignette(
            id=data["id"],
            title=data["title"],
            category=VignetteCategory(data.get("category", "domestic")),
            mood=VignetteMood(data.get("mood", "peaceful")),
            input_mode=VignetteInputMode(data.get("input_mode", "observe")),
            description=data.get("description", ""),
            journal_entry=data.get("journal_entry"),
            beats=beats,
            conditions=conditions,
            ambient_sound=data.get("ambient_sound"),
            music_track=data.get("music_track"),
            weather_override=data.get("weather_override"),
            time_scale=data.get("time_scale", 0.3),
            ma_reward=data.get("ma_reward", 5.0),
            relationship_rewards=data.get("relationship_rewards", {}),
            flags_on_complete=data.get("flags_on_complete", {}),
            flags_on_skip=data.get("flags_on_skip", {}),
            unlocks_quest=data.get("unlocks_quest"),
            priority=data.get("priority", 0),
            weight=data.get("weight", 1.0),
            leads_to=data.get("leads_to"),
            blocks=data.get("blocks", []),
        )

    def _build_condition(self, data: dict) -> QuestCondition:
        """Build a QuestCondition from YAML data."""
        return QuestCondition(
            condition_type=data["type"],
            target=data["target"],
            operator=data.get("operator", "gte"),
            value=data.get("value", True),
        )

    # ----------------------------------------------------------------
    # Initialization
    # ----------------------------------------------------------------

    def initialize_relationships(self) -> None:
        """Set up the relationship tracking for key characters."""
        characters = {
            "haruki": RelationshipState(
                character_id="haruki",
                character_name="Grandmother Haruki",
                level=6,  # Already deep - they live together
                level_descriptions={
                    6: "Aoi and Haruki share a home and a careful tenderness. "
                       "There are things unsaid between them - a silence that is "
                       "both protection and wall.",
                    8: "The secrets are surfacing. The silence between them is "
                       "changing from avoidance to understanding.",
                    10: "They have seen each other fully now. The silence between "
                        "them is no longer a wall. It is a room they both live in.",
                },
            ),
            "ren": RelationshipState(
                character_id="ren",
                character_name="Ren",
                level=0,
                level_descriptions={
                    2: "A shrine keeper who sees what Aoi sees. There is relief "
                       "in being believed.",
                    5: "Trust, built carefully. Ren knows the spirit world's "
                       "protocols. Aoi knows its heart.",
                    8: "Something unspoken. Something that lives in the ma "
                       "between their conversations.",
                    10: "Whatever this is, it is real. It exists in both worlds.",
                },
            ),
            "kaito": RelationshipState(
                character_id="kaito",
                character_name="Kaito",
                level=2,  # Estranged family, some residual bond
                level_descriptions={
                    2: "Aoi's parent. Estranged. The distance between them is "
                       "measured in years of silence.",
                    5: "Reaching across the gap. Every conversation is a bridge "
                       "built from both sides.",
                    8: "Forgiveness is not a single act. It is a daily practice. "
                       "They are practicing.",
                    10: "Family, redefined. Not as it was. As it needs to be.",
                },
            ),
            "mikan": RelationshipState(
                character_id="mikan",
                character_name="Mikan",
                level=8,  # The cat already loves Aoi
                level_descriptions={
                    8: "Mikan sleeps on Aoi's chest and sees things they cannot. "
                       "The cat's purr is a frequency between worlds.",
                    10: "Familiar, in every sense of the word. Mikan walks in "
                        "both worlds as easily as walking from room to room.",
                },
            ),
        }
        self.relationships = characters

    # ----------------------------------------------------------------
    # Runtime
    # ----------------------------------------------------------------

    def update(self, delta: float, game_state=None) -> list[dict]:
        """
        The narrative heartbeat. Called each game tick.
        Returns events that occurred.
        """
        if game_state is None:
            return []

        events = []

        # Update quest log
        quest_events = self.quest_log.update_all(game_state)
        events.extend(quest_events)

        # Update pacing
        self._update_pace(game_state, quest_events)

        # Sync relationship levels from flags
        self._sync_relationships(game_state)

        # Check chapter transitions
        chapter_event = self._check_chapter_transition(game_state)
        if chapter_event:
            events.append(chapter_event)

        # Record significant events
        for event in quest_events:
            if event.get("event") in ("quest_complete", "quest_available"):
                self.timeline.append(NarrativeEvent(
                    event_type="quest",
                    event_id=event["quest_id"],
                    day=game_state.clock.day,
                    description=event["event"],
                ))

        # Update beat counters
        self._beats_since_vignette += 1
        self._beats_since_story_event += 1
        for event in events:
            if event.get("event") == "quest_complete":
                self._beats_since_story_event = 0

        return events

    def check_for_vignette(
        self, game_state, player_idle: bool = False, delta: float = 0.0
    ) -> Optional[Vignette]:
        """
        Ask the vignette system if a moment is ready.
        The story manager adds its own judgment: pacing, rhythm.
        """
        # Don't trigger vignettes too frequently
        if self._beats_since_vignette < 100:  # ~100 ticks minimum between
            return None

        # During climactic moments, suppress ambient vignettes
        if self.pace == NarrativePace.CLIMACTIC:
            return None

        vignette = self.vignette_manager.update(delta, game_state, player_idle)
        if vignette:
            self._beats_since_vignette = 0
        return vignette

    def _update_pace(self, game_state, recent_events: list[dict]) -> None:
        """Adjust narrative pacing based on what's happening."""
        chapter = self.chapters.get(self.current_chapter)
        if not chapter:
            return

        # Check for climactic state
        if chapter.state == ChapterState.CLIMAX:
            self.pace = NarrativePace.CLIMACTIC
            return

        # Check for aftermath
        if chapter.state == ChapterState.RESOLUTION:
            self.pace = NarrativePace.AFTERMATH
            return

        # Dynamic pacing
        active_urgent = [
            q for q in self.quest_log.get_active_quests()
            if q.urgency in (QuestUrgency.URGENT, QuestUrgency.CRITICAL)
        ]
        if active_urgent:
            self.pace = NarrativePace.INTENSE
        elif self._beats_since_story_event > 500:
            self.pace = NarrativePace.QUIET
        else:
            self.pace = NarrativePace.BUILDING

    def _sync_relationships(self, game_state) -> None:
        """Sync relationship objects with game state flags."""
        for char_id, rel in self.relationships.items():
            flag_val = game_state.flags.get(f"relationship_{char_id}", rel.level)
            rel.level = min(rel.max_level, max(0, flag_val))

    def _check_chapter_transition(self, game_state) -> Optional[dict]:
        """Check if it's time to advance to the next chapter."""
        chapter = self.chapters.get(self.current_chapter)
        if not chapter:
            return None

        if chapter.state == ChapterState.COMPLETE:
            return None

        # Check if all completion flags are set
        if chapter.completion_flags:
            all_met = all(
                game_state.flags.get(flag)
                for flag in chapter.completion_flags
            )
            if all_met and chapter.state != ChapterState.COMPLETE:
                chapter.state = ChapterState.COMPLETE
                return self._advance_chapter(game_state)

        return None

    def _advance_chapter(self, game_state) -> dict:
        """Move to the next chapter. The world shifts."""
        self.current_chapter += 1
        game_state.set_flag("current_chapter", self.current_chapter)

        next_chapter = self.chapters.get(self.current_chapter)
        event = {
            "event": "chapter_change",
            "new_chapter": self.current_chapter,
        }

        if next_chapter:
            next_chapter.state = ChapterState.INTRODUCTION
            event["title"] = next_chapter.title
            event["subtitle"] = next_chapter.subtitle

            # Apply world changes
            for flag, value in next_chapter.on_start_flags.items():
                game_state.set_flag(flag, value)

            if next_chapter.global_permeability_change:
                game_state.spirit_tide.global_level += (
                    next_chapter.global_permeability_change
                )

            for district, change in next_chapter.district_changes.items():
                current = game_state.spirit_tide.district_modifiers.get(district, 0.0)
                game_state.spirit_tide.district_modifiers[district] = current + change

            self.timeline.append(NarrativeEvent(
                event_type="chapter",
                event_id=f"chapter_{self.current_chapter}",
                day=game_state.clock.day,
                description=f"Chapter {self.current_chapter}: {next_chapter.title}",
            ))

        self.pace = NarrativePace.QUIET  # New chapters begin gently
        return event

    # ----------------------------------------------------------------
    # Query methods
    # ----------------------------------------------------------------

    def get_quest(self, quest_id: str) -> Optional[Quest]:
        """Retrieve a quest by ID."""
        return self.quest_log.get_quest(quest_id)

    def get_active_main_quests(self) -> list[Quest]:
        """Get currently active main story quests."""
        return self.quest_log.get_active_quests(QuestType.MAIN)

    def get_relationship(self, character_id: str) -> Optional[RelationshipState]:
        """Get relationship state with a character."""
        return self.relationships.get(character_id)

    def get_narrative_summary(self) -> dict:
        """A snapshot of where the story stands."""
        chapter = self.chapters.get(self.current_chapter)
        return {
            "chapter": self.current_chapter,
            "chapter_title": chapter.title if chapter else "Unknown",
            "chapter_state": chapter.state.value if chapter else "unknown",
            "pace": self.pace.value,
            "active_quests": len(self.quest_log.get_active_quests()),
            "completed_quests": len(self.quest_log.completed_quest_ids),
            "vignettes_witnessed": self.vignette_manager.history.total_witnessed,
            "relationships": {
                char_id: {
                    "name": rel.character_name,
                    "level": rel.level,
                    "depth": rel.depth_label,
                }
                for char_id, rel in self.relationships.items()
            },
            "timeline_length": len(self.timeline),
        }

    def get_ending_state(self) -> dict:
        """
        For Chapter 7 - determine which ending the player has earned.
        Based on relationships, choices, ma accumulated, spirits helped.
        """
        endings = {
            "bridge": False,       # Aoi becomes a permanent bridge
            "guardian": False,     # Aoi and allies guard the boundary
            "integration": False,  # The worlds merge peacefully
            "separation": False,   # The worlds are gently separated
            "ma": False,           # The true ending: living in the space between
        }

        haruki_rel = self.relationships.get("haruki")
        ren_rel = self.relationships.get("ren")
        kaito_rel = self.relationships.get("kaito")

        # The "ma" ending requires deep relationships, high lifetime ma,
        # and a history of choosing stillness over force
        if (haruki_rel and haruki_rel.level >= 9 and
                ren_rel and ren_rel.level >= 7 and
                kaito_rel and kaito_rel.level >= 6):
            endings["ma"] = True

        # Bridge ending: high spirit affinity, chose connection consistently
        endings["bridge"] = bool(
            self.ending_flags.get("chose_spirit_empathy") and
            self.ending_flags.get("archivist_knowledge_accepted")
        )

        # Guardian ending: balanced approach, strong allies
        endings["guardian"] = bool(
            ren_rel and ren_rel.level >= 8 and
            self.ending_flags.get("miraikan_confronted_peacefully")
        )

        # Integration ending: very high permeability acceptance
        endings["integration"] = bool(
            self.ending_flags.get("spirit_council_allied") and
            self.ending_flags.get("humans_prepared")
        )

        # Separation ending: chose containment, but gently
        endings["separation"] = bool(
            self.ending_flags.get("chose_gentle_separation") and
            kaito_rel and kaito_rel.level >= 7
        )

        return endings
