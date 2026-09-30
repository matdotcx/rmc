"""SQLite index manager with FTS5 full-text search for Music.app library."""

import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any


SCHEMA_VERSION = "3"

# Tables and triggers owned by this schema, dropped when migrating from an
# older schema version (the index is a cache, so rebuilding is always safe).
_SCHEMA_OBJECTS = [
    ("TRIGGER", "tracks_ai"), ("TRIGGER", "tracks_ad"), ("TRIGGER", "tracks_au"),
    ("TABLE", "tracks_fts"), ("TABLE", "playlist_tracks"), ("TABLE", "playlists"),
    ("TABLE", "albums"), ("TABLE", "artists"), ("TABLE", "tracks"), ("TABLE", "metadata"),
]

_TRACK_COLUMNS = (
    "id, name, artist, album_artist, album, track_number, disc_number, duration, music_id"
)


class LibraryIndex:
    """SQLite-based index for fast library search and browsing."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the library index.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.config/rmc/library.db
        """
        if db_path is None:
            config_dir = Path.home() / ".config" / "rmc"
            config_dir.mkdir(parents=True, exist_ok=True)
            db_path = config_dir / "library.db"

        self.db_path = db_path
        # One connection per thread. A sqlite3 connection must never be used
        # from two threads at once (the TUI reads on the main thread while a
        # worker thread reindexes), so each thread gets its own connection and
        # WAL mode lets readers proceed while a writer is mid-transaction.
        self._local = threading.local()
        self._connections: List[sqlite3.Connection] = []
        self._connections_lock = threading.Lock()
        self._ensure_connection()
        self.create_schema()

    def _ensure_connection(self) -> sqlite3.Connection:
        """Return this thread's database connection, opening it if needed."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            self._local.conn = conn
            self._local.in_bulk = False
            with self._connections_lock:
                self._connections.append(conn)
        return conn

    @property
    def _conn(self) -> Optional[sqlite3.Connection]:
        return getattr(self._local, "conn", None)

    def _commit(self, conn: sqlite3.Connection) -> None:
        """Commit unless this thread is inside a bulk transaction."""
        if not getattr(self._local, "in_bulk", False):
            conn.commit()

    def close(self) -> None:
        """Close every database connection opened by this index."""
        with self._connections_lock:
            conns, self._connections = self._connections, []
        for conn in conns:
            try:
                conn.close()
            except sqlite3.Error:
                pass
        self._local.conn = None
        self._local.in_bulk = False

    def _needs_migration(self, cursor: sqlite3.Cursor) -> bool:
        """True if an older schema is on disk (tracks lacks the v3 columns)."""
        cursor.execute("PRAGMA table_info(tracks)")
        columns = {row["name"] for row in cursor.fetchall()}
        return bool(columns) and "in_library" not in columns

    def create_schema(self) -> None:
        """Create database tables and FTS5 virtual table."""
        conn = self._ensure_connection()
        cursor = conn.cursor()

        if self._needs_migration(cursor):
            for kind, name in _SCHEMA_OBJECTS:
                cursor.execute(f"DROP {kind} IF EXISTS {name}")

        # Tracks table. music_id is the MusicKit library ID used for playback.
        # in_library is 0 for songs that only appear in playlists (e.g. Apple
        # Music playlists); like Music.app, album/artist browsing skips them.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                artist TEXT,
                album_artist TEXT COLLATE NOCASE,
                album TEXT COLLATE NOCASE,
                track_number INTEGER,
                disc_number INTEGER,
                duration REAL,
                music_id TEXT UNIQUE,
                in_library INTEGER NOT NULL DEFAULT 1
            )
        """)

        # FTS5 virtual table for full-text search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS tracks_fts USING fts5(
                name, artist, album,
                content='tracks',
                content_rowid='id'
            )
        """)

        # Triggers to keep FTS in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS tracks_ai AFTER INSERT ON tracks BEGIN
                INSERT INTO tracks_fts(rowid, name, artist, album)
                VALUES (new.id, new.name, new.artist, new.album);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS tracks_ad AFTER DELETE ON tracks BEGIN
                INSERT INTO tracks_fts(tracks_fts, rowid, name, artist, album)
                VALUES ('delete', old.id, old.name, old.artist, old.album);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS tracks_au AFTER UPDATE ON tracks BEGIN
                INSERT INTO tracks_fts(tracks_fts, rowid, name, artist, album)
                VALUES ('delete', old.id, old.name, old.artist, old.album);
                INSERT INTO tracks_fts(rowid, name, artist, album)
                VALUES (new.id, new.name, new.artist, new.album);
            END
        """)

        # Artists table (album artists). NOCASE merges spellings such as
        # "Florence + The Machine" / "Florence + the Machine"; first one wins.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS artists (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL COLLATE NOCASE
            )
        """)

        # Albums table, keyed by album artist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS albums (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL COLLATE NOCASE,
                artist TEXT COLLATE NOCASE,
                UNIQUE(name, artist)
            )
        """)

        # Playlists table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                music_id TEXT UNIQUE
            )
        """)

        # Playlist tracks junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                playlist_id INTEGER,
                track_id INTEGER,
                position INTEGER,
                FOREIGN KEY (playlist_id) REFERENCES playlists(id),
                FOREIGN KEY (track_id) REFERENCES tracks(id),
                PRIMARY KEY (playlist_id, position)
            )
        """)

        # Metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_album_artist ON tracks(album_artist)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_album ON tracks(album, album_artist)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_albums_artist ON albums(artist)")

        self._commit(conn)

    def get_metadata(self) -> Dict[str, Any]:
        """Return index metadata.

        Returns:
            Dictionary with last_updated, track_count, version
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        metadata = {
            'last_updated': None,
            'track_count': 0,
            'version': None
        }

        cursor.execute("SELECT key, value FROM metadata")
        for row in cursor.fetchall():
            metadata[row['key']] = row['value']

        # Get actual track count
        cursor.execute("SELECT COUNT(*) as count FROM tracks")
        row = cursor.fetchone()
        metadata['track_count'] = row['count'] if row else 0

        return metadata

    def set_metadata(self, key: str, value: str) -> None:
        """Set a metadata value.

        Args:
            key: Metadata key
            value: Metadata value
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            (key, value)
        )
        self._commit(conn)

    def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """FTS5 search across library songs' name, artist, album.

        Args:
            query: Search query string
            limit: Maximum results to return

        Returns:
            List of track dictionaries
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        # Escape special FTS5 characters and prepare query
        safe_query = query.replace('"', '""')
        # Use prefix matching for partial word search
        fts_query = f'"{safe_query}"*'

        cursor.execute("""
            SELECT t.id, t.name, t.artist, t.album_artist, t.album, t.track_number,
                   t.disc_number, t.duration, t.music_id
            FROM tracks t
            JOIN tracks_fts fts ON t.id = fts.rowid
            WHERE tracks_fts MATCH ? AND t.in_library
            ORDER BY rank
            LIMIT ?
        """, (fts_query, limit))

        return [dict(row) for row in cursor.fetchall()]

    def get_all_artists(self) -> List[str]:
        """Return sorted unique album artists.

        Returns:
            List of album artist names sorted alphabetically
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM artists ORDER BY name COLLATE NOCASE")
        return [row['name'] for row in cursor.fetchall()]

    def get_all_albums(self) -> List[Tuple[str, str]]:
        """Return sorted (album, artist) tuples.

        Returns:
            List of (album_name, artist_name) tuples sorted by album name
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name, artist FROM albums
            ORDER BY name COLLATE NOCASE
        """)
        return [(row['name'], row['artist'] or '') for row in cursor.fetchall()]

    def get_albums_by_artist(self, artist: str) -> List[Tuple[str, str]]:
        """Return (album, album_artist) tuples for one album artist.

        Args:
            artist: Album artist name (case-insensitive)

        Returns:
            List of (album_name, artist_name) tuples sorted by album name
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name, artist FROM albums
            WHERE artist = ?
            ORDER BY name COLLATE NOCASE
        """, (artist,))
        return [(row['name'], row['artist'] or '') for row in cursor.fetchall()]

    def get_all_playlists(self) -> List[Dict[str, Any]]:
        """Return playlists.

        Returns:
            List of {"name", "music_id"} dictionaries sorted by name
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name, music_id FROM playlists ORDER BY name COLLATE NOCASE")
        return [dict(row) for row in cursor.fetchall()]

    def get_playlist_tracks(self, music_id: str) -> List[Dict[str, Any]]:
        """Return tracks in playlist order.

        Args:
            music_id: Playlist MusicKit ID

        Returns:
            List of track dictionaries in playlist order
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT t.id, t.name, t.artist, t.album_artist, t.album, t.track_number,
                   t.disc_number, t.duration, t.music_id
            FROM tracks t
            JOIN playlist_tracks pt ON t.id = pt.track_id
            JOIN playlists p ON pt.playlist_id = p.id
            WHERE p.music_id = ?
            ORDER BY pt.position
        """, (music_id,))

        return [dict(row) for row in cursor.fetchall()]

    def get_tracks_by_artist(self, artist: str) -> List[Dict[str, Any]]:
        """Return tracks by album artist, in album then track order.

        Args:
            artist: Album artist name (case-insensitive)

        Returns:
            List of track dictionaries
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT {_TRACK_COLUMNS}
            FROM tracks
            WHERE album_artist = ? AND in_library
            ORDER BY album, disc_number, track_number, name COLLATE NOCASE
        """, (artist,))

        return [dict(row) for row in cursor.fetchall()]

    def get_all_songs(self) -> List[Dict[str, Any]]:
        """Return every library song (not playlist-only songs), unsorted.

        Returns:
            List of track dictionaries
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute(f"SELECT {_TRACK_COLUMNS} FROM tracks WHERE in_library")
        return [dict(row) for row in cursor.fetchall()]

    def get_tracks_by_album(self, album: str, artist: str = "") -> List[Dict[str, Any]]:
        """Return tracks in album, in disc and track order.

        Args:
            album: Album name
            artist: Album artist (optional; case-insensitive)

        Returns:
            List of track dictionaries
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        where = "album = ? AND album_artist = ?" if artist else "album = ?"
        where += " AND in_library"
        params = (album, artist) if artist else (album,)
        cursor.execute(f"""
            SELECT {_TRACK_COLUMNS}
            FROM tracks
            WHERE {where}
            ORDER BY disc_number, track_number, name COLLATE NOCASE
        """, params)

        return [dict(row) for row in cursor.fetchall()]

    def is_stale(self, max_age_hours: int = 48) -> bool:
        """Check if index needs refresh.

        Args:
            max_age_hours: Maximum age in hours before considered stale

        Returns:
            True if index is stale or doesn't exist
        """
        metadata = self.get_metadata()
        last_updated = metadata.get('last_updated')

        if not last_updated or metadata.get('version') != SCHEMA_VERSION:
            return True

        try:
            updated_time = datetime.fromisoformat(last_updated)
            age = datetime.now() - updated_time
            return age > timedelta(hours=max_age_hours)
        except (ValueError, TypeError):
            return True

    def exists(self) -> bool:
        """Check if index has any data.

        Returns:
            True if index has tracks
        """
        metadata = self.get_metadata()
        return metadata.get('track_count', 0) > 0

    def get_age_description(self) -> str:
        """Get human-readable age description.

        Returns:
            String like "2h ago", "3 days old", etc.
        """
        metadata = self.get_metadata()
        last_updated = metadata.get('last_updated')

        if not last_updated:
            return "never indexed"

        try:
            updated_time = datetime.fromisoformat(last_updated)
            age = datetime.now() - updated_time

            if age.total_seconds() < 3600:
                minutes = int(age.total_seconds() / 60)
                return f"{minutes}m ago"
            elif age.days == 0:
                hours = int(age.total_seconds() / 3600)
                return f"{hours}h ago"
            elif age.days == 1:
                return "1 day ago"
            else:
                return f"{age.days} days ago"
        except (ValueError, TypeError):
            return "unknown"

    def clear(self) -> None:
        """Drop all data for rebuild."""
        conn = self._ensure_connection()
        cursor = conn.cursor()

        # Clear all tables
        cursor.execute("DELETE FROM playlist_tracks")
        cursor.execute("DELETE FROM playlists")
        cursor.execute("DELETE FROM albums")
        cursor.execute("DELETE FROM artists")
        cursor.execute("DELETE FROM tracks")
        cursor.execute("DELETE FROM metadata")

        # Rebuild FTS index
        cursor.execute("INSERT INTO tracks_fts(tracks_fts) VALUES('rebuild')")

        self._commit(conn)

    def add_track(
        self,
        name: str,
        artist: str = "",
        album: str = "",
        duration: float = 0.0,
        music_id: str = "",
        album_artist: str = "",
        track_number: Optional[int] = None,
        disc_number: Optional[int] = None,
        in_library: bool = True,
    ) -> int:
        """Add a track to the index, or return the existing row for music_id.

        Args:
            name: Track name
            artist: Track artist
            album: Album name
            duration: Track duration in seconds
            music_id: MusicKit library ID
            album_artist: Album artist (defaults to artist)
            track_number: Track number on disc
            disc_number: Disc number
            in_library: False for playlist-only songs, hidden from browsing

        Returns:
            Track ID
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        # Playlist exports repeat library tracks; reuse the existing row so
        # each song appears once and playlist rows point at the same track.
        if music_id:
            cursor.execute("SELECT id FROM tracks WHERE music_id = ?", (music_id,))
            row = cursor.fetchone()
            if row:
                return row['id']

        cursor.execute("""
            INSERT INTO tracks (name, artist, album_artist, album, track_number,
                                disc_number, duration, music_id, in_library)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, artist or '', album_artist or artist or '', album or '',
            track_number, disc_number, duration, music_id or None, int(in_library),
        ))

        track_id = cursor.lastrowid
        self._commit(conn)
        return track_id

    def add_artist(self, name: str) -> int:
        """Add an artist to the index.

        Args:
            name: Artist name

        Returns:
            Artist ID
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT OR IGNORE INTO artists (name) VALUES (?)",
            (name,)
        )
        self._commit(conn)

        cursor.execute("SELECT id FROM artists WHERE name = ?", (name,))
        row = cursor.fetchone()
        return row['id'] if row else 0

    def add_album(self, name: str, artist: str = "") -> int:
        """Add an album to the index.

        Args:
            name: Album name
            artist: Artist name

        Returns:
            Album ID
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT OR IGNORE INTO albums (name, artist) VALUES (?, ?)",
            (name, artist or '')
        )
        self._commit(conn)

        cursor.execute(
            "SELECT id FROM albums WHERE name = ? AND artist = ?",
            (name, artist or '')
        )
        row = cursor.fetchone()
        return row['id'] if row else 0

    def group_untagged_compilations(self, min_artists: int = 3) -> int:
        """File untagged compilations under "Various Artists".

        Albums with no album-artist tag come back with each track's own
        artist, scattering a compilation across dozens of artists. Treat an
        album title as a compilation when it spans several artists with about
        one track each; different artists' albums that merely share a title
        ("Greatest Hits") have many tracks per artist and are left alone.

        Returns:
            Number of tracks regrouped
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT album FROM tracks
            WHERE album != '' AND in_library
            GROUP BY album
            HAVING COUNT(DISTINCT album_artist) >= ?
               AND COUNT(*) < 2 * COUNT(DISTINCT album_artist)
        """, (min_artists,))
        albums = [row['album'] for row in cursor.fetchall()]

        regrouped = 0
        for album in albums:
            cursor.execute(
                "UPDATE tracks SET album_artist = 'Various Artists' WHERE album = ? AND in_library",
                (album,)
            )
            regrouped += cursor.rowcount
            cursor.execute("DELETE FROM albums WHERE name = ?", (album,))
            cursor.execute(
                "INSERT OR IGNORE INTO albums (name, artist) VALUES (?, 'Various Artists')", (album,)
            )
        if albums:
            cursor.execute("INSERT OR IGNORE INTO artists (name) VALUES ('Various Artists')")
            # Drop artists left with no albums or tracks after regrouping.
            cursor.execute("""
                DELETE FROM artists
                WHERE name NOT IN (SELECT DISTINCT album_artist FROM tracks WHERE in_library)
            """)

        self._commit(conn)
        return regrouped

    def add_playlist(self, name: str, music_id: str = "") -> int:
        """Add a playlist to the index.

        Args:
            name: Playlist name
            music_id: Playlist MusicKit ID

        Returns:
            Playlist ID
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO playlists (name, music_id) VALUES (?, ?)",
            (name, music_id or None)
        )
        playlist_id = cursor.lastrowid
        self._commit(conn)
        return playlist_id

    def add_playlist_track(self, playlist_id: int, track_id: int, position: int) -> None:
        """Add a track to a playlist.

        Args:
            playlist_id: Playlist ID
            track_id: Track ID
            position: Position in playlist
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO playlist_tracks (playlist_id, track_id, position)
            VALUES (?, ?, ?)
        """, (playlist_id, track_id, position))

        self._commit(conn)

    def commit(self) -> None:
        """Commit any pending changes."""
        conn = self._ensure_connection()
        self._commit(conn)

    def begin_transaction(self) -> None:
        """Begin a bulk transaction on this thread.

        Until end_transaction() is called, the per-operation commits in
        add_track() and friends are suppressed, so the whole rebuild lands
        atomically and readers on other threads keep seeing the old data.
        """
        conn = self._ensure_connection()
        if not conn.in_transaction:
            conn.execute("BEGIN")
        self._local.in_bulk = True

    def end_transaction(self) -> None:
        """Commit the bulk transaction started by begin_transaction()."""
        conn = self._ensure_connection()
        self._local.in_bulk = False
        conn.commit()

    def rollback_transaction(self) -> None:
        """Abandon the bulk transaction, restoring the previous index contents."""
        conn = self._ensure_connection()
        self._local.in_bulk = False
        conn.rollback()
