"""TUI screens for RMC."""

from src.tui.screens.main_menu import MainMenuScreen, MusicMenuScreen
from src.tui.screens.now_playing import NowPlayingScreen
from src.tui.screens.playlists import PlaylistsScreen, PlaylistScreen
from src.tui.screens.artists import ArtistsScreen, ArtistScreen, ArtistSongsScreen
from src.tui.screens.albums import AlbumsScreen, AlbumScreen
from src.tui.screens.songs import SongsScreen
from src.tui.screens.search import SearchScreen
from src.tui.screens.settings import SettingsScreen, AboutScreen

__all__ = [
    'MainMenuScreen',
    'MusicMenuScreen',
    'NowPlayingScreen',
    'PlaylistsScreen',
    'PlaylistScreen',
    'ArtistsScreen',
    'ArtistScreen',
    'ArtistSongsScreen',
    'AlbumsScreen',
    'AlbumScreen',
    'SongsScreen',
    'SearchScreen',
    'SettingsScreen',
    'AboutScreen',
]
