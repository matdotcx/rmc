"""AppleScript wrapper for controlling Music.app on macOS."""

import subprocess
from typing import Optional, Dict, Any, Literal


class MusicAppError(Exception):
    """Exception raised when Music.app operations fail."""
    pass


class AppleScriptWrapper:
    """Wrapper for controlling Music.app via AppleScript."""

    @staticmethod
    def _run_script(script: str) -> str:
        """Execute an AppleScript and return the output.

        Args:
            script: AppleScript code to execute

        Returns:
            Script output as string

        Raises:
            MusicAppError: If the script execution fails
        """
        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise MusicAppError(f"AppleScript execution failed: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise MusicAppError("AppleScript execution timed out")

    def play(self) -> None:
        """Start playback."""
        script = 'tell application "Music" to play'
        self._run_script(script)

    def pause(self) -> None:
        """Pause playback."""
        script = 'tell application "Music" to pause'
        self._run_script(script)

    def playpause(self) -> None:
        """Toggle play/pause."""
        script = 'tell application "Music" to playpause'
        self._run_script(script)

    def next_track(self) -> None:
        """Skip to next track."""
        script = 'tell application "Music" to next track'
        self._run_script(script)

    def previous_track(self) -> None:
        """Go to previous track."""
        script = 'tell application "Music" to previous track'
        self._run_script(script)

    def get_player_state(self) -> Literal['playing', 'paused', 'stopped']:
        """Get current player state.

        Returns:
            Player state: 'playing', 'paused', or 'stopped'
        """
        script = 'tell application "Music" to get player state as string'
        result = self._run_script(script)

        # AppleScript returns constants like 'kPSP', 'kPSp', 'kPSS'
        state_map = {
            'playing': 'playing',
            'paused': 'paused',
            'stopped': 'stopped',
            'kPSP': 'playing',
            'kPSp': 'paused',
            'kPSS': 'stopped'
        }

        return state_map.get(result.lower(), 'stopped')

    def get_current_track(self) -> Optional[Dict[str, Any]]:
        """Get information about the currently playing track.

        Returns:
            Dictionary with track info or None if no track is playing:
            {
                'name': str,
                'artist': str,
                'album': str,
                'duration': float,  # seconds
                'position': float,  # seconds
                'album_artist': str
            }
        """
        script = '''
        tell application "Music"
            if player state is not stopped then
                set t to current track
                set trackName to name of t
                set trackArtist to artist of t
                set trackAlbum to album of t
                set trackDuration to duration of t
                set trackPosition to player position
                set trackAlbumArtist to album artist of t
                return trackName & "|" & trackArtist & "|" & trackAlbum & "|" & trackDuration & "|" & trackPosition & "|" & trackAlbumArtist
            else
                return ""
            end if
        end tell
        '''

        result = self._run_script(script)

        if not result:
            return None

        parts = result.split('|')
        if len(parts) < 6:
            return None

        try:
            return {
                'name': parts[0],
                'artist': parts[1],
                'album': parts[2],
                'duration': float(parts[3]),
                'position': float(parts[4]),
                'album_artist': parts[5]
            }
        except (ValueError, IndexError):
            return None

    def get_volume(self) -> int:
        """Get current volume level.

        Returns:
            Volume level (0-100)
        """
        script = 'tell application "Music" to get sound volume'
        result = self._run_script(script)
        try:
            return int(result)
        except ValueError:
            return 50

    def set_volume(self, level: int) -> None:
        """Set volume level.

        Args:
            level: Volume level (0-100)
        """
        level = max(0, min(100, level))  # Clamp to 0-100
        script = f'tell application "Music" to set sound volume to {level}'
        self._run_script(script)

    def get_shuffle(self) -> bool:
        """Get shuffle mode status.

        Returns:
            True if shuffle is enabled, False otherwise
        """
        script = 'tell application "Music" to get shuffle enabled'
        result = self._run_script(script)
        return result.lower() == 'true'

    def set_shuffle(self, enabled: bool) -> None:
        """Set shuffle mode.

        Args:
            enabled: True to enable shuffle, False to disable
        """
        value = 'true' if enabled else 'false'
        script = f'tell application "Music" to set shuffle enabled to {value}'
        self._run_script(script)

    def get_repeat(self) -> Literal['off', 'one', 'all']:
        """Get repeat mode.

        Returns:
            Repeat mode: 'off', 'one', or 'all'
        """
        script = 'tell application "Music" to get song repeat as string'
        result = self._run_script(script)

        # AppleScript returns constants
        repeat_map = {
            'off': 'off',
            'one': 'one',
            'all': 'all',
            'kRpOff': 'off',
            'kRp1': 'one',
            'kRpAll': 'all'
        }

        return repeat_map.get(result.lower(), 'off')

    def set_repeat(self, mode: Literal['off', 'one', 'all']) -> None:
        """Set repeat mode.

        Args:
            mode: Repeat mode ('off', 'one', or 'all')
        """
        mode_map = {
            'off': 'off',
            'one': 'one',
            'all': 'all'
        }

        if mode not in mode_map:
            raise ValueError(f"Invalid repeat mode: {mode}")

        script = f'tell application "Music" to set song repeat to {mode_map[mode]}'
        self._run_script(script)

    def get_library_playlists(self) -> list[str]:
        """Get list of all playlists in the library.

        Returns:
            List of playlist names
        """
        script = '''
        tell application "Music"
            set playlistNames to {}
            repeat with p in user playlists
                set end of playlistNames to name of p
            end repeat
            return playlistNames
        end tell
        '''

        result = self._run_script(script)
        if not result:
            return []

        # AppleScript returns comma-separated list
        return [name.strip() for name in result.split(',') if name.strip()]

    def search_library(self, query: str) -> list[Dict[str, str]]:
        """Search the local library.

        Args:
            query: Search query string

        Returns:
            List of track dictionaries with name, artist, album
        """
        script = f'''
        tell application "Music"
            set foundTracks to search library playlist 1 for "{query}"
            set trackList to {{}}
            repeat with t in foundTracks
                set trackInfo to name of t & "|" & artist of t & "|" & album of t
                set end of trackList to trackInfo
            end repeat
            return trackList
        end tell
        '''

        result = self._run_script(script)
        if not result:
            return []

        tracks = []
        for track_str in result.split(','):
            parts = track_str.strip().split('|')
            if len(parts) >= 3:
                tracks.append({
                    'name': parts[0],
                    'artist': parts[1],
                    'album': parts[2]
                })

        return tracks

    def set_player_position(self, position: float) -> None:
        """Set playback position.

        Args:
            position: Position in seconds
        """
        script = f'tell application "Music" to set player position to {position}'
        self._run_script(script)

    def get_playlist_tracks(self, playlist_name: str) -> list[Dict[str, str]]:
        """Get tracks from a specific playlist.

        Args:
            playlist_name: Name of the playlist

        Returns:
            List of track dictionaries with name, artist, album
        """
        # Escape single quotes in playlist name
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

        result = self._run_script(script)
        if not result:
            return []

        tracks = []
        for track_str in result.split(', '):
            parts = track_str.strip().split('|')
            if len(parts) >= 3:
                tracks.append({
                    'name': parts[0],
                    'artist': parts[1],
                    'album': parts[2]
                })

        return tracks

    def play_track(self, track_name: str, artist: str = "") -> None:
        """Play a specific track by name and artist.

        Args:
            track_name: Name of the track
            artist: Artist name (optional, for better matching)
        """
        # Escape quotes in track name and artist
        safe_track = track_name.replace('"', '\\"')
        safe_artist = artist.replace('"', '\\"')

        if artist:
            script = f'''
            tell application "Music"
                set foundTracks to search library playlist 1 for "{safe_track}"
                repeat with t in foundTracks
                    if artist of t is "{safe_artist}" then
                        play t
                        return
                    end if
                end repeat
                -- If exact match not found, play first result
                if (count of foundTracks) > 0 then
                    play item 1 of foundTracks
                end if
            end tell
            '''
        else:
            script = f'''
            tell application "Music"
                set foundTracks to search library playlist 1 for "{safe_track}"
                if (count of foundTracks) > 0 then
                    play item 1 of foundTracks
                end if
            end tell
            '''

        self._run_script(script)
