"""Main Textual application for RMC."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.theme import Theme
from textual import work
import random

from src.music.rmcd_bridge import RMCDBridge, RMCDConnectionError, RMCDError
from src.index.library_index import LibraryIndex, SCHEMA_VERSION
from src.config.settings import ConfigManager


MAX_QUEUE = 1000


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

    def play_tracks(self, tracks: list, start: int = 0) -> None:
        """Queue tracks (index rows) and start playing at tracks[start]."""
        # The Songs list and Shuffle Songs span the whole library; queue a
        # window from the chosen song rather than every song in it.
        if len(tracks) > MAX_QUEUE:
            tracks, start = tracks[start:start + MAX_QUEUE], 0
        ids = [t.get("music_id") for t in tracks]
        start_id = ids[start] if 0 <= start < len(ids) else None
        if not start_id:
            self.app.notify("Track has no library ID - try reindexing", severity="error")
            return
        queue = [i for i in ids if i]
        self._call(self._bridge.play_queue, queue, queue.index(start_id))

    def play_track_in_album(self, track: dict) -> None:
        """Play a single track with the rest of its album queued around it."""
        album = self._index.get_tracks_by_album(track.get("album", ""), track.get("album_artist", ""))
        ids = [t.get("music_id") for t in album]
        if track.get("music_id") in ids:
            self.play_tracks(album, ids.index(track["music_id"]))
        else:
            self.play_tracks([track])

    def play_playlist(self, music_id: str) -> None:
        self._call(self._bridge.play_playlist, music_id)

    def shuffle_songs(self) -> None:
        """Play the whole library in random order, like the iPod's Shuffle Songs."""
        songs = self._index.get_all_songs()
        if not songs:
            self.app.notify("Library not indexed yet", severity="warning")
            return
        random.shuffle(songs)
        self.play_tracks(songs, 0)

    # -- Library reads (local SQLite index) --

    def get_playlists(self) -> list:
        return self._index.get_all_playlists()

    def get_playlist_tracks(self, music_id: str) -> list:
        return self._index.get_playlist_tracks(music_id)

    def get_all_artists(self) -> list:
        return self._index.get_all_artists()

    def get_albums_by_artist(self, name: str) -> list:
        return self._index.get_albums_by_artist(name)

    def get_tracks_by_artist(self, name: str) -> list:
        return self._index.get_tracks_by_artist(name)

    def get_all_songs(self) -> list:
        return self._index.get_all_songs()

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

        tracks = data.get("tracks", [])

        # Rebuild inside one transaction so readers on the UI thread keep the
        # old index until the new one is complete, and a failure mid-way
        # leaves the previous index intact.
        self._index.begin_transaction()
        try:
            self._index.clear()
            for t in tracks:
                album_artist = t.get("album_artist") or t.get("artist") or "Unknown Artist"
                in_library = t.get("in_library", True)
                self._index.add_track(
                    name=t.get("name", ""),
                    artist=t.get("artist", ""),
                    album=t.get("album", ""),
                    duration=t.get("duration", 0),
                    music_id=t.get("id") or "",
                    album_artist=album_artist,
                    track_number=t.get("track_number"),
                    disc_number=t.get("disc_number"),
                    in_library=in_library,
                )
                # Playlist-only songs (e.g. from Apple Music playlists) stay
                # playable from their playlists but, as in Music.app, don't
                # create partial albums or artists in the library views.
                if not in_library:
                    continue
                self._index.add_artist(album_artist)
                if t.get("album"):
                    self._index.add_album(t["album"], album_artist)

            self._index.group_untagged_compilations()

            for pl in data.get("playlists", []):
                pl_id = self._index.add_playlist(pl["name"], pl.get("id", ""))
                for pos, t in enumerate(pl.get("tracks", [])):
                    track_id = self._index.add_track(
                        name=t.get("name", ""),
                        artist=t.get("artist", ""),
                        album=t.get("album", ""),
                        duration=t.get("duration", 0),
                        music_id=t.get("id") or "",
                        track_number=t.get("track_number"),
                        disc_number=t.get("disc_number"),
                    )
                    self._index.add_playlist_track(pl_id, track_id, pos)

            self._index.set_metadata("last_updated", datetime.now().isoformat())
            self._index.set_metadata("version", SCHEMA_VERSION)
            self._index.end_transaction()
        except Exception:
            self._index.rollback_transaction()
            raise

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
    #now-playing-display {
        width: 100%;
        height: auto;
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
        height: 1;
        border: none;
        padding: 0 2;
        margin-bottom: 1;
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
        # Latest status polled from the daemon; read by title bars and screens.
        self.player_status: dict = {}

    def compose(self) -> ComposeResult:
        return
        yield  # ComposeResult requires a generator

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        # Let "q" be typed into a list's jump-to prefix instead of quitting.
        if action == "quit" and getattr(self.screen, "_jump", None) is not None:
            return False
        return True

    def on_mount(self) -> None:
        from src.tui.screens.main_menu import MainMenuScreen
        self.push_screen(MainMenuScreen())
        self.start_update_loop()
        self._wake_receiver()
        self._auto_reindex_if_stale()

    @work(exclusive=False, thread=True, exit_on_error=False)
    def _wake_receiver(self) -> None:
        """Power the receiver on and switch it to our input, as on launch."""
        try:
            self.music_controller._bridge.wake_receiver()
        except RMCDConnectionError:
            pass  # the status loop already reports a missing daemon
        except RMCDError as e:
            self.call_from_thread(self.notify, f"Receiver: {e}", severity="warning")

    @work(exclusive=False, thread=True, exit_on_error=False)
    def _auto_reindex_if_stale(self) -> None:
        """Reindex library in background if index is empty or stale."""
        try:
            if self.music_controller.index_is_stale():
                count = self.music_controller.reindex()
                if count >= 0:
                    self.call_from_thread(
                        self.notify, f"Library indexed: {count:,} tracks"
                    )
        except Exception as e:
            # A failed background reindex should not take the whole app down.
            self.call_from_thread(
                self.notify, f"Library reindex failed: {e}", severity="error"
            )

    @work(exclusive=True, thread=True)
    def start_update_loop(self) -> None:
        import time

        while not self._should_exit:
            try:
                status = self.music_controller.get_status()
                self.call_from_thread(self.apply_player_status, status)

                time.sleep(self.config_manager.config.ui.update_interval)
            except Exception:
                time.sleep(1)

    def apply_player_status(self, status: dict) -> None:
        """Store the latest player status and let the current screen redraw."""
        self.player_status = status or {}
        handler = getattr(self.screen, "on_player_status", None)
        if handler:
            handler()

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
