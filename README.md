# RMC - Remote Media Controller

A terminal-based remote control for Apple Music on macOS. Control playback, browse your library, and search tracks - all from the command line or over SSH.

## Features

- iPod-style navigation interface
- Full playback control (play, pause, skip, volume, shuffle, repeat)
- Browse playlists, artists, albums, and songs
- Fast full-text search with SQLite indexing
- Works over SSH
- Adapts to light/dark terminal themes

## Requirements

- macOS 10.15+
- Python 3.10+
- Music.app

## Installation

```bash
git clone https://github.com/matdotcx/rmc.git
cd rmc
pip install -e .
```

## Usage

```bash
rmc
```

### Controls

| Key | Action |
|-----|--------|
| `up/down` or `j/k` | Navigate |
| `right` or `enter` | Select |
| `left` or `escape` | Back |
| `q` | Quit |

### Playback

| Key | Action |
|-----|--------|
| `space` | Play/Pause |
| `n` / `p` | Next/Previous track |
| `s` | Toggle shuffle |
| `r` | Cycle repeat mode |
| `+` / `-` | Volume |

## Configuration

Config stored in `~/.config/rmc/config.json`:
- Inactivity timeout (auto-return to Now Playing)
- Update interval

## License

MIT
