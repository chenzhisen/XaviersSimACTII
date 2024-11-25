#!/bin/bash

LOG_FILE="logs/cron_xavier_$(date +\%Y\%m\%d).log"
mkdir -p logs

echo "=== Run started at $(date) ===" >> "$LOG_FILE"
PYTHONPATH=. python3 src/main.py --provider XAI --post-to-twitter >> "$LOG_FILE" 2>&1
echo "=== Run completed at $(date) ===" >> "$LOG_FILE"
