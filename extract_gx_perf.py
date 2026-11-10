#!/usr/bin/env python3
"""Extract SMG-3DS `gx perf` samples from an Azahar log.

Usage:
    python extract_gx_perf.py <azahar_log.txt>                 # compact table + summary
    python extract_gx_perf.py <azahar_log.txt> --csv out.csv   # full CSV for A/B diff
    python extract_gx_perf.py <azahar_log.txt> --slow          # only samples below 29 fps

The log is produced when the portable instance has:
    instant_debug_log=true
    log_filter=*:Info Debug.Emulated:Debug
and BOTH keys' `\\default` markers are set to false (Azahar otherwise ignores
the values). See ../AGENT_HANDOFF.md section 11.
"""
import argparse
import csv
import re
import sys

FIELDS = [
    "t_s", "frames", "ms_per_frame", "fps", "logic_steps",
    "game_thread_draw_ms", "logic_ms", "animation_ms",
    "waiting_gpu_ms", "retrace_wait_ms", "gx_stream_ms",
    "pica_wait_ms", "dsp_ms", "primitives", "vertices",
    "triangles", "draws",
]


def num(pattern, text, default=0.0):
    m = re.search(pattern, text)
    return float(m.group(1)) if m else default


def parse(path):
    rows = []
    with open(path, "rb") as f:
        for raw in f:
            line = raw.decode("utf-8", errors="replace")
            if "gx perf: t=" not in line:
                continue
            body = line.split("OutputDebugString:1190: ", 1)[-1].strip()
            m = re.search(r"t=(\d+), (\d+) frames, ([\d.]+) ms/frame \(([\d.]+) fps, ([\d.]+) logic steps", body)
            if not m:
                continue
            rows.append({
                "t_s": int(m.group(1)),
                "frames": int(m.group(2)),
                "ms_per_frame": float(m.group(3)),
                "fps": float(m.group(4)),
                "logic_steps": float(m.group(5)),
                "game_thread_draw_ms": num(r"game thread draw ([\d.]+)", body),
                "logic_ms": num(r"logic ([\d.]+),", body),
                "animation_ms": num(r"animation ([\d.]+)", body),
                "waiting_gpu_ms": num(r"waiting for the GPU ([\d.]+)", body),
                "retrace_wait_ms": num(r"retrace wait ([\d.]+)", body),
                "gx_stream_ms": num(r"GX stream read on core 2 ([\d.]+) ms", body),
                "pica_wait_ms": num(r"\(([\d.]+) of it waiting for the PICA\)", body),
                "dsp_ms": num(r"DSP ([\d.]+) ms", body),
                "primitives": int(num(r"(\d+) primitives", body)),
                "vertices": int(num(r"(\d+) vertices", body)),
                "triangles": int(num(r"(\d+) triangles", body)),
                "draws": int(num(r"(\d+) draws;", body)),
            })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--csv", metavar="PATH", help="write full CSV here")
    ap.add_argument("--slow", action="store_true", help="only show samples under 29 fps")
    args = ap.parse_args()

    rows = parse(args.log)
    if not rows:
        print("No gx perf samples found. Is instant_debug_log + Debug.Emulated enabled?", file=sys.stderr)
        return 1

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
        print("CSV written:", args.csv, len(rows), "samples")

    shown = [r for r in rows if r["fps"] < 29] if args.slow else rows
    print(f"t(s) frames  ms/f   fps | GPUwait   GX  PICA retrace logic prims draws")
    for r in shown:
        print(f"{r['t_s']:>4} {r['frames']:>6} {r['ms_per_frame']:>6.1f} {r['fps']:>5.1f} | "
              f"{r['waiting_gpu_ms']:>7.1f} {r['gx_stream_ms']:>4.1f} {r['pica_wait_ms']:>4.1f} "
              f"{r['retrace_wait_ms']:>7.1f} {r['logic_ms']:>5.1f} {r['primitives']:>5} {r['draws']:>5}")

    fps = [r["fps"] for r in rows]
    gw = [r["waiting_gpu_ms"] for r in rows]
    gx = [r["gx_stream_ms"] for r in rows]
    slow = [r for r in rows if r["fps"] < 29]
    print()
    print(f"SUMMARY  samples={len(rows)}  fps avg={sum(fps)/len(fps):.2f} min={min(fps):.1f} max={max(fps):.1f}")
    print(f"         GPUwait avg={sum(gw)/len(gw):.2f} max={max(gw):.1f}   GXstream avg={sum(gx)/len(gx):.2f} max={max(gx):.1f}")
    print(f"         samples below 29 fps: {len(slow)} -> t={[r['t_s'] for r in slow]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
