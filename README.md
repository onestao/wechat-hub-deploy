# WeChat Hub Deploy

这是 WeChat Hub 的部署与发布协调仓库。当前主线部署入口是
[`deploy/README.zh-CN.md`](deploy/README.zh-CN.md)，其中包含完整的 Compose、环境变量、
EFB 配置模板、更新和回退说明。

组件源码分别维护在独立仓库：

- `wechat-hub-runtime`
- `wechat-hub-core`
- `wechat-hub-console`
- `agent-wechat`（发布为 `wechat-hub-agent-wechat` 镜像）
- `wechat-hub-efb-linux-wechat-slave`

`main` 镜像用于持续集成和测试。长期部署应在验收后改用 `sha-*` 标签或不可变镜像摘要，
不要使用 `latest`。
