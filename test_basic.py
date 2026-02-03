#!/usr/bin/env python3
"""Basic test to verify RMC components."""

from src.music.applescript import AppleScriptWrapper, MusicAppError
from src.config.settings import ConfigManager


def test_applescript_wrapper():
    """Test AppleScript wrapper initialization."""
    print("Testing AppleScript wrapper...")
    wrapper = AppleScriptWrapper()

    try:
        state = wrapper.get_player_state()
        print(f"  Player state: {state}")

        if state != 'stopped':
            track = wrapper.get_current_track()
            if track:
                print(f"  Current track: {track['name']} by {track['artist']}")
            else:
                print("  No track info available")
        else:
            print("  Music is stopped")

        volume = wrapper.get_volume()
        print(f"  Volume: {volume}%")

        shuffle = wrapper.get_shuffle()
        print(f"  Shuffle: {shuffle}")

        repeat_mode = wrapper.get_repeat()
        print(f"  Repeat: {repeat_mode}")

        print("  ✓ AppleScript wrapper working")
        return True

    except MusicAppError as e:
        print(f"  ✗ Error: {e}")
        return False


def test_config_manager():
    """Test configuration manager."""
    print("\nTesting configuration manager...")

    config_manager = ConfigManager()
    config = config_manager.load()

    print(f"  Config loaded successfully")
    print(f"  UI update interval: {config.ui.update_interval}s")
    print(f"  Storefront: {config.api.storefront}")
    print(f"  ✓ Config manager working")
    return True


def main():
    """Run basic tests."""
    print("=" * 60)
    print("RMC Basic Component Tests")
    print("=" * 60)

    results = []

    results.append(test_applescript_wrapper())
    results.append(test_config_manager())

    print("\n" + "=" * 60)
    if all(results):
        print("✓ All tests passed!")
        print("\nYou can now run the TUI with: rmc")
    else:
        print("✗ Some tests failed")
        print("\nMake sure Music.app is running and you're signed in.")
    print("=" * 60)


if __name__ == "__main__":
    main()
