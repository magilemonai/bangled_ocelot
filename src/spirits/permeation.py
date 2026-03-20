"""
Ma no Kuni - Permeation System

Permeation is the measure of how thin the veil between worlds has become.

It is not binary. It is not even linear. It is a tide with currents and
eddies, affected by geography, time, emotion, and the actions of both
humans and spirits. When permeation rises, the impossible becomes routine.
When it falls, the spirit world recedes like a dream you can almost remember.

The permeation system tracks both the global state of the veil and the
local conditions in each district and location. As permeation rises through
the story, society transforms in ways that cascade through every layer
of human life.

Society does not simply "see spirits." It renegotiates reality.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from src.engine.game import WorldClock, Season, TimeOfDay, MoonPhase


# ---------------------------------------------------------------------------
# Permeation Tiers
# ---------------------------------------------------------------------------

class PermeationTier(Enum):
    """
    The five tiers of permeation, each a fundamentally different world state.
    These are not just visual changes - each tier reshapes society.
    """
    VEILED = "veiled"               # 0.0 - 0.2
    FLICKERING = "flickering"       # 0.2 - 0.4
    MANIFEST = "manifest"           # 0.4 - 0.6
    OVERLAPPING = "overlapping"     # 0.6 - 0.8
    CONVERGENCE = "convergence"     # 0.8 - 1.0

    @property
    def range(self) -> tuple[float, float]:
        ranges = {
            PermeationTier.VEILED: (0.0, 0.2),
            PermeationTier.FLICKERING: (0.2, 0.4),
            PermeationTier.MANIFEST: (0.4, 0.6),
            PermeationTier.OVERLAPPING: (0.6, 0.8),
            PermeationTier.CONVERGENCE: (0.8, 1.0),
        }
        return ranges[self]


# ---------------------------------------------------------------------------
# Societal Effects by Tier
# ---------------------------------------------------------------------------

@dataclass
class SocietalEffects:
    """
    How society transforms at a given permeation level. These are the
    second, third, and fourth order effects that make the world feel alive.

    Each tier doesn't just add spirits - it rewrites the social contract.
    """
    tier: PermeationTier

    # First order: direct sensory effects
    visibility: str = ""                # What people can see
    audibility: str = ""                # What people can hear
    physicality: str = ""               # How spirits interact with matter

    # Second order: immediate social responses
    media_response: str = ""            # News, social media, journalism
    government_response: str = ""       # Official policy and reaction
    religious_response: str = ""        # Shrines, temples, churches
    corporate_response: str = ""        # How businesses adapt

    # Third order: systemic changes
    economic_effects: list[str] = field(default_factory=list)
    infrastructure_effects: list[str] = field(default_factory=list)
    cultural_effects: list[str] = field(default_factory=list)
    psychological_effects: list[str] = field(default_factory=list)

    # Fourth order: deep structural shifts
    existential_effects: list[str] = field(default_factory=list)
    philosophical_shifts: list[str] = field(default_factory=list)
    power_structure_changes: list[str] = field(default_factory=list)

    # Gameplay effects
    exploration_modifiers: dict[str, float] = field(default_factory=dict)
    combat_modifiers: dict[str, float] = field(default_factory=dict)
    dialogue_unlocks: list[str] = field(default_factory=list)
    quest_unlocks: list[str] = field(default_factory=list)


def build_tier_effects() -> dict[PermeationTier, SocietalEffects]:
    """
    Build the complete societal effects table. This is the heart of
    worldbuilding encoded as game mechanics.
    """
    effects: dict[PermeationTier, SocietalEffects] = {}

    # ---- VEILED (0.0 - 0.2) ----
    effects[PermeationTier.VEILED] = SocietalEffects(
        tier=PermeationTier.VEILED,
        visibility="Only the gifted see spirits: Aoi, Mikan, shrine keepers, "
                   "certain children, the very old who remember",
        audibility="Faint whispers at shrines. Wind chimes ring without wind. "
                   "Cats stare at empty corners.",
        physicality="Spirits can nudge small objects. Candle flames flicker. "
                    "Dust motes swirl in patterns.",
        media_response="Occasional viral video of 'ghost sighting' dismissed as CGI. "
                       "Paranormal shows get slight ratings bump.",
        government_response="No official acknowledgment. Quiet funding increase for "
                            "cultural heritage preservation (front for monitoring).",
        religious_response="Shrine attendance slowly rising. Priests report 'stronger "
                          "spiritual presence.' Buddhist temples note more requests "
                          "for protective charms.",
        corporate_response="MIRAIKAN begins quiet acquisition of properties near "
                          "spiritually active sites. No public statement.",
        economic_effects=[
            "Slight increase in charm and talisman sales",
            "Property values near shrines begin subtle shift",
            "Traditional craftspeople report increased demand",
        ],
        infrastructure_effects=[
            "Occasional unexplained sensor glitches on trains",
            "Street lights flicker in spiritually active areas",
            "Certain vending machines develop 'personalities'",
        ],
        cultural_effects=[
            "Renewed interest in folklore and yokai stories",
            "Grandmother's tales taken slightly more seriously",
            "Art community produces increasingly spiritual work",
        ],
        psychological_effects=[
            "Sensitive individuals report vivid dreams",
            "Deja vu incidents increase citywide",
            "Children's imaginary friends become more detailed",
        ],
        existential_effects=[
            "A quiet unease, like the moment before an earthquake",
            "People begin questioning what they see from corners of their eyes",
        ],
        philosophical_shifts=[],
        power_structure_changes=[
            "Traditional spiritual authorities gain subtle influence",
        ],
        exploration_modifiers={
            "spirit_encounter_rate": 0.1,
            "hidden_path_visibility": 0.05,
        },
        combat_modifiers={
            "spirit_power_scale": 0.8,
        },
        dialogue_unlocks=["shrine_keeper_warnings", "grandmother_stories"],
        quest_unlocks=["investigate_flickering"],
    )

    # ---- FLICKERING (0.2 - 0.4) ----
    effects[PermeationTier.FLICKERING] = SocietalEffects(
        tier=PermeationTier.FLICKERING,
        visibility="Ordinary people catch glimpses: shadows that move wrong, "
                   "faces in reflections, shapes in peripheral vision. Most "
                   "dismiss it. Some cannot.",
        audibility="Murmuring near old buildings. Music from empty rooms. "
                   "Conversations that stop when you listen directly.",
        physicality="Spirits can move objects visibly. Doors open and close. "
                    "Items rearrange themselves. Electronics behave strangely.",
        media_response="Trending hashtags about 'Tokyo ghosts.' News runs segments "
                       "with skeptical framing. A few journalists take it seriously "
                       "and are mocked. Viral phone footage becomes undeniable.",
        government_response="Official denial but private task force established. "
                           "Police receive 'unusual incident' protocols. Diet members "
                           "quietly briefed. MIRAIKAN invited as consultant.",
        religious_response="Shrine priests openly discuss spiritual activity. "
                          "Some declare sacred territories. Temple attendance surges. "
                          "New Age movements flourish. Exorcism requests skyrocket.",
        corporate_response="MIRAIKAN launches 'spiritual energy research' publicly. "
                          "Tech companies develop spirit-detection apps (most fake). "
                          "Insurance companies quietly add exclusion clauses.",
        economic_effects=[
            "Spirit tourism becomes a real phenomenon",
            "Property values diverge: haunted sites drop, 'blessed' sites surge",
            "New industry: spiritual consulting for businesses",
            "Traditional medicine practitioners see increased demand",
            "Stock market experiences inexplicable micro-crashes during spirit surges",
        ],
        infrastructure_effects=[
            "Train delays from sensor interference become regular",
            "GPS unreliable in high-permeation areas",
            "Power grid fluctuations in spiritually active districts",
            "Some traffic lights begin responding to spirit traffic",
        ],
        cultural_effects=[
            "Yokai manga sales explode, authors consult actual witnesses",
            "A cultural divide: believers vs skeptics, tradition vs modernity",
            "Theater and film explore the theme obsessively",
            "Children begin incorporating spirits into daily play naturally",
        ],
        psychological_effects=[
            "Anxiety disorders increase, especially in sensitive areas",
            "New therapy specialization: spiritual adjustment counseling",
            "Some people develop ability to see spirits under stress",
            "Sleep disorders become epidemic near permeation hotspots",
        ],
        existential_effects=[
            "The materialist worldview cracks but doesn't shatter",
            "People begin to wonder what else they've been wrong about",
            "Nostalgia for 'normal' becomes a cultural force",
        ],
        philosophical_shifts=[
            "Animism becomes a serious philosophical position again",
            "Academic papers on 'post-materialist ontology' multiply",
        ],
        power_structure_changes=[
            "Shrine networks gain political influence",
            "MIRAIKAN positions itself as bridge between worlds",
            "Military quietly develops spirit-related protocols",
        ],
        exploration_modifiers={
            "spirit_encounter_rate": 0.3,
            "hidden_path_visibility": 0.2,
            "npc_spirit_reactions": 0.4,
        },
        combat_modifiers={
            "spirit_power_scale": 1.0,
            "environmental_hazard_rate": 0.15,
        },
        dialogue_unlocks=[
            "ordinary_npc_spirit_gossip",
            "media_investigation_leads",
            "miraikan_public_face",
        ],
        quest_unlocks=[
            "help_frightened_citizens",
            "investigate_spirit_surge",
            "media_interview",
        ],
    )

    # ---- MANIFEST (0.4 - 0.6) ----
    effects[PermeationTier.MANIFEST] = SocietalEffects(
        tier=PermeationTier.MANIFEST,
        visibility="Spirits clearly visible to most people. They walk the streets, "
                   "perch on rooftops, swim in the Sumida. Denial is no longer "
                   "possible. Tokyo has residents from two worlds.",
        audibility="Spirit voices audible to all. The city has a second soundscape. "
                   "Music from the spirit world bleeds through.",
        physicality="Spirits interact freely with material objects. Spirit weather "
                    "begins affecting the material world lightly. Rain smells "
                    "of memories.",
        media_response="24/7 coverage. Expert panels. International attention. "
                       "Some outlets try to maintain normalcy. Social media becomes "
                       "a mix of terror, wonder, and memes.",
        government_response="State of emergency declared then awkwardly rescinded. "
                           "New legislation drafted hastily. Spirit Affairs Bureau "
                           "established. International summit called.",
        religious_response="Shinto establishment asserts authority as 'always knew.' "
                          "Interfaith crisis as other religions adapt. Some declare "
                          "apocalypse. Others declare enlightenment.",
        corporate_response="MIRAIKAN is now a household name, offering 'spirit energy "
                          "solutions.' Other corporations scramble. Spirit-proof "
                          "construction, spirit-compatible electronics, spirit insurance.",
        economic_effects=[
            "Economic upheaval as entire industries are disrupted",
            "New economy: spirit-related goods and services boom",
            "Tourism floods in from around the world",
            "Property market chaos: some flee, others flock to Tokyo",
            "Traditional crafts become critical infrastructure",
            "Currency fluctuations as international markets react",
            "Spirit barter economy emerges alongside yen",
        ],
        infrastructure_effects=[
            "Train schedules adjusted for spirit traffic patterns",
            "Buildings begin developing spirit-world architectural features",
            "Some roads become impassable as geography warps slightly",
            "New infrastructure: spirit barriers, crossing points, safe zones",
            "Power plants near ley lines operate at unusual efficiency",
        ],
        cultural_effects=[
            "A cultural renaissance as artists channel spirit inspiration",
            "Schools add spirit awareness to curriculum",
            "Language evolves to include spirit concepts",
            "Fashion incorporates spirit-visible elements",
            "New music genres emerge from human-spirit collaboration",
        ],
        psychological_effects=[
            "Mass adjustment period: grief for the old world",
            "New sense of wonder for those who embrace change",
            "Spiritual sensitivity becomes a valued trait",
            "Support groups for those struggling to adapt",
            "Children adapt fastest, become cultural bridges",
        ],
        existential_effects=[
            "Materialism as a worldview collapses",
            "Death becomes a different question when spirits are visible",
            "The meaning of 'real' must be renegotiated",
            "History is rewritten as spiritual dimension is acknowledged",
        ],
        philosophical_shifts=[
            "New philosophies emerge integrating material and spiritual",
            "Science must expand its methods to include the spiritual",
            "Ethics must extend to non-human spiritual entities",
        ],
        power_structure_changes=[
            "Traditional spiritual authorities become political powers",
            "MIRAIKAN rivals government influence",
            "Spirit-human diplomatic relations begin",
            "New class divisions: the spirit-sensitive vs the spirit-blind",
        ],
        exploration_modifiers={
            "spirit_encounter_rate": 0.6,
            "hidden_path_visibility": 0.5,
            "npc_spirit_reactions": 0.8,
            "geography_warp": 0.1,
        },
        combat_modifiers={
            "spirit_power_scale": 1.2,
            "environmental_hazard_rate": 0.3,
            "spirit_ally_availability": 0.4,
        },
        dialogue_unlocks=[
            "spirit_npc_conversations",
            "government_briefings",
            "international_journalist",
            "miraikan_whistleblower_hints",
        ],
        quest_unlocks=[
            "spirit_diplomacy",
            "establish_crossing_point",
            "protect_manifest_district",
            "school_spirit_awareness",
        ],
    )

    # ---- OVERLAPPING (0.6 - 0.8) ----
    effects[PermeationTier.OVERLAPPING] = SocietalEffects(
        tier=PermeationTier.OVERLAPPING,
        visibility="The spirit world overlays the material in waves. Buildings "
                   "shimmer between their true form and spirit form. You can see "
                   "both worlds simultaneously, overlapping like double exposure.",
        audibility="Two soundscapes at once. Material and spiritual sounds "
                   "interweave. Conversations with spirits as natural as with humans.",
        physicality="Geography warps. A hallway might be longer in spirit-space. "
                    "Stairs lead to different floors depending on which world you "
                    "focus on. Spirit weather materially affects the world.",
        media_response="Media struggles to cover a reality that keeps shifting. "
                       "New forms of journalism emerge. Spirit-world correspondents. "
                       "The concept of 'news' must be redefined.",
        government_response="Governance is in crisis. Laws don't apply to spirits. "
                           "Territory is ambiguous. The Spirit Affairs Bureau is "
                           "overwhelmed. Military stands down after failed attempts.",
        religious_response="Religions transform or collapse. Those that adapt thrive. "
                          "New syncretic practices emerge. Shrine keepers become "
                          "critical community leaders.",
        corporate_response="MIRAIKAN's extraction operations visible and controversial. "
                          "Other corps develop spirit-world operations. Economic "
                          "models fail, new ones scramble to form.",
        economic_effects=[
            "Traditional economy partially breaks down",
            "Spirit economy grows to rival material economy",
            "Resources from the spirit world become tradeable",
            "Labor is redefined when spirits can do certain work",
            "Scarcity and abundance are reshuffled",
            "MIRAIKAN becomes an economic superpower",
        ],
        infrastructure_effects=[
            "City planning must account for two overlapping geographies",
            "Some buildings exist differently in each world",
            "Transit requires spirit-world routing algorithms",
            "Hospitals develop spirit-medical hybrid treatments",
            "Emergency services retrained for dual-world incidents",
        ],
        cultural_effects=[
            "Human culture and spirit culture begin merging",
            "Festivals become joint human-spirit celebrations",
            "Art is created collaboratively across the veil",
            "Language develops spirit-world vocabulary naturally",
            "Identity becomes more fluid between worlds",
        ],
        psychological_effects=[
            "Humanity collectively processes the death of the old worldview",
            "A generation grows up knowing both worlds",
            "Identity crises as some humans feel more spirit than material",
            "Deep peace for those who find harmony",
            "Deep anguish for those who cannot adapt",
        ],
        existential_effects=[
            "What does it mean to be human when spirits are people too?",
            "Memory, identity, death - all questioned at the deepest level",
            "The boundary between self and world becomes philosophical",
            "Some humans discover they have spirit aspects",
        ],
        philosophical_shifts=[
            "Dualism collapses - mind and matter were never separate",
            "Ethics must account for beings with fundamentally different natures",
            "Time itself is questioned as spirit-time bleeds through",
        ],
        power_structure_changes=[
            "Nation-states struggle with territorial sovereignty",
            "MIRAIKAN's true agenda begins to surface",
            "Greater spirits assert political claims",
            "Aoi and those like her become essential mediators",
            "The deeper corruption becomes visible to all",
        ],
        exploration_modifiers={
            "spirit_encounter_rate": 0.85,
            "hidden_path_visibility": 0.75,
            "npc_spirit_reactions": 1.0,
            "geography_warp": 0.4,
            "dual_world_navigation": True,
        },
        combat_modifiers={
            "spirit_power_scale": 1.5,
            "environmental_hazard_rate": 0.5,
            "spirit_ally_availability": 0.7,
            "reality_instability": 0.3,
        },
        dialogue_unlocks=[
            "greater_spirit_audiences",
            "government_desperation",
            "miraikan_inner_circle",
            "spirit_world_deep_lore",
        ],
        quest_unlocks=[
            "stabilize_district",
            "greater_spirit_negotiation",
            "miraikan_infiltration",
            "find_the_deeper_cause",
        ],
    )

    # ---- CONVERGENCE (0.8 - 1.0) ----
    effects[PermeationTier.CONVERGENCE] = SocietalEffects(
        tier=PermeationTier.CONVERGENCE,
        visibility="The worlds are nearly one. Material and spirit reality "
                   "flicker and merge. Looking at Tokyo, you see both its "
                   "concrete truth and its spiritual truth simultaneously. "
                   "The distinction between 'real' and 'unreal' dissolves.",
        audibility="All sounds are dual. Every voice has a spirit echo. "
                   "The city hums with a harmony or discord depending on "
                   "its spiritual health.",
        physicality="Reality is fluid. A building might be a tree might be "
                    "a memory might be a building again. Navigation requires "
                    "understanding both worlds. Physics negotiates with emotion.",
        media_response="Conventional media barely functions. Communication itself "
                       "transforms. Spirit-carried messages. Dream broadcasts. "
                       "The concept of information changes fundamentally.",
        government_response="Conventional governance impossible. New hybrid systems "
                           "emerge from necessity. Spirit-human councils. "
                           "Aoi's role as mediator becomes politically critical.",
        religious_response="Religion and daily life merge. Every act is spiritual. "
                          "The sacred is everywhere. Shrine keepers, priests, monks "
                          "are the most important people in the city.",
        corporate_response="MIRAIKAN's extraction is destroying the merged reality. "
                          "Its true purpose is revealed. Other corporations either "
                          "ally with spirits or with MIRAIKAN. No neutrality.",
        economic_effects=[
            "Economy transforms into something unrecognizable",
            "Value is measured in spiritual as well as material terms",
            "Scarcity itself changes when spirit resources exist",
            "MIRAIKAN's extraction threatens to drain everything",
        ],
        infrastructure_effects=[
            "Infrastructure is alive - buildings have spirits",
            "Transit happens through both worlds simultaneously",
            "Hospitals heal body and spirit together",
            "The city itself is becoming a living entity",
        ],
        cultural_effects=[
            "Culture is fully dual-world",
            "Art, music, food, daily life - all transformed",
            "Human and spirit cultures merge into something new",
            "History reveals itself as always having been dual",
        ],
        psychological_effects=[
            "Consciousness itself expands for those who adapt",
            "The division between waking and dreaming blurs",
            "Empathy extends across the species boundary",
            "Those who resist suffer spiritual claustrophobia",
        ],
        existential_effects=[
            "Humanity faces the question of what it becomes next",
            "The convergence could destroy both worlds or birth something new",
            "Individual identity and collective consciousness tension peaks",
            "The deeper cause of the convergence threatens everything",
        ],
        philosophical_shifts=[
            "All previous philosophies proved partially right",
            "A new understanding of reality is required to survive",
            "The answer may lie in ma - the space between",
        ],
        power_structure_changes=[
            "Power belongs to those who can navigate both worlds",
            "MIRAIKAN vs the Spirit of Tokyo - the final conflict",
            "Aoi stands at the convergence point",
            "The deeper cause reveals itself",
        ],
        exploration_modifiers={
            "spirit_encounter_rate": 1.0,
            "hidden_path_visibility": 1.0,
            "npc_spirit_reactions": 1.0,
            "geography_warp": 0.8,
            "dual_world_navigation": True,
            "reality_fluidity": 0.6,
        },
        combat_modifiers={
            "spirit_power_scale": 2.0,
            "environmental_hazard_rate": 0.7,
            "spirit_ally_availability": 1.0,
            "reality_instability": 0.6,
            "convergence_abilities": True,
        },
        dialogue_unlocks=[
            "spirit_of_tokyo",
            "the_deeper_truth",
            "convergence_choice",
            "all_spirits_accessible",
        ],
        quest_unlocks=[
            "final_confrontation",
            "convergence_decision",
            "save_or_merge_worlds",
            "the_truth_beneath",
        ],
    )

    return effects


# ---------------------------------------------------------------------------
# Local Permeation
# ---------------------------------------------------------------------------

@dataclass
class DistrictPermeation:
    """
    Permeation in a specific district of Tokyo. Each district has its own
    relationship with the spirit world based on its history, its current
    state, and what is happening there.
    """
    district_id: str
    district_name: str

    base_permeation: float = 0.0       # Inherent spiritual thinness
    current_modifier: float = 0.0      # Temporary effects
    story_modifier: float = 0.0        # Permanent changes from story events
    corruption_modifier: float = 0.0   # Corruption raises permeation chaotically

    # What makes this district spiritually significant
    spiritual_history: str = ""        # Buried river, old shrine, mass emotion
    active_shrines: int = 0            # Shrines anchor and stabilize permeation
    active_extraction_sites: int = 0   # MIRAIKAN sites destabilize

    # Hotspots within the district
    hotspot_locations: list[str] = field(default_factory=list)
    hotspot_modifiers: dict[str, float] = field(default_factory=dict)

    # Population awareness
    awareness_level: float = 0.0       # How aware are residents? 0-1
    fear_level: float = 0.0            # How afraid are residents? 0-1
    acceptance_level: float = 0.0      # How accepting are residents? 0-1

    @property
    def effective_permeation(self) -> float:
        """Total permeation for this district. Shrines stabilize, extraction destabilizes."""
        raw = (
            self.base_permeation
            + self.current_modifier
            + self.story_modifier
            + self.corruption_modifier
        )

        # Shrines provide stability (pull toward moderate levels)
        shrine_effect = self.active_shrines * 0.02
        if raw > 0.5:
            raw -= shrine_effect  # Shrines resist over-permeation
        else:
            raw += shrine_effect * 0.5  # Shrines maintain a floor

        # Extraction sites destabilize (push toward extremes)
        extraction_chaos = self.active_extraction_sites * 0.05
        raw += extraction_chaos

        return max(0.0, min(1.0, raw))

    def get_location_permeation(self, location_id: str) -> float:
        """Get permeation at a specific location within the district."""
        base = self.effective_permeation
        hotspot_mod = self.hotspot_modifiers.get(location_id, 0.0)
        return max(0.0, min(1.0, base + hotspot_mod))

    def update_awareness(self, permeation: float, delta: float) -> list[str]:
        """
        Update how the population reacts to current permeation.
        Returns event strings for notable shifts.
        """
        events: list[str] = []

        # Awareness grows with permeation
        target_awareness = permeation
        self.awareness_level += (target_awareness - self.awareness_level) * 0.01 * delta

        # Fear spikes with rapid changes, decays with stability
        if permeation > self.awareness_level + 0.2:
            self.fear_level = min(1.0, self.fear_level + 0.02 * delta)
            if self.fear_level > 0.7:
                events.append(f"panic_in_{self.district_id}")
        else:
            self.fear_level = max(0.0, self.fear_level - 0.005 * delta)

        # Acceptance grows slowly, faster if fear is low
        acceptance_rate = 0.003 if self.fear_level < 0.3 else 0.001
        if self.awareness_level > 0.3:
            self.acceptance_level = min(
                1.0, self.acceptance_level + acceptance_rate * delta
            )
            if self.acceptance_level > 0.5 and self.fear_level < 0.3:
                events.append(f"acceptance_growing_{self.district_id}")

        return events


@dataclass
class LocationPermeationEvent:
    """A specific event that affects permeation at a location."""
    event_id: str
    location_id: str
    district_id: str
    permeation_change: float           # Positive = more permeable
    duration: int                       # Turns this lasts, -1 = permanent
    remaining: int = -1
    cause: str = ""
    is_story_event: bool = False
    visual_effect: str = ""            # What the player sees
    sound_effect: str = ""             # What the player hears

    def __post_init__(self) -> None:
        if self.remaining == -1:
            self.remaining = self.duration

    @property
    def is_expired(self) -> bool:
        return self.duration != -1 and self.remaining <= 0

    def tick(self) -> bool:
        """Advance one tick. Returns True if still active."""
        if self.duration == -1:
            return True  # Permanent
        self.remaining -= 1
        return self.remaining > 0


# ---------------------------------------------------------------------------
# Permeation Engine
# ---------------------------------------------------------------------------

@dataclass
class PermeationEngine:
    """
    The master system governing permeation across all of Tokyo.

    This engine integrates with the WorldClock, SpiritTide, corruption
    systems, and narrative events to produce a living, breathing veil
    between worlds.
    """
    # Global state
    global_permeation: float = 0.1     # Story starts with thin veil
    story_permeation_floor: float = 0.1  # Minimum - rises with story progression
    story_permeation_ceiling: float = 0.3  # Maximum at current story stage

    # District tracking
    districts: dict[str, DistrictPermeation] = field(default_factory=dict)

    # Active events
    active_events: list[LocationPermeationEvent] = field(default_factory=list)

    # Tier effects table
    _tier_effects: dict[PermeationTier, SocietalEffects] = field(
        default_factory=dict
    )
    _current_tier: PermeationTier = PermeationTier.VEILED
    _previous_tier: Optional[PermeationTier] = None

    # Callbacks for tier transitions
    _tier_change_callbacks: list[Callable] = field(default_factory=list)

    # History for tracking progression
    permeation_history: list[tuple[int, float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self._tier_effects:
            self._tier_effects = build_tier_effects()

    def register_district(self, district: DistrictPermeation) -> None:
        """Register a district for permeation tracking."""
        self.districts[district.district_id] = district

    def register_tier_change_callback(self, callback: Callable) -> None:
        """Register a function to be called when the permeation tier changes."""
        self._tier_change_callbacks.append(callback)

    def add_event(self, event: LocationPermeationEvent) -> None:
        """Add a permeation-affecting event."""
        self.active_events.append(event)

        # Apply to relevant district
        district = self.districts.get(event.district_id)
        if district:
            if event.location_id in district.hotspot_modifiers:
                district.hotspot_modifiers[event.location_id] += event.permeation_change
            else:
                district.hotspot_modifiers[event.location_id] = event.permeation_change

    def advance_story_permeation(self, new_floor: float,
                                  new_ceiling: float) -> list[dict]:
        """
        Called by the narrative system when story events push the veil.
        The floor represents the minimum permeation level the story has
        established. The ceiling is how high it can currently go.
        """
        events: list[dict] = []
        old_floor = self.story_permeation_floor

        self.story_permeation_floor = max(self.story_permeation_floor, new_floor)
        self.story_permeation_ceiling = min(1.0, max(
            self.story_permeation_ceiling, new_ceiling
        ))

        # If the floor rose, push global permeation up
        if self.story_permeation_floor > old_floor:
            self.global_permeation = max(
                self.global_permeation,
                self.story_permeation_floor,
            )
            events.append({
                "type": "permeation_floor_raised",
                "old_floor": old_floor,
                "new_floor": self.story_permeation_floor,
            })

        # Check for tier change
        tier_event = self._check_tier_change()
        if tier_event:
            events.append(tier_event)

        return events

    def get_tier(self, permeation: Optional[float] = None) -> PermeationTier:
        """Get the permeation tier for a given level."""
        level = permeation if permeation is not None else self.global_permeation
        for tier in PermeationTier:
            low, high = tier.range
            if low <= level < high:
                return tier
        return PermeationTier.CONVERGENCE

    def get_current_effects(self) -> SocietalEffects:
        """Get the societal effects for the current global tier."""
        return self._tier_effects[self._current_tier]

    def get_district_permeation(self, district_id: str) -> float:
        """Get effective permeation for a district, bounded by story limits."""
        district = self.districts.get(district_id)
        if not district:
            return self.global_permeation

        raw = district.effective_permeation + self.global_permeation
        return max(
            self.story_permeation_floor,
            min(self.story_permeation_ceiling, raw),
        )

    def get_location_permeation(self, district_id: str,
                                 location_id: str) -> float:
        """Get permeation at a specific location."""
        district = self.districts.get(district_id)
        if not district:
            return self.global_permeation

        base = self.get_district_permeation(district_id)
        hotspot = district.hotspot_modifiers.get(location_id, 0.0)
        return max(0.0, min(1.0, base + hotspot))

    def update(self, delta: float, clock: "WorldClock", game_day: int) -> list[dict]:
        """
        Update the entire permeation system. Called each game tick.
        """
        events: list[dict] = []

        # Clock-driven oscillation (the veil breathes with time)
        time_mod = clock.spirit_permeability * 0.1
        self.global_permeation = max(
            self.story_permeation_floor,
            min(
                self.story_permeation_ceiling,
                self.story_permeation_floor + time_mod
                + (self.global_permeation - self.story_permeation_floor) * 0.99,
            ),
        )

        # Update active events
        still_active: list[LocationPermeationEvent] = []
        for event in self.active_events:
            if event.tick():
                still_active.append(event)
            else:
                # Event expired, remove its effect
                district = self.districts.get(event.district_id)
                if district and event.location_id in district.hotspot_modifiers:
                    district.hotspot_modifiers[event.location_id] -= event.permeation_change
                    if abs(district.hotspot_modifiers[event.location_id]) < 0.001:
                        del district.hotspot_modifiers[event.location_id]
                events.append({
                    "type": "permeation_event_expired",
                    "event_id": event.event_id,
                    "location_id": event.location_id,
                })
        self.active_events = still_active

        # Update district awareness
        for district in self.districts.values():
            local_perm = self.get_district_permeation(district.district_id)
            awareness_events = district.update_awareness(local_perm, delta)
            for ae in awareness_events:
                events.append({"type": "awareness_shift", "detail": ae})

        # Check for tier change
        tier_event = self._check_tier_change()
        if tier_event:
            events.append(tier_event)

        # Record history periodically
        if game_day > 0 and (
            not self.permeation_history
            or self.permeation_history[-1][0] != game_day
        ):
            self.permeation_history.append((game_day, self.global_permeation))

        return events

    def _check_tier_change(self) -> Optional[dict]:
        """Check if we've crossed into a new permeation tier."""
        new_tier = self.get_tier()
        if new_tier != self._current_tier:
            self._previous_tier = self._current_tier
            self._current_tier = new_tier

            # Notify callbacks
            for callback in self._tier_change_callbacks:
                callback(self._previous_tier, new_tier)

            return {
                "type": "permeation_tier_change",
                "old_tier": self._previous_tier.value,
                "new_tier": new_tier.value,
                "global_permeation": self.global_permeation,
                "effects": self._tier_effects[new_tier],
            }
        return None

    def apply_corruption_permeation(self, district_id: str,
                                     amount: float) -> None:
        """
        Corruption destabilizes the veil, raising permeation chaotically.
        This is different from natural or story-driven permeation: it's
        unstable, harmful, and tears rather than thins.
        """
        district = self.districts.get(district_id)
        if district:
            district.corruption_modifier = min(
                0.3, district.corruption_modifier + amount
            )

    def purify_permeation(self, district_id: str, amount: float) -> None:
        """Purification heals the chaotic corruption-driven permeation."""
        district = self.districts.get(district_id)
        if district:
            district.corruption_modifier = max(
                0.0, district.corruption_modifier - amount
            )

    def get_permeation_description(self, permeation: Optional[float] = None) -> str:
        """Get a narrative description of the current permeation state."""
        level = permeation if permeation is not None else self.global_permeation
        tier = self.get_tier(level)

        descriptions = {
            PermeationTier.VEILED: (
                "The veil is thick here. The material world dominates, solid "
                "and certain. Only the faintest whisper of something else."
            ),
            PermeationTier.FLICKERING: (
                "The veil flickers. Shadows move on their own. Reflections "
                "show things that aren't there. The world hasn't changed, "
                "but your certainty about it has."
            ),
            PermeationTier.MANIFEST: (
                "The spirit world is visible to all. Two realities share the "
                "same space, each visible, each undeniable. Tokyo has become "
                "a city of two worlds."
            ),
            PermeationTier.OVERLAPPING: (
                "The worlds overlap and blur. Geography itself becomes uncertain. "
                "A step in the material world might carry you further in the "
                "spirit world. The veil is not thin - it is dissolving."
            ),
            PermeationTier.CONVERGENCE: (
                "The worlds are nearly one. Reality is a negotiation between "
                "material and spiritual truth. Everything is both what it is "
                "and what it means. The veil is gone."
            ),
        }
        return descriptions[tier]
