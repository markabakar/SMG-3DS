#!/usr/bin/env python3
"""Build recipe for the on-screen FPS meter variant (SMG-3DS-fps.3dsx).

The variant is based on the OFFICIAL v0.1.0 renderer (no gpu-overlap patch,
which has never run on a PICA200) plus:
  * the forced-English fix (SCGetLanguage), needed on a Chinese/Japanese system;
  * stderr mirrored to sdmc:/3ds/SMG-3DS/boot-log.txt (keeps crash reasons);
  * a low-overhead FPS meter on the bottom screen's console.

Run from anywhere:  py -3 make_fps_build.py
It only rewrites files inside src-gpu-overlap/; run ninja afterwards.
Originals are backed up to fps-build/backup/ so the tree can be restored.
"""
import io
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
STOCK = os.path.join(ROOT, "src")
WORK = os.path.join(ROOT, "src-gpu-overlap")
BACKUP = os.path.join(ROOT, "fps-build", "backup")
os.makedirs(BACKUP, exist_ok=True)

FILES = [
    "source/compat/GxRender.cpp",
    "source/probe/MarioProbe.cpp",
    "source/compat/SystemConfig.cpp",
    "source/compat/Kpad.cpp",
    "source/core/Settings.cpp",
    "include/smg/Settings.hpp",
]


def read(path):
    with io.open(path, encoding="utf-8", newline="") as f:
        return f.read()


def write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def sub(text, old, new, label, count=1):
    n = text.count(old)
    assert n >= count, "{}: expected >= {} occurrence(s), found {}".format(label, count, n)
    return text.replace(old, new, count)


# --- Back up the working tree once ------------------------------------------
for rel in FILES:
    src = os.path.join(WORK, rel)
    dst = os.path.join(BACKUP, rel.replace("/", "__"))
    if not os.path.exists(dst):
        shutil.copy2(src, dst)
print("backed up {} files -> fps-build/backup/".format(len(FILES)))

# --- 1. GxRender.cpp: official renderer + GCC 15 fix + FPS meter ------------
gx = read(os.path.join(STOCK, "source/compat/GxRender.cpp"))

# GCC 15 mangles an extern "C" symbol declared inside the anonymous namespace.
anchor = "u64 smgAvSyncMarkTick();\nnamespace smg {"
fix = """u64 smgAvSyncMarkTick();

// GCC 15 link fix (no gameplay change): declare the C symbol at global scope.
extern "C" u32 __ctru_heap_size;
namespace smg {"""
gx = sub(gx, anchor, fix, "GxRender global-scope fix")
gx = sub(gx, 'extern "C" u32 __ctru_heap_size;  // libctru: the free store\'s size\n\n',
         "", "GxRender remove inner heap decl")

# The settings getter, declared next to the other development getters.
gx = sub(gx, 'extern "C" int smgDevGxZones();\n',
         'extern "C" int smgDevGxZones();\nextern "C" int smgDevShowFps();\n',
         "GxRender getter decl")

# perfLine() is called exactly once per drawn frame from gxRenderCopy().
meter = '''    void perfLine() {
        // On-screen FPS meter. perfLine() runs once per drawn frame, at the frame-ending
        // EFB copy. One small printf every ~500 ms to the bottom screen's console:
        // no SD-card I/O from the render thread (that costs ~150 ms a frame on hardware),
        // no GPU work, no extra clock reads beyond the two svcGetSystemTick() below.
        static const bool showFps = smgDevShowFps() != 0;
        if (showFps) {
            static u64 shownAt = 0, previous = 0, worst = 0;
            static u32 shownFrames = 0;
            const u64 nowFps = svcGetSystemTick();
            if (!shownAt) shownAt = previous = nowFps;
            const u64 gap = nowFps - previous;
            previous = nowFps;
            if (gap > worst) worst = gap;
            ++shownFrames;
            const u64 elapsed = nowFps - shownAt;
            if (elapsed >= SYSCLOCK_ARM11 / 2) {
                const double fps = double(shownFrames) * SYSCLOCK_ARM11 / elapsed;
                const double ms = double(elapsed) * 1000.0 / SYSCLOCK_ARM11 / shownFrames;
                const double peak = double(worst) * 1000.0 / SYSCLOCK_ARM11;
                std::printf("\\x1b[4;0H\\x1b[KFPS %5.1f  %5.1f ms  max %5.1f  #%llu",
                            fps, ms, peak, static_cast<unsigned long long>(framesShown));
                std::fflush(stdout);
                shownAt = nowFps;
                shownFrames = 0;
                worst = 0;
            }
        }
        const u64 now = svcGetSystemTick();'''
gx = sub(gx, "    void perfLine() {\n        const u64 now = svcGetSystemTick();",
         meter, "GxRender FPS meter")
write(os.path.join(WORK, "source/compat/GxRender.cpp"), gx)
print("GxRender.cpp: stock + GCC15 fix + FPS meter")

# --- 2. MarioProbe.cpp: boot log + unbuffered stdout ------------------------
mp = read(os.path.join(WORK, "source/probe/MarioProbe.cpp"))
mp = sub(mp, "    logCallers();\n    svcExitProcess();",
         "    logCallers();\n    std::fflush(stderr);\n    svcExitProcess();",
         "MarioProbe flush on abort", count=2)
anchor = '    consoleDebugInit(debugDevice_SVC);\n    std::printf("SMG boot bring-up\\n");'
bootlog = '''    consoleDebugInit(debugDevice_SVC);
    // Keep crash reasons on the SD card: stderr is otherwise sent to SVC (invisible
    // on hardware) and the app exits via svcExitProcess(), so Luma writes no dump.
    if (!std::freopen("sdmc:/3ds/SMG-3DS/boot-log.txt", "w", stderr)) consoleDebugInit(debugDevice_SVC);
    else std::setvbuf(stderr, nullptr, _IONBF, 0);
    // The FPS meter writes to stdout's console without a trailing newline.
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    std::printf("SMG boot bring-up\\n");'''
mp = sub(mp, anchor, bootlog, "MarioProbe boot log")
write(os.path.join(WORK, "source/probe/MarioProbe.cpp"), mp)
print("MarioProbe.cpp: stderr -> boot-log.txt, stdout unbuffered")

# --- 3. SystemConfig.cpp: forced English ------------------------------------
sc = read(os.path.join(WORK, "source/compat/SystemConfig.cpp"))
start = sc.index("u8 SCGetLanguage() {")
end = sc.index("// The top screen is 5:3", start)
sc = sc[:start] + """u8 SCGetLanguage() {
    // Force that verified path. On a Chinese/Japanese system the game loads a BMG
    // with a ruby tag (group 255, type 2) the port has no layout for and aborts.
    // The US disc's English/French/Spanish messages are the only ones validated.
    return SC_LANG_ENGLISH;
}

""" + sc[end:]
write(os.path.join(WORK, "source/compat/SystemConfig.cpp"), sc)
print("SystemConfig.cpp: SC_LANG_ENGLISH forced")

# --- 4. Settings: dev.show_fps (default ON, hidden from the written file) ----
sh = read(os.path.join(WORK, "include/smg/Settings.hpp"))
sh = sub(sh, "    bool devAvSync = false;\n",
         "    bool devAvSync = false;\n"
         "    // On by default in the FPS build; dev.show_fps=0 hides the meter. Never written back.\n"
         "    bool devShowFps = true;\n", "Settings.hpp field")
write(os.path.join(WORK, "include/smg/Settings.hpp"), sh)

setc = read(os.path.join(WORK, "source/core/Settings.cpp"))
setc = sub(setc, "a.devGxZones == b.devGxZones && a.devAvSync == b.devAvSync &&",
           "a.devGxZones == b.devGxZones && a.devAvSync == b.devAvSync && a.devShowFps == b.devShowFps &&",
           "Settings.cpp operator==")
setc = sub(setc, '|| key == "dev.gx_zones" || key == "dev.av_sync") {',
           '|| key == "dev.gx_zones" || key == "dev.av_sync" || key == "dev.show_fps") {',
           "Settings.cpp key list")
setc = sub(setc, '                 : key == "dev.av_sync" ? settings.devAvSync\n',
           '                 : key == "dev.av_sync" ? settings.devAvSync\n'
           '                 : key == "dev.show_fps" ? settings.devShowFps\n',
           "Settings.cpp value chain")
write(os.path.join(WORK, "source/core/Settings.cpp"), setc)

kp = read(os.path.join(WORK, "source/compat/Kpad.cpp"))
kp = sub(kp, "BOOL smgDevAvSync() { return input().settings().devAvSync; }\n",
         "BOOL smgDevAvSync() { return input().settings().devAvSync; }\n"
         "// FPS build: on-screen frame-rate meter (dev.show_fps=0 turns it off).\n"
         "BOOL smgDevShowFps() { return input().settings().devShowFps; }\n",
         "Kpad.cpp getter")
write(os.path.join(WORK, "source/compat/Kpad.cpp"), kp)
print("Settings.hpp/.cpp + Kpad.cpp: dev.show_fps (default on)")

print("\nDone. Now build with:")
print("  set DEVKITPRO=C:\\devkitPro && ninja -C build-3ds -j 4")
print("Then copy build-3ds/mario_probe.3dsx to real-hardware/optional/SMG-3DS-fps.3dsx")
print("Restore the tree from fps-build/backup/ afterwards.")
