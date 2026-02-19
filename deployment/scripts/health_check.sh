#!/usr/bin/env bash
set -e

HOST="${HOST:-localhost}"
PORT="${PORT:-8000}"
URL="http://${HOST}:${PORT}/health"

echo "Checking health at ${URL}..."

if curl -sf "${URL}" > /dev/null; then
    echo "Service is healthy."
    exit 0
else
    echo "Health check failed."
    exit 1
fi
