"""Main menu screen - iPod style."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Static, ListView, ListItem, Label
from textual import work
import asyncio


class MainMenuScreen(Screen):
    """iPod-style main menu."""

    BINDINGS = [
        ("escape", "quit_app", "Quit"),
        ("enter", "select_item", "Select"),
    ]

    def __init__(self):
        """Initialize the main menu."""
        super().__init__()
        self._inactivity_task = None
        self._last_activity = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="main-menu-container"):
            yield Static("\n  Music\n", id="main-menu-header")
            yield ListView(id="main-menu-list")

    def on_mount(self) -> None:
        """Set up the screen when mounted."""
        self._populate_menu()
        # Disabled inactivity timer for now - causes lockups
        # self._start_inactivity_timer()

    def _populate_menu(self) -> None:
        """Populate the menu items."""
        menu_view = self.query_one("#main-menu-list", ListView)
        menu_view.clear()

        items = [
            "Now Playing",
            "Playlists",
            "Artists",
            "Albums",
            "Songs",
            "Search",
        ]

        for item in items:
            menu_view.append(ListItem(Label(item)))

        menu_view.focus()

    def _reset_inactivity_timer(self) -> None:
        """Reset the inactivity timer."""
        import time
        self._last_activity = time.time()

    def _start_inactivity_timer(self) -> None:
        """Start monitoring for inactivity."""
        self._reset_inactivity_timer()
        self.set_interval(1.0, self._check_inactivity)

    def _check_inactivity(self) -> None:
        """Check if we should return to Now Playing."""
        import time
        # Only activate if we're the current screen AND have been inactive
        if not isinstance(self.app.screen, MainMenuScreen):
            return  # Don't interrupt if user navigated away

        if self._last_activity and (time.time() - self._last_activity) > 30:
            # Return to now playing after 30 seconds of inactivity on main menu
            from src.tui.screens.now_playing import NowPlayingScreen
            self.app.push_screen(NowPlayingScreen())

    def on_key(self, event) -> None:
        """Reset timer on any key press."""
        self._reset_inactivity_timer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle menu selection."""
        self._reset_inactivity_timer()

        if event.list_view.index is None:
            return

        items = ["Now Playing", "Playlists", "Artists", "Albums", "Songs", "Search"]
        selected = items[event.list_view.index]

        if selected == "Now Playing":
            from src.tui.screens.now_playing import NowPlayingScreen
            self.app.push_screen(NowPlayingScreen())
        elif selected == "Playlists":
            from src.tui.screens.browse import BrowseScreen
            self.app.push_screen(BrowseScreen())
        elif selected == "Artists":
            from src.tui.screens.artists_list import ArtistsListScreen
            self.app.push_screen(ArtistsListScreen())
        elif selected == "Albums":
            from src.tui.screens.albums_list import AlbumsListScreen
            self.app.push_screen(AlbumsListScreen())
        elif selected == "Songs":
            from src.tui.screens.songs_list import SongsListScreen
            self.app.push_screen(SongsListScreen())
        elif selected == "Search":
            from src.tui.screens.search import SearchScreen
            self.app.push_screen(SearchScreen())

    def action_select_item(self) -> None:
        """Select the current menu item."""
        menu_view = self.query_one("#main-menu-list", ListView)
        if menu_view.index is not None:
            # Trigger selection
            items = menu_view.query(ListItem)
            if menu_view.index < len(items):
                self.on_list_view_selected(ListView.Selected(menu_view, items[menu_view.index]))

    def action_quit_app(self) -> None:
        """Quit the application."""
        self.app.action_quit()
