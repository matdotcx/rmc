#!/bin/bash
# Start rmcd with settings from ~/.config/rmc/config.json.
#
# Run by the org.iaconelli.rmcd LaunchAgent (see `make -C daemon install`).
# Ends by exec'ing `open -W`, which stays alive as long as rmcd does, so
# launchd supervises the daemon and restarts it (and re-reads the config)
# if it exits. To restart after a config change:
#   launchctl kickstart -k gui/$(id -u)/org.iaconelli.rmcd

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DAEMON_PATH="${DAEMON_PATH:-$REPO_DIR/daemon/.build/rmcd.app}"
CONFIG_FILE="$HOME/.config/rmc/config.json"

# Default values
HOST="127.0.0.1"
PORT="18895"
RECEIVER_HOST=""

# Read from config if it exists
if [ -f "$CONFIG_FILE" ] && command -v python3 &> /dev/null; then
    read -r HOST PORT RECEIVER_HOST < <(python3 - "$CONFIG_FILE" "$HOST" "$PORT" <<'PY' || true
import json, sys
path, host, port = sys.argv[1:]
d = json.load(open(path)).get("daemon", {})
print(d.get("host") or host, d.get("port") or port, d.get("receiver_host") or "")
PY
    )
fi

CMD_ARGS=(--host "$HOST" --port "$PORT")
if [ -n "$RECEIVER_HOST" ]; then
    CMD_ARGS+=(--receiver-host "$RECEIVER_HOST")
    echo "Starting rmcd on $HOST:$PORT with receiver at $RECEIVER_HOST"
else
    echo "Starting rmcd on $HOST:$PORT (no receiver configured)"
fi

if [ ! -d "$DAEMON_PATH" ]; then
    echo "Error: Daemon not found at $DAEMON_PATH"
    echo "Build and install it with: make -C \"$REPO_DIR/daemon\" install"
    exit 1
fi

# Stop any running instance (a previous `open -W` exits with it)
pkill -x rmcd 2>/dev/null || true
sleep 1

# Request MusicKit authorization once the daemon is listening
(
    for _ in $(seq 1 20); do
        sleep 1
        curl -fs -X POST "http://$HOST:$PORT/api/v1/system/authorize" > /dev/null && exit 0
    done
) &

exec /usr/bin/open -W "$DAEMON_PATH" --args "${CMD_ARGS[@]}"
