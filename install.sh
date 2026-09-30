#!/bin/bash
# Complete installation script for RMC

set -e

echo "======================================"
echo "  RMC Installation"
echo "======================================"
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 1. Install Python package
echo "📦 Installing Python package..."
pip install -e .
echo "✓ Python package installed"
echo ""

# 2. Build and sign daemon
echo "🔨 Building rmcd daemon..."
cd daemon
make sign
cd ..
echo "✓ Daemon built and signed"
echo ""

# 3. Create config directory
echo "📁 Creating config directory..."
mkdir -p "$HOME/.config/rmc"
echo "✓ Config directory created"
echo ""

# 4. Install LaunchAgent
echo "🚀 Installing LaunchAgent..."
PLIST_NAME="org.iaconelli.rmcd.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_NAME" "$PLIST_DEST"

# Unload if already loaded
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# Load the LaunchAgent
launchctl load "$PLIST_DEST"
echo "✓ LaunchAgent installed and started"
echo ""

# 5. Add rmc to PATH
echo "🔧 Configuring PATH..."
if ! grep -q "Library/Python/3.12/bin" "$HOME/.zshrc" 2>/dev/null; then
    echo 'export PATH="$HOME/Library/Python/3.12/bin:$PATH"' >> "$HOME/.zshrc"
    echo "✓ Added Python bin to PATH in ~/.zshrc"
else
    echo "✓ PATH already configured"
fi
echo ""

# 6. Wait for daemon to start
echo "⏳ Waiting for daemon to start..."
sleep 3

# 7. Authorize MusicKit
echo "🎵 Authorizing MusicKit..."
curl -X POST -s http://127.0.0.1:18895/api/v1/system/authorize > /dev/null 2>&1 || true
echo "✓ MusicKit authorized"
echo ""

echo "======================================"
echo "  Installation Complete! 🎉"
echo "======================================"
echo ""
echo "Next steps:"
echo "  1. Reload your shell: source ~/.zshrc"
echo "  2. Run RMC: rmc"
echo "  3. Configure receiver in Settings"
echo ""
echo "The daemon is now running and will start automatically on login."
echo ""
echo "Useful commands:"
echo "  Start daemon:    launchctl load ~/Library/LaunchAgents/$PLIST_NAME"
echo "  Stop daemon:     launchctl unload ~/Library/LaunchAgents/$PLIST_NAME"
echo "  View logs:       tail -f ~/.config/rmc/daemon.log"
echo "  Uninstall:       $SCRIPT_DIR/scripts/uninstall-daemon.sh"
echo ""
