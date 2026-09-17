#!/usr/bin/env bash
# RC.14 boundary control for scripts/forensics/check_forbidden_live_core_db_access.py
#
# Purpose: separate two questions the round must answer honestly.
#   Q1  Did any command open the *protected* production Core DB set?  (policy §1.2)
#   Q2  Does the guard classify the round's command log as clean?
#
# The guard's PRODUCTION_CORE_PATH_PATTERNS[0] is `wechat-hub-f-live[/\\]+core-data`,
# which matches the *whole* core-data subtree, while policy §1.2 protects only
# core-data/core/wechat_core.sqlite(+wal/shm) and explicitly lists other stores as
# "out of scope - do not over-block".  This control measures that gap.
#
# Run from the deploy repo root.  Every control is a static text classification;
# nothing here touches the host.

set -u
GUARD="scripts/forensics/check_forbidden_live_core_db_access.py"
PY="C:/Users/YING/AppData/Local/Programs/Python/Python312/python.exe"

run() {
  local label="$1"; local expect="$2"; local cmd="$3"
  "$PY" "$GUARD" --command "$cmd" >/dev/null 2>&1
  local rc=$?
  local actual="PASS"; [ "$rc" -ne 0 ] && actual="FAIL"
  local mark="OK"; [ "$actual" != "$expect" ] && mark="DIVERGENCE"
  printf '%-8s %-6s expect=%-4s actual=%-4s  %s\n' "$mark" "$label" "$expect" "$actual" "$cmd"
}

echo "=== POSITIVE controls: protected set must FAIL ==="
run P1 FAIL "sqlite3 /mnt/user/appdata/wechat-hub-f-live/core-data/core/wechat_core.sqlite 'PRAGMA integrity_check;'"
run P2 FAIL "sha256sum /mnt/user/appdata/wechat-hub-f-live/core-data/core/wechat_core.sqlite-wal"
run P3 FAIL "cat /mnt/user/appdata/wechat-hub-f-live/core-data/core/wechat_core.sqlite-shm"
run P4 FAIL "cp /mnt/user/appdata/wechat-hub-f-live/core-data/core/wechat_core.sqlite /tmp/x.sqlite"

echo
echo "=== NEGATIVE controls: policy §1.4 allowed operations must PASS ==="
run N1 PASS "curl -fsS 'http://127.0.0.1:18082/health'"
run N2 PASS "ls -la /mnt/user/appdata/wechat-hub-f-live/core-data/core/"
run N3 PASS "docker inspect wechat-hub-f-live-core"
run N4 PASS "docker ps -a --format '{{.Names}}'"

echo
echo "=== POLICY-BOUNDARY controls: out-of-scope stores per policy §1.2 ==="
echo "    (policy: 'Out of scope (must stay out of scope - do not over-block)')"
run B1 PASS "sqlite3 \"file:/mnt/user/appdata/wechat-hub-f-live/core-data/accounts/f-live-a/memory/wechat_memory.sqlite?mode=ro\" 'select 1'"
run B2 PASS "sqlite3 \"file:/mnt/user/appdata/wechat-hub-f-live/core-data/accounts/f-live-a/wechat-decrypt/decrypted/message/media_0.db?mode=ro\" 'select 1'"
run B3 PASS "sqlite3 \"file:/mnt/user/appdata/wechat-hub-f-live/agent-data/wechat-agent.sqlite?mode=ro\" 'select 1'"

echo
echo "=== Bare protected basename mentioned but never opened ==="
run M1 FAIL "echo 'wechat_core.sqlite'"
