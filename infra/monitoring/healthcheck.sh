#!/usr/bin/env sh
set -eu
API_URL="${API_URL:-http://127.0.0.1:8000/health}"
WEB_URL="${WEB_URL:-http://127.0.0.1:4321/}"

curl -fsS "$API_URL" >/dev/null
curl -fsS "$WEB_URL" >/dev/null
printf 'healthcheck ok
'
