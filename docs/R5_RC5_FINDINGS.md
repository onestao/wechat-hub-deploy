# R5 RC.5 Integration Findings (2026-09-06)

Status: RUNNING RECORD — updated during R5 execution. Final verdicts live in the R5 completion report.

## F1. AgentWechat wh.2 artifact defects (RECORDED, FIX DEFERRED per operator instruction)

**F1.1 WeChat version drift breaks QR login (functional defect)**

- wh.1 / upstream v0.11.15 bundles WeChat `4.1.1.4`:
  QR renders normally, OpenCV-decodable, resolves to `http://weixin.qq.com/x/...`.
- wh.2 bundles WeChat `4.1.13.9`:
  QR widget exists but the QR area renders **pure white** → cannot be scanned → login impossible.
- Observed live: testB on wh.2 sat on `view=LoginQr` with an unscannable white QR for ~1h;
  after the account was recreated on wh.1 the QR scanned and login completed.

**F1.2 Non-reproducible build source (supply-chain defect)**

- The R2 CI Dockerfile path downloads
  `https://dldir1v6.qq.com/weixin/Universal/Linux/WeChatLinux_x86_64.deb`
  — an **unversioned** URL that always resolves to the latest WeChat at build time.
- Therefore `0.11.15-wh.2` is NOT a reproducible artifact and its WeChat version is
  unpinned (currently 4.1.13.9, vs 4.1.1.4 in wh.1 / upstream v0.11.15).
- Fix direction (deferred): pin the WeChat .deb by versioned URL or by sha256
  in the version-controlled Dockerfile, rebuild, and publish a new immutable tag
  (e.g. `0.11.15-wh.3`) before any production promotion.

**Consequence for RC.5**

- `0.11.15-wh.2` remains published in GHCR (immutable, revision `3f5a0a6`) but is
  **NOT deployable** for accounts that need interactive login until F1 is fixed.
- The final-artifact Canary requirement ("rc.5 runtime + wh.2 agent") is
  **BLOCKED by F1** and deferred; functional validation proceeds on the
  runtime rc.5 + wh.1 combination per operator instruction.

## F2. testB account-level image override (observed deployment fact)

- `runtime-config/wechat-runtime/accounts.json` → `testB.agent_wechat.image`
  = `ghcr.io/onestao/wechat-hub-agent-wechat:0.11.15-wh.1` (account `f-live-a` has no such override).
- `image_for()` precedence: account-level > `AGENT_WECHAT_IMAGE` env > default,
  so testB's desired image is wh.1 regardless of the compose env (which pins the wh.2 digest).
- Timeline implication: the 17:41 controlled restart created testB on the wh.2 digest
  (override not yet present); between 17:41 and 19:00 the override appeared (exact
  triggering console action unattributed); the ~19:00 restart then detected drift
  (desired wh.1 vs current wh.2) and recreated testB on wh.1, where login succeeded.
- Both recreations preserved the account data volume; no data loss. RestartCount stayed 0;
  the container object was replaced via the normal stopped-drift reconcile path.

## F3. Desktop companion lifecycle (as designed, P0 rule 15.3)

- Selkies companion is destroyed after `WECHAT_SELKIES_IDLE_TTL_SECONDS=10` without a
  connected client; the Desktop Gateway is a passive proxy and does not re-ensure on
  WebSocket connect. The supported reconnect path is the Console "打开完整微信" button
  (each click re-ensures the companion and issues a fresh session).
- The earlier manual URLs (e.g. `btVEiPym...`) died the moment the idle TTL elapsed;
  this is operator guidance, not a regression.

## F4. Cleaned-up false alarms during verification

- `src/main.js` / `assets/style.css` 426s were caused by malformed probe URLs
  (missing trailing slash); the real bundle assets (`assets/index-*.js/css`,
  `src/universalTouchGamepad.js`, `manifest.json`, `icon.png`) all serve 200.
- Desktop landing 200 HTML + WebSocket 101 + binary/text frame flow verified
  end-to-end via frame-level test through the SSH tunnel.

## F5. Selkies web client refuses non-HTTPS origins (Desktop interactive UX blocker)

- Browser shows: `Error: This application requires a secure connection (HTTPS).
  Please check the URL.` when the client page is served over plain HTTP —
  including `http://localhost:17893` through the SSH tunnel.
- The Desktop Gateway has **no TLS listener**; `https://` therefore fails with
  `ERR_CONNECTION_RESET`.
- Server-side transport is proven good: landing 200 HTML, all assets 200,
  WS upgrade 101, and live frame streaming (`MODE websockets`, cursor,
  `server_settings`, `system_stats`) captured through the full proxy chain.
  The gap is purely the client bundle's secure-context requirement.
- Login was completed via the **Console login-flow QR snapshot**
  (`qr_data_url` over the runtime control channel) — a desktop-independent path.
- Fix directions (deferred, R3-scope runtime change): serve the gateway behind
  TLS (self-signed/cert mount) or fall back to the noVNC client (works over
  plain HTTP; the runtime still carries that path via
  `ensure_interactive_desktop` + `desktop_provider=novnc`).
- Desktop UX verdict stays **FAIL for interactive use** on this artifact;
  automated server-side gate items all PASS.

## Current live stack (as of this record)

| Layer | Running |
|---|---|
| Runtime manager | `ghcr.io/onestao/wechat-hub-runtime@sha256:3d0bc2cf...` (rc.5, revision `57773ab`) |
| testB child | `wechat-hub-agent-wechat:0.11.15-wh.1` (WeChat 4.1.1.4), container `eaab185a...`, PidsLimit=512, `logged_in`, wxid matches |
| f-live-a child | wh.1, untouched since before R5 (container id unchanged), logged in |
| Core / Console | unchanged RC.4 digests |
