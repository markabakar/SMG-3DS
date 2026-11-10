# SMG-3DS 底层优化 · Agent 交接台账

> 最后更新：2026-11-08 02:25 GMT+8
> 工作区：`C:\Users\WXP\WorkBuddy\2026-11-08-01-41-44`
> 本文件是**给接手 agent 的第一入口**。配合 `.workbuddy/memory/2026-11-08.md`（逐轮排障日志）一起读。

---

## 1. 目标与硬性约束

- **上层目标**：继续优化已归档的 `github.com/cmyksoda/SMG-3DS`（GPLv3，Petari 反编译的《超级马力欧 银河》→ New 3DS 原生移植），最终在 **New 3DS / New 2DS XL 实机**上达到可玩帧率。项目设计目标是稳定 30 fps，不是 60。
- **真机基线**：约 70 ms/帧（≈14 fps），其中 **GPU 占 50–60 ms**；渲染线程等 GPU 约 51 ms，再构建 23 ms，GPU 在构建期间空闲。
- **反直觉但关键**：Azahar 把 New 3DS CPU 限到 268 MHz（真机 1/3），对 CPU 苛刻、对 PC GPU 宽松；**真机瓶颈与模拟器相反**。因此调模拟器设置、超频 emulated CPU、换 Vulkan 对实机几乎无收益，优化必须落在 PICA200/GPU 侧。别在这条错路上耗时间。
- 只有 **美版 RMGE01** 盘镜像被完整验证过（2,371 文件 / 3.15 GB / BMG 文本 / 贴图 / 关卡表）。

## 2. 关键路径速查

| 路径 | 用途 |
| --- | --- |
| `smg3ds/src/` | 官方源码 tarball 解压原版（对照基线） |
| `smg3ds/src-gpu-overlap/` | **已应用 `gpu-overlap.diff` 的优化版源码**，当前工作副本 |
| `smg3ds/SMG-3DS-0.1.0/` | v0.1.0 Release 解压包（含 `SMG-3DS.3dsx`） |
| `smg3ds/SMG-3DS-0.1.0.zip` | Release 原始包，经 GitHub API `assets` 通道下载 |
| `C:\Program Files\Azahar\azahar.exe` | **官方 Azahar 2126.2 / HEAD-219d743**（作者验证版本，优先用） |
| `C:\Users\WXP\AppData\Roaming\Azahar\sdmc\3ds\SMG-3DS\` | 官方版虚拟 SD 卡：`SMG-3DS.3dsx`、`settings.ini`、`game.wbfs`(美版副本)、`dspfirm.cdc`(占位) |
| `D:\AzaharRun\azahar.exe` | 第三方魔改 AzaharPlus `cf90688-dirty`，**不要用**（zip_pass 等非标准改动） |
| `D:\AzaharRun\user\sdmc\3ds\SMG-3DS\game.wbfs` | 硬链接到美版镜像，零额外空间 |
| `D:\Dowdload\1103\1103 - Super Mario Galaxy (USA) (En,Fr,Es) (Laojiku.com).wbfs` | **美版 RMGE01**，3,508,535,296 B，WBFS 头合法 |
| `D:\Dowdload\033\...\超级马里奥银河 [RMGJ01].wbfs` | 日版汉化，实测卡 boot，**不要用** |
| `*/config/qt-config.ini.smg-backup` | 两个模拟器配置的原始备份 |

## 3. 已完成（含验证结论）

1. 下载 v0.1.0 Release（本机无 Docker，改用预编译包），部署 `3dsx`/`settings.ini`/`dspfirm.cdc` 到两个 sdmc；New 3DS 模式与 CPU 100% 原本已开启。
2. **跑通**：官方 Azahar 2126.2 + 美版 RMGE01 WBFS → 约 90 s 进入标题画面，`速度 100%/100%`、`应用: 30 帧`。
3. **黑屏不是 Vulkan**：Vulkan / OpenGL 1x / 官方版三组对照日志一致。无盘时程序启动 1.3 s 即 `TerminateProcess`；日版汉化盘被接受但 `应用: 0 帧` 卡在 boot；美版正常。
4. **结论**：同为 WBFS，美版 30 帧、日版 0 帧 → 卡住原因是资源不兼容，不是 WBFS 实时 AES 解密。代码不校验 game ID（`DiscImage.cpp` 只打印），`WiiDisc.cpp` 仅对韩版 common key 报错。
5. 生成 `src-gpu-overlap/`：`git apply --check` 6 hunk 全过，已应用（真实差异 31 行，行尾规范为 LF）。
6. 查清过场动画根因：THP 电影按 logic step 播放，Azahar 268 MHz 下每帧解码 ~80 ms（≈11 fps）；真机 CPU 快约 3 倍 → 理论 ~27 ms/帧。`thpTiles565` 是 Y2R 硬件打不开时的 CPU 兜底。

## 4. 决策记录（改动前先读）

- **D1** 用官方 Azahar 2126.2，不用 AzaharPlus 魔改版。理由：作者验证版本 + 魔改版有 zip_pass 等非标准代码。
- **D2** 早期用 Release 预编译包（当时无 Docker）；现在目标转为源码级优化，必须自建工具链。
- **D3** 优先 GPU overlap 补丁，而非 CPU 侧/模拟器侧优化。理由：见 §1 瓶颈判断。定量预期：51 ms 与 23 ms 重叠后单帧 74 → ~51 ms（≈20 fps），**离 30 fps 仍有差距**，必须继续砍 GPU 工作量。
- **D4** 工具链选 Windows 原生 devkitPro，**不选 Docker**：`wsl.exe` 在安全中心黑名单被拦截（不可绕过、不要重试），Docker Desktop 依赖 WSL2。
- **D5** 镜像用 NTFS 硬链接（同卷）或复制，绝不改动用户原文件；`dspfirm.cdc` 若已存在（便携版是真实 49,756 B dump）一律保留。
- **D6** 改源码保留原版与优化版两份目录对照，便于 `diff` 与回滚。

## 5. 当前阻塞（接手先确认是否已解除）

| 阻塞 | 详情 |
| --- | --- |
| 网络 | `pkg.devkitpro.org` / `downloads.devkitpro.org` → Cloudflare **403**（5,948 B 拦截页）；`github.com/.../releases/download` → **502**；`api.github.com` → **403 rate limit**（60/h，重置约 02:42:37）；`pypi.org`、`raw.githubusercontent.com`、`registry-1.docker.io` 均不可达 |
| 可用通道 | `codeload.github.com`（200，可下 GitHub 仓库 tarball）、`objects.githubusercontent.com`（GitHub API assets 下载曾成功）、`cdn.winget.microsoft.com`（winget 源可用）、`WebFetch`（网页文本可达） |
| WSL | `wsl.exe` 被安全策略黑名单拦截，**禁止重试或等价绕过** |
| 本机工具 | 有 CMake 3.x、Ninja、Python 3.13、Git、winget；**无** Docker Desktop、devkitPro/devkitARM、gcc/g++/clang/cl/make、MSVC |
| 后果 | 目前**无法编译 .3dsx**，也跑不了 `tools/test-host.sh`（该脚本也走 Docker） |

**已向用户请求代下载**（见 §9），优先顺序：
1. `https://github.com/devkitPro/installer/releases/download/v3.0.3/devkitProUpdater-3.0.3.exe`（192 KB）；
2. 若浏览器能打开 `https://pkg.devkitpro.org/packages/windows/x86_64/`，下载 `devkitARM` / `libctru` / `citro3d` / `citro2d` / `3ds-tools`(picasso, 3dsxtool, smdhtool) / `3ds-zstd` 的 `.pkg.tar.xz`；
3. 统一放到 `smg3ds/dl/`。
> **处理技巧**：pacman 包本质是标准 `.pkg.tar.xz`，可直接 `tar -xf` 解压拼出 `${DEVKITPRO}` 目录结构（CMake 只引用 `devkitARM/bin`、`libctru/include|lib`、`portlibs/3ds/lib/libzstd.a`、`tools/bin/{picasso,3dsxtool,smdhtool}`），**不必运行 pacman 或安装器**。

## 6. 待办（按顺序推进）

- **T5 工具链**[进行中]：拿到包 → 解压到 `smg3ds/toolchain/devkitPro` → 验证 `arm-none-eabi-g++`、`picasso`、`3dsxtool` 可用。
- **T6 编译 + 回归**：编 `src-gpu-overlap` 出 `.3dsx`；跑 host 测试（ASan/UBSan）、`mwerks-only-asm.py`、`ub-scan.sh`，三者必须保持 0。
- **T7 模拟器验证**：优化版部署到官方版 sdmc（先备份原 `SMG-3DS.3dsx`），美版盘启动，确认进标题、≥30 fps、无渲染错误/崩溃，记录状态栏数值对照。
- **T8 EFB copy 分析**[第二优先级，达成 30 fps 的关键]：城堡每帧 12 次 EFB copy（split + transfer + pass）。作者写过"按阶段逐类移除 GPU 工作并计时"的测试构建但没跑完。需量化各类 GPU 工作占比，再合并/削减。可先做不依赖编译的静态分析与测量补丁设计。
- **T9 台账维护**[本文件]：每完成一项立即更新 §3/§5/§6，并追加 daily log。

## 7. 命令清单（工具链就绪后）

```bash
# 编译（Windows 原生 devkitPro）
export DEVKITPRO=<解压出的 devkitPro 目录>
cmake -S src-gpu-overlap -B build-3ds -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=src-gpu-overlap/tools/3ds-toolchain.cmake \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build-3ds
# 产物：build-3ds/SMG-3DS.3dsx、mario_probe.3dsx

# host 回归（需 GCC/Clang + ASan/UBSan；官方脚本走 Docker）
cmake -S src-gpu-overlap -B build-host -G Ninja -DCMAKE_BUILD_TYPE=Debug \
  -DCMAKE_CXX_FLAGS="-fsanitize=address,undefined -fno-sanitize-recover=undefined -fno-omit-frame-pointer"
cmake --build build-host && ctest --test-dir build-host --output-on-failure
python src-gpu-overlap/tools/mwerks-only-asm.py   # 必须 0
bash src-gpu-overlap/tools/ub-scan.sh             # 必须 0

# Azahar 启动
"C:\Program Files\Azahar\azahar.exe" "C:\Users\WXP\AppData\Roaming\Azahar\sdmc\3ds\SMG-3DS\SMG-3DS.3dsx"
```

## 8. 已知坑（血泪）

- **Azahar 启动/退出会把内存配置写回 `qt-config.ini`**，外部直接改 `instant_debug_log` / `log_filter` 无效（但 `graphics_api`、`resolution_factor` 生效）。要改日志项必须走 GUI。
- **`git apply` 在 Windows 会把 LF 文件转成 CRLF**，污染 diff；应用后需 `replace(b'\r\n', b'\n')` 规范行尾（已处理）。
- **测试构建绝不能在渲染线程写 SD 卡**：作者实测 +150 ms/帧。
- 标题 `Press both A and B` = 3DS 的 **A + R** = Azahar 默认键盘 **A(或 S) + W**；指针默认 stylus（下屏按住鼠标拖动）。
- 真机已知问题：天空蓝色板块、mip 层级被关（`dev.gx_mips=1` 可开）、HOME/电源菜单关闭挂起、水面/阴影/两条白色虚线、退出需长按电源。
- 项目诊断开关写在 `settings.ini`：`dev.gx_timing` / `dev.gx_zones` / `dev.gx_dump` / `dev.gx_null` / `dev.gx_mips` / `dev.av_sync` / `dev.skip_story` / `dev.galaxy`（见 `source/core/Settings.cpp`）。
- 真机部署经 ftpd + Homebrew Launcher；FAT32 单文件上限 4 GB，实机用 RVZ 或 scrubbed WBFS，不用 4.4 GB ISO。
- RVZ（Dolphin 格式）**免解密**，WBFS/ISO 需实时 AES 解密；但实测 WBFS 不是卡 boot 的原因。

## 9. 给接手 agent 的最短路径

1. 读本文件 → 读 `.workbuddy/memory/2026-11-08.md`。
2. 确认 §5 网络/工具链是否已解除；若用户已把包放进 `smg3ds/dl/`，先按 D5/§5 处理技巧解压。
3. 从 §6 第一个未完成项开始；每完成一项**立即**更新 §3、§5、§6 与 daily log。
4. 任何新补丁都保留原版与优化版对照，行尾统一 LF。
5. 改动渲染器前先读 `src/docs/PORTING.md`「On a real 3DS」——Azahar 对 PICA 的很多行为比真机宽容，模拟器通过 ≠ 真机可用。
6. 用户明确要求：**优化以 New 3DS 实机为准，不要停在模拟器调参**。

---

## 10. 独立便携模拟器实例（2026-11-08 02:40 追加）

用户要求"复制一版模拟器专门跑这个项目"，已完成并**验证通过**。

- 位置：`smg3ds/azahar-portable/`
- 来源：官方 Azahar 2126.2 / HEAD-219d743 的程序文件（exe + dll + plugins + scripting + qt.conf，约 102 MB），**不是** AzaharPlus 魔改版。
- 便携机制：`azahar.exe` 同级存在 `user/` 目录即进入便携模式。`user/config/qt-config.ini` 中**删除了写死的 `nand_directory` / `sdmc_directory`**（`UseCustomStorage: false`），所有数据相对 `./user` 解析，因此整个目录可整体搬走，无需改配置。
- 内容：
  - `user/config/qt-config.ini`：New 3DS = on、CPU 100%、OpenGL、1x；开启 `instant_debug_log` 与 `log_filter=*:Info Debug.Emulated:Debug` 便于看移植程序输出；清空了 `Paths\recentFiles`。
  - `user/sdmc/3ds/SMG-3DS/`：`SMG-3DS.3dsx`(6.7 MB)、`settings.ini`、`game.wbfs`(**同卷 NTFS 硬链接到主实例的美版盘，零额外磁盘占用**)。
  - `user/sdmc/3ds/dspfirm.cdc`：占位文件。
  - `user/nand/`、`user/sysdata/`：从主实例复制（243 KB / 3 KB），保证 homebrew 环境一致。
  - `user/{log,cheats,shaders,states,screenshots}/`：空目录。
  - 未复制主实例的 `states/`(13 MB 即时存档) 与日志，保持干净。
- 启动：`run-smg.bat`（双击）或 `azahar.exe "user\sdmc\3ds\SMG-3DS\SMG-3DS.3dsx"`；说明见 `HOWTO.txt`。
- **验证结果**：日志写入 `.../azahar-portable/user/log/azahar_log.txt`、cheats 路径指向便携 `user/`，主实例 `AppData/Roaming/Azahar/log/` 时间戳未变 → 完全隔离；启动约 85 s 后标题画面正常，`速度 100%/100%`、`应用: 30 帧`、`帧延迟 3.40 ms`，无 `TerminateProcess`。截图：`smg3ds/window_portable.png`。
- **用途**：以后编译出优化版 `.3dsx`，先备份 `user/sdmc/3ds/SMG-3DS/SMG-3DS.3dsx` 再替换，用状态栏数值与 stock 二进制做 A/B；新存档、shader cache、配置都留在这个目录，不污染用户日常模拟器。
- 注意：硬链接在本机有效；若把目录拷到其它卷/机器，`game.wbfs` 会退化为普通 3.3 GB 文件副本，属正常，保持文件名即可。

### 决策 D7
独立实例而非共用主实例。理由：项目仍处于反复替换 `.3dsx` 的开发阶段，共用会污染用户存档/配置/着色器缓存，且不便整体迁移给其它 agent。

### 命令补充
```bash
# 启动独立实例
"/c/Users/WXP/WorkBuddy/2026-11-08-01-41-44/smg3ds/azahar-portable/azahar.exe" \
  'C:\Users\WXP\WorkBuddy\2026-11-08-01-41-44\smg3ds\azahar-portable\user\sdmc\3ds\SMG-3DS\SMG-3DS.3dsx'
# 部署新构建（先备份 stock）
cp <new>/SMG-3DS.3dsx <portable>/user/sdmc/3ds/SMG-3DS/SMG-3DS.3dsx
```

### 工具链状态（02:40）
用户表示正在安装 devkitPro；`smg3ds/dl/` 与 `C:\devkitPro` 由接手 agent 复查。安装到位后按 §5 处理技巧解压拼 `${DEVKITPRO}`，再从 §6 的 T6 继续。

---

## 11. 实机时序模拟档 + `gx perf` 内部日志（02:50 追加，重要）

用户提议"限制模拟器性能来模拟 New 3DS 实机"。结论：**方向可行，但 CPU 要加速、GPU 才要约束，且单靠开关不能完整复现 PICA200 瓶颈**；然而这一轮意外打通了移植程序自己的性能日志通道，价值比模拟本身更大。

### 11.1 反直觉的 CPU 方向
项目文档：Azahar 的 New 3DS CPU 只跑 268 MHz（真机 804 MHz 的 **1/3**），对 CPU 苛刻、对 PC GPU 宽松。所以要贴近实机，CPU 不是限速而是 **超到 ~300%**（`cpu_clock_percentage`，合法范围 25–400%）。GPU 侧才需要约束。

### 11.2 两档配置（已建、可切换）
- `profiles/stock.ini`：`cpu_clock_percentage=100`、`simulate_3ds_gpu_timings=false` → 基线，30 fps。
- `profiles/console-sim.ini`：`cpu_clock_percentage=300`、`simulate_3ds_gpu_timings=true`。
- 切换：`python switch-profile.py stock|console-sim`（**必须先关闭模拟器**，见 §11.3）。
- `simulate_3ds_gpu_timings` 是 Azahar 2126.0 引入的**实验性** GPU 中断队列/时序精度开关，官方说明"真机上跑不到 60 FPS 的游戏，开了在 Azahar 里也跑不到"，默认关闭。它提高的是时序精度，不是把 PC 显卡降速到 PICA200 算力。

### 11.3 关键坑：QSettings `\default` 标记
Azahar 的 `qt-config.ini` 每个键都有一行 `key\default=true|false`。**只要 `\default=true`，Azahar 就忽略你写的 `key=value`，直接用内置默认**。所以光改数值不生效（这解释了此前 `instant_debug_log` / `log_filter` 全部无效，而 `graphics_api` / `resolution_factor` 因原本就是 `\default=false` 所以生效）。
正确做法：改值时**同时**把对应 `key\default=true` 改成 `=false`。已对 `cpu_clock_percentage`、`simulate_3ds_gpu_timings`、`instant_debug_log`、`log_filter` 四处处理，并在新日志中确认生效：
```
Core_CPUClockPercentage: 300
Renderer_Simulate3DSGPUTimings: true
Debugging_InstantDebugLog: true
```

### 11.4 重大收获：`gx perf` 内部性能日志
开启 `instant_debug_log=true` + `log_filter=*:Info Debug.Emulated:Debug`（且 `\default=false`）后，移植程序的 `OutputDebugString` 会进 `user/log/azahar_log.txt`，周期性输出自测明细。**这是做 GPU 优化 A/B 的黄金指标**，远优于状态栏。

console-sim 档标题画面实测（`t=35`，120 帧平均）：
```
33.4 ms/frame (29.9 fps, 2.00 logic steps each)
per logic step: draw 0.7, logic 0.3, animation 0.5, waiting for the GPU 0.0, retrace wait 15.2
per frame: GX stream read on core 2 5.0 ms (0.0 waiting for the PICA), DSP 1.2 ms
1188 primitives, 9211 vertices, 378 triangles, 24 draws
GPU path 9 draws, 1893 triangles, display lists 1153 (55543 bytes)/frame
```
解读：标题画面 `waiting for the GPU 0.0 ms` → **开了 simulate 也没复现真机 50–60 ms 的 GPU 瓶颈**（标题太轻 + 该开关不降算力）；大量时间花在 `retrace wait`（游戏按 30 fps 节奏等 VBlank），说明有空闲。

### 11.5 结论与下一步用法
- 这套档是**测试夹具，不是性能优化**；日常玩请用 `stock`。
- 要真正复现真机 GPU 瓶颈，下一步试 `delay_game_render_thread_us` 注入人为延迟（目标 ~50 ms/帧，注意该值在 ini 里是 QVariant 二进制 `@Variant(...)`，不能当普通整数写，需在 GUI 设或按 QVariant 编码构造），再用 `gx perf` 看 `waiting for the GPU` 是否抬升。
- **优化版 A/B 流程**：编译出 gpu-overlap 版 `.3dsx` → 部署到便携实例 → 同一档配置下对比 `gx perf` 的 `waiting for the GPU`、`GX stream read`、帧时间；重点验证 GPU 等待能否与帧构建重叠。进复杂场景（城堡/过场）再看，标题画面太轻。
- 渲染正确性（天空、mip、Y2R、TEV 夹取）**仍必须上真机**，Azahar 对 PICA 行为比真机宽容，模拟档解决不了。

### 11.6 工具链复查（02:45，明确阻塞）
- 用户已装好 `C:\devkitPro`：只有 MSYS2 本体 + `pacman.exe`，`installed.ini` 勾选了 3DSDev 等组件，但 **`devkitARM` / `libctru` / `citro3d` / `citro2d` / `picasso` / `3dsxtool` / `libzstd.a` 全部 MISSING**。
- `msys2/etc/pacman.conf` 已配好 `[dkp-libs]` / `[dkp-windows]` → `https://pkg.devkitpro.org/...`。
- 实测 `pacman -Sy` 明确失败：`错误：无法从 pkg.devkitpro.org : The requested URL returned error: 403 获取文件 'dkp-windows.db' / 'dkp-libs.db'`。winget 也无 devkitPro 包。
- **需要用户用浏览器代下载**：`https://pkg.devkitpro.org/packages/windows/x86_64/` 下的 `.db` 与 3DS 相关 `.pkg.tar.xz`（devkitARM、libctru、citro3d、citro2d、3ds-tools、3ds-zstd/3ds-portlibs、general-tools、devkitpro-keyring）→ 放 `smg3ds/dl/packages/`。拿到后按 §5 直接 `tar -xf` 拼 `${DEVKITPRO}`，不必跑 pacman。

---

## 12. gx perf 基线数据与提取工具（03:02 追加）

后台实例正常退出后，从 `azahar-portable/user/log/azahar_log.txt` 提取了完整基线（用户实际进游戏约 713 s，跨多个场景）。

- **工具**：`smg3ds/extract_gx_perf.py` —— 解析 Azahar 日志里的 `gx perf: t=` 行，输出紧凑表格 / `--csv` 全量 / `--slow` 仅掉帧点 / 汇总统计。纯 Python，不需编译。**以后每个优化版都用同一工具提取，便于 diff。**
- **数据**：`smg3ds/baseline/console-sim-20261108.csv`（174 采样点 × 17 字段）、`console-sim-table.txt`、`README.md`（采集条件、汇总、掉帧点、结论、A/B 复现命令）。
- **关键数字**：fps 平均 29.66 / 最低 17.1；**`waiting for the GPU` 平均 0.06 ms、最大 4.9 ms**；`GX stream read on core 2` 平均 4.60 / 峰值 17.4 ms；`retrace wait` 7–16 ms；低于 29 fps 的采样点 8 个（t=23/27/71/119/208/412/437/485）。
- **结论（修正 §11.5 的期待）**：即便 `cpu_clock_percentage=300` + `simulate_3ds_gpu_timings=true`，**真机 50–60 ms GPU 瓶颈完全没被复现**（GPU 等待几乎为 0）。掉帧来自 CPU 侧逻辑/加载（t=23 的 `logic 12.5 ms`）与场景切换（t=71 的 GX 12.6 ms + GPUwait 4.9 ms）。`movie frames decoded` 全程 0 → 用户说的"过场卡"更像故事书/场景切换/资源加载，不是 THP 电影解码。
- **用途边界**：基线适合验证 CPU 侧与流水线重叠逻辑有没有回归；**不能外推真机 GPU 收益**。要模拟真机 GPU 仍需注入 `delay_game_render_thread_us`（QVariant 二进制，须 GUI 设）约 50 ms/帧。
- **状态**：便携实例已用 `switch-profile.py stock` 切回默认档（CPU 100% / simulate=false），无残留进程。下次打开即为正常可玩状态；做 A/B 时先关模拟器再切 `console-sim`。
- 渲染正确性（天空、mip、Y2R、TEV 夹取）依旧只能上真机验证。

---

## 13. 缺口清单（03:10 全面复查）

### 已具备 / 本轮补齐
- 源码两版：`src/`（原版）与 `src-gpu-overlap/`（补丁版，真实差异 31 行，LF 行尾）。
- **Petari 子模块已补齐**（本轮发现 tarball 不含 submodule，`upstream/Petari` 原为 0 文件）：经 `codeload.github.com` 下载 pinned commit `31bacf2e4f9788f50c1e7b2e501b3a66da9dd8f2`（6.0 MB / 4,853 条目），解压到两份源码目录，各 4,634 文件，`diff -rq` 完全一致。
- **源码生成链验证通过**：`python src-gpu-overlap/tools/prepare-petari.py <PETARI> build-check/petari` → exit 0，生成 354 个文件；`Spine.cpp` 等 CMake 前置检查项存在。
- 着色器 `shaders/gx.v.pica`、`model.v.pica` 齐全。
- 独立便携模拟器、双档配置、`gx perf` 基线（174 采样点）、提取工具、完整台账与记忆。
- 美版 RMGE01 WBFS 已挂载；CMake 3.x / Ninja / Python 3.13 / Git 可用。

### A. 硬阻塞（唯一下不来 `.3dsx` 的原因）
`C:\devkitPro` 只装了 MSYS2 本体 + pacman，`dl/` 仅有安装器与 `msys-2.10.0.1.7z`，`dl/packages/` 不存在。以下 9 项全 MISSING：
`devkitARM`(arm-none-eabi-g++、3dsx.specs)、`libctru`(含 `default_icon.png`)、`libcitro3d.a`、`libcitro2d.a`、`picasso`、`3dsxtool`、`smdhtool`、`portlibs/3ds/lib/libzstd.a`、`zstd.h`。
`pacman -Sy` 明确 403（`dkp-libs.db` / `dkp-windows.db`），winget 无 devkitPro 包。
→ **需用户浏览器下载 `.db` + 3DS 相关 `.pkg.tar.xz` 到 `smg3ds/dl/packages/`**，之后按 §5 直接 `tar -xf` 拼 `${DEVKITPRO}`。

### B. 软阻塞（可并行补，不卡 3DS 编译）
- host 回归测试：MSYS2 自带 GCC 16.2.0（`usr/bin/g++`），但 `-lasan` / `-lubsan` 缺失 → ASan/UBSan 跑不了；普通 `ctest` 仍可跑。MSYS2 的 `msys` 仓库同步无报错（只有 dkp 403），可尝试 `pacman -Sy --repo msys` 后装 sanitizer 或 `mingw-w64-x86_64-gcc`。
- 源码为 tarball、无 `.git` 历史；`git apply` 可用但多轮补丁管理不便。建议 `git init` + 基线提交（未做，待决定）。

### C. 真机验证条件（需用户确认/提供）
- New 3DS / New 2DS XL 实机 + Luma3DS + Homebrew Launcher + ftpd。
- **真实 `dspfirm.cdc`**：当前 sdmc 里是 105 B 占位文本，真机会无声；需 DSP1 导出。
- 3.3 GB WBFS < FAT32 4 GB 上限，实机可用；RVZ 免解密更优但需转换工具（本机无 Dolphin/wit）。
- 真机诊断靠 `settings.ini` 的 `dev.gx_timing` / `dev.gx_zones`，且测试构建禁止渲染线程写 SD 卡。

### D. 待做工作（不缺工具，缺推进）
- T8：城堡每帧 12 次 EFB copy 的量化分析与削减（到 30 fps 的关键，尚未开始）。
- T6/T7：编译 + Azahar A/B 验证（等 A 解除）。
- 模拟真机 GPU 瓶颈：`delay_game_render_thread_us` 注入约 50 ms（QVariant 二进制格式，须在 GUI 设）。
- 过场卡顿复现：需特意进入过场抓 `movie frames decoded` 与 `logic`（基线里全程为 0）。

### E. 环境限制（不可绕过，别重试）
- `wsl.exe` 在安全中心黑名单 → Docker Desktop 路线不可用。
- `pkg.devkitpro.org` Cloudflare 403、`github.com/.../releases/download` 502、`api.github.com` 曾限流（已重置）；`codeload.github.com` 与 winget 源可用。

---

## 14. 与其它 3DS 项目共存的冲突面（03:22，重要）

用户同时在跑另一个《超级马力欧 64》3DS 移植项目，需避免互相干扰。

### 已发生的事故 / 禁令
- **严禁再执行 `taskkill /F /IM azahar.exe`**：它按进程名全局终止，会误杀其它项目的 Azahar 实例。本项目排障阶段用过多次，可能已影响对方，属操作失误。
- 替代方案：`smg3ds/stop-portable.py`（`--dry-run` 可预览）。它用 Toolhelp32 枚举进程、`QueryFullProcessImageNameW` 比对可执行路径，**只终止 `smg3ds/azahar-portable/` 下启动的实例**，其它实例一律不动。
- 需要重启本项目模拟器时：先 `python stop-portable.py`，再启动；不要按名杀。

### 冲突面清单
| 资源 | 风险 | 本项目状态 / 处理 |
| --- | --- | --- |
| Azahar 进程 | **高**（全局 taskkill 误杀） | 已改精确停止脚本；当前无 azahar 进程 |
| GitHub API 限流 | 中（按出口 IP 共享 60 次/小时） | 曾撞限流；尽量用 `codeload.github.com` 与本地已有资源，少调 API |
| `C:\devkitPro`（共享工具链） | 中 | 本项目**只新增** `portlibs/3ds/lib/libzstd.a` + `include/zstd.h`/`zstd_errors.h`，未改动任何既有包。若另一项目也编译 3DS，共用是安全的；但**不要同时跑 `pacman -Sy`**（数据库/缓存锁） |
| `%APPDATA%\Roaming\Azahar`（主模拟器） | 中 | 早期放入 `sdmc/3ds/SMG-3DS/`（3dsx + 3.3 GB 镜像副本 + settings.ini），改过日志配置后已恢复并留 `.smg-backup`。若另一项目用主实例，注意 `qt-config.ini` 会被任一实例退出时写回 |
| `D:\AzaharRun`（AzaharPlus） | 低 | 仅放了一个硬链接 `game.wbfs` 与项目文件；配置已恢复原样 |
| GDB stub / UDP 端口 | 低 | 便携实例 GDB 4000、主实例 24689、cemuhook UDP 26760；两个 Azahar 同时开时可能争端口，但不致命 |
| 工作区文件 / build 目录 | 无 | 本项目全部在 `smg3ds/` 下，`build-3ds/`、`build-check/` 独立 |
| CPU / 磁盘 | 低 | 编译 `-j 8` 会占满 CPU，两边同时编译会互相拖慢，不产生错误 |

### 隔离措施（已做）
- 独立便携实例 `azahar-portable/` 自带 `user/`（config/nand/sdmc/log/shaders），与主实例完全隔离。
- 美版镜像用同卷 NTFS 硬链接，避免重复占用 3.3 GB。
- 双档配置 `profiles/` + `switch-profile.py`，切档前须先精确停止。

### 给另一项目的建议
使用各自的便携 Azahar + 独立 `user/`；避免同时 `pacman` 操作；注意 GitHub API 限流是共享的；不要按进程名批量终止模拟器。

---

## 15. 工具链到位与 Windows 构建适配（03:26）

用户已装好 devkitPro，复核 10 项关键件：

| 项 | 状态 |
| --- | --- |
| `devkitARM/bin/arm-none-eabi-g++.exe` | OK（release 66 / GCC 15.1.0） |
| `libctru/include/3ds.h`、`lib/libctru.a`、`default_icon.png` | OK（libctru 2.5.0-2） |
| `libcitro3d.a`(1.7.1-2)、`libcitro2d.a`(1.6.0-1) | OK |
| `tools/bin/{picasso,3dsxtool,smdhtool}.exe` | OK |
| `portlibs/3ds/lib/libzstd.a` | **本项目自行补齐** |

### 本地补齐 zstd（无需用户下载）
pacman 列表里的 `zstd 1.5.7` / `libzstd 1.5.7` 是 MSYS2 的 x86_64 包，`portlibs/3ds/` 只有 `bin`，**不是** 3DS 平台库。
- 从 `codeload.github.com/facebook/zstd/tar.gz/refs/tags/v1.5.7` 取源码（2.4 MB）。
- 项目 `DiscImage.cpp` 只用 4 个解压 API：`ZSTD_createDCtx` / `ZSTD_decompressDCtx` / `ZSTD_isError` / `ZSTD_freeDCtx`，故只交叉编译 `lib/common/*.c` + `lib/decompress/*.c`（排除 `pool.c`/`threading.c`），flags：
  `-O2 -march=armv6k -mtune=mpcore -mfloat-abi=hard -mtp=soft -D__3DS__ -ffunction-sections -fdata-sections -DZSTD_MULTITHREAD=0 -DZSTD_LEGACY_SUPPORT=0 -DXXH_STATIC_LINKING_ONLY`
- 10 个 .c 全部编译成功，`arm-none-eabi-ar` 打成 `libzstd.a`（125 KB），`nm` 验证 4 个符号齐全。
- 部署到 `C:/devkitPro/portlibs/3ds/lib/libzstd.a` 与 `include/{zstd.h,zstd_errors.h}`（**只新增文件，未改动既有包**）。
- 源码与产物备份在 `smg3ds/zstd-src/`、`smg3ds/zstd-arm/`。

### Windows 构建适配（两处，均在 `src-gpu-overlap/`，原版 `src/` 保持干净对照）
1. `tools/3ds-toolchain.cmake`：编译器路径加 `if(WIN32) set(DKP_EXE ".exe")`，否则 CMake 报 "not a full path to an existing compiler tool"。
2. `tools/prepare-petari.py`：脚本生成 7 个"大小写别名头"（如 `include/revolution/FS.h` → `#include "revolution/fs.h"`），本意是适配 Metrowerks 不区分大小写。Linux 大小写敏感下两文件不同、工作正常；**Windows 大小写不敏感下二者同一文件 → 自引用 → `#include nested depth 200` 编译失败**。已加 `case_sensitive_filesystem()` 探测，仅在大小写敏感文件系统上生成这些别名；脚本自带的 stale 清理会自动删除已生成的 5 个别名（实测 `prepare-petari: removed ...`，生成文件 354→349）。
   - 连带错误 `'MEMAllocator' does not name a type` 等也是该自引用的连锁反应，修后应一并消失。
3. CMake configure 已通过（GNU 15.1.0 / Python 3.14 / Petari 生成链）；命令见 §7，须用**绝对路径**传 `-S`/`-B`/`-DCMAKE_TOOLCHAIN_FILE` 并显式 `-DCMAKE_MAKE_PROGRAM=<ninja.exe 绝对路径>`。

### 第一次构建结果（已修）
`cmake --build build-3ds -j 8` 失败于别名头自引用（日志 `build-3ds.log`）。修复后以 `-j 4` 重编（降低 CPU 占用以免干扰另一个 3DS 项目），日志 `build-3ds-2.log`、真实退出码写入 `build-3ds-2.exit`。
> 注意：早期把 `echo` 放在管道末尾会让后台任务的 exit code 永远是 0，**必须单独落盘退出码**。

---

## 16. 构建成功 + 优化版 A/B（03:40）

### 又修了 3 处 Windows/工具链兼容问题（均在 `src-gpu-overlap/`，原版 `src/` 保持干净）
3. **C 符号命名空间**：`extern "C" char __C3D_Context[];`（补丁新增）与 `extern "C" u32 __ctru_heap_size;`（原版就有）写在匿名 namespace 内，本机 GCC 15.1 会修饰成 `_ZN3smg12_GLOBAL__N_1...`，链接报 undefined（`libcitro3d.a` / `libctru.a` 里确实是 C 符号）。已把两个声明提到**全局作用域**（`namespace smg {` 之前），namespace 内引用保持不变。`nm` 验证 ELF 里 `gxCmdQueueRun/Stop/Wait` 均为 `T`（被链接保留 → 补丁代码确实在调用）。
4. **POST_BUILD 弱引用检查**：`CMakeLists.txt` 的 `smg_no_missing_weak()` 用 POSIX `sh -c "…{…}"`，Windows 下被 `cmd.exe` 拆坏（`'__register_frame_info' 不是内部或外部命令`）。加 `if(CMAKE_HOST_WIN32) return() endif()` 跳过该检查（链接器本身仍解析符号，不影响正确性）。**坑**：`WIN32` 指目标平台（此处 Generic/3DS），必须用 `CMAKE_HOST_WIN32`。
5. **host 构建编码**：MSYS2 里 Python 默认 GBK 读 Petari 源码报 `UnicodeDecodeError`；用 `PYTHONUTF8=1 PYTHONIOENCODING=utf-8` 后 `cmake -S src-gpu-overlap -B build-host -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Debug` 通过。
6. 每次用 Python 改源码后必须把 CRLF 规范回 LF（Windows `open(...,'w')` 会自动转换，否则 diff 变成全文件差异）。

### 最终构建
`cmake --build build-3ds -j 4` **exit=0**，产物：
- `build-3ds/mario_probe.3dsx` **6,589,820 B**（游戏本体）
- `build-3ds/SMG-3DS.3dsx` 892,000 B（早期场景查看器）
> 注意：v0.1.0 Release 包里那个 6.7 MB 的 `SMG-3DS.3dsx` 其实是**重命名后的 `mario_probe.3dsx`**，与编译出的 892 KB 同名文件不是一回事，部署别搞混。

### A/B 部署与结果（无回归）
- 便携实例 `user/sdmc/3ds/SMG-3DS/SMG-3DS.3dsx` 备份为 `.stock`（6,704,396 B），替换为编译出的 `mario_probe.3dsx`；用 `switch-profile.py console-sim` 切到与基线相同档位。
- 启动后画面正常进游戏（见 `window_optimized.png`：Mario/星币/星屑，状态栏 `速度 100%/100%`、`应用: 30 帧`、`帧延迟 4.16 ms`），**无 `TerminateProcess`、无黑屏**。
- 用 `extract_gx_perf.py` 提取：27 采样点、fps 平均 29.39、GPUwait 平均 0.05、掉帧点仅 t=10(17.3fps, logic 12.4ms 启动加载) 与 t=14(28.2fps)，与基线启动段一一对应。
- **严格同时段对比**（日志时间戳 t<50 的 11 个干净采样 vs 基线前 11 点）：
  | 指标 | stock | optimized | delta |
  | --- | --- | --- | --- |
  | fps | 28.61 | 28.63 | +0.02 |
  | ms/frame | 35.85 | 35.80 | -0.05 |
  | waiting_gpu_ms | 0.11 | 0.12 | +0.01 |
  | retrace_wait_ms | 15.45 | 15.35 | -0.10 |
  | logic_ms | 1.34 | 1.38 | +0.05 |
  | gx_stream_ms | 4.44 | 6.19 | +1.75 |
  → **帧率/帧时间/GPU 等待基本完全一致，无回归**；`gx_stream` 差异来自采样窗口内场景不完全一致，不是补丁退化。结论印证作者所述"补丁在 Azahar 保持 30 fps"。
- 数据：`baseline/optimized-20261108.csv`；日志 `user/log/azahar_log.txt`。

### 坑：日志时间戳污染
本次 `azahar_log.txt` 里 t 序列为 `5 10 … 47 713 717 … 830`，后半段是旧基线残留（归档后仍被写入）。**A/B 只取 t<50 的采样**；以后采集前先清空/移走 user/log 下所有 `azahar_log*` 文件，并用 `t_s` 单调性校验。

### 仍未完成
- host 回归：configure 已过，`cmake --build build-host -j 4` + `ctest` 在后台跑（日志 `build-host.log` / `ctest.log`，退出码 `.exit`）。MSYS2 GCC 16.2 缺 `libasan`/`libubsan`，**ASan/UBSan 版本仍未跑**；需 Docker 或补齐 sanitizer。
- T8：12 次 EFB copy 分析与削减（尚未开始）。
- **真机验证**：gpu-overlap 补丁从没上过 PICA200；Azahar 的 `waiting for GPU≈0` 决定收益只能在真机测。需实机 + ftpd + 真实 `dspfirm.cdc`。

### host 回归状态（Windows 环境限制，非代码问题）
- `cmake -S src-gpu-overlap -B build-host -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Debug` 在 MSYS2 内需 `PYTHONUTF8=1`（否则 Python 以 GBK 读 Petari 源码报 `UnicodeDecodeError`），configure 已通过。
- 但 `cmake --build build-host -j 4` 失败：`cc1plus: error: no iconv implementation, cannot convert from UTF-8 to CP932`（MSYS2 GCC 16.2 缺字符集转换实现），`LC_ALL=C` 无效；CTest 28 项全 `Not Run`。
- MSYS2 GCC 还缺 `libasan`/`libubsan`，ASan/UBSan 版本也跑不了。
- **结论**：host 回归请按官方方式在 Docker/Linux 跑（`tools/test-host.sh`，镜像 `devkitpro/devkitarm@sha256:116af...`）；或给 host 构建加 `-finput-charset=UTF-8 -fexec-charset=UTF-8` 并补齐 sanitizer 后再试（未做，收益有限，3DS 目标构建与 Azahar A/B 已通过）。日志：`build-host.log` / `build-host-2.log` / `ctest.log`。

---

## 17. EFB copy 热点分析（T8 第一步，03:45）

### 每次 EFB copy 的三段开销（`source/compat/GxRender.cpp::gpuCopy`, 约 2593–2700）
1. **split**：`runSplit()` = `flushVertices()` + `C3D_FrameSplit(GX_CMDLIST_FLUSH)` + `gxCmdQueueRun()`（gpu-overlap 补丁新增，让已切出的部分立刻上 GPU）。
2. **transfer**：`GX_TextureCopy` 把 framebuffer 的目标 tile 行搬进 256×512 的 `scratch` VRAM 纹理。已有优化：只拷 copy 采样到的 tile 行（`firstRow..endRow`），左右各留一列给 filter，且保证字节数非零（真机零字节 transfer 会冻结）。
3. **pass**：`copyCombiner()` / `copyStages()` 按 filter taps 采样 scratch，输出到按 Wii 地址缓存的 VRAM 纹理 `gpuCopies[copy.address]`（尺寸变化才重建 render target / texture）。

作者记录：城堡每帧 **12 次** copy，每次 = split + transfer + pass，是 GPU 50–60 ms 的主要来源（HANDOFF §"What was open" #2）。

### 已有优化，别重复造轮子
- `sCopiesStayOnGpu`：能走 PICA 的 copy 不再逐 texel CPU 编码（PORTING.md「EFB copies on the GPU」）。
- 按地址复用目标纹理、scratch 全局复用、`copyStages` 预检 combiner 阶段上限（超限退回 CPU 路径）。
- 深度 peek、texture copy、movie frame 各自走 `runSplit()`；`endFrame()` 在 `C3D_FrameEnd` 前 wait/stop 队列，避免 display transfer 抢在帧标记前完成导致黑屏。

### 真机硬约束（PORTING.md 1518，改动前必读）
- `C3D_SyncTextureCopy` 以 0 做 split 会把命令留在 CPU cache，真机随机冻结；**EFB copy 必须用带 `GX_CMDLIST_FLUSH` 的 split**，所以"直接去掉 split"不可行。
- 任何 transfer 不能搬 0 字节。
- Azahar 对 PICA 行为宽容，模拟器通过 ≠ 真机可用；改动必须上机验证。

### 下一步该做的（按收益排序）
1. **先测量再改**：作者写过"按阶段逐类移除 GPU 工作并计时"的测试构建但没跑完。建议在 `dev.gx_timing` / `dev.gx_zones` 下做 4 个构建（全开 / 去 transfer / 去 pass / 去 split），在真机记录每帧 GPU ms，得出三类工作各占比，避免盲目优化。
2. 若 transfer 占大头：进一步收窄 `firstRow..endRow`（按实际 filter taps 精算，而非 ±1 列）、探索多 copy 共用一次连续 transfer。
3. 若 pass 占大头：检查 12 个 copy 的目标纹理是否可复用同一 combiner program（当前 `copyCombiner` 按 taps/weights/noAlpha 生成），减少 shader 切换与 `C3D_TexInitVRAM`。
4. 若 split 占大头：分析连续 copy 之间的依赖（后一个是否读前一个 `gpuCopies` 的输出），只在真正需要同步处 split。

**当前停在分析阶段是有意的**：没有真机 GPU 计时数据就改渲染器，极可能引入真机冻结（作者多次踩过）。T8 的实现需真机 + ftpd 配合。

---

## 18. 控制映射：体感摇晃 → 按键（03:45 答疑）

用户问"Wii 版靠体感旋转，移植到 3DS 能否用某个键代替摇晃"。**答案：已经实现，就是 `bind.spin`**，不需要改代码。

### 默认映射（Release 与两个实例一致）
| 动作 | Wii | 3DS | Azahar 默认键盘 | `settings.ini` |
| --- | --- | --- | --- | --- |
| 跳跃 | A | A 或 B | A 或 S | `bind.jump=A+B` |
| **旋转（摇 Remote）** | **shake** | **X 或 Y** | **Z 或 X** | **`bind.spin=X+Y`** |
| 蹲下/砸地 | Nunchuk Z | L | Q | `bind.crouch=L` |
| 发射星屑 | B | R | W | `bind.shoot=R` |
| 镜头归位 | Nunchuk C | ZL | 1 | `bind.camera=ZL` |
| 指针归位 | — | ZR | 2 | `bind.recenter=ZR` |
| 暂停 | + | Start | M | `bind.pause=Start` |

### 实现链路（源码已确认）
1. `source/core/Settings.cpp::defaultBindings()` → `bindings[Spin] = X | Y`（位或，即**任意一个**键）。
2. `source/core/Input.cpp::toWiiInput()` → `result.swing = frame.spin.held; result.swingTrigger = frame.spin.pressed;`，把 spin 动作翻译成 Wii 的显式 shake 状态，与 Wii 按键位掩码一起交给原版游戏代码。
3. `source/compat/Kpad.cpp` → `smgSpinHeld()` / `smgSpinPressed()` 供适配过的 `WPadHVSwing::update` 查询，注释原文："The 3DS has no remote to shake: the spin buttons are its swing."
4. PORTING.md：「spin to a digital shake」。所以原游戏看到的就是"摇晃"事件，跟真 Wii Remote 走同一套逻辑。

### 改键方法
- 文件：两个实例各一份（改哪个实例就改哪个；建议两份保持一致）：
  - `smg3ds/azahar-portable/user/sdmc/3ds/SMG-3DS/settings.ini`
  - `%APPDATA%\Roaming\Azahar\sdmc\3ds\SMG-3DS\settings.ini`
- 语法：`bind.spin=<键名>`；可用键名 `A B X Y L R ZL ZR Up Down Left Right Start Select`；多个用 `+` 连接表示**任意一个触发**（`Settings.cpp::parseKeys` 按位或）。
- 例：只留单键 `bind.spin=Y`；或改成肩键 `bind.spin=L+R`。**改完重启游戏生效**（启动时读 settings.ini）；游戏内另有 Remap 页面可直接改。
- `Settings.cpp` 的 `actionNames` 只有 8 个动作：jump / spin / crouch / shoot / camera / recenter / pause / minus。

### 限制与易混点
- 是**数字 shake**：只有 held / pressed 两个状态，没有摇晃强度或加速度的模拟量。PORTING.md 明确写「Digital spin and stylus data remain explicit boundary values until the swing/pointer and GamePadUtil work is finished」，TODO 里还有「Integrate the input boundary into GamePadUtil/WPad, including explicit digital spin input」。SMG 的旋转本身是二值触发，实际够用；若某机制依赖连续摇晃强度，手感会与原版不同。
- Mario 要等 Gateway Galaxy 从 Luma 处获得能力后才能旋转，与原版一致，不是键位问题。
- **别和指针体感混淆**：`pointer=motion` 用 3DS 陀螺仪控制星屑指针（Azahar 里按住右键拖动模拟），`pointer=cstick` 用 C-Stick，默认 `pointer=stylus` 是下屏鼠标。这与 spin 是两套独立输入。

---

## 19. 下一步优化路线（决策 D8：先测量，后优化）

### 核心判断
**PC 侧的性能探索已经到边际，继续在 Azahar 调设置或盲改渲染器没有依据。**
- 真机：约 70 ms/帧（≈14 fps），GPU 占 50–60 ms；渲染线程等 GPU 约 51 ms，再构建 23 ms，GPU 在构建期空闲。
- Azahar：`waiting for the GPU` 平均 0.06 ms、最大 4.9 ms（基线 174 采样）；`console-sim` 档（CPU 300% + `simulate_3ds_gpu_timings=true`）也没复现真机 GPU 瓶颈。
- 因此**真机 GPU 时间花在 transfer / pass / split / draw 各多少，目前完全是未知数**。作者写了"按阶段逐类移除 GPU 工作并计时"的测试构建但没跑完（HANDOFF open #2），这正是最大缺口。

### 阶段 1（阻塞项）：上真机测量
- 需要：New 3DS / New 2DS XL + Luma3DS + Homebrew Launcher + ftpd；**真实 `dspfirm.cdc`**（DSP1 导出，否则无声）。
- 部署 3 个 `.3dsx` 做 A/B：① stock（`SMG-3DS.3dsx.stock` 备份 / v0.1.0 Release）② 已编好的 gpu-overlap 版（`build-3ds/mario_probe.3dsx`）③ 测量构建（分阶段关闭一类 GPU 工作）。
- 采集：`settings.ini` 开 `dev.gx_timing=1`、`dev.gx_zones=1`，用 `gx perf` 的 `render thread zones` / `renderer time per frame` 明细。`perfLine()` 输出到 `stderr`（`GxRender.cpp:2349`），3DS 上需经 3dslink / ftpd 或下屏 console 取回。
- **硬约束**：测试构建**绝不能在渲染线程写 SD 卡**（作者实测 +150 ms/帧）；先确认 stderr 在真机上的落点再开日志。
- 目标产出：50–60 ms GPU 中三类工作占比 + gpu-overlap 的实际收益（补丁从未上过真机）。

### 阶段 2：按测量数据选唯一主攻方向
| 若占大头 | 主攻 |
| --- | --- |
| transfer | 收窄 `firstRow..endRow`（按实际 filter taps 精算而非 ±1 列）、探索连续 copy 合并 transfer |
| pass | 复用 `copyCombiner` program、减少 shader 切换与 `C3D_TexInitVRAM`、检查 12 个目标纹理是否可合并 |
| split | 分析相邻 copy 的依赖，仅在真正需要同步处 split（受 `GX_CMDLIST_FLUSH` 硬约束限制） |
| 主渲染 draw | 减少 draw calls / 填充率（已有批处理优化，需数据支撑再动） |

### 阶段 3（并行支线，不依赖真机测量）
正确性/完成度修复，低风险、可在 Azahar 验证：
- HOME/电源菜单关闭挂起：作者给了明确 fix —— `aptExit` 之后补发 `APT_CloseApplication` 再等结束（HANDOFF open #3）。**这是当前性价比最高的一项**。
- 天空蓝色板块：把 Sky/Air/Sun 的 display list 走 CPU guard-band 路径（open #4）。
- mip 层级：tint 各级颜色与真机截图逐层比对（open #5）。
- 水面、阴影、过场两条白色虚线（open #7）。

### 阶段 4：回归与验证
- 每个改动都要 A/B：`extract_gx_perf.py` 比 `waiting_gpu_ms` / `gx_stream_ms` / `ms_per_frame`（同一场景），真机再比帧时间。
- host 回归按官方方式在 Docker/Linux 跑 `tools/test-host.sh`（本机 MSYS2 缺 iconv/ASan，见 §16）。
- `mwerks-only-asm.py`、`ub-scan.sh` 必须保持 0。

### 明确不推荐
- 继续调 Azahar 设置（CPU 超频 / Vulkan / 分辨率）：瓶颈与真机相反，无收益。
- 无真机数据就改渲染器：PICA 对 split/transfer 零字节等极敏感，作者多次踩过随机冻结。
- CPU 侧微优化（如静态 BCK 关节缓存，约省 10% 骨骼动画）：真机是 GPU-bound，优先级最低。

### 需要用户提供的
实机 + ftpd 通道 + 真实 `dspfirm.cdc`；或者授权先做阶段 3 的纯软件修复（HOME 挂起优先）。

---

## 20. 旁支调研：黄昏公主 → New 3DS 可行性（03:54，非主线任务）

用户问《塞尔达传说：黄昏公主》移植可行性。结论：**概念验证层面已被他人证实可行；完整可玩未证实**。以下为外部事实，多家报道交叉印证，数值以官方仓库为准。

### 现状（2026-11）
- `zeldaret/tp`：GameCube 版 **100% matching**（2025-12，约 48k 函数、11.5 MB C++/C、CC0），但 fully linked 87.13%；**Wii 版（RZDE01 等）仍在推进，约 53%（2026-05）**。仓库明确声明只做反编译、不做移植。
- `TwilitRealm/dusklight`：基于 GC decomp 的 PC 原生移植，2026-05-09 首发，v2.0.x 支持 mod/randomizer/Wii 盘读取，但仍是 GC 的 HUD/控制，**不支持 Wii 体感**；另有 Courage Reborn。
- **Game of Tobi（Brendan Tobias，曾做 SM64→GBA）已在做 3DS 原生移植**：2026-07 首次展示，09-28 放出 27 分钟 New 3DS 实机视频，**立体 3D 已工作**，作者称在 New 3DS 上"works very well"；仍有掉帧、卡顿、贴图/资源 pop-in，早期版崩溃频繁，**无发布日期、未见公开源码仓库**。
- New 3DS 规格：804 MHz ARM11 四核 / 256 MB RAM（64 MB 系统占用）/ 10 MB VRAM / PICA200 @204–268 MHz；上屏立体模式每眼 400×240。老 3DS 为 268 MHz 双核 / 128 MB。
- TP 的 Wii 版相对 GC 版：世界镜像、体感挥剑 / Nunchuk 摇晃 / IR 瞄准、4 道具槽、无自由镜头；GC 版是纯按键 + C-stick 自由镜头。**GC 版更适合 3DS**（也避开未完成的 Wii decomp）。

### 判断
- 有利：反编译完整且 CC0；有成熟 PC 移植可参考图形层设计；GC 版无需模拟体感；已有实机 PoC；New 3DS 内存比原机宽裕。
- 主要风险：**GPU**（本项目真机实测 70 ms/帧、GPU 占 50–60 ms，TP 视距更远、后处理更多，很可能同量级或更差）；内存/资源流式加载（Tobi 自称"RAM 是一场战争"）；**立体 3D 双份渲染与 GPU 瓶颈直接冲突**；GC 音频栈与 Wii JAudio2 不同。
- 代码规模约 11.5 MB、48k 函数，与 SMG-3DS 的接入工作量同级。

### 与本项目基础设施的复用度
| 组件 | 复用度 | 说明 |
| --- | --- | --- |
| `GxRender.cpp`（GX 命令流→PICA200、TEV→combiner、批处理、EFB copy） | **高** | GX 原是 GC 的 API，Wii GX 是其超集；最有价值的资产，但 TP 的 TEV 用法与后处理需扩展 |
| 工具链 / 便携实例 / `gx perf` 基线 / A/B 方法 | **高** | 与游戏无关的工程方法，可直接搬 |
| 线程/内存/盘读取思路、输入绑定架构、THP 类视频解码 | 中 | 框架可借鉴，细节需重写 |
| `WiiDsp`（JAudio2 软件实现）、Wii SDK compat（WPAD/IOS 等）、Wii 分区 AES 解密 | 低 | GC 平台不需要 / 栈不同 |

### 建议的最小验证（若真要评估）
把 TP 一帧的 GX 命令流喂进本项目 `GxCommandProcessor`，统计 TEV→combiner 精确覆盖率（本项目 SMG 基线约 6,987/7,780 ≈ 89.8%），快速判断渲染层能否复用——比直接起新项目便宜得多。**先确认 Tobi 项目是否开源/招人，避免重复造轮子。**

官方来源：`github.com/zeldaret/tp`、`github.com/TwilitRealm/dusklight`、`decomp.dev/zeldaret/tp`；Tobi 项目仅见 YouTube 频道「Game of Tobi」。注意搜索结果含多个第三方聚合/SEO 站，具体数值以官方仓库为准。

---

## §21 实机安装包交付（2026-11-08 16:20）

用户问「马里奥银河的实机安装包有吗」。结论：**只有 .3dsx + SD 卡目录，没有 .cia，也不能装到主菜单。** 项目必须直接读 SD 卡上的盘镜像与 settings.ini，CIA 沙箱反而不适合；本机也没有 makerom/bannertool。已整理成可直接拷卡的包。

### 交付物
| 路径 | 说明 |
| --- | --- |
| `smg3ds/SMG-3DS-hardware.zip` | 6.42 MB，不含盘镜像，CRC 校验通过 |
| `smg3ds/real-hardware/` | zip 的解包形态，可直接整体拷到 SD 卡根 |
| `real-hardware/README.txt` | 中文部署说明（硬件/系统、安装步骤、按键、已知问题、测量键） |
| `real-hardware/prepare-disc.py` | 可选：自动找到本机美版镜像并复制进包，带 `--check` 干跑 |

包内结构：`3ds/dspfirm.cdc`、`3ds/SMG-3DS/{SMG-3DS.3dsx, settings.ini, nand/}`、`optional/SMG-3DS.gpu-overlap.3dsx`。

### 关键决策
1. **主程序用官方 v0.1.0 原版**（6,704,396 B），不用优化版。理由：优化版只在 Azahar 验证过，作者与我们都**没让它上过 PICA200**；实机包应以能启动为第一优先。优化版放 `optional/`，README 写明覆盖方法与回滚。
2. **`dspfirm.cdc` 换成真实 dump**：`D:\AzaharRun\user\sdmc\3ds\dspfirm.cdc` 是 **49,756 B 二进制**（零字节率 ~10%，非文本），来自用户本机 AzaharPlus 便携实例。官方 Release 里的 105 B 是占位文本，真机上会导致无声。已在 README 注明"最稳妥仍用自己机器 DSP1 导出、勿外发"。
   - 注意：主实例与 `azahar-portable` 的 sdmc 里仍是 105 B 占位文件，模拟器侧不受影响。
3. **镜像不需要转 RVZ**：本机美版 WBFS = 3,508,535,296 B = 3.268 GiB，已 scrubbed，**在 FAT32 单文件 4 GiB−1 限制内**，直接命名 `game.wbfs` 放进去即可（修正 §8 里"实机用 RVZ"的笼统说法）。SD 卡须 FAT32、剩余 ≥4 GB。
4. 包内**不含盘镜像**（版权 + 3.3 GB），只给本机路径与 `--check` 校验脚本。`prepare-disc.py` 实测：WBFS 头 OK、game ID `RMGE01`、FAT32 可放。

### 本轮从源码新挖出的信息（已写进 README §7）
`source/core/Settings.cpp:137` 支持一整套开发键，`docs/PORTING.md:1398` 有精确语义：
- `dev.gx_timing=1` 渲染器分项；`dev.gx_zones=1` 按渲染线程阶段切分；**`dev.gx_null=1` 什么都不画，测游戏自身开销** —— 三者做差即可在真机量化 GPU 占比，正是 §19 阶段 1 缺的"分阶段计时构建"的现成开关，不必自己改渲染器。
- 其它：`dev.gx_dump` / `dev.gx_check` / `dev.gx_inline` / `dev.gx_mips` / `dev.skip_story`。
- 固定场景 A/B：`dev.start=GALAXY N [ZONE]`、`dev.galaxy=GALAXY N`、`dev.warp=X Y Z [秒]`；配合 `dev.skip_story=1` 最省时。
- 两条约束：`dev.gx_timing` 每次读时钟在 Azahar 要 150 cycles，全开最多拖慢被测对象 1/5；测试构建禁止渲染线程写 SD 卡（+150 ms/帧）。

### 仍未验证 / 待用户提供
包本身未上过实机。需 New 3DS/2DS XL + Luma3DS + Homebrew Launcher + ftpd；真机约 14 fps、天空/mip/水面异常、HOME 关闭可能挂起。真机 `gx perf` 采集与 gpu-overlap 收益仍是 §19 阶段 1 的唯一阻塞项。

### 边界
本轮只在 `smg3ds/` 内新建文件、只读 D 盘镜像；未启动/终止任何进程，未改共享工具链或其它项目的模拟器配置。
> **§21 的"没有 CIA"结论已被 §22 推翻**：现在包里同时提供 `.3dsx` 与 `.cia`。

---

## §22 CIA 打包（2026-11-08 16:40）

用户问「能帮我打包成 cia 吗」。**已完成并验证**：`smg3ds/real-hardware/cia/SMG-3DS.cia`（6,547,392 B，SHA-256 `483ab56656297e25d43e764ba5290a9307daefd2f8664433149fa629c336d8b7`）。

### 工具获取（网络通道）
本机没有 makerom/bannertool/ctrtool。用**已验证的 GitHub API octet-stream 通道**（`api.github.com/repos/OWNER/REPO/releases/assets/<id>` + `Accept: application/octet-stream`，绕过 `github.com/.../releases/download` 的 502）拿到：
- `3DSGuy/Project_CTR` release `makerom-v0.19.0` → `makerom.exe`（asset 342178994）
- `3DSGuy/Project_CTR` release `ctrtool-v1.2.1` → `ctrtool.exe`（asset 216390444）
- RSF 字段来源：3dbrew Makerom 页 + gist `jakcron/9f9f02ffd94d98a72632`（完整 sample1.rsf）+ `Project_CTR` 源码 `makerom/src/rsf_settings.c` 交叉核对字段名。
- 全部落在 `smg3ds/tools-cia/`，可直接复用，不装系统。

### 决定 RSF 的源码事实（新挖出）
- `Main.cpp`：`DataRoot = "sdmc:/3ds/SMG-3DS/game"`；`main()` 调 `osSetSpeedupEnable(true)`（走 `ptm:sysm` 的 ConfigureNew3DSCPU）。
- `DiscImage.cpp`：`FSUSER_OpenFileDirectly(ARCHIVE_SDMC, ..., "/3ds/SMG-3DS/game.{rvz,wbfs,iso}")` —— **SD 卡绝对路径硬编码**，不依赖 3dsx 所在目录，所以做成 CIA 后照样能读盘。
- `GxFifo.cpp:247` / `WiiAudio.cpp:95`：`APT_SetAppCpuTimeLimit(80)` + `threadCreate(..., 1, true)` 把渲染线程绑**核心 2**。
- 结论：RSF 的 `AccessControlInfo`（**不是** SystemControlInfo）必须给 `CpuSpeed: 804MHz`、`EnableL2Cache: true`、`CanAccessCore2: true`、`SystemModeExt: 124MB`、`DirectSdmc` + `DirectSdmcWrite`、VRAM/DSP 内存映射、`ptm:sysm`/`dsp::DSP`/`y2r:u`/`qtm:u` 服务。
- 3dsx 产物**无 RomFS**（`3dsxtool` 命令没带 `--romfs`），CIA 里 `FormType: Executable (without RomFS)`，省掉一整类坑。

### 打包与踩坑
```
cd smg3ds/tools-cia
./makerom.exe -f cia -o SMG-3DS.cia -target t -rsf smg3ds.rsf \
  -elf "../build-3ds/mario_probe.elf" -icon "../build-3ds/SMG-3DS.smdh" -v
```
- `Dependency: {}` **不被 makerom 接受**（`[RSF ERROR] 'Dependency' requires a value`）→ 整段省略。理由：列出不存在的模块会让应用卡在 logo。
- `-icon` 可直接吃 smdhtool 产出的 `.smdh`（14016 B），无需转 icon.bin。
- `-target t` = test/false keys + prod certs，专为 CFW 自制 CIA；不要用 `-target p`。
- `EnableCrypt: false` / `EnableCompress: false`，NCCH 不加密、ExeFS .code 不压缩，便于模拟器加载与 ctrtool 校验。
- 缺 `bannertool` 的 Windows 构建（仓库无 release、devkitPro 3dstools 里也没有）→ **CIA 无 banner**（ExeFS 只有 `.code` 和 `icon`）。HOME 菜单启动动画为默认，不影响运行，已在交付说明标注。

### 验证结果
- `ctrtool -p/ -y` 完整解析：证书链、Ticket、TMD、NCCH、ExeFS、Exheader 合法；**Content / ExeFS / Exheader / Logo 哈希全 GOOD**；Ticket / TMD / AccessDescriptor **签名 FAIL 是预期**（CFW 签名绕过，原版系统装不了）。
- TitleID `000400000A5D3300`（UniqueId 0xA5D33）、ProductCode `CTR-H-SMGS`、Program ID 一致；Content hash `6EB830B7...70ADF` 与 TMD 一致。
- exheader 逐项核对：804 MHz / L2 YES / Core2 YES / 124MB / `Direct SDMC` + `Direct SDMC (Write Only)` / 32 services / stack 0x40000 / text 0x579C58 / bss 0x1E08EC。
- **功能验证**：把 CIA 里的 NCCH 导出为 `.cxi`（与独立 `makerom -f ncch` 输出**逐字节一致**，sha256 同为 `6eb830b7...`），在便携 Azahar 2126.2 里直接加载：
  `The disc: WBFS, game RMGE01` → 进《超级马力欧 银河》标题画面，状态栏 `速度 100%/100%`、`应用: 30 帧`；gx perf 持续到 t=102 s 无崩溃；窗口标题变 `Azahar 2126.2 | SMG-3DS`（SMDH 生效）。截图 `smg3ds/window_cia.png`。
- 日志里 `ConfigureNew3DSCPU: port='ptm:sysm'` 报 unimplemented 是 **Azahar 未实现该服务**，不是 CIA 错误；exheader 已把 804 MHz 写死，真机由 Luma 处理。
- `Failed to open .../title/0004000e/.../00000000.app` 是模拟器在找 update-data 补丁，无更新数据属正常。

### 交付整合
- `real-hardware/cia/`：`SMG-3DS.cia`、`smg3ds.rsf`、`README-CIA.txt`（适用范围、安装、权限表、已验证/未验证、复现命令）。
- `real-hardware/README.txt` 已改：§1 不再说"没有 CIA"，新增 §8；`SMG-3DS-hardware.zip` 重打为 9,573,875 B，10 项、CRC OK。
- 工具与中间产物留在 `smg3ds/tools-cia/`（makerom.exe、ctrtool/、smg3ds.rsf、SMG-3DS.cxi、exheader.bin、exefs.bin、sample1.rsf、project_ctr.tar.gz）。

### 重要限制（必须转告用户）
1. **仅 Luma3DS 破解机可装**（测试签名），FBI/GodMode9 安装到 SD；原版系统不行。
2. **CIA 不自带资源**：装完仍需 `SD:/3ds/SMG-3DS/game.wbfs`、`settings.ini`、`SD:/3ds/dspfirm.cdc`。
3. **CIA 基于 gpu-overlap 优化版 ELF**（`build-3ds/mario_probe.elf`），不是官方原版；真机 PICA200 未验证。回滚用 3dsx 目录里的官方 v0.1.0 原版（HBL 启动，共用同一份 SD 卡资源）。若要**原版 CIA**，需先用 `smg3ds/src/` 编出原版 ELF 再跑同一条 makerom 命令。
4. 无 banner；真机安装动作本身（写 NAND / 签名链）**未验证**，验证的是等价 CXI 直接加载。
5. 真机老问题照旧：约 14 fps、天空/mip/水面异常、HOME 关闭可能挂起。

### 边界
全程只在 `smg3ds/` 内新建/修改文件；工具下载走只读 HTTP；模拟器用 `stop-portable.py` **按路径精确停止**（PID 35440），**没有再用 `taskkill /F /IM azahar.exe`**；便携实例已切回 `stock` 档、无残留进程；未碰共享 `C:\devkitPro` 与另一项目的配置/进程。任务 #11/#12/#13 完成，#8 仍为唯一剩余项。

---

## §23 把包做成"自带资源、拷一次就能用"（2026-11-08 16:50）

用户追问「这个不自带资源怎么用呢」。**上一轮措辞有歧义，已改正并彻底解决。**

### 概念澄清
程序用 `FSUSER_OpenFileDirectly(ARCHIVE_SDMC, ..., "/3ds/SMG-3DS/game.wbfs")` 按
**硬编码 SD 卡绝对路径**流式读盘；这是移植本身的设计，官方 3dsx 也一样。
所以 CIA 装到主菜单后读的是**同一个 SD 卡目录**，"资源不在二进制里"不等于"要另外找文件"。
`SD:/3ds/SMG-3DS/` 在，两种启动方式都能用；删了就都跑不了。

### 本轮实际改动
1. **把镜像复制进包**：运行已有的 `prepare-disc.py`，把美版 WBFS
   （3,508,535,296 B，校验 WBFS 头 / RMGE01 / FAT32 可放）复制到
   `real-hardware/3ds/SMG-3DS/game.wbfs`。`real-hardware/` 目录现在**真正自带全部资源**。
2. **新增 `real-hardware/install-to-sd.py`** 一键拷卡：
   - `--list` 列出盘符/类型/剩余空间；`<盘符> --dry-run` 预览；`<盘符>` 实际执行。
   - 把 `3ds/` 合并到 SD 卡根（含空的 `nand/`）、CIA 放到 `SD:/cia/`，校验 4 个关键文件大小。
   - 安全约束：拒绝写 `C:\`、检查剩余空间 ≥4 GiB、**合并式复制不删除目标上任何其它文件**。
   - 实测 `--list` 与 `D: --dry-run` 通过，`py_compile` OK。
3. **新增 `smg3ds/pack-hardware.py`**：`python pack-hardware.py` 出轻量 zip（**排除 game.wbfs**）、
   `--full` 出完整 zip（ZIP_STORED + allowZip64）。避免"目录里加了镜像后轻量 zip 变 3.3 GB"。
4. **文档改写**：`real-hardware/README.txt` 开头不再说"不含镜像"；§1 新增「关于资源」解释与
   三个交付形态；§3 改为「方式 A 一键脚本 / 方式 B 手动」并明确镜像已带；§8 改成"装完别删目录"。
   `cia/README-CIA.txt` §1/§2 同步改成"资源已备好在 ../3ds/，用 ../install-to-sd.py"。

### 三个交付形态（任选其一）
| 形态 | 大小 | 说明 |
| --- | --- | --- |
| `smg3ds/real-hardware/` | 3.3 GiB | 完整目录，已含镜像，直接拷，最快 |
| `smg3ds/SMG-3DS-hardware-FULL.zip` | 3,528,459,262 B (3.286 GiB) | 完整单文件，12 项，CRC OK |
| `smg3ds/SMG-3DS-hardware.zip` | 9,577,584 B | 轻量归档，11 项，**不含镜像**，解压后跑 `prepare-disc.py` 补齐 |

两个 zip 均已用 `pack-hardware.py` 重打并 `testzip()` 校验；README / install-to-sd.py 都是最新版。

### 最短使用路径
```
cd smg3ds/real-hardware
python install-to-sd.py --list
python install-to-sd.py E:            # E: = SD 卡盘符
# 开机 → FBI/GodMode9 安装 SD:\cia\SMG-3DS.cia（需 Luma3DS）→ HOME 菜单启动
# 或不用 CIA：Homebrew Launcher 启动 3dsx 原版
```

### 边界
本轮只在 `smg3ds/` 内复制/新建文件，只读 D 盘镜像；**没有启动或终止任何进程**，
未改模拟器配置，未碰 `C:\devkitPro` 或另一个任务。C 盘剩余 248 GiB。
#8（EFB copy 削减）仍是唯一剩余项。

---

## §24 实机「装了 CIA 但 HOME 菜单没图标」排查与 v2（2026-11-08 16:58）

用户实机反馈：装了 CIA，3DS 主页没出现应用图标。

### 本地核查结论：CIA 本身没问题
- **`azahar.exe -i <cia>` 是官方支持的命令行安装**（pocketjs 3DS host 文档里见过）——
  用它在独立便携实例走完整 `Service.AM::InstallCIA` 流程：
  `Installed ... successfully`，SD 卡生成
  `Nintendo 3DS/<id0>/<id1>/title/00040000/<tid>/content/{00000000.tmd, *.app}`（6.3 MB），
  NAND `dbs/ticket.db/` 写入 `.tik`。**这条命令以后可用于验证任何 CIA 的可安装性。**
- `ctrtool -y`：Content / ExeFS / Exheader / Logo / Section 哈希全 GOOD；
  Ticket / TMD / AccessDescriptor 签名 FAIL 是 `-target t` 自制 CIA 的预期（靠 Luma sig patch）。
- **SMDH 排除了"图标坏"**：两处 SMDH（NCCH ExeFS icon + CIA meta）都带 `SMG-3DS`
  标题，`flags=0x141` **含 0x0001 Visibility Flag（3dbrew 明确写"Required for visibility on the Home Menu"）**，
  图标像素 3095/5760 非零。TMD titleType=0x40、ContentCount=1、Encrypted NO 均正常。
- `3dbrew/SMDH` 关键字段：flags @0x2028，region lockout @0x2018，region free=0x7fffffff，
  `0x0080`=usage recorded in HOME Menu icon cache，`0x0400`=New3DS exclusive（会在老机报错）。
- 结论：问题更可能在**真机侧**（安装是否真成功、HOME Menu 图标库未刷新、SysNAND/EmuNAND、
  Luma 签名补丁、或非常规 UniqueId 被过滤），而不是包结构。

### 找到的可疑点
1. **v1 UniqueId `0xA5D33` 落在非常规区间**。自制 CIA 普遍用 `0xFF000–0xFFFFF`
   （makerom 官方样例就是 `0xff3ff`；GBAtemp 教程用 `0xFFFFF`；pocketjs 用
   `0xFF000 | hash & 0xFFF` 且明确说该区间"no retail or system title uses"）。
   某些系统版本可能把非常规区间的 title 当成非应用类而不在 HOME Menu 列出。
2. v1 缺 ExeFS logo（`-exefslogo`）。
3. SMDH 缺 `0x0080`（usage recorded）；region 是 `0xFFFFFFFF` 而非标准 `0x7FFFFFFF`。
4. 注：pocketjs 文档明确写 **"No banner is required"**，故判 banner 不是图标不显示的主因；
   但 v1/v2 仍无 banner，作为残余风险记录在排障文档里。

### v2 加固版（已交付）
`smg3ds/real-hardware/cia/SMG-3DS.cia`，6,547,392 B，
SHA-256 `e2cb8020b93f527eaabf5f18b7e971d4a296f56e9d69403c61a8a3b38cf5422b`。

| 项 | v1 | v2 |
| --- | --- | --- |
| TitleID | `000400000A5D3300` | **`000400000FF3FF00`** (UniqueId 0xff3ff) |
| ExeFS | .code + icon | .code + icon + **logo** |
| SMDH flags | 0x141 | 0x1C1（补 0x0080，去掉 0x0400 风险） |
| Region | 0xFFFFFFFF | 0x7FFFFFFF |
| 游戏本体 / exheader 权限 | — | **完全不变**（804MHz/L2/Core2/124MB/DirectSdmc） |

v2 已 `azahar -i` 安装成功、ctrtool 哈希全 GOOD。**TitleID 变了所以不会覆盖 v1**：
装 v2 前必须先用 FBI 删除旧的 `000400000A5D3300`，装完重启。
v1 备份在 `smg3ds/tools-cia/SMG-3DS-v1-a5d33.cia`（SHA-256 `483ab566…`），
旧 RSF 备份 `smg3ds-v1.rsf`；加固后的 SMDH 在 `cia/SMG-3DS.smdh`。

### 新增交付
- `real-hardware/cia/TROUBLESHOOTING-ICON.txt`：四步排障 ——
  ①FBI Title List / GodMode9 确认是否真装上（含错误码与 SHA-256 核对）
  ②重启、系统设置刷新图标库、SysNAND vs EmuNAND
  ③换装 v2（先卸载旧 TitleID）
  ④仍不行需要提供：FBI 结果/错误码、Title List 内容、Luma 版本、NAND 类型、机型、系统版本。
  另给"暂时绕过 CIA 用 HBL 启动 3dsx 原版"的退路。
- 主 README §8、`cia/README-CIA.txt` 头部均已更新为 v2 TitleID/SHA 并指向排障文档。
- `pack-hardware.py` 重打两个 zip：轻量 9,582,408 B / 13 项、完整 3,528,480,155 B / 14 项，CRC OK。

### 仍未确认（等用户回话）
真机上 v1 到底装成功没有、FBI 显示什么、Luma 版本、SysNAND/EmuNAND、机型。
**没有这些信息无法在 PC 侧进一步定位**；v2 是覆盖面最广的一次性修复尝试。

### 边界
只在 `smg3ds/` 内复制/新建文件；`azahar -i` 写入的是本项目独立便携实例的
`user/nand` / `user/sdmc`，未污染主实例或另一个任务；`-i` 是短命进程，无残留；
未用全局 taskkill。

### 补充（17:01）一页纸速查卡
用户追问「这个 CIA 怎么使用」，新增 `real-hardware/START-HERE.txt`：把
「PC 拷 SD 卡（install-to-sd.py 或手动两步）→ FBI 安装 → 若装过 v1 先删
`000400000A5D3300` → 关机重启 → 点图标 → 标题按 A+R → 按键表 → 别删
`3ds/SMG-3DS/`」收成一张可直接照做的卡片，避免用户在长文档里翻。
主 README 结构树加了该文件；两个 zip 用 `pack-hardware.py` 重打
（轻量 9,584,409 B / 14 项，完整 3,528,483,453 B / 15 项，CRC OK，均含速查卡）。

---

## §25 实机「打开 CIA 直接崩溃重启」→ 换回官方原版 CIA（17:34）

用户实机：装好 CIA、打开游戏直接崩溃重启。

### 首要嫌疑与判断
之前所有 CIA 都基于 `src-gpu-overlap`（**gpu-overlap 补丁**）。作者文档明确写该补丁
只在 Azahar 验证、**从未上过 PICA200 真机**，它改了 `C3D_FrameSplit` / `gxCmdQueueRun`
时序，真机极可能触发 GPU 异常导致系统重启。而官方 v0.1.0 3dsx 是作者验证过
"starts and plays, but slowly (about 14 fps)" 的。故决定编一个**官方原版 ELF 的 CIA**。

### 编译原版 ELF 的三个坑（重要，接手必读）
1. **TMP 问题**：`cmake --build` / ninja 调 devkitARM 报
   `Cannot create temporary file in C:\Windows\ : Permission denied`。
   Bash 里 `export TMP=...` 无效（Git Bash 路径转换），PowerShell 里 `cmake`
   是 MSYS2 版会把 `C:\...` 当相对路径。**有效解法**：用 Windows 原生 Python
   `subprocess.run([shutil.which('ninja'), '-C','build-3ds','-j','4'], cwd=root, env=env)`，
   其中 `env['TMP']=env['TEMP']=env['TMPDIR']=root/tmp`。已验证 rc=0。
2. **原版源码自身也有 GCC 15 链接 bug**：`__ctru_heap_size` 的 `extern "C"` 写在匿名
   namespace 内被修饰 → `undefined reference to smg::(anonymous namespace)::__ctru_heap_size`。
   之前只修了优化版，原版同样要修（把声明提到全局作用域）。这是**纯编译修复，不改游戏逻辑**。
3. 验证方式：不要用 `gxCmdQueueRun/Stop/Wait` 判断补丁（那是 citro3d 自带符号，
   两个 ELF 都有）；**用 ELF sha256 对比**：
   `mario_probe.gpu-overlap.elf = 2185c691…`、`mario_probe.stock.elf = 084d3db9…`。
   源码 diff 确认原版构建副本只比 `src/source/compat/GxRender.cpp` 多 8 行（全局声明 + 删行）。

### 交付（已部署）
- **`real-hardware/cia/SMG-3DS.cia` 主 CIA 换成官方原版**，
  SHA-256 `48c45d9adfb91cd9f27477e4c0a5d1da7622e883688191b5969a52c6f972f2c7`，
  TitleID 仍 `000400000FF3FF00`，**TitleVersion `0.0.1`**（`-ver 1`；
  注意 `-minor 1` 单独不生效，`-major 1` 也不生效，只有 `-ver` 生效）。
  同 ID + 更高版本 → **FBI 直接覆盖安装，无需卸载**。
- 优化版改名 `real-hardware/cia/SMG-3DS-gpu-overlap.cia` 保留供对照，标注"真机未验证，别装"。
- 中间产物在 `tools-cia/`：`mario_probe.stock.elf`、`mario_probe.gpu-overlap.elf`、
  `GxRender.gpu-overlap.cpp`、`SMG-3DS-stock.cia`。
- **工作区一致性已恢复**：把 `GxRender.gpu-overlap.cpp` 拷回 `src-gpu-overlap/` 并重新
  ninja 构建（rc=0），`build-3ds/mario_probe.elf` 现在又是优化版；源码 diff 回到 38 行。

### 新增 `cia/TROUBLESHOOTING-CRASH.txt`
- **一分钟决定性实验**：用 HBL 启动 `SD:/3ds/SMG-3DS/SMG-3DS.3dsx` 官方原版。
  能进标题 → 问题在 CIA（补丁/exheader）；一样崩 → 与 CIA 无关（环境）。
- 其它按序：`3ds/SMG-3DS/` 资源是否齐全；**`dspfirm.cdc` 是别台机器模拟器的 dump，
  不是用户这台 3DS 导出的**，建议临时换成 105 B 占位文本做对照（占位只是没声音、
  不会崩），再用 DSP1 从本机导出真固件；exheader 的
  `SpecialMemoryArrange:true + 124MB` 可能冲突（若 3dsx 正常可出保守版）。
- **请用户提供 `SD:/luma/dumps/` 里的 ARM11 exception dump**（异常类型/PC/LR 能定位模块），
  以及机型、系统版本、Luma 版本、装的是哪个 CIA、崩溃表现、3dsx 实验结果。
- 退路：直接用 3dsx 原版走 HBL，功能一样、无 CIA 变量。

### 文档与包
`START-HERE.txt`、`README.txt`（结构树 / §8 / 排障指引）、`cia/README-CIA.txt`（头部
SHA / 版本沿革 / 换原版原因）全部更新；两个 zip 重打：
轻量 12,734,230 B / 16 项，完整 3,535,038,103 B / 17 项，CRC OK。

### 边界
只在 `smg3ds/` 内编译/写文件，未启动或终止任何进程，未碰共享 `C:\devkitPro`
（只读取）与另一任务；`tmp/` 为本次编译临时目录。任务 #8 仍是唯一剩余项。

---

## §26 3dsx 官方原版也崩 → 排除 CIA 分支、DSP 固件复位（18:20）

用户回话：「实验依旧崩溃」「检查文件齐全」。**这是本轮最有价值的信息**。

### 结论：CIA 分支整体出局
`real-hardware/3ds/SMG-3DS/SMG-3DS.3dsx` 是作者发布的官方 v0.1.0 原版
（6,704,396 B，SHA-256 `aebfc64e56421e8d6be2770ef3becff8ba136be3a7db0647d9f99bd2e7a09297`，
与 `SMG-3DS-0.1.0/` 逐字节一致）。作者 README 写明它在 New 3DS 上
"starts and plays, but slowly (about 14 fps)"。官方原版也崩 + 文件齐全 →
**CIA、gpu-overlap 补丁、exheader 权限、打包方式全部不是根因**，问题在真机环境。
以后不要在换 CIA 版本这条线上继续花时间。

### 已复位：我们引入的唯一偏差 `dspfirm.cdc`
- 之前把官方 Release 的 105 B 占位文本换成了 `D:\AzaharRun\...\dspfirm.cdc`
  （49,756 B）。本地校验它**是合法 DSP1 固件**，不是坏文件：
  `DSP1` magic @0x100、magic 后 4 字节声明大小 49756（= 文件大小）、
  firmware base = 0、section header 在 base+0x120 起结构合理、SHA-256 `8e213f3e…`。
- 但它来自别台机器/模拟器，**DSP 固件随区域/系统版本变化**（DSP1 从不同区域的
  HOME Menu title 提取）。GBAtemp 上「homebrew 卡在声音初始化」是常见故障；
  项目 README 明确真机上必须用**本机 DSP1 导出的** dump，占位文本只是没声音、不崩。
- 处置：`real-hardware/3ds/dspfirm.cdc` **改回官方 105 B 占位文本**；
  合法 dump 移到 `real-hardware/optional/dspfirm.cdc.from-other-console` 留档。
  现在 `real-hardware/3ds/` 与官方 Release 的 sdmc 结构**完全一致**
  （`diff -rq` 只多 `game.wbfs` 和空的 `nand/`），是最干净的对照配置。

### 剩余嫌疑（按优先级，写在 CRASH 文档开头）
0. **机型**：项目 README 原话 "The original 3DS and 2DS can't run it."。
   老机 268MHz 双核 / 64MB 可用 / 无 Core2，程序却要 `C3D_Init(1MB)`、
   假设 804MHz、把渲染线程绑核心 2 → 老机上崩溃是预期。**必须先确认机型**。
1. `dspfirm.cdc`：重拷占位、或直接删掉做对照；要声音用本机 DSP1 导出。
2. SD 卡必须 FAT32；`game.wbfs` 3,508,535,296 B / WBFS / RMGE01 已校验；
   真机 WBFS 实时 AES 解密，坏块或传输损坏会 abort。
3. Luma / 系统版本；CIA 能装说明 sig patch 大致可用，但 3dsx 走 HBL 是另一路径。
4. **★ `SD:/luma/dumps/` 的 ARM11 exception dump** —— 异常类型 / PC / LR 能直接
   定位崩在 DSP、GPU 还是读盘。没有它 PC 侧只能继续猜。

### 交付更新
`cia/TROUBLESHOOTING-CRASH.txt` 开头新增【最新结论】+ 排查优先级 + 需用户回答的
5 项；`README.txt`（4 处）、`cia/README-CIA.txt`（2 处）、`START-HERE.txt`
的 dspfirm 描述全部改成官方占位文本口径，旧描述已清除。
两个 zip 重打：轻量 12,736,134 B / 17 项，完整 3,535,042,048 B / 18 项，CRC OK。

### 需要用户回答（阻塞点）
机型（New 3DS/2DS XL 还是老款）、崩溃表现（Luma 异常屏/直接黑屏重启/先出画面）、
`SD:/luma/dumps/` 是否有异常日志、Luma 与系统版本、复位 dspfirm 后有无变化。
**没有这些信息无法继续定位**；不要再猜 CIA 版本。

### 边界
只在 `smg3ds/` 内复制/改文件，只读 D 盘 dump 与盘镜像头部；未启动或终止任何进程，
未碰共享工具链与另一任务。

---

## §27 找到「看不到崩溃原因」的机制 + 诊断版 3dsx（20:42）

用户新信息：**New 3DS LL**（排除老机）、`luma/dumps/` 没有文件、
下屏出现 `SMG boot bring-up` 后上屏没出来就崩、删掉 dspfirm 依旧。

### 源码层面的决定性发现（解释全部现象）
`source/probe/MarioProbe.cpp`（**游戏本体 `mario_probe` 的 main**，不是 892KB 的
场景查看器 `Main.cpp`）：
```cpp
consoleInit(GFX_BOTTOM, nullptr);      // stdout/stderr -> 下屏 console
consoleDebugInit(debugDevice_SVC);     // ★ 又把 stderr 抢到 SVC（真机不可见）
std::printf("SMG boot bring-up\n");    // stdout -> 下屏，所以用户只看得到这一行
```
- `DiscImage.cpp` 的 `stop()` 和 `MarioProbe.cpp` 的 `smgFault()` 都把原因
  **`fprintf` 到 stderr**；`debugDevice_SVC` 在真机上无显示 → 原因永远看不到。
- `smgFault()` 与 `__wrap_abort()` 结尾都是 **`svcExitProcess()`** →
  **应用主动退出，不是硬件重启**，用户看到的"崩溃重启"其实是回到 HOME/HBL。
- `smgCatchFaults()` 用 `threadOnException(smgFault, ...)` 注册了自己的 CPU
  异常处理器，**优先于 Luma 接管** → `SD:/luma/dumps/` 永远为空。
  **这解释了用户找不到 dump：不是 Luma 没开，是程序自己把异常吃了。**
- `smgGameMain()` 是生成的 `build-3ds/petari/Game/System/GameSystem.cpp:56`
  （`prepare-petari.py:1747` 把原版 `main` 改名），内部做 DVDInit / 堆初始化 /
  `GameSystem::init()` / `frameLoop()`。

### 诊断版（已交付）
`real-hardware/optional/SMG-3DS-diag.3dsx`，6.3 MB，
SHA-256 `a34b998e70b5d18efd65ee2c1b89afa7e8852a6006cf1e4ae8610fdecf83140a`。
基于**官方 v0.1.0 原版渲染器**（`src/source/compat/GxRender.cpp` + GCC 15 链接修复），
只改 `MarioProbe.cpp` 三处：
1. main 里 `consoleDebugInit` 之后 `freopen("sdmc:/3ds/SMG-3DS/boot-log.txt","w",stderr)`
   + `setvbuf(_IONBF)`；失败则恢复 `consoleDebugInit(debugDevice_SVC)`。
2. `__wrap_abort()` / `smgFault()` 在 `svcExitProcess()` 前 `fflush(stderr)`。
3. `smgGameMain()` 前后各写一行 stderr 打点。
→ 所有原本看不见的 stderr（memory、读盘错误、CPU fault 类型/PC/LR、callers）
  都会无缓冲落到 SD 卡，崩完仍在。

### 最值得看的一行
`mario-probe: application memory X KiB, Y free` —— Azahar 是 126976 KiB (124MB)。
**真机 HBL 下如果只有 ~65536 KiB (64MB)，就是 Homebrew Launcher 没给 New3DS
大内存模式**，程序加载资源会 OOM/abort —— 这是当前最可能的根因，
也解释了为什么 CIA（能申请 124MB）和 3dsx 都可能出问题、以及为什么
`luma/dumps/` 为空（是 abort 不是 fault）。诊断日志会直接给出这个数字。

### 交付与文档
- `cia/HOWTO-DIAG.txt`：机制说明、三步用法（覆盖 `SD:/3ds/SMG-3DS/SMG-3DS.3dsx`
  → 启动 → 取 `SD:/3ds/SMG-3DS/boot-log.txt`）、日志结局判读表 a–d、
  顺手核对 `game.wbfs` 路径/大小 3,508,535,296 B 与 FAT32。
- `README.txt`（结构树 / 排障指引）、`START-HERE.txt` 已指向诊断版；
  两个 zip 重打：轻量 15,906,651 B / 19 项，完整 3,541,638,824 B / 20 项，CRC OK。
- 备份：`tools-cia/MarioProbe.orig.cpp`、`tools-cia/GxRender.gpu-overlap.cpp`。
  编译后**已恢复两个源文件并重新 ninja 构建**，
  `build-3ds/mario_probe.elf` sha256 回到优化版基准 `2185c691…`，工作区一致。

### 下一步（阻塞在用户）
等 `boot-log.txt` 内容。据此可直接判断：内存不足 / 读盘失败（含具体原因）/
CPU fault（含 PC、LR，可反查符号）/ 更底层 GPU fault。
不要再猜 CIA 版本或 DSP 固件 —— 两者都已被本轮证据排除。

### 边界
只在 `smg3ds/` 内编译/写文件；未启动或终止任何进程，未碰共享工具链与另一任务。

### 补充（20:49）详细步骤 + 一键脚本
用户要「怎么操作，详细步骤」。新增：
- `real-hardware/install-diag.py`：`python install-diag.py <盘符>` 一键把
  `optional/SMG-3DS-diag.3dsx` 覆盖到 `SD:/3ds/SMG-3DS/SMG-3DS.3dsx`，
  自动备份为 `.stock`、删除旧 `boot-log.txt`、SHA-256 校验；
  `--restore` 还原、`--dry-run` 预览、`--list` 列盘符；拒绝写 C:。
  脚本用 `__file__` 定位资源，**不需要先 cd**，cmd/任意终端都能跑。
  已用 `D:\_smg_diag_selftest` 假 SD 目录完整自测（预览/安装/恢复/校验 OK），
  测试目录已删除。
- `real-hardware/STEP-BY-STEP-DIAG.txt`：做法 A 脚本 / 做法 B 纯手动
  （含「勾选文件扩展名，别写成 .3dsx.3dsx」的坑）、3DS 上走 HBL 且等 1–3 分钟
  别按 HOME、取 `boot-log.txt`、恢复原版、日志判读、常见问题。
  诊断版精确大小 **6,590,896 B**（官方原版 6,704,396 B），可用于确认是否覆盖成功。
- README 结构树 / §8、START-HERE、cia/HOWTO-DIAG 已指向新文档；
  两个 zip 重打：轻量 15,912,697 B / 21 项，完整 3,541,651,854 B / 22 项，CRC OK。

### 补充（20:56）路径全部写成绝对路径
用户指出回答里用了 `...\smg3ds\real-hardware\optional\` 这种省略写法。新增
`real-hardware/PATHS.txt`（30 条完整绝对路径：本机脚本/说明/3ds/optional/cia/zip/
源码目录、SD 卡目标路径、6 条完整命令），并在 README、START-HERE、
STEP-BY-STEP-DIAG、cia/HOWTO-DIAG、cia/README-CIA 开头写明
「相对路径的基准 = `C:\Users\WXP\WorkBuddy\2026-11-08-01-41-44\smg3ds\real-hardware\`」。
STEP-BY-STEP 里两处包内引用也换成绝对路径。
注意：Bash 里用 Python `-c` 内联 Windows 路径会被 Git Bash 转成混合斜杠
（`C:/.../real-hardware\...`），已用独立脚本 `fix_paths.py` 修回并删除该临时脚本；
以后改文档路径优先用 Edit/Write 工具，别走 shell 内联。
两个 zip 再重打：轻量 15,914,522 B / 22 项，完整 3,541,657,799 B / 23 项，CRC OK。

---

## §28 根因定位并修复：系统语言 → BMG ruby tag → abort（21:12）

用户交回 `F:\3DS\SMG-3DS\boot-log.txt`（SD 卡盘符是 **F:**），并补充「我是日版机器，但是汉化了」
→ 系统语言是中文，不是我先前猜的日语；**但结论不变**：只要不是美版验证过的
En/Fr/Es，就会走未验证的 BMG 路径。

### 日志逐行结论（前面所有猜测全部排除）
```
DIAG: stderr mirrored / application memory 126976 KiB, 0 free  → 124MB 正常，排除 OOM
DIAG: entering smgGameMain / The disc: WBFS, game RMGE01        → 盘读到了，排除读盘失败
NW4R LYT / ARInit / RVL_SDK GX / FIFO drawn on core 2           → 初始化正常、核心 2 可用
A BMG message file has a tag kind the port has no layout for
  (group 255, type 2)                                          → ★ 失败点
mario-probe: callers on the stack: ...                         → __wrap_abort()，程序主动退出
```
`callers on the stack` 来自 `__wrap_abort()`，说明是 **abort() → svcExitProcess()**，
不是 CPU fault / GPU 挂死 / 硬件重启；这也就是 `luma/dumps/` 为空的原因。
addr2line（官方原版 ELF）指向 `MessageData::MessageData` /
`GameSystemObjHolder::initDisplay()` / `JKRArchive::getResource`。

### 根因链（源码证据）
1. `source/compat/SystemConfig.cpp::SCGetLanguage()` 用 `CFGU_GetSystemLanguage()`
   把 3DS 系统语言映射成 Wii 语言（JP→0, 简中→SC_LANG_SIMP_CHINESE, 繁中→…,
   默认 EN）。日版+汉化机 → 非英语。
2. 游戏据此加载非英语 BMG 文本，其中含 **ruby（振り仮名）tag**。
3. `docs/PORTING.md`「Messages (BMG)」原文：**"the system group's ruby …
   aren't on the US disc"**；`resource_audit` 只验证美版盘 3 个 BMG / 50 种 tag /
   none refused。`group 255` = system group，`type 2` = ruby。
4. `source/core/Bmg.cpp:65` `planParameters()` 只实现
   `(group==255 && type==0)`（玩家名/颜色 getParam8），type 2 落 else →
   `problem("has a tag kind the port has no layout for (group %u, type %u)")`。
5. `source/compat/NativeResources.cpp::smgNativeBmg()` → `fprintf(stderr,…)` + `abort()`。
**Azahar 从不复现**：模拟器系统语言默认英语，只走作者验证过的美版英语 BMG。

### 已交付修复
- `optional/SMG-3DS-english.3dsx`（6,590,648 B，
  SHA `5c13c3b7796766ef73dae2782136f5bdc37d37b4113eafe114b191fbda6128fa`）：
  `SCGetLanguage()` 强制 `return SC_LANG_ENGLISH;`（`SC_LANG_ENGLISH=1`），
  其余官方 v0.1.0 原版渲染器，并保留诊断版 stderr→boot-log.txt 落盘。
  编译用 `make_english_build.py`（已删），rc=0；备份在
  `tools-cia/SystemConfig.orig.cpp` 等；三个源码已恢复并重新 ninja 构建，
  `build-3ds/mario_probe.elf` sha256 回到优化版基准 `2185c691…`。
- `install-diag.py` 新增 `--english`：一键切换修复版（自动备份 `.stock`、删旧日志、
  SHA 校验），`--restore` 还原；假 SD 目录完整自测通过并清理。
  用户的实际命令：`python "C:\Users\WXP\WorkBuddy\2026-11-08-01-41-44\smg3ds\real-hardware\install-diag.py" F: --english`
- `cia/ROOT-CAUSE.txt`：日志逐行解读、根因链、两个解法、限制；
  README / START-HERE / STEP-BY-STEP-DIAG / cia/HOWTO-DIAG / PATHS.txt 已指向它，
  PATHS.txt 补了 english 3dsx、ROOT-CAUSE.txt 与 `--english` 完整命令，并注明 F:。
- 两个 zip 重打：轻量 19,086,551 B / 24 项，完整 3,548,256,870 B / 25 项，CRC OK。

### 零成本备选
把 3DS 系统语言改成 English 后用官方原版 3dsx 启动（原理相同）。
但汉化系统切语言不便、会影响其它软件，**主推 `--english` 修复版**。

### 仍未解决 / 风险
- ruby tag 本身**没实现**，只是绕开；中文/日语文本仍不能正确显示（菜单会是英文）。
  真要支持需在 `Bmg.cpp::planParameters()` 补该 tag 的参数布局（文本在奇数字节）并跑
  `resource_audit` 验证。
- **`cia/SMG-3DS.cia` 没有强制英语**，汉化机上装 CIA 大概率仍踩同一个 abort。
  如需 CIA 版修复，用同一套源码改 `SystemConfig.cpp` 后按 §25 的 makerom 命令重打。
- 真机约 14 fps、天空/mip/水面缺陷、HOME 挂起等项目固有老问题照旧。
- 下一步：等用户跑 `--english` 的结果；若仍退出，新版 `boot-log.txt` 会给出下一个原因。

### 边界
只在 `smg3ds/` 内编译/写文件，只读用户 F: 盘的日志；未启动或终止任何进程，
未碰共享工具链与另一任务。


## §29 命令报错（MSYS2 Python 抢占 PATH）与一键批处理（21:30）
**用户报错**：PowerShell 执行 `python "<Windows绝对路径>\install-diag.py" F: --english` 得到
`/opt/devkitpro/msys2/usr/bin/python: can't open file '/c/Windows/system32/C:\Users\...': No such file or directory`。
根因不是文件丢失：`where.exe python` 第一项是 `c:\devkitPro\msys2\usr\bin\python.exe`（MSYS2 版，
按 POSIX 规则把 `C:\...` 当相对路径拼到 cwd 后）。本机同时有 `py -0p` → Python 3.14.7
（pythoncore-3.14-64 / `C:\Users\WXP\AppData\Local\Python\bin\python.exe`），`py -3` 与原生
python.exe 均能正常运行脚本。

**交付**：
- `real-hardware/FIX-ENGLISH.bat` / `RESTORE-STOCK.bat`：纯 ASCII 内容 + CRLF，内部直接定位原生
  `python.exe`（找不到时回退 `py -3`），完全绕开 PATH；默认盘符 `F:`，`%~1` 可覆盖，`%~2` 透传
  `--dry-run`；`SMG_NOPAUSE=1` 可跳过 pause 便于自动化。假 SD 目录完整自测通过。
- 文档所有命令 `python "..."` → `py -3 "..."`（ROOT-CAUSE / STEP-BY-STEP-DIAG / PATHS /
  START-HERE），并写明坑的成因；两个 Python 脚本 docstring/用法提示同步改为 `py -3`。
- **修掉一个真隐患**：`install-diag.py` 原先在 `.stock` 不存在时把「卡上当前文件」备份成 `.stock`。
  用户 F: 卡当前是诊断版（`a34b998e…`，6,590,896 B）且无 `.stock`，直接装修复版会让
  `--restore` 回到诊断版。现改为**始终用包内官方原版**（`aebfc64e…`，6,704,396 B）建立
  `.stock`，并把当前非原版文件另存 `.previous`。自测哈希链：target=`5c13c3b7…`(english) /
  `.previous`=`a34b998e…`(diag) / `.stock`=`aebfc64e…`(stock)，restore 后回到 `aebfc64e…`。
- 真机首份日志归档：`smg3ds/diagnostics/boot-log-20261108-hardware.txt`（753 B，只读复制自 F:）。
- 两个 zip 重打并校验：轻量 19,089,185 B / 26 项、完整 3,548,262,504 B / 27 项，均含两个 bat。

**当前 F: 卡状态（只读核对）**：`3DS/SMG-3DS/` 内 3dsx=诊断版、`boot-log.txt`=753 B、
`game.wbfs`=3,508,535,296 B、`nand/`、`settings.ini`；无 `.stock`、无 `dspfirm.cdc`（用户已删）。
跑 `FIX-ENGLISH.bat` 后会自动生成 `.stock` + `.previous`、删旧日志、写入 english 版。

**下一步**：等用户执行 `FIX-ENGLISH.bat`（或 `py -3 ... F: --english`），在 HBL 启动并回报结果；
若仍退出，把新的 `boot-log.txt` 发来定位下一个未实现点。CIA 版仍未带强制英语修复（§28）。
本轮未启动/终止任何进程，未写用户 SD 卡（仅 dry-run），未碰共享工具链与另一任务。


## §30 真机跑通 + 渲染异常归因 + 帧率显示功能（21:34–21:50）
**用户两张实机照片**：第一张上屏故事书文字 "Every hundred years, a comet …"、下屏 `SMG boot bring-up`
→ **强制英语修复版生效，真机已能进游戏**（§28 的结论被实机确认）。第二张进入星系场景，
HUD（生命 3、星币、星屑）与地面/树木正常，但出现渲染异常。

### 渲染异常：已知缺陷，不是打包/编译引入
现象：Mario 身上白/青色大斜条、顶部竖直白色宽带、天空纯蓝色板块。逐条对上作者文档：
- `docs/HANDOFF.md` "On a real New 2DS XL"：`The sky draws as blue slabs near the camera on long jumps`；
  `Shooting stars' trails became giant streaks. A fix is committed but was never confirmed on a console`。
- `docs/PORTING.md` "On a real 3DS"：Wii 的 JPA 条纹不裁剪直接画，顶点落近平面之后时 PICA200 自己
  裁出的新顶点可抛到几万像素外，PC GPU 容忍、真机画成巨大条纹。CPU guard-band 裁剪
  (`GxVertexPipeline::GuardBand`) 只覆盖透视三角形，`GxDraw.cpp` 的 `perspective` 判定会跳过 2D draw；
  作者原话 "Not yet confirmed on the console; the sky … is the next candidate"。
→ 照片证实该「提交过但未在真机确认」的修复仍未覆盖这些条纹。我们所有 3dsx/CIA 都用官方 v0.1.0
渲染器，只加 5 行 GCC 15 链接修复 / 强制英语 / 下屏文字，**从未改 GPU、TEV 或裁剪逻辑**。
结论与五个 `settings.ini` 对照实验（`dev.gx_mips=1`、`dev.gx_noraw=1`、`dev.gx_inline=1`、
`dev.gx_check=1`、`dev.gx_timing=1`，一次一个、重启生效）写在 `real-hardware/cia/RENDER-ARTIFACTS.txt`。
真修需真机 GPU 计时 + 快速迭代；无数据改裁剪路径会让真机随机冻结（作者多次记录），故**有意不动渲染器**。

### 帧率显示功能（本轮实现，已编译 + 已验证）
- 产物 `real-hardware/optional/SMG-3DS-fps.3dsx`（6,591,152 B，SHA `337fd25e…`）。
  基于**官方 v0.1.0 渲染器**（不含 gpu-overlap），含强制英语修复 + stderr→boot-log.txt + FPS 显示。
- 实现：挂在 `GxRender.cpp::perfLine()`（由 `gxRenderCopy()` 在帧结束 EFB copy 时每帧调一次）。
  每 ~500 ms 用 `svcGetSystemTick()` 算窗口内 fps / 平均 ms / 最慢帧，一次 `printf("\x1b[4;0H\x1b[K…")`
  到下屏 console 固定行；`setvbuf(stdout, _IONBF)` + `fflush` 保证刷新。**无 SD 卡写、无 GPU 工作、
  每帧仅 2 次时钟读取**，避开了作者「渲染线程写 SD 卡 +150 ms/帧」的坑。
- 开关：`Settings.hpp` 新增 `devShowFps = true`（默认开，不回写 settings.ini），`dev.show_fps=0` 关闭；
  `Kpad.cpp` 加 `smgDevShowFps()` getter，`GxRender.cpp` 用 `static const bool` 首次调用时读取。
  其它版本忽略这个未知键，无害。
- 构建配方 `smg3ds/make_fps_build.py`（可复现，改 6 个文件），原件备份在 `smg3ds/fps-build/backup/`。
- **Azahar 实测**：便携实例加载 FPS 版，下屏固定一行 `FPS  30.0   33.4 ms  max 39.9  #7784`，
  无滚动/乱码，ANSI 定位有效；上屏游戏画面正常、状态栏 `应用: 30 帧`。截图 `smg3ds/window_fps.png`。

### 交付与工作区状态
- 一键：`real-hardware/SHOW-FPS.bat`（默认 F:，纯 ASCII + CRLF），或
  `py -3 "<包>\install-diag.py" F: --fps`；用完 `RESTORE-STOCK.bat`。`install-diag.py` 新增 `--fps`
  分支与 SHA 校验，假 SD 目录预览/安装/恢复全自测通过。
- 文档：README / START-HERE / PATHS / ROOT-CAUSE / settings.ini 注释同步；新增 `cia/RENDER-ARTIFACTS.txt`。
  两个 zip 重打：轻量 23,238,662 B / 29 项、完整 3,554,862,694 B / 30 项，均含新 bat、fps 3dsx 与归因文档。
- **工作区一致性**：编译后从 `fps-build/backup/` 恢复 6 个源码，`ninja` 初次因备份时间戳较旧显示
  `no work to do`（ELF 仍为 FPS 版）→ `os.utime` 强制 touch 后重编，ELF 回到优化版基准
  `2185c69179e50c23`，`GxRender` 差异回到 38 行，FPS 符号在源码中 0 残留。
- **限制**：`cia/SMG-3DS.cia` 仍是官方原版 ELF，**没有**英语修复与 FPS；需要时按 §25 的 makerom
  命令用 FPS 版 ELF 重打。渲染缺陷按上面结论有意未改。
- 边界：验证只启动/停止本项目便携实例（精确脚本停 PID 21428），未用全局 taskkill；未写用户 F: 卡；
  未碰共享 `C:\devkitPro` 与另一任务。


## §31 整屏几何崩坏 + 「为什么模拟器没事」+ 实验裁剪版（21:54–22:10）
**用户第三张真机照片**：整个场景撕裂成蓝/棕大三角 + 网点棋盘花纹，HUD 仍完整。
用户追问「为什么模拟器运行就没这种错误」。

### 为什么模拟器正常（机制结论）
Azahar 把 GX 命令流转成 PC 显卡（OpenGL/Vulkan）绘制：高精度浮点裁剪、保护带范围大、
驱动会丢弃坐标极端的三角形，所以 Wii 那种「不裁剪直接画」的 JPA 条纹在屏外就消失。
真机 PICA200 是定点裁剪器，自己生成的新顶点会溢出到几万像素外还被当成有效三角形画出。
作者原话 "Azahar forgives a lot that a real PICA200 doesn't"。**模拟器看不出这类 bug
恰恰因为它不是 PICA200**；模拟器 A/B 只能验证「改动有没有把游戏弄崩」，不能验证画面修复。

### 只读核对 F: 卡 —— 推翻了上一轮的首要猜测
F: 期间曾拔出（只剩 C:/D:），22:05 左右重新挂载后核对到：
- `settings.ini` = **494 B、2026-10-19 16:38、零 `dev.*` 行** → 用户**没有**试过 §30 建议的
  任何对照开关，网点花纹不是 `dev.gx_mips=1` 造成的，是纯真机缺陷。
- 当前 `SMG-3DS.3dsx` = `5c13c3b7…`（6,590,648 B，**强制英语修复版**，21:09 装的），
  不是 FPS / clipfix 版；另有 `.previous`（诊断版 6,590,896 B）、`.stock`（官方原版）。
- `boot-log.txt` = 268,226 B / 1085 行 / **180 个 gx perf 采样**（英语版 stderr 落盘）。

### ★ 首次拿到真机 GPU 分项（填补 #8 最大信息缺口）
归档 `smg3ds/diagnostics/boot-log-20261108-gameplay.txt`，用 `extract_gx_perf.py` 生成
`smg3ds/baseline/hardware-20261108.csv`（180×17）。全采样平均：

| 指标 | 均值 | 说明 |
| --- | --- | --- |
| fps | 14.77 (min 5.7 / max 29.8) | 印证作者 ~14 fps |
| ms/frame | 74.68 (max 176.7) | 印证作者 ~70 ms |
| **pica_wait_ms** | **51.05** | 作者说的「GPU 占 50–60 ms」实测坐实 |
| gx_stream_ms | 61.48 | 渲染线程 GX 流读取 |
| waiting_gpu_ms | 23.22 | 每逻辑步等 GPU |
| retrace / logic | 2.86 / 2.77 | CPU 侧很轻，确属 GPU-bound |

注意：日志由 stderr 每 ~4 秒写一次 SD 卡（不是每帧），`max 176.7 ms` 尖峰可能是落盘；
按作者经验测试构建在渲染线程每帧写 SD 卡会 +150 ms/帧，此份数据仍需谨慎外推。
即便如此，**#8「没有真机 GPU 计时数据」这个阻塞项现在有数据了**，可按 §19 阶段 2
开始量化 transfer / pass / split 占比。

### 交付
- `real-hardware/RESET-SETTINGS.bat` + `reset-settings.py`：删掉 `settings.ini` 里所有
  `dev.*` 行，键位/指针/速度全保留，原文件备份 `.bak`，支持 `--dry-run`。假 SD 目录自测通过。
  （虽然本次核实配置是干净的，但把它作为以后试开关后的标准回退工具保留。）
- `optional/SMG-3DS-clipfix.3dsx`（6,591,128 B，SHA `d64891a0…`）= FPS 版 +
  `GxDraw.cpp` 去掉 `perspective` 判定，让 **2D / JPA 条纹也走 CPU guard-band 裁剪**。
  只在有顶点落近平面之后时裁，不动 GPU 命令序列；风险相对可控但**真机效果未验证**。
  配方 `smg3ds/make_clipfix_build.py`，`TRY-CLIPFIX.bat` / `install-diag.py --clipfix` 安装。
- **Azahar 验证**：clipfix 版进标题、下屏 `FPS 29.7 33.6 ms max 34.1 #12555`、
  状态栏 `应用: 30 帧`、无 abort（截图 `smg3ds/window_clipfix.png`）。
  注意模拟器画面本来就没有这些缺陷，此验证只说明「没把游戏弄崩」。
- 文档：`cia/RENDER-ARTIFACTS.txt` 新增「最优先：确认不是 dev.* 开关」与
  「为什么模拟器正常、真机不正常（含 A/B 顺序）」；README / START-HERE / PATHS 同步。
  两个 zip 重打：轻量 26,549,008 B / 33 项、完整 3,561,463,035 B / 34 项。

### 下一步（需用户真机 A/B）
1. 先 `SHOW-FPS.bat` 装 FPS 版，同一崩坏场景拍一张 + 记下屏 FPS；
2. 再 `TRY-CLIPFIX.bat` 装实验版，同场景对比蓝板块/条纹/网点是否减少、FPS 是否下降；
3. 变差就 `SHOW-FPS.bat` 装回对照版。两张照片发回即可判断裁剪方向对不对。
   真正的修复仍可能要按作者 TODO 第 4 条把 Sky/Air/Sun display lists 强制走 CPU path。

### 边界
从 `fps-build/backup/` 恢复 **7 个**源码并 `os.utime` 强制重编，ELF 回到优化版基准
`2185c69179e50c23`、GxRender 差异 38 行、GxDraw 与官方一致、FPS/clipfix 符号 0 残留。
精确停本项目 PID 38440（未用全局 taskkill），**只读**用户 F: 卡（未写入），
未碰共享工具链与另一任务。

## §32 实机调试通道（不再拔卡猜）（22:10–22:50）
用户问「现在修改是不是全靠猜？有没有实机调试的办法」。结论：之前确实是盲改→拔卡拷文件→拍照，
一轮十几分钟、信息量只有一帧；已用 devkitPro 自带工具搭出三套真机调试通道，把循环压到几分钟。

### 三套通道与工具
1. **3dslink 网络推送**（不拔 SD 卡）：HBL 按 Y 显示 IP → `deploy-3ds.py --ip <IP> --build debug`，
   内部调用 `C:\devkitPro\tools\bin\3dslink.exe`（0.6.3，确认支持 `-a`/`-s`）。备选 `ftpd`。
2. **3dslink `--server` 实时日志**（不拍照）：debug 构建启动时若经 3dslink 启动，把 stderr
   （gx perf / stops / faults）实时回传 PC；从 SD 卡启动则降级写 `boot-log.txt`（已验证：
   azahar 无 host 时重新生成 64K 日志）。PC 端 `live-log.py --stdin` 格式化+告警+CSV 导出；
   也支持 `--drive F:` / `--ftp <IP>` 轮询。
3. **Rosalina 真机 GDB**（断点/看变量/回溯）：3DS 上 Rosalina（L+Down+Select）→ Debugger →
   Enable debugger → Force-debug next application at launch（端口 4003）→ `GDB-3DS.cmd <IP>`
   （内部 `arm-none-eabi-gdb` + `target remote <IP>:4003`）。

### 关键产物
- `real-hardware/optional/SMG-3DS-debug.3dsx`（SHA `1b7685c1`，= netlog 配方：
  强制英语 + FPS + 3dslink 实时日志）+ `optional/SMG-3DS-debug.elf`（13 MB，含 `.debug_info`/
  `.debug_line`，`perfLine`/`GxVertexPipeline`/`GxDrawState` 等符号可读）——**同一构建，地址对应**。
- `make_debug_build.py`（在 `smg3ds/` 源码树根，与 `make_fps_build.py` 同处）：生成上面配对并
  **自动还原源码树**。
- `real-hardware/DEBUGGING.md` 完整手册；`deploy-3ds.py --list` 列出全部构建哈希。
- 注入点 `source/probe/MarioProbe.cpp`：仅当 `__3dslink_host.s_addr != 0` 才 `link3dsStdioForDebug()`，
  libctru API `link3dsStdioForDebug()`（= `link3dsConnectToHost(false,true)`）确认存在。

### 验证状态
已验证：netlog 降级路径（无 host→boot-log.txt）、编译通过、libctru/`3dslink` 标志与 API 名正确、
debug.elf 含调试符号。**尚未真机联网验证**的是 3dslink 实时回传流与 GDB attach（需真机在 WiFi 上）。

### 下一步
用户按 `DEBUGGING.md` 在真机验证：进崩坏场景用 `WATCH-NETLOG.bat` 看 `gx perf`（pica_wait /
primitives 是否异常）→ 对比 `SHOW-FPS`(对照)/`TRY-CLIPFIX`(实验)/`debug`+GDB(断点看顶点是否被抛飞)。
渲染修复必须真机验证（模拟器用 PC 显卡，PICA200 定点裁剪缺陷不复现）。

### 边界
源码树恢复到 `fps-build/backup/` 基准后，`make_debug_build.py` 还原用了 `copy2`（保留旧 mtime）
导致 ninja 误判「无改动」、`build-3ds` 一度停在 netlog 版；已用 `os.utime` 刷全树 mtime 强制重编，
最终 `build-3ds` ELF 回到 `2185c69179e50c23`、源码 6 文件与备份一致、无残留 azahar 进程。
精确停本项目 PID 37788（`stop-portable.py`，netlog 验证实例），**只读**用户 F: 卡，未用全局 taskkill，
未碰共享工具链与另一任务。两个 zip 重打：轻量 38,824,480 B/41 项、完整（含 3.27 GiB wbfs）/42 项。

### §33 — GitHub 上传（仅我方部分 + fork 上游）

**决策**：不能直接推整个 `smg3ds/`（含 `game.wbfs` 3.27 GiB 任天堂镜像、`*.cia/*.3dsx/*.elf`
含反编译代码、`*.cdc` 任天堂 DSP 固件、上游源码、模拟器实例、截图——均为版权/二进制红线）。
用户拍板「只传我自己那部分 + fork 上游」。

**已完成（本地，未 push）**：在 `smg3ds/` `git init`，写 `.gitignore`（排除上述红线，反向保留
`real-hardware/3ds/SMG-3DS/settings.ini`），生成 `source-changes-vs-upstream.patch`
（`src/`→`src-gpu-overlap/`，184 行 4 文件：gpu-overlap 优化 + Windows/GCC15 构建修复）。
提交 `e001048`（分支 `master`，无 remote），**43 文件**、零红线泄漏。committer 为全局身份
`Codex <codex@local>`，用户若上 GitHub 应先 `git config user.name/email`。

**收录**：7 个 make*/pack/extract/stop 脚本；real-hardware 下 deploy/live-log/reset/install 脚本 +
一键 bat/cmd；DEBUGGING/README/START-HERE/PATHS/cia/* 文档；baseline/*.csv；diagnostics/boot-log-*.txt；
.gitignore；patch。

**push 待办（需用户给目标 + 授权）**：
- 策略 A（配套仓）：本仓库直接推到新建空仓——不含源码，靠 `source-changes-vs-upstream.patch` 叠加；
- 策略 B（fork 整合）：克隆 `cmyksoda/SMG-3DS` 的 fork → `git apply -p1` 应用 patch 到源码 →
  拷入本仓库脚本文档 → 提交推送（**才能直接构建**，推荐）。需 fork 已存在 + 联网 + 凭据。
- 红线再确认：`dspfirm.cdc.from-other-console` 后缀是 `.from-other-console` 非 `.cdc`，已用 `*.cdc.*` 拦截。

**边界**：本次只建本地 git、未上传任何内容、未碰 F: 卡/共享工具链/另一任务。详见 `.workbuddy/memory/2026-11-10.md`。
