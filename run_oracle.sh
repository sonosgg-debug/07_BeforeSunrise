#!/bin/bash
# ==============================================================================
# BeforeSunrise - Oracle Linux Server Execution Script
# ==============================================================================

# Change to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Determine Python executable
if [ -f "/home/ubuntu/venv_apps/bin/python3" ]; then
    PYTHON_BIN="/home/ubuntu/venv_apps/bin/python3"
elif [ -d "venv" ]; then
    source venv/bin/activate
    PYTHON_BIN="python3"
elif [ -d ".venv" ]; then
    source .venv/bin/activate
    PYTHON_BIN="python3"
else
    PYTHON_BIN="python3"
fi

# When run via Cron, verify New York market close hour (16:xx EST/EDT)
# This automatically handles Daylight Saving Time (05:05 KST during EDT, 06:05 KST during EST)
if [ "$1" == "--cron" ]; then
    NY_HOUR=$(TZ="America/New_York" date +"%-H")
    if [ "$NY_HOUR" -ne 16 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Skipped: NY hour is $NY_HOUR (Not market close 16:xx)." >> execution.log
        exit 0
    fi
fi

# Run daily indicators script and log output
$PYTHON_BIN daily_indicators.py >> execution.log 2>&1
