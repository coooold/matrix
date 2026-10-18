# 云端迭代验证

本轮实现并验证了可在云端运行的原生桌面主线，**没有完成完整桌面发布验收**。
用户确认仅云端开发；同机 Windows、真实 GPU 与输入到光子测试继续保留为未执行，未降低原有标准。

本次回归场景（APP-01 / DISPLAY-01 / SYS-01）：给定独立 wheel 和两个虚拟输出，启动入口应从安装目录读取资源；在第一屏打开系统面板、再从第二屏打开菜单时，第一屏菜单应关闭且释放状态轮询。仅保留当前可见视图的轮询，不让隐藏面板长期运行后台采样。

## 环境与可复现命令

当前镜像：Debian 13 amd64、Python 3.12、PySide/Qt 6.8.3。
通过 Debian 签名索引准备 KWin 6.3.6、LayerShellQt 6.3.4、kscreen-doctor 与 Konsole 运行时；包版本与 SHA256 保存在 `.cache/kwin/packages.txt`。

```sh
./tools/setup.sh
./tools/prepare_kwin.sh
./tools/check.sh
.venv/bin/python tools/cloud_check.py
.venv/bin/python -m pip wheel --no-deps --no-build-isolation . -w dist
.venv/bin/python tools/wheel_check.py dist/matrix_shell-0.1.0-py3-none-any.whl
.venv/bin/python tools/probe_environment.py
```

基础测试、CLI 启动和五组场景是不同证据；不以一个进程、端口或零测试退出码当作通过。
`kwin_check.py` 删除目标场景旧结果，再要求本次结果文件存在且 passed=true，并保留底层进程退出码和日志。
检查创建的是隔离 D-Bus/KWin 临时会话，测试后退出；不依赖快照保留进程。

## 已有执行证据

| 范围 | 可失败的检查 | 原始产物 |
| --- | --- | --- |
| 基础 CI | 模型竞争、错误恢复、目录分页、权限/重名/取消、回收站、磁盘满注入、应用目录/真实进程、设置持久化、UI 键盘与焦点 | `artifacts/tests.xml` |
| 通知协议 | 真实独立 D-Bus：Notify/替换/动作/关闭原因/超时/勿扰/服务冲突 | `tests/notification_scenario.py` 与测试报告 |
| 安装后启动 | 独立 KWin 中 CLI 创建原生表面、提交帧、窗口桥接和通知端点连接 | `artifacts/kwin/cli-startup/result.json` |
| KWin | 真窗口、面板角色/保留区、启动器界面启动、真实文件关联、通知表面、上下文菜单、窗口状态、崩溃移除 | 各场景的 `result.json` / `session.log` |
| 输出配置 | 100%、125%、150%、200%、125%+200%，验证合成器实际值及窗口实际 DPR；双输出移除/重连 | `artifacts/kwin/{one-100,two-125,two-150,two-200,mixed-125-200}/` |
| 基础应用 | 十进制运算；笔记重启不丢失；真实图片解码；媒体播放/暂停/静音状态；四种独立客户端；Konsole 真 PTY | pytest 与 KWin 场景报告 |
| OMEGA 参考 | 固定提交，真实 Chromium 加载、九种截图和操作 trace；外部资源使用系统 CA 验证的 HTTPS 传输并记录哈希 | `artifacts/reference/report.json`、截图、`trace.zip` |
| Matrix 外观 | 明确标记测试应用和文件的预览截图；原生菜单截图 | `artifacts/matrix/`、KWin 场景中的 `launcher.png` |
| 发行包 | wheel 构建后，在 checkout 外独立安装；确认导入路径与 QML/音效/KWin 资源，再运行两个实际入口 | `dist/`、`artifacts/wheel-install.json` |

截图工具生成的测试条目不是实现进度，Qt 媒体状态不是听感验收。
OMEGA 的资源加载保留 TLS 验证；没有关闭浏览器 Web 安全，也没有修改参考源码来让场景通过。
参考采集目前是截图和可回放 trace，尚无独立视频与完整人工设计签核。

## 仍不能关闭的验收

| 验收 | 现有能力 | 剩余条件 |
| --- | --- | --- |
| REF-01 / UX-01 | 固定参考、截图、主题、焦点、键盘、缩放 | 完整设计签核、读屏器、中文输入法、触屏与视觉 golden 回归 |
| APP-01 / CFG-01 | 真应用启动、持久化、云端交互 | 完整视觉 gate、音效实际输出及全部异常边界复核 |
| WIN-01 / DISPLAY-01 | 真窗口控制、原生层、双输出/缩放/虚拟重连 | 真实指针拖动/吸附、主屏切换与物理热插拔；当前控制脚本代替不了指针路径 |
| FILE-01 | 真实文件生命周期、关联打开、取消/错误 | 长时间/复杂文件系统负载及进一步边界；目录树复制尚未实现 |
| NOTIFY-01 | 真 D-Bus、原生通知层、勿扰和动作 | 完整可访问性与视觉 gate；焦点/激活行为的真实输入复核 |
| SYS-01 / APPS-01 | 真 proc/进程、四种应用及 Konsole | 电池/音量/网络管理后端、听感与完整使用体验复核 |
| PERF-01 | 统计工具、帧预算与协议 | 无 `/dev/dri`、无 Windows 基线，不能测真实 GPU/功耗/输入到光子或宣称不劣于 Windows |
| SESSION-01 | 可信服务锁定适配器，缺失服务拒绝宣称已锁定；重启模板 | 无系统总线、无可信锁屏/PAM 会话；systemd 用户管理器 offline，认证/恢复/升级回滚未验收 |
| STORE-01 | 用户 Flatpak 操作与错误/取消入口 | Flatpak 未安装，用户命名空间探测失败：`/proc/self/uid_map` 只读；未执行真实安装/运行/卸载 |
| 资源隔离 | slice 模板、后台限并发 | cgroup 不可写，权重与内存保护未启用，不能称资源隔离已验证 |
| EXTRA-01 | 保持独立扩展范围 | 天气/AI/游戏等尚未实现，不计入主线通过率 |

这些项保持 partial/planned，没有将未执行 gate 记为 passed。
`docs/acceptance.json` 的 verified 表示完整契约通过；基础测试数量增加不自动将完整契约变绿。
后续有对应系统能力时按原 ID 恢复验证，不需要重做已通过的无关步骤。

## 自动化边界

`development-gates` 自动运行基础检查和打包，`kwin-cloud` 自动运行普通用户下的临时 Debian/KWin 软件合成场景并上传产物。
提交 `287260ac1d61ced5cd7808aa1a4c7c2a662eef0c` 已完成远端执行：[基础测试/打包 passed](https://github.com/coooold/matrix/actions/runs/39057481765)、[KWin 云端矩阵 passed](https://github.com/coooold/matrix/actions/runs/39057481606)。基础测试为 40 项；KWin 包含独立 CLI 和五种输出配置，不是硬件帧预算数据。
干净 Debian CI 容器会移除 KWin 文件上的非必需 `CAP_SYS_NICE`，避免 Docker capability bounding set 导致 exec EPERM；没有增加容器权限或使用 privileged runner。
后续提交仍需查看对应 run；已通过记录不代表未来代码自动通过。wheel 独立安装与多屏隐藏面板回归由后续工作流继续检查。
仓库尚未自动设置分支保护、合并 PR、发布环境或安装默认登录会话。
