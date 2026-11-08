#!/usr/bin/env bash
# Download a portable Windows Redis build used only for local development.
# The binary is NOT installed as a Windows service and is gitignored.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/tools/redis"
TMP="$ROOT/.dev/redis-download.zip"
EXTRACT="$ROOT/.dev/redis-extract"
VERSION="8.10.3"
URLS=(
  "https://ghproxy.net/https://github.com/redis-windows/redis-windows/releases/download/${VERSION}/Redis-${VERSION}-Windows-x64-msys2.zip"
  "https://gh-proxy.com/https://github.com/redis-windows/redis-windows/releases/download/${VERSION}/Redis-${VERSION}-Windows-x64-msys2.zip"
  "https://github.com/redis-windows/redis-windows/releases/download/${VERSION}/Redis-${VERSION}-Windows-x64-msys2.zip"
)

mkdir -p "$DEST" "$ROOT/.dev"

if [[ -x "$DEST/redis-server.exe" ]]; then
  existing="$("$DEST/redis-server.exe" --version 2>/dev/null || true)"
  if [[ "$existing" =~ v=([7-9]|[1-9][0-9])\. ]]; then
    echo "[fetch_redis] already present: $existing"
    exit 0
  fi
  echo "[fetch_redis] replacing old Redis build: $existing" >&2
fi

download_ok=0
for url in "${URLS[@]}"; do
  echo "[fetch_redis] trying: $url"
  if curl -L --fail --retry 3 --retry-delay 2 --max-time 600 -o "$TMP" "$url"; then
    if unzip -t "$TMP" >/dev/null 2>&1; then
      download_ok=1
      break
    fi
    echo "[fetch_redis] archive invalid from this mirror, trying next" >&2
  else
    echo "[fetch_redis] download failed from this mirror, trying next" >&2
  fi
done

if [[ "$download_ok" -ne 1 ]]; then
  echo "[fetch_redis] ERROR: could not obtain a valid Redis zip." >&2
  echo "[fetch_redis] You can manually place redis-server.exe/redis-cli.exe in tools/redis/." >&2
  exit 1
fi

rm -rf "$EXTRACT"
mkdir -p "$EXTRACT"
unzip -q -o "$TMP" -d "$EXTRACT"

SRC="$EXTRACT"
if [[ ! -x "$SRC/redis-server.exe" ]]; then
  SRC="$(find "$EXTRACT" -maxdepth 2 -type f -name redis-server.exe -printf '%h\n' | head -n1)"
fi
if [[ -z "${SRC:-}" || ! -x "$SRC/redis-server.exe" ]]; then
  echo "[fetch_redis] ERROR: redis-server.exe missing after extraction" >&2
  exit 1
fi

# Replace tools/redis atomically enough for local development. Stop the old
# server first (scripts/dev_services.sh stop) if files are locked.
rm -rf "$DEST"
mkdir -p "$DEST"
cp -a "$SRC"/. "$DEST"/
rm -rf "$EXTRACT" "$TMP"

echo "[fetch_redis] installed portable Redis:"
"$DEST/redis-server.exe" --version
echo "[fetch_redis] NOTE: this is a development-only Windows build; see docs/KNOWN_LIMITATIONS.md."
