"""Album screens."""

from src.tui.screens.list_screen import ListScreen


class AlbumsScreen(ListScreen):
    """Lists all albums."""

    screen_title = "Albums"

    def load_items(self) -> list:
        return self.app.music_controller.get_all_albums() or []

    def format_item(self, item) -> tuple:
        name, artist = item
        label = f"{name} - {artist}" if artist else name
        return (label, True, "")

    def on_item_selected(self, index: int, item) -> None:
        name, artist = item
        self.app.push_screen(AlbumScreen(name, artist))


class AlbumScreen(ListScreen):
    """Shows tracks in a single album."""

    def __init__(self, album_name: str, artist: str = ""):
        self._album_name = album_name
        self._artist = artist
        super().__init__()
        self.screen_title = album_name

    def load_items(self) -> list:
        return self.app.music_controller.get_tracks_by_album(
            self._album_name, self._artist
        ) or []

    def format_item(self, item) -> tuple:
        return (item.get("name", "Unknown"), False, "")

    def on_item_selected(self, index: int, item) -> None:
        self.app.music_controller.play_track(
            item.get("name", ""), item.get("artist", self._artist)
        )
        from src.tui.screens.now_playing import NowPlayingScreen
        self.app.push_screen(NowPlayingScreen())
