#!/usr/bin/env python3
"""Deploy an SMG-3DS build to the real console WITHOUT removing the SD card.

Two transports (both standard in devkitPro / used by the original author):

A) 3dslink netloader - fastest, does not touch the SD card at all.
   On the 3DS: open Homebrew Launcher, press Y, note the IP it shows.
   On the PC:  py -3 deploy-3ds.py --ip 192.168.1.50 --build netlog --server
   The --server flag keeps the connection open and prints the game's stderr
   (gx perf, stops, faults) live in this terminal. Use the NETLOG build for it.

B) ftpd - writes the 3dsx to the SD card over WiFi (the author's method).
   On the 3DS: start ftpd (FBI -> titleDB -> ftpd, or ftpd.cia).
   On the PC:  py -3 deploy-3ds.py --ftp 192.168.1.50 --build fps
   Then start SMG-3DS from the Homebrew Launcher as usual.

    py -3 deploy-3ds.py --list             show available builds and hashes
    py -3 deploy-3ds.py --fetch-log --ftp 192.168.1.50   pull boot-log.txt
"""
import argparse
import ftplib
import hashlib
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
THREEDSLINK = r"C:\devkitPro\tools\bin\3dslink.exe"
BUILDS = {
    "debug": os.path.join(HERE, "optional", "SMG-3DS-debug.3dsx"),
    "netlog": os.path.join(HERE, "optional", "SMG-3DS-netlog.3dsx"),
    "fps": os.path.join(HERE, "optional", "SMG-3DS-fps.3dsx"),
    "clipfix": os.path.join(HERE, "optional", "SMG-3DS-clipfix.3dsx"),
    "english": os.path.join(HERE, "optional", "SMG-3DS-english.3dsx"),
    "diag": os.path.join(HERE, "optional", "SMG-3DS-diag.3dsx"),
    "stock": os.path.join(HERE, "3ds", "SMG-3DS", "SMG-3DS.3dsx"),
    "current": os.path.join(ROOT, "build-3ds", "mario_probe.3dsx"),
}
SD_PATH = "/3ds/SMG-3DS/SMG-3DS.3dsx"
SD_LOG = "/3ds/SMG-3DS/boot-log.txt"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def list_builds():
    print("Available builds:")
    for name, path in BUILDS.items():
        if os.path.isfile(path):
            print("  {:<10} {:>9,} B  {}  {}".format(name, os.path.getsize(path), sha(path), path))
        else:
            print("  {:<10} MISSING  {}".format(name, path))


def fetch_log(ip, out):
    with ftplib.FTP(ip, timeout=10) as ftp:
        ftp.login()
        data = io.BytesIO()
        ftp.retrbinary("RETR " + SD_LOG, data.write)
    with open(out, "wb") as f:
        f.write(data.getvalue())
    print("saved {} ({} bytes)".format(out, len(data.getvalue())))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", help="3DS IP for 3dslink (HBL, press Y)")
    ap.add_argument("--ftp", help="3DS IP for ftpd")
    ap.add_argument("--build", default="netlog", choices=sorted(BUILDS))
    ap.add_argument("--server", action="store_true", help="3dslink -s: keep link open, stream stderr")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--fetch-log", nargs="?", const="boot-log.txt", help="pull boot-log.txt over ftpd")
    a = ap.parse_args()

    if a.list:
        list_builds()
        return 0
    if a.fetch_log is not None:
        if not a.ftp:
            print("--fetch-log needs --ftp <3DS IP>")
            return 1
        try:
            fetch_log(a.ftp, a.fetch_log)
            return 0
        except Exception as e:
            print("FTP failed:", type(e).__name__, e)
            return 1

    path = BUILDS[a.build]
    if not os.path.isfile(path):
        print("Build not found:", path)
        return 1
    print("build : {} ({} B, sha {})".format(a.build, os.path.getsize(path), sha(path)))

    if a.ip:
        cmd = [THREEDSLINK, "-a", a.ip, "-r", "10"]
        if a.server:
            cmd.append("-s")
        cmd.append(path)
        print("3dslink:", " ".join(cmd))
        if a.dry_run:
            return 0
        if not os.path.isfile(THREEDSLINK):
            print("3dslink.exe not found:", THREEDSLINK)
            return 1
        print("Waiting for the 3DS (Homebrew Launcher -> Y). Ctrl+C to stop.\n")
        return subprocess.call(cmd)
    if a.ftp:
        print("ftpd   : STOR {} -> ftp://{}{}".format(os.path.basename(path), a.ftp, SD_PATH))
        if a.dry_run:
            return 0
        try:
            with ftplib.FTP(a.ftp, timeout=15) as ftp:
                ftp.login()
                with open(path, "rb") as f:
                    ftp.storbinary("STOR " + SD_PATH, f)
            print("Uploaded. Start SMG-3DS from the Homebrew Launcher.")
            return 0
        except Exception as e:
            print("FTP failed:", type(e).__name__, e)
            print("Check: ftpd running on the 3DS, same WiFi, IP correct.")
            return 1

    print("Nothing to do: pass --ip (3dslink) or --ftp (ftpd), or --list.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
