#!/bin/bash
exec > /root/rc14-filevoice-pull.log 2>&1
TAG=ghcr.io/onestao/wechat-hub-core:0.1.0-rc.14-core-filevoice-media-ref
echo "START_UTC=$(date -u "+%Y-%m-%dT%H:%M:%SZ")"
docker pull "$TAG"
echo "PULL_RC=$?"
docker image inspect "$TAG" --format "CONFIG_ID={{.Id}}"
docker image inspect "$TAG" --format "OCI_REVISION={{index .Config.Labels \"org.opencontainers.image.revision\"}}"
docker image inspect "$TAG" --format "OCI_VERSION={{index .Config.Labels \"org.opencontainers.image.version\"}}"
docker image inspect "$TAG" --format "IMAGE_CREATED={{.Created}}"
docker image inspect "$TAG" --format "REPO_DIGESTS={{json .RepoDigests}}"
docker image inspect "$TAG" --format "IMAGE_SIZE={{.Size}}"
docker images --digests --format "{{.Repository}}:{{.Tag}}|{{.Digest}}|{{.ID}}" | grep wechat-hub-core
echo "END_UTC=$(date -u "+%Y-%m-%dT%H:%M:%SZ")"
