"""HTTP bridge for communicating with the rmcd daemon."""

import httpx
from typing import Optional, Dict, Any, List, Literal, Tuple
from urllib.parse import quote


class RMCDConnectionError(Exception):
    """Raised when the daemon is unreachable."""
    pass


class RMCDError(Exception):
    """Raised when the daemon returns an error response."""
    pass


class RMCDBridge:
    """Bridge for controlling Music.app via the rmcd daemon over HTTP."""

    def __init__(self, host: str = "127.0.0.1", port: int = 18895):
        self.base_url = f"http://{host}:{port}/api/v1"
        self._client = httpx.Client(base_url=self.base_url, timeout=60.0)

    def close(self):
        self._client.close()

    def _get(self, path: str, **params) -> dict:
        try:
            r = self._client.get(path, params=params)
            r.raise_for_status()
            return r.json()
        except httpx.ConnectError as e:
            raise RMCDConnectionError(f"Daemon unreachable: {e}")
        except httpx.TimeoutException as e:
            raise RMCDError(f"Request timed out: {e}")
        except httpx.HTTPStatusError as e:
            msg = e.response.json().get("error", str(e)) if e.response.headers.get("content-type", "").startswith("application/json") else str(e)
            raise RMCDError(msg)

    def _post(self, path: str, json: Optional[dict] = None) -> dict:
        try:
            r = self._client.post(path, json=json)
            r.raise_for_status()
            return r.json()
        except httpx.ConnectError as e:
            raise RMCDConnectionError(f"Daemon unreachable: {e}")
        except httpx.TimeoutException as e:
            raise RMCDError(f"Request timed out: {e}")
        except httpx.HTTPStatusError as e:
            msg = e.response.json().get("error", str(e)) if e.response.headers.get("content-type", "").startswith("application/json") else str(e)
            raise RMCDError(msg)

    def _put(self, path: str, json: dict) -> dict:
        try:
            r = self._client.put(path, json=json)
            r.raise_for_status()
            return r.json()
        except httpx.ConnectError as e:
            raise RMCDConnectionError(f"Daemon unreachable: {e}")
        except httpx.TimeoutException as e:
            raise RMCDError(f"Request timed out: {e}")
        except httpx.HTTPStatusError as e:
            msg = e.response.json().get("error", str(e)) if e.response.headers.get("content-type", "").startswith("application/json") else str(e)
            raise RMCDError(msg)

    # MARK: - Health check

    def is_available(self) -> bool:
        """Check if the daemon is running and reachable."""
        try:
            self._get("/system/health")
            return True
        except Exception:
            return False

    # MARK: - Combined status (replaces 5 individual calls)

    def get_status(self) -> dict:
        """Get combined player status in a single call.

        Returns:
            Dict with keys: state, track, volume, shuffle, repeat
        """
        return self._get("/status")

    # MARK: - Playback control

    def play(self) -> None:
        self._post("/playback/play")

    def pause(self) -> None:
        self._post("/playback/pause")

    def playpause(self) -> None:
        self._post("/playback/playpause")

    def next_track(self) -> None:
        self._post("/playback/next")

    def previous_track(self) -> None:
        self._post("/playback/previous")

    def set_player_position(self, position: float) -> None:
        self._post("/playback/seek", json={"position": position})

    def play_track(self, track_name: str, artist: str = "") -> None:
        self._post("/playback/play-track", json={"name": track_name, "artist": artist})

    def play_playlist(self, name: str) -> None:
        self._post("/playback/play-playlist", json={"name": name})

    # MARK: - Player state (individual getters for compatibility)

    def get_player_state(self) -> Literal['playing', 'paused', 'stopped']:
        status = self.get_status()
        return status.get("state", "stopped")

    def get_current_track(self) -> Optional[Dict[str, Any]]:
        status = self.get_status()
        return status.get("track")

    def get_volume(self) -> int:
        status = self.get_status()
        return status.get("volume", 50)

    def get_shuffle(self) -> bool:
        status = self.get_status()
        return status.get("shuffle", False)

    def get_repeat(self) -> Literal['off', 'one', 'all']:
        status = self.get_status()
        return status.get("repeat", "off")

    # MARK: - Settings

    def set_volume(self, level: int) -> None:
        self._put("/settings/volume", json={"level": level})

    def set_shuffle(self, enabled: bool) -> None:
        self._put("/settings/shuffle", json={"enabled": enabled})

    def set_repeat(self, mode: str) -> None:
        self._put("/settings/repeat", json={"mode": mode})

    # MARK: - Library (Phase 3 — requires MusicKit)

    def get_all_artists(self) -> List[str]:
        data = self._get("/library/artists")
        return data.get("artists", [])

    def get_all_albums(self) -> List[Tuple[str, str]]:
        data = self._get("/library/albums")
        return [(a["name"], a["artist"]) for a in data.get("albums", [])]

    def get_library_playlists(self) -> List[str]:
        data = self._get("/library/playlists")
        return data.get("playlists", [])

    def get_playlist_tracks(self, playlist_name: str) -> List[Dict[str, Any]]:
        data = self._get(f"/library/playlists/{quote(playlist_name, safe='')}")
        return data.get("tracks", [])

    def get_tracks_by_artist(self, artist: str) -> List[Dict[str, Any]]:
        data = self._get(f"/library/artists/{quote(artist, safe='')}")
        return data.get("tracks", [])

    def get_tracks_by_album(self, album: str, artist: str = "") -> List[Dict[str, Any]]:
        data = self._get(f"/library/albums/{quote(album, safe='')}", artist=artist)
        return data.get("tracks", [])

    def search_library(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        data = self._get("/library/search", q=query, limit=limit)
        return data.get("tracks", [])

    # MARK: - Library Export

    def export_library(self) -> dict:
        """Fetch full library export for local indexing. Uses extended timeout."""
        try:
            r = self._client.post("/library/index", timeout=300.0)
            r.raise_for_status()
            return r.json()
        except httpx.ConnectError as e:
            raise RMCDConnectionError(f"Daemon unreachable: {e}")
        except httpx.TimeoutException as e:
            raise RMCDError(f"Library export timed out: {e}")
        except httpx.HTTPStatusError as e:
            msg = e.response.json().get("error", str(e)) if e.response.headers.get("content-type", "").startswith("application/json") else str(e)
            raise RMCDError(msg)
