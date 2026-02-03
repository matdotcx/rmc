"""Albums list screen."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Static, ListView, ListItem, Label
from textual.reactive import reactive
from textual import work
from typing import List, Tuple


class AlbumsListScreen(Screen):
    """Screen for browsing all albums."""

    BINDINGS = [
        ("left", "back", "Back"),
        ("escape", "back", "Back"),
        ("right", "view_album", "View"),
        ("enter", "view_album", "View"),
    ]

    albums = reactive([])

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="albums-list-container"):
            yield Static("\n  Albums\n", id="albums-list-header")
            yield Static("\n  Loading albums...\n", id="albums-list-status")
            yield ListView(id="albums-list")

    def on_mount(self) -> None:
        """Set up the screen when mounted."""
        self._load_albums()

    @work(exclusive=True, thread=True)
    def _load_albums(self) -> None:
        """Load all albums from library."""
        try:
            albums = self.app.music_controller.get_all_albums()
            self.app.call_from_thread(self._handle_albums, albums)
        except Exception as e:
            self.app.call_from_thread(self._handle_error, str(e))

    def _handle_albums(self, albums: List[Tuple[str, str]]) -> None:
        """Handle albums loaded from background thread."""
        self.albums = sorted(albums, key=lambda x: x[0])  # Sort by album name
        self._update_display()

    def _handle_error(self, error: str) -> None:
        """Handle loading error."""
        status = self.query_one("#albums-list-status", Static)
        status.update(f"\n  Error loading albums: {error}\n")

    def _update_display(self) -> None:
        """Update the albums display."""
        albums_view = self.query_one("#albums-list", ListView)
        albums_view.clear()

        status = self.query_one("#albums-list-status", Static)

        if not self.albums:
            status.update("\n  No albums found\n")
            return

        status.update(f"\n  {len(self.albums)} albums\n")

        for album_name, artist_name in self.albums:
            label_text = f"{album_name} - {artist_name}"
            albums_view.append(ListItem(Label(label_text)))

        albums_view.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle album selection."""
        if event.list_view.index is not None and event.list_view.index < len(self.albums):
            album_name, artist_name = self.albums[event.list_view.index]
            from src.tui.screens.album import AlbumScreen
            self.app.push_screen(AlbumScreen(album_name, artist_name))

    def action_back(self) -> None:
        """Go back to main menu."""
        self.app.pop_screen()

    def action_view_album(self) -> None:
        """View the selected album."""
        albums_view = self.query_one("#albums-list", ListView)
        if albums_view.index is not None and albums_view.index < len(self.albums):
            album_name, artist_name = self.albums[albums_view.index]
            from src.tui.screens.album import AlbumScreen
            self.app.push_screen(AlbumScreen(album_name, artist_name))
