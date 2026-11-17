#!/bin/bash
# Build single-line (pen path) versions of characters from a font, for characters the writer
# has not given a sample of.  usage: hw_fallback.sh font.ttf "characters" out_skel.json
# A monoline handwriting font (e.g. Zen Kurenaido, SIL OFL) works best. macOS only.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/handwriting-fill"
mkdir -p "$CACHE"
if [ ! -x "$CACHE/hw_glyphdump" ] || [ "$HERE/hw_glyphdump.swift" -nt "$CACHE/hw_glyphdump" ]; then
  swiftc -O "$HERE/hw_glyphdump.swift" -o "$CACHE/hw_glyphdump"
fi
TMP="$(mktemp -t hwglyphs).json"
"$CACHE/hw_glyphdump" "$1" "$2" "$TMP"
python3 "$HERE/hw_skeleton.py" "$TMP" "$3"
rm -f "$TMP"
