#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"
BUNDLE_NAME="com.github.mvleest-code.joplin-search"
ZIP_NAME="joplin-note-search"

rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}"

python - "$ROOT_DIR" "$DIST_DIR" "$BUNDLE_NAME" "$ZIP_NAME" <<'PY'
import shutil
import sys
from pathlib import Path

root = Path(sys.argv[1])
dist_dir = Path(sys.argv[2])
bundle_name = sys.argv[3]
zip_name = sys.argv[4]

bundle_root = dist_dir / bundle_name

ignore_patterns = shutil.ignore_patterns(
    '.git',
    '.gitignore',
    'dist',
    'scripts',
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '*.pyi',
    '*.pyz',
    'debug.log'
)

shutil.copytree(root, bundle_root, ignore=ignore_patterns)

archive_path = shutil.make_archive((dist_dir / zip_name).as_posix(), 'zip', dist_dir, bundle_name)
shutil.rmtree(bundle_root)

print(f"Created {Path(archive_path).relative_to(root)}")
PY
