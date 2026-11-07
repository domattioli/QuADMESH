#!/usr/bin/env bash
# Fail if a built sdist or wheel contains any file under cpp/ (SC-011).
# Usage: scripts/check_no_cpp_in_dist.sh <dist-dir>
# Build first, for example: python -m build --sdist --wheel --outdir "$TMPDIR/dist"
set -euo pipefail

dist_dir="${1:-dist}"
shopt -s nullglob
sdists=("$dist_dir"/*.tar.gz)
wheels=("$dist_dir"/*.whl)

if [ ${#sdists[@]} -eq 0 ] || [ ${#wheels[@]} -eq 0 ]; then
  echo "check_no_cpp_in_dist: need one sdist and one wheel in $dist_dir" >&2
  exit 2
fi

status=0
for f in "${sdists[@]}"; do
  # sdist entries start with <name>-<version>/
  if tar -tzf "$f" | grep -E '^[^/]+/cpp/'; then
    echo "check_no_cpp_in_dist: cpp/ found in $f" >&2
    status=1
  fi
done
for f in "${wheels[@]}"; do
  if python3 -c 'import sys, zipfile; print("\n".join(zipfile.ZipFile(sys.argv[1]).namelist()))' "$f" \
      | grep -E '(^|/)cpp/'; then
    echo "check_no_cpp_in_dist: cpp/ found in $f" >&2
    status=1
  fi
done

if [ $status -eq 0 ]; then
  echo "check_no_cpp_in_dist: OK, no cpp/ entries"
fi
exit $status
