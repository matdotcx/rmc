"""Playlist screens."""

from src.tui.screens.list_screen import ListScreen, SongListScreen


class PlaylistsScreen(ListScreen):
    """Lists all playlists."""

    screen_title = "Playlists"

    def load_items(self) -> list:
        return self.app.music_controller.get_playlists() or []

    def format_item(self, item) -> tuple:
        return (item["name"], True, "")

    def on_item_selected(self, index: int, item) -> None:
        self.app.push_screen(PlaylistScreen(item))


class PlaylistScreen(SongListScreen):
    """Shows the songs of a single playlist, in playlist order."""

    def __init__(self, playlist: dict):
        self._playlist = playlist
        super().__init__()
        self.screen_title = playlist["name"]

    def load_items(self) -> list:
        return self.app.music_controller.get_playlist_tracks(self._playlist["music_id"]) or []
