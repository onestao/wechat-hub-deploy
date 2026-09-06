# WeChat Hub Canary / H2 Host-Side Observability Toolkit

Host-side, strictly read-only evidence tooling for the RC.5 Full-Chat PIDs
canary (and future H2 long-window resource profiling) of the WeChat Hub
`agent-wechat` container.

Verdict logic maps 1:1 onto the PASS criteria in
`docs/P0_RC4_FULL_CHAT_PIDS_CANARY_GATE.md` (section 6) and the log-phrase /
auth-freshness clarifications in `docs/P0_RC4_FULL_CHAT_PIDS_CANARY_ERRATA.md`.

## Files

| File | Purpose |
| --- | --- |
| `wechat_cgroup_sample.sh` | One sample = one JSONL line on stdout. |
| `wechat_canary_run.sh` | Loops the sampler at `--interval` for `--duration`, appends JSONL to `--output`, flushes safely on INT/TERM. |
| `summarize_canary.py` | Baseline/peak/end statistics + window deltas + PASS-CANDIDATE / FAIL / INCOMPLETE verdict. |

Related but separate: `scripts/observability/` is an earlier generic toolkit
kept for its own session's evidence; this directory is the canary-specific
toolset aligned with the RC.5 gate documents.

## `/proc` race policy (explicit, tested, non-masking)

`/proc` read failures during a sampling sweep are classified by the sampler
into two separate counters (`tasks` in each JSONL sample):

- `proc_race_count` — **tolerable transient race**: the pid directory no
  longer exists at the immediate recheck (the process exited naturally
  mid-sweep), or the read succeeds on one immediate retry (torn read of an
  exiting process).
- `proc_read_error_count` — **never tolerable**: the pid is still present but
  the read keeps failing (unexplained). Any read error in any sample makes
  the summarizer verdict INCOMPLETE regardless of the race tolerance.

The summarizer's `--max-proc-races` tolerance therefore covers vanish-type
races only, is an explicit parameter, and is recorded in every summary inside
the `proc_race_policy` block together with the observed totals
(`races_total`, `samples_with_races`, `max_races_in_single_sample`,
`read_errors_total`, and whether the evidence predates the recheck policy).

**Approved tolerance values** (do not relax to an arbitrary large number):

| Window | Samples | Tolerance | Derivation |
| --- | --- | --- | --- |
| 30-min final canary | 60 | 8 | empirically observed vanish-race count on two independent final-artifact windows (R5 baseline 66 samples: 8; final canary 60 samples: 8, spread ≤ 2 per sample) |
| 6h H2 soak | 360 | 48 | same policy, linearly scaled: 8 races / 60 samples = 0.134 per sampling round; races are host-churn driven and accrue per round, not per wall-clock hour |

**Non-masking guarantee:** races never mask real failure signals. EAGAIN,
thread-constructor failures, OOM / oom_kill, `pids.events` fork rejections,
watchdog kills/restarts, monotonic task growth, zombie accumulation,
pids.current peak-at-limit, auth continuity, and digest/wxid identity are
independent FAIL criteria that take precedence over the race tolerance
(FAIL > INCOMPLETE > PASS-CANDIDATE). This property is covered by dedicated
tests (`tests/canary/test_summarize_canary.py::test_races_within_tolerance_*`).

## Security model

Allowed (read-only): `docker inspect`, `docker logs`, reads under `/proc`,
reads under `/sys/fs/cgroup` (cgroup v2 only), `date`, `awk`, `tr`, `cat`,
`grep`-class text tools, `python` (only for optional `--status-url` fetch).

Refused by construction and by an in-script guard:

- No `docker exec` — processes are never created inside the container cgroup
  (would skew every measurement; prohibited by the P0 gate document).
- No `docker update/restart/stop/kill/rm/pause`, no process signals
  (`kill`/`pkill`/`killall`), no cgroup writes, no `rm`/`prune`.
- Any invocation containing a destructive token, or any run with
  `WECHAT_CANARY_ALLOW_DESTRUCTIVE` set, exits with code 3 before doing
  anything (see the `BEGIN/END DESTRUCTIVE GUARD` block).
- The runner's only signal use is `kill "$sleep_pid"` on its own backgrounded
  `sleep` child, solely to make INT/TERM interrupts responsive.

Both shell scripts carry a `ps -T`-free implementation: task counts come from
traversing `/proc/[0-9]*` and matching the cgroup v2 path (field 3) exactly;
per-task thread counts come from `/proc/PID/status` `Threads:`.

## Usage

Run on the Unraid host (must see the host's `/proc` and `/sys/fs/cgroup`;
do not run inside a container):

```bash
# RC.5 watchdog pre-gate (5-10 min)
scripts/canary/wechat_canary_run.sh \
    --output evidence.jsonl --duration 600 --interval 30 \
    --container <agent-wechat-container> \
    --status-url http://127.0.0.1:<port>/api/status/auth

# RC.5 Full-Chat canary (>= 30 min, start only after view=Chat, status=logged_in)
scripts/canary/wechat_canary_run.sh \
    --output evidence.jsonl --duration 1800 --interval 30 \
    --container <agent-wechat-container> \
    --runtime-container <runtime-container> \
    --status-url http://127.0.0.1:<port>/api/status/auth \
    --run-id rc5-fullchat-$(date -u +%Y%m%dT%H%M%SZ)

# H2 long profiling (only when the operator resumes H2; see
# docs/RC5_H2_PREFLIGHT.md for the full execution package)
# NOTE: --duration must exceed the 21600 s evidence window because the runner
# bounds round STARTS and each round costs interval + ~0.5 s sampler runtime;
# 21600/60 would yield ~357 samples / ~21.5 ks and fail both minimums.
scripts/canary/wechat_canary_run.sh \
    --output h2.jsonl --duration 22600 --interval 60 --profile h2 \
    --container <agent-wechat-container> \
    --runtime-container <runtime-container> \
    --status-url <verified-GET-only-auth-status-url>

# Verdict (advisory only; never promotes)
scripts/canary/summarize_canary.py evidence.jsonl \
    --expected-pids-limit 512 \
    --expected-agent-wechat-digest <AGENTWECHAT_DIGEST> \
    --expected-runtime-digest <RUNTIME_DIGEST> \
    --expected-wxid <EXPECTED_WXID>
scripts/canary/summarize_canary.py h2.jsonl \
    --minimum-duration 21600 --minimum-samples 360 \
    --max-proc-races 48
```

Interrupting the runner with Ctrl+C or TERM stops cleanly; every completed
sample is already flushed (each line is appended atomically once fully built).

Watchdog counter patterns default to the RC.4-observed upstream phrases
(`Killed WeChat pid=`, `WeChat process disappeared`, `Spawned WeChat`,
`unresponsive`, `pthread_create` + `EAGAIN`, `thread constructor failed`) and
can be overridden via `--pattern-*` flags. `--watchdog-log-file` replaces
`docker logs` (used by the fixture tests; also useful for post-hoc log
analysis). `--container-init-pid` + friends replace `docker inspect`
(offline/fixture mode).

## JSONL sample schema (`wechat-hub.canary.sample/v1`)

Every line contains:

- `timestamp`, `run` (`id`, `profile`)
- `container`: name, id, state, init pid, `host_config_pids_limit`,
  `docker_oom_killed`, `started_at`
- `cgroup`: v2 path (exact-match root for task enumeration) and resolved dir
- `collection`: mode (`live` / `offline-fixture`), log source, roots used
- `pids`: `current`, `max` (number or `"max"`), `events_max_hit` — cumulative
  cgroup counters
- `memory`: `current_bytes`, `max_bytes`, `events_oom`, `events_oom_kill`
- `tasks`: `grand_total` (`processes`, `threads`), `zombie_count`,
  `proc_race_count` (vanish-type / recovered-torn-read races),
  `proc_read_error_count` (pid present but persistently unreadable — never
  tolerated), per-component `processes`/`threads` for `wechat`,
  `wechatappex`, `wxplayer`, `wxocr`, `crashpad`, `agent-server`, `other`
- `watchdog`: cumulative `unresponsive_kill`, `killed_wechat`,
  `process_disappeared`, `spawned_wechat`, `pthread_create_eagain`,
  `thread_constructor_failed`
- `auth`: `status_url`, `reported_auth_status` (raw endpoint report),
  `current_ui_observation` (always `"unknown"` — a fresh UI truth is
  unobtainable host-side without `docker exec`), `current_ui_fresh` (always
  `false`). Reported `logged_in` is NOT treated as proof of the current Chat
  UI (errata section 2.3: persisted FSM context can be stale when
  `identified.main_window` is unset).

All counters are cumulative over the container lifetime; the summarizer
derives window deltas from the first and last samples.

## Verdict mapping (gate document section 6)

| Gate criterion | Summarizer check |
| --- | --- |
| 1. `PidsLimit == 512` throughout | observed `pids.max` / `host_config_pids_limit` must equal `--expected-pids-limit`; `"max"`/unbounded fails |
| 2. `pids.events max` delta == 0 | endpoint delta |
| 3. zero `pthread_create EAGAIN` | log-counter delta |
| 4. zero `thread constructor failed` | log-counter delta |
| 5. no health-monitor kill/restart | kill counters + `spawned_wechat` delta |
| 6. auth stays `view=Chat, status=logged_in` | per-sample reported auth (INCOMPLETE if never sampled via `--status-url`) |
| 7. task counts oscillate, no monotonic growth | monotonic check on `pids.current` and aggregated threads; peak-at-limit fails, peak near limit warns |
| 8. no accumulating zombies/dead generations | net zombie growth (`--fail-zombie-growth`) and peak (`--fail-zombie-max`) |
| 9. `memory.events oom/oom_kill` == 0 | deltas + docker `OOMKilled` flag |
| 10. data intact | operator check, out of scope for a read-only sampler |

Evidence-integrity rules: window shorter than `--minimum-duration` (default
1800 s), fewer than `--minimum-samples`, `/proc` vanish-races above the
explicit `--max-proc-races` tolerance (default 0; approved values in the
race-policy section above), any `/proc` read error (pid present but
persistently unreadable), or missing auth samples yield INCOMPLETE. The
chosen tolerance and the observed race distribution are always recorded in
the summary's `proc_race_policy` block.

Precedence: FAIL > INCOMPLETE > PASS-CANDIDATE. The summary always reports
`"promotion_performed": false` and marks the verdict as advisory — this tool
never promotes, resumes H2, or unlocks any gate.

## Tests

`tests/canary/` runs entirely on synthetic fixtures (mock docker executable,
fabricated `/proc` and cgroup trees) — no docker daemon and no real container
are touched. `pytest tests/canary` covers stable/leak/restart/OOM/EAGAIN/race
scenarios for the summarizer, sampler behavior (live + offline modes,
component classification, zombie exclusion, race tolerance), runner
duration/interval/flush semantics, and the destructive-mode guard. Test
scratch data stays inside the project at `.local/tmp/canary-tests/` and is
removed after each run.
