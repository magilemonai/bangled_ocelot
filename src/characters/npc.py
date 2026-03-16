"""
Ma no Kuni - Non-Player Characters

The people and spirits Aoi meets along the way. Each one carries
their own relationship with the space between worlds -- some have
always known, some are just learning, some refuse to see.

Every NPC has depth. They have lives Aoi doesn't witness, opinions
Aoi never hears, histories that surface only if you listen long
enough. They are not quest dispensers. They are people.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ---------------------------------------------------------------------------
# NPC classification
# ---------------------------------------------------------------------------

class NPCType(Enum):
    """The nature of a being determines what kind of relationship is possible."""
    HUMAN = "human"
    SPIRIT = "spirit"
    DUAL = "dual"           # Exists in both worlds (like the Archivist)
    AWAKENED = "awakened"    # Human who has crossed into spirit awareness
    VESSEL = "vessel"       # Human hosting a spirit presence


class NPCDisposition(Enum):
    """Default disposition toward Aoi before any relationship develops."""
    WARM = "warm"
    NEUTRAL = "neutral"
    GUARDED = "guarded"
    HOSTILE = "hostile"
    CURIOUS = "curious"
    INDIFFERENT = "indifferent"


class NPCAvailability(Enum):
    """When and where can this NPC be found?"""
    ALWAYS = "always"
    DAYTIME = "daytime"
    NIGHTTIME = "nighttime"
    SCHEDULE = "schedule"       # Follows a specific schedule
    EVENT_ONLY = "event_only"   # Only during specific story events
    SUMMONED = "summoned"       # Must be called or sought out


# ---------------------------------------------------------------------------
# NPC schedule and routines
# ---------------------------------------------------------------------------

@dataclass
class ScheduleEntry:
    """Where an NPC will be at a given time."""
    time_start: float       # 0.0-24.0 hours
    time_end: float
    location: str
    activity: str           # What they're doing -- affects dialogue
    interruptible: bool = True
    days: Optional[set[int]] = None  # None = every day, otherwise set of day numbers


@dataclass
class NPCSchedule:
    """
    NPCs have lives. They go places. They do things.
    You can find Yuki at the konbini, or Ren sweeping the shrine.
    Their routines shift with the story.
    """
    entries: list[ScheduleEntry] = field(default_factory=list)
    override_location: Optional[str] = None  # Story override
    override_activity: Optional[str] = None

    def get_current(self, hour: float, day: int = 0) -> Optional[ScheduleEntry]:
        if self.override_location:
            return ScheduleEntry(
                time_start=0.0, time_end=24.0,
                location=self.override_location,
                activity=self.override_activity or "waiting",
            )
        for entry in self.entries:
            if entry.days is not None and day % 7 not in entry.days:
                continue
            if entry.time_start <= hour < entry.time_end:
                return entry
            # Handle overnight entries (e.g., 22.0 to 6.0)
            if entry.time_start > entry.time_end:
                if hour >= entry.time_start or hour < entry.time_end:
                    return entry
        return None


# ---------------------------------------------------------------------------
# NPC profile
# ---------------------------------------------------------------------------

@dataclass
class NPCPersonality:
    """
    The inner landscape of a character. These traits affect how they
    speak, what they notice, and how they respond to Aoi's choices.
    """
    # Core traits (0.0 to 1.0)
    openness: float = 0.5         # Willingness to share, be vulnerable
    patience: float = 0.5         # Tolerance for uncertainty
    warmth: float = 0.5           # Natural friendliness
    directness: float = 0.5       # How bluntly they communicate
    humor: float = 0.5            # Tendency toward levity
    spirituality: float = 0.5     # Connection to the spirit world
    pragmatism: float = 0.5       # Practical vs. idealistic
    loyalty: float = 0.5          # Depth of commitment to bonds
    secrecy: float = 0.5          # How much they hold back

    # Speech patterns
    formality: float = 0.5        # Casual to formal speech
    verbosity: float = 0.5        # Terse to verbose
    uses_silence: bool = False    # Comfortable with ma in conversation


@dataclass
class NPCBackground:
    """
    What shaped this person before Aoi met them.
    """
    backstory: str = ""
    secrets: list[str] = field(default_factory=list)
    fears: list[str] = field(default_factory=list)
    desires: list[str] = field(default_factory=list)
    regrets: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    connections: dict[str, str] = field(default_factory=dict)  # npc_id -> relationship description


@dataclass
class NPCSpiritProfile:
    """
    How this character relates to the spirit world.
    """
    can_see_spirits: bool = False
    spirit_sight_level: int = 0       # 0 = none, 5 = full dual vision
    spirit_affinity: float = 0.0      # How spirits feel about them
    known_spirits: list[str] = field(default_factory=list)
    spirit_pacts: list[str] = field(default_factory=list)
    visibility_to_spirits: float = 0.5  # How visible to the spirit world


@dataclass
class NPCState:
    """
    The mutable state of an NPC -- things that change as the story unfolds.
    """
    mood: str = "neutral"
    current_location: str = ""
    current_activity: str = ""
    is_available: bool = True
    has_been_met: bool = False
    trust_toward_aoi: float = 0.0    # Managed by relationship system but cached here
    story_phase: int = 0              # Which phase of their personal arc
    flags: dict[str, bool] = field(default_factory=dict)
    temporary_dialogue_override: Optional[str] = None


@dataclass
class NPC:
    """
    A non-player character in Ma no Kuni.

    Each NPC is a full person with their own history, feelings,
    schedule, and relationship to the spirit world. They change
    over time. They remember what Aoi says and does.
    """
    id: str
    name: str
    display_name: str           # May differ from name (nicknames, titles)
    npc_type: NPCType
    disposition: NPCDisposition
    availability: NPCAvailability

    personality: NPCPersonality = field(default_factory=NPCPersonality)
    background: NPCBackground = field(default_factory=NPCBackground)
    spirit_profile: NPCSpiritProfile = field(default_factory=NPCSpiritProfile)
    schedule: NPCSchedule = field(default_factory=NPCSchedule)
    state: NPCState = field(default_factory=NPCState)

    # Dialogue
    dialogue_tree_ids: list[str] = field(default_factory=list)
    greeting_pool: list[str] = field(default_factory=list)
    idle_lines: list[str] = field(default_factory=list)

    # Visual / Audio
    portrait: str = ""
    sprite: str = ""
    voice_style: str = ""

    # Tags for systems to query
    tags: set[str] = field(default_factory=set)

    def is_at(self, location: str) -> bool:
        return self.state.current_location == location

    def update_location(self, hour: float, day: int = 0) -> None:
        """Update NPC location based on schedule."""
        entry = self.schedule.get_current(hour, day)
        if entry:
            self.state.current_location = entry.location
            self.state.current_activity = entry.activity

    def get_greeting(self, context: dict) -> Optional[str]:
        """
        Select an appropriate greeting based on context.
        Context may include: time_of_day, relationship_level, flags, etc.
        """
        if self.state.temporary_dialogue_override:
            return self.state.temporary_dialogue_override
        if not self.greeting_pool:
            return None
        # Simple selection -- more sophisticated systems can override
        if not self.state.has_been_met:
            return self.greeting_pool[0] if self.greeting_pool else None
        return self.greeting_pool[-1] if self.greeting_pool else None


# ---------------------------------------------------------------------------
# NPC Registry -- all characters in the world
# ---------------------------------------------------------------------------

class NPCRegistry:
    """
    The world's population. Every named character lives here.
    """

    def __init__(self) -> None:
        self._npcs: dict[str, NPC] = {}

    def register(self, npc: NPC) -> None:
        self._npcs[npc.id] = npc

    def get(self, npc_id: str) -> Optional[NPC]:
        return self._npcs.get(npc_id)

    def get_all(self) -> list[NPC]:
        return list(self._npcs.values())

    def npcs_at_location(self, location: str) -> list[NPC]:
        return [
            npc for npc in self._npcs.values()
            if npc.state.current_location == location and npc.state.is_available
        ]

    def npcs_by_type(self, npc_type: NPCType) -> list[NPC]:
        return [npc for npc in self._npcs.values() if npc.npc_type == npc_type]

    def npcs_by_tag(self, tag: str) -> list[NPC]:
        return [npc for npc in self._npcs.values() if tag in npc.tags]

    def update_all(self, hour: float, day: int = 0) -> None:
        """Update all NPC locations based on schedules."""
        for npc in self._npcs.values():
            npc.update_location(hour, day)


# ---------------------------------------------------------------------------
# Main character definitions
# ---------------------------------------------------------------------------

def create_obaa_chan() -> NPC:
    """
    Grandmother Haruki (春樹) -- "spring tree."

    She has lived in this house for forty years. The garden was
    already old when she arrived. She tends it with the patience
    of someone who knows that some things grow on their own schedule.

    She knows more about spirits than she lets on. How much more
    is one of the game's central mysteries.
    """
    return NPC(
        id="obaa_chan",
        name="Haruki",
        display_name="Obaa-chan",
        npc_type=NPCType.HUMAN,
        disposition=NPCDisposition.WARM,
        availability=NPCAvailability.SCHEDULE,
        personality=NPCPersonality(
            openness=0.6,
            patience=0.95,
            warmth=0.9,
            directness=0.3,      # She speaks in gentle indirections
            humor=0.6,
            spirituality=0.85,
            pragmatism=0.7,
            loyalty=1.0,
            secrecy=0.7,         # She holds many things close
            formality=0.3,
            verbosity=0.3,       # She says little. It means a lot.
            uses_silence=True,   # A master of ma
        ),
        background=NPCBackground(
            backstory=(
                "Haruki married young, lost her husband to illness twenty years ago, "
                "and raised her child -- Aoi's parent -- alone. The rift between "
                "Aoi and their parents weighs on her, but she does not push. She "
                "waits. She has always been able to feel the spirits in the garden, "
                "though she has never called it that."
            ),
            secrets=[
                "She can sense spirits through her garden -- always could.",
                "She knew the Archivist when she was young, though she has never spoken of it.",
                "She understands why the veil is thinning. She has been expecting it.",
                "The cat Mikan was a gift from a spirit, given in exchange for a promise.",
            ],
            fears=[
                "That Aoi will be consumed by the spirit world.",
                "That the rift with Aoi's parents will never heal.",
                "That her secrets, kept to protect, will instead wound.",
            ],
            desires=[
                "To see Aoi at peace.",
                "To tend her garden until the very end.",
                "To finally speak honestly about what she knows.",
            ],
            skills=["Gardening", "Cooking", "Herbalism", "Spirit-warding (instinctive)"],
            connections={
                "aoi": "Grandchild -- the most important person in her world",
                "mikan": "Her cat, companion, and spirit-seer",
                "the_archivist": "An old acquaintance she has not spoken to in decades",
            },
        ),
        spirit_profile=NPCSpiritProfile(
            can_see_spirits=False,  # She feels them, doesn't see them
            spirit_sight_level=0,
            spirit_affinity=0.8,
            known_spirits=["garden_kodama", "kitchen_zashiki"],
            visibility_to_spirits=0.7,
        ),
        schedule=NPCSchedule(entries=[
            ScheduleEntry(5.0, 7.0, "grandmother_house_garden", "tending the garden at dawn"),
            ScheduleEntry(7.0, 9.0, "grandmother_house_kitchen", "preparing breakfast"),
            ScheduleEntry(9.0, 11.0, "grandmother_house_garden", "gardening"),
            ScheduleEntry(11.0, 14.0, "grandmother_house_kitchen", "cooking and housework"),
            ScheduleEntry(14.0, 16.0, "grandmother_house_engawa", "resting, reading, or napping"),
            ScheduleEntry(16.0, 18.0, "grandmother_house_garden", "evening garden care"),
            ScheduleEntry(18.0, 20.0, "grandmother_house_kitchen", "preparing dinner"),
            ScheduleEntry(20.0, 22.0, "grandmother_house_living", "quiet evening -- tea, conversation, ma"),
            ScheduleEntry(22.0, 5.0, "grandmother_house_bedroom", "sleeping"),
        ]),
        state=NPCState(
            mood="gentle",
            current_location="grandmother_house_garden",
            has_been_met=True,
            trust_toward_aoi=0.9,
            story_phase=0,
        ),
        dialogue_tree_ids=["obaa_chan_greeting", "obaa_chan_evening", "obaa_chan_garden", "obaa_chan_memories"],
        greeting_pool=[
            "Ah, Aoi. Come, sit. The tea is still warm.",
            "You've been out again. ... That's fine. Mikan missed you.",
            "The garden is restless tonight. Can you feel it?",
        ],
        idle_lines=[
            "*She hums quietly while watering the plants.*",
            "*She watches the garden, her hands still on her lap.*",
            "*Mikan is curled in her lap. Neither of them move.*",
        ],
        tags={"family", "key_character", "spirit_aware", "yanaka"},
    )


def create_ren() -> NPC:
    """
    Ren (蓮) -- "lotus." Grows from mud.

    A shrine keeper's child who has always been able to see spirits.
    For years, no one believed them. Now that the veil has thinned
    and others can see, Ren is not grateful or relieved.
    They are angry.

    Why should everyone suddenly believe when they wouldn't before?
    """
    return NPC(
        id="ren",
        name="Ren",
        display_name="Ren",
        npc_type=NPCType.AWAKENED,
        disposition=NPCDisposition.GUARDED,
        availability=NPCAvailability.SCHEDULE,
        personality=NPCPersonality(
            openness=0.2,         # Burned too many times
            patience=0.3,         # Ran out years ago
            warmth=0.35,          # Buried under resentment
            directness=0.85,      # Blunt to the point of cutting
            humor=0.4,            # Dry, self-deprecating
            spirituality=0.9,     # This is their whole life
            pragmatism=0.6,
            loyalty=0.8,          # Once earned, unshakable
            secrecy=0.4,          # They've stopped hiding
            formality=0.2,        # Casual, sometimes rough
            verbosity=0.5,
            uses_silence=False,   # Silence reminds them of being ignored
        ),
        background=NPCBackground(
            backstory=(
                "Ren has seen spirits since birth. Their parents, shrine keepers, "
                "should have believed them. Instead they called it imagination, then "
                "attention-seeking, then something to grow out of. Ren grew up feeling "
                "gaslit by the people who should have understood best. Now that the "
                "permeation makes spirits visible to everyone, Ren keeps the shrine "
                "but trusts almost no one."
            ),
            secrets=[
                "They have a pact with a guardian spirit of the shrine -- made at age seven.",
                "They almost left the shrine entirely. The spirit convinced them to stay.",
                "They are terrified of losing their sight -- it's all they've ever been sure of.",
            ],
            fears=[
                "Being dismissed again.",
                "That the permeation will end and they'll be alone with the spirits once more.",
                "That their anger will drive away the one good thing forming with Aoi.",
            ],
            desires=[
                "To be believed. Finally, permanently, without qualification.",
                "To understand why the veil thinned.",
                "To find someone who understands what it's like.",
            ],
            skills=["Spirit sight (innate)", "Shrine rituals", "Ofuda crafting", "Spirit negotiation"],
            connections={
                "aoi": "A tentative bond -- someone who might understand",
                "the_archivist": "The Archivist remembers Ren as a child, crying at the shrine",
                "kaito": "Distrusts deeply -- sees him as exploiting what Ren suffered for",
            },
        ),
        spirit_profile=NPCSpiritProfile(
            can_see_spirits=True,
            spirit_sight_level=4,
            spirit_affinity=0.7,
            known_spirits=["shrine_guardian", "torii_watcher", "stone_fox_pair"],
            spirit_pacts=["shrine_guardian_pact"],
            visibility_to_spirits=0.9,
        ),
        schedule=NPCSchedule(entries=[
            ScheduleEntry(5.0, 8.0, "kanda_shrine_inner", "morning rituals"),
            ScheduleEntry(8.0, 12.0, "kanda_shrine_grounds", "shrine maintenance"),
            ScheduleEntry(12.0, 13.0, "kanda_shrine_office", "lunch break"),
            ScheduleEntry(13.0, 17.0, "kanda_shrine_grounds", "greeting visitors, selling charms"),
            ScheduleEntry(17.0, 19.0, "kanda_shrine_inner", "evening rituals"),
            ScheduleEntry(19.0, 22.0, "kanda_neighborhood", "walking, thinking, watching spirits"),
            ScheduleEntry(22.0, 5.0, "kanda_shrine_quarters", "sleeping"),
        ]),
        state=NPCState(
            mood="guarded",
            current_location="kanda_shrine_grounds",
            has_been_met=False,
            trust_toward_aoi=0.0,
            story_phase=0,
        ),
        dialogue_tree_ids=["ren_first_meeting", "ren_shrine_talk", "ren_anger", "ren_opening_up"],
        greeting_pool=[
            "... You can see them too, huh. Welcome to the club. There are no perks.",
            "Back again? The shrine's open. The spirits don't charge admission.",
            "You look like you actually slept. Must be nice.",
        ],
        idle_lines=[
            "*Ren is sweeping the shrine path, muttering to something you can't quite see.*",
            "*They're sitting on the shrine steps, watching the sky with an unreadable expression.*",
            "*Ren is arranging ofuda with practiced, almost angry precision.*",
        ],
        tags={"key_character", "spirit_seer", "shrine", "kanda"},
    )


def create_yuki() -> NPC:
    """
    Yuki (雪) -- "snow." Clear, practical, and surprisingly warm
    once you get past the efficiency.

    Runs a konbini that has become -- through no intention of her own --
    a rest stop for spirits. She deals with it the way she deals with
    everything: pragmatically.
    """
    return NPC(
        id="yuki",
        name="Yuki",
        display_name="Yuki",
        npc_type=NPCType.HUMAN,
        disposition=NPCDisposition.NEUTRAL,
        availability=NPCAvailability.SCHEDULE,
        personality=NPCPersonality(
            openness=0.5,
            patience=0.7,
            warmth=0.6,           # Hidden under professionalism
            directness=0.8,
            humor=0.7,            # Deadpan, situational
            spirituality=0.2,     # She doesn't think about it, she just adapts
            pragmatism=0.95,      # The most practical person in the game
            loyalty=0.6,
            secrecy=0.3,
            formality=0.4,        # Konbini-casual
            verbosity=0.6,
            uses_silence=False,
        ),
        background=NPCBackground(
            backstory=(
                "Yuki took over the konbini from her uncle three years ago. Business was "
                "fine until spirits started showing up. At first she thought she was losing "
                "it. Then she realized they were browsing. Now she stocks items that spirits "
                "like alongside the regular inventory and has a 'no-haunting-the-customers' "
                "policy posted by the door. She's making it work."
            ),
            secrets=[
                "She can't see spirits clearly -- she sees them as heat-shimmer distortions.",
                "The konbini sits on a ley line intersection. Her uncle knew.",
                "She's been quietly documenting spirit preferences and behaviors in a notebook.",
            ],
            fears=[
                "That the spirit traffic will destroy her business.",
                "That something genuinely dangerous will walk through her door.",
                "That she's in over her head and doesn't know it.",
            ],
            desires=[
                "To keep the konbini running. That's it. That's the goal.",
                "Okay, also to understand the notebook her uncle left behind.",
                "And maybe to stop pretending she isn't fascinated by all of this.",
            ],
            skills=["Business management", "Negotiation", "Improvisation", "Spirit commerce (emerging)"],
            connections={
                "aoi": "A customer who became something more like a friend",
                "hinata": "Regular customer, buys energy drinks at 3am",
                "kaito": "His corporation keeps trying to buy the building. She keeps saying no.",
            },
        ),
        spirit_profile=NPCSpiritProfile(
            can_see_spirits=True,  # Partially -- heat shimmer vision
            spirit_sight_level=1,
            spirit_affinity=0.4,
            known_spirits=["konbini_tanuki", "shelf_spirit", "vending_machine_tsukumogami"],
            visibility_to_spirits=0.6,
        ),
        schedule=NPCSchedule(entries=[
            ScheduleEntry(6.0, 14.0, "yuki_konbini", "morning shift"),
            ScheduleEntry(14.0, 16.0, "yuki_apartment", "break -- lunch, rest"),
            ScheduleEntry(16.0, 23.0, "yuki_konbini", "evening shift"),
            ScheduleEntry(23.0, 6.0, "yuki_apartment", "sleeping -- mostly"),
        ]),
        state=NPCState(
            mood="matter-of-fact",
            current_location="yuki_konbini",
            has_been_met=False,
            trust_toward_aoi=0.0,
            story_phase=0,
        ),
        dialogue_tree_ids=["yuki_konbini_intro", "yuki_spirit_commerce", "yuki_uncle_notebook"],
        greeting_pool=[
            "Welcome. Regular stuff on the left, spirit stuff on the right. Don't ask me how to tell the difference.",
            "Hey. The onigiri are fresh. The spirit on aisle three is not. Steer clear.",
            "You again. Good. I have questions and you seem like someone who has answers.",
        ],
        idle_lines=[
            "*Yuki is restocking shelves, pausing occasionally to shoo away something invisible.*",
            "*She's writing in a battered notebook behind the counter, frowning.*",
            "*She adjusts a small offering dish near the register. Business is business.*",
        ],
        tags={"key_character", "merchant", "information", "konbini_district"},
    )


def create_kaito() -> NPC:
    """
    Kaito (海斗) -- "ocean" + "dipper," a name that reaches for vastness.

    Aoi's former best friend. They grew up together, shared everything.
    Then Kaito took a job at SpiritBridge Corp, a company turning spirit
    energy into a commodity. He believes he's helping. He might be wrong.

    The tragedy of Kaito is that he isn't a villain. He's a person
    making choices he believes are right, and those choices are pulling
    him away from everything he used to care about.
    """
    return NPC(
        id="kaito",
        name="Kaito",
        display_name="Kaito",
        npc_type=NPCType.HUMAN,
        disposition=NPCDisposition.GUARDED,
        availability=NPCAvailability.SCHEDULE,
        personality=NPCPersonality(
            openness=0.4,         # Used to be higher
            patience=0.5,
            warmth=0.5,           # Still there, suppressed under ambition
            directness=0.7,
            humor=0.5,
            spirituality=0.15,    # Sees spirits as resources
            pragmatism=0.85,
            loyalty=0.6,          # Conflicted
            secrecy=0.7,          # Corporate secrets
            formality=0.6,        # Business-casual persona
            verbosity=0.6,
            uses_silence=False,   # Fills every gap -- afraid of what silence says
        ),
        background=NPCBackground(
            backstory=(
                "Kaito and Aoi were inseparable through middle school. When Aoi's "
                "family situation fractured, Kaito didn't know how to help and pulled "
                "away -- something he's never forgiven himself for. He threw himself "
                "into academics, then business. SpiritBridge Corp recruited him for "
                "his analytical mind. He tells himself he's building a bridge between "
                "worlds. The name is right there in the company name. But the bridge "
                "has a toll booth."
            ),
            secrets=[
                "He left Aoi when they needed him most. He knows it. It eats at him.",
                "He's seen what SpiritBridge does in its labs. He has doubts he won't voice.",
                "He keeps a photo of himself and Aoi from middle school in his desk drawer.",
                "His boss has asked him to acquire Yuki's konbini -- by any means.",
            ],
            fears=[
                "That Aoi is right about SpiritBridge.",
                "That he's already gone too far to turn back.",
                "That the friendship is truly over.",
            ],
            desires=[
                "Success. Recognition. To prove the path he chose was right.",
                "Somewhere buried: to repair what he broke with Aoi.",
                "To believe that what SpiritBridge does helps more than it harms.",
            ],
            skills=["Business analysis", "Negotiation", "Spirit-tech operation", "Data analysis"],
            connections={
                "aoi": "Former best friend -- the wound that won't close",
                "yuki": "Business target -- but he respects her stubbornness",
                "ren": "Views with condescension that masks discomfort",
                "hinata": "Doesn't understand -- finds the art unsettling",
            },
        ),
        spirit_profile=NPCSpiritProfile(
            can_see_spirits=False,
            spirit_sight_level=0,
            spirit_affinity=-0.2,  # Spirits avoid him -- they sense something
            visibility_to_spirits=0.3,
        ),
        schedule=NPCSchedule(entries=[
            ScheduleEntry(7.0, 9.0, "spiritbridge_tower", "morning briefings"),
            ScheduleEntry(9.0, 12.0, "spiritbridge_tower", "lab oversight"),
            ScheduleEntry(12.0, 13.0, "business_district_cafe", "lunch -- alone"),
            ScheduleEntry(13.0, 18.0, "spiritbridge_tower", "afternoon operations"),
            ScheduleEntry(18.0, 20.0, "business_district", "networking events or walking"),
            ScheduleEntry(20.0, 22.0, "kaito_apartment", "working from home"),
            ScheduleEntry(22.0, 7.0, "kaito_apartment", "restless sleep"),
        ]),
        state=NPCState(
            mood="controlled",
            current_location="spiritbridge_tower",
            has_been_met=False,
            trust_toward_aoi=0.2,  # Residual bond, but walls are up
            story_phase=0,
        ),
        dialogue_tree_ids=["kaito_reunion", "kaito_spiritbridge", "kaito_confrontation", "kaito_doubt"],
        greeting_pool=[
            "...Aoi. It's been a while. You look-- ... How are you?",
            "I don't have long. What do you need?",
            "If you're here to lecture me about SpiritBridge, save it. I've heard it.",
        ],
        idle_lines=[
            "*Kaito stares at his phone, jaw tight. He hasn't noticed you.*",
            "*He's adjusting his tie in a window's reflection. His hands are unsteady.*",
            "*He's sitting alone at a cafe table, coffee untouched and cooling.*",
        ],
        tags={"key_character", "antagonist_adjacent", "spiritbridge", "business_district"},
    )


def create_hinata() -> NPC:
    """
    Hinata (陽向) -- "facing the sun." An artist who paints light.

    A street artist whose work has always been vivid, emotional,
    almost alive. After the permeation, it became literally alive.
    Their paintings move. Some of them leave the walls.

    Hinata is ecstatic and terrified in equal measure.
    """
    return NPC(
        id="hinata",
        name="Hinata",
        display_name="Hinata",
        npc_type=NPCType.AWAKENED,
        disposition=NPCDisposition.WARM,
        availability=NPCAvailability.SCHEDULE,
        personality=NPCPersonality(
            openness=0.9,         # Heart on sleeve, always
            patience=0.4,         # Restless creative energy
            warmth=0.8,
            directness=0.5,       # Expresses through art more than words
            humor=0.7,            # Playful, sometimes manic
            spirituality=0.6,     # Intuitive, not studied
            pragmatism=0.2,       # The least practical person alive
            loyalty=0.7,
            secrecy=0.1,          # Couldn't keep a secret if paid
            formality=0.1,        # Profoundly casual
            verbosity=0.8,        # Talks a lot when nervous (often)
            uses_silence=False,   # Fears stillness
        ),
        background=NPCBackground(
            backstory=(
                "Hinata dropped out of art school because they said their work was "
                "'too fantastical.' They took to the streets, painting murals in "
                "underpasses and alleyways. The spirits loved the paintings before "
                "anyone else did. After the permeation, spirit energy began flowing "
                "through Hinata's art, animating it. Now their murals breathe, blink, "
                "and sometimes wander off. Hinata calls them their children."
            ),
            secrets=[
                "They didn't start the permeation. But their art might have widened the cracks.",
                "One of their paintings disappeared and hasn't come back. They're worried.",
                "They dream in colors that don't exist in the waking world.",
            ],
            fears=[
                "That their art will hurt someone.",
                "That they'll lose the ability to create.",
                "Stillness. Emptiness. A blank wall.",
            ],
            desires=[
                "To understand the connection between their art and the spirit world.",
                "To paint something that changes the world. (More than it already has.)",
                "To find the painting that walked away.",
            ],
            skills=["Painting", "Mural art", "Spirit channeling (unconscious)", "Color theory"],
            connections={
                "aoi": "Kindred spirit -- sees something in Aoi that reminds them of their art",
                "yuki": "Buys energy drinks from the konbini at ridiculous hours",
                "ren": "Respects deeply -- wants to paint Ren's anger, hasn't dared ask",
                "the_archivist": "The Archivist collects Hinata's work. Hinata doesn't know this yet.",
            },
        ),
        spirit_profile=NPCSpiritProfile(
            can_see_spirits=True,  # Through their art -- like a lens
            spirit_sight_level=2,
            spirit_affinity=0.75,
            known_spirits=["paint_spirits", "mural_children", "color_kami"],
            visibility_to_spirits=0.85,  # Spirits are drawn to creators
        ),
        schedule=NPCSchedule(entries=[
            ScheduleEntry(10.0, 13.0, "hinata_studio", "late morning, sketching"),
            ScheduleEntry(13.0, 14.0, "yuki_konbini", "buying supplies and snacks"),
            ScheduleEntry(14.0, 19.0, "shimokitazawa_streets", "painting murals"),
            ScheduleEntry(19.0, 21.0, "hinata_studio", "reviewing work, eating"),
            ScheduleEntry(21.0, 3.0, "shimokitazawa_streets", "night painting -- when the spirits are thickest"),
            ScheduleEntry(3.0, 10.0, "hinata_studio", "sleeping -- usually"),
        ]),
        state=NPCState(
            mood="electric",
            current_location="shimokitazawa_streets",
            has_been_met=False,
            trust_toward_aoi=0.0,
            story_phase=0,
        ),
        dialogue_tree_ids=["hinata_first_mural", "hinata_studio_visit", "hinata_missing_painting"],
        greeting_pool=[
            "Oh! Oh, you can-- can you see the colors? Around you? They're incredible!",
            "Aoi! Perfect timing. I need someone to tell me if this wall is breathing or if I need sleep.",
            "I haven't slept. Don't look at me like that. Look at THIS. *gestures at a luminous mural*",
        ],
        idle_lines=[
            "*Hinata is painting furiously, talking to the wall. The wall might be talking back.*",
            "*They're mixing paints with their bare hands, humming something discordant and beautiful.*",
            "*A small painted bird hops along the edge of a mural. Hinata watches it with wet eyes.*",
        ],
        tags={"key_character", "artist", "spirit_channeler", "shimokitazawa"},
    )


def create_the_archivist() -> NPC:
    """
    The Archivist (記録者, Kirokumono).

    An ancient spirit who has existed as long as Tokyo has had memories.
    They catalog everything -- every joy, every loss, every forgotten
    afternoon. Their archive is a place between places, a library
    that exists in the pause between one thought and the next.

    They are neither kind nor cruel. They are thorough.
    """
    return NPC(
        id="the_archivist",
        name="Kirokumono",
        display_name="The Archivist",
        npc_type=NPCType.SPIRIT,
        disposition=NPCDisposition.CURIOUS,
        availability=NPCAvailability.SUMMONED,
        personality=NPCPersonality(
            openness=0.5,         # They will share -- for a price
            patience=1.0,         # Infinite. They have nothing but time.
            warmth=0.2,           # Not cold, but vast -- like the sky
            directness=0.6,       # Precise when they choose to be
            humor=0.3,            # Ancient, dry, references no one gets
            spirituality=1.0,     # They ARE the spiritual
            pragmatism=0.4,       # Deals in memory, not practicality
            loyalty=0.3,          # Loyal to the archive, not to people
            secrecy=0.9,          # Everything is secret until it isn't
            formality=0.8,        # Speaks with the weight of centuries
            verbosity=0.5,        # Never a word wasted, never a word missing
            uses_silence=True,    # The pauses in their speech contain information
        ),
        background=NPCBackground(
            backstory=(
                "The Archivist came into being when the first person in what would "
                "become Tokyo told a story and someone else remembered it. They have "
                "been collecting ever since. Every memory of every person who has ever "
                "lived in this city -- the Archivist has it cataloged. They are the "
                "living memory of Tokyo. The permeation concerns them not because it is "
                "dangerous, but because it is generating more memories than they have "
                "ever had to process. The archive is growing faster than they can organize."
            ),
            secrets=[
                "They know why the veil thinned. They are not permitted to say.",
                "They met Haruki when she was young. The memory is filed under 'Promises.'",
                "They are afraid. For the first time in centuries, they are afraid.",
                "The archive has a door that leads somewhere even the Archivist has never been.",
            ],
            fears=[
                "That memories will be lost faster than they can be saved.",
                "That the permeation will destroy the archive.",
                "Forgetting. The one thing they must never do.",
            ],
            desires=[
                "To catalog everything. Always. Forever.",
                "To understand the door in the archive.",
                "To find someone worthy of carrying a memory they cannot hold alone.",
            ],
            skills=[
                "Total recall of Tokyo's history",
                "Memory manipulation",
                "Temporal perception",
                "Archival magic",
                "Binding oaths",
            ],
            connections={
                "obaa_chan": "A promise made long ago, unfulfilled",
                "aoi": "A pattern in the archive -- this one appears in too many futures",
                "ren": "Watched them cry at the shrine as a child. Filed under 'Injustice.'",
                "hinata": "Collects their art. It is the most alive thing in the archive.",
            },
        ),
        spirit_profile=NPCSpiritProfile(
            can_see_spirits=True,
            spirit_sight_level=5,
            spirit_affinity=1.0,
            known_spirits=["all"],
            spirit_pacts=[],
            visibility_to_spirits=1.0,
        ),
        schedule=NPCSchedule(entries=[
            # The Archivist exists outside normal time
            ScheduleEntry(0.0, 24.0, "the_archive", "cataloging, always cataloging"),
        ]),
        state=NPCState(
            mood="contemplative",
            current_location="the_archive",
            has_been_met=False,
            trust_toward_aoi=0.0,
            story_phase=0,
        ),
        dialogue_tree_ids=["archivist_first_encounter", "archivist_bargain", "archivist_revelations"],
        greeting_pool=[
            "... You found this place. That is not a small thing.",
            "Aoi. Yes. I have your file. It is... extensive, for one so young.",
            "You have questions. I have answers. But nothing here is free.",
        ],
        idle_lines=[
            "*The Archivist moves between towering shelves of light, fingers trailing through memories like water.*",
            "*They hold a glowing orb close to their face, studying it. A child's laughter echoes from within.*",
            "*The silence here is not empty. It is full -- impossibly, overwhelmingly full.*",
        ],
        tags={"key_character", "ancient_spirit", "information", "quest_giver", "the_archive"},
    )


def create_mikan() -> NPC:
    """
    Mikan (蜜柑) -- the cat. Orange, fat, judgmental, and
    a better spirit-seer than anyone in the game.

    Cats have always seen both worlds. Mikan is not special in this
    regard. Mikan is special because Mikan chooses to care.
    """
    return NPC(
        id="mikan",
        name="Mikan",
        display_name="Mikan",
        npc_type=NPCType.DUAL,
        disposition=NPCDisposition.WARM,
        availability=NPCAvailability.SCHEDULE,
        personality=NPCPersonality(
            openness=0.3,
            patience=0.8,         # Cat patience -- absolute, then zero
            warmth=0.7,           # For Aoi and Haruki. Others: variable.
            directness=1.0,       # It's a cat
            humor=0.0,            # Cats are not funny. Cats are serious.
            spirituality=1.0,
            pragmatism=0.9,
            loyalty=0.85,
            secrecy=1.0,          # Keeps all secrets. Is a cat.
            formality=0.0,
            verbosity=0.0,        # Meows and stares. That's the range.
            uses_silence=True,    # A grandmaster of ma
        ),
        background=NPCBackground(
            backstory=(
                "Mikan appeared at Haruki's door twelve years ago as a kitten. "
                "Haruki says a neighbor gave her the cat. This is not entirely true. "
                "Mikan has always seen both worlds and acts as an informal guardian "
                "of the household. Where Mikan stares, pay attention."
            ),
            secrets=[
                "Mikan was given to Haruki by a spirit as part of a bargain.",
                "Mikan can travel between worlds when no one is watching.",
                "Mikan has been protecting Aoi since before they could walk.",
            ],
            fears=["The vacuum cleaner."],
            desires=["Fish.", "Naps.", "Aoi's safety."],
            skills=["Spirit sight (innate)", "Spirit travel", "Judgment", "Napping"],
            connections={
                "obaa_chan": "Bonded -- the most important human",
                "aoi": "Protected one -- would cross worlds for them",
                "garden_kodama": "Tolerates. Barely.",
            },
        ),
        spirit_profile=NPCSpiritProfile(
            can_see_spirits=True,
            spirit_sight_level=5,
            spirit_affinity=0.9,
            known_spirits=["garden_kodama", "kitchen_zashiki", "the_archivist"],
            visibility_to_spirits=1.0,
        ),
        schedule=NPCSchedule(entries=[
            ScheduleEntry(5.0, 8.0, "grandmother_house_garden", "dawn patrol"),
            ScheduleEntry(8.0, 11.0, "grandmother_house_engawa", "napping in the sun"),
            ScheduleEntry(11.0, 14.0, "grandmother_house_kitchen", "supervising lunch"),
            ScheduleEntry(14.0, 17.0, "grandmother_house_living", "napping again"),
            ScheduleEntry(17.0, 20.0, "grandmother_house_garden", "evening patrol"),
            ScheduleEntry(20.0, 22.0, "grandmother_house_living", "sitting with family"),
            ScheduleEntry(22.0, 5.0, "unknown", "where cats go at night"),
        ]),
        state=NPCState(
            mood="inscrutable",
            current_location="grandmother_house_engawa",
            has_been_met=True,
            trust_toward_aoi=0.85,
            story_phase=0,
        ),
        dialogue_tree_ids=["mikan_stare", "mikan_lead"],
        greeting_pool=[
            "*Mikan looks at you. Then looks at something you can't see. Then looks at you again.*",
            "*A slow blink. In cat, this means trust. Or hunger. Or both.*",
            "*Mikan headbutts your shin and walks toward the garden, pausing to check if you follow.*",
        ],
        idle_lines=[
            "*Mikan is staring intently at an empty corner of the room. It might not be empty.*",
            "*Purring. The vibration has an odd quality -- almost harmonic.*",
            "*Mikan is asleep. Or pretending to be asleep. With cats, you never know.*",
        ],
        tags={"family", "spirit_seer", "guide", "yanaka", "cat"},
    )


def create_all_main_npcs() -> NPCRegistry:
    """
    Create and register all main story NPCs.
    Returns a populated registry ready for the game.
    """
    registry = NPCRegistry()
    registry.register(create_obaa_chan())
    registry.register(create_ren())
    registry.register(create_yuki())
    registry.register(create_kaito())
    registry.register(create_hinata())
    registry.register(create_the_archivist())
    registry.register(create_mikan())
    return registry
