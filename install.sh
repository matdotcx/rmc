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

# 2. Create config directory
echo "📁 Creating config directory..."
mkdir -p "$HOME/.config/rmc"
echo "✓ Config directory created"
echo ""

# 3. Stable signing identity, so permissions survive daemon rebuilds
echo "🔏 Creating local code-signing identity..."
make -C daemon cert
echo ""

# 4. Build, sign and install the daemon LaunchAgent
echo "🔨 Building rmcd daemon and installing LaunchAgent..."
make -C daemon install
echo "✓ Daemon built, signed and started"
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

# 6. MusicKit authorization is requested by scripts/start-daemon.sh once
# the daemon is up; approve the Apple Music prompt on this Mac if shown.

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
echo "  Restart daemon:  launchctl kickstart -k gui/$(id -u)/org.iaconelli.rmcd"
echo "  Stop daemon:     make -C daemon uninstall"
echo "  View logs:       tail -f ~/.config/rmc/daemon.log"
echo "  Uninstall:       $SCRIPT_DIR/scripts/uninstall-daemon.sh"
echo ""
