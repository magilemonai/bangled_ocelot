"""
Ma no Kuni - Quest System

Every quest is a thread in the fabric between worlds. Some threads are silk -
the main story, pulling taut toward resolution. Some are spider-web thin -
side stories that glimmer only when the light catches them. Some are invisible
until you stop moving and let the stillness reveal them.

Quest types:
    MAIN        - The central story of Aoi and the convergence
    SIDE        - Stories of the people and spirits of Tokyo
    SPIRIT      - Quests given by spirits, often wordless
    RELATIONSHIP - Deepening bonds with companions
    HIDDEN      - Revealed only through ma, stillness, or specific conditions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class QuestType(Enum):
    """The nature of a story thread."""
    MAIN = "main"
    SIDE = "side"
    SPIRIT = "spirit"
    RELATIONSHIP = "relationship"
    HIDDEN = "hidden"


class QuestStatus(Enum):
    """Where a quest lives in the arc of telling."""
    UNKNOWN = "unknown"         # Not yet revealed to the player
    AVAILABLE = "available"     # Conditions met, waiting to be discovered
    DISCOVERED = "discovered"   # Player knows it exists but hasn't started
    ACTIVE = "active"           # In progress
    COMPLETED = "completed"     # Finished - one of potentially many outcomes
    FAILED = "failed"           # Time ran out, or choices closed this path
    ABANDONED = "abandoned"     # Player chose to walk away


class QuestUrgency(Enum):
    """Some stories wait forever. Some do not."""
    ETERNAL = "eternal"         # Will wait for the player indefinitely
    PATIENT = "patient"         # Has a generous but real deadline
    PRESSING = "pressing"       # Days, not weeks
    URGENT = "urgent"           # Must be addressed soon
    CRITICAL = "critical"       # The moment is now or never


@dataclass
class QuestCondition:
    """
    A condition that must be met for a quest to become available,
    for an objective to unlock, or for a branch to open.
    """
    condition_type: str         # "flag", "quest", "relationship", "permeability",
                                # "time", "ma", "item", "location", "chapter"
    target: str                 # What to check
    operator: str = "gte"       # "eq", "neq", "gt", "gte", "lt", "lte", "exists"
    value: object = True        # What to compare against

    def evaluate(self, game_state) -> bool:
        """Check if this condition is currently met."""
        actual = self._get_actual_value(game_state)

        if self.operator == "exists":
            return actual is not None
        elif self.operator == "eq":
            return actual == self.value
        elif self.operator == "neq":
            return actual != self.value
        elif self.operator == "gt":
            return actual > self.value
        elif self.operator == "gte":
            return actual >= self.value
        elif self.operator == "lt":
            return actual < self.value
        elif self.operator == "lte":
            return actual <= self.value
        return False

    def _get_actual_value(self, game_state) -> object:
        """Retrieve the current value from game state."""
        if self.condition_type == "flag":
            return game_state.flags.get(self.target)
        elif self.condition_type == "quest":
            quest_sys = game_state.systems.get("narrative")
            if quest_sys:
                quest = quest_sys.get_quest(self.target)
                if quest:
                    return quest.status.value
            return None
        elif self.condition_type == "relationship":
            # Relationship level with a character
            return game_state.flags.get(f"relationship_{self.target}", 0)
        elif self.condition_type == "permeability":
            if game_state.current_district:
                return game_state.spirit_tide.get_local_level(
                    game_state.current_district, game_state.clock
                )
            return game_state.clock.spirit_permeability
        elif self.condition_type == "time":
            return game_state.clock.time_of_day.value
        elif self.condition_type == "ma":
            if self.target == "current":
                return game_state.ma.current_ma
            elif self.target == "lifetime":
                return game_state.ma.lifetime_ma
        elif self.condition_type == "item":
            # Check player inventory
            if game_state.player and hasattr(game_state.player, 'inventory'):
                return game_state.player.inventory.has(self.target)
            return False
        elif self.condition_type == "location":
            return game_state.current_district
        elif self.condition_type == "chapter":
            return game_state.flags.get("current_chapter", 1)
        return None


@dataclass
class QuestObjective:
    """
    A single step within a quest. Some objectives are clear tasks.
    Others are simply: wait. Listen. Be present.
    """
    id: str
    description: str
    hint: Optional[str] = None
    completed: bool = False
    optional: bool = False
    hidden: bool = False        # Revealed only when conditions met
    conditions_to_reveal: list[QuestCondition] = field(default_factory=list)
    conditions_to_complete: list[QuestCondition] = field(default_factory=list)

    # Some objectives are about stillness
    requires_ma: Optional[float] = None     # Minimum ma to complete
    requires_time: Optional[str] = None     # Time of day requirement
    requires_location: Optional[str] = None

    # Narrative content
    on_complete_text: Optional[str] = None
    on_complete_flags: dict = field(default_factory=dict)

    def check_completion(self, game_state) -> bool:
        """Check if this objective's completion conditions are met."""
        if self.completed:
            return True

        # Check ma requirement
        if self.requires_ma is not None:
            if game_state.ma.current_ma < self.requires_ma:
                return False

        # Check time requirement
        if self.requires_time is not None:
            if game_state.clock.time_of_day.value != self.requires_time:
                return False

        # Check location requirement
        if self.requires_location is not None:
            if game_state.current_district != self.requires_location:
                return False

        # Check explicit conditions
        return all(c.evaluate(game_state) for c in self.conditions_to_complete)

    def complete(self, game_state) -> None:
        """Mark this objective as done. Set any resulting flags."""
        self.completed = True
        for flag_name, flag_value in self.on_complete_flags.items():
            game_state.set_flag(flag_name, flag_value)

    def check_reveal(self, game_state) -> bool:
        """Check if a hidden objective should now be visible."""
        if not self.hidden:
            return True
        return all(c.evaluate(game_state) for c in self.conditions_to_reveal)


@dataclass
class QuestBranch:
    """
    A branching point in a quest. Choices have weight here.
    Some branches close forever. Some open new worlds.
    """
    id: str
    description: str
    options: list[QuestBranchOption] = field(default_factory=list)
    chosen: Optional[str] = None
    conditions_to_appear: list[QuestCondition] = field(default_factory=list)

    # Some branches only appear during ma
    requires_ma: Optional[float] = None
    time_limit_days: Optional[int] = None   # None = no limit
    day_appeared: Optional[int] = None

    def is_available(self, game_state) -> bool:
        """Can this branch be reached right now?"""
        if self.chosen is not None:
            return False  # Already decided
        if self.requires_ma is not None:
            if game_state.ma.current_ma < self.requires_ma:
                return False
        if self.time_limit_days is not None and self.day_appeared is not None:
            if game_state.clock.day - self.day_appeared > self.time_limit_days:
                return False
        return all(c.evaluate(game_state) for c in self.conditions_to_appear)

    def choose(self, option_id: str, game_state) -> Optional[QuestBranchOption]:
        """Make a choice. Some doors close behind you."""
        for option in self.options:
            if option.id == option_id:
                self.chosen = option_id
                for flag_name, flag_value in option.on_choose_flags.items():
                    game_state.set_flag(flag_name, flag_value)
                return option
        return None


@dataclass
class QuestBranchOption:
    """A single choice within a branching point."""
    id: str
    text: str
    description: str
    consequence_text: Optional[str] = None   # Shown after choosing
    next_objectives: list[str] = field(default_factory=list)  # Objective IDs unlocked
    closes_objectives: list[str] = field(default_factory=list)  # Objective IDs closed
    on_choose_flags: dict = field(default_factory=dict)
    conditions: list[QuestCondition] = field(default_factory=list)

    # Relationship impacts
    relationship_changes: dict[str, int] = field(default_factory=dict)

    # Some choices are only visible during stillness
    requires_ma: Optional[float] = None

    def is_available(self, game_state) -> bool:
        """Can this option be chosen?"""
        if self.requires_ma is not None:
            if game_state.ma.current_ma < self.requires_ma:
                return False
        return all(c.evaluate(game_state) for c in self.conditions)


@dataclass
class QuestReward:
    """What you receive. Not always items. Sometimes understanding."""
    items: list[str] = field(default_factory=list)
    experience: int = 0
    ma_bonus: float = 0.0
    relationship_changes: dict[str, int] = field(default_factory=dict)
    flags: dict = field(default_factory=dict)
    spirit_affinity: Optional[str] = None    # Befriend a specific spirit
    unlock_area: Optional[str] = None
    unlock_ability: Optional[str] = None
    narrative_text: Optional[str] = None     # The real reward is often a sentence


@dataclass
class Quest:
    """
    A quest - a story being told through play.

    Some quests are grand arcs spanning the game. Some are a single
    conversation with a spirit who has been waiting centuries for someone
    to listen. The system treats both with equal care.
    """
    id: str
    title: str
    quest_type: QuestType
    status: QuestStatus = QuestStatus.UNKNOWN

    # Narrative content
    description: str = ""
    short_description: str = ""
    chapter: Optional[int] = None            # For main quests
    journal_entries: list[str] = field(default_factory=list)

    # Structure
    objectives: list[QuestObjective] = field(default_factory=list)
    branches: list[QuestBranch] = field(default_factory=list)

    # Requirements
    prerequisites: list[QuestCondition] = field(default_factory=list)
    min_permeability: Optional[float] = None  # Spirit tide level needed
    required_time: Optional[str] = None       # Time of day
    required_location: Optional[str] = None
    required_chapter: Optional[int] = None

    # Timing
    urgency: QuestUrgency = QuestUrgency.ETERNAL
    deadline_day: Optional[int] = None
    day_started: Optional[int] = None

    # Rewards
    rewards: QuestReward = field(default_factory=QuestReward)

    # Ma integration
    requires_ma_to_discover: Optional[float] = None  # Ma threshold to find this quest
    ma_on_complete: float = 0.0               # Ma granted on completion
    is_ma_triggered: bool = False             # Only appears during ma moments

    # Connections
    next_quests: list[str] = field(default_factory=list)  # Quest IDs to unlock
    blocks_quests: list[str] = field(default_factory=list)  # Quest IDs locked by this

    def check_prerequisites(self, game_state) -> bool:
        """Are all conditions met for this quest to become available?"""
        # Check chapter requirement
        if self.required_chapter is not None:
            current_chapter = game_state.flags.get("current_chapter", 1)
            if current_chapter < self.required_chapter:
                return False

        # Check permeability requirement
        if self.min_permeability is not None:
            if game_state.current_district:
                local = game_state.spirit_tide.get_local_level(
                    game_state.current_district, game_state.clock
                )
            else:
                local = game_state.clock.spirit_permeability
            if local < self.min_permeability:
                return False

        # Check ma discovery threshold
        if self.requires_ma_to_discover is not None:
            if game_state.ma.current_ma < self.requires_ma_to_discover:
                return False

        return all(p.evaluate(game_state) for p in self.prerequisites)

    def start(self, game_state) -> None:
        """Begin this quest."""
        self.status = QuestStatus.ACTIVE
        self.day_started = game_state.clock.day

    def update(self, game_state) -> list[str]:
        """
        Check quest state. Returns list of events.
        ('objective_complete', 'branch_available', 'quest_complete',
         'quest_failed', 'objective_revealed')
        """
        events = []

        if self.status != QuestStatus.ACTIVE:
            return events

        # Check deadline
        if self.deadline_day is not None:
            if game_state.clock.day > self.deadline_day:
                self.status = QuestStatus.FAILED
                events.append("quest_failed")
                return events

        # Check hidden objectives for reveal
        for obj in self.objectives:
            if obj.hidden and obj.check_reveal(game_state):
                obj.hidden = False
                events.append(f"objective_revealed:{obj.id}")

        # Check objective completion
        for obj in self.objectives:
            if not obj.completed and not obj.hidden and obj.check_completion(game_state):
                obj.complete(game_state)
                events.append(f"objective_complete:{obj.id}")

        # Check branch availability
        for branch in self.branches:
            if branch.chosen is None and branch.is_available(game_state):
                if branch.day_appeared is None:
                    branch.day_appeared = game_state.clock.day
                events.append(f"branch_available:{branch.id}")

        # Check if all required objectives are complete
        required_objectives = [o for o in self.objectives if not o.optional]
        if required_objectives and all(o.completed for o in required_objectives):
            self.status = QuestStatus.COMPLETED
            # Grant rewards
            self._grant_rewards(game_state)
            events.append("quest_complete")

        return events

    def _grant_rewards(self, game_state) -> None:
        """Bestow what was earned."""
        if self.ma_on_complete > 0:
            game_state.ma.accumulate(self.ma_on_complete, f"quest_complete:{self.id}")

        for flag_name, flag_value in self.rewards.flags.items():
            game_state.set_flag(flag_name, flag_value)

        for char_id, change in self.rewards.relationship_changes.items():
            current = game_state.flags.get(f"relationship_{char_id}", 0)
            game_state.set_flag(f"relationship_{char_id}", current + change)

        # Unlock next quests
        for quest_id in self.next_quests:
            game_state.set_flag(f"quest_unlocked_{quest_id}", True)

    @property
    def progress(self) -> float:
        """How far through this quest are we? 0.0 to 1.0."""
        required = [o for o in self.objectives if not o.optional]
        if not required:
            return 0.0
        completed = sum(1 for o in required if o.completed)
        return completed / len(required)

    @property
    def active_objectives(self) -> list[QuestObjective]:
        """The objectives currently visible and incomplete."""
        return [
            o for o in self.objectives
            if not o.completed and not o.hidden
        ]

    @property
    def completed_objectives(self) -> list[QuestObjective]:
        """What has already been accomplished."""
        return [o for o in self.objectives if o.completed]


@dataclass
class QuestLog:
    """
    The journal of stories. Some pages are filled with adventure.
    The most important pages are the ones left intentionally blank.
    """
    quests: dict[str, Quest] = field(default_factory=dict)
    completed_quest_ids: list[str] = field(default_factory=list)
    failed_quest_ids: list[str] = field(default_factory=list)
    hidden_quests_discovered: int = 0

    def add_quest(self, quest: Quest) -> None:
        """Add a quest to the log."""
        self.quests[quest.id] = quest

    def get_quest(self, quest_id: str) -> Optional[Quest]:
        """Retrieve a quest by ID."""
        return self.quests.get(quest_id)

    def get_active_quests(self, quest_type: Optional[QuestType] = None) -> list[Quest]:
        """Get all currently active quests, optionally filtered by type."""
        active = [q for q in self.quests.values() if q.status == QuestStatus.ACTIVE]
        if quest_type:
            active = [q for q in active if q.quest_type == quest_type]
        return active

    def get_available_quests(self) -> list[Quest]:
        """Quests that are available but not yet started."""
        return [
            q for q in self.quests.values()
            if q.status in (QuestStatus.AVAILABLE, QuestStatus.DISCOVERED)
        ]

    def update_all(self, game_state) -> list[dict]:
        """
        Update all active quests. Check for newly available quests.
        Returns a list of events for the event system.
        """
        all_events = []

        # Update active quests
        for quest in self.get_active_quests():
            events = quest.update(game_state)
            for event in events:
                all_events.append({"quest_id": quest.id, "event": event})
                if event == "quest_complete":
                    self.completed_quest_ids.append(quest.id)
                elif event == "quest_failed":
                    self.failed_quest_ids.append(quest.id)

        # Check unknown quests for availability
        for quest in self.quests.values():
            if quest.status == QuestStatus.UNKNOWN:
                if quest.check_prerequisites(game_state):
                    quest.status = QuestStatus.AVAILABLE
                    if quest.is_ma_triggered:
                        self.hidden_quests_discovered += 1
                    all_events.append({
                        "quest_id": quest.id,
                        "event": "quest_available",
                    })

        return all_events

    @property
    def completion_stats(self) -> dict:
        """How much of the world's story has been heard."""
        total = len(self.quests)
        if total == 0:
            return {"total": 0, "completed": 0, "failed": 0, "percentage": 0.0}
        return {
            "total": total,
            "completed": len(self.completed_quest_ids),
            "failed": len(self.failed_quest_ids),
            "active": len(self.get_active_quests()),
            "hidden_found": self.hidden_quests_discovered,
            "percentage": len(self.completed_quest_ids) / total * 100,
        }
