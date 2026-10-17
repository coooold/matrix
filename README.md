# Matrix

面向 Linux 的桌面体验项目：**Wayland + KWin + Qt Quick/QML**。
目标是用可测量的交互延迟、帧稳定性与视觉一致性，达到同机 Windows 桌面的体验水平。

当前为可运行的窗口化桌面壳原型：背景、面板、菜单、异步主目录列表与文件名筛选。
视觉颜色与间距集中在 `Theme.qml`，交互控件提供焦点样式和可访问名称。
尚未实现 KWin 桌面角色、真实任务栏、应用启动器、窗口管理、锁屏或登录会话；不要将此预览安装为默认桌面。

## 原型操作

- 点击“开始”或按 Ctrl+Space 打开/关闭菜单（仅当前窗口内的快捷键）。
- 输入文件名进行大小写不敏感的筛选；只搜索当前枚举的前 200 项，不递归扫描磁盘。
- 在搜索框按 ↓ 进入列表，↑/↓ 移动选择；第一项再按 ↑ 返回搜索框。
- Tab 切换控件；Esc 或点击菜单外部关闭菜单，焦点回到“开始”。
- 列表目前仅选择和预览名称，不会打开文件；“文件”按钮打开同一个目录预览。

## 开发

需要 Linux、Python 3.11+、venv，以及 Qt 所需 EGL/OpenGL/xkbcommon 运行库。

```sh
./tools/setup.sh
./tools/check.sh
.venv/bin/matrix-shell
```

在现有 KWin Wayland 会话内可显式使用：

```sh
QT_QPA_PLATFORM=wayland .venv/bin/matrix-shell
```

无显示服务的 CI 使用 offscreen，仅证明 QML 加载和帧提交，不证明 KWin 或 GPU 性能。
运行测试后可构建发行包：`.venv/bin/python -m pip wheel --no-deps --no-build-isolation . -w dist`。

- [架构与迭代路线](docs/architecture.md)
- [帧预算、负载与 Windows 对照验收](docs/performance.md)
- [自动开发约定](AGENTS.md)

无需账号、API 密钥或外部服务。安装依赖访问 PyPI；CI 由 GitHub Actions 执行。
