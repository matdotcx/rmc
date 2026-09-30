"""Album screens."""

from src.tui.screens.list_screen import ListScreen, SongListScreen


class AlbumsScreen(ListScreen):
    """Lists all albums."""

    screen_title = "Albums"

    def load_items(self) -> list:
        return self.app.music_controller.get_all_albums() or []

    def format_item(self, item) -> tuple:
        name, _artist = item
        return (name, True, "")

    def on_item_selected(self, index: int, item) -> None:
        name, artist = item
        self.app.push_screen(AlbumScreen(name, artist))


class AlbumScreen(SongListScreen):
    """Shows the songs of a single album, in album order."""

    def __init__(self, album_name: str, artist: str = ""):
        self._album_name = album_name
        self._artist = artist
        super().__init__()
        self.screen_title = album_name

    def load_items(self) -> list:
        return self.app.music_controller.get_tracks_by_album(
            self._album_name, self._artist
        ) or []
