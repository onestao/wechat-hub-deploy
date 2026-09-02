# WeChat Hub Deploy

This repository is the deploy and release coordination source of truth. It
holds release manifests, deployment wiring, contracts, mock Core, release
reports, and coordination documents.

It intentionally does not contain the service source trees under `work/`.
Service changes belong in their own repositories:

- `wechat-hub-runtime`
- `wechat-hub-core`
- `wechat-hub-console`
- `wechat-hub-agent`
- `wechat-hub-efb-linux-wechat-slave`

Release images must be promoted by immutable digest. Do not use `latest` in
production compose or manifests.
