# SMG-3DS

An unfinished native port of *Super Mario Galaxy* to the New Nintendo 3DS, built on
[Petari](https://github.com/SMGCommunity/Petari), the SMGCommunity's decompilation of the game.

> **This project is archived.** Nobody is working on it, and it is not a finished or fully playable port.
> The code is left here as it was when work stopped in October 2026, for anyone who wants to study it or pick it back up.
>
> **Want to pick it up?** Start with [docs/HANDOFF.md](docs/HANDOFF.md): where the port stands, how to build and test it,
> and what was being worked on.

> **This is a fork.** It is based on the archived original above (cmyksoda/SMG-3DS) and adds a real-hardware
> deployment/debugging toolkit plus a few build fixes. See [Fork additions](#fork-additions) below.

## Status

- **The game's own code runs on the 3DS.** All 1,803 of Petari's source files compile for the 3DS's ARM11 CPU,
  running on a port of the Wii SDK layers the game calls: threads, the disc, video, the GX graphics API translated
  to the 3DS's PICA200 GPU, and the Wii's audio DSP in software.
- **In the Azahar emulator** it boots through the title screen, the file select and the storybook into the game.
  Every galaxy loads and runs without crashing, most of them at 30 fps.
- **On a real New 2DS XL** it boots and plays, but slowly: about 14 fps, mostly waiting on the GPU. The sky and some
  textures draw wrong there, and closing it from the HOME Menu ends in an error or a hang.
- **New 3DS and New 2DS only.** It needs ZL, ZR, the C-Stick and the faster CPU.
- **Only the USA disc (RMGE01) was tested.** No game data is included. The port reads your own disc image from the SD card.

## Building

```sh
git clone --recursive https://github.com/cmyksoda/SMG-3DS.git
cd SMG-3DS
tools/build-3ds.sh    # builds in Docker with a pinned devkitARM image, into ~/.cache/smg-3ds/3ds/
tools/test-host.sh    # runs the host tests under ASan and UBSan
```

The game is `mario_probe.3dsx`. It kept the name from when it was a bring-up probe.
[docs/HANDOFF.md](docs/HANDOFF.md) covers setting up the SD card, the controls, and running it in Azahar or on a console.

## Picking it up

Start with [docs/HANDOFF.md](docs/HANDOFF.md). It explains how the port is put together, how it was tested, what is
known to be broken, and what was being worked on when it stopped. [docs/PORTING.md](docs/PORTING.md) holds the
detailed notes on every part of the port.

## Fork additions

This fork keeps the original port as-is and layers on top a set of tools and fixes aimed at **getting it running and
debuggable on a real New 3DS**, and at making the build work on a plain Windows + devkitARM toolchain.

### GPU / build improvements
- **GPU-overlap optimization** (the original author's `docs/untested/gpu-overlap.diff`) applied to
  `source/compat/GxRender.cpp`, reducing per-frame GPU stalls.
- **Windows / GCC 15 build fixes** so it compiles with a current devkitARM toolchain — in `CMakeLists.txt`,
  `tools/3ds-toolchain.cmake` and `tools/prepare-petari.py`.
- Every source change vs. upstream is captured in `source-changes-vs-upstream.patch`.

### Real-hardware toolkit (`real-hardware/`)
A self-contained kit for deploying to and debugging on a console, without the "edit → pull the SD card → guess" loop:
- **Network deploy** — `deploy-3ds.py` pushes a build to the 3DS over the network via `3dslink` (no SD-card swapping).
- **Live logging** — `live-log.py` streams the game's `stderr` back to your PC in real time (via the `netlog` build
  variant), so crashes and GPU warnings show up immediately instead of ending in a black screen.
- **On-device debugging** — `GDB-3DS.cmd` attaches to the Rosalina GDB stub over Wi-Fi; pair it with the `debug`
  build's `optional/SMG-3DS-debug.elf` for symbols.
- **Build variants** — `make_fps_build.py` (on-screen FPS), `make_clipfix_build.py` (PICA200 clipping workarounds),
  `make_debug_build.py` and `make_netlog_build.py` generate the different `.3dsx` variants. These artifacts are
  produced locally and are **not committed** (they contain decompiled game code and are built from your own disc image).
- **CJK / Chinese-system boot fix** — on a Chinese-language 3DS the original build aborts at boot because `Bmg.cpp`
  has no layout for a ruby-tag BMG group. `optional/SMG-3DS-english.3dsx` forces `SC_LANG_ENGLISH` and boots correctly.
  See `real-hardware/cia/ROOT-CAUSE.txt`.
- `real-hardware/DEBUGGING.md` is the full walkthrough; `real-hardware/START-HERE.txt` is the quick start.

### Real-hardware measurements (`baseline/`)
GPU timing captures from a real New 3DS LL (~14.77 fps, ~51 ms/frame waiting on the PICA200), used as the
before/after baseline for any optimization.

### What is *not* included
No game data, disc images, `.3dsx`/`.cia` binaries, DSP firmware (`.cdc`), or upstream source trees are committed.
Build artifacts are generated locally from your own disc image. This keeps the repo source-only and avoids
redistributing copyrighted material.

## Made with

- [Petari](https://github.com/SMGCommunity/Petari) by the SMGCommunity, the decompilation all of this runs on (CC0)
- [devkitPro](https://devkitpro.org/): devkitARM, libctru, citro3d and citro2d
- [Azahar](https://azahar-emu.org/), the 3DS emulator, for everyday testing
- [Wiimms ISO Tools](https://wit.wiimm.de/), [Dolphin](https://dolphin-emu.org/) and [3dbrew](https://www.3dbrew.org/)
  as references for Wii discs, the Wii's hardware and the 3DS's
- AI coding assistants: OpenAI's Codex did the first bring-up, and Anthropic's Claude (in Claude Code) wrote most of
  the code after that, directed by cmyksoda and tested on real hardware

## License

SMG-3DS is released under the [GNU General Public License v3.0](LICENSE). Petari, which it builds on, is CC0.

Super Mario Galaxy is © Nintendo. This is an unofficial fan project, not affiliated with or endorsed by Nintendo.
