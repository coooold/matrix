# 架构与自动开发流程

## 分层

| 层 | 职责 | 当前状态 |
| --- | --- | --- |
| Linux DRM/KMS、驱动 | 显示提交、GPU 与 dma-buf 同步 | 依赖宿主，未改造 |
| KWin / Wayland | 合成、窗口管理、显示器、输入路由 | 沿用系统，待实机集成 |
| Matrix shell / QML | 桌面、面板、启动器、通知、交互动画 | 窗口化预览 |
| Qt 对象与模型 | 界面状态、异步结果、安全的应用接口 | 有限列表、单工作线程、最新请求优先的筛选 |
| 后台服务 | 索引、缩略图、更新、搜索 | 后续拆为独立受限服务 |
| 测量与回归 | 帧间隔、输入延迟、冷/热启动、资源 | 统计工具及基础 CI |

PySide6 是 Qt 官方 Python 绑定，QML 场景由 Qt Quick 渲染。Python 层只负责低频状态及 I/O 调度。
CPU 密集型解码、索引和搜索应使用独立进程或原生工作模块，避免 Python GIL 抢占交互。
文件扫描限一个并发、最多返回 200 项，并在工作线程执行。当前只是浏览演示；真实文件管理需要分页、取消与增量模型。
文件名筛选在同一限并发工作池执行，100 ms 防抖，最多一个运行任务及一个最新请求，使用修订号丢弃旧结果。
筛选只覆盖已枚举的 200 项，不能等同完整搜索；小窗口最小尺寸 360×480。

基础壳已提供 Theme 视觉令牌、Qt Quick Controls 按钮/输入框、焦点恢复、键盘列表导航及 Accessible 名称/角色。
自动测试覆盖鼠标、键盘、空结果、小窗口和过期结果抑制；读屏器、中文输入法、触屏及真实 Wayland 焦点行为仍待实机验收。

后续 KWin 集成优先评估 KDE Plasma 的受支持 shell 扩展路径以及对应版本的 layer-shell、窗口列表和快捷键接口。
需记录 KDE/Qt 兼容矩阵后再选择原生桥接模块；普通顶层窗口不具备独占区域、桌面角色或安全锁屏能力。
不直接改造 KWin、不假设所有合成器都支持 KDE 私有协议。

## 资源管理

packaging/systemd 提供 user slice 候选参数；尚未启用，数值必须通过实机负载校准。
交互进程放入 matrix-interactive.slice，索引等进程放入 matrix-background.slice。
可由用户复制到 `~/.config/systemd/user/`、执行 `systemctl --user daemon-reload` 后，使用：

```sh
systemd-run --user --scope --slice=matrix-interactive.slice .venv/bin/matrix-shell
systemctl --user show matrix-interactive.slice -p CPUWeight -p IOWeight -p MemoryLow
```

需 cgroup v2 及对应控制器委派；MemoryLow 是尽力保护，CPUWeight/IOWeight 是相对竞争权重。
后台服务仍需自身限并发（初始 1–2），配额不能替代任务取消和调度。不要向已有会话全局应用未经验证的参数。

## 迭代顺序

阶段交付与验收以 [OMEGA-OS 基准流程](omega-development-workflow.md) 和 [结构化清单](acceptance.json) 为准；以下是技术依赖顺序。

1. 基础壳：设计令牌、键盘导航、可访问性、自动界面交互测试。
2. KWin 集成：桌面层、面板保留区、多显示器、分数缩放、热插拔；先在嵌套会话验证。
3. 真实桌面功能：应用注册表、窗口激活、通知；文件与搜索用独立服务。
4. 性能闭环：合成器 presentation 时间、输入到光子测量、负载测试、Windows 对照。
5. 会话与发行：退出恢复、崩溃重启、安全锁屏、升级回滚；审核后才安装会话文件。

## 自动任务闭环

验收 ID → Given/When/Then → 接口验证 → 垂直切片 → 基础 CI → 必需场景 gate → 证据与人工复核 → PR。

`./tools/check.sh` 验证验收清单结构、运行 pytest/JUnit 和 offscreen smoke；GitHub Actions 保存测试报告与 wheel。
KWin、visual、hardware、session gate 尚未建设，不能由基础 CI 代替。
GitHub Actions 自动执行基础 gate；失败必须诊断，不可通过跳过测试过关。
涉及渲染、输入或资源管理时还必须在有 GPU 的专用 runner 或实机执行性能协议；基础 CI 无法替代。
硬件结果由 reviewer 审核后才进入发布；暂不启用自动合并和自动发布。
