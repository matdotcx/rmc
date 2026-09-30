"""Songs screen - every song in the library."""

from src.tui.screens.list_screen import SongListScreen, sort_key


class SongsScreen(SongListScreen):
    """All library songs, alphabetically."""

    screen_title = "Songs"

    def load_items(self) -> list:
        songs = self.app.music_controller.get_all_songs() or []
        return sorted(songs, key=lambda song: sort_key(song.get("name", "")))
