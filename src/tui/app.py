"""Main Textual application for RMC."""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.binding import Binding
from textual import work
from typing import Optional, List, Dict, Any, Tuple
import asyncio

from src.music.pyobjc_bridge import PyObjCBridge as AppleScriptWrapper, MusicAppError
from src.tui.screens.now_playing import NowPlayingScreen
from src.config.settings import ConfigManager
from src.index import LibraryIndex, LibraryIndexer


class MusicController:
    """Controller for Music.app operations."""

    def __init__(self, app: 'RMCApp', index: Optional[LibraryIndex] = None):
        """Initialize music controller.

        Args:
            app: Reference to main app
            index: Optional library index for fast search/browse
        """
        self.app = app
        self.music = AppleScriptWrapper()
        self.index = index

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

    def search_library(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Search the music library using index if available.

        Args:
            query: Search query string
            limit: Maximum results to return

        Returns:
            List of track dictionaries
        """
        # Use index if available and has data
        if self.index and self.index.exists():
            return self.index.search(query, limit=limit)

        # Fall back to live AppleScript search
        try:
            return self.music.search_library(query)
        except MusicAppError:
            return []

    def get_playlist_tracks(self, playlist_name: str) -> List[Dict[str, Any]]:
        """Get tracks from a playlist.

        Args:
            playlist_name: Name of the playlist

        Returns:
            List of track dictionaries
        """
        # Use live query for playlists to ensure accuracy
        # (playlists may change more frequently than the full library)
        try:
            return self.music.get_playlist_tracks(playlist_name)
        except MusicAppError:
            # Fall back to index if live query fails
            if self.index and self.index.exists():
                return self.index.get_playlist_tracks(playlist_name)
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

    def get_tracks_by_artist(self, artist: str) -> List[Dict[str, Any]]:
        """Get all tracks by a specific artist.

        Args:
            artist: Artist name

        Returns:
            List of track dictionaries
        """
        # Use index if available
        if self.index and self.index.exists():
            return self.index.get_tracks_by_artist(artist)

        try:
            return self.music.get_tracks_by_artist(artist)
        except MusicAppError:
            return []

    def get_tracks_by_album(self, album: str, artist: str = "") -> List[Dict[str, Any]]:
        """Get all tracks in a specific album.

        Args:
            album: Album name
            artist: Artist name (optional)

        Returns:
            List of track dictionaries
        """
        # Use index if available
        if self.index and self.index.exists():
            return self.index.get_tracks_by_album(album, artist)

        try:
            return self.music.get_tracks_by_album(album, artist)
        except MusicAppError:
            return []

    def get_all_artists(self) -> List[str]:
        """Get list of all artists.

        Returns:
            List of artist names
        """
        # Use index if available
        if self.index and self.index.exists():
            return self.index.get_all_artists()

        try:
            return self.music.get_all_artists()
        except MusicAppError:
            return []

    def get_all_albums(self) -> List[Tuple[str, str]]:
        """Get list of all albums.

        Returns:
            List of (album_name, artist_name) tuples
        """
        # Use index if available
        if self.index and self.index.exists():
            return self.index.get_all_albums()

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

    #main-menu-status {
        height: auto;
        margin-top: 1;
        color: $text-muted;
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
        self.config_manager = ConfigManager()

        # Initialize library index
        self.library_index = LibraryIndex()
        self.music_controller = MusicController(self, index=self.library_index)

        # Initialize indexer (bridge from music_controller)
        self.library_indexer = LibraryIndexer(
            self.music_controller.music,
            self.library_index
        )

        self._update_task: Optional[asyncio.Task] = None
        self._should_exit = False
        self._indexing = False

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        """Set up the application when mounted."""
        from src.tui.screens.main_menu import MainMenuScreen
        self.push_screen(MainMenuScreen())
        self.start_update_loop()
        self._check_index_on_launch()

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
        if self.library_index:
            self.library_index.close()
        self.exit()

    def _check_index_on_launch(self) -> None:
        """Check if index needs to be built or refreshed on launch."""
        config = self.config_manager.config.index

        if not config.auto_index_on_launch:
            return

        # Check if index exists and is not stale
        if not self.library_index.exists():
            self.notify("Building library index for first time...")
            self._trigger_reindex()
        elif self.library_index.is_stale(config.stale_warning_hours):
            metadata = self.library_index.get_metadata()
            track_count = metadata.get('track_count', 0)
            age = self.library_index.get_age_description()
            self.notify(f"Index stale ({track_count} tracks, {age}) - rebuilding...")
            self._trigger_reindex()

    @work(exclusive=True, thread=True)
    def _trigger_reindex(self) -> None:
        """Trigger background reindex."""
        if self._indexing:
            return

        self._indexing = True

        def progress_callback(current: int, total: int, phase: str) -> None:
            if total > 0:
                self.call_from_thread(
                    self.notify,
                    f"Indexing: {phase} ({current}/{total})"
                )

        self.library_indexer.set_progress_callback(progress_callback)

        success = self.library_indexer.rebuild_full()

        self._indexing = False

        if success:
            metadata = self.library_index.get_metadata()
            track_count = metadata.get('track_count', 0)
            self.call_from_thread(
                self.notify,
                f"Index complete: {track_count} tracks"
            )
        else:
            self.call_from_thread(
                self.notify,
                "Index build failed",
                severity="error"
            )

    def action_reindex(self) -> None:
        """Manually trigger library reindex."""
        if self._indexing:
            self.notify("Indexing already in progress...")
            return

        self.notify("Starting library reindex...")
        self._trigger_reindex()

    def get_index_status(self) -> str:
        """Get human-readable index status.

        Returns:
            Status string like "15,432 tracks (2h ago)" or "not indexed"
        """
        if self._indexing:
            progress = self.library_indexer.get_progress()
            current, total, phase = progress
            if total > 0:
                return f"Indexing: {current}/{total}"
            return f"Indexing: {phase}"

        if not self.library_index.exists():
            return "Not indexed"

        metadata = self.library_index.get_metadata()
        track_count = metadata.get('track_count', 0)
        age = self.library_index.get_age_description()

        config = self.config_manager.config.index
        if self.library_index.is_stale(config.stale_warning_hours):
            return f"{track_count:,} tracks (stale - {age})"

        return f"{track_count:,} tracks ({age})"


def run():
    """Run the application."""
    app = RMCApp()
    app.run()


if __name__ == "__main__":
    run()
