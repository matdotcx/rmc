"""Main menu screen - iPod style."""

import time
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static
from textual.reactive import reactive

from src.tui.widgets import MenuItem


class MainMenuScreen(Screen):
    """iPod-style main menu with single-line items and right-justified chevrons."""

    BINDINGS = [
        ("left", "back", "Back"),
        ("escape", "quit_app", "Quit"),
        ("right", "select_item", "Select"),
        ("enter", "select_item", "Select"),
        ("up", "move_up", "Up"),
        ("down", "move_down", "Down"),
        ("k", "move_up", "Up"),
        ("j", "move_down", "Down"),
    ]

    selected_index = reactive(0)

    def __init__(self):
        """Initialize the main menu."""
        super().__init__()
        self._last_activity = time.time()
        self._inactivity_timer = None
        self.menu_items = [
            ("Now Playing", True, "*"),
            ("Playlists", True, ""),
            ("Artists", True, ""),
            ("Albums", True, ""),
            ("Songs", True, ""),
            ("Search", True, ""),
            ("Reindex Library", False, ""),
            ("Settings", True, ""),
        ]

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static("Music".center(48), id="main-menu-header")
        with Vertical(id="main-menu-list"):
            for i, (label, has_chevron, indicator) in enumerate(self.menu_items):
                item = MenuItem(label, has_chevron, indicator, id=f"menu-item-{i}")
                if i == 0:
                    item.add_class("selected")
                yield item
        yield Static("", id="main-menu-status")

    def on_mount(self) -> None:
        """Set up the screen when mounted."""
        self._update_status()
        self.set_interval(2.0, self._update_status)
        # Start inactivity monitoring
        self._inactivity_timer = self.set_interval(1.0, self._check_inactivity)

    def _update_status(self) -> None:
        """Update the index status display."""
        try:
            status_text = self.app.get_index_status()
            status = self.query_one("#main-menu-status", Static)
            status.update(f"  Index: {status_text}")
        except Exception:
            pass

    def _reset_inactivity_timer(self) -> None:
        """Reset the inactivity timer."""
        self._last_activity = time.time()

    def _check_inactivity(self) -> None:
        """Check if we should return to Now Playing due to inactivity."""
        timeout = self.app.config_manager.config.ui.inactivity_timeout
        if timeout == 0:
            return  # Disabled

        # Only trigger if this screen is active
        if self.app.screen is not self:
            return

        elapsed = time.time() - self._last_activity
        if elapsed >= timeout:
            from src.tui.screens.now_playing import NowPlayingScreen
            # Reset timer before navigation to avoid re-triggering
            self._reset_inactivity_timer()
            self.app.push_screen(NowPlayingScreen())

    def watch_selected_index(self, old_index: int, new_index: int) -> None:
        """Update selection styling when index changes."""
        if old_index != new_index:
            try:
                self.query_one(f"#menu-item-{old_index}", MenuItem).remove_class("selected")
                self.query_one(f"#menu-item-{new_index}", MenuItem).add_class("selected")
            except Exception:
                pass

    def action_move_up(self) -> None:
        """Move selection up."""
        self._reset_inactivity_timer()
        if self.selected_index > 0:
            self.selected_index -= 1

    def action_move_down(self) -> None:
        """Move selection down."""
        self._reset_inactivity_timer()
        if self.selected_index < len(self.menu_items) - 1:
            self.selected_index += 1

    def on_key(self, event) -> None:
        """Reset timer on any key press."""
        self._reset_inactivity_timer()

    def action_select_item(self) -> None:
        """Handle menu selection."""
        self._reset_inactivity_timer()
        selected_label = self.menu_items[self.selected_index][0]

        if selected_label == "Now Playing":
            from src.tui.screens.now_playing import NowPlayingScreen
            self.app.push_screen(NowPlayingScreen())
        elif selected_label == "Playlists":
            from src.tui.screens.browse import BrowseScreen
            self.app.push_screen(BrowseScreen())
        elif selected_label == "Artists":
            from src.tui.screens.artists_list import ArtistsListScreen
            self.app.push_screen(ArtistsListScreen())
        elif selected_label == "Albums":
            from src.tui.screens.albums_list import AlbumsListScreen
            self.app.push_screen(AlbumsListScreen())
        elif selected_label == "Songs":
            from src.tui.screens.songs_list import SongsListScreen
            self.app.push_screen(SongsListScreen())
        elif selected_label == "Search":
            from src.tui.screens.search import SearchScreen
            self.app.push_screen(SearchScreen())
        elif selected_label == "Reindex Library":
            self.app.action_reindex()
        elif selected_label == "Settings":
            from src.tui.screens.settings import SettingsScreen
            self.app.push_screen(SettingsScreen())

    def action_back(self) -> None:
        """Back does nothing on main menu (we're at the root)."""
        pass

    def action_quit_app(self) -> None:
        """Quit the application."""
        self.app.action_quit()
