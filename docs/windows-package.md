# Windows 预览安装包

范围对应 UX-01、CFG-01、APPS-01：保留 Linux 的 Wayland/KWin 主线，在 Windows 10/11 x64 安装窗口化 Qt Quick 预览与四种基础客户端。Windows 包不提供 Linux 会话、KWin 窗口管理、Flatpak 或 freedesktop 通知服务。

验收场景：Given 干净的 Windows 云端 runner，When 构建并按当前用户静默安装，Then 安装目录中的程序实际创建 QML 窗口、提交帧，计算器与笔记可启动，中文笔记可重启读取；卸载后程序文件移除。安装包和 SHA256 上传 GitHub Actions。源码 checkout 不能代替安装目录运行。

构建使用 Windows 原生 Python/PySide、PyInstaller 与 Inno Setup，不在 Linux 上把 wheel 改名为 exe。不申请管理员权限，不替换 Explorer，不注册为默认桌面或文件关联。设置与笔记保留在用户数据目录，卸载不删除个人数据。

Windows 下显示的 Linux 专用功能明确不可用，不用模拟系统指标、假锁屏或假软件安装掩盖差异。安装包未进行代码签名，Windows 可能显示未知发布者提示。

## 本地重建

在 Windows x64 的仓库根目录使用 Python 3.12：

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-windows-build.txt
.venv/Scripts/python -m pip install --no-deps --no-build-isolation -e .
.venv/Scripts/python tools/windows_model_check.py
.venv/Scripts/python -m PyInstaller --noconfirm --clean packaging/windows/matrix.spec
```

CI 随后复制第三方说明和许可证，用 Inno Setup 6 生成按用户安装的 exe，并从独立安装目录运行 `tools/windows_smoke.py`。完整命令见 `.github/workflows/windows.yml`。Qt 使用可替换的动态库，Windows 音频使用 Media Foundation，不打包 FFmpeg 后端。验证产物随工作流上传，不能以构建成功代替安装后验证。

打包钩子只收集本界面所需的 QtCore/QtQml/QtQuick/QtMultimedia QML 模块，避免将未使用的 WebEngine、Charts、PDF、虚拟键盘等模块一并装入预览包。

## 按需上传

本次用户明确要求上传安装包；`upload-request.json` 固定已通过的 CI run、源码提交及安装器 SHA256。专用上传任务重新校验这些值、安装后报告和五个窗口的帧提交，再用 GitHub runner 的短期令牌上传预发行附件。只有显式变更该请求文件或手工触发才上传；普通源码提交、PR 和 fork PR 不触发发布。后续上传请求仍需用户授权，不自动发布 Linux 桌面或合并代码。
