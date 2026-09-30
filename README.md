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
./install.sh
```

This will:
- Install the Python package
- Build and sign the rmcd daemon
- Install the LaunchAgent (auto-start on login)
- Configure PATH
- Authorize MusicKit

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
- Daemon host/port and Marantz receiver hostname (`daemon.receiver_host`)

### Daemon

`rmcd` runs as the `org.iaconelli.rmcd` LaunchAgent, which starts it via
`scripts/start-daemon.sh` so the settings above are applied. Changing the
receiver in Settings restarts it automatically.

The daemon is signed with a local self-signed certificate (created once by
`make -C daemon cert`, which `install.sh` runs) so macOS keeps its Apple Music
and Automation permissions across rebuilds. Over SSH, unlock the login
keychain first: `security unlock-keychain ~/Library/Keychains/login.keychain-db`.

```bash
make -C daemon cert         # one-off: create the signing identity
make -C daemon install      # build, sign, install and start
launchctl kickstart -k gui/$(id -u)/org.iaconelli.rmcd   # restart
make -C daemon uninstall    # stop and remove
```

## License

MIT
