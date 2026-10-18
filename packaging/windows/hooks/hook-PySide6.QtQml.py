"""Collect only QML runtime modules used by the preview and bundled clients."""
from PyInstaller.utils.hooks.qt import add_qt6_dependencies, pyside6_library_info

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
qml_binaries, qml_datas = pyside6_library_info.collect_qtqml_files()


def used_module(entry):
    destination = '/' + entry[1].replace('\\', '/') + '/'
    if '/qml/' not in destination:
        return False
    module = destination.split('/qml/', 1)[1].strip('/').split('/')
    if module[0] in {'QtCore', 'QtQml', 'QtMultimedia'}:
        return True
    if module[0] != 'QtQuick':
        return False
    return len(module) == 1 or module[1] in {
        'Controls', 'Templates', 'Layouts', 'Window', 'Dialogs', 'NativeStyle',
        'Shapes', 'Effects',
    }


binaries += [entry for entry in qml_binaries if used_module(entry)]
datas += [entry for entry in qml_datas if used_module(entry)]
