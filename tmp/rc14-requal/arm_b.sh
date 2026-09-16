#!/bin/bash
# RC.14 EFB shutdown requalification - ARM B (supplementary instrument arm).
# Uses the host-side mark fixture (SHA256 pinned in the taskbook), which reuses
# the FROZEN in-image probe module verbatim. Image bytes unmodified.
# Frozen gate-runner profile verbatim, including startup_healthcheck: true.
# Arm B does NOT carry the gate verdict; it validates the Arm A derivation and
# supplies the five absolute monotonic marks plus the post-exit tail.
set -u
IMAGE="ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241"
RUNS=${RUNS:-3}
T=2
BASE=/root/rc14-requal
OUT=$BASE/armB.json
FIX=$BASE/marks/marks_fixture.py
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
startup_healthcheck: true
bootstrap_mode: at_head
shutdown_master_budget_sec: 1.0
shutdown_slave_drain_budget_sec: 0.75
shutdown_hard_exit: true
shutdown_install_deferred: false
YAML
}

fail() {
  echo "ARM_B_FAIL: $1"
  printf '{"gate":"FAIL","arm":"B","error":"%s"}\n' "$1" > "$OUT"
  exit 1
}

ROWS=""
for i in $(seq 1 "$RUNS"); do
  D=$(mktemp -d "$BASE/tmp/b${i}-XXXXXX") || fail "mktemp"
  write_profile "$D"
  mkdir -p "$D/marks"
  cp "$FIX" "$D/marks/marks_fixture.py" || fail "fixture copy"
  N="rc14-requal-b${i}-$(date +%s%N | md5sum | cut -c1-8)"
  docker run -d --name "$N" --label rc14.requal.arm=b --network none \
    --volume "$D:/qualification" --entrypoint python "$IMAGE" \
    /qualification/marks/marks_fixture.py --marks /qualification/marks.json \
    --profile /qualification/profile/blueset.wechat.linux/config.yaml \
    --data-dir /qualification/data \
    --shutdown-evidence /qualification/shutdown-evidence.json \
    --core-evidence /qualification/core-evidence.json \
    --ready /qualification/ready.json >/dev/null || fail "docker run run $i"
  ok=0
  for _n in $(seq 1 150); do
    [ -f "$D/ready.json" ] && { ok=1; break; }
    s=$(docker inspect -f '{{.State.Status}}' "$N" 2>/dev/null || echo missing)
    [ "$s" = running ] || { docker logs "$N" 2>&1 | tail -30; docker rm -f "$N" >/dev/null 2>&1; fail "probe exited before ready run $i"; }
    sleep 0.1
  done
  [ "$ok" = 1 ] || { docker rm -f "$N" >/dev/null 2>&1; fail "ready timeout run $i"; }
  sleep 0.5
  docker events --filter container="$N" --format '{{json .}}' > "$D/events.jsonl" 2>&1 &
  EP=$!
  sleep 0.4
  docker wait "$N" > "$D/wait.rc" 2>&1 &
  WP=$!
  T0N=$(date +%s%N)
  docker stop -t "$T" "$N" >/dev/null 2>&1; SRC=$?
  T1N=$(date +%s%N)
  for _n in $(seq 1 120); do kill -0 "$WP" 2>/dev/null || break; sleep 0.05; done
  T2N=$(date +%s%N)
  kill "$EP" 2>/dev/null; wait "$EP" 2>/dev/null

  INS=$(docker inspect "$N")
  EC=$(echo "$INS" | jq -r '.[0].State.ExitCode')
  OOM=$(echo "$INS" | jq -r '.[0].State.OOMKilled')
  RUN=$(echo "$INS" | jq -r '.[0].State.Running')
  PIDV=$(echo "$INS" | jq -r '.[0].State.Pid')
  WRC=$(tr -d '\r\n' < "$D/wait.rc" 2>/dev/null)
  DIEN=$(grep -m1 '"Action":"die"' "$D/events.jsonl" 2>/dev/null | jq -r '.timeNano // empty')
  KILLN=$(grep -m1 '"Action":"kill"' "$D/events.jsonl" 2>/dev/null | jq -r '.timeNano // empty')
  [ -n "$DIEN" ] || fail "no die event run $i"
  KEV=0; [ -n "$KILLN" ] && KEV=1
  SE=$D/shutdown-evidence.json; CE=$D/core-evidence.json; MK=$D/marks.json
  [ -f "$SE" ] || { docker rm -f "$N" >/dev/null 2>&1; fail "no shutdown evidence run $i"; }
  [ -f "$CE" ] || { docker rm -f "$N" >/dev/null 2>&1; fail "no core evidence run $i"; }
  [ -f "$MK" ] || { docker rm -f "$N" >/dev/null 2>&1; fail "no marks file run $i"; }

  PROC=$(jq -r '.elapsed_sec' "$SE")
  MSIG=$(jq -r '.signal_received_monotonic' "$MK")
  MRUN=$(jq -r '.coordinator_run_start_monotonic' "$MK")
  MSUP=$(jq -r '.delivery_suppressed_monotonic' "$MK")
  MCK=$(jq -r '.checkpoint_flush_completed_monotonic' "$MK")
  MLG=$(jq -r '.ledger_flush_completed_monotonic' "$MK")
  MEX=$(jq -r '.exit_requested_monotonic' "$MK")
  MRT=$(jq -r '.realtime_at_start' "$MK")
  MMA=$(jq -r '.monotonic_at_start' "$MK")
  BPROC=$(awk -v a="$MEX" -v b="$MSIG" 'BEGIN{printf "%.6f", a-b}')
  SUP=$(awk -v a="$MSUP" -v b="$MSIG" 'BEGIN{printf "%.6f", a-b}')
  CK=$(awk -v a="$MCK" -v b="$MSIG" 'BEGIN{printf "%.6f", a-b}')
  LG=$(awk -v a="$MLG" -v b="$MSIG" 'BEGIN{printf "%.6f", a-b}')
  EXITOFF=$(awk -v a="$MEX" -v b="$MSIG" 'BEGIN{printf "%.6f", a-b}')
  SIGLAG=$(awk -v a="$MRUN" -v b="$MSIG" 'BEGIN{printf "%.6f", a-b}')
  MEXRT=$(awk -v a="$MRT" -v b="$MMA" -v c="$MEX" 'BEGIN{printf "%.0f", (a + (c-b))*1000000000}')
  DIE=$(awk -v a="$DIEN" -v b="$T0N" 'BEGIN{printf "%.6f", (a-b)/1000000000}')
  CLI=$(awk -v a="$T1N" -v b="$T0N" 'BEGIN{printf "%.6f", (a-b)/1000000000}')
  TAIL=$(awk -v a="$DIEN" -v b="$MEXRT" 'BEGIN{printf "%.6f", (a-b)/1000000000}')
  DRIFT=$(awk -v a="$MEXRT" -v b="$T0N" -v c="$BPROC" 'BEGIN{printf "%.6f", (a-b)/1000000000 - c}')

  CHK=""
  [ "$EC" = 0 ] || CHK="$CHK exit_code"
  [ "$RUN" = false ] || CHK="$CHK still_running"
  [ "$PIDV" = 0 ] || CHK="$CHK pid_nonzero"
  [ "$OOM" = false ] || CHK="$CHK oom_killed"
  [ "$SRC" = 0 ] || CHK="$CHK stop_rc"
  [ "$WRC" = 0 ] || CHK="$CHK wait_rc"
  [ "$KEV" = 0 ] || CHK="$CHK kill_event"
  jq -e '.exit_code == 0' "$SE" >/dev/null || CHK="$CHK ev_exit_code"
  jq -e '.delivery_suppressed == true' "$SE" >/dev/null || CHK="$CHK delivery_suppressed"
  jq -e '([.slave_drain[].detail.checkpoint_flushed] | all)' "$SE" >/dev/null || CHK="$CHK checkpoint_flushed"
  jq -e '([.slave_drain[].detail.ledger_wal_checkpointed] | all)' "$SE" >/dev/null || CHK="$CHK ledger_wal_checkpointed"
  jq -e '([.slave_drain[].detail.checkpoint_cursor] | all(. == 272548))' "$SE" >/dev/null || CHK="$CHK checkpoint_cursor"
  jq -e '[.checkpoint_requests[].processed_through_cursor] | index(272548) != null' "$CE" >/dev/null || CHK="$CHK core_checkpoint_272548"

  cp "$SE" "$BASE/evidence/armB-run${i}-shutdown.json"
  cp "$CE" "$BASE/evidence/armB-run${i}-core.json"
  cp "$MK" "$BASE/evidence/armB-run${i}-marks.json"

  R=$(jq -n --argjson run "$i" --argjson proc "$PROC" --argjson bproc "$BPROC" --argjson die "$DIE" \
       --argjson cli "$CLI" --argjson sup "$SUP" --argjson ck "$CK" --argjson lg "$LG" \
       --argjson exoff "$EXITOFF" --argjson siglag "$SIGLAG" --argjson tail "$TAIL" \
       --argjson drift "$DRIFT" --argjson ec "$EC" --argjson kev "$KEV" --arg chk "$CHK" \
       '{run:$run, frozen_elapsed_sec:$proc, instrumented_process_sec:$bproc,
         container_die_sec:$die, cli_return_sec:$cli,
         mark_signal_to_run_start_sec:$siglag, mark_delivery_suppressed_sec:$sup,
         mark_checkpoint_flush_completed_sec:$ck, mark_ledger_flush_completed_sec:$lg,
         mark_exit_requested_sec:$exoff, post_exit_request_to_die_sec:$tail,
         derived_vs_instrumented_delta_sec:$drift,
         exit_code:$ec, kill_event:($kev==1), checks_failed:$chk}')
  ROWS="$ROWS$R,"
  echo "runB $i proc=$PROC inst=$BPROC die=$DIE cli=$CLI sup=$SUP ck=$CK lg=$LG exoff=$EXOFF tail=$TAIL drift=$DRIFT exit=$EC chk=[$CHK]"
  docker rm -f "$N" >/dev/null 2>&1
  rm -rf "$D"
done

ORPH=$(docker ps -aq --filter label=rc14.requal.arm=b | wc -l | tr -d ' ')
J="[${ROWS%,}]"
jq -n --arg img "$IMAGE" --argjson runs "$J" --argjson orph "$ORPH" \
  '{arm:"B", role:"SUPPLEMENTARY_INSTRUMENT_VALIDATION", carries_gate_verdict:false,
    image:$img, run_count:($runs|length), runs:$runs, orphan_container_count:$orph}' > "$OUT"
echo "ARM_B_DONE orphans=$ORPH"
jq -c '{run_count, orphan_container_count}' "$OUT"
