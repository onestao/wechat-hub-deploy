# RC.14 Core File / Voice Media Reference — Production Deployment Execution Erratum

```text
DOCUMENT_TYPE                    = PRODUCTION_DEPLOYMENT_EXECUTION_ERRATUM
DOCUMENT_STATUS                  = SEALED / NOT_EXECUTED
WORK_PACKAGE                     = RC14_CORE_FILE_VOICE_MEDIA_REFERENCE_ENGINEERING
PARENT_TASKBOOK                  = docs/RC14_CORE_FILE_VOICE_MEDIA_REFERENCE_PRODUCTION_DEPLOYMENT_TASKBOOK.md
PARENT_TASKBOOK_SHA256           = 9081ccaaa5a053ec2bca7e36610efef6418ed6fcaa3dd3efb2b90551c554aaae
PARENT_TASKBOOK_MODIFIED         = NO
PARENT_TASKBOOK_SEAL_VERIFIED    = YES
SCOPE                            = EXACTLY ONE EXECUTION RULE
OVERRIDDEN_RULE                  = EFB post-Core-deployment checkpoint policy
SEALED_AT_UTC                    = 2026-09-17T11:55:00Z
AUTHORIZES                       = nothing by itself
ACTION                           = STOP
```

> **This erratum does not authorize anything.** It corrects one execution rule of the parent
> sealed taskbook. Everything else in the parent taskbook remains in force, unchanged and
> byte-identical.

---

## 0. Inheritance — not a new rule

This erratum is executed **inside the same production deployment package** as its parent
taskbook and therefore inherits, unchanged:

* the **ACTIVE CORE PRODUCTION DB ACCESS RULE** and its required return values
  `ACTIVE_CORE_RAW_SQLITE_READS = 0` and `ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0`;
* the parent taskbook's protected set, prohibitions, rollback gates, protected-service gates,
  runtime contract qualification and return block.

Nothing in this section is a new obligation. It records inheritance so the document is not read
in isolation.

---

## E1 — EFB checkpoint policy (supersedes parent taskbook §5.5 clause 2)

### E1.1 The overridden text

The parent taskbook §5.5 ("Bounded re-emission disclosure and the next-round entry obligation")
requires, at clause 2:

```text
2. Therefore the next EFB live round MUST fix its entry checkpoint at the
   post-deployment stream head, not at 273844.
```

**Any content in the parent taskbook that requires a next EFB entry checkpoint to equal the
post-deployment stream head no longer has execution force.** Clause 2 is void.

### E1.2 The authoritative rule

```text
EFB_CHECKPOINT_PRE                    = 273844
EFB_CHECKPOINT_POST_CORE_DEPLOYMENT   = 273844
EFB_CHECKPOINT_MUTATION               = 0
```

During Core deployment, and after deployment closure, **the EFB checkpoint must not be
advanced.** The next EFB round resumes normally from its current durable consumer position
`273844`.

### E1.3 Why the override is correct

The frozen EFB candidate

```text
EFB_SOURCE = 69a1f58e29177634b6790ed3b5ec688871ba590c
```

already satisfies the properties that the parent taskbook's checkpoint-advance clause was a
workaround for:

```text
UNKNOWN_IDENTITY_HARDENING                  = PASS
EVENT_TYPE_USED_FOR_DUPLICATE_DECISION      = NO
DURABLE_SUBSCRIPTION_FLOOR                  = YES
W1/W2 reprojection zero-effect gates        = PASS
```

Consequently the next EFB round is expected to recover normally from `273844`, and Core
re-projection is idempotently suppressed by the **EffectLedger plus durable subscription
provenance** — not by skipping a cursor range.

The parent taskbook's clause was written when the re-emission window was believed to need a
cursor fence. It must not be executed, because a cursor fence is **unsound here**: the same
range can contain genuinely new business alongside Core re-emitted events, so skipping it would
silently drop real messages. The hardening above is what makes the fence unnecessary; the fence
would be actively harmful.

### E1.4 What this does **not** change

```text
CHECKPOINT_PROTOCOL                      = UNCHANGED
EFB's LOCAL CONTINUATION POINT           = UNCHANGED  (core-event-cursor.json; not the Core row)
CONSUMER CHECKPOINT ADVANCE AUTHORIZATION = STILL REQUIRED, AND IS NOT GRANTED HERE
AGENT_CHECKPOINT                         = UNTOUCHED
```

The general rule that advancing any consumer checkpoint is a consumer-state mutation requiring
its own separate authorization is **reinforced**, not relaxed: this erratum grants no advance
and mandates zero mutation.

---

## E2 — Post-deployment stream head (observability only)

After Core deployment the round must still record:

```text
POST_DEPLOY_STREAM_HEAD =
```

Its meaning is restricted to:

```text
OBSERVABILITY / REPLAY_WINDOW_UPPER_BOUND
```

It **must not** be converted, automatically or by inference, into:

```text
EFB checkpoint target
```

Record it with its timestamp (it is a moving value — the `account.status` heartbeat advances it
roughly every 5 s) and use it only to bound the replay window being observed and reported.

---

## E3 — Precedence

This erratum takes precedence over the parent sealed taskbook **only** for:

```text
EFB post-Core-deployment checkpoint policy
```

For everything else the parent sealed taskbook continues to govern, in particular:

```text
candidate identity            -> parent taskbook §2
exact digest                  -> parent taskbook §2 / §4.1
Core recreate budget          -> parent taskbook §3 / §12.1   (EXHAUSTED; new authorization required)
DB governance                 -> parent taskbook §0 / §7
rollback gates                -> parent taskbook §6
protected-service gates       -> parent taskbook §5.1 / §5.2 / §5.3
runtime contract qualification-> parent taskbook §5.4
return block                  -> parent taskbook §8, as amended by E4 below
```

Where the parent taskbook and this erratum could be read as conflicting on any subject other
than the EFB post-Core-deployment checkpoint policy, **the parent taskbook prevails.**

---

## E4 — Return block amendment

Only the following fields of the parent taskbook §8 return block are re-specified:

```text
EFB_CHECKPOINT_AFTER          = 273844        (must equal EFB_CHECKPOINT_PRE; no advance)
EFB_CHECKPOINT_MUTATION       = 0
POST_DEPLOY_STREAM_HEAD       = <value>       (observability / replay-window upper bound only)
POST_DEPLOY_STREAM_HEAD_USED_AS_EFB_CHECKPOINT_TARGET = NO
```

All other §8 fields keep their original meaning and required values.

---

## E5 — Non-actions of this erratum

```text
PARENT_TASKBOOK_MODIFIED            = NO
PARENT_TASKBOOK_SHA256_UNCHANGED    = YES
EFB_STARTED                         = NO
EFB_CHECKPOINT_MODIFIED             = NO
AGENT_STARTED                       = NO
AGENT_CHECKPOINT_MODIFIED           = NO
CORE_DEPLOYED                       = NO
CORE_RECREATE_COUNT_THIS_ROUND      = 0
PRODUCTION_CORE_MUTATION            = NO
PRODUCTION_EFB_TOUCHED              = NO
PRODUCTION_AGENT_TOUCHED            = NO
ACTIVE_CORE_PRODUCTION_DB_FILE_OPENS = 0
ACTIVE_CORE_RAW_SQLITE_READS         = 0
```

Sealing this erratum changes exactly one file plus its `.sha256` sidecar. It does not deploy,
does not start EFB, and does not touch any checkpoint.

---

## E6 — Seal

```text
ERRATUM_PATH   = docs/RC14_CORE_FILE_VOICE_MEDIA_REFERENCE_PRODUCTION_DEPLOYMENT_EXECUTION_ERRATUM.md
ERRATUM_SHA256 = see docs/RC14_CORE_FILE_VOICE_MEDIA_REFERENCE_PRODUCTION_DEPLOYMENT_EXECUTION_ERRATUM.md.sha256
ORIGINAL_TASKBOOK_MODIFIED = NO
ORIGINAL_TASKBOOK_SHA256   = 9081ccaaa5a053ec2bca7e36610efef6418ed6fcaa3dd3efb2b90551c554aaae
ACTION = STOP
```

The erratum carries no self-referential digest in its body: a document cannot contain its own
SHA256. The authoritative value is the sealed sidecar, verified with
`sha256sum -c RC14_CORE_FILE_VOICE_MEDIA_REFERENCE_PRODUCTION_DEPLOYMENT_EXECUTION_ERRATUM.md.sha256`.
