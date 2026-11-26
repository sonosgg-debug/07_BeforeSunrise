#!/bin/bash
# ==============================================================================
# BeforeSunrise - Oracle Linux Server Execution Script
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
python3 daily_indicators.py >> execution.log 2>&1
