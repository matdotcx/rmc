"""iPod menu screens: the top-level menu and the Music menu."""

import time

from src.tui.screens.list_screen import ListScreen


def _now_playing_screen():
    from src.tui.screens.now_playing import NowPlayingScreen
    return NowPlayingScreen()


class MenuScreen(ListScreen):
    """A fixed iPod menu. Items are (label, has_chevron, action) tuples."""

    def menu(self) -> list:
        raise NotImplementedError

    def load_items(self) -> list:
        return self.menu()

    def format_item(self, item) -> tuple:
        label, has_chevron, _action = item
        return (label, has_chevron, "")

    def on_item_selected(self, index: int, item) -> None:
        item[2]()


class MainMenuScreen(MenuScreen):
    """The top-level "iPod" menu.

    Like the iPod, "Now Playing" is only listed while something is playing,
    and after a period of inactivity the menu gives way to Now Playing.
    """

    screen_title = "iPod"

    BINDINGS = [("escape", "quit_app", "Quit")]

    def __init__(self):
        super().__init__()
        self._last_activity = time.time()

    def menu(self) -> list:
        from src.tui.screens.settings import SettingsScreen
        items = [
            ("Music", True, lambda: self.app.push_screen(MusicMenuScreen())),
            ("Settings", True, lambda: self.app.push_screen(SettingsScreen())),
            ("Shuffle Songs", False, self._shuffle_songs),
        ]
        if self._is_playing():
            items.append(("Now Playing", True, lambda: self.app.push_screen(_now_playing_screen())))
        return items

    def _is_playing(self) -> bool:
        status = getattr(self.app, "player_status", None) or {}
        return status.get("state") in ("playing", "paused")

    def _shuffle_songs(self) -> None:
        self.app.music_controller.shuffle_songs()
        self.app.push_screen(_now_playing_screen())

    # Textual calls on_mount/on_key on every class in the MRO, so these run
    # alongside ListScreen's handlers without calling super().
    def on_mount(self) -> None:
        self.set_interval(1.0, self._check_inactivity)

    def on_player_status(self) -> None:
        super().on_player_status()
        # Add or drop "Now Playing" when playback starts or stops.
        if self._items and len(self.menu()) != len(self._items):
            selected = self._selected
            self._populate(self.menu())
            self._select(selected)

    def on_key(self, event) -> None:
        self._last_activity = time.time()

    def on_screen_resume(self) -> None:
        self._last_activity = time.time()

    def _check_inactivity(self) -> None:
        timeout = self.app.config_manager.config.ui.inactivity_timeout
        if timeout == 0 or self.app.screen is not self or not self._is_playing():
            return
        if time.time() - self._last_activity >= timeout:
            self._last_activity = time.time()
            self.app.push_screen(_now_playing_screen())

    def action_back(self) -> None:
        pass

    def action_quit_app(self) -> None:
        self.app.action_quit()


class MusicMenuScreen(MenuScreen):
    """The iPod "Music" menu."""

    screen_title = "Music"

    def menu(self) -> list:
        from src.tui.screens.playlists import PlaylistsScreen
        from src.tui.screens.artists import ArtistsScreen
        from src.tui.screens.albums import AlbumsScreen
        from src.tui.screens.songs import SongsScreen
        from src.tui.screens.search import SearchScreen

        def opener(screen_class):
            return lambda: self.app.push_screen(screen_class())

        return [
            ("Playlists", True, opener(PlaylistsScreen)),
            ("Artists", True, opener(ArtistsScreen)),
            ("Albums", True, opener(AlbumsScreen)),
            ("Songs", True, opener(SongsScreen)),
            ("Search", True, opener(SearchScreen)),
        ]
