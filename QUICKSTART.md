# Quick Start Guide

Get up and running with RMC in under 2 minutes!

## Prerequisites

- macOS 10.15+ (Catalina or later)
- Python 3.10+
- Music.app installed

## Installation

```bash
# Navigate to project directory
cd ~/Developer/workspace/matdotcx/rmc

# Install dependencies and package
pip3 install -e .
```

## Before First Run

1. **Open Music.app**
   ```bash
   open -a Music
   ```

2. **Play a song** (any song, to verify Music.app works)

3. **Grant permissions** if prompted by macOS

## Launch

```bash
rmc
```

Or use the launcher script:
```bash
./launch.sh
```

## Your First Session

Once launched, you'll see the Now Playing screen:

```
╭──────────────────────────────────────────╮
│ ♫ Current Song Name                      │
│ Artist: Artist Name                      │
│ Album: Album Name                        │
╰──────────────────────────────────────────╯
```

### Try These Keys

1. Press `Space` - Pause/play the current song
2. Press `n` - Skip to next song
3. Press `+` - Turn up the volume
4. Press `-` - Turn down the volume
5. Press `s` - Toggle shuffle
6. Press `r` - Change repeat mode
7. Press `q` - Quit

## Using Over SSH

From your work computer:

```bash
# SSH into your Mac
ssh your-mac.local

# Launch RMC
rmc

# Control your music remotely!
```

## Troubleshooting

### "Command not found: rmc"

The package isn't installed. Run:
```bash
pip3 install -e .
```

### "AppleScript execution timed out"

Music.app isn't running. Open it:
```bash
open -a Music
```

### Display looks broken

Your terminal doesn't support Unicode/colors well. Try:
- iTerm2 (macOS)
- Kitty terminal
- Modern Terminal.app with proper profile

### Permission errors

Grant automation permissions:
1. System Preferences → Security & Privacy
2. Privacy tab → Automation
3. Enable your terminal to control Music

## What's Working

✅ Now Playing screen with real-time updates
✅ Playback controls (play, pause, skip)
✅ Volume control
✅ Shuffle and repeat modes
✅ SSH support

## What's Coming

🔜 Library browser (browse your music collection)
🔜 Catalog search (search Apple Music)
🔜 Playlist management
🔜 Album art display

## Learn More

- Full documentation: `README.md`
- Detailed usage guide: `USAGE.md`
- Implementation details: `IMPLEMENTATION.md`

## Getting Help

1. Check `USAGE.md` for detailed troubleshooting
2. Verify Music.app is working with `./check_music.sh`
3. Test components with `python3 test_basic.py`

---

**Happy listening! 🎵**
