# SMG-3DS 实机调试手册

之前那几轮确实是「盲改 → 你拔卡拷文件 → 拍照回来」，一轮十几分钟、信息量只有一帧画面。
这本不是调试，是猜。下面三套通道用 devkitPro 自带工具把循环压到几分钟，且能在**真机**
（不是模拟器）上看到发生了什么。

> 前置：3DS 与 PC 在同一 WiFi。3DS 已破译（Luma3DS，你已有）。
> 所有命令从 `real-hardware/` 目录运行，或双击同名 `.bat` / `.cmd`。

---

## 通道 A —— 3dslink 网络推送（不再拔 SD 卡）

用 Homebrew Launcher 的 netloader 把 3dsx 直接推到内存运行，**完全不碰 SD 卡**。

1. 3DS 上打开 Homebrew Launcher，按 **Y** —— 屏幕会显示本机 IP（如 `192.168.1.50`）。
2. PC 上（把 IP 换成你 3DS 显示的）：

```bat
py -3 deploy-3ds.py --ip 192.168.1.50 --build debug
:: 或一键： WATCH-NETLOG.bat 192.168.1.50
```

`deploy-3ds.py` 会调用 `C:\devkitPro\tools\bin\3dslink.exe` 推送并启动。
`--build debug` 指向带符号的 `optional/SMG-3DS-debug.3dsx`（含强制英语修复，中文机不崩）。

备选：若不想用 netloader，用 **ftpd**（FBI → titleDB → ftpd，或 ftpd.cia）把文件写进 SD 卡：

```bat
py -3 deploy-3ds.py --ftp 192.168.1.50 --build debug
```

---

## 通道 B —— 3dslink `--server` 实时日志（不再拍照片）

`debug`（= netlog）构建在启动时若检测到经 3dslink 启动，会把 **stderr 实时回传 PC**
（gx perf、stops、faults 一字不漏）；从 SD 卡启动时则自动降级写 `boot-log.txt`（与 FPS 版一致）。

PC 端把回传流接进 `live-log.py` 做格式化 + 告警 + CSV：

```bat
py -3 deploy-3ds.py --ip 192.168.1.50 --build debug --server | py -3 live-log.py --stdin
```

你会实时看到（每 4 秒一条采样）：

```
t= 181  33.5 ms  29.9 fps | GPUwait   0.0  GX  15.2  PICA   0.0 | 4985 prim
   heartbeat: Mario at (0, 0, 0)
```

- 任意 `abort / fault / no layout / BMG message / data abort` 会立刻以 `!!` 标红。
- 想导出 CSV 做 A/B：`live-log.py --stdin --csv baseline/runN.csv`。
- 没开 3dslink 时也能用：`live-log.py --drive F:`（SD 卡盘符）或 `live-log.py --ftp <IP>`（轮询 ftpd）。

这取代了「拍一张崩坏画面 → 猜是哪一步」。现在你能看到**每一帧到底卡在等 GPU、还是 primitive 暴涨**。

---

## 通道 C —— Rosalina 真机 GDB（真正的断点 / 看变量 / 回溯）

这是唯一能「看程序内部状态」的通道。需要 Luma3DS 的 GDB stub 与带符号的 ELF。

**3DS 上：**
1. 呼出 Rosalina 菜单（默认组合 **L + Down + Select**）。
2. `Debugger options` → `Enable debugger` → `Force-debug next application at launch`。
3. 记下**右上角的 IP** 和提示的**端口**（break-on-start 用 **4003**；普通 attach 用 4000–4002）。

**PC 上（屏幕会在 3DS 启动后变黑等待）：**
1. 从 HBL / SD 卡启动 SMG-3DS（也可经 3dslink 推）。
2. 双击 `GDB-3DS.cmd 192.168.1.50`（内部：`arm-none-eabi-gdb` + `target remote 192.168.1.50:4003`）。

常用命令：

```
(gdb) c                      # 继续运行
(gdb) b smg::Renderer::perfLine        # 按函数名下断点
(gdb) b source/core/GxDraw.cpp:1250    # 按文件:行下断点
(gdb) p someVar             # 打印变量
(gdb) watch *(float*)0xaddr # 监视某地址写
(gdb) bt                    # 崩溃时看调用栈
(gdb) s / n                 # 单步 / 下一步
```

- 符号文件：`optional/SMG-3DS-debug.elf`（与部署的 `SMG-3DS-debug.3dsx` **同一构建**，地址对应）。
- 当前构建带 `-g`、优化为 `-O2`：函数入口断点、`p`、`bt`、`watch` 都好用；单步会被内联打乱。
  要更细的单步，把 `CMakeLists.txt` 优化改成 `-Og` 再跑 `make_debug_build.py` 即可。

---

## 用这套工具解决当前的渲染撕裂

你拍的那张「网点花纹 + 大蓝三角」是 PICA200 定点裁剪缺陷（模拟器用的是 PC 显卡，不复现，
所以**任何渲染修复都必须真机验证**）。现在可以这样定位，而不是猜：

1. **复现场景**：进崩坏的那个场景，用通道 B 看 `gx perf`——
   `pica_wait` 是否异常、`primitives` 是否暴涨、`refused by reason` 是否变化。
2. **A/B 对比**：
   - `SHOW-FPS.bat`（对照，原渲染器）
   - `TRY-CLIPFIX.bat`（实验，2D/JPA 条纹走 CPU guard-band 裁剪）
   - `deploy-3ds.py --build debug` + GDB（带断点，看顶点坐标是否被抛到几万像素外）
3. **真机断点示例**：在 `GxVertexPipeline::runDecoded` 或 `GxDraw.cpp` 近平面裁剪处下断点，
   打印被裁剪顶点的齐次坐标 `w` 和裁剪后新顶点的屏幕坐标，确认是不是 PICA 把新角点抛飞。

一轮流程从「15 分钟 + 一张照片」变成「几分钟 + 实时数字 / 断点」。

---

## 工具清单（都在 `real-hardware/`）

| 文件 | 作用 |
| --- | --- |
| `deploy-3ds.py` | 3dslink 推送 / ftpd 写卡 / 拉 `boot-log.txt`；`--list` 看所有构建与哈希 |
| `live-log.py` | 实时或轮询日志，格式化 + 告警 + CSV 导出 |
| `make_debug_build.py` | 生成 matched-pair 调试构建（3dsx + 对应 ELF），并自动还原源码树；位于 `smg3ds/` 源码树根目录（与 `make_fps_build.py` 同处），不在 `real-hardware/` |
| `WATCH-NETLOG.bat` | `deploy-3ds.py --ip %1 --build debug --server \| live-log.py --stdin` 一键 |
| `GDB-3DS.cmd` | 启动 `arm-none-eabi-gdb` 并 `target remote %1:4003` 一键 |
| `optional/SMG-3DS-debug.3dsx` | 部署用（强制英语 + FPS + 3dslink 实时日志） |
| `optional/SMG-3DS-debug.elf` | GDB 符号文件，与上面 3dsx 地址对应 |

> 注：`deploy-3ds.py --list` 会列出全部构建及 SHA，部署前先核对哈希，避免装错版本。
