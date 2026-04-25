#!/usr/bin/env bash
# Synapse — quick install
#
#   git clone https://github.com/AkimT13/Synapse.git
#   cd Synapse && bash install.sh

set -euo pipefail

info()  { printf '\033[0;36m▸ %s\033[0m\n' "$*"; }
ok()    { printf '\033[0;32m✓ %s\033[0m\n' "$*"; }
fail()  { printf '\033[0;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# ── preflight ──────────────────────────────────────────────────────────
[ -f "backend/pyproject.toml" ] || fail "Run this from the Synapse repo root"
command -v python3 >/dev/null || fail "python3 is required (3.10+)"
command -v node   >/dev/null || fail "node is required (18+)"
command -v docker >/dev/null || info "docker not found — you'll need it for the vector DB"

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
  fail "Python 3.10+ required (found $PY_VERSION)"
fi

# ── backend: venv + install ───────────────────────────────────────────
info "Setting up Python environment…"
cd backend

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install --upgrade pip -q
pip install -e . -q

ok "synapse CLI installed"
cd ..

# ── frontend: npm install ─────────────────────────────────────────────
info "Installing frontend dependencies…"
cd frontend
npm install --silent
cd ..

ok "Frontend ready"

# ── done ──────────────────────────────────────────────────────────────
echo ""
ok "Synapse is ready"
echo ""
echo "  Getting started:"
echo ""
echo "    source backend/.venv/bin/activate"
echo "    synapse init                         # configure workspace"
echo "    synapse services up                  # start vector DB"
echo "    synapse ingest                       # index code + knowledge"
echo "    synapse ui                           # launch the GUI"
echo ""
echo "  Agent integrations:"
echo ""
echo "    synapse install-skill                # Claude Code + Codex skills"
echo "    synapse vscode                       # VS Code extension"
echo ""
