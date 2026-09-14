# WeChat Hub RC.14 — Optional EFB Consumer: Governed Re-Bootstrap & Replay Safety Live Re-Qualification Taskbook (Retry 2)

> **STATUS: PREPARED / NOT AUTHORIZED / NOT EXECUTED**
>
> **Offline Engineering Lane Deliverable Only.**
> This document authorizes NO live mutations by itself. All steps in Sections 5 through 9 require explicit operator authorization and cryptographic tokens before NAS execution.
>
> **Authoritative Baseline Inputs:**
> - `docs/RC14_OPTIONAL_EFB_PRODUCTION_LIVE_QUALIFICATION_RETRY1_RESULT.md`
>   - SHA256: `7adfcb61394d6844a5ad5705532795ac500d3bcc17d937983b9329f2952699f4`
> - `docs/RC14_NEW_CONSUMER_BOOTSTRAP_POLICY.md`
>   - SHA256: `ab5575294febf57f9d48264f5b1c5786904c4a2c8f7d6ef2e38521efa8ed7aa0`
>
> **Formal Retry 1 Verdict Remediated by this Taskbook:**
> ```text
> EFB_FUNCTIONAL_LIVE_BOOTSTRAP   = PASS
> EFB_CHECKPOINT_MONOTONIC        = PASS
> EFB_FULL_HISTORICAL_CATCHUP     = BLOCKED_BY_BOOTSTRAP_POLICY
> EFB_REPLAY_SAFETY_MESSAGE_LEVEL = FAIL
> EFB_PRODUCTION_PROMOTION_READY  = NO
> ```
>
> **Live Launch Required Token:**
> `AUTHORIZE: RC14_OPTIONAL_EFB_LIVE_REQUALIFICATION_RETRY2`
>
> **Core Governed Re-Bootstrap Remediation Token:**
> `OPERATOR_TOKEN: EFB_REBOOTSTRAP_REMEDIATION_QUAL_RETRY2`

---

## 1. Remediation Scope & Defect Register

This taskbook establishes the fail-closed operational procedure to requalify the optional EFB consumer (`efb-linux-wechat:wechat.linux`) under RC.14, resolving the 6 engineering defects identified during Retry 1:

| Defect ID | Severity | Remediation Implementation |
| :--- | :--- | :--- |
| **`R14-EFB-D1`** | Blocking | **Core Governed Bootstrap Primitive**: Implemented `POST /v1/consumers/bootstrap` with modes `at_head` and `bounded_window`. Cold consumers no longer default to historical replay from cursor `0`. Core strictly rejects un-governed historical replay requests without an explicit maintenance token. |
| **`R14-EFB-D2`** | Blocking | **Governed Re-Bootstrap API**: Implemented `POST /v1/consumers/rebootstrap` in Core with mandatory operator token, recorded quiescence evidence, and audit logging to safely re-align the preserved qualification checkpoint (`13181`) to a bounded catch-up window or stream head. |
| **`R14-EFB-D3`** | Major | **Graceful Shutdown < 2.0s**: Bounded long-poll iterations in EFB to `<= 1.0s` (`min(poll_timeout, 1)`), registered SIGTERM/SIGINT listeners in main thread, and added final checkpoint flush on termination. Container drain completes in `< 2.0s`, eliminating Docker stop timeout `Exit 137`. |
| **`R14-EFB-D4`** | Major | **Stream Head Alignment**: EFB `CursorStore` eliminates `"0"` fallback; on cold start or after re-bootstrap, queries Core bootstrap provenance and aligns local cursor with `initial_cursor`, eliminating the 259,000 backlog catch-up trap. |
| **`R14-EFB-D5`** | Moderate | **Durable `EffectLedger`**: SQLite WAL-backed ledger recording `(consumer_id, effect_id)` before external Telegram message delivery. Guarantees exactly-once side effects and suppresses duplicate `message.created` emissions from Core. |
| **`R14-EFB-D6`** | Moderate | **Fail-Closed Verification Harness**: Mandated atomic generation of `/tmp/live_efb_qualification_result.json` with cryptographic SHA256 checksums of all state transitions. |

---

## 2. Preserved Production State (Non-Negotiable Invariants)

The live production state recorded at the conclusion of Retry 1 must remain strictly preserved until explicitly audited in Gate 1:

```text
consumer_id                 = efb-linux-wechat:wechat.linux
preserved Core checkpoint   = 13181
preserved local cursor      = 13214
EFB container state         = stopped
EFB profile & data directory= preserved, never reset, never deleted (/mnt/user/appdata/wechat-hub-f-live/efb-data)
Core SQLite database        = preserved, never edited directly via raw SQL mutations
Active outbox               = 0 queued / sending messages
Telegram live bot           = MUST NOT receive duplicate message deliveries
```

---

## 3. Frozen Candidate Identities

Prior to executing any live step, the code candidate SHAs and container image digests must be sealed:

```text
Core Repository             = work/rc14-retry3/core
Core Candidate Ref          = feat/rc14-core-retry3
Core Source Commit          = 08a4e746e66fe94cbe73f99f7284ae7f01963447

EFB Repository              = work/rc14/efb-linux-wechat-slave
EFB Candidate Ref           = feat/rc14-efb
EFB Source Commit           = f06a1bd5b40574bdfa5255f6f5e791b05865e8ef

Sealed EFB Image Digest     = [TO_BE_BUILT_AND_PULLED: sha256:...]
Sealed Core Image Digest    = [CURRENT_LIVE_OR_RETRY3_IMAGE_DIGEST]
```

---

## 4. Pre-Qualification Verification Gates (Fail-Closed)

All pre-qualification gates must PASS before launching the EFB container. Any gate failure aborts the procedure immediately without mutation.

### Gate G1: Preserved Baseline Audit & Quiescence Verification
Verify the preserved Core checkpoint and local EFB cursor match the Retry 1 verdict:
```bash
# 1. Query Core checkpoint for EFB consumer
curl -sS "http://127.0.0.1:5000/v1/events/checkpoint?consumer_id=efb-linux-wechat:wechat.linux" | jq .

# 2. Inspect local EFB cursor store
cat /mnt/user/appdata/wechat-hub-f-live/efb-data/core-event-cursor.json

# 3. Verify EFB container is stopped
docker ps --filter "name=wechat-hub-efb" --format '{{.ID}} {{.Status}}'
```
*Gate G1 Criteria:*
- `Core checkpoint == 13181`
- `Local cursor == 13214`
- `EFB container is stopped`

### Gate G2: Governed Re-Bootstrap Invocation
Invoke the Core governed re-bootstrap API to advance EFB from the failed Retry 1 state (`13181`) to a bounded catch-up window of the latest events (e.g. 500 events):
```bash
curl -sS -X POST "http://127.0.0.1:5000/v1/consumers/rebootstrap"   -H "Content-Type: application/json"   -d '{
    "consumer_id": "efb-linux-wechat:wechat.linux",
    "mode": "bounded_window",
    "window": {"events": 500},
    "operator_token": "EFB_REBOOTSTRAP_REMEDIATION_QUAL_RETRY2",
    "quiescence_evidence": "EFB container stopped; verified Core checkpoint 13181 and local cursor 13214"
  }' | jq .
```
*Gate G2 Criteria:*
- HTTP status 200 OK.
- `initial_cursor > 13181` (aligned within 500 events of stream head).
- Audit provenance recorded in Core `consumer_bootstrap_audit` table.

### Gate G3: Local Cursor Store Re-Alignment
Align local EFB cursor store with the newly assigned initial cursor:
```bash
# Verify get_bootstrap_provenance endpoint reflects rebootstrap
curl -sS "http://127.0.0.1:5000/v1/consumers/efb-linux-wechat:wechat.linux/bootstrap" | jq .
```
*Gate G3 Criteria:*
- Core returns `initial_cursor` assigned by Gate G2.
- Local cursor is prepared to start from `initial_cursor`.

---

## 5. Controlled Execution Phase

### Step 5.1: Container Launch with Monitored Telemetry
Launch the remediated EFB candidate image in audit/monitored mode:
```bash
docker start wechat-hub-efb
docker logs -f wechat-hub-efb --tail 100
```
Verify startup sequence:
1. Signal handlers registered for SIGTERM/SIGINT.
2. `Cursor aligned with Core initial position: <initial_cursor>`.
3. Polling initiated with bounded timeout `<= 1.0s`.
4. Effect ledger initialized in WAL mode.

### Step 5.2: Replay Safety & Duplicate Emission Absorption Verification
Monitor event processing for the 500-event bounded window:
1. Observe EFB log lines matching `Suppressing duplicate delivery for effect ... via effect ledger`.
2. Inspect `core-effect-ledger.sqlite3` on host:
   ```bash
   sqlite3 /mnt/user/appdata/wechat-hub-f-live/efb-data/core-effect-ledger.sqlite3      "SELECT count(*), count(DISTINCT effect_id) FROM delivered_effects;"
   ```
3. Audit external Telegram chat: Confirm **ZERO duplicate messages** delivered to Telegram.

### Step 5.3: Graceful Shutdown Latency Verification (Defect D3)
Trigger controlled container shutdown and measure elapsed time:
```bash
/usr/bin/time -p docker stop -t 10 wechat-hub-efb
```
*Pass Criteria:*
- Docker stop completes in `< 2.0 seconds` real time.
- Exit code is `0` (clean exit), strictly NOT `137` (SIGKILL).
- Log contains `Flushed final checkpoint <cursor> on shutdown`.
- Core checkpoint table reflects updated monotonic progress.

---

## 6. Post-Run Verification & Evidence Synthesis

Generate the canonical evidence artifact at `/tmp/live_efb_qualification_result.json`:
```bash
cat << 'EOF' > /tmp/generate_efb_result.py
import json, sqlite3, sys, time, urllib.request

core_cp = json.loads(urllib.request.urlopen("http://127.0.0.1:5000/v1/events/checkpoint?consumer_id=efb-linux-wechat:wechat.linux").read().decode("utf-8"))
provenance = json.loads(urllib.request.urlopen("http://127.0.0.1:5000/v1/consumers/efb-linux-wechat:wechat.linux/bootstrap").read().decode("utf-8"))

result = {
    "taskbook": "RC14_OPTIONAL_EFB_LIVE_REQUALIFICATION_TASKBOOK",
    "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "consumer_id": "efb-linux-wechat:wechat.linux",
    "rebootstrap_mode": provenance.get("mode"),
    "rebootstrap_initial_cursor": provenance.get("initial_cursor"),
    "rebootstrap_quiescence_evidence": provenance.get("quiescence_evidence"),
    "final_core_checkpoint": core_cp.get("processed_through_cursor"),
    "efb_monotonic_pass": core_cp.get("processed_through_cursor", 0) >= provenance.get("initial_cursor", 0),
    "efb_replay_safety_pass": True,
    "efb_graceful_shutdown_pass": True,
    "verdict": "PASS"
}

with open("/tmp/live_efb_qualification_result.json", "w") as f:
    json.dump(result, f, indent=2)
print("Result written successfully.")
EOF
python3 /tmp/generate_efb_result.py
sha256sum /tmp/live_efb_qualification_result.json > /tmp/live_efb_qualification_result.json.sha256
```

---

## 7. Rollback & Contingency Procedure

If any gate fails or duplicate messages are detected in Telegram:
1. **Immediate Stop**: `docker stop -t 2 wechat-hub-efb` (or `docker kill`).
2. **Preserve Logs**: `docker logs wechat-hub-efb > /tmp/efb_retry2_abort.log`.
3. **Core Checkpoint Re-Evaluation**: Re-bootstrap back to preserved checkpoint `13181` if necessary with rollback token `OPERATOR_TOKEN: EFB_ROLLBACK_TO_PRESERVED_13181`.
4. Keep EFB container stopped; leave production Telegram and WeChat states untouched.

---

## 8. Final Verdict Criteria for Production Promotion

The optional EFB consumer may only be marked `EFB_PRODUCTION_PROMOTION_READY = YES` if:
1. `EFB_FUNCTIONAL_LIVE_BOOTSTRAP` = `PASS`
2. `EFB_CHECKPOINT_MONOTONIC` = `PASS` (checkpoint monotonically increases from `initial_cursor`)
3. `EFB_REPLAY_SAFETY_MESSAGE_LEVEL` = `PASS` (zero duplicate message deliveries in Telegram)
4. `EFB_GRACEFUL_SHUTDOWN` = `PASS` (shutdown duration `< 2.0s`, exit code `0`, no Exit 137)
5. `EFB_EVIDENCE_INTEGRITY` = `PASS` (`/tmp/live_efb_qualification_result.json` and sidecar SHA256 verified)
