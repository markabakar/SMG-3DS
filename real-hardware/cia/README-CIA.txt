SMG-3DS.cia —— 可安装到 3DS 主菜单的 CIA（官方原版）
=====================================================

  SMG-3DS.cia              6,547,392 B  ★ 官方 v0.1.0 原版，版本 0.0.1
                            SHA-256 48c45d9adfb91cd9f27477e4c0a5d1da7622e883688191b5969a52c6f972f2c7
  SMG-3DS-gpu-overlap.cia  6,547,392 B  优化版（真机未验证，仅供对照，别装）
  smg3ds.rsf               makerom 的 ROM Spec File（可复现打包）
  SMG-3DS.smdh             加固后的 SMDH 图标（可见性 / 使用记录 / 区域位）
  TROUBLESHOOTING-ICON.txt    装了 CIA 但 HOME 菜单没图标 → 看这个
  TROUBLESHOOTING-CRASH.txt   ★ 打开就崩溃重启 → 先看这个
  （本文件里的 ../ 指包根目录 C:\Users\WXP\WorkBuddy\2026-11-08-01-41-44\smg3ds\real-hardware\ ）

Title ID      : 000400000FF3FF00   (UniqueId 0xff3ff，homebrew 保留区)
TitleVersion  : 0.0.1              (便于 FBI 覆盖安装)
Product Code : CTR-H-SMGS
Title        : SMG-3DS（取自 SMDH，Azahar 窗口标题已验证）
构建工具     : CTR MAKEROM v0.19.0，-target t -exefslogo，CTR Tool v1.2.1 校验
内容         : **官方 v0.1.0 原版 ELF**（仅加 5 行 GCC 15 链接修复，无游戏逻辑改动）

**为什么换成原版**：用户实机装了 gpu-overlap 优化版 CIA 后打开直接崩溃重启。
作者文档明确说该补丁「从未上过 PICA200 真机」，它改了 `C3D_FrameSplit` /
`gxCmdQueueRun` 时序，真机极可能触发 GPU 异常。因此主 CIA 换回官方原版。
优化版保留为 `SMG-3DS-gpu-overlap.cia`（SHA-256 `e2cb8020…38cf5422b`）。
**同 TitleID + 更高版本，FBI 直接覆盖安装即可，无需卸载。**
崩溃排查见 TROUBLESHOOTING-CRASH.txt（3dsx 对照实验、DSP 固件、Luma dump）。

版本沿革：v1 `000400000A5D3300`（自定义 UniqueId，图标不显示）→ v2
`000400000FF3FF00`（换保留区 + ExeFS logo + SMDH 加固，但基于优化版）→
当前（沿用 v2 TitleID，改回官方原版 ELF，版本 0.0.1）。


一、适用范围（务必先读）
------------------------
- **仅适用于已破解、装有 Luma3DS（签名绕过）的 New 3DS / New 2DS XL。**
  这是未签名/测试签名的自制 CIA：ctrtool -y 显示 Ticket / TMD / AccessDescriptor
  签名 FAIL，而所有内容哈希 GOOD。这是 homebrew CIA 的正常状态，FBI / GodMode9
  能装；**原版未破解系统装不了**。
- **作者本人从未发布过 CIA**，这个文件是本项目自行打包的，不是官方版本。
- **游戏资源不在 CIA 里，而在 SD 卡上**——这是这个移植的设计（官方 3dsx 也一样），
  程序用 `FSUSER_OpenFileDirectly(ARCHIVE_SDMC, "/3ds/SMG-3DS/game.wbfs")` 按硬编码
  的 SD 卡绝对路径流式读盘，与程序装在哪里无关。
  **好消息：本包已把这些文件全部备好在 `../3ds/` 目录里**，用 `../install-to-sd.py`
  一键拷到 SD 卡即可，不需要你另外找任何文件。装完必须保留：
    SD:/3ds/SMG-3DS/game.wbfs       美版 RMGE01 盘镜像（3.268 GiB，已带）
    SD:/3ds/SMG-3DS/settings.ini    键位 / 开发开关（已带）
    SD:/3ds/SMG-3DS/nand/           存档目录（可空）
    SD:/3ds/dspfirm.cdc             官方占位文本（真机要声音需本机 DSP1 导出）
- **基于 gpu-overlap 优化版**。该补丁在 Azahar 验证过无回归，但**从没上过
  PICA200 真机**。若真机出现花屏/冻结，改用 3dsx 目录里的官方 v0.1.0 原版
  （Homebrew Launcher 启动）即可，两者共用同一份 SD 卡资源。


二、安装
--------
1. 在 `../` 目录运行 `python install-to-sd.py E:`（E: 换成你的 SD 卡盘符）。
   它会把 `3ds/` 拷到 SD 卡根、把 CIA 放到 `SD:/cia/`，并校验关键文件。
   手动做法：把 `../3ds/` 整个文件夹拷到 SD 卡根（已含盘镜像和官方占位 DSP 文件，
   **无需另找文件**），再把 `SMG-3DS.cia` 拷到 SD 卡任意位置。
2. 开机进 FBI（或 GodMode9）→ 选 "Install and delete CIA" / "Install CIA" → 装到 SD。
3. 退出到 HOME 菜单，会出现 "SMG-3DS" 图标，点它启动（约 1 分钟到标题）。
   如果不想装 CIA，直接用 Homebrew Launcher 启动 3dsx 原版也行，共用同一份资源。

注意：图标能显示，但**这个 CIA 没有 banner**（ExeFS 只有 .code 和 icon），
HOME 菜单启动时的上屏动画/音效会是默认或空白，不影响游戏本身运行。
本机没有 bannertool 的 Windows 构建，因此没有补上；需要的话可自行用 bannertool
生成 banner.bin 再用 makerom -banner 重打。


三、exheader 权限（ctrtool 逐项核对过）
---------------------------------------
  CPU Speed (New3DS)  : 804MHz        ← 项目必须，268MHz 跑不动
  Enable L2 Cache     : YES
  Access Core 2       : YES           ← GxFifo.cpp 把渲染线程绑到核心 2
  System mode (N3DS)  : 124MB (snake prod)
  FS access           : Direct SDMC + Direct SDMC (Write Only)
  Stack               : 0x40000       SaveDataSize 0
  Services            : 32 个，含 fs:USER / gsp::Gpu / hid:USER / APT:U /
                        ptm:sysm / dsp::DSP / y2r:u / qtm:u
  NCCH                : Executable (without RomFS), Crypto Key None,
                        不加密、不压缩 ExeFS .code
  ExeFS               : .code 0x631000 B、icon 0x36c0 B（SMDH）
  Content hash        : 6EB830B743778FA2ACFB59F527C2C75A045CEEFC60E0570ECBB026030E170ADF
                        （与 TMD ContentInfo / ctrtool -y 一致）

`osSetSpeedupEnable(true)` 在 main() 里调用，走 ptm:sysm 的 ConfigureNew3DSCPU；
Azahar 2126.2 未实现该服务函数（日志会报 unimplemented），但 exheader 已把
804MHz 写死，真机上由 Luma 正常处理。


四、已验证 / 未验证
--------------------
已验证（Azahar 2126.2 官方版，独立便携实例）：
- ctrtool 完整解析 CIA：证书链、Ticket、TMD、NCCH、ExeFS、Exheader 全部合法；
  内容/ExeFS/Exheader/Logo 哈希 GOOD。
- 把 CIA 里的 NCCH 提取成 .cxi（与独立 makerom 输出逐字节一致）直接加载：
  `The disc: WBFS, game RMGE01` → 成功进《超级马力欧 银河》标题画面，
  状态栏 `速度 100%/100%`、`应用: 30 帧`，gx perf 持续到 t=102 秒无崩溃。
- 窗口标题变为 `Azahar 2126.2 | SMG-3DS`，SMDH 生效。

未验证：
- **真机安装与运行**（缺 New 3DS + Luma3DS + ftpd）；签名链在真机 CFW 下的表现、
  HOME 菜单关闭行为、gpu-overlap 补丁在 PICA200 上的收益，都还没测。
- CIA 本身的"安装到 NAND"动作（验证用的是等价 CXI 直接加载，内容哈希已比对一致）。

真机已知问题照旧：约 14 fps（GPU 占 50–60 ms）、天空蓝色板块、mip 被关、
水面/阴影异常、HOME 关闭可能挂起（长按电源）、下屏调试文字。


五、重新打包（给接手的 agent）
------------------------------
工具与中间产物都在 `smg3ds/tools-cia/`：makerom.exe、ctrtool/ctrtool.exe、
smg3ds.rsf、SMG-3DS.cxi、exheader.bin、exefs.bin、sample1.rsf、project_ctr.tar.gz。

  cd smg3ds/tools-cia
  ./makerom.exe -f cia -o SMG-3DS.cia -target t -rsf smg3ds.rsf ^
      -elf "../build-3ds/mario_probe.elf" ^
      -icon "../build-3ds/SMG-3DS.smdh" -v
  ./ctrtool/ctrtool.exe -y SMG-3DS.cia          # 校验哈希
  ./ctrtool/ctrtool.exe -t exheader -v exheader.bin   # 查看权限位

要点：
- RSF 里 `Dependency: {}` 不被 makerom 接受，必须整段省略。
- `-icon` 可直接吃 smdhtool 产出的 .smdh（14016 B）。
- 换 ELF 即可换版本：目前 build-3ds 里是 gpu-overlap 优化版；若要官方原版 CIA，
  需用 `smg3ds/src/`（原版源码）先编出 ELF 再执行同一条命令。
- `-target t` = test/false keys + prod certs，专为 CFW 自制软件；不要改成 -target p。

打包时间：2026-11-08
