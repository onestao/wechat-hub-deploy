# WeChat Hub 主线部署说明

这个目录是当前主线唯一推荐的部署入口。不要混用根目录历史 RC Compose、旧候选镜像或测试报告里的临时命令。
本批镜像已通过 GitHub 自动构建和测试，尚未替换 NAS 测试环境的真实账号容器进行整套实机验收。已发布镜像的固定摘要和构建记录见 [`release/main-source-lock.yaml`](../release/main-source-lock.yaml)。
`.env` 中每个参数、数据目录及 EFB 配置文件的用途见 [配置说明](CONFIGURATION.zh-CN.md)。

## 免责声明（Disclaimer）

> 本项目仅供 Linux 桌面环境与消息协议学习交流，请勿用于商业及批量营销。使用者因违规操作导致账号受限与开发者无关。

## 组件和架构

| 组件 | GHCR 镜像 | amd64 | arm64 | 说明 |
| --- | --- | --- | --- | --- |
| Runtime | `ghcr.io/onestao/wechat-hub-runtime:main` | 支持 | 支持 | 微信桌面、账号和子容器管理 |
| Core | `ghcr.io/onestao/wechat-hub-core:main` | 支持 | 支持 | 消息、事件、媒体和发送队列 |
| Console | `ghcr.io/onestao/wechat-hub-console:main` | 支持 | 支持 | Web 管理界面 |
| EFB | `ghcr.io/onestao/wechat-hub-efb-linux-wechat-slave:main` | 支持 | 支持 | 可选的 Telegram 转发 |
| AgentWechat | `ghcr.io/onestao/wechat-hub-agent-wechat:main` | 支持 | 暂不发布 | 当前真实账号验收使用的是固定 amd64 微信运行底座 |

因此，**完整五组件部署当前要求 x86-64/amd64 主机**。arm64 可以运行 Runtime、Core、Console 和 EFB，但不能宣称完整真实微信链路已经通过。
`main` 和 `latest` 会在每次主线构建时指向同一镜像；这两个标签都不是固定版本。下文默认使用 `main`，长期部署请按发布锁文件改用验收过的镜像摘要。
**源码仓库公开不等于 GHCR 镜像包公开。** 维护者须分别核对 Runtime、Core、Console、EFB、AgentWechat 五个镜像包的可见性，并从未登录的环境验证全部可拉取，才能向其他用户宣称下面的免登录部署步骤可用。若某个镜像包仍为 Private，有读取权限的账号需要先执行 `docker login ghcr.io`。

## 1. 准备

主机需要 Docker Engine 24+ 和 Docker Compose v2。建议至少 4 核、8 GB 内存，并为微信数据准备独立持久化目录。

```bash
git clone https://github.com/onestao/wechat-hub-deploy.git
cd wechat-hub-deploy/deploy
cp .env.example .env
mkdir -p data/runtime/config data/runtime/state data/core data/console
```

此时 `WECHAT_HUB_DATA=./data` 即使用刚创建的 `deploy/data/`。如需放到 Unraid 的持久化目录，先创建对应目录，再编辑 `.env`：

```text
PASSWORD=一个新的强密码
WECHAT_HUB_DATA=/mnt/user/appdata/wechat-hub
```

`WECHAT_HUB_DATA` 必须指向宿主机上的真实持久化路径。账号登录数据、Core 数据库和 Console 数据都保存在这里；EFB 的游标和去重账本由 `EFB_PROFILE_DIR` 保存，也必须备份。不要把这个示例 Compose 直接覆盖到现有 NAS 测试环境；迁移已有账号数据前应单独核对容器配置和卷路径。

## 2. 启动主链路

```bash
docker compose pull
docker compose up -d wechat-runtime wechat-core wechat-console
docker compose ps
```

若拉取 GHCR 镜像提示无权限，先确认对应镜像包的可见性；有读取权限的账号可执行 `docker login ghcr.io` 后重试。不要在 `.env` 中保存 GitHub 令牌。公开源码仓库或补上 `latest` 标签都不会自动改变包的访问权限。

浏览器打开：

- Console：`http://主机IP:8078`
- Runtime 桌面：`http://主机IP:3000`
- AgentWechat 桌面网关：`http://主机IP:17892`

Core 默认只监听宿主机 `127.0.0.1:8080`，不会直接暴露到局域网。

## 3. 添加真实微信账号

1. 打开 Console 的“微信账号”。
2. 新建账号时选择 `agent_wechat` 运行方式。
3. 启动账号，等待 AgentWechat 子容器创建完成。
4. 点击扫码登录，或打开完整微信桌面扫码。
5. 登录后确认账号状态为 `online / logged_in`。

Runtime 是唯一有权访问 `/var/run/docker.sock` 的组件。它按账号创建 AgentWechat 子容器；不要再手工启动第二个相同账号容器，否则会造成数据卷和微信登录冲突。

## 4. 启用 EFB/Telegram

先复制示例配置：

```bash
cp -a efb-profile.example efb-profile
mv efb-profile/profiles/default/blueset.telegram/config.yaml.example \
  efb-profile/profiles/default/blueset.telegram/config.yaml
chmod 600 efb-profile/profiles/default/blueset.telegram/config.yaml
```

编辑 Telegram 配置，只填写自己的 Bot Token 和管理员 Telegram 数字 ID。不要把真实配置提交到 Git。

启动 EFB：

```bash
docker compose --profile efb up -d wechat-efb
docker compose logs --tail 100 wechat-efb
```

验收顺序：先从微信发送一条新文本，再发送一张图片或表情；确认 Core 产生新事件，随后 Telegram 收到相同内容。EFB 的历史游标追平不等同于实时收信通过，必须用新消息验证。

## 5. 更新和回退

更新主线镜像：

```bash
docker compose pull
docker compose up -d
```

已启用 EFB 的部署还需执行：

```bash
docker compose --profile efb pull
docker compose --profile efb up -d
```

正式长期运行时，建议把 `.env` 中的 `:main` 改成已经验收的 `sha-*` 标签或 `@sha256:...` 摘要，避免下一次主线构建自动改变运行内容。
GitHub 构建通过仅证明镜像可以构建且自动化测试通过，不等于在真实微信账号上完成新镜像的收发验收。

回退前先保存当前镜像摘要：

```bash
docker compose images
docker inspect wechat-hub-runtime wechat-hub-core wechat-hub-console wechat-hub-efb
```

然后把 `.env` 中对应镜像改回上一摘要并执行 `docker compose up -d`。不要删除 `WECHAT_HUB_DATA`，回退镜像不应同时删除账号和数据库。

## 6. 安全边界

- `deploy/.env`、`deploy/data/`、`deploy/efb-profile/` 已加入忽略规则。
- 不要向公网直接开放 3000、8078、17892；远程访问应放在带认证的 HTTPS 反向代理或 VPN 后面。
- 不要把 Telegram Token、微信数据卷、Core SQLite 或 AgentWechat token 放进仓库。
- AgentWechat 数据库迁移 SQL 被强制为 LF，构建流程还会核对固定 SHA256，防止 Windows CRLF 再次导致迁移校验失败。
