"""Browse screen for the TUI."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Static, ListView, ListItem, Label
from textual.reactive import reactive
from textual import work
from typing import List


class BrowseScreen(Screen):
    """Screen for browsing playlists."""

    BINDINGS = [
        ("left", "back", "Back"),
        ("escape", "back", "Back"),
        ("right", "view_playlist", "View"),
        ("enter", "view_playlist", "View"),
    ]

    playlists = reactive([])

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="browse-container"):
            yield Static("\n  Browse Playlists\n", id="browse-header")
            yield Static("\n  Loading playlists...\n", id="browse-status")
            yield ListView(id="playlist-list")

    def on_mount(self) -> None:
        """Set up the screen when mounted."""
        self._load_playlists()

    @work(exclusive=True, thread=True)
    def _load_playlists(self) -> None:
        """Load playlists from Music.app in background thread."""
        try:
            playlists = self.app.music_controller.get_playlists()
            self.app.call_from_thread(self._handle_playlists, playlists)
        except Exception as e:
            self.app.call_from_thread(self._handle_error, str(e))

    def _handle_playlists(self, playlists: List[str]) -> None:
        """Handle playlists loaded from background thread.

        Args:
            playlists: List of playlist names
        """
        self.playlists = playlists
        self._update_display()

    def _handle_error(self, error: str) -> None:
        """Handle loading error.

        Args:
            error: Error message
        """
        status = self.query_one("#browse-status", Static)
        status.update(f"\n  Error loading playlists: {error}\n")

    def _update_display(self) -> None:
        """Update the playlists display."""
        playlist_view = self.query_one("#playlist-list", ListView)
        playlist_view.clear()

        status = self.query_one("#browse-status", Static)

        if not self.playlists:
            status.update("\n  No playlists found\n")
            return

        status.update(f"\n  {len(self.playlists)} playlists\n")

        for playlist in self.playlists:
            playlist_view.append(ListItem(Label(playlist)))

        # Focus the list so it can receive key events
        playlist_view.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle playlist selection."""
        if event.list_view.index is not None and event.list_view.index < len(self.playlists):
            playlist_name = self.playlists[event.list_view.index]
            from src.tui.screens.playlist import PlaylistScreen
            self.app.push_screen(PlaylistScreen(playlist_name))

    def action_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()

    def action_view_playlist(self) -> None:
        """View the selected playlist (fallback for enter key)."""
        playlist_view = self.query_one("#playlist-list", ListView)
        if playlist_view.index is not None and playlist_view.index < len(self.playlists):
            playlist_name = self.playlists[playlist_view.index]
            from src.tui.screens.playlist import PlaylistScreen
            self.app.push_screen(PlaylistScreen(playlist_name))
