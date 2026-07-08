#!/usr/bin/env bash
set -euo pipefail
# Install the latest DocsForge VS Code extension from GitHub releases.
# Usage: bash install.sh
# This script downloads the .vsix and its published .sha256 checksum,
# verifies the checksum, and installs the extension with `code`.

REPO="QQSHI13/docsforge"
API_URL="https://api.github.com/repos/${REPO}/releases/latest"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

echo "Fetching latest release info from ${API_URL}..."
JSON=$(curl -fsSL "$API_URL")

VSIX_URL=$(echo "$JSON" | grep -oP '"browser_download_url":\s*"\K[^"]+\.vsix' | head -1)
SHA_URL=$(echo "$JSON" | grep -oP '"browser_download_url":\s*"\K[^"]+\.vsix\.sha256' | head -1)

if [ -z "$VSIX_URL" ]; then
  echo "ERROR: Could not find a .vsix asset in the latest release." >&2
  exit 1
fi

if [ -z "$SHA_URL" ]; then
  echo "ERROR: Could not find a .vsix.sha256 checksum asset in the latest release." >&2
  exit 1
fi

VSIX_NAME=$(basename "$VSIX_URL")
SHA_NAME=$(basename "$SHA_URL")
VSIX_PATH="${TMP_DIR}/${VSIX_NAME}"
SHA_PATH="${TMP_DIR}/${SHA_NAME}"

echo "Downloading ${VSIX_NAME}..."
curl -fsSL "$VSIX_URL" -o "$VSIX_PATH"

echo "Downloading ${SHA_NAME}..."
curl -fsSL "$SHA_URL" -o "$SHA_PATH"

echo "Verifying checksum..."
EXPECTED=$(awk -v f="$VSIX_NAME" '$2 == f {print $1}' "$SHA_PATH")
if [ -z "$EXPECTED" ]; then
  EXPECTED=$(cut -d' ' -f1 "$SHA_PATH")
fi
ACTUAL=$(sha256sum "$VSIX_PATH" | cut -d' ' -f1)

if [ "$EXPECTED" != "$ACTUAL" ]; then
  echo "ERROR: SHA256 checksum mismatch." >&2
  echo "Expected: $EXPECTED" >&2
  echo "Actual:   $ACTUAL" >&2
  exit 1
fi
echo "Checksum OK."

code --install-extension "$VSIX_PATH" --force
echo "Installed!"
