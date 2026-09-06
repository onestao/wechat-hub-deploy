# WeChat Hub RC.5 — H2 6h Soak Preflight + Canary Proc-Race Policy Normalization

- 日期：2026-09-06
- 会话角色：Flash-H（任务书 §3；只做准备/审计，不做 live mutation）
- 分支：`rc5/integration-live`
- 权威输入：`docs/FLASH_RC5_POST_H3_PARALLEL_TASKBOOK.md`、`docs/RC5_INTEGRATION_LIVE_RESULT.md` §7、`release/manifest-0.1.0-rc.5.yaml`、final Canary 证据（`.local/canary_final_b.jsonl` 及 NAS 副本）

## 0. 裁定

```text
H2 PREFLIGHT = READY_FOR_OPERATOR_DECISION
H2 LIVE RUN = NOT STARTED
CANARY PROC-RACE POLICY = EXPLICIT / TESTED
REAL SEND COUNT = 0
LIVE MUTATION COUNT = 0
```

本报告不构成 H2 授权。6 小时 H2 只能由唯一 Live 会话在 operator 明确选择
`H2_REQUIRED_AND_PASS` 且 Sending Gate（G9）完成之后启动（任务书 §0.9、§5）。

---

## 1. H1 — `/proc` race 口径明文化（已闭环）

### 1.1 原口径的三个缺口

1. **tolerance 是临场拼凑的**：final Canary strict 默认 `--max-proc-races 0` →
   INCOMPLETE（唯一原因：8 次瞬时 /proc 读竞态，8 个样本各 1 次、稀疏散布）；
   判 PASS 用的是临场加的 `--max-proc-races 8`，该数字无文档化依据，且 summary
   输出根本不记录当次使用的 tolerance。
2. **race 计数器混淆了三种失败模式**：采样器把「pid 目录消失（自然退出）」、
   「status 读一半撕裂但进程仍在」、「pid 仍在但持续不可读」全部计入
   `proc_race_count`。因此 tolerance=8 无法证明它容忍的只是自然消失 read race。
3. **无"不掩盖"证明**：没有测试证明 race tolerance 无法掩盖 EAGAIN/OOM/
   pids.events/watchdog 重启/单调增长等真实故障。

### 1.2 新 policy（已实现 + 测试）

**采样器**（`scripts/canary/wechat_cgroup_sample.sh`）：/proc 读失败按
"失败后立即复查 pid 目录 + 一次重试" 分类为两个独立计数器：

| 计数器 | 判定 | 含义 |
|---|---|---|
| `proc_race_count` | pid 目录已消失（自然退出），或一次立即重试后读取成功（退出中进程的撕裂读） | 唯一允许被 tolerance 覆盖的瞬态 race |
| `proc_read_error_count`（新增字段） | pid 仍在但重试后仍不可读 | 未解释的持续失败，**永不**被 tolerance 覆盖 |

- glob 之后、轮到它之前就消失的进程：静默跳过（不计任何计数器）——与 RC.5
  基线口径一致，避免膨胀历史对比。
- JSONL schema 增加 `tasks.proc_read_error_count`（`wechat-hub.canary.sample/v1`
  内新增可选字段，旧证据无此字段仍可判定）。

**判定器**（`scripts/canary/summarize_canary.py`）：

- `--max-proc-races` 保持显式参数（默认 0=strict，负值被拒绝）；**当次使用的
  tolerance 与实际 race 分布强制记录**在 summary 新增的 `proc_race_policy` 块：
  `definition`、`max_proc_races`、`races_total`、`samples_with_races`、
  `max_races_in_single_sample`、`read_errors_total`、`race_recheck_available`。
- `read_errors_total > 0` → 独立 INCOMPLETE 理由（无论 race tolerance 给多少）。
- 旧证据（无新字段）：`race_recheck_available=false` 并在 `recheck_note` 披露
  "无法区分 vanish race 与持续读失败"；判定结果不变。
- **非掩盖保证**（结构性 + 测试证明）：EAGAIN、thread constructor 失败、OOM、
  `pids.events`、watchdog kill/restart、单调任务增长、僵尸累积、
  pids.current 摸顶、auth 连续性、digest/wxid 身份全部是独立 FAIL 判据，
  优先级 FAIL > INCOMPLETE > PASS-CANDIDATE。无论 tolerance 放多大，
  这些信号出现即 FAIL。

### 1.3 批准的 tolerance 值（不许放宽成大数）

| 窗口 | 样本数 | tolerance | 依据 |
|---|---|---|---|
| 30min final Canary | 60 | **8** | 两个独立 final-artifact 窗口的实测 vanish-race 上界（R5 基线 66 样本/1979s：8 次，单样本 ≤2；final Canary 60 样本/1801s：8 次，单样本 ≤1） |
| 6h H2 | 360 | **48** | 同一 policy 按采样轮线性缩放：8/60 = 0.134 次/轮；race 由宿主进程churn驱动、按轮累积而非按小时累积，360 轮 × 0.134 ≈ 48 |

任何实测 race 超过上述 tolerance → INCOMPLETE（不是 FAIL）→ 硬停并交 operator
裁定，严禁改 tolerance 重算出 PASS。

### 1.4 测试与回归证据

- `tests/canary`：**62 passed, 1 skipped**（该 skip 为预存的 POSIX-only 信号量
  测试，win32 环境跳过）。新增覆盖：
  - 分类器：`test_persistent_read_errors_are_counted_separately_from_races`
    （present-but-unreadable → read_error，绝不计为 race）、
    `test_vanished_pid_counts_as_race_not_read_error`（用 FIFO 握手构造确定性
    的 mid-sweep 消失 → race 而非 read_error）。
  - 非掩盖证明：`test_races_within_tolerance_cannot_mask_{eagain,pids_events,
    oom,watchdog_restart,monotonic_thread_growth,zombie_accumulation}`。
  - policy 块：tolerance/分布记录、read-error 永不容忍、旧证据兼容。
- 旧证据回归：用新判定器重算 final Canary（`--max-proc-races 8` + 全部身份
  flags）仍为 `PASS-CANDIDATE, failure_reasons=[]`，与 manifest `49988a2` 记录
  一致，manifest 无需改动。
- 附注：`tests/observability` 有 1 个与本工作无关的预存环境性失败（其 `rel()`
  助手在系统 TEMP 位于项目外时报错）；observability 工具集不属于 canary
  tooling，本次未触碰。

---

## 2. H2 目标钉定（唯一权威组合）

| 项 | 权威值 |
|---|---|
| 目标账号 | B = `testB` |
| 权威 wxid | `wxid_rpfflqttdz4a22_7fcd` |
| AgentWechat digest | `sha256:2e6eff3f1ad8918ce5dd028be744bf464846878b6e898ba929d498f2df458019`（`0.11.15-wh.3`） |
| Runtime digest | `sha256:b5a0b0088ff7ff40803964d735fe110cd689c1dcfb6ea092a817204d01f85cb4`（`0.1.0-rc.6`） |
| PidsLimit | `512`（cgroup `pids.max` 与 `HostConfig.PidsLimit` 都必须等于 512） |
| B 容器名（final Canary 实测） | `wechat-agent-testb-a7c4f6c8`（drift 重建后名字保持；启动前仍须按 §4 重验） |
| Runtime 容器名 | `wechat-hub-f-live-runtime` |
| profile / duration / interval | `h2` / 21600s 证据窗 / 60s（runner 参数见 §5.3 时长算术） |
| 最低样本数 | 360 |
| proc-race tolerance | `--max-proc-races 48`（§1.3） |

## 3. status-url 校正（关键修正）

**权威值（唯一允许的 H2 status-url）**：

```text
http://127.0.0.1:8080/v1/runtime/accounts/testB/login
```

- 这是 Core 容器**内部视角**的 GET-only auth/status 路径，final Canary（L5）
  用它完成 60/60 轮 `http_ok` 采样，是当前 final stack 上唯一"已验证可工作"
  的口径。返回 `{"status":"logged_in","loggedInUser":"wxid_...","view":...}`。
- **禁止照抄** `docs/RC5_FINAL_LIVE_ACCEPTANCE_RUNBOOK.md` 里的
  `http://127.0.0.1:18080/api/status/auth`：18080 是历史 agent 直连端口，
  final 组合下 B 容器 `Ports=null`（无 host publish），该 URL 已不可用。
- **禁止**新增任何端口绑定或进被测容器取状态。
- Host 无 python：auth 探测经 `WECHAT_CANARY_PYTHON_BIN` wrapper 代理到
  Core 容器内执行（`docker exec -i <CORE_CONTAINER> python3`）。边界说明：
  exec 目标只有 Core（非被测容器，不影响测量口径）；每轮恰好 1 次 GET
  （urllib `method="GET"`，timeout=5s，无轮询、无循环 fork），每 60s 一次、
  有界；与 final Canary 的已验证机制一致。被测的 agent-wechat 容器保持
  "零 exec"（sampler 内建 destructive guard 继续拦截）。

## 4. H2 启动前 fail-closed 预检断言（全部 PASS 才允许开始）

由唯一 Live 会话在 NAS 上执行并记录输出到 `$RUN_DIR/preflight_assertions.txt`。
任何一条不满足 → 不启动 H2，报告 operator。

```bash
RUN_DIR=/mnt/user/appdata/wechat-hub-f-live/test/h2-soak-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$RUN_DIR/tooling"

# P1. B 容器身份/digest/限制/端口
docker inspect wechat-agent-testb-a7c4f6c8 \
  --format 'name={{.Name}} image={{.Config.Image}} pids={{.HostConfig.PidsLimit}} ports={{json .HostConfig.PortBindings}} state={{.State.Status}}'
# 断言：state=running；Config.Image 含 wh.3 digest；PidsLimit=512；PortBindings 为 null/{}

# P2. Runtime digest
docker inspect wechat-hub-f-live-runtime \
  --format 'image={{.Config.Image}} state={{.State.Status}}'
# 断言：含 rc.6 digest 且 running

# P3. Core 容器名解析（供 §5.2 wrapper 使用）
docker ps --format '{{.Names}}' | grep -i core
# 记录为 <CORE_CONTAINER>；若解析出多个，用 docker compose ps core 确认

# P4. B fresh auth（GET-only，经 wrapper 语义直接在 Core 内执行一次）
docker exec <CORE_CONTAINER> python3 -c \
  "import json,urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8080/v1/runtime/accounts/testB/login',timeout=5).read().decode())"
# 断言：status=logged_in，loggedInUser=wxid_rpfflqttdz4a22_7fcd（新鲜 auth，非缓存）

# P5. wrapper 冒烟（一次 GET 通过 wrapper 路径，见 §5.2 创建后执行）
"$RUN_DIR/tooling/pywrap-core-python3.sh" -c "print('wrapper-ok')"
# 并重跑一次 P4 等价 GET，确认 wrapper 输出含 logged_in

# P6. zero-send 基线
sqlite3 /mnt/user/appdata/wechat-hub-f-live/core/wechat_hub.db \
  "SELECT COALESCE(MAX(updated_at),'none') FROM outbox_messages;"
# 记录该值；H2 结束后必须不变（§7.3 再断言）

# P7. 无 desktop session / companion 残留
docker ps --format '{{.Names}}' | grep -i "companion\|selkies" || echo "no companion"
# 断言：无输出（no companion）

# P8. 工具 provenance（§5.1 复制后）
sha256sum "$RUN_DIR"/tooling/*
```

## 5. H2 执行包（仅唯一 Live 会话、仅 operator 授权后）

### 5.1 证据目录布局（AGENTS.md：test 数据统一在 Data Root/test/<run_id>/）

```text
$RUN_DIR/                              # /mnt/user/appdata/wechat-hub-f-live/test/h2-soak-<UTC时间戳>/
├─ .wechat-hub-managed.json            # managed marker: {"resource_type":"test-evidence","run":"h2-soak","created_by":"integration-posth3-live"}
├─ tooling/                            # canary 工具副本（来自本 commit 的 scripts/canary/）
├─ tooling.sha256
├─ preflight_assertions.txt            # §4 全部断言输出
├─ h2_soak_testb.jsonl                 # 6h 采样证据
├─ h2_soak_runner_stderr.log           # 每轮 flush 记录 + failed-round 警告（0 failed rounds 证据）
└─ h2_soak_summary.json                # 判定结果（本地镜像后产出，见 §6）
```

### 5.2 python wrapper（GET-only 探测代理）

```bash
cat > "$RUN_DIR/tooling/pywrap-core-python3.sh" <<'EOF'
#!/usr/bin/env bash
# Canary auth probe proxy: runs ONLY the sampler's stdin GET-only python
# program inside the Core container. The measured agent-wechat container is
# never exec'd into. One GET per round, 5s timeout, bounded.
exec docker exec -i <CORE_CONTAINER> python3 "$@"
EOF
chmod +x "$RUN_DIR/tooling/pywrap-core-python3.sh"
export WECHAT_CANARY_PYTHON_BIN="$RUN_DIR/tooling/pywrap-core-python3.sh"
```

### 5.3 采样命令与时长算术（为什么 `--duration 21600` 不够）

runner 的 deadline 约束的是每轮的**开始时刻**，而每轮实际耗时 =
`interval + 采样器运行时间 r`（final Canary 实测 r≈0.53s：59 轮间隔共 1801s）。
若直接 `--duration 21600 --interval 60`：

```text
第 k 轮开始时刻 ≈ (k-1)×(60+r) ≤ 21600 → k ≤ 1 + 21600/60.53 ≈ 357 轮
→ ~357 samples（< 360 最低样本）且 duration_seconds ≈ 356×60.53 ≈ 21548s（< 21600）
→ 按构建必 INCOMPLETE
```

因此 runner 参数取 **`--duration 22600`**（给 r 留出 [0.17, 2.94]s 安全域，
实测 0.53s），而**证据窗门槛不变**：`--minimum-duration 21600` +
`--minimum-samples 360`。预期产出 ~373 样本，墙钟约 6.3 小时。
启动后 6 小时内（任务书 §5）：

```text
不操作 Desktop、不发送任何消息、不重启 A/B/Runtime/Core、不做其他任何 NAS live mutation
```

```bash
"$RUN_DIR/tooling/wechat_canary_run.sh" \
    --output "$RUN_DIR/h2_soak_testb.jsonl" \
    --duration 22600 --interval 60 --profile h2 \
    --container wechat-agent-testb-a7c4f6c8 \
    --runtime-container wechat-hub-f-live-runtime \
    --status-url "http://127.0.0.1:8080/v1/runtime/accounts/testB/login" \
    --run-id "h2-soak-testb-$(date -u +%Y%m%dT%H%M%SZ)" \
    2> "$RUN_DIR/h2_soak_runner_stderr.log"
```

运行前置条件（任务书 §5）：Sending Gate 已完成且账号稳定在 Chat 态；
Stage S 与 H2 不并发。runner 支持安全中断（已 flush 样本全部保留），
但中断即放弃本轮 H2 判定，交 operator 决定是否重跑。

## 6. 判定（H2 PASS 判据，fail-closed）

优先在有 python 的机器上判定（工作区内与本 commit sha256 一致的工具副本；
jsonl 从 NAS 拉回后先对 sha256）。若必须在 NAS 上判定且 NAS 无 python：
`docker exec -i <CORE_CONTAINER> sh -c 'cat > /tmp/h2.jsonl && python3 /tmp/summarize_canary.py /tmp/h2.jsonl …' < h2_soak_testb.jsonl`（先 exec cat 分别送入 summarizer 与 jsonl——不使用 docker cp；分析临时文件判定后立即删除）。

```bash
python3 summarize_canary.py h2_soak_testb.jsonl \
    --minimum-duration 21600 \
    --minimum-samples 360 \
    --expected-pids-limit 512 \
    --expected-agent-wechat-digest "sha256:2e6eff3f1ad8918ce5dd028be744bf464846878b6e898ba929d498f2df458019" \
    --expected-runtime-digest "sha256:b5a0b0088ff7ff40803964d735fe110cd689c1dcfb6ea092a817204d01f85cb4" \
    --expected-wxid "wxid_rpfflqttdz4a22_7fcd" \
    --max-proc-races 48 \
    --output h2_soak_summary.json
```

**H2 PASS-CANDIDATE 必须同时满足（缺一即 fail-closed，不得出 PASS）：**

1. `outcome = PASS-CANDIDATE`，`failure_reasons = []`，`incomplete_reasons = []`；
2. `duration_seconds ≥ 21600` 且 `input_samples ≥ 360`；
3. `proc_race_policy.read_errors_total = 0`，`races_total ≤ 48`；
   `race_recheck_available = true`；
4. `pids.events`/EAGAIN/ctor/watchdog kill+restart/OOM 全 0 delta；无僵尸累积；
   进程数无单调/净增长；pids.current 峰值 < 512；
5. `auth`：全程 `logged_in`（view=Chat 若上报），`users_seen=[wxid_rpfflqttdz4a22_7fcd]`；
6. `identity`：observed digests 含 wh.3 与 rc.6 权威值；
7. runner stderr log：0 failed rounds。

FAIL → 硬停，保全证据，报告 operator，Production 继续 BLOCKED。
INCOMPLETE → 同样硬停（INCOMPLETE 不是 PASS；禁止调 tolerance 重算）。

## 7. H2 后置（summary/archive/continuity/garbage）

1. **证据归档**：`$RUN_DIR` 保留 jsonl/summary/断言/工具 sha256；本地镜像到
   仓库 `.local/h2-soak-<runid>/`。结果写入 readiness matrix 的 G10 证据行
   （由 Live 会话/operator 记录，本工具不 promote）。
2. **login continuity**（H2 结束后立即）：
   - 重复 §4 P4 的 fresh auth GET：必须 `logged_in` + 权威 wxid；
   - Core 投影 `state=online`（`docker exec <CORE_CONTAINER> …` 或 host
     `curl -s http://127.0.0.1:18082/v1/accounts`）；
   - 可选 UI 真值：短暂 desktop 会话确认 `view=Chat`（仅 H2 结束后进行；
     结束后验证 companion 对称回收，无 orphan）。
3. **zero-send 再断言**：§4 P6 记录的 `MAX(updated_at)` 不变；两 agent 容器
   日志 send 关键字 0 hits。
4. **garbage check**（AGENTS.md §12 格式报告）：
   - 无 H2 期间新增的 managed container/companion（除既有生产栈）；
   - wrapper 与工具副本属 `$RUN_DIR` 证据（Owner=Live 会话，随 RC.5 证据归档，
     由 operator 决定归档去留）；
   - 本地临时文件（拉回的 jsonl 校验副本等）在镜像完成后删除；
   - `resource cleanup: PASS / PARTIAL / FAIL` 明示。

## 8. 授权边界重申

- 本 preflight 全程 0 次 live mutation、0 次真实发送、未启动任何 soak。
- H2 启动需要 operator 明确选择 `H2_REQUIRED_AND_PASS`（任务书 §7 推荐），
  且 G9 Sending 完成在前；`H2_DEFERRED_BY_EXPLICIT_APPROVAL` 路径不运行本 §5-6。
- 本工具判定永远是 advisory：PASS-CANDIDATE ≠ promotion。
