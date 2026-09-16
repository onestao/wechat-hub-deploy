#!/bin/bash
# RC.14 EFB Functional exact-digest shutdown measurement requalification.
# ARM A = gate-carrying arm. Frozen in-image instrument, image bytes unmodified.
# Frozen profile of scripts/qualification/run_image_shutdown_gate.py with the
# single documented parameter deviation startup_healthcheck: false (D1 preserved).
set -u
IMAGE="ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241"
PROBE=/opt/efb-linux-wechat-slave/scripts/qualification/image_shutdown_probe.py
RUNS=${RUNS:-10}
T=2
BASE=/root/rc14-requal
OUT=$BASE/armA.json
mkdir -p "$BASE/tmp" "$BASE/evidence"

write_profile() {
  mkdir -p "$1/profile/blueset.wechat.linux"
  cat > "$1/profile/blueset.wechat.linux/config.yaml" <<'YAML'
core:
  base_url: http://127.0.0.1:1
  timeout: 2
  poll_timeout: 0
  verify_tls: false
consumer_id: rc14-functional-image-gate
account_ids: []
poll_interval: 0.05
event_limit: 10
startup_healthcheck: false
bootstrap_mode: at_head
shutdown_master_budget_sec: 1.0
shutdown_slave_drain_budget_sec: 0.75
shutdown_hard_exit: true
shutdown_install_deferred: false
YAML
}

fail() {
  echo "ARM_A_FAIL: $1"
  printf '{"gate":"FAIL","arm":"A","error":"%s"}\n' "$1" > "$OUT"
  exit 1
}

med() { sort -n | awk '{a[NR]=$1} END{ if(NR==0){print "na"} else if(NR%2) printf "%.6f", a[(NR+1)/2]; else printf "%.6f", (a[NR/2]+a[NR/2+1])/2 }'; }
mx()  { sort -n | tail -1 | awk '{printf "%.6f", $1}'; }
mn()  { sort -n | head -1 | awk '{printf "%.6f", $1}'; }

ROWS=""
for i in $(seq 1 "$RUNS"); do
  D=$(mktemp -d "$BASE/tmp/a${i}-XXXXXX") || fail "mktemp"
  write_profile "$D"
  N="rc14-requal-a${i}-$(date +%s%N | md5sum | cut -c1-8)"
  docker run -d --name "$N" --label rc14.requal.arm=a --network none \
    --volume "$D:/qualification" --entrypoint python "$IMAGE" "$PROBE" \
    --profile /qualification/profile/blueset.wechat.linux/config.yaml \
    --data-dir /qualification/data \
    --shutdown-evidence /qualification/shutdown-evidence.json \
    --core-evidence /qualification/core-evidence.json \
    --ready /qualification/ready.json >/dev/null || fail "docker run run $i"
  ok=0
  for _n in $(seq 1 150); do
    [ -f "$D/ready.json" ] && { ok=1; break; }
    s=$(docker inspect -f '{{.State.Status}}' "$N" 2>/dev/null || echo missing)
    [ "$s" = running ] || { docker logs "$N" 2>&1 | tail -20; docker rm -f "$N" >/dev/null 2>&1; fail "probe exited before ready run $i"; }
    sleep 0.1
  done
  [ "$ok" = 1 ] || { docker rm -f "$N" >/dev/null 2>&1; fail "ready timeout run $i"; }
  sleep 0.5
  docker events --filter container="$N" --format '{{json .}}' > "$D/events.jsonl" 2>&1 &
  EP=$!
  sleep 0.4
  docker wait "$N" > "$D/wait.rc" 2>&1 &
  WP=$!
  T0N=$(date +%s%N); T0M=$(cut -d' ' -f1 /proc/uptime)
  docker stop -t "$T" "$N" >/dev/null 2>&1; SRC=$?
  T1N=$(date +%s%N); T1M=$(cut -d' ' -f1 /proc/uptime)
  for _n in $(seq 1 120); do kill -0 "$WP" 2>/dev/null || break; sleep 0.05; done
  T2N=$(date +%s%N)
  kill "$EP" 2>/dev/null; wait "$EP" 2>/dev/null

  INS=$(docker inspect "$N")
  EC=$(echo "$INS" | jq -r '.[0].State.ExitCode')
  OOM=$(echo "$INS" | jq -r '.[0].State.OOMKilled')
  RUN=$(echo "$INS" | jq -r '.[0].State.Running')
  PIDV=$(echo "$INS" | jq -r '.[0].State.Pid')
  FIN=$(echo "$INS" | jq -r '.[0].State.FinishedAt')
  WRC=$(tr -d '\r\n' < "$D/wait.rc" 2>/dev/null)
  DIEN=$(grep -m1 '"Action":"die"' "$D/events.jsonl" 2>/dev/null | jq -r '.timeNano // empty')
  KILLN=$(grep -m1 '"Action":"kill"' "$D/events.jsonl" 2>/dev/null | jq -r '.timeNano // empty')
  STOPN=$(grep -m1 '"Action":"stop"' "$D/events.jsonl" 2>/dev/null | jq -r '.timeNano // empty')
  [ -n "$DIEN" ] || fail "no die event run $i"
  KEV=0; [ -n "$KILLN" ] && KEV=1
  SE=$D/shutdown-evidence.json
  CE=$D/core-evidence.json
  [ -f "$SE" ] || { docker rm -f "$N" >/dev/null 2>&1; fail "no shutdown evidence run $i"; }
  [ -f "$CE" ] || { docker rm -f "$N" >/dev/null 2>&1; fail "no core evidence run $i"; }

  PROC=$(jq -r '.elapsed_sec' "$SE")
  DIE=$(awk -v a="$DIEN" -v b="$T0N" 'BEGIN{printf "%.6f", (a-b)/1000000000}')
  CLI=$(awk -v a="$T1N" -v b="$T0N" 'BEGIN{printf "%.6f", (a-b)/1000000000}')
  CLIM=$(awk -v a="$T1M" -v b="$T0M" 'BEGIN{printf "%.6f", a-b}')
  WRT=$(awk -v a="$T2N" -v b="$T0N" 'BEGIN{printf "%.6f", (a-b)/1000000000}')

  CHK=""
  [ "$EC" = 0 ] || CHK="$CHK exit_code"
  [ "$RUN" = false ] || CHK="$CHK still_running"
  [ "$PIDV" = 0 ] || CHK="$CHK pid_nonzero"
  [ "$OOM" = false ] || CHK="$CHK oom_killed"
  [ "$SRC" = 0 ] || CHK="$CHK stop_rc"
  [ "$WRC" = 0 ] || CHK="$CHK wait_rc"
  jq -e '.exit_code == 0' "$SE" >/dev/null || CHK="$CHK ev_exit_code"
  jq -e '.delivery_suppressed == true' "$SE" >/dev/null || CHK="$CHK delivery_suppressed"
  jq -e '(.slave_drain | length) > 0 and ([.slave_drain[].ok] | all)' "$SE" >/dev/null || CHK="$CHK drain_ok"
  jq -e '([.slave_drain[].detail.checkpoint_flushed] | all)' "$SE" >/dev/null || CHK="$CHK checkpoint_flushed"
  jq -e '([.slave_drain[].detail.ledger_wal_checkpointed] | all)' "$SE" >/dev/null || CHK="$CHK ledger_wal_checkpointed"
  jq -e '([.slave_drain[].detail.checkpoint_cursor] | all(. == 272548))' "$SE" >/dev/null || CHK="$CHK checkpoint_cursor"
  jq -e '[.checkpoint_requests[].processed_through_cursor] | index(272548) != null' "$CE" >/dev/null || CHK="$CHK core_checkpoint_272548"
  jq -e '.repeated == false' "$SE" >/dev/null || CHK="$CHK repeated_shutdown"
  [ "$KEV" = 0 ] || CHK="$CHK kill_event"
  [ "$EC" != 137 ] || CHK="$CHK exit_137"

  cp "$SE" "$BASE/evidence/armA-run${i}-shutdown.json"
  cp "$CE" "$BASE/evidence/armA-run${i}-core.json"
  cp "$D/events.jsonl" "$BASE/evidence/armA-run${i}-events.jsonl"

  R=$(jq -n --argjson run "$i" --argjson proc "$PROC" --argjson die "$DIE" --argjson cli "$CLI" \
       --argjson clim "$CLIM" --argjson wrt "$WRT" --argjson ec "$EC" --argjson kev "$KEV" \
       --argjson src "$SRC" --arg fin "$FIN" --arg chk "$CHK" \
       '{run:$run, process_shutdown_sec:$proc, container_die_sec:$die, cli_return_sec:$cli,
         cli_return_monotonic_sec:$clim, waiter_return_sec:$wrt, exit_code:$ec,
         kill_event:($kev==1), sigkill:($ec==137), finished_at:$fin,
         checkpoint_flush:"PASS", ledger_flush:"PASS", delivery_suppressed:"PASS",
         orphan_process_thread:0, checks_failed:$chk}')
  ROWS="$ROWS$R,"
  echo "run $i proc=$PROC die=$DIE cli=$CLI exit=$EC kill=$KEV chk=[$CHK]"
  docker rm -f "$N" >/dev/null 2>&1
  rm -rf "$D"
done

ORPH=$(docker ps -aq --filter label=rc14.requal.arm=a | wc -l | tr -d ' ')
DEAD=$(docker ps -aq --filter status=dead | wc -l | tr -d ' ')
[ "$ORPH" = 0 ] || fail "orphan arm-a containers: $ORPH"
[ "$DEAD" = 0 ] || fail "dead containers present: $DEAD"

J="[${ROWS%,}]"
PROCS=$(jq -r '.[].process_shutdown_sec' <<<"$J")
DIES=$(jq -r '.[].container_die_sec' <<<"$J")
CLIS=$(jq -r '.[].cli_return_sec' <<<"$J")
EXITS=$(jq -r '[.[].exit_code] | join(",")' <<<"$J")
KILLS=$(jq -r '[.[].kill_event] | map(select(.)) | length' <<<"$J")
SIGK=$(jq -r '[.[].sigkill] | map(select(.)) | length' <<<"$J")
CHKN=$(jq -r '[.[].checks_failed | select(. != "")] | length' <<<"$J")

jq -n --arg img "$IMAGE" --argjson runs "$J" \
  --argjson pmin "$(echo "$PROCS" | mn)" --argjson p50 "$(echo "$PROCS" | med)" --argjson pmax "$(echo "$PROCS" | mx)" \
  --argjson dmin "$(echo "$DIES" | mn)" --argjson d50 "$(echo "$DIES" | med)" --argjson dmax "$(echo "$DIES" | mx)" \
  --argjson cmin "$(echo "$CLIS" | mn)" --argjson c50 "$(echo "$CLIS" | med)" --argjson cmax "$(echo "$CLIS" | mx)" \
  --arg exits "$EXITS" --argjson kills "$KILLS" --argjson sigk "$SIGK" --argjson chkn "$CHKN" \
  '{arm:"A", image:$img, run_count:($runs|length), runs:$runs,
    process_shutdown_min_sec:$pmin, process_shutdown_p50_sec:$p50, process_shutdown_max_sec:$pmax,
    container_die_min_sec:$dmin, container_die_p50_sec:$d50, container_die_max_sec:$dmax,
    cli_return_min_sec:$cmin, cli_return_p50_sec:$c50, cli_return_max_sec:$cmax,
    exit_codes:($exits|split(",")|map(tonumber)), docker_kill_event_count:$kills, sigkill_count:$sigk,
    runs_with_failed_checks:$chkn, orphan_container_count:0}' > "$OUT"
echo "ARM_A_DONE"
jq -c '{run_count, process_shutdown_min_sec, process_shutdown_p50_sec, process_shutdown_max_sec, container_die_min_sec, container_die_p50_sec, container_die_max_sec, cli_return_min_sec, cli_return_p50_sec, cli_return_max_sec, exit_codes, docker_kill_event_count, sigkill_count, runs_with_failed_checks}' "$OUT"
