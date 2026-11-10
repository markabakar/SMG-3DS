#!/usr/bin/env python3
"""Recipe for the NETLOG build: FPS build + real-time stderr over 3dslink.

Launch through the Homebrew Launcher netloader (press Y) with:
    3dslink -a <3DS-IP> -s SMG-3DS-netlog.3dsx
The -s server receives stderr (gx perf, stops, faults) live on the PC.
stdout stays on the bottom-screen console so the FPS meter still works.

When started from the SD card instead, __3dslink_host is zero and the build
falls back to writing sdmc:/3ds/SMG-3DS/boot-log.txt (same as the FPS build).
"""
import io
import os
import runpy

ROOT = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(ROOT, "src-gpu-overlap")

runpy.run_path(os.path.join(ROOT, "make_fps_build.py"), run_name="__main__")

p = os.path.join(WORK, "source", "probe", "MarioProbe.cpp")
s = io.open(p, encoding="utf-8", newline="").read()

old = """    consoleDebugInit(debugDevice_SVC);
    // Keep crash reasons on the SD card: stderr is otherwise sent to SVC (invisible
    // on hardware) and the app exits via svcExitProcess(), so Luma writes no dump.
    if (!std::freopen("sdmc:/3ds/SMG-3DS/boot-log.txt", "w", stderr)) consoleDebugInit(debugDevice_SVC);
    else std::setvbuf(stderr, nullptr, _IONBF, 0);
    // The FPS meter writes to stdout's console without a trailing newline.
    std::setvbuf(stdout, nullptr, _IONBF, 0);"""

new = """    consoleDebugInit(debugDevice_SVC);
    // NETLOG: when launched through 3dslink's netloader (-s on the PC), stream
    // stderr (gx perf, stops, faults) to the PC in real time. stdout stays on the
    // bottom-screen console for the FPS meter. From the SD card, fall back to
    // boot-log.txt so this build behaves exactly like the FPS build.
    bool netlog = false;
    if (__3dslink_host.s_addr != 0) {
        u32* socBuffer = static_cast<u32*>(memalign(0x1000, 0x100000));
        if (socBuffer && R_SUCCEEDED(socInit(socBuffer, 0x100000))) {
            netlog = link3dsStdioForDebug() >= 0;
            if (!netlog) socExit();
        }
        if (!netlog && socBuffer) std::free(socBuffer);
    }
    if (!netlog) {
        if (!std::freopen("sdmc:/3ds/SMG-3DS/boot-log.txt", "w", stderr)) consoleDebugInit(debugDevice_SVC);
        else std::setvbuf(stderr, nullptr, _IONBF, 0);
    }
    // The FPS meter writes to stdout's console without a trailing newline.
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    std::fprintf(stderr, "mario-probe: log %s\\n", netlog ? "NETLOG (3dslink)" : "sdmc boot-log.txt");"""

assert old in s, "MarioProbe.cpp stderr anchor not found"
s = s.replace(old, new, 1)
s = s.replace("#include <3ds.h>\n#include <cstdio>\n",
              "#include <3ds.h>\n#include <3ds/3dslink.h>\n#include <netinet/in.h>\n#include <malloc.h>\n#include <cstdlib>\n#include <cstdio>\n", 1)
io.open(p, "w", encoding="utf-8", newline="").write(s)
print("MarioProbe.cpp: 3dslink real-time stderr (with SD-card fallback)")
print("Build with ninja, then save as optional/SMG-3DS-netlog.3dsx")
