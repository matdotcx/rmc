#!/bin/bash
# Uninstall the org.iaconelli.rmcd LaunchAgent and stop rmcd

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
make -C "$REPO_DIR/daemon" uninstall

echo "✓ rmcd LaunchAgent uninstalled"
