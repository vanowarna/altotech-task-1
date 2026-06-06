#!/usr/bin/env bash
# Run the full unit-test suite.
#
# Each service has its own top-level `app` package (api, afdd-engine), so the suites
# must run in SEPARATE processes — a single pytest invocation across services hits a
# sys.modules name collision (`app` from one service shadows another). This script
# runs each suite in its own subshell, which is the correct, isolated way.
#
# Usage:
#   pip install -r requirements-dev.txt
#   ./scripts/run_tests.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PASS=0; FAIL=0
run() {
  local name="$1"; shift
  echo "── $name ──"
  if ( "$@" ); then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi
  echo
}

run "shared"    bash -c "cd '$ROOT' && python -m pytest packages/shared/tests -q -p no:cacheprovider"
run "simulator" bash -c "cd '$ROOT/services/edge-simulator' && python -m pytest tests -q -p no:cacheprovider"
run "api"       bash -c "cd '$ROOT/services/api' && python -m pytest tests -q -p no:cacheprovider"
run "engine"    bash -c "cd '$ROOT/services/afdd-engine' && python -m pytest tests -q -p no:cacheprovider"

echo "Suites passed: $PASS, failed: $FAIL"
[ "$FAIL" -eq 0 ]
