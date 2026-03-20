"""
Ma no Kuni - Relationship System

Relationships in this game are not meters to be filled.
They are living things -- complicated, sometimes contradictory,
capable of growing in unexpected directions.

Trust can exist without affinity. Understanding can exist
without trust. And sometimes the deepest bonds are the ones
where nothing needs to be said at all.

The system also tracks how NPCs feel about EACH OTHER.
Aoi exists in a web of relationships, not a series of
isolated connections.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ---------------------------------------------------------------------------
# Relationship axes
# ---------------------------------------------------------------------------

class RelationshipAxis(Enum):
    """
    The three dimensions of every relationship.
    Each tells a different story about what two people share.
    """
    TRUST = "trust"               # Do they believe in each other?
    AFFINITY = "affinity"         # Do they enjoy each other's company?
    UNDERSTANDING = "understanding"  # Do they truly see each other?


class RelationshipPhase(Enum):
    """
    Relationships evolve through phases. These aren't strictly linear --
    trust can break, understanding can deepen even as affinity wanes.
    But there are recognizable stages.
    """
    STRANGERS = "strangers"
    ACQUAINTANCES = "acquaintances"
    FAMILIAR = "familiar"
    BONDED = "bonded"
    INTIMATE = "intimate"           # Deep mutual knowledge, not necessarily romantic
    ESTRANGED = "estranged"         # Were close, now distant
    FRACTURED = "fractured"         # Actively broken
    RECONCILING = "reconciling"     # Healing what was broken


class BondType(Enum):
    """The nature of the connection."""
    FRIENDSHIP = "friendship"
    FAMILY = "family"
    MENTOR = "mentor"
    RIVAL = "rival"
    ROMANTIC = "romantic"
    SPIRITUAL = "spiritual"       # A bond with a spirit
    PROFESSIONAL = "professional"
    COMPLICATED = "complicated"   # Defies easy categorization


# ---------------------------------------------------------------------------
# Relationship events
# ---------------------------------------------------------------------------

class RelationshipEventType(Enum):
    """What caused the relationship to change?"""
    DIALOGUE = "dialogue"
    GIFT = "gift"
    QUEST = "quest"
    BETRAYAL = "betrayal"
    SACRIFICE = "sacrifice"
    SHARED_SILENCE = "shared_silence"   # Ma together
    SHARED_DANGER = "shared_danger"
    CONFESSION = "confession"
    TIME_TOGETHER = "time_together"
    TIME_APART = "time_apart"
    MEMORY_SHARED = "memory_shared"
    BOUNDARY_RESPECTED = "boundary_respected"
    BOUNDARY_CROSSED = "boundary_crossed"


@dataclass
class RelationshipEvent:
    """A single moment that shifted a relationship."""
    event_type: RelationshipEventType
    description: str
    axis_changes: dict[RelationshipAxis, float] = field(default_factory=dict)
    day: int = 0
    location: str = ""
    memory_id: Optional[str] = None  # Links to Aoi's memory system


# ---------------------------------------------------------------------------
# Core relationship
# ---------------------------------------------------------------------------

@dataclass
class Relationship:
    """
    A relationship between two characters.

    The three axes move independently. You can trust someone you don't
    understand. You can understand someone you don't like. The interplay
    between these axes creates the texture of every connection.
    """
    id: str
    character_a: str          # NPC id or "aoi"
    character_b: str          # NPC id or "aoi"
    bond_type: BondType

    # Core axes: -1.0 (hostile/aversion/misunderstanding) to 1.0 (deep trust/love/clarity)
    trust: float = 0.0
    affinity: float = 0.0
    understanding: float = 0.0

    phase: RelationshipPhase = RelationshipPhase.STRANGERS
    history: list[RelationshipEvent] = field(default_factory=list)
    flags: dict[str, bool] = field(default_factory=dict)

    # Thresholds for phase transitions
    _phase_thresholds: dict[RelationshipPhase, float] = field(default_factory=lambda: {
        RelationshipPhase.STRANGERS: -0.5,
        RelationshipPhase.ACQUAINTANCES: 0.0,
        RelationshipPhase.FAMILIAR: 0.2,
        RelationshipPhase.BONDED: 0.5,
        RelationshipPhase.INTIMATE: 0.8,
    })

    def modify(
        self,
        axis: RelationshipAxis,
        amount: float,
        event_type: RelationshipEventType,
        description: str = "",
        day: int = 0,
        memory_id: Optional[str] = None,
    ) -> tuple[float, Optional[RelationshipPhase]]:
        """
        Change a relationship axis. Returns (new_value, new_phase_or_None).

        Changes are dampened at extremes -- it's hard to move from
        0.9 to 1.0, easy to move from 0.0 to 0.1. Relationships
        resist perfection and resist total destruction equally.
        """
        current = self._get_axis(axis)

        # Dampen changes at extremes
        if amount > 0 and current > 0.7:
            amount *= 0.5
        elif amount < 0 and current < -0.7:
            amount *= 0.5

        new_value = max(-1.0, min(1.0, current + amount))
        self._set_axis(axis, new_value)

        # Record event
        event = RelationshipEvent(
            event_type=event_type,
            description=description,
            axis_changes={axis: amount},
            day=day,
            memory_id=memory_id,
        )
        self.history.append(event)

        # Check for phase transition
        old_phase = self.phase
        self._recalculate_phase()
        phase_change = self.phase if self.phase != old_phase else None

        return new_value, phase_change

    def modify_multiple(
        self,
        changes: dict[RelationshipAxis, float],
        event_type: RelationshipEventType,
        description: str = "",
        day: int = 0,
        memory_id: Optional[str] = None,
    ) -> Optional[RelationshipPhase]:
        """Modify multiple axes at once from a single event."""
        for axis, amount in changes.items():
            current = self._get_axis(axis)
            if amount > 0 and current > 0.7:
                amount *= 0.5
            elif amount < 0 and current < -0.7:
                amount *= 0.5
            self._set_axis(axis, max(-1.0, min(1.0, current + amount)))

        event = RelationshipEvent(
            event_type=event_type,
            description=description,
            axis_changes=changes,
            day=day,
            memory_id=memory_id,
        )
        self.history.append(event)

        old_phase = self.phase
        self._recalculate_phase()
        return self.phase if self.phase != old_phase else None

    def _get_axis(self, axis: RelationshipAxis) -> float:
        if axis == RelationshipAxis.TRUST:
            return self.trust
        elif axis == RelationshipAxis.AFFINITY:
            return self.affinity
        return self.understanding

    def _set_axis(self, axis: RelationshipAxis, value: float) -> None:
        if axis == RelationshipAxis.TRUST:
            self.trust = value
        elif axis == RelationshipAxis.AFFINITY:
            self.affinity = value
        else:
            self.understanding = value

    def _recalculate_phase(self) -> None:
        """
        Determine relationship phase from current axis values.
        Special phases (estranged, fractured, reconciling) are set by flags.
        """
        if self.flags.get("fractured"):
            self.phase = RelationshipPhase.FRACTURED
            return
        if self.flags.get("estranged"):
            if self.composite_score > 0.3:
                self.phase = RelationshipPhase.RECONCILING
                return
            self.phase = RelationshipPhase.ESTRANGED
            return

        score = self.composite_score
        if score >= 0.8:
            self.phase = RelationshipPhase.INTIMATE
        elif score >= 0.5:
            self.phase = RelationshipPhase.BONDED
        elif score >= 0.2:
            self.phase = RelationshipPhase.FAMILIAR
        elif score >= 0.0:
            self.phase = RelationshipPhase.ACQUAINTANCES
        else:
            self.phase = RelationshipPhase.STRANGERS

    @property
    def composite_score(self) -> float:
        """
        Overall relationship strength. Not a simple average --
        trust weighs slightly more because it's harder to earn.
        """
        return (self.trust * 0.4 + self.affinity * 0.3 + self.understanding * 0.3)

    @property
    def is_positive(self) -> bool:
        return self.composite_score > 0.0

    @property
    def is_strong(self) -> bool:
        return self.composite_score > 0.5

    @property
    def tension(self) -> float:
        """
        How much internal contradiction exists in this relationship.
        High trust but low affinity creates tension. So does high
        understanding with low trust. Tension creates drama.
        """
        values = [self.trust, self.affinity, self.understanding]
        if not values:
            return 0.0
        spread = max(values) - min(values)
        return spread

    def get_axis(self, axis: RelationshipAxis) -> float:
        return self._get_axis(axis)

    def recent_trend(self, lookback: int = 5) -> dict[RelationshipAxis, float]:
        """What direction has this relationship been moving recently?"""
        recent = self.history[-lookback:] if self.history else []
        trends: dict[RelationshipAxis, float] = {
            RelationshipAxis.TRUST: 0.0,
            RelationshipAxis.AFFINITY: 0.0,
            RelationshipAxis.UNDERSTANDING: 0.0,
        }
        for event in recent:
            for axis, change in event.axis_changes.items():
                trends[axis] += change
        return trends


# ---------------------------------------------------------------------------
# Group dynamics
# ---------------------------------------------------------------------------

@dataclass
class GroupDynamic:
    """
    How a set of NPCs interact as a group. Group quests and events
    are affected by the web of relationships between participants.
    """
    id: str
    members: list[str]         # NPC ids
    cohesion: float = 0.0      # How well the group works together
    tensions: list[tuple[str, str, str]] = field(default_factory=list)  # (npc_a, npc_b, reason)
    shared_history: list[str] = field(default_factory=list)  # Event descriptions

    def recalculate_cohesion(self, system: RelationshipSystem) -> float:
        """
        Group cohesion is the average of all pairwise relationships,
        minus penalties for active tensions.
        """
        if len(self.members) < 2:
            self.cohesion = 1.0
            return self.cohesion

        pair_scores: list[float] = []
        for i, member_a in enumerate(self.members):
            for member_b in self.members[i + 1:]:
                rel = system.get_relationship(member_a, member_b)
                if rel:
                    pair_scores.append(rel.composite_score)
                else:
                    pair_scores.append(0.0)  # Strangers contribute nothing

        base = sum(pair_scores) / len(pair_scores) if pair_scores else 0.0
        tension_penalty = len(self.tensions) * 0.1
        self.cohesion = max(-1.0, min(1.0, base - tension_penalty))
        return self.cohesion


# ---------------------------------------------------------------------------
# Relationship system
# ---------------------------------------------------------------------------

class RelationshipSystem:
    """
    Manages all relationships in the game.

    This is the connective tissue of the story. Every quest, every
    dialogue choice, every gift and betrayal and shared silence
    flows through here.
    """

    def __init__(self) -> None:
        self._relationships: dict[str, Relationship] = {}
        self._groups: dict[str, GroupDynamic] = {}
        self._pair_index: dict[tuple[str, str], str] = {}  # (a, b) -> rel_id

    def create_relationship(
        self,
        character_a: str,
        character_b: str,
        bond_type: BondType,
        initial_trust: float = 0.0,
        initial_affinity: float = 0.0,
        initial_understanding: float = 0.0,
        flags: Optional[dict[str, bool]] = None,
    ) -> Relationship:
        """Create a new relationship between two characters."""
        # Normalize the pair ordering for consistent lookups
        pair = tuple(sorted([character_a, character_b]))
        rel_id = f"rel_{pair[0]}_{pair[1]}"

        rel = Relationship(
            id=rel_id,
            character_a=pair[0],
            character_b=pair[1],
            bond_type=bond_type,
            trust=initial_trust,
            affinity=initial_affinity,
            understanding=initial_understanding,
            flags=flags or {},
        )
        rel._recalculate_phase()

        self._relationships[rel_id] = rel
        self._pair_index[(pair[0], pair[1])] = rel_id
        return rel

    def get_relationship(
        self, character_a: str, character_b: str
    ) -> Optional[Relationship]:
        """Get the relationship between two characters, if it exists."""
        pair = tuple(sorted([character_a, character_b]))
        rel_id = self._pair_index.get((pair[0], pair[1]))
        if rel_id:
            return self._relationships.get(rel_id)
        return None

    def get_or_create(
        self,
        character_a: str,
        character_b: str,
        bond_type: BondType = BondType.FRIENDSHIP,
    ) -> Relationship:
        """Get existing relationship or create a new one."""
        rel = self.get_relationship(character_a, character_b)
        if rel:
            return rel
        return self.create_relationship(character_a, character_b, bond_type)

    def get_all_for(self, character_id: str) -> list[Relationship]:
        """Get all relationships involving a character."""
        return [
            rel for rel in self._relationships.values()
            if character_id in (rel.character_a, rel.character_b)
        ]

    def get_strongest_bonds(self, character_id: str, count: int = 3) -> list[Relationship]:
        """Get the strongest relationships for a character."""
        rels = self.get_all_for(character_id)
        return sorted(rels, key=lambda r: r.composite_score, reverse=True)[:count]

    def get_most_tense(self, character_id: str) -> Optional[Relationship]:
        """Get the most internally conflicted relationship."""
        rels = self.get_all_for(character_id)
        if not rels:
            return None
        return max(rels, key=lambda r: r.tension)

    # -------------------------------------------------------------------
    # Group dynamics
    # -------------------------------------------------------------------

    def create_group(self, group_id: str, members: list[str]) -> GroupDynamic:
        group = GroupDynamic(id=group_id, members=members)
        group.recalculate_cohesion(self)
        self._groups[group_id] = group
        return group

    def get_group(self, group_id: str) -> Optional[GroupDynamic]:
        return self._groups.get(group_id)

    def add_group_tension(
        self, group_id: str, npc_a: str, npc_b: str, reason: str
    ) -> None:
        group = self._groups.get(group_id)
        if group:
            group.tensions.append((npc_a, npc_b, reason))
            group.recalculate_cohesion(self)

    def resolve_group_tension(
        self, group_id: str, npc_a: str, npc_b: str
    ) -> bool:
        """Resolve a tension. Returns True if a tension was found and removed."""
        group = self._groups.get(group_id)
        if not group:
            return False
        for tension in group.tensions:
            if set(tension[:2]) == {npc_a, npc_b}:
                group.tensions.remove(tension)
                group.recalculate_cohesion(self)
                return True
        return False

    # -------------------------------------------------------------------
    # Queries for the dialogue and quest systems
    # -------------------------------------------------------------------

    def how_does_a_feel_about_b(
        self, character_a: str, character_b: str
    ) -> dict[str, float]:
        """
        Summary of how character_a feels about character_b.
        Returns axis values and composite score.
        """
        rel = self.get_relationship(character_a, character_b)
        if not rel:
            return {"trust": 0.0, "affinity": 0.0, "understanding": 0.0, "composite": 0.0}
        return {
            "trust": rel.trust,
            "affinity": rel.affinity,
            "understanding": rel.understanding,
            "composite": rel.composite_score,
        }

    def would_npc_help(
        self, npc_id: str, asking_character: str, difficulty: float = 0.5
    ) -> bool:
        """
        Would an NPC agree to help? Based on trust and affinity,
        weighted against the difficulty of what's being asked.
        """
        rel = self.get_relationship(npc_id, asking_character)
        if not rel:
            return difficulty < 0.2  # Strangers might help with trivial things
        willingness = rel.trust * 0.6 + rel.affinity * 0.4
        return willingness > difficulty

    def check_relationship_condition(
        self,
        character_a: str,
        character_b: str,
        axis: RelationshipAxis,
        minimum: float,
    ) -> bool:
        """Check if a relationship meets a minimum threshold on an axis."""
        rel = self.get_relationship(character_a, character_b)
        if not rel:
            return minimum <= 0.0
        return rel.get_axis(axis) >= minimum


def create_initial_relationships() -> RelationshipSystem:
    """
    Set up the relationships that exist at the start of the game.
    Some connections are deep. Some are strained. Some haven't
    formed yet.
    """
    system = RelationshipSystem()

    # Aoi <-> Obaa-chan: deep family bond, warm but with unspoken layers
    system.create_relationship(
        "aoi", "obaa_chan", BondType.FAMILY,
        initial_trust=0.8, initial_affinity=0.9, initial_understanding=0.5,
    )

    # Aoi <-> Mikan: loyal companion
    system.create_relationship(
        "aoi", "mikan", BondType.FAMILY,
        initial_trust=0.7, initial_affinity=0.8, initial_understanding=0.3,
    )

    # Aoi <-> Kaito: estranged former best friend
    system.create_relationship(
        "aoi", "kaito", BondType.COMPLICATED,
        initial_trust=-0.1, initial_affinity=0.2, initial_understanding=0.1,
        flags={"estranged": True, "shared_childhood": True},
    )

    # Obaa-chan <-> Mikan: bonded pair
    system.create_relationship(
        "obaa_chan", "mikan", BondType.SPIRITUAL,
        initial_trust=0.9, initial_affinity=0.95, initial_understanding=0.7,
    )

    # Obaa-chan <-> The Archivist: an old, complicated connection
    system.create_relationship(
        "obaa_chan", "the_archivist", BondType.SPIRITUAL,
        initial_trust=0.3, initial_affinity=0.1, initial_understanding=0.4,
        flags={"old_promise": True},
    )

    # Ren <-> Kaito: mutual distrust
    system.create_relationship(
        "ren", "kaito", BondType.RIVAL,
        initial_trust=-0.4, initial_affinity=-0.3, initial_understanding=-0.2,
    )

    # Yuki <-> Kaito: adversarial (he wants her building)
    system.create_relationship(
        "yuki", "kaito", BondType.PROFESSIONAL,
        initial_trust=-0.3, initial_affinity=-0.1, initial_understanding=0.1,
    )

    # Yuki <-> Hinata: friendly regulars
    system.create_relationship(
        "yuki", "hinata", BondType.FRIENDSHIP,
        initial_trust=0.3, initial_affinity=0.4, initial_understanding=0.2,
    )

    # Hinata <-> Ren: mutual respect, cautious distance
    system.create_relationship(
        "hinata", "ren", BondType.FRIENDSHIP,
        initial_trust=0.1, initial_affinity=0.2, initial_understanding=0.15,
    )

    return system
