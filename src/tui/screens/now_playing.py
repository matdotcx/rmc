"""Now Playing screen for the TUI."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Static
from textual.reactive import reactive
from typing import Optional, Dict, Any


class NowPlayingScreen(Screen):
    """Screen displaying currently playing track and playback controls."""

    BINDINGS = [
        ("left", "back", "Back"),
        ("escape", "back", "Back"),
        ("space", "playpause", "Play/Pause"),
        ("n", "next_track", "Next"),
        ("p", "previous_track", "Previous"),
        ("s", "toggle_shuffle", "Shuffle"),
        ("r", "cycle_repeat", "Repeat"),
        ("+", "volume_up", "Volume Up"),
        ("-", "volume_down", "Volume Down"),
        ("a", "view_artist", "Artist"),
        ("l", "view_album", "Album"),
    ]

    # Reactive attributes
    track_name = reactive("No track playing")
    track_artist = reactive("")
    track_album = reactive("")
    track_position = reactive(0.0)
    track_duration = reactive(0.0)
    player_state = reactive("stopped")
    volume = reactive(50)
    shuffle = reactive(False)
    repeat_mode = reactive("off")

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="now-playing-container"):
            yield Static(id="now-playing-display", classes="now-playing-display")

    def on_mount(self) -> None:
        """Set up the screen when mounted."""
        self.update_display()

    def watch_track_name(self, new_value: str) -> None:
        """React to track name changes."""
        self.update_display()

    def watch_track_artist(self, new_value: str) -> None:
        """React to track artist changes."""
        self.update_display()

    def watch_track_album(self, new_value: str) -> None:
        """React to track album changes."""
        self.update_display()

    def watch_track_position(self, new_value: float) -> None:
        """React to track position changes."""
        self.update_display()

    def watch_track_duration(self, new_value: float) -> None:
        """React to track duration changes."""
        self.update_display()

    def watch_player_state(self, new_value: str) -> None:
        """React to player state changes."""
        self.update_display()

    def watch_volume(self, new_value: int) -> None:
        """React to volume changes."""
        self.update_display()

    def watch_shuffle(self, new_value: bool) -> None:
        """React to shuffle changes."""
        self.update_display()

    def watch_repeat_mode(self, new_value: str) -> None:
        """React to repeat mode changes."""
        self.update_display()

    def update_display(self) -> None:
        """Update all display elements."""
        display_widget = self.query_one("#now-playing-display", Static)
        display_widget.update(self._format_display())

    def _format_display(self) -> str:
        """Format the entire display as simple text."""
        lines = []
        lines.append("")
        lines.append(f"  ⎿  State: {self.player_state}")
        lines.append(f"     Track: {self.track_name}")

        if self.track_artist:
            lines.append(f"     Artist: {self.track_artist}")

        if self.track_album:
            lines.append(f"     Album: {self.track_album}")

        if self.track_duration > 0:
            position = self._format_duration(self.track_position)
            duration = self._format_duration(self.track_duration)
            lines.append(f"     Time: {position} / {duration}")

        lines.append("")

        # Add playback modes on one line
        modes = []
        if self.shuffle:
            modes.append("shuffle: on")
        if self.repeat_mode != "off":
            modes.append(f"repeat: {self.repeat_mode}")
        if modes:
            lines.append(f"     {' | '.join(modes)}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in seconds to MM:SS."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def update_track_info(self, track_info: Optional[Dict[str, Any]]) -> None:
        """Update track information.

        Args:
            track_info: Dictionary with track details or None
        """
        if track_info is None:
            self.track_name = "No track playing"
            self.track_artist = ""
            self.track_album = ""
            self.track_position = 0.0
            self.track_duration = 0.0
        else:
            self.track_name = track_info.get('name', 'Unknown')
            self.track_artist = track_info.get('artist', 'Unknown Artist')
            self.track_album = track_info.get('album', 'Unknown Album')
            self.track_position = track_info.get('position', 0.0)
            self.track_duration = track_info.get('duration', 0.0)

    def action_playpause(self) -> None:
        """Handle play/pause action."""
        self.app.music_controller.playpause()

    def action_next_track(self) -> None:
        """Handle next track action."""
        self.app.music_controller.next_track()

    def action_previous_track(self) -> None:
        """Handle previous track action."""
        self.app.music_controller.previous_track()

    def action_toggle_shuffle(self) -> None:
        """Handle shuffle toggle action."""
        self.app.music_controller.toggle_shuffle()

    def action_cycle_repeat(self) -> None:
        """Handle repeat mode cycle action."""
        self.app.music_controller.cycle_repeat()

    def action_volume_up(self) -> None:
        """Handle volume up action."""
        self.app.music_controller.volume_up()

    def action_volume_down(self) -> None:
        """Handle volume down action."""
        self.app.music_controller.volume_down()

    def action_view_artist(self) -> None:
        """View all tracks by the current artist."""
        if self.track_artist and self.track_artist != "Unknown Artist":
            from src.tui.screens.artist import ArtistScreen
            self.app.push_screen(ArtistScreen(self.track_artist))

    def action_view_album(self) -> None:
        """View all tracks in the current album."""
        if self.track_album and self.track_album != "Unknown Album":
            from src.tui.screens.album import AlbumScreen
            self.app.push_screen(AlbumScreen(self.track_album, self.track_artist))

    def action_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()
