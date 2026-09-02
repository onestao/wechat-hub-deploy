# GHCR Private Image Pull Guide (Unraid / Linux Host)

## Prerequisites

Create a dedicated read-only PAT (classic) scoped to `read:packages` only:

1. Go to https://github.com/settings/tokens (classic tokens).
2. Generate a new token with the `read:packages` scope.
3. Name it e.g. `wechat-hub-ghcr-pull`.
4. Do NOT grant `write:packages`, `delete:packages`, or `repo`.

## Login

```bash
echo "<TOKEN>" | docker login ghcr.io --username <your-github-username> --password-stdin
```

For Unraid, the credential lands in `/root/.docker/config.json` (or the
docker daemon user's config). It is never written to compose files or
environment files.

## Pull the pinned digest

```bash
docker pull ghcr.io/onestao/wechat-hub-runtime@sha256:<digest>
```

Digests are recorded in `release/manifest-*.yaml`. Never pull `:latest`
in production.

## Security Notes

- The pull token is read-only; it cannot push or delete packages.
- Do not commit the token or `config.json` to any repository.
- When rotating tokens, log out first:
  `docker logout ghcr.io`
