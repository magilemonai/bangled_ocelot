"""
Ma no Kuni - Menu System

Even the menus breathe. The pause screen is not an escape from the world -
it's a deeper look at it.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Callable


class MenuType(Enum):
    MAIN_MENU = auto()
    PAUSE = auto()
    INVENTORY = auto()
    BESTIARY = auto()
    MAP = auto()
    SPIRIT_BONDS = auto()
    CRAFTING = auto()
    QUEST_LOG = auto()
    SETTINGS = auto()
    SAVE_LOAD = auto()
    DIALOGUE_CHOICE = auto()


@dataclass
class MenuItem:
    """A single menu item."""
    label: str
    description: str = ""
    action: Optional[str] = None  # Action identifier
    enabled: bool = True
    visible: bool = True
    icon: Optional[str] = None
    spirit_glow: bool = False  # Spirit-touched menu items glow


@dataclass
class MenuState:
    """Current state of a menu."""
    menu_type: MenuType
    items: List[MenuItem] = field(default_factory=list)
    selected_index: int = 0
    scroll_offset: int = 0
    max_visible: int = 8
    title: str = ""
    subtitle: str = ""
    background_effect: str = "none"  # none, blur, spirit_overlay, memory_wash

    def move_up(self) -> None:
        if self.selected_index > 0:
            self.selected_index -= 1
            if self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index

    def move_down(self) -> None:
        visible_items = [i for i in self.items if i.visible]
        if self.selected_index < len(visible_items) - 1:
            self.selected_index += 1
            if self.selected_index >= self.scroll_offset + self.max_visible:
                self.scroll_offset = self.selected_index - self.max_visible + 1

    @property
    def selected_item(self) -> Optional[MenuItem]:
        visible_items = [i for i in self.items if i.visible]
        if 0 <= self.selected_index < len(visible_items):
            return visible_items[self.selected_index]
        return None


class TitleScreen:
    """
    The title screen. Cherry blossoms fall. A distant shakuhachi plays.
    The title materializes slowly, like a spirit becoming visible.
    """

    def __init__(self):
        self.phase: float = 0.0
        self.title_opacity: float = 0.0
        self.subtitle_opacity: float = 0.0
        self.menu_opacity: float = 0.0
        self.blossom_particles: list = []
        self.state: str = "intro"  # intro, title_reveal, menu_ready

        self.menu = MenuState(
            menu_type=MenuType.MAIN_MENU,
            title="間の国",
            subtitle="Ma no Kuni — The Country Between",
            items=[
                MenuItem(
                    label="New Journey",
                    description="Begin Aoi's story",
                    action="new_game",
                ),
                MenuItem(
                    label="Continue",
                    description="Resume a saved journey",
                    action="load_game",
                    enabled=False,  # Enabled when saves exist
                ),
                MenuItem(
                    label="Settings",
                    description="Adjust the world",
                    action="settings",
                ),
                MenuItem(
                    label="Quit",
                    description="Return to the other world",
                    action="quit",
                ),
            ],
        )

    def update(self, delta: float) -> None:
        self.phase += delta

        if self.state == "intro":
            # Blossoms fall for 3 seconds before title appears
            if self.phase > 3.0:
                self.state = "title_reveal"

        elif self.state == "title_reveal":
            self.title_opacity = min(1.0, self.title_opacity + delta * 0.5)
            if self.title_opacity >= 1.0:
                self.subtitle_opacity = min(1.0, self.subtitle_opacity + delta * 0.3)
            if self.subtitle_opacity >= 1.0:
                self.menu_opacity = min(1.0, self.menu_opacity + delta * 0.4)
            if self.menu_opacity >= 1.0:
                self.state = "menu_ready"

    def check_saves(self, saves_exist: bool) -> None:
        """Enable continue option if saves exist."""
        self.menu.items[1].enabled = saves_exist


class PauseMenu:
    """
    The pause menu overlays the world with a gentle blur.
    The spirit world is slightly more visible during pause -
    as if pausing lets you see more clearly.
    """

    def __init__(self):
        self.menu = MenuState(
            menu_type=MenuType.PAUSE,
            title="Pause",
            background_effect="blur",
            items=[
                MenuItem(label="Resume", action="resume"),
                MenuItem(label="Inventory", action="inventory", icon="bag"),
                MenuItem(label="Spirit Bonds", action="spirit_bonds", icon="bond",
                         spirit_glow=True),
                MenuItem(label="Bestiary", action="bestiary", icon="book"),
                MenuItem(label="Quest Log", action="quests", icon="scroll"),
                MenuItem(label="Map", action="map", icon="map"),
                MenuItem(label="Crafting", action="crafting", icon="hammer"),
                MenuItem(label="Save", action="save", icon="crystal"),
                MenuItem(label="Settings", action="settings", icon="gear"),
                MenuItem(label="Title Screen", action="title", icon="door"),
            ],
        )


@dataclass
class DialogueBox:
    """
    The dialogue box. Where words live - and where silence speaks loudest.
    """
    speaker: str = ""
    text: str = ""
    full_text: str = ""
    char_index: int = 0
    chars_per_second: float = 30.0
    is_complete: bool = False
    is_spirit_speech: bool = False    # Spirit text renders differently
    is_whisper: bool = False          # Whisper text is nearly transparent
    is_silence: bool = False          # The [...] option. Ma.
    choices: List[dict] = field(default_factory=list)
    selected_choice: int = 0
    portrait: Optional[str] = None
    emotion: str = "neutral"
    time_accumulator: float = 0.0

    def set_text(self, speaker: str, text: str, is_spirit: bool = False,
                 is_whisper: bool = False, portrait: str = None,
                 emotion: str = "neutral") -> None:
        self.speaker = speaker
        self.full_text = text
        self.text = ""
        self.char_index = 0
        self.is_complete = False
        self.is_spirit_speech = is_spirit
        self.is_whisper = is_whisper
        self.is_silence = text == "..."
        self.portrait = portrait
        self.emotion = emotion
        self.time_accumulator = 0.0

    def update(self, delta: float) -> None:
        """Reveal text character by character."""
        if self.is_complete:
            return

        self.time_accumulator += delta
        chars_to_show = int(self.time_accumulator * self.chars_per_second)

        if chars_to_show > self.char_index:
            self.char_index = min(chars_to_show, len(self.full_text))
            self.text = self.full_text[:self.char_index]

            if self.char_index >= len(self.full_text):
                self.is_complete = True

    def skip_to_end(self) -> None:
        """Show full text immediately."""
        self.text = self.full_text
        self.char_index = len(self.full_text)
        self.is_complete = True

    def set_choices(self, choices: List[dict]) -> None:
        """Set dialogue choices. Include silence as an option when appropriate."""
        self.choices = choices
        self.selected_choice = 0

    def select_next_choice(self) -> None:
        if self.choices:
            self.selected_choice = (self.selected_choice + 1) % len(self.choices)

    def select_prev_choice(self) -> None:
        if self.choices:
            self.selected_choice = (self.selected_choice - 1) % len(self.choices)


@dataclass
class NotificationToast:
    """
    Subtle notifications that drift in like spirits.
    Discovery notifications shimmer. Quest updates glow warm.
    Spirit whispers appear at the edge of perception.
    """
    text: str
    toast_type: str = "info"  # info, discovery, quest, spirit_whisper, ma_threshold
    duration: float = 3.0
    elapsed: float = 0.0
    opacity: float = 0.0
    target_opacity: float = 1.0

    def update(self, delta: float) -> bool:
        """Update toast. Returns True when expired."""
        self.elapsed += delta

        # Fade in
        if self.elapsed < 0.5:
            self.opacity = self.elapsed / 0.5
        # Hold
        elif self.elapsed < self.duration - 0.5:
            self.opacity = 1.0
        # Fade out
        elif self.elapsed < self.duration:
            self.opacity = (self.duration - self.elapsed) / 0.5
        else:
            return True

        if self.toast_type == "spirit_whisper":
            self.opacity *= 0.5  # Spirit whispers are always faint

        return False
