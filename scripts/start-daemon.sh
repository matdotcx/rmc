#!/bin/bash
# Start rmcd daemon with settings from ~/.config/rmc/config.json

set -e

DAEMON_PATH="${DAEMON_PATH:-$HOME/Developer/workspace/matdotcx/rmc/daemon/.build/rmcd.app}"
CONFIG_FILE="$HOME/.config/rmc/config.json"

# Default values
HOST="127.0.0.1"
PORT="18895"
RECEIVER_HOST=""

# Read from config if it exists
if [ -f "$CONFIG_FILE" ]; then
    # Extract values using Python
    if command -v python3 &> /dev/null; then
        HOST=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('daemon',{}).get('host','$HOST'))" 2>/dev/null || echo "$HOST")
        PORT=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('daemon',{}).get('port',$PORT))" 2>/dev/null || echo "$PORT")
        RECEIVER_HOST=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c.get('daemon',{}).get('receiver_host',''))" 2>/dev/null || echo "")
    fi
fi

# Build command
CMD_ARGS="--host $HOST --port $PORT"
if [ -n "$RECEIVER_HOST" ]; then
    CMD_ARGS="$CMD_ARGS --receiver-host $RECEIVER_HOST"
    echo "Starting rmcd on $HOST:$PORT with receiver at $RECEIVER_HOST"
else
    echo "Starting rmcd on $HOST:$PORT (no receiver configured)"
fi

# Stop any running instance
pkill -9 rmcd 2>/dev/null || true
sleep 1

# Start daemon
if [ -d "$DAEMON_PATH" ]; then
    open "$DAEMON_PATH" --args $CMD_ARGS
    echo "Daemon started!"

    # Wait a moment and authorize MusicKit
    sleep 3
    if command -v curl &> /dev/null; then
        echo "Authorizing MusicKit..."
        curl -X POST -s http://$HOST:$PORT/api/v1/system/authorize > /dev/null
        echo "Done!"
    fi
else
    echo "Error: Daemon not found at $DAEMON_PATH"
    echo "Build it first with: cd daemon && make sign"
    exit 1
fi
