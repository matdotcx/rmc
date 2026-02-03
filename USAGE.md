# RMC Usage Guide

## Getting Started

### Prerequisites

1. Ensure Music.app is installed (comes with macOS)
2. Open Music.app and sign in to your Apple Music account
3. Play any song to verify Music.app is working

### First Run

1. Install the application:
```bash
cd ~/Developer/workspace/matdotcx/rmc
pip3 install -e .
```

2. Check Music.app connectivity:
```bash
./check_music.sh
```

3. Launch the TUI:
```bash
rmc
```

## Interface Overview

### Now Playing Screen

The default screen shows:

```
┌─────────────────────────────────────────┐
│ ♫ Song Name                             │
│ Artist: Artist Name                     │
│ Album: Album Name                       │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ [████████████░░░░░░░░░░]               │
│ 02:34 / 04:15                          │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ ▶ Playing                               │
│ Volume: ████████████░░░░░░░░ 60%       │
│ 🔀 Shuffle | 🔁 Repeat: off             │
└─────────────────────────────────────────┘
```

## Keyboard Controls

### Navigation
- `q` - Quit application
- `1` - Go to Now Playing screen

### Playback Control
- `Space` - Toggle Play/Pause
- `n` - Next track
- `p` - Previous track

### Audio Settings
- `+` - Increase volume by 5%
- `-` - Decrease volume by 5%

### Playback Modes
- `s` - Toggle Shuffle (on/off)
- `r` - Cycle Repeat modes:
  - off → all → one → off

## Common Tasks

### Control Music Over SSH

From your work computer:

```bash
# Connect to your Mac
ssh your-mac.local

# Launch RMC
rmc

# Control your music!
# Press Space to play/pause, n for next track, etc.
```

### Adjust Volume

Press `+` repeatedly to increase volume, or `-` to decrease.
Each press adjusts by 5%.

### Change Repeat Mode

Press `r` to cycle through:
- **off**: No repeat
- **all**: Repeat entire playlist/library
- **one**: Repeat current track

### Enable Shuffle

Press `s` to toggle shuffle on/off.

## Troubleshooting

### "AppleScript execution timed out"

**Cause**: Music.app is not running or not responding.

**Solution**:
1. Open Music.app manually
2. Play any song
3. Try launching `rmc` again

### "Permission denied" errors

**Cause**: Terminal doesn't have automation permissions.

**Solution**:
1. Open System Preferences → Security & Privacy → Privacy
2. Select "Automation" from the sidebar
3. Enable permissions for Terminal/iTerm to control Music

### Display looks broken over SSH

**Cause**: Terminal doesn't support Unicode/colors properly.

**Solution**: Use a modern terminal:
- macOS: iTerm2 or Terminal.app (recent versions)
- Linux: Kitty, Alacritty, or modern gnome-terminal
- Windows: Windows Terminal with SSH

### Progress bar not updating

The app updates every second. If you don't see updates:
1. Check if Music.app is actually playing
2. Try pressing Space to play/pause
3. Check Music.app directly to verify playback

## Tips & Tricks

### Quick Control Without Full TUI

For simple commands, you can use AppleScript directly:

```bash
# Play/pause
osascript -e 'tell application "Music" to playpause'

# Next track
osascript -e 'tell application "Music" to next track'

# Set volume to 50%
osascript -e 'tell application "Music" to set sound volume to 50'
```

But the TUI provides a much nicer interface!

### Running in Background

You can run `rmc` in a `tmux` or `screen` session to keep it running:

```bash
# Create a new tmux session
tmux new -s music

# Launch rmc
rmc

# Detach with Ctrl+B, then D
# Reattach later with: tmux attach -t music
```

### Monitoring While Working

Open RMC in a separate terminal window or pane to monitor what's playing
while you work in other windows.

## Coming Soon

### Library Browser (Phase 2)
- Browse your full music library
- Search for songs, albums, artists
- Play directly from library

### Catalog Search (Phase 4)
- Search Apple Music catalog
- Add songs to your library
- Discover new music

### Playlist Management (Phase 5)
- Create and edit playlists
- Add/remove songs
- Organize your music

## Getting Help

For issues or feature requests:
- Check the README.md
- Review this usage guide
- Open an issue on GitHub (if available)
