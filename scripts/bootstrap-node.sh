#!/usr/bin/env bash
# Reproducible, no-sudo Node.js toolchain install into ~/.local (persistent).
# Pins the current Node LTS; re-run to upgrade by bumping NODE_VERSION.
set -euo pipefail

NODE_VERSION="${NODE_VERSION:-v24.16.0}"   # latest LTS line (Krypton)
ARCH="$(uname -m)"
case "$ARCH" in
  x86_64) NARCH="x64" ;;
  aarch64|arm64) NARCH="arm64" ;;
  *) echo "unsupported arch: $ARCH" >&2; exit 1 ;;
esac

PREFIX="$HOME/.local"
DEST="$PREFIX/node-${NODE_VERSION}-linux-${NARCH}"
TARBALL="node-${NODE_VERSION}-linux-${NARCH}.tar.xz"
URL="https://nodejs.org/dist/${NODE_VERSION}/${TARBALL}"

mkdir -p "$PREFIX/bin"
if [ ! -x "$DEST/bin/node" ]; then
  echo "Installing Node ${NODE_VERSION} to ${DEST} ..."
  tmp="$(mktemp -d)"
  curl -fsSL "$URL" -o "$tmp/$TARBALL"
  tar -xJf "$tmp/$TARBALL" -C "$PREFIX"
  rm -rf "$tmp"
fi

ln -sfn "$DEST/bin/node" "$PREFIX/bin/node"
ln -sfn "$DEST/bin/npm"  "$PREFIX/bin/npm"
ln -sfn "$DEST/bin/npx"  "$PREFIX/bin/npx"

# Enable pnpm via corepack (ships with Node). Scope to pnpm to avoid a
# yarn realpath error when yarnpkg isn't present.
"$DEST/bin/node" "$DEST/bin/corepack" enable pnpm --install-directory "$PREFIX/bin" 2>/dev/null || true
"$DEST/bin/node" "$DEST/bin/corepack" prepare pnpm@latest --activate 2>/dev/null || true

echo "node: $("$PREFIX/bin/node" -v)"
echo "npm:  $("$PREFIX/bin/npm" -v)"
"$PREFIX/bin/pnpm" -v >/dev/null 2>&1 && echo "pnpm: $("$PREFIX/bin/pnpm" -v)" || echo "pnpm: (enable via 'corepack enable')"
