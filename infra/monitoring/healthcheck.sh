#!/usr/bin/env sh
set -eu
API_URL="${API_URL:-http://127.0.0.1:8000/api/health}"
WEB_URL="${WEB_URL:-http://127.0.0.1:4321/}"
CURL_TIMEOUT_SECONDS="${CURL_TIMEOUT_SECONDS:-10}"

curl --fail --silent --show-error --max-time "$CURL_TIMEOUT_SECONDS" "$API_URL" >/dev/null
curl --fail --silent --show-error --max-time "$CURL_TIMEOUT_SECONDS" "$WEB_URL" >/dev/null
printf '%s\n' 'healthcheck ok'
