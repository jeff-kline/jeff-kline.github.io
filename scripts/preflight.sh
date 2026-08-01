#!/bin/sh
set -eu

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

python3 scripts/check_privacy.py "$@"
python3 scripts/check_writing.py "$@"
python3 scripts/check_site.py "$@"

echo "Preflight checks passed."
