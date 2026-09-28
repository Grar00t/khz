#!/bin/sh
# Use the same verified registry and process supervision as the CLI.
set -eu
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$DIR/khz" run "${1:-Rawaseeng-14B-Oracle}" "${2:-8080}"
