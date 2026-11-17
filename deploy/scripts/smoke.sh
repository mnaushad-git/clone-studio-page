#!/usr/bin/env bash
# Read-only checks against a running API; creates no orders. Exits non-zero on any failure.
#
#   deploy/scripts/smoke.sh [base-url]     default: https://api.terrific-bites.trunexus.ai
set -uo pipefail

BASE="${1:-https://api.terrific-bites.trunexus.ai}"
ORIGIN="${FRONTEND_ORIGIN:-https://terrific-bites.trunexus.ai}"
EXPECTED_STAGE="${EXPECTED_STAGE:-staging}"
fail=0

check() {  # name expected-status path
  code="$(curl -s -m 15 -o /dev/null -w '%{http_code}' "$BASE$3")"
  if [[ "$code" == "$2" ]]; then echo "ok    $1 ($code)"; else echo "FAIL  $1: got $code, expected $2"; fail=1; fi
}

check liveness 200 /api/v1/health
check "readiness (database + redis)" 200 /api/v1/readiness
check "catalogue homepage" 200 /api/v1/catalogue/homepage
check "catalogue categories" 200 /api/v1/catalogue/categories
check "api docs hidden in production" 404 /docs
check "api schema hidden in production" 404 /openapi.json
check "admin requires login" 401 /api/v1/admin/auth/me

if curl -s -m 15 "$BASE/api/v1/version" | grep -q "\"deployment_stage\":\"$EXPECTED_STAGE\""; then
  echo "ok    deployment stage is $EXPECTED_STAGE"
else
  echo "FAIL  deployment stage is not $EXPECTED_STAGE"; fail=1
fi

if curl -s -m 15 -D - -o /dev/null -H "Origin: $ORIGIN" "$BASE/api/v1/health" | grep -qi "^access-control-allow-origin: $ORIGIN"; then
  echo "ok    CORS allows $ORIGIN"
else
  echo "FAIL  CORS does not allow $ORIGIN"; fail=1
fi
if curl -s -m 15 -D - -o /dev/null -H "Origin: https://example.com" "$BASE/api/v1/health" | grep -qi '^access-control-allow-origin:'; then
  echo "FAIL  CORS allows an unrelated origin"; fail=1
else
  echo "ok    CORS refuses an unrelated origin"
fi

exit "$fail"
