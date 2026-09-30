"""Artist screens."""

from src.tui.screens.list_screen import ListScreen, SongListScreen, sort_key
from src.tui.screens.albums import AlbumScreen

ALL_SONGS = object()


class ArtistsScreen(ListScreen):
    """Lists all album artists."""

    screen_title = "Artists"

    def load_items(self) -> list:
        return sorted(self.app.music_controller.get_all_artists() or [], key=sort_key)

    def format_item(self, item) -> tuple:
        return (item, True, "")

    def on_item_selected(self, index: int, item) -> None:
        self.app.push_screen(ArtistScreen(item))


class ArtistScreen(ListScreen):
    """Albums by a single album artist, with "All Songs" first when there are several."""

    def __init__(self, artist_name: str):
        self._artist_name = artist_name
        super().__init__()
        self.screen_title = artist_name

    def load_items(self) -> list:
        albums = self.app.music_controller.get_albums_by_artist(self._artist_name) or []
        return [ALL_SONGS] + albums if len(albums) > 1 else albums

    def format_item(self, item) -> tuple:
        if item is ALL_SONGS:
            return ("All Songs", True, "")
        name, _artist = item
        return (name, True, "")

    def on_item_selected(self, index: int, item) -> None:
        if item is ALL_SONGS:
            self.app.push_screen(ArtistSongsScreen(self._artist_name))
        else:
            name, artist = item
            self.app.push_screen(AlbumScreen(name, artist))


class ArtistSongsScreen(SongListScreen):
    """Every song by an album artist, album by album."""

    def __init__(self, artist_name: str):
        self._artist_name = artist_name
        super().__init__()
        self.screen_title = artist_name

    def load_items(self) -> list:
        return self.app.music_controller.get_tracks_by_artist(self._artist_name) or []
