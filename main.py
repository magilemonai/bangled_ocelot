#!/usr/bin/env python3
"""
間の国 — Ma no Kuni — The Country Between

In Tokyo, the veil between the material world and the spirit world has thinned.
The old spirits remember. The new spirits are waking. And in the space between—
in the ma—a young person named Aoi is learning to walk in both worlds.

This is a story about the spaces between things:
between people, between worlds, between words.
The silence that speaks. The pause that connects.

Press any key to begin.
Or wait. The spirits notice those who wait.
"""

import sys
import os

# Add source to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.engine.game import Game, GameState
from src.engine.config import DISPLAY, GAMEPLAY, AUDIO, SPIRIT
from src.engine.events import EventBus, EventType, GameEvent


def print_title():
    """Display the title in the terminal."""
    title = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║                        間  の  国                            ║
    ║                                                              ║
    ║                   M A   N O   K U N I                        ║
    ║                                                              ║
    ║                  The Country Between                         ║
    ║                                                              ║
    ║                         ・                                   ║
    ║                                                              ║
    ║          In the space between worlds, between words,         ║
    ║              between heartbeats — there is ma.               ║
    ║                                                              ║
    ║                And in the ma, there is you.                  ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝

                     Tokyo, Spring, Year One
                  of the Great Permeation

    """
    print(title)


def print_opening():
    """The opening text crawl."""
    opening = """
    ─────────────────────────────────────────────

    It started with small things.

    A teacup that hummed when left alone too long.
    A cat staring at an empty corner, purring.
    A crosswalk signal that flickered in a rhythm
    no engineer had programmed.

    Then the bigger things.

    The cherry trees in Inokashira Park bloomed
    in October. Every train on the Chuo Line
    arrived exactly on time for a week — including
    the ones that had been cancelled.

    Then the impossible things.

    The old woman at the shrine said she'd always
    known. The scientists said it was unprecedented.
    The politicians said it was under control.

    None of them were entirely right.

    The veil between worlds had thinned.
    Not torn — thinned. Like paper held to light.
    And through it, the spirits were remembering
    that they had always been here.

    Your name is Aoi.
    You live with your grandmother in Kichijoji.
    Her cat is named Mikan.
    You haven't spoken to your parents in a year.
    And this morning, the tea kettle said good morning.

    ─────────────────────────────────────────────
    """
    print(opening)


def initialize_game() -> Game:
    """Initialize all game systems."""
    game = Game()
    event_bus = EventBus()

    # Register the event bus
    game.register_system("events", event_bus)

    print("  [Initializing the material world...]")
    print("  [Initializing the spirit world...]")
    print("  [Thinning the veil between them...]")
    print("  [Listening for the silence...]")
    print()
    print("  Ma no Kuni is ready.")
    print()

    return game


def main():
    """Entry point for Ma no Kuni."""
    print_title()
    print_opening()

    game = initialize_game()

    print("  ─── Game Systems ───")
    print(f"  Display: {DISPLAY.SCREEN_WIDTH}x{DISPLAY.SCREEN_HEIGHT}")
    print(f"  World: Day {game.clock.day}, {game.clock.season.value}")
    print(f"  Time: {game.clock.time_of_day.value}")
    print(f"  Spirit Permeability: {game.clock.spirit_permeability:.0%}")
    print(f"  Ma Level: {game.ma.current_ma:.0f}/{game.ma.max_ma:.0f}")
    print()
    print("  The journey begins in Kichijoji.")
    print("  Grandmother is making tea.")
    print("  Mikan is watching something you can't see.")
    print()
    print("  ...yet.")
    print()


if __name__ == "__main__":
    main()
