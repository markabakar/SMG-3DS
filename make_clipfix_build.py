#!/usr/bin/env python3
"""Experimental "clipfix" build recipe.

Runs the FPS build recipe first, then additionally sends 2D / JPA stripe
triangles through the CPU guard-band clip. On the stock build GxDraw.cpp only
clips perspective triangles (w differs); a PICA200 near-plane cut on a 2D
quad still throws its new corners thousands of pixels away, which is the
"giant streaks / blue slabs" artifact seen on real hardware.

  py -3 make_clipfix_build.py
  -> ninja -C build-3ds -j 4
  -> copy build-3ds/mario_probe.3dsx to optional/SMG-3DS-clipfix.3dsx

UNCONFIRMED ON HARDWARE. Keep the FPS build as the control.
"""
import io
import os
import runpy
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(ROOT, "src-gpu-overlap")
BACKUP = os.path.join(ROOT, "fps-build", "backup")

runpy.run_path(os.path.join(ROOT, "make_fps_build.py"), run_name="__main__")

src = os.path.join(WORK, "source", "core", "GxDraw.cpp")
bak = os.path.join(BACKUP, "source__core__GxDraw.cpp")
if not os.path.exists(bak):
    shutil.copy2(src, bak)
    print("backed up GxDraw.cpp")

s = io.open(src, encoding="utf-8", newline="").read()
old = """        const bool perspective = pa[3] != pb[3] || pb[3] != pc[3];  // a 2D draw's cut stays within its own corners
        if (outside && perspective && behindNear(pa) && behindNear(pb) && behindNear(pc)) return;  // all of it behind
        if (outside && perspective && (behindNear(pa) || behindNear(pb) || behindNear(pc)) && corners + 8 <= room) {"""
new = """        // EXPERIMENTAL clipfix: clip 2D / JPA stripes on the CPU as well. The stock
        // build skips them because their w is equal, but a PICA near-plane cut on
        // such a quad still throws corners thousands of pixels away on hardware.
        if (outside && behindNear(pa) && behindNear(pb) && behindNear(pc)) return;  // all of it behind
        if (outside && (behindNear(pa) || behindNear(pb) || behindNear(pc)) && corners + 8 <= room) {"""
assert old in s, "GxDraw.cpp near-plane clipping anchor not found"
s = s.replace(old, new, 1)
io.open(src, "w", encoding="utf-8", newline="").write(s)
print("GxDraw.cpp: 2D/JPA stripes now clipped to the guard band (experimental)")
print("Build with ninja, then save as optional/SMG-3DS-clipfix.3dsx")
