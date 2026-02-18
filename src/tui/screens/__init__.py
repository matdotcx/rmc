"""TUI screens for RMC."""

from src.tui.screens.now_playing import NowPlayingScreen
from src.tui.screens.playlists import PlaylistsScreen, PlaylistScreen
from src.tui.screens.artists import ArtistsScreen, ArtistScreen
from src.tui.screens.albums import AlbumsScreen, AlbumScreen
from src.tui.screens.search import SearchScreen
from src.tui.screens.settings import SettingsScreen

__all__ = [
    'NowPlayingScreen',
    'PlaylistsScreen',
    'PlaylistScreen',
    'ArtistsScreen',
    'ArtistScreen',
    'AlbumsScreen',
    'AlbumScreen',
    'SearchScreen',
    'SettingsScreen',
]
