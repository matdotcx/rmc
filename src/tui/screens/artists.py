"""Artist screens."""

from src.tui.screens.list_screen import ListScreen


class ArtistsScreen(ListScreen):
    """Lists all artists."""

    screen_title = "Artists"

    def load_items(self) -> list:
        return self.app.music_controller.get_all_artists() or []

    def format_item(self, item) -> tuple:
        return (item, True, "")

    def on_item_selected(self, index: int, item) -> None:
        self.app.push_screen(ArtistScreen(item))


class ArtistScreen(ListScreen):
    """Shows tracks by a single artist."""

    def __init__(self, artist_name: str):
        self._artist_name = artist_name
        super().__init__()
        self.screen_title = artist_name

    def load_items(self) -> list:
        return self.app.music_controller.get_tracks_by_artist(self._artist_name) or []

    def format_item(self, item) -> tuple:
        name = item.get("name", "Unknown")
        album = item.get("album", "")
        label = f"{name} ({album})" if album else name
        return (label, False, "")

    def on_item_selected(self, index: int, item) -> None:
        self.app.music_controller.play_track(
            item.get("name", ""), item.get("artist", self._artist_name)
        )
        from src.tui.screens.now_playing import NowPlayingScreen
        self.app.push_screen(NowPlayingScreen())
