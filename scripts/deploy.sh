#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────
# DocsForge Deploy Script
#   - Builds VSCode extension (.vsix)
#   - Installs it locally (code --install-extension)
#   - Builds & deploys docs site to GitHub Pages
# ──────────────────────────────────────────────

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VSCODE_DIR="$ROOT/packages/vscode-docsforge"
DOCS_DIR="$ROOT/packages/docsforge-docs"
VSIX_FILE=""

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}▶${NC} $1"; }
ok()    { echo -e "${GREEN}✓${NC} $1"; }
err()   { echo -e "${RED}✗${NC} $1"; exit 1; }

# ── VSCode Extension ──

build_vsix() {
  info "Building VSCode extension..."
  cd "$VSCODE_DIR"
  npm install --silent 2>/dev/null
  npm run compile 2>/dev/null || err "TypeScript compilation failed"

  # Get version from package.json
  local version
  version=$(node -e "console.log(require('./package.json').version)")

  rm -f docsforge-vscode-*.vsix
  npx vsce package --out "docsforge-vscode-${version}.vsix" 2>/dev/null || err "vsce package failed"
  VSIX_FILE="docsforge-vscode-${version}.vsix"
  ok "Built: $VSIX_FILE"
}

install_vsix() {
  if [ ! -f "$VSCODE_DIR/$VSIX_FILE" ]; then
    build_vsix
  fi

  if command -v code &>/dev/null; then
    info "Installing extension via VS Code CLI..."
    code --install-extension "$VSCODE_DIR/$VSIX_FILE" --force 2>/dev/null || \
      err "Failed to install extension. Is 'code' in PATH?"
    ok "Extension installed"
  else
    info "VS Code CLI not found. Install manually:"
    echo "  Extensions → ... → Install from VSIX... → $VSCODE_DIR/$VSIX_FILE"
  fi
}

# ── Docs Site ──

build_docs() {
  info "Building docs site..."
  cd "$DOCS_DIR"
  pip install -e "$ROOT/packages/docsforge" --quiet 2>/dev/null
  rm -rf site
  docsforge build 2>/dev/null || err "docsforge build failed"
  ok "Docs built at $DOCS_DIR/site/"
}

deploy_docs() {
  build_docs

  if [ ! -d "$DOCS_DIR/site" ]; then
    err "No site/ directory found. Build failed."
  fi

  if ! git -C "$ROOT" remote get-url origin &>/dev/null; then
    err "No git remote 'origin' found"
  fi

  info "Deploying to GitHub Pages..."
  cd "$DOCS_DIR"

  # Use gh-pages or the pages workflow
  if command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
    gh workflow run pages.yml --ref main 2>/dev/null || \
      err "Failed to trigger Pages workflow"
    ok "Triggered GitHub Pages workflow"
  else
    info "GitHub CLI not authenticated. Deploy manually:"
    echo "  git push origin main  # triggers .github/workflows/pages.yml"
  fi
}

# ── Help ──

usage() {
  echo "Usage: $0 [command]"
  echo
  echo "Commands:"
  echo "  all        Build + install extension + build + deploy docs (default)"
  echo "  vsix       Build the VSCode extension .vsix file"
  echo "  install    Build and install the extension via VS Code CLI"
  echo "  docs       Build the docs site locally"
  echo "  deploy     Build and deploy docs to GitHub Pages"
  echo "  help       Show this help"
  exit 0
}

# ── Main ──

case "${1:-all}" in
  all)
    build_vsix
    install_vsix
    deploy_docs
    ;;
  vsix)
    build_vsix
    ;;
  install)
    build_vsix
    install_vsix
    ;;
  docs)
    build_docs
    ;;
  deploy)
    deploy_docs
    ;;
  help|--help|-h)
    usage
    ;;
  *)
    err "Unknown command: $1. Use '$0 help' for usage."
    ;;
esac

ok "Done!"
