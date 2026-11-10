#!/usr/bin/env python3
"""Debug build recipe: English fix + FPS meter + 3dslink live log + MATCHING ELF.

Unlike the one-shot .3dsx recipes, this also keeps the ELF that GDB needs so the
symbols line up with the binary you actually deploy to the console.

  py -3 make_debug_build.py
  -> runs make_netlog_build.py (English + FPS + 3dslink stderr)
  -> ninja -C build-3ds -j 4
  -> saves optional/SMG-3DS-debug.3dsx  (deploy this)
  -> saves optional/SMG-3DS-debug.elf   (point GDB at this)
  -> restores src-gpu-overlap/ from fps-build/backup/

The .3dsx and .elf come from the SAME build-3ds/ pass, so addresses match.
For finer single-stepping change the optimization in CMakeLists.txt to -Og and
rerun; -g is always on so function names and line numbers are available as-is.
"""
import io
import os
import runpy
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(ROOT, "src-gpu-overlap")
BACKUP = os.path.join(ROOT, "fps-build", "backup")
OPT = os.path.join(ROOT, "real-hardware", "optional")

runpy.run_path(os.path.join(ROOT, "make_netlog_build.py"), run_name="__main__")

# Build (same env as the rest of the pipeline: TMP must live in the workspace).
env = os.environ.copy()
env["TMP"] = os.path.join(ROOT, "tmp")
env["TEMP"] = env["TMP"]
env["TMPDIR"] = env["TMP"]
env["DEVKITPRO"] = r"C:\devkitPro"
r = subprocess.run([shutil.which("ninja"), "-C", "build-3ds", "-j", "4"],
                   cwd=ROOT, env=env, capture_output=True, text=True)
print(r.stdout[-1500:])
if r.returncode != 0:
    print("BUILD FAILED:\n", r.stderr[-2000:])
    sys.exit(1)

elf = os.path.join(ROOT, "build-3ds", "mario_probe.elf")
dsx = os.path.join(ROOT, "build-3ds", "mario_probe.3dsx")
assert os.path.isfile(elf) and os.path.isfile(dsx), "build outputs missing"

shutil.copy2(dsx, os.path.join(OPT, "SMG-3DS-debug.3dsx"))
shutil.copy2(elf, os.path.join(OPT, "SMG-3DS-debug.elf"))
print("saved SMG-3DS-debug.3dsx + SMG-3DS-debug.elf (matched pair)")

# Restore the working tree so build-3ds stays the consistent optimized build.
for rel in ["source/compat/GxRender.cpp", "source/probe/MarioProbe.cpp",
            "source/compat/SystemConfig.cpp", "source/compat/Kpad.cpp",
            "source/core/Settings.cpp", "include/smg/Settings.hpp"]:
    src = os.path.join(WORK, rel)
    bak = os.path.join(BACKUP, rel.replace("/", "__"))
    if os.path.exists(bak):
        shutil.copy2(bak, src)
print("restored src-gpu-overlap/ from backup")
print("Done. Deploy --build debug, debug with optional/SMG-3DS-debug.elf")
