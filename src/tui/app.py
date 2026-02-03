"""Main Textual application for RMC."""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.binding import Binding
from textual import work
from typing import Optional
import asyncio

from src.music.pyobjc_bridge import PyObjCBridge as AppleScriptWrapper, MusicAppError
from src.tui.screens.now_playing import NowPlayingScreen
from src.config.settings import ConfigManager


class MusicController:
    """Controller for Music.app operations."""

    def __init__(self, app: 'RMCApp'):
        """Initialize music controller.

        Args:
            app: Reference to main app
        """
        self.app = app
        self.music = AppleScriptWrapper()

    def playpause(self) -> None:
        """Toggle play/pause."""
        try:
            self.music.playpause()
        except MusicAppError as e:
            self.app.notify(f"Error: {e}", severity="error")

    def play(self) -> None:
        """Start playback."""
        try:
            self.music.play()
        except MusicAppError as e:
            self.app.notify(f"Error: {e}", severity="error")

    def pause(self) -> None:
        """Pause playback."""
        try:
            self.music.pause()
        except MusicAppError as e:
            self.app.notify(f"Error: {e}", severity="error")

    def next_track(self) -> None:
        """Skip to next track."""
        try:
            self.music.next_track()
        except MusicAppError as e:
            self.app.notify(f"Error: {e}", severity="error")

    def previous_track(self) -> None:
        """Go to previous track."""
        try:
            self.music.previous_track()
        except MusicAppError as e:
            self.app.notify(f"Error: {e}", severity="error")

    def volume_up(self, step: int = 5) -> None:
        """Increase volume.

        Args:
            step: Volume increase step
        """
        try:
            current = self.music.get_volume()
            new_volume = min(100, current + step)
            self.music.set_volume(new_volume)
        except MusicAppError as e:
            self.app.notify(f"Error: {e}", severity="error")

    def volume_down(self, step: int = 5) -> None:
        """Decrease volume.

        Args:
            step: Volume decrease step
        """
        try:
            current = self.music.get_volume()
            new_volume = max(0, current - step)
            self.music.set_volume(new_volume)
        except MusicAppError as e:
            self.app.notify(f"Error: {e}", severity="error")

    def toggle_shuffle(self) -> None:
        """Toggle shuffle mode."""
        try:
            current = self.music.get_shuffle()
            self.music.set_shuffle(not current)
        except MusicAppError as e:
            self.app.notify(f"Error: {e}", severity="error")

    def cycle_repeat(self) -> None:
        """Cycle through repeat modes."""
        try:
            current = self.music.get_repeat()
            modes = ['off', 'all', 'one']
            current_index = modes.index(current) if current in modes else 0
            next_mode = modes[(current_index + 1) % len(modes)]
            self.music.set_repeat(next_mode)
        except MusicAppError as e:
            self.app.notify(f"Error: {e}", severity="error")

    def get_current_track(self):
        """Get current track information."""
        try:
            return self.music.get_current_track()
        except MusicAppError:
            return None

    def get_player_state(self):
        """Get player state."""
        try:
            return self.music.get_player_state()
        except MusicAppError:
            return 'stopped'

    def get_volume(self):
        """Get current volume."""
        try:
            return self.music.get_volume()
        except MusicAppError:
            return 50

    def get_shuffle(self):
        """Get shuffle state."""
        try:
            return self.music.get_shuffle()
        except MusicAppError:
            return False

    def get_repeat(self):
        """Get repeat mode."""
        try:
            return self.music.get_repeat()
        except MusicAppError:
            return 'off'

    def get_playlists(self):
        """Get list of playlists."""
        try:
            return self.music.get_library_playlists()
        except MusicAppError:
            return []

    def search_library(self, query: str):
        """Search the music library."""
        try:
            return self.music.search_library(query)
        except MusicAppError:
            return []

    def get_playlist_tracks(self, playlist_name: str):
        """Get tracks from a playlist."""
        try:
            return self.music.get_playlist_tracks(playlist_name)
        except MusicAppError:
            return []

    def play_track(self, track: dict):
        """Play a specific track."""
        try:
            # Use AppleScript to play the track
            track_name = track.get('name', '')
            artist = track.get('artist', '')
            self.app.notify(f"Playing: {track_name}", severity="information")
            self.music.play_track(track_name, artist)
        except MusicAppError as e:
            self.app.notify(f"Error: {e}", severity="error")

    def get_tracks_by_artist(self, artist: str):
        """Get all tracks by a specific artist."""
        try:
            return self.music.get_tracks_by_artist(artist)
        except MusicAppError:
            return []

    def get_tracks_by_album(self, album: str, artist: str = ""):
        """Get all tracks in a specific album."""
        try:
            return self.music.get_tracks_by_album(album, artist)
        except MusicAppError:
            return []

    def get_all_artists(self):
        """Get list of all artists."""
        try:
            return self.music.get_all_artists()
        except MusicAppError:
            return []

    def get_all_albums(self):
        """Get list of all albums."""
        try:
            return self.music.get_all_albums()
        except MusicAppError:
            return []


class RMCApp(App):
    """Apple Music Remote Control TUI Application."""

    CSS = """
    Screen {
        background: $surface;
    }

    #now-playing-container {
        width: 100%;
        height: 100%;
        padding: 2;
        background: $surface;
    }

    .now-playing-display {
        width: 100%;
        height: auto;
    }

    #search-container, #browse-container, #playlist-container, #artist-container, #album-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }

    #search-header, #browse-header, #playlist-header, #artist-header, #album-header {
        text-style: bold;
        height: auto;
    }

    #search-status, #browse-status, #playlist-status, #artist-status, #album-status {
        height: auto;
        margin-bottom: 1;
    }

    #search-input {
        margin-bottom: 1;
    }

    ListView {
        height: 1fr;
    }

    #main-menu-container, #artists-list-container, #albums-list-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }

    #main-menu-header, #artists-list-header, #albums-list-header {
        text-style: bold;
        height: auto;
    }

    #artists-list-status, #albums-list-status {
        height: auto;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
    ]

    TITLE = "Apple Music Remote Control"
    SUB_TITLE = "Control your music from anywhere"

    def __init__(self):
        """Initialize the application."""
        super().__init__()
        self.music_controller = MusicController(self)
        self.config_manager = ConfigManager()
        self._update_task: Optional[asyncio.Task] = None
        self._should_exit = False

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        """Set up the application when mounted."""
        from src.tui.screens.main_menu import MainMenuScreen
        self.push_screen(MainMenuScreen())
        self.start_update_loop()

    @work(exclusive=True, thread=True)
    def start_update_loop(self) -> None:
        """Start the background update loop."""
        self.update_player_state()

    def update_player_state(self) -> None:
        """Update player state from Music.app."""
        import time

        while not self._should_exit:
            try:
                # Get current track info
                track_info = self.music_controller.get_current_track()
                player_state = self.music_controller.get_player_state()
                volume = self.music_controller.get_volume()
                shuffle = self.music_controller.get_shuffle()
                repeat_mode = self.music_controller.get_repeat()

                # Update the Now Playing screen if it's active
                if isinstance(self.screen, NowPlayingScreen):
                    self.call_from_thread(
                        self._update_now_playing_screen,
                        track_info,
                        player_state,
                        volume,
                        shuffle,
                        repeat_mode
                    )

                # Sleep for update interval
                time.sleep(self.config_manager.config.ui.update_interval)

            except Exception:
                # Continue on errors
                time.sleep(1)

    def _update_now_playing_screen(
        self,
        track_info,
        player_state,
        volume,
        shuffle,
        repeat_mode
    ) -> None:
        """Update Now Playing screen with new data.

        Args:
            track_info: Current track information
            player_state: Player state
            volume: Volume level
            shuffle: Shuffle state
            repeat_mode: Repeat mode
        """
        if isinstance(self.screen, NowPlayingScreen):
            screen = self.screen
            screen.update_track_info(track_info)
            screen.player_state = player_state
            screen.volume = volume
            screen.shuffle = shuffle
            screen.repeat_mode = repeat_mode

    def action_show_now_playing(self) -> None:
        """Show the Now Playing screen."""
        if not isinstance(self.screen, NowPlayingScreen):
            self.push_screen(NowPlayingScreen())

    def action_show_search(self) -> None:
        """Show the Search screen."""
        from src.tui.screens.search import SearchScreen
        self.push_screen(SearchScreen())

    def action_show_browse(self) -> None:
        """Show the Browse screen."""
        from src.tui.screens.browse import BrowseScreen
        self.push_screen(BrowseScreen())

    def action_quit(self) -> None:
        """Quit the application."""
        self._should_exit = True
        self.exit()


def run():
    """Run the application."""
    app = RMCApp()
    app.run()


if __name__ == "__main__":
    run()
