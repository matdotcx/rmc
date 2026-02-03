"""Search screen for the TUI."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Static, Input, ListView, ListItem, Label
from textual.reactive import reactive
from textual import work
from typing import List, Dict, Any


class SearchScreen(Screen):
    """Screen for searching the music library."""

    BINDINGS = [
        ("left", "back", "Back"),
        ("escape", "back", "Back"),
        ("right", "play_selected", "Play"),
        ("enter", "play_selected", "Play"),
        ("tab", "focus_results", "Results"),
    ]

    search_results = reactive([])

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="search-container"):
            yield Static("\n  Search Library\n", id="search-header")
            yield Input(placeholder="Type to search tracks, artists, albums...", id="search-input")
            yield Static("", id="search-status")
            yield ListView(id="search-results")

    def on_mount(self) -> None:
        """Set up the screen when mounted."""
        self.query_one("#search-input", Input).focus()
        self._last_query = ""

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        query = event.value.strip()

        if len(query) < 3:
            self.search_results = []
            self._update_results_display()
            return

        # Only search if query changed significantly
        if query != self._last_query:
            self._last_query = query
            status = self.query_one("#search-status", Static)
            status.update("\n  Searching...\n")
            self._perform_search(query)

    @work(exclusive=True, thread=True)
    def _perform_search(self, query: str) -> None:
        """Perform library search in background thread.

        Args:
            query: Search query string
        """
        try:
            results = self.app.music_controller.search_library(query)
            self.app.call_from_thread(self._handle_search_results, results)
        except Exception as e:
            self.app.call_from_thread(self._handle_search_error, str(e))

    def _handle_search_results(self, results: List[Dict[str, Any]]) -> None:
        """Handle search results from background thread.

        Args:
            results: List of track dictionaries
        """
        self.search_results = results
        self._update_results_display()

    def _handle_search_error(self, error: str) -> None:
        """Handle search error.

        Args:
            error: Error message
        """
        status = self.query_one("#search-status", Static)
        status.update(f"\n  Error: {error}\n")

    def _update_results_display(self) -> None:
        """Update the search results display."""
        results_view = self.query_one("#search-results", ListView)
        results_view.clear()

        status = self.query_one("#search-status", Static)

        if not self.search_results:
            status.update("\n  No results\n")
            return

        status.update(f"\n  Found {len(self.search_results)} tracks (Tab to select)\n")

        for track in self.search_results:
            name = track.get('name', 'Unknown')
            artist = track.get('artist', 'Unknown Artist')
            album = track.get('album', 'Unknown Album')
            label = f"{name} - {artist} ({album})"
            results_view.append(ListItem(Label(label)))

        # Don't auto-focus - let user Tab to results

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle track selection."""
        if event.list_view.index is not None and event.list_view.index < len(self.search_results):
            track = self.search_results[event.list_view.index]
            self.app.music_controller.play_track(track)

    def action_focus_results(self) -> None:
        """Focus the search results list."""
        results_view = self.query_one("#search-results", ListView)
        if self.search_results:
            results_view.focus()

    def action_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()

    def action_play_selected(self) -> None:
        """Play the selected track (fallback for enter key)."""
        results_view = self.query_one("#search-results", ListView)
        if results_view.index is not None and results_view.index < len(self.search_results):
            track = self.search_results[results_view.index]
            self.app.music_controller.play_track(track)
            self.app.notify(f"Playing: {track['name']}")
