# Post-F Release Status

Date: 2026-09-02
Session: 0 — Release Coordinator / Source Freeze (COMPLETED)

## Result

`RELEASE_BASELINE_READY`

## Baseline commits

| Repo | Old HEAD | New baseline commit | Pushed to origin |
|---|---|---|---|
| work/runtime | `ea76d649d4684c3d5acd0f96de9c257425c1464e` | `010b94cfb9a4a25341aca1fbf8bf3edbb246f34f` | `feat/multi-account-runtime` |
| work/core | `b540ab1be0efa8b54fb34afd14baaea210d7f34f` | `ed171a881dbe9b97056ea901ad5b08287e0b767c` | `feat/multi-account-core` |
| work/console | `58b2c43ff18597c6d0c9ec47270eb40e4fb0b2bb` | `0c54273ffeef08a66e6752f0c3a3a2bd796c39f1` | `feat/decoupled-console` |
| work/agent | `e1b5d15f8be9d59a3329184476f4fca891836a3a` | `b7ce32a2bf9bd40cb85aaa6ce07d9f59f0009f24` | `feat/mcp-monitor-agent` |
| work/efb-linux-wechat-slave | `f26e7c3a30ea39792bc5a5ccc8746ce2383aff78` | `679da04e44b19abe3f5107b43851a524a2a1668c` | `feat/linux-wechat-slave` |
| root deploy repo | not a Git repo | `cbf982d47ced395b22e495be2c7655e542c68787` | `main` |

All work repositories used the existing feature branches. Upstream remotes
were left untouched. No force push, rewrite, squash, or monorepo conversion was
performed.

## Git hygiene

- `git status` is clean for runtime, core, agent, and EFB.
- Console had user-authored edits arrive during the freeze; they are in the
  working tree but NOT part of the pushed baseline. The baseline commit
  `0c54273` was pushed as-is.
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

## GitHub

`READY`

- GitHub account: `onestao` (active, keyring)
- Token scopes: `repo`, `workflow`
- `gh auth setup-git` configured: git push uses onestao token
- All six repos created as private under `onestao/`:
  - `runtime`    -> `https://github.com/onestao/wechat-hub-runtime.git`
  - `core`       -> `https://github.com/onestao/wechat-hub-core.git`
  - `console`    -> `https://github.com/onestao/wechat-hub-console.git`
  - `agent`      -> `https://github.com/onestao/wechat-hub-agent.git`
  - `efb`        -> `https://github.com/onestao/wechat-hub-efb-linux-wechat-slave.git`
  - `deploy`     -> `https://github.com/onestao/wechat-hub-deploy.git`
- All baseline branches pushed to origin:
  - `runtime: feat/multi-account-runtime` @ `010b94cfb9a4a25341aca1fbf8bf3edbb246f34f`
  - `core: feat/multi-account-core` @ `ed171a881dbe9b97056ea901ad5b08287e0b767c`
  - `console: feat/decoupled-console` @ `0c54273ffeef08a66e6752f0c3a3a2bd796c39f1`
  - `agent: feat/mcp-monitor-agent` @ `b7ce32a2bf9bd40cb85aaa6ce07d9f59f0009f24`
  - `efb: feat/linux-wechat-slave` @ `679da04e44b19abe3f5107b43851a524a2a1668c`
  - `deploy: main` @ `cbf982d47ced395b22e495be2c7655e542c68787`
- GHCR namespace: `onestao` (not yet configured; Wave 1 will set up CI)

## Deploy baseline

The root deploy repository now includes `docs/`, `stack/`, `release/`,
`.github/`, `F_COMPLETION_REPORT.md`, `.gitignore`, `README.md`, and the
updated status doc.

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
| GitHub auth | READY |
| GitHub namespace | `onestao` |
| GHCR publish | Wave 1 |

Wave 1 may start after this status commit is pushed. Do not begin Wave 2
or H3 until the Wave 1 reports and RC digests exist.
