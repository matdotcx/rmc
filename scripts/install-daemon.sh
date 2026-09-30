#!/bin/bash
# Build rmcd and install it as the org.iaconelli.rmcd LaunchAgent

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
make -C "$REPO_DIR/daemon" install

echo "✓ rmcd LaunchAgent installed and started"
echo ""
echo "Commands:"
echo "  Restart: launchctl kickstart -k gui/$(id -u)/org.iaconelli.rmcd"
echo "  Stop:    make -C \"$REPO_DIR/daemon\" uninstall"
echo "  Logs:    tail -f ~/.config/rmc/daemon.log"
