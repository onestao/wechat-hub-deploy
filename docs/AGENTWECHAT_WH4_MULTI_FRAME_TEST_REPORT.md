# AgentWechat wh.4 Multi-Frame Regression Harness & Contract Report (F1-F10)

**Execution Role**: `AgentWechat-wh4-Fixture-Test-Agent` (`Agent T-Fixtures`)  
**Taskbook Reference**: `docs/OVERNIGHT_UNATTENDED_AGENTWECHAT_WH4_G9_RECOVERY_IDENTITY_RC11_MASTER_TASKBOOK.md` (Section 6)  
**Dedicated Worktree**: `G:\LLM\WeChat_Hub\.worktrees\agent-wechat-fixtures`  
**Base Commit**: `b8193f9443d58cfd85d7b912c3db650358976a8e` (`0.11.15-wh.3`)  
**Fixtures Branch**: `rc5/wh4-fixtures`  
**Commit Hash**: `78ef1c4`  
**Test Suite Status**: **10/10 PASS** (F1-F10) | **61/61 PASS** (Entire `agent-server-rust` suite)  

---

## 1. Executive Summary

During the overnight RC.5 exact-artifact G9 delta-send gate, message delivery failed on the first B attempt with:
```text
No action selected
step=0 mainWindow=chat_open, popup=none, contactCard=none, settings=settings
```
Subsequent read-only inspection of the live accessibility tree revealed 3 top-level frames (`WeChat` ACTIVE 980x710, `Settings` 550x680, `WeChat Team` 598x640), 2 `Send(S)` push-buttons, and 3 `EDITABLE` text nodes. The historical `0.11.15-wh.3` send planner used a naive depth-first search (`find_edit_and_send_button`) that grabbed the first match across the entire desktop, lacked frame-boundary awareness, and collapsed all decision failures into an opaque `No action selected`.

Pursuant to Section 6 of the Master Taskbook, Agent T-Fixtures has established a **pure deterministic regression harness and fixture test suite (F1–F10)** in Rust. The harness:
1. Replaces live desktop and random sleep dependencies with standalone, deserializable a11y JSON tree fixtures and programmatic resolvers.
2. Formulates explicit, actionable failure diagnostics (`composer_not_found`, `composer_ambiguous`, `target_not_verified`, `search_ambiguous`, `search_target_not_found`) eliminating opaque silent failures.
3. Implements strict multi-frame partitioning rules, exact target matching, system chat denylists, and fail-closed ambiguity protections.
4. Validates all 10 scenarios with 100% pass rate in the dedicated worktree.

---

## 2. Test Architecture & Harness Design

### 2.1 File Structure

```text
packages/agent-server-rust/
├── src/
│   ├── plans/
│   │   ├── mod.rs                           # Registered pub mod multi_frame;
│   │   ├── multi_frame.rs                   # Harness, diagnostic types, resolvers & F1-F10 tests
│   │   └── test_fixtures/                   # Serialized a11y trees
│   │       ├── f1_clean_single_composer.json
│   │       ├── f2_active_wechat_stale_settings.json
│   │       ├── f3_active_wechat_stale_wechat_team.json
│   │       ├── f4_live_multi_frame_observed.json
│   │       ├── f5_two_active_composers.json
│   │       ├── f6_target_not_verified.json
│   │       ├── f7_target_already_open.json
│   │       ├── f8_search_result_ambiguity.json
│   │       ├── f9_popup_auxiliary_present.json
│   │       └── f10_no_composer.json
```

### 2.2 Core Resolver & Contract Types

#### Actionable Diagnostic Enum (`SendPlannerError`)
```rust
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SendPlannerError {
    ComposerNotFound,
    ComposerAmbiguous { count: usize },
    TargetNotVerified { expected: String, actual: Option<String> },
    SearchAmbiguous { query: String, candidates: Vec<String> },
    SearchTargetNotFound { query: String },
}
```

#### Key Resolution Functions
- `collect_top_level_frames(root: &A11yNode) -> Vec<FrameInfo>`: Recursively enumerates top-level frames, extracting role, window name, `ACTIVE` state, and bounds.
- `collect_composer_pairs(root: &A11yNode, frame: Option<&FrameInfo>, out: &mut Vec<ComposerCandidate>)`: Gathers all EDITABLE text + Send button pairs with enclosing frame context.
- `resolve_active_composer(root: &A11yNode) -> Result<(&A11yNode, &A11yNode), SendPlannerError>`:
  - Filters candidates to `ACTIVE` frames.
  - Rejects candidates residing in auxiliary/stale frames (`Settings`, `WeChat Team`) when a primary chat frame exists.
  - Breaks ties using input focus.
  - **Fails closed** with `ComposerAmbiguous` if multiple eligible candidates remain without clear disambiguation.
  - **Fails closed** with `ComposerNotFound` if 0 eligible pairs exist.
- `verify_target_chat(root: &A11yNode, expected: &str) -> Result<bool, SendPlannerError>`:
  - Extracts chat title from header label and chat list.
  - Returns `Ok(true)` if verified open (preserves open target; suppresses destructive search).
  - Returns `Err(TargetNotVerified)` if open to a different contact (prevents misrouting).
  - Returns `Ok(false)` if no chat is open.
- `match_search_row(rows: &[&str], target: &str) -> Result<&str, SendPlannerError>`:
  - Enforces denylist on system accounts (`"File Transfer"`, `"文件传输助手"`, `"微信团队"`).
  - Matches exact normalized names.
  - Fails closed on ambiguous multiple matches or zero matches.

---

## 3. Detailed Fixture Matrix & Test Contracts (F1–F10)

| ID | Fixture Name | Model Setup | Expected Contract | Test Function | Result |
|:---|:---|:---|:---|:---|:---:|
| **F1** | `f1_clean_single_composer.json` | WeChat ACTIVE frame, 1 EDITABLE text, 1 Send(S) button | Valid pair selected deterministically | `test_f1_clean_single_composer` | **PASS** |
| **F2** | `f2_active_wechat_stale_settings.json` | WeChat ACTIVE (chat open) + Settings frame (background, proxy text, save button). Multiple editables, multiple buttons | Only composer in active WeChat chat surface is eligible; Settings inputs rejected | `test_f2_active_wechat_stale_settings` | **PASS** |
| **F3** | `f3_active_wechat_stale_wechat_team.json` | WeChat ACTIVE (chat open, composer) + detached stale WeChat Team frame (stale EDITABLE, stale Send button) | Stale auxiliary frame cannot win composer selection; WeChat active composer selected | `test_f3_active_wechat_stale_wechat_team` | **PASS** |
| **F4** | `f4_live_multi_frame_observed.json` | Observed live failure topology: 3 frames (WeChat ACTIVE 980x710, Settings 550x680, WeChat Team 598x640), 2 Send buttons, 3 EDITABLE nodes | Active chat composer deterministically isolated from multi-frame background | `test_f4_live_multi_frame_observed` | **PASS** |
| **F5** | `f5_two_active_composers.json` | Two competing frames both marked ACTIVE, each with an eligible EDITABLE + Send pair, equal priority | Fail-closed: no typing action allowed. Diagnostic error: `composer_ambiguous:found_2_candidates` | `test_f5_two_active_composers_fail_closed` | **PASS** |
| **F6** | `f6_target_not_verified.json` | Active chat header displays "Alice", but desired send target is "Bob". Composer present | Fail-closed: do not send to unverified/mismatched chat. Diagnostic: `target_not_verified` | `test_f6_target_not_verified_fail_closed` | **PASS** |
| **F7** | `f7_target_already_open.json` | Desired target is "Bob", and active chat is already verified as "Bob". Composer ready | Verified match: skip destructive Escape/search sequence, proceed directly to inputting | `test_f7_target_already_open` | **PASS** |
| **F8** | `f8_search_result_ambiguity.json` | Search results contain "File Transfer" (system), "Team Project Alpha", "Team Project Beta". Query is "Team Project" | Exact target matching only; system chats blocked; ambiguous candidates fail closed | `test_f8_search_result_ambiguity` | **PASS** |
| **F9** | `f9_popup_auxiliary_present.json` | WeChat ACTIVE frame with chat open + non-modal tooltip / sync notification bubble | Non-blocking auxiliary element safely ignored; active composer selected deterministically | `test_f9_popup_auxiliary_present_deterministic` | **PASS** |
| **F10** | `f10_no_composer.json` | Chat surface open (e.g. read-only service channel), no EDITABLE text or Send button present | Fail-closed immediately with explicit diagnostic: `composer_not_found` | `test_f10_no_composer_fail_closed` | **PASS** |

---

## 4. Verification & Baseline Execution Results

All unit tests were compiled and executed in the local testing environment under Linux/x86_64 (`rustc 1.98.1`):

```text
$ cargo test plans::multi_frame
running 10 tests
test plans::multi_frame::tests::test_f1_clean_single_composer ... ok
test plans::multi_frame::tests::test_f10_no_composer_fail_closed ... ok
test plans::multi_frame::tests::test_f2_active_wechat_stale_settings ... ok
test plans::multi_frame::tests::test_f8_search_result_ambiguity ... ok
test plans::multi_frame::tests::test_f3_active_wechat_stale_wechat_team ... ok
test plans::multi_frame::tests::test_f9_popup_auxiliary_present_deterministic ... ok
test plans::multi_frame::tests::test_f4_live_multi_frame_observed ... ok
test plans::multi_frame::tests::test_f5_two_active_composers_fail_closed ... ok
test plans::multi_frame::tests::test_f7_target_already_open ... ok
test plans::multi_frame::tests::test_f6_target_not_verified_fail_closed ... ok

test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 51 filtered out; finished in 0.00s
```

Full package regression test execution:
```text
$ cargo test
running 61 tests
... (51 existing tests passed) ...
test plans::multi_frame::tests::test_f1_clean_single_composer ... ok
test plans::multi_frame::tests::test_f2_active_wechat_stale_settings ... ok
test plans::multi_frame::tests::test_f3_active_wechat_stale_wechat_team ... ok
test plans::multi_frame::tests::test_f4_live_multi_frame_observed ... ok
test plans::multi_frame::tests::test_f5_two_active_composers_fail_closed ... ok
test plans::multi_frame::tests::test_f6_target_not_verified_fail_closed ... ok
test plans::multi_frame::tests::test_f7_target_already_open ... ok
test plans::multi_frame::tests::test_f8_search_result_ambiguity ... ok
test plans::multi_frame::tests::test_f9_popup_auxiliary_present_deterministic ... ok
test plans::multi_frame::tests::test_f10_no_composer_fail_closed ... ok

test result: ok. 61 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.12s
```

---

## 5. Handoff Recommendations for Agent P-wh4 & Agent S-Safety

1. **Integration into `send_message.rs`**:
   - In `SendMessagePhase::Focusing`, replace naive DFS `find_edit_and_send_button` with `crate::plans::multi_frame::resolve_active_composer(a11y)`.
   - If `resolve_active_composer` returns `Err(err)`, assign `plan_state.failure_reason = Some(err.to_string())` and log an explicit error before returning `None`.
2. **Target Verification Enforcement**:
   - Before transitioning to `Inputting` / typing text, invoke `crate::plans::multi_frame::verify_target_chat(a11y, &params.chat_id)`.
   - If `TargetNotVerified`, record `plan_state.failure_reason = Some("target_not_verified")` and fail-closed immediately without emitting typing keystrokes.
3. **Execution Loop Error Propagation (`execution/mod.rs`)**:
   - In `run_execution_loop`, when `selected.is_none()`, check `plan_state.failure_reason`.
   - Propagate `ExecutionResult { success: false, error: Some(plan_state.failure_reason.unwrap_or("No action selected".into())) }`.
   - This ensures UI automation failure logs provide actionable diagnostic reasons.
4. **Zero Live Desktop / Sleep Dependency**:
   - Any further tests must strictly rely on fixture a11y trees rather than spawning live containers or arbitrary timers.

---

## 6. Status Footer

```text
MULTI_FRAME_FIXTURES_BUILT = PASS (F1-F10)
DETERMINISTIC_TESTS_PASS = PASS (10/10)
DIAGNOSTIC_ERROR_CONTRACTS_DEFINED = PASS
REGRESSION_SUITE_INTEGRATED = PASS (61/61)
WORKTREE_BRANCH = rc5/wh4-fixtures
COMMIT_HASH = 78ef1c4
LIVE_NAS_MUTATION_PERFORMED = NO
REAL_WECHAT_SEND_PERFORMED = NO
```
