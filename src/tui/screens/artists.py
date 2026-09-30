"""Artist screens."""

from src.tui.screens.list_screen import ListScreen
from src.tui.screens.albums import AlbumScreen


class ArtistsScreen(ListScreen):
    """Lists all album artists."""

    screen_title = "Artists"

    def load_items(self) -> list:
        return self.app.music_controller.get_all_artists() or []

    def format_item(self, item) -> tuple:
        return (item, True, "")

    def on_item_selected(self, index: int, item) -> None:
        self.app.push_screen(ArtistScreen(item))


class ArtistScreen(ListScreen):
    """Shows albums by a single album artist."""

    def __init__(self, artist_name: str):
        self._artist_name = artist_name
        super().__init__()
        self.screen_title = artist_name

    def load_items(self) -> list:
        return self.app.music_controller.get_albums_by_artist(self._artist_name) or []

    def format_item(self, item) -> tuple:
        name, _artist = item
        return (name, True, "")

    def on_item_selected(self, index: int, item) -> None:
        name, artist = item
        self.app.push_screen(AlbumScreen(name, artist))
