#!/bin/bash
# Read every payload block and compare file contents with the build root.
set -euo pipefail
image="${1:?usage: verify-squashfs.sh image source-root}"
source_root="${2:?usage: verify-squashfs.sh image source-root}"
check_dir="$(mktemp -d "${TMPDIR:-/var/tmp}/horyzont-squash-check.XXXXXX")"
trap 'rm -rf "$check_dir"' EXIT
if ! unsquashfs -no-progress -no-xattrs -strict-errors -d "$check_dir/root" "$image" >"$check_dir/extract.log" 2>&1; then
    cat "$check_dir/extract.log" >&2
    echo 'Uszkodzony SquashFS: pełny odczyt plików nie powiódł się.' >&2
    exit 1
fi
# Metadata is restored separately by the installer; check data and symlink targets.
if ! rsync -rclni --delete --out-format='%i %n' \
    --exclude=/proc --exclude=/sys --exclude=/dev --exclude=/run --exclude=/tmp \
    "${source_root%/}/" "$check_dir/root/" >"$check_dir/differences"; then
    echo 'Nie udało się porównać obrazu z katalogiem źródłowym.' >&2
    exit 1
fi
if [ -s "$check_dir/differences" ]; then
    head -40 "$check_dir/differences" >&2
    echo 'Zawartość SquashFS różni się od plików źródłowych.' >&2
    exit 1
fi
echo 'SquashFS: wszystkie pliki odczytane i zgodne ze źródłem.'
