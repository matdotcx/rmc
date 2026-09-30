#!/bin/bash
# Uninstall rmcd LaunchAgent

set -e

PLIST_NAME="org.iaconelli.rmcd.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "Uninstalling rmcd LaunchAgent..."

# Unload the LaunchAgent
if [ -f "$PLIST_DEST" ]; then
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    rm "$PLIST_DEST"
    echo "✓ rmcd LaunchAgent uninstalled"
else
    echo "LaunchAgent not installed"
fi

# Kill any running instances
pkill -9 rmcd 2>/dev/null || true

echo "Done!"
