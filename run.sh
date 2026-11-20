#!/usr/bin/env sh
cd "$(dirname "$0")" || exit 1
exec ./.venv/bin/python hub.py "$@"
