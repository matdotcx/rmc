"""Main menu screen - iPod style."""

import time
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static
from textual.reactive import reactive

from src.tui.widgets import MenuItem


class MainMenuScreen(Screen):
    """iPod-style main menu."""

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
        super().__init__()
        self._last_activity = time.time()
        self._inactivity_timer = None
        self.menu_items = [
            ("Now Playing", True, "*"),
            ("Playlists", True, ""),
            ("Artists", True, ""),
            ("Albums", True, ""),
            ("Search", True, ""),
            ("Settings", True, ""),
        ]

    def compose(self) -> ComposeResult:
        yield Static("Music".center(48), id="main-menu-header")
        with Vertical(id="main-menu-list"):
            for i, (label, has_chevron, indicator) in enumerate(self.menu_items):
                item = MenuItem(label, has_chevron, indicator, id=f"menu-item-{i}")
                if i == 0:
                    item.add_class("selected")
                yield item
        yield Static("", id="main-menu-status")

    def on_mount(self) -> None:
        self._inactivity_timer = self.set_interval(1.0, self._check_inactivity)
        self._update_index_status()

    def _update_index_status(self) -> None:
        exists, age, count = self.app.music_controller.index_status()
        if exists:
            status_text = f"Library: {age} | {count:,} tracks"
        else:
            status_text = "Library: not indexed"
        try:
            self.query_one("#main-menu-status", Static).update(status_text)
        except Exception:
            pass

    def _reset_inactivity_timer(self) -> None:
        self._last_activity = time.time()

    def _check_inactivity(self) -> None:
        timeout = self.app.config_manager.config.ui.inactivity_timeout
        if timeout == 0:
            return

        if self.app.screen is not self:
            return

        elapsed = time.time() - self._last_activity
        if elapsed >= timeout:
            from src.tui.screens.now_playing import NowPlayingScreen
            self._reset_inactivity_timer()
            self.app.push_screen(NowPlayingScreen())

    def watch_selected_index(self, old_index: int, new_index: int) -> None:
        if old_index != new_index:
            try:
                self.query_one(f"#menu-item-{old_index}", MenuItem).remove_class("selected")
                self.query_one(f"#menu-item-{new_index}", MenuItem).add_class("selected")
            except Exception:
                pass

    def action_move_up(self) -> None:
        self._reset_inactivity_timer()
        if self.selected_index > 0:
            self.selected_index -= 1

    def action_move_down(self) -> None:
        self._reset_inactivity_timer()
        if self.selected_index < len(self.menu_items) - 1:
            self.selected_index += 1

    def on_screen_resume(self) -> None:
        self._update_index_status()

    def on_key(self, event) -> None:
        self._reset_inactivity_timer()

    def action_select_item(self) -> None:
        self._reset_inactivity_timer()
        selected_label = self.menu_items[self.selected_index][0]

        if selected_label == "Now Playing":
            from src.tui.screens.now_playing import NowPlayingScreen
            self.app.push_screen(NowPlayingScreen())
        elif selected_label == "Playlists":
            from src.tui.screens.playlists import PlaylistsScreen
            self.app.push_screen(PlaylistsScreen())
        elif selected_label == "Artists":
            from src.tui.screens.artists import ArtistsScreen
            self.app.push_screen(ArtistsScreen())
        elif selected_label == "Albums":
            from src.tui.screens.albums import AlbumsScreen
            self.app.push_screen(AlbumsScreen())
        elif selected_label == "Search":
            from src.tui.screens.search import SearchScreen
            self.app.push_screen(SearchScreen())
        elif selected_label == "Settings":
            from src.tui.screens.settings import SettingsScreen
            self.app.push_screen(SettingsScreen())

    def action_back(self) -> None:
        pass

    def action_quit_app(self) -> None:
        self.app.action_quit()
