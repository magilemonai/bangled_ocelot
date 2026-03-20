#!/usr/bin/env python3
"""
間の国 — Ma no Kuni — The Country Between

In Tokyo, the veil between the material world and the spirit world has thinned.
The old spirits remember. The new spirits are waking. And in the space between—
in the ma—a young person named Aoi is learning to walk in both worlds.

Press any key to begin.
Or wait. The spirits notice those who wait.
"""

import sys
import os
import logging

# Add source to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def setup_logging() -> None:
    """Configure logging for the game."""
    logging.basicConfig(
        level=logging.INFO,
        format="  [%(name)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )


def main():
    """Entry point for Ma no Kuni."""
    setup_logging()
    logger = logging.getLogger("ma_no_kuni")

    print()
    print("  間の国 — Ma no Kuni — The Country Between")
    print("  ─────────────────────────────────────────")
    print()

    # Step 1: Bootstrap the game world from data files
    logger.info("Initializing the material world...")

    try:
        from src.engine.bootstrap import GameBootstrap
        bootstrap = GameBootstrap()
        systems = bootstrap.initialize()
    except Exception as e:
        logger.error("Bootstrap failed: %s", e)
        import traceback
        traceback.print_exc()
        print("\n  The world could not be initialized.")
        print("  Check the logs above for details.")
        return

    game = systems["game"]
    event_bus = systems["event_bus"]

    logger.info("Thinning the veil between worlds...")
    logger.info(
        "World: Day %d, %s, %s | Permeability: %.0f%% | Ma: %.0f/%.0f",
        game.clock.day,
        game.clock.season.value,
        game.clock.time_of_day.value,
        game.clock.spirit_permeability * 100,
        game.ma.current_ma,
        game.ma.max_ma,
    )

    # Step 2: Create the pygame game loop
    logger.info("Opening the window to both worlds...")

    try:
        from src.engine.game_loop import GameLoop
        from src.engine.input_handler import InputHandler

        loop = GameLoop()

        # Override the loop's game with our bootstrapped one
        loop._game = game
        loop._event_bus = event_bus

        # Create and register input handler
        input_handler = InputHandler(event_bus=event_bus)
        loop.register_input_handler(input_handler)

        # Register scene manager from bootstrap
        scene_manager = systems.get("scene_manager")
        if scene_manager is not None:
            loop.register_scene_manager(scene_manager)

        logger.info("Ma no Kuni is ready.")
        logger.info("The journey begins in Kichijoji.")
        print()

        # Step 3: Run the game
        loop.run()

    except ImportError as e:
        logger.error("Could not start pygame: %s", e)
        print(f"\n  Missing dependency: {e}")
        print("  Run: pip install pygame")
        return
    except Exception as e:
        logger.error("Game crashed: %s", e)
        import traceback
        traceback.print_exc()
        return

    print()
    print("  The spirits will remember you.")
    print("  間")
    print()


if __name__ == "__main__":
    main()
