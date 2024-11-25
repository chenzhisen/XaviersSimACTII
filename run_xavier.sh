#!/bin/bash

# Set full environment
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

# Use $HOME for user directory
SCRIPT_DIR="$HOME/Desktop/ef/XaviersSimACTII"
cd "$SCRIPT_DIR"

# Log file with date
LOG_FILE="$SCRIPT_DIR/logs/cron_xavier_$(date +\%Y\%m\%d).log"
mkdir -p "$SCRIPT_DIR/logs"

echo "=== Run started at $(date) ===" >> "$LOG_FILE"

# Install required packages
echo "Installing required packages..." >> "$LOG_FILE"
pip3 install -r requirements.txt >> "$LOG_FILE" 2>&1

# Run the main script
PYTHONPATH="$SCRIPT_DIR" python3 "$SCRIPT_DIR/src/main.py" --provider XAI --post-to-twitter >> "$LOG_FILE" 2>&1
echo "=== Run completed at $(date) ===" >> "$LOG_FILE"