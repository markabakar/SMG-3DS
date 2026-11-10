#!/usr/bin/env python3
"""Live performance / crash monitor for the real console.

Three sources (pick one):

  1. 3dslink server output (NETLOG build, fastest, no SD card):
       py -3 deploy-3ds.py --ip <3DS-IP> --build netlog --server | py -3 live-log.py --stdin
  2. SD card mounted as a drive:
       py -3 live-log.py --drive F:
  3. ftpd on the 3DS (polls boot-log.txt over WiFi):
       py -3 live-log.py --ftp <3DS-IP>

Prints one compact line per gx perf sample, flags faults/stops immediately,
and optionally appends everything to a CSV for A/B comparison.
"""
import argparse
import csv
import ftplib
import io
import os
import re
import sys
import time

PERF = re.compile(r"gx perf: t=(\d+), (\d+) frames, ([\d.]+) ms/frame \(([\d.]+) fps")
PICA = re.compile(r"waiting for the GPU ([\d.]+)")
STREAM = re.compile(r"GX stream read on core \d ([\d.]+) ms \(([\d.]+) of it waiting for the PICA\)")
DRAWS = re.compile(r"(\d+) primitives")
ALERT = re.compile(r"abort|fault|no layout|callers on the stack|BMG message|data abort|prefetch|undefined instruction", re.I)
FIELDS = ["t_s", "frames", "ms_per_frame", "fps", "waiting_gpu_ms", "gx_stream_ms", "pica_wait_ms", "primitives"]


def line_metrics(line):
    m = PERF.search(line)
    if not m:
        return None
    g = PICA.search(line)
    s = STREAM.search(line)
    d = DRAWS.search(line)
    return {
        "t_s": m.group(1), "frames": m.group(2), "ms_per_frame": m.group(3), "fps": m.group(4),
        "waiting_gpu_ms": g.group(1) if g else "",
        "gx_stream_ms": s.group(1) if s else "",
        "pica_wait_ms": s.group(2) if s else "",
        "primitives": d.group(1) if d else "",
    }


def emit(line, csv_writer, csv_file):
    text = line.rstrip("\r\n")
    if ALERT.search(text):
        print("!! " + text[:220], flush=True)
        return
    r = line_metrics(text)
    if r:
        print("t={:>4}s  {:>6} ms  {:>5} fps | GPUwait {:>6}  GX {:>6}  PICA {:>6} | {:>5} prim".format(
            r["t_s"], r["ms_per_frame"], r["fps"], r["waiting_gpu_ms"] or "-",
            r["gx_stream_ms"] or "-", r["pica_wait_ms"] or "-", r["primitives"] or "-"), flush=True)
        if csv_writer:
            csv_writer.writerow(r)
            csv_file.flush()
    elif "heartbeat: Mario at" in text or "mario-probe:" in text or "The disc:" in text:
        print("   " + text[:180], flush=True)


def follow_file(path, csv_writer, csv_file):
    print("watching", path, flush=True)
    last_size = 0
    pos = 0
    while True:
        try:
            size = os.path.getsize(path)
            if size < last_size:
                pos = 0  # file was rewritten by a new run
            last_size = size
            if size > pos:
                with open(path, "rb") as f:
                    f.seek(pos)
                    chunk = f.read(size - pos)
                pos = size
                for line in chunk.decode("utf-8", errors="replace").splitlines():
                    emit(line, csv_writer, csv_file)
        except FileNotFoundError:
            pass
        except OSError as e:
            print("read error:", e, flush=True)
        time.sleep(0.5)


def follow_ftp(ip, csv_writer, csv_file):
    print("polling ftpd on", ip, flush=True)
    path = "/3ds/SMG-3DS/boot-log.txt"
    seen = 0
    while True:
        try:
            with ftplib.FTP(ip, timeout=8) as ftp:
                ftp.login()
                ftp.sendcmd("TYPE I")
                size = ftp.size(path)
                if size is not None and size > seen:
                    buf = io.BytesIO()
                    def cb(data):
                        if buf.tell() >= seen:
                            buf.write(data)
                    ftp.retrbinary("RETR " + path, cb)
                    data = buf.getvalue()
                    seen = size
                    for line in data.decode("utf-8", errors="replace").splitlines():
                        emit(line, csv_writer, csv_file)
        except Exception as e:
            print("ftp:", type(e).__name__, e, flush=True)
            time.sleep(2)
        time.sleep(1.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stdin", action="store_true", help="read a piped 3dslink -s stream")
    ap.add_argument("--drive", help="SD card drive, e.g. F:")
    ap.add_argument("--ftp", help="3DS IP running ftpd")
    ap.add_argument("--csv", help="append samples to this CSV")
    a = ap.parse_args()

    csv_file = csv_writer = None
    if a.csv:
        new = not os.path.isfile(a.csv)
        csv_file = open(a.csv, "a", newline="", encoding="utf-8")
        csv_writer = csv.DictWriter(csv_file, fieldnames=FIELDS)
        if new:
            csv_writer.writeheader()
        print("CSV ->", a.csv, flush=True)

    try:
        if a.stdin:
            print("reading 3dslink stream from stdin", flush=True)
            for line in sys.stdin:
                emit(line, csv_writer, csv_file)
        elif a.drive:
            p = os.path.join(a.drive, "3DS", "SMG-3DS", "boot-log.txt")
            follow_file(p, csv_writer, csv_file)
        elif a.ftp:
            follow_ftp(a.ftp, csv_writer, csv_file)
        else:
            print("Pass --stdin, --drive F: or --ftp <IP>. See --help.")
            return 1
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        if csv_file:
            csv_file.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
