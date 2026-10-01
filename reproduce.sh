#!/bin/sh
set -eu
cd "$(dirname "$0")"
if [ "$#" -ne 2 ]; then
  echo "Usage: sh reproduce.sh NEW_OUTPUT_DIRECTORY models|oracles|allocation|verify" >&2
  exit 2
fi
exec python reproduce.py "$1" "$2"
