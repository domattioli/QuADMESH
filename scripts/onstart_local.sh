#!/bin/bash
# scripts/onstart_local.sh — QuADMesh-specific session startup checks.
# Sourced by scripts/instructions_on_start.sh after generic checks.

# Python port smoke (cheap): confirm src layout still importable from python/.
# Post-#13 reorg this becomes `python -c "import quadmesh"` from repo root.
if [ -d python ]; then
  echo "Python port: python/quadmesh (pre-#13-reorg layout)"
fi
