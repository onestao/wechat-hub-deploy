# Post-F Release Status

Date: 2026-09-02
Session: 0 — Release Coordinator / Source Freeze

## Result

`RELEASE_BASELINE_READY`

## Baseline commits

| Repo | Old HEAD | New baseline commit |
|---|---|---|
| work/runtime | `ea76d649d4684c3d5acd0f96de9c257425c1464e` | `010b94cfb9a4a25341aca1fbf8bf3edbb246f34f` |
| work/core | `b540ab1be0efa8b54fb34afd14baaea210d7f34f` | `ed171a881dbe9b97056ea901ad5b08287e0b767c` |
| work/console | `58b2c43ff18597c6d0c9ec47270eb40e4fb0b2bb` | `0c54273ffeef08a66e6752f0c3a3a2bd796c39f1` |
| work/agent | `e1b5d15f8be9d59a3329184476f4fca891836a3a` | `b7ce32a2bf9bd40cb85aaa6ce07d9f59f0009f24` |
| work/efb-linux-wechat-slave | `f26e7c3a30ea39792bc5a5ccc8746ce2383aff78` | `679da04e44b19abe3f5107b43851a524a2a1668c` |
| root deploy repo | not a Git repo | local-only baseline |

All work repositories used the existing feature branches. Upstream remotes
were left untouched. No force push, rewrite, squash, or monorepo conversion was
performed.

## Git hygiene

- `git status` is clean for runtime, core, agent, and EFB.
- Console had user-authored edits arrive during the freeze; they were retested
  and committed as part of the same baseline.
- Large local design/audit PNG files in Console are ignored. Source HTML/SVG
  and the contrast-audit script remain tracked.
- Upstream remotes remain intact:
  - Runtime upstream: `https://github.com/nickrunning/wechat-selkies.git`
  - Core/Console/Agent upstream: `https://github.com/xiaoguiwucan/linux-wechat-agent.git`
  - EFB upstream: `https://github.com/ehForwarderBot/efb-wechat-comwechat-slave.git`

## Secret / artifact scan

`PASS`

The scan covered changed and untracked files in all five work repositories plus
`docs/` and `stack/`. It checked private keys, SSH keys, GitHub/API/OpenAI/Slack
token shapes, JWTs, credential assignments, bearer values, generated SQLite
databases, key/config artifacts, QR/image artifacts, and `.pem`/`.key` files.
No credential-value hit was found. No token value was printed.

Local design screenshots are intentionally excluded from Git; they were not
needed for CI and should not become a redistribution surface.

## Regression

`PASS`

| Suite | Result |
|---|---:|
| Runtime | 37 / 37 PASS |
| Core | 49 / 49 PASS |
| EFB | 19 / 19 PASS |
| Console | 9 / 9 PASS |
| Agent | 9 / 9 PASS |
| Mock Core | 6 / 6 PASS |
| Stack | 8 / 8 PASS |

Additional checks:

- Console Python compile: PASS
- Console JavaScript syntax: PASS
- Agent Python compile: PASS
- Runtime Python compile: PASS
- EFB Python compile: PASS
- YAML / OpenAPI parse: 11 files PASS
- `git diff --check`: PASS; only existing Windows LF/CRLF conversion warnings

Core tests were run through a temporary repository-external runner because the
local sandbox denied creation of `work/core/.tmp`. This was a host-sandbox
issue, not a product-code failure. No source logic was changed for the run.

## GitHub

`GITHUB_AUTH_REQUIRED`

The five local baseline commits are ready, but no user-owned `origin` was
configured, so no push was attempted. The root deploy repository is local-only.

Minimum next user actions:

1. Complete GitHub login with `gh auth login` on the Windows host.
2. Confirm the preferred GitHub username or organization.
3. Create the six private repositories named in the taskbook or let the next
   authenticated session create them.
4. Add each repo as `origin` without overwriting or replacing `upstream`.

## Deploy baseline

The root deploy repository now includes only `docs/`, `stack/`, `release/`,
`.github/`, `F_COMPLETION_REPORT.md`, `.gitignore`, and `README.md`.

It explicitly excludes `work/`, `upstream/`, `.tmp/`, `.probe-release/`,
`.playwright-mcp/`, `.learnings/`, and local runtime artifacts.

## Current release posture

| Area | Status |
|---|---|
| Functional / Live F Gate | PASS |
| Dual-account isolation | PASS |
| Dual-account concurrent sending | PASS |
| Core DB-confirmed text send | PASS |
| Desktop isolation | PASS |
| Token isolation | PASS |
| EFB media reconciliation | PARTIAL |
| Remote filename preservation | PARTIAL |
| Reproducible Runtime image | BLOCKED until G1 |
| Core source-built image | PARTIAL until G2 |
| Production Ready | PARTIAL |

Wave 1 may start after GitHub auth and the user-owned namespace are available.
Do not begin Wave 2 or H3 until the Wave 1 reports and RC digests exist.
