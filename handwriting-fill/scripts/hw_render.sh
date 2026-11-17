#!/bin/bash
# Draw ink.json onto a PDF.  usage: hw_render.sh form.pdf ink.json out.pdf [r,g,b]
# macOS only: uses the system PDF engine through a small Swift program, compiled on first use.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/handwriting-fill"
mkdir -p "$CACHE"
if ! command -v swiftc >/dev/null; then
  echo "swiftc not found. This renderer needs macOS with the Xcode command line tools (xcode-select --install)." >&2; exit 1
fi
if [ ! -x "$CACHE/hw_render" ] || [ "$HERE/hw_render.swift" -nt "$CACHE/hw_render" ]; then
  swiftc -O "$HERE/hw_render.swift" -o "$CACHE/hw_render"
fi
"$CACHE/hw_render" "$@"
