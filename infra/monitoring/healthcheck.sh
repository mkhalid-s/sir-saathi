#!/usr/bin/env sh
set -eu
API_URL="${API_URL:-http://127.0.0.1:8000/api/ready}"
WEB_URL="${WEB_URL:-}"
CURL_TIMEOUT_SECONDS="${CURL_TIMEOUT_SECONDS:-10}"

if [ -z "$WEB_URL" ]; then
    printf '%s\n' 'WEB_URL must be set to the deployed public HTTPS origin' >&2
    exit 2
fi

curl --fail --silent --show-error --max-time "$CURL_TIMEOUT_SECONDS" "$API_URL" >/dev/null
curl --fail --silent --show-error --max-time "$CURL_TIMEOUT_SECONDS" "$WEB_URL" >/dev/null
printf '%s\n' 'healthcheck ok'
