#!/bin/bash
# Render Blender scenes s3 + s5. Extra flags are passed through to blender_scene.py, e.g.
#   ./render_all.sh --res 720 --samples 8 --fast-lights
#   ./render_all.sh --draft
B="${BLENDER:-/c/Program Files/Blender Foundation/Blender 5.2/blender.exe}"
R="$(cd "$(dirname "$0")" && pwd -W 2>/dev/null || pwd)/frames"
cd "$(dirname "$0")"
mkdir -p frames
"$B" -b -P blender_scene.py -- s3 "$R/s3" "$@" > frames/s3.log 2>&1 || { echo "s3 failed, see frames/s3.log"; exit 1; }
"$B" -b -P blender_scene.py -- s5 "$R/s5" "$@" > frames/s5.log 2>&1 || { echo "s5 failed, see frames/s5.log"; exit 1; }
echo DONE
