#!/usr/bin/env bash
# dev_setup.sh — provision the QuADMESH pytest validation gate in a fresh container.
#
# The routine's QuADMESH validation gate is `pytest tests/`, but a fresh
# container ships without numpy/scipy/chilmesh/pytest. chilmesh installs from
# PyPI (`chilmesh>=1.2.1`) as a normal dependency of `quadmesh[dev]`.
# Optional developer override: set QUADMESH_CHILMESH_SRC=<path> to
# editable-install a local CHILmesh checkout first. If that path holds no
# checkout, the script prints a notice and uses the PyPI release. Idempotent.
# See issue #48.
#
# USAGE:
#   bash scripts/dev_setup.sh        # provision (idempotent; chilmesh from PyPI)
#   QUADMESH_CHILMESH_SRC=../CHILmesh bash scripts/dev_setup.sh   # local checkout
#   . .venv/bin/activate && pytest tests/
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
venv="$repo_root/.venv"

# Optional local CHILmesh checkout (editable install); default is PyPI.
chilmesh_dir=""
if [ -n "${QUADMESH_CHILMESH_SRC:-}" ]; then
  if [ -f "$QUADMESH_CHILMESH_SRC/pyproject.toml" ] || [ -f "$QUADMESH_CHILMESH_SRC/setup.py" ]; then
    chilmesh_dir="$(cd "$QUADMESH_CHILMESH_SRC" && pwd)"
  else
    echo "NOTICE: QUADMESH_CHILMESH_SRC=$QUADMESH_CHILMESH_SRC holds no CHILmesh checkout; using chilmesh from PyPI." >&2
  fi
fi

if [ ! -d "$venv" ]; then
  echo "Creating venv at $venv"
  python3 -m venv "$venv"
fi
# shellcheck disable=SC1091
. "$venv/bin/activate"

python -m pip install --quiet --upgrade pip
if [ -n "$chilmesh_dir" ]; then
  echo "Installing chilmesh (editable) from $chilmesh_dir"
  pip install --quiet -e "$chilmesh_dir"
fi
echo "Installing quadmesh[dev] (editable; chilmesh from PyPI unless already installed)"
pip install --quiet -e "$repo_root/.[dev]"

echo "dev_setup OK | chilmesh=${chilmesh_dir:-PyPI} | venv=$venv"
echo "Next: . .venv/bin/activate && pytest tests/"
