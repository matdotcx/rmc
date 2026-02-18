"""Playlist screens."""

from src.tui.screens.list_screen import ListScreen


class PlaylistsScreen(ListScreen):
    """Lists all playlists."""

    screen_title = "Playlists"

    def load_items(self) -> list:
        return self.app.music_controller.get_playlists() or []

    def format_item(self, item) -> tuple:
        return (item, True, "")

    def on_item_selected(self, index: int, item) -> None:
        self.app.music_controller.play_playlist(item)
        from src.tui.screens.now_playing import NowPlayingScreen
        self.app.push_screen(NowPlayingScreen())


class PlaylistScreen(ListScreen):
    """Shows tracks in a single playlist."""

    def __init__(self, playlist_name: str):
        self._playlist_name = playlist_name
        super().__init__()
        self.screen_title = playlist_name

    def load_items(self) -> list:
        return self.app.music_controller.get_playlist_tracks(self._playlist_name) or []

    def format_item(self, item) -> tuple:
        name = item.get("name", "Unknown")
        artist = item.get("artist", "")
        label = f"{name} - {artist}" if artist else name
        return (label, False, "")

    def on_item_selected(self, index: int, item) -> None:
        self.app.music_controller.play_track(
            item.get("name", ""), item.get("artist", "")
        )
        from src.tui.screens.now_playing import NowPlayingScreen
        self.app.push_screen(NowPlayingScreen())
