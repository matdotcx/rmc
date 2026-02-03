"""Background indexer that scans Music.app and populates the database."""

import subprocess
from datetime import datetime
from typing import Optional, Tuple, Callable

from src.index.library_index import LibraryIndex, SCHEMA_VERSION
from src.music.pyobjc_bridge import PyObjCBridge


class LibraryIndexer:
    """Background indexer for Music.app library."""

    def __init__(self, bridge: PyObjCBridge, index: LibraryIndex):
        """Initialize the indexer.

        Args:
            bridge: PyObjC bridge for Music.app access
            index: Library index to populate
        """
        self.bridge = bridge
        self.index = index

        self._current = 0
        self._total = 0
        self._phase = "idle"
        self._cancelled = False
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None

    def get_progress(self) -> Tuple[int, int, str]:
        """Return indexing progress.

        Returns:
            Tuple of (current, total, phase)
        """
        return (self._current, self._total, self._phase)

    def set_progress_callback(self, callback: Callable[[int, int, str], None]) -> None:
        """Set callback for progress updates.

        Args:
            callback: Function called with (current, total, phase)
        """
        self._progress_callback = callback

    def cancel(self) -> None:
        """Cancel the current indexing operation."""
        self._cancelled = True

    def _update_progress(self, current: int, total: int, phase: str) -> None:
        """Update progress and notify callback."""
        self._current = current
        self._total = total
        self._phase = phase

        if self._progress_callback:
            self._progress_callback(current, total, phase)

    def rebuild_full(self) -> bool:
        """Complete library scan and index rebuild.

        Returns:
            True if successful, False if cancelled or failed
        """
        self._cancelled = False
        self._update_progress(0, 0, "Starting...")

        try:
            # Clear existing data
            self._update_progress(0, 0, "Clearing index...")
            self.index.clear()

            if self._cancelled:
                return False

            # Index tracks
            self._update_progress(0, 0, "Scanning tracks...")
            if not self._index_tracks():
                return False

            if self._cancelled:
                return False

            # Extract artists and albums from tracks
            self._update_progress(0, 0, "Extracting artists/albums...")
            self._extract_artists_albums()

            if self._cancelled:
                return False

            # Index playlists
            self._update_progress(0, 0, "Scanning playlists...")
            self._index_playlists()

            # Update metadata
            self.index.set_metadata('last_updated', datetime.now().isoformat())
            self.index.set_metadata('version', SCHEMA_VERSION)

            self._update_progress(self._current, self._total, "Complete")
            return True

        except Exception as e:
            self._update_progress(0, 0, f"Error: {e}")
            return False

    def _get_track_count(self) -> int:
        """Get total track count quickly.

        Returns:
            Number of tracks in library, or 0 on error
        """
        script = '''
        tell application "Music"
            return count of tracks of library playlist 1
        end tell
        '''
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
        except Exception:
            pass
        return 0

    def _index_tracks(self) -> bool:
        """Scan all tracks via AppleScript.

        Returns:
            True if successful
        """
        # First get the count so we can show progress
        track_count = self._get_track_count()
        self._total = track_count
        self._update_progress(0, track_count, f"Scanning {track_count:,} tracks...")

        # Use AppleScript to get all tracks in batches
        # This is more efficient than iterating via PyObjC
        script = '''
        tell application "Music"
            set trackList to {}
            set allTracks to every track of library playlist 1
            set trackCount to count of allTracks
            repeat with i from 1 to trackCount
                set t to item i of allTracks
                try
                    set trackName to name of t
                    set trackArtist to artist of t
                    set trackAlbum to album of t
                    set trackDuration to duration of t
                    set trackPID to persistent ID of t
                    set trackInfo to trackName & "|||" & trackArtist & "|||" & trackAlbum & "|||" & trackDuration & "|||" & trackPID
                    set end of trackList to trackInfo
                end try
            end repeat
            set AppleScript's text item delimiters to "~~~"
            return trackList as text
        end tell
        '''

        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout for large libraries
            )

            if result.returncode != 0:
                return False

            output = result.stdout.strip()
            if not output:
                return True  # Empty library is valid

            tracks = output.split('~~~')
            self._total = len(tracks)

            self.index.begin_transaction()

            for i, track_str in enumerate(tracks):
                if self._cancelled:
                    self.index.end_transaction()
                    return False

                parts = track_str.strip().split('|||')
                if len(parts) >= 5:
                    name = parts[0]
                    artist = parts[1] if parts[1] != 'missing value' else ''
                    album = parts[2] if parts[2] != 'missing value' else ''
                    try:
                        duration = float(parts[3]) if parts[3] != 'missing value' else 0.0
                    except ValueError:
                        duration = 0.0
                    persistent_id = parts[4] if parts[4] != 'missing value' else ''

                    self.index.add_track(
                        name=name,
                        artist=artist,
                        album=album,
                        duration=duration,
                        persistent_id=persistent_id
                    )

                self._current = i + 1
                if i % 100 == 0:
                    self._update_progress(self._current, self._total, "Indexing tracks...")

            self.index.end_transaction()
            self._update_progress(self._total, self._total, "Tracks indexed")
            return True

        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

    def _extract_artists_albums(self) -> None:
        """Derive artists and albums from indexed tracks."""
        conn = self.index._ensure_connection()
        cursor = conn.cursor()

        # Extract unique artists
        cursor.execute("""
            SELECT DISTINCT artist FROM tracks
            WHERE artist IS NOT NULL AND artist != ''
        """)
        artists = [row['artist'] for row in cursor.fetchall()]

        for artist in artists:
            self.index.add_artist(artist)

        # Extract unique album/artist combinations
        cursor.execute("""
            SELECT DISTINCT album, artist FROM tracks
            WHERE album IS NOT NULL AND album != ''
        """)
        albums = [(row['album'], row['artist'] or '') for row in cursor.fetchall()]

        for album_name, artist_name in albums:
            self.index.add_album(album_name, artist_name)

    def _index_playlists(self) -> None:
        """Scan playlists and their tracks."""
        try:
            # Get playlist names from PyObjC bridge
            playlist_names = self.bridge.get_library_playlists()

            for playlist_name in playlist_names:
                if self._cancelled:
                    return

                playlist_id = self.index.add_playlist(playlist_name)

                # Get tracks for this playlist
                tracks = self._get_playlist_track_ids(playlist_name)

                for position, persistent_id in enumerate(tracks):
                    # Look up track by persistent ID
                    conn = self.index._ensure_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id FROM tracks WHERE persistent_id = ?",
                        (persistent_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        self.index.add_playlist_track(playlist_id, row['id'], position)

        except Exception:
            pass  # Playlist indexing is optional

    def _get_playlist_track_ids(self, playlist_name: str) -> list[str]:
        """Get persistent IDs of tracks in a playlist.

        Args:
            playlist_name: Name of the playlist

        Returns:
            List of persistent IDs in playlist order
        """
        safe_name = playlist_name.replace('"', '\\"')
        script = f'''
        tell application "Music"
            set pidList to {{}}
            try
                set targetPlaylist to playlist "{safe_name}"
                repeat with t in tracks of targetPlaylist
                    set end of pidList to persistent ID of t
                end repeat
            end try
            set AppleScript's text item delimiters to ","
            return pidList as text
        end tell
        '''

        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and result.stdout.strip():
                return [pid.strip() for pid in result.stdout.strip().split(',') if pid.strip()]
        except Exception:
            pass

        return []
