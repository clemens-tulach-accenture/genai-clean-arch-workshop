#!/usr/bin/env bash
set -e
MODE="${APP_MODE:-http}"
if [ "$MODE" = "http" ]; then
  exec uvicorn app.server:app --host 0.0.0.0 --port 8000
elif [ "$MODE" = "mcp" ]; then
  exec python -m app.mcp_server
else
  echo "Unknown APP_MODE: $MODE"; exit 1
fi
