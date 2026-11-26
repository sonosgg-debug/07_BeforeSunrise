#!/bin/bash
# ==============================================================================
# MorningWatch - Oracle Linux Server Execution Script
# ==============================================================================

# Change to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Activate Python virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run daily indicators script and log output
python3 daily_indicators.py >> execution.log 2>&1
