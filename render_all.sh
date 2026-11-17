#!/bin/bash
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
R="C:/Users/akp/Downloads/owen_hart_explainer/frames"
"$B" -b -P blender_scene.py -- s3 "$R/s3" > frames/s3.log 2>&1
"$B" -b -P blender_scene.py -- s5 "$R/s5" > frames/s5.log 2>&1
echo DONE
