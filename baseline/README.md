# gx perf 基线 · console-sim 档（2026-11-08）

## 数据文件
| 文件 | 内容 |
| --- | --- |
| `console-sim-20261108.csv` | 174 个采样点的完整结构化数据（17 列，便于 diff） |
| `console-sim-table.txt` | 同一数据的紧凑表格 + 汇总 |
| 源日志 | `../azahar-portable/user/log/azahar_log.txt`（约 713 s / 12 min，用户实际进游戏跨多个场景） |
| 提取工具 | `../extract_gx_perf.py`（`--csv` 导出、`--slow` 只看掉帧点） |

## 采集条件
独立便携实例 `azahar-portable`，官方 Azahar 2126.2，美版 RMGE01 WBFS，v0.1.0 原版 `SMG-3DS.3dsx`（**未应用任何优化补丁**）。
配置档 `console-sim`：`cpu_clock_percentage=300`、`simulate_3ds_gpu_timings=true`、`graphics_api=1`(OpenGL)、`resolution_factor=1`、`is_new_3ds=true`。
日志开关：`instant_debug_log=true`、`log_filter=*:Info Debug.Emulated:Debug`，且四个键的 `\default` 标记均为 `false`（否则 Azahar 忽略写入值）。

## 汇总
```
samples=174  fps avg=29.66  min=17.1  max=30.2
GPUwait avg=0.06 ms  max=4.9 ms
GXstream avg=4.60 ms max=17.4 ms
below 29 fps: 8 -> t=[23, 27, 71, 119, 208, 412, 437, 485]
```

## 掉帧点
| t(s) | ms/帧 | fps | GPUwait | GX stream | PICAwait | retrace | logic | prims | draws |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 23 | 58.5 | 17.1 | 0.0 | 0.3 | 0.0 | 16.5 | **12.5** | 4 | 4 |
| 27 | 35.4 | 28.2 | 1.2 | 4.5 | 0.0 | 15.8 | 0.4 | 242 | 9 |
| **71** | **42.8** | **23.3** | **4.9** | **12.6** | **0.8** | 15.2 | 0.8 | 426 | 15 |
| 119 | 35.4 | 28.3 | 1.0 | 5.3 | 0.1 | 15.4 | 0.5 | 113 | 18 |
| 208 | 34.7 | 28.9 | 0.0 | 0.3 | 0.0 | 2.3 | 0.3 | 3 | 2 |
| 412 | 35.0 | 28.6 | 0.0 | 0.3 | 0.0 | 1.8 | 0.3 | 3 | 2 |
| 437 | 34.6 | 28.9 | 0.0 | 0.3 | 0.0 | 1.8 | 0.3 | 3 | 2 |
| 485 | 36.2 | 27.7 | 1.5 | 5.8 | 0.1 | 14.5 | 1.4 | 66 | 31 |

场景复杂度演进（另见日志 `gx perf: GPU path` 行）：draws 最高约 108、GPU path 三角形峰值约 71k、display list 峰值约 1.1 MB/帧；`movie frames decoded` 全程为 0（本轮未播放 THP 电影）。

## 结论（重要）
1. **这套 `console-sim` 档没有复现真机 GPU 瓶颈**：`waiting for the GPU` 平均仅 0.06 ms、最大 4.9 ms，而真机是 50–60 ms/帧。`simulate_3ds_gpu_timings` 提高的是 GPU 中断队列的时序精度，**不会把 RTX 3090 降速成 PICA200**。
2. 真正的掉帧主要来自 **CPU 侧逻辑/加载**（t=23 的 `logic 12.5 ms`）与场景切换（t=71 的 GX stream 12.6 ms + GPUwait 4.9 ms），不是 GPU 算力。
3. `retrace wait` 常年在 7–16 ms，说明 30 fps 目标下仍有大量空闲；`GX stream read on core 2` 在 t=573–655 稳定 15–17 ms，是 CPU 侧最重的一项，值得作为优化目标观察。
4. 用户反馈的"过场动画卡"，本轮日志里 `movie frames decoded=0`，所以更可能是故事书/场景切换/资源加载，而不是 THP 电影解码。下次复现时请特意进入过场并抓取 `movie frames decoded` 与 `logic` 值。
5. **用途边界**：这份数据适合做 CPU 侧与流水线重叠逻辑的 A/B（例如验证 `gpu-overlap` 改动有没有引入回归），**不能**用来外推真机 GPU 优化收益。要模拟真机 GPU，需给渲染线程注入人为延迟（`delay_game_render_thread_us`，QVariant 二进制格式，须在 GUI 设），目标约 50 ms/帧，再看 `waiting for the GPU` 是否抬升。

## A/B 复现
```bash
# 1. 关闭模拟器，切到与基线相同的档
python ../azahar-portable/switch-profile.py console-sim
# 2. 备份 stock 3dsx，换上优化版
# 3. 启动，跑同一段路线（或同一场景停留等长）
# 4. 提取并 diff
python ../extract_gx_perf.py ../azahar-portable/user/log/azahar_log.txt --csv new.csv
diff <(cut -d, -f1-5 console-sim-20261108.csv) <(cut -d, -f1-5 new.csv) | head
```
重点对比：`waiting_gpu_ms`、`gx_stream_ms`、`ms_per_frame`、`retrace_wait_ms`，且必须在**同一场景/同一操作**下比较。
