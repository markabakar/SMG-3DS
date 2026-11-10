"""Stop ONLY this project's portable Azahar instance.

NEVER use `taskkill /F /IM azahar.exe` in this project: that kills every Azahar
process on the machine, including instances belonging to other 3DS projects.
This script enumerates processes, compares the executable path, and terminates
only the ones launched from ..\\azahar-portable\\.

Usage:  python stop-portable.py [--dry-run]
"""
import ctypes
import os
import sys
from ctypes import wintypes

TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_TERMINATE = 0x0001
MAX_PATH = 260

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR = os.path.normcase(os.path.join(BASE, "azahar-portable") + os.sep)


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * MAX_PATH),
    ]


def main():
    dry = "--dry-run" in sys.argv
    k32 = ctypes.windll.kernel32
    k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)
    ]
    k32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]

    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    found = []
    if k32.Process32FirstW(snap, ctypes.byref(entry)):
        while True:
            if entry.szExeFile.lower() == "azahar.exe":
                h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_TERMINATE, False, entry.th32ProcessID)
                if h:
                    buf = ctypes.create_unicode_buffer(1024)
                    size = wintypes.DWORD(1024)
                    if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                        path = os.path.normcase(buf.value)
                        if path.startswith(TARGET_DIR):
                            found.append((entry.th32ProcessID, buf.value, h))
                            if not k32.Process32NextW(snap, ctypes.byref(entry)):
                                break
                            continue
                    k32.CloseHandle(h)
            if not k32.Process32NextW(snap, ctypes.byref(entry)):
                break
    k32.CloseHandle(snap)

    if not found:
        print("No portable SMG-3DS Azahar instance running (other projects' instances left untouched).")
        return 0
    for pid, path, h in found:
        if dry:
            print("DRY-RUN would stop:", pid, path)
        else:
            k32.TerminateProcess(h, 1)
            print("Stopped:", pid, path)
        k32.CloseHandle(h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
