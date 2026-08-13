#!/usr/bin/env bash
# DocsForge migration — converts mkdocs/properdocs/zensical config to
# docsforge.yml. One-liner:
#   curl -fsSL https://raw.githubusercontent.com/QQSHI13/docsforge/main/scripts/migrate.sh | bash
set -euo pipefail

MIGRATE_URL="${DOCSFORGE_MIGRATE_URL:-https://raw.githubusercontent.com/QQSHI13/docsforge/main/scripts/migrate.py}"

log()  { printf 'docsforge-migrate: %s\n' "$*"; }
fail() { log "$*" >&2; exit 1; }

# 1. Python?
if ! command -v python3 >/dev/null 2>&1; then
  fail "python3 not found — install Python 3.11+ (https://www.python.org/downloads/)"
fi

# 2. Download migrate.py
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
if ! curl -fsSL "$MIGRATE_URL" -o "$TMP/migrate.py" 2>/dev/null; then
  fail "could not download $MIGRATE_URL — check your connection"
fi

# 3. Ensure PyYAML (venv fallback if the system python is externally managed)
RUN_PY="python3"
if ! python3 -c 'import yaml' >/dev/null 2>&1; then
  log "PyYAML not found — setting up a temporary environment…"
  PY_MAJOR="$(python3 -c 'import sys; print(sys.version_info[:2] >= (3, 11))')"
  if [ "$PY_MAJOR" != "True" ]; then
    fail "Python 3.11+ required (found $(python3 --version))"
  fi
  if python3 -m pip install --user --quiet pyyaml 2>/dev/null && python3 -c 'import yaml' >/dev/null 2>&1; then
    log "PyYAML installed (user site)."
  else
    log "Creating a temporary virtualenv…"
    python3 -m venv "$TMP/venv"
    "$TMP/venv/bin/pip" install --quiet pyyaml
    RUN_PY="$TMP/venv/bin/python"
  fi
fi

exec "$RUN_PY" "$TMP/migrate.py" "$@"
