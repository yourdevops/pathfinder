#!/bin/bash
# DevSSP development runner
# Runs web server and worker with interleaved, prefixed logs

set -e
set -m  # Enable job control so background jobs get their own process groups

PYTHON="$1"
WEB_PID_FILE="$2"
WORKER_PID_FILE="$3"

# Colors
CYAN='\033[36m'
YELLOW='\033[33m'
GREEN='\033[32m'
RED='\033[31m'
RESET='\033[0m'

# Track child PIDs
WEB_PID=""
WORKER_PID=""

cleanup() {
    echo ""
    echo -e "${RED}Shutting down...${RESET}"

    # Kill entire process groups (negative PID kills the group)
    if [ -n "$WEB_PID" ] && kill -0 "$WEB_PID" 2>/dev/null; then
        kill -- -"$WEB_PID" 2>/dev/null || kill "$WEB_PID" 2>/dev/null || true
        wait "$WEB_PID" 2>/dev/null || true
    fi

    if [ -n "$WORKER_PID" ] && kill -0 "$WORKER_PID" 2>/dev/null; then
        kill -- -"$WORKER_PID" 2>/dev/null || kill "$WORKER_PID" 2>/dev/null || true
        wait "$WORKER_PID" 2>/dev/null || true
    fi

    rm -f "$WEB_PID_FILE" "$WORKER_PID_FILE"
    echo -e "${GREEN}Stopped.${RESET}"
    exit 0
}

# Set up signal handlers
trap cleanup INT TERM

echo -e "${GREEN}Starting DevSSP...${RESET}"
echo ""

# Start worker with prefixed output
(
    $PYTHON manage.py db_worker --queue-name "*" 2>&1 | while IFS= read -r line; do
        echo -e "${YELLOW}[worker]${RESET} $line"
    done
) &
WORKER_PID=$!
echo "$WORKER_PID" > "$WORKER_PID_FILE"

# Small delay to let worker start first
sleep 0.5

# Start web server with prefixed output
(
    $PYTHON manage.py runserver 2>&1 | while IFS= read -r line; do
        echo -e "${CYAN}[portal]${RESET} $line"
    done
) &
WEB_PID=$!
echo "$WEB_PID" > "$WEB_PID_FILE"

echo -e "${GREEN}Both services running. Press Ctrl+C to stop.${RESET}"
echo ""

# Wait for either process to exit
wait
