#!/usr/bin/env bash
# Build @devdash/ui + the standalone UI and bundle it into the Python package's
# static dir, so the wheel / Docker image serve the real dashboard. Run before
# building the wheel or the Docker image.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATIC="$ROOT/packages/api/src/devdash/static"

pnpm -C "$ROOT" install --frozen-lockfile
pnpm -C "$ROOT/packages/ui" build
pnpm -C "$ROOT/standalone-ui" build

# Replace the dev placeholder with the built bundle.
find "$STATIC" -mindepth 1 -not -name '.gitkeep' -delete
cp -r "$ROOT/standalone-ui/dist/." "$STATIC/"
echo "bundled standalone UI -> $STATIC"
ls "$STATIC"
