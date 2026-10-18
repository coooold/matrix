"""Keep PySide's Qt plugins separate from distro Qt private ABI plugins."""
import os
from pathlib import Path
import tempfile
from PySide6.QtCore import QLibraryInfo


def isolate_plugins(layer_shell=False):
    own = QLibraryInfo.path(QLibraryInfo.PluginsPath)
    temporary = tempfile.TemporaryDirectory(prefix='matrix-qt-plugins-')
    if layer_shell:
        roots = os.environ.get('QT_PLUGIN_PATH', '').split(':') + ['/usr/lib/x86_64-linux-gnu/qt6/plugins']
        candidate = next((Path(root) / 'wayland-shell-integration/liblayer-shell.so' for root in roots
                          if root and (Path(root) / 'wayland-shell-integration/liblayer-shell.so').exists()), None)
        if candidate is None:
            temporary.cleanup()
            raise RuntimeError('LayerShellQt 插件不可用；需要安装 layer-shell-qt')
        target = Path(temporary.name) / 'wayland-shell-integration'
        target.mkdir()
        (target / 'liblayer-shell.so').symlink_to(candidate.resolve())
    qml_root = Path(temporary.name) / 'qml'
    qml_root.mkdir()
    if layer_shell:
        roots = os.environ.get('QML_IMPORT_PATH', '').split(':') + ['/usr/lib/x86_64-linux-gnu/qt6/qml']
        module = next((Path(root) / 'org/kde/layershell' for root in roots
                       if root and (Path(root) / 'org/kde/layershell/qmldir').exists()), None)
        if module is None:
            temporary.cleanup()
            raise RuntimeError('LayerShellQt QML 模块不可用；需要 qml6-module-org-kde-layershell')
        target = qml_root / 'org/kde'
        target.mkdir(parents=True)
        (target / 'layershell').symlink_to(module.resolve())
    os.environ['QML_IMPORT_PATH'] = QLibraryInfo.path(QLibraryInfo.QmlImportsPath) + os.pathsep + str(qml_root)
    os.environ['QT_PLUGIN_PATH'] = own + os.pathsep + temporary.name
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(Path(own) / 'platforms')
    return temporary


def client_environment():
    environment = dict(os.environ)
    own_libraries = QLibraryInfo.path(QLibraryInfo.LibrariesPath)
    paths = [path for path in environment.get('LD_LIBRARY_PATH', '').split(':') if path and path != own_libraries]
    if paths:
        environment['LD_LIBRARY_PATH'] = ':'.join(paths)
    else:
        environment.pop('LD_LIBRARY_PATH', None)
    for name in ('QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 'QT_WAYLAND_SHELL_INTEGRATION', 'QML_IMPORT_PATH'):
        environment.pop(name, None)
    return environment
