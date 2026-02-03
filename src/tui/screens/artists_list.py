"""Artists list screen."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Static, ListView, ListItem, Label
from textual.reactive import reactive
from textual import work
from typing import List


class ArtistsListScreen(Screen):
    """Screen for browsing all artists."""

    BINDINGS = [
        ("left", "back", "Back"),
        ("escape", "back", "Back"),
        ("right", "view_artist", "View"),
        ("enter", "view_artist", "View"),
    ]

    artists = reactive([])

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="artists-list-container"):
            yield Static("\n  Artists\n", id="artists-list-header")
            yield Static("\n  Loading artists...\n", id="artists-list-status")
            yield ListView(id="artists-list")

    def on_mount(self) -> None:
        """Set up the screen when mounted."""
        self._load_artists()

    @work(exclusive=True, thread=True)
    def _load_artists(self) -> None:
        """Load all artists from library."""
        try:
            artists = self.app.music_controller.get_all_artists()
            self.app.call_from_thread(self._handle_artists, artists)
        except Exception as e:
            self.app.call_from_thread(self._handle_error, str(e))

    def _handle_artists(self, artists: List[str]) -> None:
        """Handle artists loaded from background thread."""
        self.artists = sorted(set(artists))  # Remove duplicates and sort
        self._update_display()

    def _handle_error(self, error: str) -> None:
        """Handle loading error."""
        status = self.query_one("#artists-list-status", Static)
        status.update(f"\n  Error loading artists: {error}\n")

    def _update_display(self) -> None:
        """Update the artists display."""
        artists_view = self.query_one("#artists-list", ListView)
        artists_view.clear()

        status = self.query_one("#artists-list-status", Static)

        if not self.artists:
            status.update("\n  No artists found\n")
            return

        status.update(f"\n  {len(self.artists)} artists\n")

        for artist in self.artists:
            artists_view.append(ListItem(Label(artist)))

        artists_view.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle artist selection."""
        if event.list_view.index is not None and event.list_view.index < len(self.artists):
            artist_name = self.artists[event.list_view.index]
            from src.tui.screens.artist import ArtistScreen
            self.app.push_screen(ArtistScreen(artist_name))

    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()

    def action_view_artist(self) -> None:
        """View the selected artist."""
        artists_view = self.query_one("#artists-list", ListView)
        if artists_view.index is not None and artists_view.index < len(self.artists):
            artist_name = self.artists[artists_view.index]
            from src.tui.screens.artist import ArtistScreen
            self.app.push_screen(ArtistScreen(artist_name))
