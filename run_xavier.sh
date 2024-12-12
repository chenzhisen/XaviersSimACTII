#!/bin/bash

# Debug line - will show in system logs
logger "Xavier cron job started at $(date)"

# Set full environment
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

# Use absolute paths
SCRIPT_DIR="/Users/yufeili/Desktop/ef/XaviersSimACTII"
cd "$SCRIPT_DIR"

# Set PYTHONPATH to current directory
export PYTHONPATH=.

# Log file with date
LOG_FILE="$SCRIPT_DIR/logs/cron_xavier_$(date +\%Y\%m\%d).log"
mkdir -p "$SCRIPT_DIR/logs"

echo "=== Run started at $(date) ===" >> "$LOG_FILE"

# Use full path to Python executable
/Users/yufeili/.pyenv/versions/3.8.17/bin/python3 src/main.py --provider xai --is-production >> "$LOG_FILE" 2>&1
RESULT=$?

echo "Python script exit code: $RESULT" >> "$LOG_FILE"
echo "=== Run completed at $(date) ===" >> "$LOG_FILE"