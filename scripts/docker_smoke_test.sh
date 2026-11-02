#!/usr/bin/env bash
# Starts the Docker Compose stack, checks the API, and always shuts it down again.
# Used by GitHub Actions and locally:  bash scripts/docker_smoke_test.sh
# Uses port 8000, or API_PORT if set (e.g. API_PORT=8001 when a local server runs on 8000).
set -euo pipefail

# Own project name: the smoke test only creates and deletes its own containers and volume,
# never a stack (and its data) you started yourself with `docker compose up`.
export COMPOSE_PROJECT_NAME=cognitive_os_smoke
export API_PORT="${API_PORT:-8000}"
API="http://127.0.0.1:${API_PORT}"
WAIT_SECONDS=60

cleanup() {
  status=$?
  if [ "$status" -ne 0 ]; then
    echo "Smoke test failed. API and database logs:"
    docker compose logs api db || true
  fi
  docker compose down --volumes
  exit "$status"
}
trap cleanup EXIT

if lsof -nP -iTCP:"$API_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $API_PORT is already in use. Stop the local API or set API_PORT to a free port."
  exit 1
fi

docker compose up --build --detach

# Compose reports the container as started about a second before uvicorn accepts requests: retry.
for second in $(seq 1 "$WAIT_SECONDS"); do
  if curl --silent --fail --output /dev/null "$API/docs"; then
    echo "API ready after ${second} s"
    break
  fi
  if [ "$second" -eq "$WAIT_SECONDS" ]; then
    echo "API did not answer within ${WAIT_SECONDS} s"
    exit 1
  fi
  sleep 1
done

expect() {
  local expected=$1 description=$2; shift 2
  local actual
  actual=$(curl --silent --output /dev/null --write-out "%{http_code}" "$@")
  if [ "$actual" != "$expected" ]; then
    echo "FAIL: $description: expected $expected, got $actual"
    exit 1
  fi
  echo "ok: $description ($actual)"
}

expect 200 "API docs page" "$API/docs"
expect 200 "stats from the container database" "$API/api/stats/summary"
expect 403 "foreign Host header (DNS rebinding)" -H "Host: attacker.example" "$API/api/stats/summary"
expect 403 "other website as Origin" -H "Origin: https://evil.example" "$API/api/stats/summary"
echo "Smoke test passed."
