#!/bin/bash
# Simple script to check if Music.app is available

echo "Checking Music.app status..."

# Check if Music.app exists
if [ ! -d "/System/Applications/Music.app" ]; then
    echo "✗ Music.app not found at /System/Applications/Music.app"
    exit 1
fi

echo "✓ Music.app is installed"

# Try a simple AppleScript command with shorter timeout
if timeout 3 osascript -e 'tell application "Music" to get name' &>/dev/null; then
    echo "✓ Music.app is responding to AppleScript"
else
    echo "⚠ Music.app may not be running or is not responding"
    echo "  Try opening Music.app manually"
fi

echo ""
echo "You can now run: rmc"
