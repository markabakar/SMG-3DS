SMG-3DS 实机安装包（New Nintendo 3DS / New 2DS XL）
===================================================

本包由本机已有文件整理而成，只在你自己的机器上使用。
游戏本体版权归 Nintendo 所有；**完整目录与 FULL zip 已含你自己提取的美版盘镜像**
（3.268 GiB），请勿对外分发。轻量 zip 不含镜像，见第三节补齐方法。

本文所有 `cia/`、`optional/`、`3ds/` 等相对路径，基准都是包根目录：
    C:\Users\WXP\WorkBuddy\2026-11-08-01-41-44\smg3ds\real-hardware\
**每个文件的完整绝对路径都列在 `PATHS.txt`**，可直接复制到资源管理器地址栏。


一、这是什么格式
----------------
本包同时提供两种启动方式：

- **`.3dsx`（主用）**：官方 v0.1.0 原版，通过 Homebrew Launcher 启动。
- **`.cia`（可选，`cia/` 目录）**：本项目用 makerom 自行打包，可装到 3DS 主菜单，
  **仅适用于已破解、装了 Luma3DS 的机器**；基于 gpu-overlap 优化版，真机未验证。

**关于"资源"**：程序不会把 3.3 GB 游戏盘打进可执行二进制里，而是启动时按硬编码的
绝对路径 `sdmc:/3ds/SMG-3DS/game.wbfs` 去读 SD 卡——官方 3dsx 也是这么设计的。
所以 CIA 装到主菜单之后，读的还是**同一个 SD 卡目录**。这不是 CIA 缺东西，
而是这个移植的工作方式：**只要 `SD:/3ds/SMG-3DS/` 在，两种启动方式都能用**。
本包已经把这个目录（含盘镜像、settings.ini、官方占位 DSP 文件）全部准备好了，
你只需拷到 SD 卡，不需要另外找文件。

项目作者本人从未发布过 CIA，`cia/` 里那个是我们自己打的。详见 `cia/README-CIA.txt`。

  3ds/
    dspfirm.cdc                  105 B     官方占位文本（真机要声音需本机 DSP1 导出）
    SMG-3DS/
      SMG-3DS.3dsx             6,704,396 B  ★ 主程序：官方 v0.1.0 原版
      settings.ini             键位 / 指针设置
      nand/                    空目录，游戏存档会写在这里
      game.wbfs               3,508,535,296 B  ← 【本包已自带】美版 RMGE01 盘镜像
  optional/
    SMG-3DS.gpu-overlap.3dsx  6,589,820 B  可选：本项目编译的 GPU 重叠优化版
    SMG-3DS-diag.3dsx         ★ 诊断版：崩溃时把原因写进 SD 卡（见 cia/HOWTO-DIAG.txt）
    SMG-3DS-english.3dsx      ★ 强制英语修复版（根因解法，见 cia/ROOT-CAUSE.txt）
    SMG-3DS-fps.3dsx          ★★ 帧率显示版（英语修复 + 下屏 FPS，日常推荐）
    SMG-3DS-clipfix.3dsx      ★ 实验：2D/JPA 条纹改走 CPU 裁剪（真机未验证）
    SMG-3DS-debug.3dsx        ★ 调试版（= 英语修复 + FPS + 3dslink 实时日志），配合 GDB 用
    SMG-3DS-debug.elf         ★ 调试版的符号文件（GDB 用，与上面 3dsx 地址对应）
    dspfirm.cdc.from-other-console  别台机器的 DSP 固件（默认不用，仅留档）
  cia/
    ROOT-CAUSE.txt                    ★ 崩溃根因与强制英语修复版
    RENDER-ARTIFACTS.txt              ★ 真机渲染异常（蓝天空/白条纹）归因与对照实验
    SMG-3DS.cia               ★ 官方原版 CIA（推荐，版本 0.0.1）
    SMG-3DS-gpu-overlap.cia   优化版（真机未验证，仅供对照，别装）
    smg3ds.rsf                            ROM Spec File（复现用）
    SMG-3DS.smdh                          加固图标
    README-CIA.txt                       安装说明 / 权限 / 版本沿革
    TROUBLESHOOTING-ICON.txt             装完没图标看这个
    HOWTO-DIAG.txt                       ★ 诊断版用法（把崩溃原因写进 SD 卡）
    TROUBLESHOOTING-CRASH.txt            打开崩溃重启的排障清单
  RESET-SETTINGS.bat                   ★ 清掉 settings.ini 里的 dev.* 实验开关
  TRY-CLIPFIX.bat                      实验裁剪版一键安装
  prepare-disc.py                        轻量 zip 补齐镜像用
  install-to-sd.py                       ★ 一键拷到 SD 卡
  install-diag.py                        ★ 一键切换诊断版 / 恢复原版
  DEBUGGING.md                          ★ 实机调试手册（3dslink 网络推送 / 实时日志 / Rosalina GDB）
  deploy-3ds.py                         ★ 3dslink 推送到真机 / ftpd 写卡 / 拉 boot-log.txt
  live-log.py                           ★ 实时或轮询日志，格式化 + 告警 + CSV 导出
  WATCH-NETLOG.bat                      ★ 一键：deploy --server | live-log（实时看帧率/崩溃）
  GDB-3DS.cmd                           ★ 一键：arm-none-eabi-gdb 接真机 GDB stub（端口 4003）
  START-HERE.txt                         ★ 一页纸速查：CIA 怎么用
  STEP-BY-STEP-DIAG.txt                 ★ 崩溃诊断的详细逐步骤（含一键脚本）
  PATHS.txt                             ★ 所有文件的完整绝对路径清单

本包有三个形态，任选其一：
  `smg3ds/real-hardware/`              完整目录（已含镜像），最快，直接拷
  `smg3ds/SMG-3DS-hardware-FULL.zip`   完整单文件（3.286 GiB），解压即得同样目录
  `smg3ds/SMG-3DS-hardware.zip`        轻量归档（9.5 MB，不含镜像），解压后跑 prepare-disc.py


二、硬件与系统要求
------------------
- 必须是 **New** 3DS / New 3DS XL / **New** 2DS XL。老款 3DS / 2DS 跑不动（CPU/GPU 不够）。
- Luma3DS 自制固件 + Homebrew Launcher（通常是 sdmc:/boot.firm 与 hblauncher_loader）。
- SD 卡格式化为 **FAT32**（3DS 不认 exFAT/NTFS），簇大小 32 KB 或 64 KB 均可。
- SD 卡剩余空间 ≥ 4 GB；单个文件上限 4 GiB - 1。


三、安装步骤（最省事：一条命令）
--------------------------------
本包**已自带全部资源**：`3ds/SMG-3DS/game.wbfs` 是美版 RMGE01 盘镜像
（3,508,535,296 B = 3.268 GiB，已校验 WBFS 头与 game ID），`3ds/dspfirm.cdc` 是
官方占位文本（真机上只是没声音，不会崩），CIA 也在 `cia/` 里。你要做的只是把这些文件放到 SD 卡上。

方式 A（推荐，一键脚本）：
  cd smg3ds/real-hardware
  python install-to-sd.py --list          # 找 SD 卡盘符
  python install-to-sd.py E: --dry-run    # 预览，不写入
  python install-to-sd.py E:              # 实际拷贝

脚本把 `3ds/` 合并到 SD 卡根、把 CIA 放到 `SD:/cia/`，并校验 4 个关键文件；
**不删除 SD 卡上任何其它文件**，也拒绝写 C 盘。拷贝前会检查剩余空间 ≥4 GiB。

方式 B（手动）：把本包里的 `3ds/` 文件夹整个复制到 SD 卡**根目录**
（合并，不要套一层文件夹），最终应该是：
     SD:/3ds/dspfirm.cdc
     SD:/3ds/SMG-3DS/SMG-3DS.3dsx
     SD:/3ds/SMG-3DS/settings.ini
     SD:/3ds/SMG-3DS/game.wbfs          ← 3.268 GiB，本包已带
     SD:/3ds/SMG-3DS/nand/              （存档目录，可空）
再把 `cia/SMG-3DS.cia` 拷到 SD 卡任意位置。

镜像说明：3.268 GiB 是已 scrubbed 的 WBFS，**在 FAT32 单文件 4 GiB−1 限制内**，
直接放即可，不必转 RVZ。日版汉化 RMGJ01 实测卡在 boot（0 帧），只有美版能进游戏。
如果你手上只有**轻量 zip**（不含镜像），运行 `python prepare-disc.py` 会从本机
`D:\Dowdload\1103\...wbfs` 复制补齐，或手动放自己的美版 `game.wbfs` / `.rvz` / `.iso`。

`dspfirm.cdc`：本包现在放的是**官方 Release 的 105 B 占位文本**——真机上只是没有声音，不会崩，
这是与作者验证过的配置最接近的状态。之前那个 49,756 B 的合法 DSP1 固件来自
别台机器/模拟器（区域/系统版本可能不匹配），已移到 `optional/dspfirm.cdc.from-other-console`。
**要声音**：在你这台机器上跑 DSP1（FBI → titleDB → DSP1）导出到 `sdmc:/3ds/dspfirm.cdc` 再覆盖。
如果启动仍崩溃，也可以直接把这个文件删掉做对照。

启动：
  - 3dsx：插卡开机 → Homebrew Launcher → 选 SMG-3DS。
  - CIA：FBI / GodMode9 安装 `SD:/cia/SMG-3DS.cia`（需 Luma3DS）→ HOME 菜单点 SMG-3DS。
首次到标题约 1 分钟，下屏一直显示 `SMG boot bring-up` 调试文字，属正常。
**装完别删 `SD:/3ds/SMG-3DS/`** —— 游戏每帧都从这里流式读盘。


四、按键（3DS 实体键，不是 Azahar 键盘）
----------------------------------------
  移动               Circle Pad
  跳跃 (Wii A)       A 或 B
  旋转 (摇 Remote)   X 或 Y        ← 体感摇晃已做成按键，默认 X/Y
  蹲下 / 砸地        L
  发射星屑 (Wii B)   R
  镜头归位 (Wii C)   ZL
  指针归位           ZR
  暂停 (Wii +)       Start
  Wii -              Select
  Wii 十字键         D-pad

  标题处 `Press both A and B` = 3DS 的 **A + R** 一起按。
  Mario 要先在 Gateway Galaxy 从 Luma 拿到能力才能旋转，跟 Wii 一样。

  指针默认 `stylus`：下屏按住拖动即可。改 `settings.ini` 的 `pointer=` 可换成
  `cstick`（C-Stick）或 `motion`（陀螺仪）；改 `bind.spin=` 可换旋转键，
  多个键用 `+` 连接表示任一触发。改完需重启游戏。


五、实机已知问题（作者 README + 本项目文档）
--------------------------------------------
- **约 14 fps**（真机 ~70 ms/帧），其中 GPU 占 50–60 ms。这是 PICA200 侧瓶颈，
  和模拟器里 30 fps 完全是两回事。
- 画面缺陷：天空有蓝色板块、mip 层级在真机被关、水面/阴影异常、出现过场白线。
- 从 HOME 菜单关闭可能挂起；真挂了就长按电源键强制关机。
- 下屏全程只有调试文字；项目已归档、未完成，可能在没人测到的地方卡住。
- 存档在 `SD:/3ds/SMG-3DS/nand/`。


六、可选：换成 gpu-overlap 优化版
----------------------------------
`optional/SMG-3DS.gpu-overlap.3dsx` 是本项目用 devkitARM 自行编译的优化版，
应用了作者留下的 `docs/untested/gpu-overlap.diff`。它在 Azahar 里验证过无回归
（11 个采样：28.61 → 28.63 fps），但**从未上过 PICA200 真机**——作者当年只测了模拟器。

要测试就把它改名为 `SMG-3DS.3dsx` 覆盖主程序（先备份原版）。若出现花屏、冻结或
启动失败，换回原版即可。真机上这一版的价值主要在于验证「GPU 与帧构建重叠」
到底能不能把 51 ms 的 GPU 等待和 23 ms 的帧构建折叠起来。


七、如果要做真机性能采集（本项目下一步）
------------------------------------------
在 `settings.ini` 末尾加开发键（值为 0/1）。程序通过 stderr 输出 `gx perf` 明细：
每帧各阶段耗时、GPU 等待、retrace、draws/primitives/vertices、display lists、
mesh 缓存命中等。源码位置：`source/core/Settings.cpp:137`、`GxRender.cpp` 的 `perfLine()`。

  dev.gx_timing=1    把渲染器分项加进 perf 行（状态构建/缓存命中、CPU 路径顶点与
                     draw、mesh 查找、uniform、纹理首次使用、texture copies、frame ends）
  dev.gx_zones=1     按「渲染线程当时在做什么」切分时间 —— 分阶段计时的关键
  dev.gx_null=1      什么都不画，测出游戏自身（非 GPU）开销；与上两项做差即得 GPU 侧占比
  dev.gx_dump=1      每分钟 dump 一帧的 draws 到日志
  dev.gx_check=1     每个新 mesh 与 CPU 路径比对
  dev.gx_inline=1    在游戏线程而非渲染线程绘制
  dev.gx_mips=1      打开 mip 层级（真机上贴图会花，仅用于对照）
  dev.skip_story=1   跳过序章故事书/电影，快速进场景

固定场景做 A/B（避免每次走不同的路）：
  dev.start=GALAXY N [ZONE]   直接从某星系的起始点 N 开局，可带 zone
  dev.galaxy=GALAXY N         文件选择后第一个星系改成指定星系/剧本
  dev.warp=X Y Z [秒]         传送到坐标
  dev.skip_story=1 + dev.start=... 是最省时的复现组合。

**注意（作者实测的两条硬约束）**
- `dev.gx_timing` 每次读时钟在 Azahar 上要 150 cycles，全开会把它测量的对象拖慢最多 1/5；
  真机上影响不同，读数要留余量，别把计时开销当成优化收益。
- **测试构建绝不能在渲染线程写 SD 卡**，作者实测那样会 +150 ms/帧。
  先确认 stderr 的落点（3dslink / ftpd / 下屏 console），再开日志。

完整测量方案、分阶段计时构建的思路和「12 次 EFB copy」分析见工作区
`smg3ds/AGENT_HANDOFF.md` §17 / §19；`smg3ds/extract_gx_perf.py` 可把日志转成 CSV，
`smg3ds/baseline/` 有模拟器侧 174 点基线可对照。

**想真正在真机上迭代（而不是拔卡猜）**：见 `DEBUGGING.md`。三种通道——
3dslink 网络推送（不拔卡）、`deploy-3ds.py --server` 实时回传 stderr（不拍照）、
Rosalina GDB 断点/看变量（真机调试器）。模拟器用的是 PC 显卡，**PICA200 的定点裁剪缺陷
在模拟器上不复现**，所以任何画面修复都必须用这套真机通道验证。


八、可选：装成主菜单图标（CIA）
--------------------------------
`cia/SMG-3DS.cia` 可装到 3DS 主菜单，但**不是官方版本**，也不是装上就完事：

- 仅适用于已破解、装了 Luma3DS 的机器；Ticket/TMD 是测试签名，原版系统装不了。
  用 FBI 或 GodMode9 安装到 SD。
- **盘镜像不在 CIA 里，而在 SD 卡上**：程序按硬编码的 SD 卡绝对路径读盘，与装在
  哪无关。本包已把 `3ds/`（含 `game.wbfs`、`settings.ini`、`dspfirm.cdc`）备好，
  用 `install-to-sd.py` 拷到 SD 卡根即可，**装完别删这个目录**。
- **`cia/SMG-3DS.cia` 现在是官方 v0.1.0 原版 ELF 重打的**（版本 0.0.1）。
  之前的 gpu-overlap 优化版已改名 `SMG-3DS-gpu-overlap.cia` 并标注"真机未验证"，
  别装它——用户实机装优化版后打开直接崩溃重启，而该补丁作者从未上过 PICA200 真机。
  同 TitleID + 更高版本，FBI 直接覆盖安装即可。若原版仍异常，用 3dsx 原版走
  Homebrew Launcher 启动，共用同一份资源。
- 该 CIA 已用 ctrtool 校验全部内容哈希、用 `azahar -i` 走完整安装流程成功，
  并在 Azahar 2126.2 里以等价 CXI 进标题画面（30 帧、读到 RMGE01）；
  **真机图标显示仍待确认**（用户装 v1 后未出现图标，因此出了 v2 加固版）。
- 已知缺 banner（HOME 菜单启动动画为默认），不影响运行。

Title ID `000400000FF3FF00`（v2）、804 MHz / L2 / Core 2 / 124MB / Direct SDMC 权限，
以及完整复现命令，全部写在 `cia/README-CIA.txt`。
**装了 CIA 但 HOME 菜单没图标 → 看 `cia/TROUBLESHOOTING-ICON.txt`**：
确认是否真装上、重启刷新图标库、SysNAND vs EmuNAND、卸载旧 TitleID `000400000A5D3300`。
**★ 根因已定位（21:10）：系统语言非英语 → 加载含 ruby tag 的 BMG → 程序 abort。**
先看 `cia/ROOT-CAUSE.txt`；推荐直接双击 `SHOW-FPS.bat` 装帧率显示版
（= 强制英语修复 + 下屏 FPS），命令行等价写法：
    py -3 "C:\Users\WXP\WorkBuddy\2026-11-08-01-41-44\smg3ds\real-hardware\install-diag.py" F: --fps

**画面花纹 / 几何撕裂 → 先双击 `RESET-SETTINGS.bat` 清掉 dev.* 开关再试；
仍不消退看 `cia/RENDER-ARTIFACTS.txt`（含为什么模拟器正常、真机不正常）。

**3dsx 也崩 / `luma/dumps/` 是空的 → 看 `STEP-BY-STEP-DIAG.txt`（诊断步骤）**：
`python install-diag.py <盘符>` 一键切换诊断版（自动备份原版），
用 `optional/SMG-3DS-diag.3dsx` 把 stderr 写进 `SD:/3ds/SMG-3DS/boot-log.txt`，
崩完把文件发回即可定位（程序自己注册了 CPU 异常处理器，Luma 不会生成 dump）。
机制细节见 `cia/HOWTO-DIAG.txt`。


来源
----
- 官方 Release：https://github.com/cmyksoda/SMG-3DS/releases/tag/v0.1.0
- 本项目台账：smg3ds/AGENT_HANDOFF.md
- 打包时间：2026-11-08
