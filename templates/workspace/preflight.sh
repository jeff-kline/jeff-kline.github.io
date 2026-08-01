#!/bin/sh
set -eu

private_root=$(git rev-parse --show-toplevel)
public_root=$(git config --local --get jeff.publicSitePath || true)

test -n "$public_root" || {
    echo "Private preflight failed: paired public repository is not configured." >&2
    exit 1
}
test -d "$public_root" || {
    echo "Private preflight failed: paired public repository does not exist." >&2
    exit 1
}

python3 "$public_root/scripts/check_privacy.py" --root "$private_root" --allow-draft-paths "$@"
python3 "$public_root/scripts/check_writing.py" --root "$private_root" "$@"
python3 "$public_root/scripts/check_site.py" --root "$private_root" --all-html "$@"

echo "Private preflight checks passed."
