#!/usr/bin/env bash
set -euo pipefail
# Usage: curl -fsSL https://is.gd/docsforge_vsix | bash
URL=$(curl -sL https://api.github.com/repos/QQSHI13/docsforge/releases/latest | grep -oP '"browser_download_url":\s*"\K[^"]*\.vsix' | head -1)
[ -n "$URL" ] && curl -fsSL "$URL" -o /tmp/docsforge.vsix && code --install-extension /tmp/docsforge.vsix --force && rm /tmp/docsforge.vsix && echo "Installed!" || echo "Failed"
