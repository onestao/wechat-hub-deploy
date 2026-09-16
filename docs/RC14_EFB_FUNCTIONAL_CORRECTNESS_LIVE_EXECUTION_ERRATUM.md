# RC.14 EFB Functional Correctness — Live Execution Erratum

- **Document type:** Execution erratum (narrow scope, additive only)
- **Applies to:** `docs/RC14_EFB_FUNCTIONAL_CORRECTNESS_LIVE_QUALIFICATION_TASKBOOK.md`
- **Issued:** 2026-09-16
- **Status:** FROZEN

> This erratum is **additive**. It does not edit, supersede or reinterpret the sealed live
> qualification taskbook except in the two fields named in §E3. Every safety gate, test gate,
> abort criterion, rollback step and evidence requirement in the original taskbook remains in
> full force.

---

## E1 — Authoritative candidate identity

The sealed taskbook §5 contains a **stale lineage reference**:

> `- [ ] The candidate was built from source commit `af3707d` plus Core commits `2caee27` and `1e5eddd`.`

That line describes the withdrawn Retry2 lineage. It is **superseded** for the purposes of the
Functional Correctness live execution.

The **only** authoritative candidate for RC.14 EFB Functional Correctness live execution is:

```text
SOURCE_COMMIT = 91a69cef323d120f0e32196917a630d2cf3baa88
IMAGE_DIGEST  = sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241
OCI_REVISION  = 91a69cef323d120f0e32196917a630d2cf3baa88
```

Full image reference (immutable, must be used verbatim — mutable tags are forbidden):

```text
ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241
```

Wherever `af3707d`, `2caee27` or `1e5eddd` appears in the sealed taskbook as a candidate
identity, read it as the block above. This is consistent with — and does not weaken — the
taskbook's own §2, §2.1 and §6, which already pin `91a69cef…`.

Verification basis (`docs/RC14_EFB_FUNCTIONAL_PRODUCTION_PREFLIGHT_RESULT.md` §0):

```text
IMAGE_LINEAGE = PASS
local image ID  = sha256:bc6efcb73c4d62207c1e5d72fef18f55fbb158c22e5a5a15d7fc2cd2831d444a
OCI revision    = 91a69cef323d120f0e32196917a630d2cf3baa88
repoDigest      = ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave@sha256:d45029d586b9224c92a1097191f0add81e793ff826e7ca2e5e91eef077456241
```

---

## E2 — Deployment overlay

The overlay named by the withdrawn Retry2 candidate
(`docker-compose.rc14-optional-efb-retry2-candidate.yml`) no longer exists on the host and
**must not be restored or recreated**.

The **only** permitted deployment overlay for this live execution is:

```text
release/docker-compose.rc14-efb-functional-live.yml
FUNCTIONAL_LIVE_OVERLAY_SHA256 = 8479fcdecf900ba58dc2751b78b5ce900356edcbbbca50f49c3e4a56c4d968dd
```

Properties proven by static compose qualification (§4 of the closure round, `docker compose config`,
no container started):

| Property | Result |
| --- | --- |
| `EFB_IMAGE_EXACT_DIGEST` | `PASS` — exactly one EFB image reference, matching the pinned digest |
| `EFB_INSTANCE_COUNT` | `1` |
| `NO_PROTECTED_SERVICE_OVERRIDE` | `PASS` — `console` / `core` / `runtime` blocks byte-identical to the base-only render |
| `NO_NEW_HOST_PORT` | `PASS` — published ports unchanged (`18078`, `18082`, `17893`); `efb-multi` publishes none |
| `PRODUCTION_PROFILE_MOUNT` | `PASS` — `/mnt/user/appdata/wechat-hub-f-live/efb-profile` → `/root/.ehforwarderbot` |
| `CORE_NETWORK_PATH` | `PASS` — `efb-multi` and `core` both on network `internal` (`wechat-hub-f-live-internal`) |

Invocation (operator only; the closure round did **not** execute this):

```bash
cd /mnt/user/appdata/wechat-hub-f-live
docker compose -f docker-compose.yml -f <path-to-release/docker-compose.rc14-efb-functional-live.yml> \
  up -d --no-deps efb-multi
```

Production identity is carried by the mounted profile and is unchanged:

```text
consumer_id = efb-linux-wechat:wechat.linux
account     = f-live-a
```

No new production consumer may be created and no rebootstrap may be performed.

---

## E3 — Precedence

This erratum takes precedence over the sealed taskbook **only** for:

1. **candidate identity** (E1), and
2. **execution overlay** (E2).

Outside those two fields the original taskbook is unchanged and controlling. In particular:

- All §4 hard prohibitions remain in force.
- All §5 preconditions remain in force (with §5's stale lineage line read per E1).
- All §6 startup-gate criteria remain in force.
- The §7 live test matrix `LQ-01` … `LQ-06`, §8 evidence table, §9 abort criteria and
  §10 rollback steps remain in force **verbatim**.
- The §0 Active Core Production DB Access Rule remains in force, including
  `ACTIVE_CORE_RAW_SQLITE_READS = 0` and `ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0`.
- **No historical shutdown-gate conclusion is amended, reopened or reinterpreted.** The following
  remain exactly as sealed:

```text
EXACT_DIGEST_SHUTDOWN_PRODUCT_GATE = PASS
PREVIOUS_STRICT_WALL_GATE = FAIL_PRESERVED
PREVIOUS_DIE_EVENT_PROTOCOL = INDETERMINATE_PRESERVED
RETRY2_RESULT = FAIL_HISTORICAL_PRESERVED
RETRY2_CROSS_RUN_REPLAY_EVIDENCE = INDETERMINATE_HISTORICAL
```

---

## E4 — No retroactive rewrite

```text
ORIGINAL_TASKBOOK_MODIFIED = NO
ORIGINAL_TASKBOOK_SHA256_PRESERVED = YES
```

| Item | Value |
| --- | --- |
| Original taskbook | `docs/RC14_EFB_FUNCTIONAL_CORRECTNESS_LIVE_QUALIFICATION_TASKBOOK.md` |
| Original SHA256 | `0f7624cc28123648370ea359530450f15f42f0170c7bd2215570a1ca594ff511` |
| Re-hashed this round | identical |
| Taskbook content edited | NO |
| Sealed predecessor docs edited | NO |

This erratum is a **new file**. It does not rewrite, re-seal or supersede the original taskbook
file, and the original SHA256 above remains the authoritative seal for that document.

---

## Resolution summary

```text
TASKBOOK_LINEAGE_CONFLICT_RESOLVED = PASS
```

The conflict was: the sealed taskbook §5 cites the withdrawn Retry2 source lineage (`af3707d` +
Core `2caee27` / `1e5eddd`) while §2 / §2.1 / §6 pin the functional candidate `91a69cef…`.
It is resolved by E1 (authoritative identity = `91a69cef…`) without editing the sealed document,
so both the historical record and the execution identity stay intact.

**`ACTION = STOP` — this erratum authorizes no live traffic by itself.**
