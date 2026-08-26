#!/usr/bin/env bash
set -euo pipefail

IMAGE="${IMAGE:-samhudson02/sbotify}"
VERSION="${1:-$(uv version --short)}"
PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"

# refuse to release a dirty tree so the git tag matches what was built
if [ -n "$(git status --porcelain)" ] && [ "${ALLOW_DIRTY:-0}" != "1" ]; then
    echo "working tree has uncommitted changes; commit them or set ALLOW_DIRTY=1" >&2
    exit 1
fi

# ensure a buildx builder exists for multi-arch builds
docker buildx inspect sbotify-builder >/dev/null 2>&1 \
    || docker buildx create --name sbotify-builder --use

docker buildx build \
    --platform "$PLATFORMS" \
    -t "$IMAGE:$VERSION" \
    -t "$IMAGE:latest" \
    --push .

# tag the released commit and push the tag
if git rev-parse -q --verify "refs/tags/v$VERSION" >/dev/null; then
    echo "git tag v$VERSION already exists, skipping"
else
    git tag -a "v$VERSION" -m "Release v$VERSION"
    git push origin "v$VERSION"
fi
