#!/bin/bash
# Launcher script for RMC with prerequisite checks

set -e

echo "RMC - Apple Music Remote Control"
echo "================================="
echo ""

# Check if Music.app exists
if [ ! -d "/System/Applications/Music.app" ]; then
    echo "✗ Error: Music.app not found"
    echo "  Music.app is required to run RMC"
    exit 1
fi

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "✗ Error: Python 3 not found"
    echo "  Please install Python 3.10 or later"
    exit 1
fi

# Check if rmc is installed
if ! command -v rmc &> /dev/null; then
    echo "⚠ Warning: rmc command not found in PATH"
    echo "  Trying to run directly with python3..."
    python3 -m src.main
else
    echo "✓ Starting RMC..."
    echo ""
    rmc
fi
