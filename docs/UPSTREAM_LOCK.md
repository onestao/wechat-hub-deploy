# Upstream Lock

Lock date: 2026-08-31 (Asia/Shanghai)

The repositories below were cloned from the remotes required by the taskbook. `Commit` is the exact output of `git rev-parse HEAD`. `Dirty` was checked with `git status --porcelain=v1 --untracked-files=all` while overriding the inaccessible user-level excludes file with each repository's local `.git/info/exclude`.

| Repo | Remote | Branch | Commit | Dirty |
|---|---|---|---|---|
| linux-wechat-agent | https://github.com/xiaoguiwucan/linux-wechat-agent.git | main | `58b2c43ff18597c6d0c9ec47270eb40e4fb0b2bb` | no |
| wechat-selkies | https://github.com/nickrunning/wechat-selkies.git | master | `b3b5341a26b803e06a1a7daaf420151297da4e79` | no |
| efb-wechat-comwechat-slave | https://github.com/ehForwarderBot/efb-wechat-comwechat-slave.git | master | `989db6947f565dbbb5588d04edfca3cf5ca49c24` | no |
| efb-wechat-slave | https://github.com/ehForwarderBot/efb-wechat-slave.git | master | `80dadf21558c1be28d7ec23f247383b5a229975b` | no |
| kettly1260/efb-telegram-master | https://github.com/kettly1260/efb-telegram-master.git | dev | `36b3382ed784efeba176dba269df47d4df0ef4e7` | no |

## Local Paths

| Repo | Path |
|---|---|
| linux-wechat-agent | `upstream/linux-wechat-agent` |
| wechat-selkies | `upstream/wechat-selkies` |
| efb-wechat-comwechat-slave | `upstream/efb-wechat-comwechat-slave` |
| efb-wechat-slave | `upstream/efb-wechat-slave` |
| kettly1260/efb-telegram-master | `upstream/efb-telegram-master-kettly` |

The `upstream/` checkouts are read-only source references for the work packages. Implementation happens in independent copies under `work/`.
