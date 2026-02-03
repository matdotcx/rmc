# RMC - Apple Music Remote Control

A Python TUI (Text User Interface) application for remotely controlling Apple Music on macOS via SSH. Features an iPod-like interface for playback control, library browsing, and Apple Music catalog search.

## Features

### Phase 1 (MVP) - ✅ Implemented
- **Now Playing Screen**: View current track info with real-time updates
- **Playback Controls**: Play, pause, skip tracks
- **Volume Control**: Adjust volume with +/- keys
- **Shuffle & Repeat**: Toggle shuffle and cycle through repeat modes
- **SSH Support**: Works seamlessly over SSH connections

### Upcoming Features
- **Library Browser**: Browse playlists, artists, albums, and songs
- **Catalog Search**: Search Apple Music catalog and add songs to library
- **Playlist Management**: Create and modify playlists
- **Album Art Display**: View album artwork (terminal graphics support)

## Requirements

- macOS 10.15+ (Catalina or later)
- Python 3.10+
- Music.app installed and signed in
- Swift 5.9+ (comes with macOS)

## Installation

1. Clone the repository:
```bash
cd ~/Developer/workspace/matdotcx/rmc
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install the package in development mode:
```bash
pip install -e .
```

## Usage

Launch the TUI application:

```bash
rmc
```

Or run directly with Python:

```bash
python -m src.main
```

### Key Bindings

#### Global
- `q` - Quit application
- `1` - Show Now Playing screen

#### Now Playing Screen
- `Space` - Play/Pause
- `n` - Next track
- `p` - Previous track
- `s` - Toggle shuffle
- `r` - Cycle repeat mode (off → all → one)
- `+` - Volume up
- `-` - Volume down

## SSH Usage

The application works perfectly over SSH. From your work machine:

```bash
ssh your-mac
rmc
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Python TUI (Textual)                  │
│  - UI Components (Now Playing, Library, Search, etc.)   │
└───────────────┬─────────────────────┬───────────────────┘
                │                     │
        ┌───────▼────────┐    ┌──────▼──────────┐
        │   AppleScript  │    │  Swift Helper   │
        │    Wrapper     │    │      CLI        │
        │   (Python)     │    │   (music-api)   │
        └───────┬────────┘    └──────┬──────────┘
                │                     │
        ┌───────▼────────┐    ┌──────▼──────────┐
        │   Music.app    │    │ Apple Music API │
        │   (Local)      │    │  (Web Service)  │
        └────────────────┘    └─────────────────┘
```

### Components

- **Python TUI (Textual)**: Interactive text-based interface
- **AppleScript Wrapper**: Direct control of Music.app for playback and library operations
- **Swift Helper** (Coming soon): Handles Apple Music API authentication and catalog operations

## Project Structure

```
rmc/
├── src/
│   ├── main.py              # Entry point
│   ├── tui/
│   │   ├── app.py           # Main Textual app
│   │   ├── screens/
│   │   │   └── now_playing.py
│   │   └── widgets/
│   ├── music/
│   │   └── applescript.py   # AppleScript wrapper
│   └── config/
│       └── settings.py      # Configuration management
├── music-api/               # Swift helper (coming soon)
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Configuration

Configuration is stored in `~/.config/rmc/config.json`. The file is created automatically on first run with default settings.

## Development

### Running Tests

```bash
# Install in development mode
pip install -e .

# Run the application
rmc
```

### Implementation Phases

- [x] Phase 1: Core Infrastructure (MVP)
- [ ] Phase 2: Library Browser
- [ ] Phase 3: Swift API Helper
- [ ] Phase 4: Catalog Search Integration
- [ ] Phase 5: Playlist Management
- [ ] Phase 6: Polish & Features

## Troubleshooting

### Music.app not responding
Ensure Music.app is running and you're signed in to your Apple Music account.

### Permission errors
The app requires access to control Music.app. Grant permissions when prompted by macOS.

### SSH display issues
Use a terminal with good Unicode support. Recommended: iTerm2, Kitty, or modern Terminal.app.

## License

MIT License

## Contributing

Contributions welcome! Please feel free to submit pull requests or open issues.

## References

- [Apple Music API Documentation](https://developer.apple.com/documentation/applemusicapi)
- [Textual Documentation](https://textual.textualize.io/)
- [AppleScript for Music.app](https://dougscripts.com/itunes/)
