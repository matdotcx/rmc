"""Songs list screen - redirects to search."""

from textual.screen import Screen


class SongsListScreen(Screen):
    """Screen for browsing songs - uses search functionality."""

    def on_mount(self) -> None:
        """Redirect to search screen."""
        from src.tui.screens.search import SearchScreen
        self.app.pop_screen()  # Remove this screen
        self.app.push_screen(SearchScreen())
