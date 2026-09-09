# WeChat Hub Identity v2 / RC.11 — Real NAS Acceptance Result

## 1. Executive Summary

- **Taskbook**: [`docs/identity_v2_flash_taskbook/23_RC11_REAL_NAS_ACCEPTANCE.md`](file:///G:/LLM/WeChat_Hub/docs/identity_v2_flash_taskbook/23_RC11_REAL_NAS_ACCEPTANCE.md)
- **Authorization**: `AUTHORIZE: IDENTITY_V2_RC11_REAL_NAS_ACCEPTANCE`
- **Host / Target Environment**:
  - Host: Unraid NAS (`192.168.22.102`)
  - Compose project: `wechat-hub-f-live` (`/mnt/user/appdata/wechat-hub-f-live`)
  - Live Data Root: `/mnt/user/appdata/wechat-hub-f-live` (physical disk: `/mnt/disk3`)
- **Execution Window**: `2026-09-09T16:51:00Z` – `2026-09-09T18:43:45Z` (UTC) / `00:51:00` – `02:43:45` (CST)
- **Evidence Directory**: `/mnt/user/appdata/wechat-hub-f-live/test/identity-v2-rc11-20260909T165100Z/`
- **Sealed Evidence Manifest**: `artifacts.sha256` (43 files sealed and verified)
- **Overall Verdict**: **`IDENTITY_V2_RC11_REAL_NAS = PASS`** (100% compliant across all functional, endurance, database integrity, cgroup resource limit, and login continuity criteria).

---

## 2. Pinned Release Candidate Artifacts

The exact immutable candidate artifacts specified in [`release/manifest-0.1.0-rc.11.yaml`](file:///G:/LLM/WeChat_Hub/release/manifest-0.1.0-rc.11.yaml) were deployed and verified:

| Service | Component Role | Source Commit | Tag / Version | Pinned Digest | Live Verified Digest |
|---|---|---|---|---|---|
| `runtime` | Runtime Manager | `6b43d0f477dad9f49118692738d605dd0cc33894` | `0.1.0-rc.10` | `sha256:5a2454a6a772852a7c38b0e4321345db1fcb5bd6eb038f018d3067d40dd02158` | `sha256:5a2454a6a772852a7c38b0e4321345db1fcb5bd6eb038f018d3067d40dd02158` |
| `core` | Core Service | `6f1b1739afe63cc7cd10e89f0a27945c829694ea` | `0.1.0-rc.9` | `sha256:d68c57ba908b78e34d909a4d59b4fc74309c2c04005a44185a807a9581f12150` | `sha256:d68c57ba908b78e34d909a4d59b4fc74309c2c04005a44185a807a9581f12150` |
| `console` | Console Service | `831faa81cb7dee61ace8836ed5cd9f9acf0a6a92` | `0.1.0-rc.7` | `sha256:da8a72f8989ce173083a437d308c63ba9c943458952d9703d37e0642e7ec145a` | `sha256:da8a72f8989ce173083a437d308c63ba9c943458952d9703d37e0642e7ec145a` |
| `agent_wechat` | Isolated WeChat Agent | `f7bd772bef682739abab1f9a91ffb1aed033d5f2` | `0.11.15-wh.5` | `sha256:87b055e3ed2b9b5091421b15ed802c3e9f36e0029d11ea1f12a727bb5f3c85e4` | `sha256:87b055e3ed2b9b5091421b15ed802c3e9f36e0029d11ea1f12a727bb5f3c85e4` |

---

## 3. Phase 1: Preflight Verification & Database Integrity

| Check Item | Observed Value | Expected / Invariant | Verdict |
|---|---|---|---|
| NAS Host Reachability | `root@192.168.22.102` online | Responsive SSH connectivity | **PASS** |
| Outbox Count Baseline | `96\|2026-09-09T07:47:36Z` | Frozen post-WH5 G9 count | **PASS** |
| Core DB Backup | `wechat_core.sqlite.backup` (636,985,344 bytes) | Hash: `af7d807129b2...` | **PASS** |
| Core DB Quick Check | `ok` | Btree integrity clean | **PASS** |
| Console DB Quick Check | `ok` | `console.sqlite` integrity clean | **PASS** |
| Preflight Accounts State | A & B `online` / `logged_in` | Both accounts operational | **PASS** |
| Desktop Port 6174 | Unbound (0 listeners) | Isolation invariant | **PASS** |
| Active Companion Containers | 0 companion containers | Zero companion leaks | **PASS** |

---

## 4. Phase 2: Candidate Overlay Staging

| Step | Detail | Result | Verdict |
|---|---|---|---|
| Manifest Digest Verification | `manifest-0.1.0-rc.11.yaml` | `4fcdbd19291a17d1a98a5647b1c2d32db6a9b496f764e6b909c76329bbf025bc` | **PASS** |
| Compose Overlay Digest Verification | `docker-compose.identity-v2-rc11-candidate.yml` | `897a17cd8cced80527424bb9ead4b3b3429c93ed7715ae2bb571587f747845d0` | **PASS** |
| Candidate Image Pre-pull | Pulled `runtime@sha256:5a2454a6`, `core@sha256:d68c57ba`, `console@sha256:da8a72f8` | All layers extracted and verified locally | **PASS** |
| Live Project Overlay Synthesis | `docker-compose.live-rc11-overlay.yml` mapped to live services `runtime`, `core`, `console` | `docker compose config` validation clean | **PASS** |

---

## 5. Phase 3: Container Recreation & Service Verification

1. **Recreation Execution**:
   - `wechat-hub-f-live-runtime`: Recreated -> **`healthy`** (in 5s)
   - `wechat-hub-f-live-core`: Recreated -> **`healthy`** (completed one-time Identity v2 schema migration and btree indexing for legacy rows)
   - `wechat-hub-f-live-console`: Recreated -> **`healthy`** (completed additive column migration for `message_projection`)
2. **P0 cgroup PidsLimit Guard Enforcement**:
   - Runtime: `HostConfig.PidsLimit = 200` (live: 53) — **PASS**
   - Core: `HostConfig.PidsLimit = 100` (live: 4) — **PASS**
   - Console: `HostConfig.PidsLimit = 100` (live: 2) — **PASS**
   - Agent A: `HostConfig.PidsLimit = 512` (live: 297) — **PASS**
   - Agent B: `HostConfig.PidsLimit = 512` (live: 304) — **PASS**
3. **Runtime Configuration**:
   - `AGENT_WECHAT_IMAGE` inside runtime verified: `ghcr.io/onestao/wechat-hub-agent-wechat@sha256:87b055e3ed2b9b5091421b15ed802c3e9f36e0029d11ea1f12a727bb5f3c85e4` (wh.5).
4. **Login Continuity Without QR Re-scan**:
   - **Account A (`f-live-a`)**:
     - Status: `logged_in` / `online`
     - Bound identity: `wxid_7ugft7xlkf5a22_4117`
     - Binding state: `bound` (`wechat_identity_uuid: 40887bed-6c2b-4248-bf78-3ad12f2bdc9e`)
     - QR re-scans required: **0**
   - **Account B (`testB`)**:
     - Status: `logged_in` / `online`
     - Bound identity: `wxid_rpfflqttdz4a22_7fcd`
     - Binding state: `bound` (`wechat_identity_uuid: fb041e1f-5f24-49d5-ae6b-fa98073970b5`)
     - QR re-scans required: **0**
5. **Zero Real Send Preservation**:
   - Outbox count verified post-recreation: `96|2026-09-09T07:47:36Z` (0 real sends performed, count frozen).
6. **Isolation Invariants**:
   - Active companion containers: `0`
   - Port 6174 listeners: `Unbound`

---

## 6. Phase 4: 30-Minute Canary Observability

- **Observation Period**: `2026-09-09T18:14:42Z` – `2026-09-09T18:43:05Z` (1,703 seconds)
- **Sampling Cadence**: 15 samples at 120-second intervals
- **Logged Metrics**: `/mnt/user/appdata/wechat-hub-f-live/test/identity-v2-rc11-20260909T165100Z/canary/canary_samples.log`

| Sample | Timestamp (UTC) | Runtime Health | Core Health | Console Health | Account A | Account B | Failed Sync Cycles | Outbox Count | Runtime PIDs | Core PIDs | Console PIDs | Agent A PIDs | Agent B PIDs |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 18:14:42Z | healthy | healthy | healthy | logged_in | logged_in | 0 | 96 | 53 | 4 | 2 | 297 | 305 |
| 2 | 18:16:44Z | healthy | healthy | healthy | logged_in | logged_in | 0 | 96 | 53 | 4 | 2 | 297 | 305 |
| 3 | 18:18:48Z | healthy | healthy | healthy | logged_in | logged_in | 0 | 96 | 53 | 4 | 2 | 297 | 305 |
| 4 | 18:20:49Z | healthy | healthy | healthy | logged_in | logged_in | 0 | 96 | 53 | 4 | 2 | 297 | 305 |
| 5 | 18:22:50Z | healthy | healthy | healthy | logged_in | logged_in | 0 | 96 | 53 | 4 | 2 | 297 | 305 |
| 6 | 18:24:51Z | healthy | healthy | healthy | logged_in | logged_in | 0 | 96 | 53 | 4 | 2 | 297 | 305 |
| 7 | 18:26:52Z | healthy | healthy | healthy | logged_in | logged_in | 0 | 96 | 53 | 4 | 2 | 297 | 305 |
| 8 | 18:28:53Z | healthy | healthy | healthy | logged_in | logged_in | 0 | 96 | 53 | 4 | 2 | 297 | 305 |
| 9 | 18:30:54Z | healthy | healthy | healthy | logged_in | logged_in | 0 | 96 | 53 | 4 | 2 | 297 | 305 |
| 10 | 18:32:56Z | healthy | healthy | healthy | logged_in | logged_in | 0 | 96 | 53 | 4 | 2 | 297 | 305 |
| 11 | 18:34:57Z | healthy | healthy | healthy | logged_in | logged_in | 0 | 96 | 53 | 4 | 2 | 297 | 305 |
| 12 | 18:37:01Z | healthy | healthy | healthy | logged_in | logged_in | 0 | 96 | 53 | 4 | 2 | 297 | 305 |
| 13 | 18:39:03Z | healthy | healthy | healthy | logged_in | logged_in | 0 | 96 | 53 | 4 | 2 | 297 | 305 |
| 14 | 18:41:04Z | healthy | healthy | healthy | logged_in | logged_in | 0 | 96 | 53 | 4 | 2 | 297 | 305 |
| 15 | 18:43:05Z | healthy | healthy | healthy | logged_in | logged_in | 0 | 96 | 53 | 4 | 2 | 297 | 304 |

**Canary Summary**:
- Total Samples: 15 / 15 (100% PASS)
- Unhealthy Cycles: 0
- Consecutive Failed Sync Cycles: 0
- Account Dropoffs / Re-scans: 0
- Outbox Modifications: 0
- Cgroup PIDs Monotonic Growth: None (PIDs completely flat across all containers)
- Verdict: **`CANARY_30MIN_PASS`**

---

## 7. Phase 5: Postflight Evidence Audit & Garbage Check

1. **Terminal Outbox Verification**:
   - `terminal_outbox.txt` SHA256: `e33966f1837f83d7ed42d8d1e1a8d365137f8f2efe4259dc966b047786fda051`
   - `outbox_baseline.txt` SHA256: `e33966f1837f83d7ed42d8d1e1a8d365137f8f2efe4259dc966b047786fda051`
   - Exact hash match confirms zero real send emissions throughout the acceptance run.
2. **Resource Cleanup Audit**:
   - Unexpected managed containers: `0`
   - Orphan test volumes: `0`
   - Orphan test directories: `0` (all test artifacts isolated under `/mnt/user/appdata/wechat-hub-f-live/test/identity-v2-rc11-20260909T165100Z/`)
   - Production directories (`/data`, `/home/wechat`, `wechat_core.sqlite`, `console.sqlite`): 100% preserved and intact.
   - Global prune commands executed: **0** (`docker system prune` and `docker volume prune` were strictly forbidden and never executed).
   - Resource cleanup: **`PASS`**

---

## 8. Final Invariant Status Footer

```text
IDENTITY_V2_RC11_REAL_NAS = PASS
IDENTITY_V2_RC11_PROMOTION_READY = YES
ZERO_REAL_SEND_PRESERVED = YES
LOGIN_CONTINUITY_MAINTAINED = YES
RESOURCE_CLEANUP = PASS
```
