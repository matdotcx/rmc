"""SQLite index manager with FTS5 full-text search for Music.app library."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any


SCHEMA_VERSION = "1"


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
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_connection()
        self.create_schema()

    def _ensure_connection(self) -> sqlite3.Connection:
        """Ensure database connection is open."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def create_schema(self) -> None:
        """Create database tables and FTS5 virtual table."""
        conn = self._ensure_connection()
        cursor = conn.cursor()

        # Tracks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                artist TEXT,
                album TEXT,
                duration REAL,
                persistent_id TEXT UNIQUE
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

        # Artists table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS artists (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        """)

        # Albums table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS albums (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                artist TEXT,
                UNIQUE(name, artist)
            )
        """)

        # Playlists table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
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
                PRIMARY KEY (playlist_id, track_id)
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_album ON tracks(album)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_albums_artist ON albums(artist)")

        conn.commit()

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
        conn.commit()

    def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """FTS5 search across name, artist, album.

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
            SELECT t.id, t.name, t.artist, t.album, t.duration, t.persistent_id
            FROM tracks t
            JOIN tracks_fts fts ON t.id = fts.rowid
            WHERE tracks_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (fts_query, limit))

        return [dict(row) for row in cursor.fetchall()]

    def get_all_artists(self) -> List[str]:
        """Return sorted unique artists.

        Returns:
            List of artist names sorted alphabetically
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

    def get_all_playlists(self) -> List[str]:
        """Return playlist names.

        Returns:
            List of playlist names
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM playlists ORDER BY name COLLATE NOCASE")
        return [row['name'] for row in cursor.fetchall()]

    def get_playlist_tracks(self, name: str) -> List[Dict[str, Any]]:
        """Return tracks in playlist order.

        Args:
            name: Playlist name

        Returns:
            List of track dictionaries in playlist order
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT t.id, t.name, t.artist, t.album, t.duration, t.persistent_id
            FROM tracks t
            JOIN playlist_tracks pt ON t.id = pt.track_id
            JOIN playlists p ON pt.playlist_id = p.id
            WHERE p.name = ?
            ORDER BY pt.position
        """, (name,))

        return [dict(row) for row in cursor.fetchall()]

    def get_tracks_by_artist(self, artist: str) -> List[Dict[str, Any]]:
        """Return tracks by artist.

        Args:
            artist: Artist name

        Returns:
            List of track dictionaries
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, artist, album, duration, persistent_id
            FROM tracks
            WHERE artist = ?
            ORDER BY album COLLATE NOCASE, name COLLATE NOCASE
        """, (artist,))

        return [dict(row) for row in cursor.fetchall()]

    def get_tracks_by_album(self, album: str, artist: str = "") -> List[Dict[str, Any]]:
        """Return tracks in album.

        Args:
            album: Album name
            artist: Artist name (optional for better matching)

        Returns:
            List of track dictionaries
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        if artist:
            cursor.execute("""
                SELECT id, name, artist, album, duration, persistent_id
                FROM tracks
                WHERE album = ? AND artist = ?
                ORDER BY name COLLATE NOCASE
            """, (album, artist))
        else:
            cursor.execute("""
                SELECT id, name, artist, album, duration, persistent_id
                FROM tracks
                WHERE album = ?
                ORDER BY name COLLATE NOCASE
            """, (album,))

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

        if not last_updated:
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

        conn.commit()

    def add_track(
        self,
        name: str,
        artist: str = "",
        album: str = "",
        duration: float = 0.0,
        persistent_id: str = ""
    ) -> int:
        """Add a track to the index.

        Args:
            name: Track name
            artist: Artist name
            album: Album name
            duration: Track duration in seconds
            persistent_id: Music.app persistent ID

        Returns:
            Track ID
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        # Use None for empty persistent_id so UNIQUE constraint allows multiple NULLs
        pid = persistent_id if persistent_id else None
        if pid:
            cursor.execute("""
                INSERT OR REPLACE INTO tracks (name, artist, album, duration, persistent_id)
                VALUES (?, ?, ?, ?, ?)
            """, (name, artist or '', album or '', duration, pid))
        else:
            cursor.execute("""
                INSERT INTO tracks (name, artist, album, duration, persistent_id)
                VALUES (?, ?, ?, ?, NULL)
            """, (name, artist or '', album or '', duration))

        track_id = cursor.lastrowid
        conn.commit()
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
        conn.commit()

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
        conn.commit()

        cursor.execute(
            "SELECT id FROM albums WHERE name = ? AND artist = ?",
            (name, artist or '')
        )
        row = cursor.fetchone()
        return row['id'] if row else 0

    def add_playlist(self, name: str) -> int:
        """Add a playlist to the index.

        Args:
            name: Playlist name

        Returns:
            Playlist ID
        """
        conn = self._ensure_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT OR IGNORE INTO playlists (name) VALUES (?)",
            (name,)
        )
        conn.commit()

        cursor.execute("SELECT id FROM playlists WHERE name = ?", (name,))
        row = cursor.fetchone()
        return row['id'] if row else 0

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

        conn.commit()

    def commit(self) -> None:
        """Commit any pending changes."""
        if self._conn:
            self._conn.commit()

    def begin_transaction(self) -> None:
        """Begin a transaction for bulk operations."""
        conn = self._ensure_connection()
        conn.execute("BEGIN TRANSACTION")

    def end_transaction(self) -> None:
        """End a transaction."""
        if self._conn:
            self._conn.commit()
