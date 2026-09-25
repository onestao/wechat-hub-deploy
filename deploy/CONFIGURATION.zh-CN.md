# WeChat Hub 配置说明

本页对应当前目录的 `.env.example`、`compose.yaml` 和 `efb-profile.example/`。先复制 `.env.example` 为 `.env`，在 `deploy/` 目录内编辑；修改后用 `docker compose config` 检查展开结果，再用 `docker compose up -d` 应用。`.env` 不是运行中的容器热配置。启用 EFB 后，更新时还须加 `--profile efb`，具体命令见 [部署说明](README.zh-CN.md)。

普通用户首次部署只需设置强 `PASSWORD`、确认 `WECHAT_HUB_DATA`、按需设置对外端口。需要 Telegram 转发时，再填写 EFB 配置。其余参数建议保持示例值。

## 基础与数据

| `.env` 参数 | 示例值 | 作用及何时修改 |
| --- | --- | --- |
| `TZ` | `Asia/Shanghai` | 容器时区；不在此时区才修改。 |
| `PUID` / `PGID` | `1000` / `100` | Runtime 写入挂载目录时使用的宿主机用户、组 ID；应与数据目录的实际所有者权限匹配。 |
| `PASSWORD` | `change-this-password` | Runtime Web 桌面的访问密码；**必须换成强密码**。它不替代对 Console 等其他端口的网络访问控制。 |
| `WECHAT_HUB_DATA` | `./data` | 宿主机持久化数据根目录。相对路径以 `deploy/` 为基准；Unraid 可改为 `/mnt/user/appdata/wechat-hub` 等绝对路径。更改现有部署的路径前必须迁移原数据，不能仅改这一行。 |
| `WECHAT_HUB_NETWORK` | `wechat-hub-internal` | Compose 内网及 Runtime 创建的 AgentWechat 子容器共用的 Docker 网络名；现有部署不要随意改名，否则子容器和 Core 可能无法互通。 |

`WECHAT_HUB_DATA` 下的主要目录：

| 目录 | 保存内容 |
| --- | --- |
| `runtime/config/` | Runtime 配置、账号注册表、`agent-wechat/` 下每个账号的登录数据、令牌和微信数据。 |
| `runtime/state/` | Runtime 运行状态及供 Core 使用的控制 socket；由服务启动时生成，不应手工编辑。 |
| `core/` | Core 消息库等持久化数据。 |
| `console/` | Console 运行数据。 |

备份时至少包含 `runtime/config/`、`core/`、`console/`，启用 EFB 的还要包含下述 `EFB_PROFILE_DIR`。不要仅备份 Compose 文件，也不要用 `docker compose down -v` 或删除账号绑定卷来“重装”。Runtime 通过 Docker 创建的 AgentWechat 命名卷绑定到 `runtime/config/agent-wechat/` 中的实际宿主机目录。

## 镜像版本

| `.env` 参数 | 用途 |
| --- | --- |
| `RUNTIME_IMAGE` | Runtime 桌面及账号管理容器的镜像。 |
| `CORE_IMAGE` | Core 消息、事件、媒体及发送队列容器的镜像。 |
| `CONSOLE_IMAGE` | Web 管理界面的镜像。 |
| `EFB_IMAGE` | 可选 EFB/Telegram 转发容器的镜像。 |
| `AGENT_WECHAT_IMAGE` | Runtime 按账号创建的 AgentWechat 子容器默认镜像；账号注册表内若显式指定镜像，则账号设置优先。 |

示例的五项都使用 `:main`；每次主线发布也同时更新同一镜像的 `:latest` 别名，两者都是可变标签。长期运行应从 [发布锁文件](../release/main-source-lock.yaml) 选取已经验收的 `@sha256:...` 摘要逐项填写；改动镜像项并重建 Compose 容器，不保证已经运行的 AgentWechat 子容器随之切换，需核对账号注册表及子容器的实际镜像。完整微信链路目前仅在 `amd64` 有 AgentWechat 镜像。

## 对外访问

下列 `*_BIND` 是**宿主机监听地址**，`*_PORT` 是**宿主机端口**。`0.0.0.0` 允许其他机器访问，`127.0.0.1` 只允许本机访问；更改端口后须使用新端口访问并检查防火墙、反向代理映射。它们不改变容器间的内部地址。

| `.env` 参数 | 示例值 | 作用 |
| --- | --- | --- |
| `RUNTIME_HTTP_BIND` / `RUNTIME_HTTP_PORT` | `0.0.0.0` / `3000` | Runtime Web 桌面的 HTTP 入口。 |
| `RUNTIME_HTTPS_BIND` / `RUNTIME_HTTPS_PORT` | `0.0.0.0` / `3001` | Runtime Web 桌面的 HTTPS 端口映射。 |
| `DESKTOP_GATEWAY_BIND` / `WECHAT_DESKTOP_GATEWAY_PORT` | `0.0.0.0` / `17892` | AgentWechat 账号桌面网关的宿主机入口；网关还使用同一容器端口。 |
| `CONSOLE_BIND` / `CONSOLE_PORT` | `0.0.0.0` / `8078` | Console Web 管理入口。 |
| `CORE_BIND` / `CORE_PORT` | `127.0.0.1` / `8080` | Core API 的宿主机映射，默认不向局域网开放；Console 和 EFB 仍通过 Docker 内网访问 `wechat-core:8080`。 |

不要直接向公网开放这些端口。尤其是 Console 和桌面网关，不应因为设置了 `PASSWORD` 就认为所有入口都受其保护。

## 账号与资源

| `.env` 参数 | 示例值 | 作用及注意事项 |
| --- | --- | --- |
| `AUTO_START_WECHAT` | `true` | Runtime 启动时引导账号注册表，并启动标记为自动启动的账号；设为 `false` 后需手工启动账号。 |
| `ENABLE_WECHAT_AUTO_LOGIN` | `true` | 控制旧版桌面微信的自动登录辅助程序；不是免扫码保证，也不负责 AgentWechat 的会话恢复。 |
| `WECHAT_ACCOUNTS` | 空 | **仅在注册表首次创建时**用逗号分隔的账号 ID 初始化账号；留空会创建 `default` 账号。注册表已存在时改此值不会覆盖现有账号，应在 Console 管理账号。 |
| `WECHAT_DEFAULT_ACCOUNT_ID` | `default` | Runtime 命令未指定账号 ID 时使用的默认目标；不会重命名已有账号。 |
| `WECHAT_LEGACY_DEFAULT_ACCOUNT` | `true` | 首次初始化 `default` 时沿用旧版 `abc` 用户及 `/config` 主页的布局。不是切换账号运行方式的开关；已有注册表不受事后修改影响。 |
| `AGENT_WECHAT_SHM_MB` | `512` | 每个 AgentWechat 子容器的共享内存大小，单位 MiB；代码至少使用 64 MiB。 |
| `AGENT_WECHAT_PULL_TIMEOUT` | `900` | Runtime 拉取 AgentWechat 镜像的超时秒数；代码至少使用 60 秒，网络较慢时才增加。 |
| `WECHAT_SELKIES_ATTACH_ENABLED` | `true` | 允许在 HTTPS 公共入口下使用 Selkies 账号桌面；HTTP 入口会使用 noVNC。设为 `false` 禁用 Selkies 接入，不会关闭桌面网关。 |
| `RUNTIME_SHM_SIZE` | `1gb` | Runtime 主容器的共享内存大小，与上面的 AgentWechat 子容器设置不同。 |

## Core 与 EFB

| `.env` 参数 | 示例值 | 作用及注意事项 |
| --- | --- | --- |
| `CORE_SYNC_INTERVAL` | `5` | Core 同步账号数据的间隔秒数；`0` 关闭自动同步。 |
| `CORE_SEND_INTERVAL` | `1` | Core 处理待发送消息的间隔秒数；`0` 关闭自动发送循环。 |
| `CORE_REGISTRY_RELOAD_INTERVAL` | `1` | Core 检查 Runtime 账号注册表变更的间隔秒数；`0` 关闭自动重新加载。 |
| `EFB_PROFILE_DIR` | `./efb-profile` | EFB 的宿主机配置和运行数据目录，含游标、消息映射及去重账本；启用 Telegram 后必须持久化并备份。 |

EFB 使用 `--profile efb` 才会启动，未启用时不需要创建 Telegram 配置。不要为了“从头收信”随意更换 profile 目录或删除游标、账本。

## 桌面网关的外部地址

这三项只影响 Runtime **返回给浏览器的账号桌面地址**，不负责开启 TLS，也不改变上面的宿主机监听地址。没有反向代理时保持示例值。

| `.env` 参数 | 示例值 | 作用 |
| --- | --- | --- |
| `WECHAT_DESKTOP_GATEWAY_PUBLIC_SCHEME` | `http` | 浏览器实际使用的协议。仅在可信反向代理确实提供 HTTPS 时设为 `https`；显式请求 Selkies 必须使用 HTTPS。 |
| `WECHAT_DESKTOP_GATEWAY_PUBLIC_HOST` | 空 | 浏览器可访问的网关域名或主机名；通过反向代理使用固定域名时填写。 |
| `WECHAT_DESKTOP_GATEWAY_PUBLIC_PORT` | 空 | 浏览器访问反向代理的外部端口；留空时 Runtime 使用网关内部端口值，代理改端口时应明确填写。 |

例如反向代理将 `https://wechat.example.com:443` 转发到网关时，可设置 `SCHEME=https`、`HOST=wechat.example.com`、`PORT=443`。需在 `.env` 中填写上述**完整变量名**，并确保代理同时转发 WebSocket。

## EFB 配置文件

从 `efb-profile.example/` 复制出 `efb-profile/` 后，三个文件分别承担不同职责：

| 路径（相对 `EFB_PROFILE_DIR`） | 字段 | 用途 |
| --- | --- | --- |
| `profiles/default/config.yaml` | `master_channel: blueset.telegram` | Telegram 为接收和回复的主通道。 |
| 同上 | `slave_channels: [wechat.linux]` | 将本项目微信通道接入 EFB。 |
| 同上 | `middlewares: []` | 不启用额外中间件；保持默认即可。 |
| `profiles/default/blueset.telegram/config.yaml` | `token` | 自己创建的 Telegram Bot Token，属于密钥；不可提交到 Git。 |
| 同上 | `admins` | 允许管理这个 Bot 的 Telegram **数字用户 ID 列表**，不是用户名或群 ID。 |
| `profiles/default/wechat.linux/config.yaml` | `core.base_url` | EFB 容器访问 Core 的地址，Compose 中保持 `http://wechat-core:8080`，不要写宿主机 `127.0.0.1`。 |
| 同上 | `core.timeout` | Core 普通 HTTP 请求超时秒数。 |
| 同上 | `core.poll_timeout` | 等待 Core 新事件的长轮询秒数，代码最多使用 30 秒。 |
| 同上 | `core.verify_tls` | 使用 HTTPS Core 时校验其证书；保持 `true`，当前 HTTP 内网地址不涉及证书校验。 |
| 同上 | `account_ids` | 要转发的 Core 账号 ID 列表；`[]` 表示不按账号过滤。若只转发一个账号，写成 `["实际账号ID"]`。 |
| 同上 | `consumer_id` | Core 消费者及 EFB 游标的身份前缀；部署后保持不变，改动会形成不同的消费进度。 |
| 同上 | `poll_interval` | 没有事件时再次轮询前的等待秒数。 |
| 同上 | `event_limit` | 每页最多取多少事件，代码限制在 1 到 200。 |
| 同上 | `startup_healthcheck` | 启动时检查 Core；暂时连不上会记录警告并继续重试，接口契约错误仍会报错。 |

首次启用 EFB 默认从当前事件队头建立订阅，**不会自动把全部旧消息补发到 Telegram**。EFB 游标、去重账本和 Core 消费者身份是一组数据；迁移或回退时应整体保留，而不是只复制 Bot Token。

## Compose 中的固定设置

`compose.yaml` 中的账号注册表路径、Runtime 控制 socket、Console 的 `WECHAT_CORE_URL`、EFB 的 Core 内网地址已按四个容器的挂载和网络关系配套设置，普通部署不需要修改。Runtime 挂载 `/var/run/docker.sock` 才能创建账号子容器，因而等同于赋予其较高的宿主机控制权限；不要在不可信主机运行，也不要把这些内部接口暴露到公网。剪贴板相关项被锁定为禁用，不是供用户打开的选项。
