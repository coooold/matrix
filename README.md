# Matrix

面向 Linux 的桌面项目：**Wayland + KWin + Qt Quick/QML**。
以 OMEGA-OS 的功能与视觉层次为体验基准，以同机 Windows 的帧稳定性和输入延迟为性能验收基准。

已实现窗口化开发预览，以及可在隔离 KWin 会话运行的原生桌面层、面板和任务栏。
云端使用虚拟输出与软件合成验证功能；完整发布验收尚未完成，详情见 [迭代证据与缺口](docs/cloud-validation.md)。

## 已有能力

- XDG `.desktop` 应用发现、名称/类别过滤、GIO 启动、刷新及失败反馈。
- KWin 真实窗口枚举、激活、最小化/恢复、最大化、左右贴靠、关闭和崩溃后移除。
- LayerShellQt 背景层、面板保留区、每屏桌面/面板、虚拟输出重连与分数缩放。
- 文件分页、目录导航、新建、文件复制/取消、GIO 打开和可恢复回收站。
- 主题、提示音、减少动态效果、低特效配置的原子保存与错误回退。
- freedesktop D-Bus 通知、替换、动作、超时、勿扰、历史和原生通知层。
- 真实 CPU/内存/当前用户进程状态及带身份校验的进程结束操作。
- 独立 Qt 计算器、笔记、图片、音频客户端；终端集成成熟的 Konsole。
- 可信会话锁定及用户 Flatpak 操作入口；缺失服务时明确报错，不显示模拟成功。

## 基础开发与检查

Windows 可运行独立的 **桌面预览安装包**；它不安装 Linux 或替换 Explorer。构建、功能范围与安装验证见 [Windows 打包说明](docs/windows-package.md)，安装包由 `windows-installer` 工作流上传至 GitHub。

需要 Linux、Python 3.11+、venv、GIO、D-Bus，以及 Qt 的 EGL/OpenGL/xkbcommon 运行库。
当前验证工具链：PySide/Qt 6.8.3；云端 KWin/LayerShellQt 版本记录在验证报告中。

```sh
./tools/setup.sh
./tools/check.sh
.venv/bin/python -m pip wheel --no-deps --no-build-isolation . -w dist
.venv/bin/python tools/wheel_check.py dist/matrix_shell-0.1.0-py3-none-any.whl
```

在已有 Wayland 会话打开开发预览；`--kwin` 显式启用 KWin 窗口桥接：

```sh
QT_QPA_PLATFORM=wayland .venv/bin/matrix-shell --kwin
```

无显示服务时：

```sh
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/matrix-shell --smoke --config-dir .cache/profile
```

预览中“开始”打开真实应用列表，“文件”打开目录；Ctrl+Space、方向键、Tab、Enter、Esc 可操作。
文件列表按“更多”继续加载；文件操作不会覆盖已有目标，删除先确认并移入回收站。
文件名过滤仅覆盖已加载页，不是全盘索引；复制目前支持普通文件，不支持目录树复制。

## 云端原生会话验收

以下脚本已在当前 Debian 13 amd64 镜像验证；下载 Debian 签名索引中的运行包到仓库忽略的缓存，不安装系统包、不替换登录会话。
依赖镜像已有的 Qt/KDE 基础库；其他发行版应使用其包管理器提供匹配的运行时。

```sh
./tools/prepare_kwin.sh
.venv/bin/python tools/cloud_check.py
```

会启动并退出独立 D-Bus/KWin，会话与用户配置均放在临时目录。
验证安装后的 CLI、单/双虚拟输出、100%/125%/150%/200% 和混合缩放、虚拟输出移除/重连。
结果保存在 `artifacts/kwin/<场景>/`，包含原始结果、日志与界面截图。
GitHub Actions `kwin-cloud` 在临时 Debian 容器以普通用户执行同一矩阵，不使用特权 GPU runner。

`--session` 创建真实 LayerShellQt 表面，仅在隔离的 KWin 会话中显式使用；需要 `layer-shell-qt` 和 `qml6-module-org-kde-layershell`。
它不安装登录项，不提供安全锁屏替代品，也不应直接叠加到用户正在使用的 Plasma 桌面。
`--notifications` 仅申请无人占用的通知服务名称，已有服务时拒绝接管。

## 基础应用

```sh
.venv/bin/matrix-app calculator
.venv/bin/matrix-app notes --file /path/to/note.txt
.venv/bin/matrix-app image --file /path/to/image.png
.venv/bin/matrix-app music --file /path/to/audio.wav
.venv/bin/python tools/register_apps.py --data-dir .cache/desktop-data --konsole .cache/kwin/root/usr/bin/konsole
```

注册只写指定数据目录中的 Matrix 管理条目，不覆盖其他条目，也不改用户默认文件关联。
将该数据目录加入 `XDG_DATA_DIRS` 后，启动器可以发现这些客户端。
笔记最多加载 2 MiB；计算器支持 34 位有效数字的十进制四则运算。音频无输出设备时只能验证解码/播放状态，不能验收听感。
Flatpak 页面只管理用户安装，使用已有可信远端及默认签名/TLS 校验；不会自动添加软件源。

## 流程与证据

- [OMEGA-OS 基准与验收驱动流程](docs/omega-development-workflow.md)
- [结构化验收清单](docs/acceptance.json)：`python3 tools/acceptance_report.py`
- [云端验证与剩余缺口](docs/cloud-validation.md)
- [架构](docs/architecture.md) · [性能协议](docs/performance.md) · [开发约定](AGENTS.md)

可选参考采集：`.venv/bin/python -m pip install -r requirements-reference.txt` 后，用 `tools/capture_reference.py <固定提交的外部检出>` 生成 OMEGA 截图与 trace。
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software .venv/bin/python tools/capture_matrix.py` 生成明确标记测试数据的预览截图。
