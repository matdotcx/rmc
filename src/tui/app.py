"""Main Textual application for RMC."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.theme import Theme
from textual import work

from src.music.rmcd_bridge import RMCDBridge, RMCDConnectionError, RMCDError
from src.index.library_index import LibraryIndex
from src.tui.screens.now_playing import NowPlayingScreen
from src.config.settings import ConfigManager


class MusicController:
    """Controller using local SQLite index for reads, daemon for playback."""

    def __init__(self, app: 'RMCApp', host: str, port: int):
        self.app = app
        self._bridge = RMCDBridge(host=host, port=port)
        self._index = LibraryIndex()

    def _call(self, method, *args, **kwargs):
        try:
            return method(*args, **kwargs)
        except RMCDConnectionError:
            self.app.notify("Daemon disconnected", severity="warning")
        except RMCDError as e:
            self.app.notify(f"Error: {e}", severity="error")
        return None

    # -- Playback (daemon) --

    def playpause(self):
        self._call(self._bridge.playpause)

    def next_track(self):
        self._call(self._bridge.next_track)

    def previous_track(self):
        self._call(self._bridge.previous_track)

    def volume_up(self, step: int = 5):
        status = self.get_status()
        if status:
            new_volume = min(100, status.get('volume', 50) + step)
            self._call(self._bridge.set_volume, new_volume)

    def volume_down(self, step: int = 5):
        status = self.get_status()
        if status:
            new_volume = max(0, status.get('volume', 50) - step)
            self._call(self._bridge.set_volume, new_volume)

    def toggle_shuffle(self):
        status = self.get_status()
        if status:
            self._call(self._bridge.set_shuffle, not status.get('shuffle', False))

    def cycle_repeat(self):
        status = self.get_status()
        if status:
            modes = ['off', 'all', 'one']
            current = status.get('repeat', 'off')
            current_index = modes.index(current) if current in modes else 0
            next_mode = modes[(current_index + 1) % len(modes)]
            self._call(self._bridge.set_repeat, next_mode)

    def get_status(self) -> dict:
        result = self._call(self._bridge.get_status)
        return result if result is not None else {}

    def play_track(self, name: str, artist: str = "") -> None:
        self._call(self._bridge.play_track, name, artist)

    def play_playlist(self, name: str) -> None:
        self._call(self._bridge.play_playlist, name)

    # -- Library reads (local SQLite index) --

    def get_playlists(self) -> list:
        return self._index.get_all_playlists()

    def get_playlist_tracks(self, name: str) -> list:
        return self._index.get_playlist_tracks(name)

    def get_all_artists(self) -> list:
        return self._index.get_all_artists()

    def get_tracks_by_artist(self, name: str) -> list:
        return self._index.get_tracks_by_artist(name)

    def get_all_albums(self) -> list:
        return self._index.get_all_albums()

    def get_tracks_by_album(self, name: str, artist: str = "") -> list:
        return self._index.get_tracks_by_album(name, artist)

    def search_library(self, query: str) -> list:
        return self._index.search(query)

    # -- Indexing --

    def reindex(self) -> int:
        """Fetch full library from daemon and rebuild local index.

        Returns:
            Number of tracks indexed, or -1 on failure.
        """
        data = self._call(self._bridge.export_library)
        if data is None:
            return -1

        from datetime import datetime

        self._index.clear()
        self._index.begin_transaction()

        tracks = data.get("tracks", [])
        for t in tracks:
            self._index.add_track(
                name=t.get("name", ""),
                artist=t.get("artist", ""),
                album=t.get("album", ""),
                duration=t.get("duration", 0),
            )
            if t.get("artist"):
                self._index.add_artist(t["artist"])
            if t.get("album"):
                self._index.add_album(t["album"], t.get("artist", ""))

        for pl in data.get("playlists", []):
            pl_id = self._index.add_playlist(pl["name"])
            for pos, t in enumerate(pl.get("tracks", [])):
                track_id = self._index.add_track(
                    name=t.get("name", ""),
                    artist=t.get("artist", ""),
                    album=t.get("album", ""),
                    duration=t.get("duration", 0),
                )
                self._index.add_playlist_track(pl_id, track_id, pos)

        self._index.end_transaction()
        self._index.set_metadata("last_updated", datetime.now().isoformat())
        self._index.set_metadata("version", "1")

        return len(tracks)

    def index_status(self) -> tuple:
        """Return (exists: bool, age_description: str, track_count: int)."""
        exists = self._index.exists()
        age = self._index.get_age_description()
        meta = self._index.get_metadata()
        count = meta.get("track_count", 0)
        return (exists, age, count)

    def index_is_stale(self) -> bool:
        """Check if the index needs refreshing."""
        return self._index.is_stale()


class RMCApp(App):
    """Apple Music Remote Control TUI Application."""

    CSS = """
    #main-menu-header {
        width: 100%;
        height: 1;
        text-style: bold;
    }

    #main-menu-list {
        width: 100%;
        height: auto;
        padding: 0;
    }

    #main-menu-status {
        width: 100%;
        height: 1;
        margin-top: 1;
    }

    #now-playing-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }

    .now-playing-display {
        width: 100%;
        height: auto;
    }

    #list-header {
        width: 100%;
        height: 1;
        text-style: bold;
    }

    #list-container {
        width: 100%;
        height: 1fr;
    }

    #list-status {
        width: 100%;
        height: 1;
        dock: bottom;
    }

    #search-input {
        width: 100%;
        height: 3;
        margin: 0 1;
    }

    #settings-list {
        width: 100%;
        height: auto;
        padding: 0;
    }
    """

    theme = "textual-ansi"

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
    ]

    TITLE = "Apple Music Remote Control"
    SUB_TITLE = "Control your music from anywhere"

    def __init__(self):
        super().__init__(ansi_color=True)
        self.register_theme(
            Theme(
                name="textual-ansi",
                primary="ansi_blue",
                secondary="ansi_cyan",
                warning="ansi_yellow",
                error="ansi_red",
                success="ansi_green",
                accent="ansi_bright_blue",
                foreground="ansi_default",
                background="ansi_default",
                surface="ansi_default",
                panel="ansi_default",
                boost="ansi_default",
                dark=True,
                variables={
                    "block-cursor-text-style": "b",
                    "block-cursor-blurred-text-style": "i",
                    "input-selection-background": "ansi_blue",
                    "input-cursor-text-style": "reverse",
                    "scrollbar": "ansi_blue",
                    "border-blurred": "ansi_blue",
                    "border": "ansi_bright_blue",
                },
            )
        )
        self.theme = "textual-ansi"
        self.config_manager = ConfigManager()
        daemon_cfg = self.config_manager.config.daemon
        self.music_controller = MusicController(self, host=daemon_cfg.host, port=daemon_cfg.port)
        self._should_exit = False

    def compose(self) -> ComposeResult:
        return
        yield  # ComposeResult requires a generator

    def on_mount(self) -> None:
        from src.tui.screens.main_menu import MainMenuScreen
        self.push_screen(MainMenuScreen())
        self.start_update_loop()
        self._auto_reindex_if_stale()

    @work(exclusive=False, thread=True)
    def _auto_reindex_if_stale(self) -> None:
        """Reindex library in background if index is empty or stale."""
        if self.music_controller.index_is_stale():
            count = self.music_controller.reindex()
            if count >= 0:
                self.call_from_thread(
                    self.notify, f"Library indexed: {count:,} tracks"
                )

    @work(exclusive=True, thread=True)
    def start_update_loop(self) -> None:
        import time

        while not self._should_exit:
            try:
                status = self.music_controller.get_status()

                self.call_from_thread(
                    self._update_now_playing_screen,
                    status.get('track'),
                    status.get('state', 'stopped'),
                    status.get('volume', 50),
                    status.get('shuffle', False),
                    status.get('repeat', 'off'),
                )

                time.sleep(self.config_manager.config.ui.update_interval)
            except Exception:
                time.sleep(1)

    def _update_now_playing_screen(self, track_info, player_state, volume, shuffle, repeat_mode):
        if isinstance(self.screen, NowPlayingScreen):
            screen = self.screen
            screen.update_track_info(track_info)
            screen.player_state = player_state
            screen.volume = volume
            screen.shuffle = shuffle
            screen.repeat_mode = repeat_mode

    def action_quit(self) -> None:
        import os
        import threading

        self._should_exit = True
        self.workers.cancel_all()

        def force_exit():
            import time
            time.sleep(0.5)
            os._exit(0)

        threading.Thread(target=force_exit, daemon=True).start()
        self.exit(return_code=0)


def run():
    app = RMCApp()
    app.run()


if __name__ == "__main__":
    run()
