"""PyObjC bridge for controlling Music.app on macOS."""

import subprocess
from typing import Optional, Dict, Any, Literal
from ScriptingBridge import SBApplication
from Foundation import NSAppleScript


class MusicAppError(Exception):
    """Exception raised when Music.app operations fail."""
    pass


class PyObjCBridge:
    """Bridge for controlling Music.app via PyObjC."""

    def __init__(self):
        """Initialize the PyObjC bridge."""
        try:
            self.music = SBApplication.applicationWithBundleIdentifier_("com.apple.Music")
        except Exception as e:
            raise MusicAppError(f"Failed to connect to Music.app: {e}")

    def _run_applescript(self, script: str) -> tuple[bool, str, str]:
        """Run AppleScript using NSAppleScript (doesn't spawn subprocess).

        Args:
            script: AppleScript code to execute

        Returns:
            Tuple of (success, result_string, error_message)
        """
        try:
            apple_script = NSAppleScript.alloc().initWithSource_(script)
            result, error = apple_script.executeAndReturnError_(None)
            if error:
                return False, "", str(error.get('NSAppleScriptErrorMessage', 'Unknown error'))
            result_str = str(result.stringValue()) if result else ""
            return True, result_str, ""
        except Exception as e:
            return False, "", str(e)

    def play(self) -> None:
        """Start playback."""
        try:
            self.music.play()
        except Exception as e:
            raise MusicAppError(f"Failed to play: {e}")

    def pause(self) -> None:
        """Pause playback."""
        try:
            self.music.pause()
        except Exception as e:
            raise MusicAppError(f"Failed to pause: {e}")

    def playpause(self) -> None:
        """Toggle play/pause."""
        try:
            self.music.playpause()
        except Exception as e:
            raise MusicAppError(f"Failed to playpause: {e}")

    def next_track(self) -> None:
        """Skip to next track."""
        try:
            self.music.nextTrack()
        except Exception as e:
            raise MusicAppError(f"Failed to skip to next track: {e}")

    def previous_track(self) -> None:
        """Go to previous track."""
        try:
            self.music.previousTrack()
        except Exception as e:
            raise MusicAppError(f"Failed to go to previous track: {e}")

    def get_player_state(self) -> Literal['playing', 'paused', 'stopped']:
        """Get current player state.

        Returns:
            Player state: 'playing', 'paused', or 'stopped'
        """
        try:
            state = self.music.playerState()
            # FourCC codes: kPSP = playing, kPSp = paused, kPSS = stopped
            state_map = {
                1800426320: 'playing',  # 'kPSP'
                1800426112: 'paused',   # 'kPSp'
                1800426323: 'stopped'   # 'kPSS'
            }
            return state_map.get(state, 'stopped')
        except Exception:
            return 'stopped'

    def get_current_track(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently playing track.

        Returns:
            Dictionary with track info or None if no track is playing
        """
        try:
            if self.music.playerState() == 0:  # stopped
                return None

            track = self.music.currentTrack()
            if not track:
                return None

            return {
                'name': str(track.name() or 'Unknown'),
                'artist': str(track.artist() or 'Unknown Artist'),
                'album': str(track.album() or 'Unknown Album'),
                'duration': float(track.duration() or 0),
                'position': float(self.music.playerPosition() or 0),
                'album_artist': str(track.albumArtist() or track.artist() or 'Unknown')
            }
        except Exception:
            return None

    def get_volume(self) -> int:
        """Get current volume level.

        Returns:
            Volume level (0-100)
        """
        try:
            return int(self.music.soundVolume())
        except Exception:
            return 50

    def set_volume(self, level: int) -> None:
        """Set volume level.

        Args:
            level: Volume level (0-100)
        """
        try:
            level = max(0, min(100, level))
            self.music.setSoundVolume_(level)
        except Exception as e:
            raise MusicAppError(f"Failed to set volume: {e}")

    def get_shuffle(self) -> bool:
        """Get shuffle mode status.

        Returns:
            True if shuffle is enabled, False otherwise
        """
        try:
            return bool(self.music.shuffleEnabled())
        except Exception:
            return False

    def set_shuffle(self, enabled: bool) -> None:
        """Set shuffle mode.

        Args:
            enabled: True to enable shuffle, False to disable
        """
        try:
            self.music.setShuffleEnabled_(enabled)
        except Exception as e:
            raise MusicAppError(f"Failed to set shuffle: {e}")

    def get_repeat(self) -> Literal['off', 'one', 'all']:
        """Get repeat mode.

        Returns:
            Repeat mode: 'off', 'one', or 'all'
        """
        try:
            mode = self.music.songRepeat()
            # 0 = off, 1 = one, 2 = all
            mode_map = {
                0: 'off',
                1: 'one',
                2: 'all'
            }
            return mode_map.get(mode, 'off')
        except Exception:
            return 'off'

    def set_repeat(self, mode: Literal['off', 'one', 'all']) -> None:
        """Set repeat mode.

        Args:
            mode: Repeat mode ('off', 'one', or 'all')
        """
        mode_map = {
            'off': 0,
            'one': 1,
            'all': 2
        }

        if mode not in mode_map:
            raise ValueError(f"Invalid repeat mode: {mode}")

        try:
            self.music.setSongRepeat_(mode_map[mode])
        except Exception as e:
            raise MusicAppError(f"Failed to set repeat: {e}")

    def get_all_artists(self) -> list[str]:
        """Get list of all artists in the library.

        Returns:
            List of artist names
        """
        try:
            library = self.music.sources()[0].libraryPlaylists()[0]
            artists = set()

            # Get unique artists (PyObjC way is slow, use AppleScript)
            script = '''
            tell application "Music"
                set artistList to {}
                repeat with t in (every track of library playlist 1)
                    set artistName to artist of t
                    if artistName is not missing value and artistName is not "" then
                        if artistList does not contain artistName then
                            set end of artistList to artistName
                        end if
                    end if
                end repeat
                return artistList
            end tell
            '''

            success, result, error = self._run_applescript(script)
            if success and result:
                return [a.strip() for a in result.split(', ') if a.strip()]
            return []
        except Exception:
            return []

    def get_all_albums(self) -> list[tuple[str, str]]:
        """Get list of all albums in the library.

        Returns:
            List of tuples (album_name, artist_name)
        """
        try:
            script = '''
            tell application "Music"
                set albumList to {}
                repeat with t in (every track of library playlist 1)
                    set albumName to album of t
                    set artistName to artist of t
                    if albumName is not missing value and albumName is not "" then
                        set albumInfo to albumName & "|" & artistName
                        if albumList does not contain albumInfo then
                            set end of albumList to albumInfo
                        end if
                    end if
                end repeat
                return albumList
            end tell
            '''

            success, result, error = self._run_applescript(script)
            if success and result:
                albums = []
                for item in result.split(', '):
                    parts = item.split('|')
                    if len(parts) >= 2:
                        albums.append((parts[0], parts[1]))
                return albums
            return []
        except Exception:
            return []

    def get_library_playlists(self) -> list[str]:
        """Get list of all playlists in the library.

        Returns:
            List of playlist names
        """
        try:
            playlists = self.music.userPlaylists()
            return [str(p.name()) for p in playlists if p.name()]
        except Exception:
            return []

    def search_library(self, query: str) -> list[Dict[str, str]]:
        """Search the local library using AppleScript (faster for search).

        Args:
            query: Search query string

        Returns:
            List of track dictionaries with name, artist, album
        """
        try:
            # Use AppleScript for search (has native indexed search)
            safe_query = query.replace('"', '\\"')
            script = f'''
            tell application "Music"
                set foundTracks to search library playlist 1 for "{safe_query}"
                set trackList to {{}}
                repeat with t in items 1 thru (count of foundTracks) of foundTracks
                    if (count of trackList) ≥ 50 then exit repeat
                    set trackInfo to name of t & "|" & artist of t & "|" & album of t
                    set end of trackList to trackInfo
                end repeat
                return trackList
            end tell
            '''

            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return []

            output = result.stdout.strip()
            if not output:
                return []

            tracks = []
            for track_str in output.split(', '):
                parts = track_str.strip().split('|')
                if len(parts) >= 3:
                    tracks.append({
                        'name': parts[0],
                        'artist': parts[1],
                        'album': parts[2]
                    })

            return tracks
        except Exception:
            return []

    def get_tracks_by_artist(self, artist: str) -> list[Dict[str, str]]:
        """Get all tracks by a specific artist.

        Args:
            artist: Artist name

        Returns:
            List of track dictionaries with name, artist, album
        """
        try:
            safe_artist = artist.replace('"', '\\"')
            script = f'''
            tell application "Music"
                set foundTracks to (every track of library playlist 1 whose artist is "{safe_artist}")
                set trackList to {{}}
                repeat with t in foundTracks
                    set trackInfo to name of t & "|" & artist of t & "|" & album of t
                    set end of trackList to trackInfo
                end repeat
                return trackList
            end tell
            '''

            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode != 0:
                return []

            output = result.stdout.strip()
            if not output:
                return []

            tracks = []
            for track_str in output.split(', '):
                parts = track_str.strip().split('|')
                if len(parts) >= 3:
                    tracks.append({
                        'name': parts[0],
                        'artist': parts[1],
                        'album': parts[2]
                    })

            return tracks
        except Exception:
            return []

    def get_tracks_by_album(self, album: str, artist: str = "") -> list[Dict[str, str]]:
        """Get all tracks in a specific album.

        Args:
            album: Album name
            artist: Artist name (optional, for better matching)

        Returns:
            List of track dictionaries with name, artist, album
        """
        try:
            safe_album = album.replace('"', '\\"')
            safe_artist = artist.replace('"', '\\"')

            if artist:
                script = f'''
                tell application "Music"
                    set foundTracks to (every track of library playlist 1 whose album is "{safe_album}" and artist is "{safe_artist}")
                    set trackList to {{}}
                    repeat with t in foundTracks
                        set trackInfo to name of t & "|" & artist of t & "|" & album of t
                        set end of trackList to trackInfo
                    end repeat
                    return trackList
                end tell
                '''
            else:
                script = f'''
                tell application "Music"
                    set foundTracks to (every track of library playlist 1 whose album is "{safe_album}")
                    set trackList to {{}}
                    repeat with t in foundTracks
                        set trackInfo to name of t & "|" & artist of t & "|" & album of t
                        set end of trackList to trackInfo
                    end repeat
                    return trackList
                end tell
                '''

            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode != 0:
                return []

            output = result.stdout.strip()
            if not output:
                return []

            tracks = []
            for track_str in output.split(', '):
                parts = track_str.strip().split('|')
                if len(parts) >= 3:
                    tracks.append({
                        'name': parts[0],
                        'artist': parts[1],
                        'album': parts[2]
                    })

            return tracks
        except Exception:
            return []

    def get_playlist_tracks(self, playlist_name: str) -> list[Dict[str, str]]:
        """Get tracks from a specific playlist using AppleScript.

        Args:
            playlist_name: Name of the playlist

        Returns:
            List of track dictionaries with name, artist, album
        """
        try:
            # Use AppleScript (faster for iteration)
            safe_name = playlist_name.replace('"', '\\"')
            script = f'''
            tell application "Music"
                set targetPlaylist to playlist "{safe_name}"
                set trackList to {{}}
                repeat with t in tracks of targetPlaylist
                    set trackInfo to name of t & "|" & artist of t & "|" & album of t
                    set end of trackList to trackInfo
                end repeat
                return trackList
            end tell
            '''

            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode != 0:
                return []

            output = result.stdout.strip()
            if not output:
                return []

            tracks = []
            for track_str in output.split(', '):
                parts = track_str.strip().split('|')
                if len(parts) >= 3:
                    tracks.append({
                        'name': parts[0],
                        'artist': parts[1],
                        'album': parts[2]
                    })

            return tracks
        except Exception:
            return []

    def set_player_position(self, position: float) -> None:
        """Set playback position.

        Args:
            position: Position in seconds
        """
        try:
            self.music.setPlayerPosition_(position)
        except Exception as e:
            raise MusicAppError(f"Failed to set position: {e}")

    def play_track(self, track_name: str, artist: str = "") -> None:
        """Play a specific track by name and artist using NSAppleScript.

        Args:
            track_name: Name of the track
            artist: Artist name (optional, for better matching)
        """
        # Use NSAppleScript to avoid subprocess/Python app launching
        safe_track = track_name.replace('"', '\\"')
        safe_artist = artist.replace('"', '\\"')

        if artist and artist != "Unknown Artist":
            script = f'''
            tell application "Music"
                try
                    set theTrack to (some track of library playlist 1 whose name is "{safe_track}" and artist is "{safe_artist}")
                    set pid to persistent ID of theTrack
                    play (some track whose persistent ID is pid)
                    delay 0.3
                    if player state is not playing then
                        play
                    end if
                    return "OK"
                on error errMsg
                    try
                        set theTrack to (some track of library playlist 1 whose name contains "{safe_track}" and artist contains "{safe_artist}")
                        set pid to persistent ID of theTrack
                        play (some track whose persistent ID is pid)
                        delay 0.3
                        if player state is not playing then
                            play
                        end if
                        return "OK"
                    on error errMsg2
                        return "ERROR: " & errMsg2
                    end try
                end try
            end tell
            '''
        else:
            script = f'''
            tell application "Music"
                try
                    set theTrack to (some track of library playlist 1 whose name is "{safe_track}")
                    set pid to persistent ID of theTrack
                    play (some track whose persistent ID is pid)
                    delay 0.3
                    if player state is not playing then
                        play
                    end if
                    return "OK"
                on error errMsg
                    try
                        set theTrack to (some track of library playlist 1 whose name contains "{safe_track}")
                        set pid to persistent ID of theTrack
                        play (some track whose persistent ID is pid)
                        delay 0.3
                        if player state is not playing then
                            play
                        end if
                        return "OK"
                    on error errMsg2
                        return "ERROR: " & errMsg2
                    end try
                end try
            end tell
            '''

        success, result, error = self._run_applescript(script)
        if not success:
            raise MusicAppError(f"AppleScript failed: {error}")
        if result and result.startswith("ERROR:"):
            raise MusicAppError(result)
