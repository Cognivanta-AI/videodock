#!/usr/bin/env bash
# Thin wrapper: resolve Python relative to this script, not the caller's cwd.
set -euo pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/publish_video.py" "$@"
