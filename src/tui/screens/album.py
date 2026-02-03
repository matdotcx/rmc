"""Album view screen for the TUI."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Static, ListView, ListItem, Label
from textual.reactive import reactive
from textual import work
from typing import List, Dict, Any


class AlbumScreen(Screen):
    """Screen for viewing tracks in a specific album."""

    BINDINGS = [
        ("left", "back", "Back"),
        ("escape", "back", "Back"),
        ("right", "play_selected", "Play"),
        ("enter", "play_selected", "Play"),
    ]

    tracks = reactive([])

    def __init__(self, album_name: str, artist_name: str = ""):
        """Initialize the album screen.

        Args:
            album_name: Name of the album
            artist_name: Name of the artist (optional)
        """
        super().__init__()
        self.album_name = album_name
        self.artist_name = artist_name

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="album-container"):
            if self.artist_name:
                yield Static(f"\n  Album: {self.album_name}\n  Artist: {self.artist_name}\n", id="album-header")
            else:
                yield Static(f"\n  Album: {self.album_name}\n", id="album-header")
            yield Static("\n  Loading tracks...\n", id="album-status")
            yield ListView(id="track-list")

    def on_mount(self) -> None:
        """Set up the screen when mounted."""
        self._load_tracks()

    @work(exclusive=True, thread=True)
    def _load_tracks(self) -> None:
        """Load tracks in the album in background thread."""
        try:
            tracks = self.app.music_controller.get_tracks_by_album(self.album_name, self.artist_name)
            self.app.call_from_thread(self._handle_tracks, tracks)
        except Exception as e:
            self.app.call_from_thread(self._handle_error, str(e))

    def _handle_tracks(self, tracks: List[Dict[str, Any]]) -> None:
        """Handle tracks loaded from background thread.

        Args:
            tracks: List of track dictionaries
        """
        self.tracks = tracks
        self._update_display()

    def _handle_error(self, error: str) -> None:
        """Handle loading error.

        Args:
            error: Error message
        """
        status = self.query_one("#album-status", Static)
        status.update(f"\n  Error loading tracks: {error}\n")

    def _update_display(self) -> None:
        """Update the tracks display."""
        track_view = self.query_one("#track-list", ListView)
        track_view.clear()

        status = self.query_one("#album-status", Static)

        if not self.tracks:
            status.update("\n  No tracks found in this album\n")
            return

        status.update(f"\n  {len(self.tracks)} tracks\n")

        for track in self.tracks:
            name = track.get('name', 'Unknown')
            artist = track.get('artist', 'Unknown Artist')
            label = f"{name} - {artist}"
            track_view.append(ListItem(Label(label)))

        # Focus the list
        track_view.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle track selection."""
        if event.list_view.index is not None and event.list_view.index < len(self.tracks):
            track = self.tracks[event.list_view.index]
            self.app.music_controller.play_track(track)

    def action_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()

    def action_play_selected(self) -> None:
        """Play the selected track (fallback for enter key)."""
        track_view = self.query_one("#track-list", ListView)
        if track_view.index is not None and track_view.index < len(self.tracks):
            track = self.tracks[track_view.index]
            self.app.music_controller.play_track(track)
