# 性能验收协议

## 帧预算

60 Hz 的显示周期是 16.67 ms；120 Hz 是 8.33 ms。
初始工程目标：GUI 每帧 CPU 工作 P99 分别不超过 4 ms / 2 ms，剩余时间留给渲染、合成和调度。
这不是实测结论，也不代表三者简单串行相加。先排除主线程阻塞，再评估模糊、阴影与透明叠加。
避免逐帧创建阴影或反复布局；列表按需创建、reuseItems；解码、网络、遍历均不在 GUI 线程执行。

## 同机 Windows 对照

每次记录硬件、驱动、内核、KWin/Qt/Windows 版本、电源模式、温度、分辨率、刷新率、缩放与视觉效果。
统一屏幕、输入设备与电源，冷/热缓存分开。每场景至少 5 次、每次稳定采样 60 秒，分别保留原始数据。

| 场景 | 采集指标 |
| --- | --- |
| 拖动、缩放、滚动、桌面切换 | presentation 帧间隔 P95/P99、实际丢失刷新数 |
| 点击、键入、打开菜单 | 输入到画面变化 P95/P99，优先高速摄像或硬件触发测量 |
| 启动 | 冷启动、热启动、首次可操作时间，统一判定点 |
| 资源与稳定性 | CPU/GPU、RSS、功耗、内存压力、崩溃及恢复 |

上述交互必须分别在空闲、复制大文件、CPU 饱和、GPU 饱和时测试。
尤其验收边复制边拖窗、CPU 高负载开菜单、GPU 高负载切换应用。
固定负载工具、参数、文件规模和磁盘，避免不可比的压力强度。压力生成只在专用实机上显式执行。

Qt Quick profiler 分析 GUI/渲染阶段，合成器 presentation 反馈用于输出节奏；frameSwapped 不能代表物理屏幕显示。
输入到光子延迟不能从帧间隔推算。Windows 侧使用 PresentMon/ETW 与同一外部延迟测量设备。

`tools/frame_report.py capture.json` 接受 `{"refresh_hz":120,"interval_ms":[8.3,8.4,16.7]}`。
输出 nearest-rank P95/P99 和超预算区间比例（容忍 5% 计时抖动），后者**不是掉帧率**。
真实掉帧数需结合 presentation 序号/刷新周期另行采集。不同来源的统计不得混用。

验收要求：各场景帧间隔、掉帧率、输入延迟不劣于同机 Windows；预先声明测量误差和置信区间。
没有基线、原始数据或硬件 runner 时标记“未验收”，不得按通过处理。
当前仓库没有真实性能捕获数据；云端软件渲染 smoke 仅为功能检查。

参考：[Qt Quick 性能](https://doc.qt.io/qt-6/qtquick-performance.html)、
[systemd 资源控制](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html)。
