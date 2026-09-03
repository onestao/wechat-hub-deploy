## WeChat Hub 数据目录与资源生命周期硬规则

### 1. 统一数据根目录

所有需要映射到 Host 的 WeChat Hub 持久化数据，必须统一放在一个用户可见、可管理的数据根目录下。

Unraid 默认建议：

```text
/mnt/user/appdata/wechat-hub
```

允许通过统一环境变量覆盖：

```text
WECHAT_HUB_DATA_ROOT=/mnt/user/appdata/wechat-hub
```

禁止各组件自行在 Host 上随意创建新的持久化目录。

禁止将持久化业务数据散落在：

```text
/tmp
/var/tmp
/root
/home/<random>
项目源码目录
随机 Docker volume
随机 NAS 目录
```

------

### 2. 推荐目录结构

生产数据统一组织为：

```text
${WECHAT_HUB_DATA_ROOT}/
├─ runtime/
├─ core/
├─ console/
├─ agent/
├─ efb/
├─ accounts/
│  ├─ <account_id>/
│  │  ├─ data/
│  │  ├─ home-wechat/
│  │  ├─ browser-files/
│  │  └─ runtime/
│  └─ <account_id-2>/
│     └─ ...
└─ test/
```

其中每个微信账号的：

```text
/data
/home/wechat
browser-files
需要 Host 持久化的账号级 runtime 数据
```

必须映射到：

```text
${WECHAT_HUB_DATA_ROOT}/accounts/<account_id>/
```

不同账号禁止共用同一个持久数据目录。

------

### 3. Docker Volume 规则

禁止创建无法追踪所有者的 anonymous volume。

如果使用 Docker named volume，只允许：

1. 名称可确定；
2. 带 WeChat Hub managed label；
3. 明确绑定 account_id / service；
4. 实际 Host 数据目录仍位于 `WECHAT_HUB_DATA_ROOT` 下。

例如 local-driver bind volume 可以使用，但其 `device=` 必须解析到：

```text
${WECHAT_HUB_DATA_ROOT}/...
```

不得让生产数据长期隐藏在不可追踪的随机：

```text
/var/lib/docker/volumes/<random>/
```

中。

------

### 4. 资源必须有明确 Owner

所有由 WeChat Hub 创建的：

- container
- companion container
- bind directory
- named volume
- browser-files
- X11/runtime directory
- test directory

都必须可以确定其 Owner。

Docker 资源至少使用：

```text
com.wechat-hub.managed=true
com.wechat-hub.account-id=<account_id>
com.wechat-hub.resource-type=<type>
```

账号目录建议建立 WeChat Hub managed marker，例如：

```text
.wechat-hub-managed.json
```

记录：

```text
account_id
resource_type
created_by
```

用于安全 cleanup。

------

### 5. Stop / Restart / Upgrade / Rollback 不删除数据

以下操作只是生命周期切换，不代表用户不要数据：

```text
stop
restart
container recreate
image upgrade
RC deploy
rollback
temporary SIGSTOP
health recovery
```

这些操作必须保留：

- `/data`
- `/home/wechat`
- browser-files
- Core DB
- Console DB
- account registry
- credential
- 用户持久数据

不能因为 container recreate 就删除账号目录。

------

### 6. 真正删除账号时必须同时清理资源

如果用户明确执行：

```text
删除微信账号
永久删除账号
remove account + delete data
purge account
```

则不能只删除 container 而留下大量垃圾。

必须清理该账号全部由 WeChat Hub 管理的资源，包括：

```text
primary AgentWechat container
Selkies companion
账号级临时 container
账号级 managed volumes
accounts/<account_id>/data
accounts/<account_id>/home-wechat
accounts/<account_id>/browser-files
accounts/<account_id>/runtime
账号级 X11/runtime leftovers
账号级 desktop session descriptors
```

最终要求：

```text
账号不存在
→ 不应残留该账号的 managed container
→ 不应残留该账号的 managed volume
→ 不应残留该账号的 managed data directory
```

------

### 7. 删除临时测试资源必须收尾

Agent 创建的：

- Canary container
- Gate container
- temporary test volume
- temporary bind directory
- build context
- test file
- screenshot
- marker
- probe directory

如果任务结束后不再需要，必须在任务结束前删除。

测试数据统一优先放入：

```text
${WECHAT_HUB_DATA_ROOT}/test/<run_id>/
```

或明确的项目临时目录。

成功或失败退出时都必须执行 cleanup。

禁止每次测试产生新的永久目录而不回收。

------

### 8. 创建失败也必须清理半成品

资源创建过程如果发生：

```text
container create succeeded
但后续 start / health / mount / initialization failed
```

不得留下无主半成品。

Agent/代码必须清理本次操作新创建且确认未被使用的：

- container
- companion
- volume
- empty directory
- temporary secret
- temporary session

但不得因此删除升级前已经存在的生产数据。

------

### 9. 删除必须 Fail-Closed

任何自动删除前必须验证：

1. canonical path 位于 `WECHAT_HUB_DATA_ROOT` 内；
2. 资源具有 `com.wechat-hub.managed=true` 或等价 managed marker；
3. account_id / resource owner 匹配；
4. 路径不存在 `..` escape；
5. resolved path 没有通过 symlink 跳出 Data Root。

任何一项无法确认：

```text
拒绝删除
```

并报告给用户。

绝不能为了 cleanup 使用模糊路径递归删除。

------

### 10. 禁止全局 Prune

任何 Agent、部署脚本、rollback、测试脚本均禁止执行：

```text
docker system prune
docker volume prune
docker container prune
```

作为正常清理手段。

只能删除：

```text
本任务明确创建
+
具有 WeChat Hub managed ownership
+
确认已经不再需要
```

的具体资源。

不得影响 NAS 上其他项目。

------

### 11. Container 删除与数据删除必须语义明确

必须区分：

```text
停止服务
```

和：

```text
永久删除
```

推荐行为：

```text
Stop
→ 保留 container/data 或仅停止 container

Restart/Recreate/Upgrade
→ 可以替换 container
→ 必须保留数据

Remove container only
→ 删除 container
→ 如果账号仍存在，则保留数据

Delete account permanently
→ 删除 container
→ 删除 companion
→ 删除账号 managed volumes
→ 删除账号 managed directories

Delete temporary/test deployment
→ container + 对应 test directory/volume 一起删除
```

不得出现：

```text
container 已永久废弃
但相关 test/data 目录无限累积
```

------

### 12. Agent 任务结束前必须做 Garbage Check

所有涉及 Docker / Runtime / NAS 的 Agent，在 completion report 前必须检查本次任务是否遗留：

```text
unexpected managed containers
orphan test volumes
orphan test directories
temporary secrets
temporary build directories
temporary Desktop sessions
temporary marker files
```

报告至少写明：

```text
resource cleanup: PASS / PARTIAL / FAIL
```

如有 intentionally preserved resource，必须说明：

```text
资源名称
Owner
为什么需要保留
后续由谁删除
```

不能简单留下一堆“以后可能有用”的目录。

------

### 13. Release / H3 特别规则

H3 Canary、RC deploy、rollback 期间：

```text
升级/回滚
≠
删除账号
```

所以必须保留生产账号数据。

但是 H3 自己创建的：

```text
临时 Canary 容器
临时测试目录
临时测试 volume
临时 marker
临时 deployment artifacts
```

在不再需要后必须清理。

最终生产部署应只留下：

```text
当前有效 container
当前有效账号数据
当前有效持久数据库
当前有效 Release 配置
```

而不是保留所有历史测试实例。

------

### 14. 核心原则

遵守：

```text
一个统一 Data Root
+
每资源明确 Owner
+
创建时登记
+
删除时对称清理
+
升级/回滚保留业务数据
+
永久删除时不留垃圾
+
绝不全局 prune
```

任何新 Runtime Provider、Desktop Provider、Container 或测试工具都必须遵守本规则。

------

### 15. Subprocess 与 Container 资源防护硬规则 (P0 防护)

任何能够创建大量 subprocess、worker 线程或 dynamic companion container 的组件，必须满足以下硬规则：

1. **强制 cgroup PidsLimit 防护**
   - 任何由 WeChat Hub 编排的 container 必须配置明确的 `PidsLimit`（严禁 `<nil>` / `max`）。
   - Selkies companion container：默认 `PidsLimit = 100` (`WECHAT_SELKIES_PIDS_LIMIT`)。
   - AgentWechat primary container：默认 `PidsLimit = 256` (`AGENT_WECHAT_PIDS_LIMIT`)。
   - WeChat Runtime 容器：默认 `pids_limit: 200`。
   - Core / Console / Agent / EFB 容器：默认 `pids_limit: 100`。
   - 严禁允许单 container 无限制 fork 进程拖垮 Host 内核调度队列。

2. **资源隔离与 Fail-Closed**
   - 单 companion 或容器内进程耗尽 PID 或 OOM 时，必须仅由其自身 cgroup fail-closed（收到 `-EAGAIN` 或终止该 companion），严禁突破 cgroup 影响 Host 或其他账号容器。
   - 任何账号 A 的 companion failure 不得影响账号 B 的正常运行与 Desktop 访问。
   - 严禁使用 `oom_kill_disable` 等方式阻止宿主机保护自身。

3. **Desktop Session 生命周期对称清理与 Orphan 防治**
   - 当最后一个 Desktop control session（如 WebSocket / 浏览器连接）断开或过期，必须触发自动生命周期回收。
   - 闲置 companion 容器必须在短 TTL（默认 10 秒）后彻底销毁，严禁 orphan companion 长期驻留。
   - Shell entrypoint 或容器终止时，必须通过 trap 递归清理子进程树（`pkill -P` 及 `pkill -u`），彻底 reap `xclip` 或辅助 helper。

4. **无界 Subprocess 轮询严禁启用**
   - 默认彻底禁用未经验证的剪贴板轮询或未 reap 的外部 CLI 调用（如 `xclip`）。
   - 除非处于安全上下文且具备严格的 timeout + wait/reap 机制，否则不得在循环中反复 fork 子进程。

5. **任务结束垃圾检查 (Task Garbage Check)**
   - 任何执行自动化测试、benchmark、profiling 或 canary 的 Agent，必须在退出前验证进程与容器计数。
   - 若发现任何单调增长的 subprocess、zombie 进程或 orphan companion，判定为 FAIL 并阻断发布。

