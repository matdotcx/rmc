#!/bin/bash
# Install rmcd as a LaunchAgent to run automatically

set -e

PLIST_NAME="org.iaconelli.rmcd.plist"
PLIST_SOURCE="$HOME/Developer/workspace/matdotcx/rmc/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "Installing rmcd LaunchAgent..."

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$HOME/Library/LaunchAgents"

# Copy plist file
if [ -f "$PLIST_SOURCE" ]; then
    cp "$PLIST_SOURCE" "$PLIST_DEST"
    echo "Copied $PLIST_NAME to ~/Library/LaunchAgents/"
else
    echo "Error: $PLIST_SOURCE not found"
    exit 1
fi

# Unload if already loaded
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# Load the LaunchAgent
launchctl load "$PLIST_DEST"

echo "✓ rmcd LaunchAgent installed and started!"
echo ""
echo "The daemon will now start automatically on login."
echo ""
echo "Commands:"
echo "  Stop:    launchctl unload ~/Library/LaunchAgents/$PLIST_NAME"
echo "  Start:   launchctl load ~/Library/LaunchAgents/$PLIST_NAME"
echo "  Logs:    tail -f ~/.config/rmc/daemon.log"
