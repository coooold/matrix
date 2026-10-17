"""Real Wayland clients and KWin window-state actions; called by kwin_check.py."""
import json
import asyncio
from dbus_next import Message
from dbus_next.aio import MessageBus
import os
from pathlib import Path
import subprocess
import sys
import time
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl, QPointF, Qt, QCoreApplication, QEvent, QLibraryInfo, QObject
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from matrix_shell.backend import DesktopBackend
from matrix_shell.qt_runtime import isolate_plugins, client_environment
from register_apps import register, quote_exec

layer_session = os.environ.get('MATRIX_LAYER_SESSION') == '1'
plugins = isolate_plugins(layer_session)
app = QGuiApplication([])
app.setDesktopFileName('matrix-shell')
backend = DesktopBackend(config_dir=Path(os.environ['XDG_CONFIG_HOME']) / 'Matrix')
bridge = backend.windows
engine = QQmlApplicationEngine()
session = None
if layer_session:
    from matrix_shell.session import DesktopSession
    app.setQuitOnLastWindowClosed(False)
    session = DesktopSession(engine, backend)
    window = list(session.windows.values())[0][1]
else:
    engine.setInitialProperties({'backend': backend})
    engine.load(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / 'src/matrix_shell/qml/Main.qml')))
    window = engine.rootObjects()[0]
clients = []
checks = []
report = {'kind': 'KWin virtual output; software compositing; not hardware performance', 'checks': checks, 'passed': False,
          'outputs': int(os.environ.get('MATRIX_KWIN_OUTPUTS', '1')), 'scale': float(os.environ.get('MATRIX_KWIN_SCALE', '1'))}
result_path = Path(os.environ['MATRIX_KWIN_RESULT'])


def until(predicate, message, timeout=8):
    end = time.monotonic() + timeout
    while not predicate() and time.monotonic() < end:
        app.processEvents()
        time.sleep(.005)
    if not predicate():
        raise AssertionError(message + ': ' + bridge.error + ' entries=' + repr(bridge.entries))
    checks.append(message)


source = """
import sys
from PySide6.QtGui import QGuiApplication, QColor
from PySide6.QtQuick import QQuickWindow
from PySide6.QtCore import QTimer
app = QGuiApplication([])
app.setDesktopFileName('matrix-fixture-' + sys.argv[1])
window = QQuickWindow()
window.setTitle('Matrix Fixture ' + sys.argv[1])
window.resize(320, 240)
window.setColor(QColor('#123456'))
window.show()
QTimer.singleShot(35000, app.quit)
app.exec()
"""

try:
    bridge.start()
    until(lambda: bridge.online, 'KWin scripting bridge connected')
    until(lambda: bridge.environment.get('screens') == report['outputs'], 'Expected virtual outputs available')
    scales = {screen.name(): report['scale'] if index == 0 else float(os.environ['MATRIX_KWIN_SECOND_SCALE']) for index, screen in enumerate(app.screens())}
    report['requested_scales'] = scales
    def configure_outputs(arguments):
        doctor = Path(os.environ['MATRIX_KWIN_PREFIX']) / 'usr/bin/kscreen-doctor'
        doctor_env = client_environment()
        prefix = Path(os.environ['MATRIX_KWIN_PREFIX'])
        doctor_env['QT_PLUGIN_PATH'] = str(prefix / 'usr/lib/x86_64-linux-gnu/qt6/plugins') + ':/usr/lib/x86_64-linux-gnu/qt6/plugins'
        doctor_env['QT_QPA_PLATFORM'] = 'wayland'
        doctor_env['LD_LIBRARY_PATH'] = str(prefix / 'usr/lib/x86_64-linux-gnu') + ':' + str(prefix.parent / 'native-qt')
        configured = subprocess.run([str(doctor), *arguments], env=doctor_env, capture_output=True, text=True, timeout=10)
        if configured.returncode:
            raise AssertionError(configured.stderr + configured.stdout)
    if any(value != 1 for value in scales.values()):
        configure_outputs([f"output.{name}.scale.{scale}" for name, scale in scales.items()])
    until(lambda: all(abs(output['scale'] - scales[output['name']]) < .01 for output in bridge.environment.get('screenDetails', [])), 'Compositor reports requested output scales')
    if session:
        until(lambda: all(abs(surface.devicePixelRatio() - scales[screen.name()]) < .01 for screen, surfaces in session.windows.items() for surface in surfaces), 'Qt surfaces observe requested fractional pixel ratios')
    if session:
        fixture_dir = Path(os.environ['XDG_DATA_HOME']) / 'applications'
        fixture_dir.mkdir(parents=True, exist_ok=True)
        fixture_script = fixture_dir / 'client.py'
        fixture_script.write_text(source)
        fixture_desktop = fixture_dir / 'matrix-cloud.desktop'
        fixture_desktop.write_text(f'[Desktop Entry]\nType=Application\nName=Cloud Fixture\nExec=env {quote_exec('LD_LIBRARY_PATH=' + QLibraryInfo.path(QLibraryInfo.LibrariesPath))} "{sys.executable}" "{fixture_script}" launcher\n')
        register(fixture_dir.parent, Path(sys.executable).with_name('matrix-app'), Path(os.environ['MATRIX_KWIN_PREFIX']) / 'usr/bin/konsole')
        backend.applications.directories = [fixture_dir]
        start = window.findChild(QQuickItem, 'sessionStartButton')
        point = start.mapToScene(QPointF(start.width() / 2, start.height() / 2)).toPoint()
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
        popup = window.findChild(QObject, 'sessionLauncher')
        until(lambda: popup.property('visible') and not backend.applications.busy, 'Native panel application popup opened')
        def find_button(item):
            if item.objectName() == 'sessionApp-matrix-cloud.desktop':
                return item
            for child in item.childItems():
                found = find_button(child)
                if found:
                    return found
        until(lambda: find_button(popup.property('contentItem')) is not None, 'Native popup contains discovered desktop entry')
        button = find_button(popup.property('contentItem'))
        popup_window = button.window()
        until(lambda: popup_window.isVisible(), 'Launcher is a separate visible popup window')
        menu_panel = popup.findChild(QQuickItem, 'sessionLauncherPanel')
        report['popup_dimensions'] = {'requested': [popup.property('width'), popup.property('height')], 'actual': [popup_window.width(), popup_window.height()]}
        until(lambda: menu_panel.width() >= 300 and menu_panel.height() >= 300 and menu_panel.y() >= 0 and menu_panel.y() + menu_panel.height() <= popup_window.height(), 'Native menu content has its full unclipped size')
        assert popup_window.y() >= 0
        image = popup_window.grabWindow()
        image.save(str(result_path.parent / 'launcher.png'))
        position = button.mapToScene(QPointF(button.width()/2, button.height()/2)).toPoint()
        if report['scale'] == 1:
            QTest.keyClick(popup_window, Qt.Key_Return)
        else:
            QTest.mouseClick(popup_window, Qt.LeftButton, Qt.NoModifier, position)
        until(lambda: any(entry['appId'] == 'matrix-fixture-launcher' for entry in bridge.entries), 'Desktop entry launched a real Wayland client through panel UI')
        launched = next(entry['id'] for entry in bridge.entries if entry['appId'] == 'matrix-fixture-launcher')
        bridge.action(launched, 'close')
        until(lambda: not bridge.busy and not bridge.entries, 'Launched GUI client closed cleanly')
    if session:
        backend.notifications.start()
        until(lambda: backend.notifications.online, 'Native session notification endpoint connected')
        async def send_notification(summary):
            bus = await MessageBus().connect()
            try:
                reply = await bus.call(Message(destination='org.freedesktop.Notifications', path='/org/freedesktop/Notifications', interface='org.freedesktop.Notifications', member='Notify', signature='susssasa{sv}i', body=['Cloud fixture', 0, '', summary, 'Real DBus notification', [], {}, 0]))
                return reply.body[0]
            finally:
                bus.disconnect()
        notification_id = asyncio.run(send_notification('Native toast'))
        until(lambda: any(role.get('notification') for role in bridge.environment.get('roles', [])), 'Real notification layer surface visible')
        backend.notifications.setDoNotDisturb(True)
        until(lambda: not any(role.get('notification') for role in bridge.environment.get('roles', [])), 'Do not disturb hides native toast')
        asyncio.run(send_notification('History only'))
        until(lambda: len(backend.notifications.entries) == 2, 'DND retains notification history')
        assert backend.notifications.latest == {}
        backend.notifications.clear()
        backend.notifications.setDoNotDisturb(False)
        mime = Path(os.environ['XDG_CONFIG_HOME']) / 'mimeapps.list'
        mime.parent.mkdir(parents=True, exist_ok=True)
        mime.write_text('[Default Applications]\ntext/plain=org.matrixdesktop.notes.desktop;\n')
        target_file = mime.parent / 'open-test.txt'
        target_file.write_text('Real GIO file association')
        backend.fileBrowser.navigate(str(target_file.parent))
        until(lambda: not backend.fileBrowser.busy, 'File browser navigated actual directory')
        backend.fileBrowser.open(target_file.name)
        until(lambda: not backend.fileBrowser.busy, 'GIO file open dispatched')
        until(lambda: any(entry['appId'] == 'org.matrixdesktop.notes' for entry in bridge.entries), 'Real file association opens native note client')
        entry = next(entry['id'] for entry in bridge.entries if entry['appId'] == 'org.matrixdesktop.notes')
        bridge.action(entry, 'close')
        until(lambda: not bridge.busy and not bridge.entries, 'File handler closes cleanly')
        for kind in ('calculator', 'notes', 'image', 'music'):
            backend.applications.refresh()
            until(lambda: not backend.applications.busy, 'Core desktop entries refreshed ' + kind)
            backend.applications.launch('org.matrixdesktop.' + kind + '.desktop')
            until(lambda: not backend.applications.launching, 'Core app launch dispatched ' + kind)
            until(lambda: any(entry['appId'] == 'org.matrixdesktop.' + kind for entry in bridge.entries), 'Independent native core application ' + kind)
            entry = next(entry['id'] for entry in bridge.entries if entry['appId'] == 'org.matrixdesktop.' + kind)
            bridge.action(entry, 'close')
            until(lambda: not bridge.busy and not bridge.entries, 'Core application closes cleanly ' + kind)
        terminal = Path(os.environ['MATRIX_KWIN_PREFIX']) / 'usr/bin/konsole'
        terminal_env = client_environment()
        terminal_env['QT_PLUGIN_PATH'] = str(terminal.parents[2] / 'usr/lib/x86_64-linux-gnu/qt6/plugins') + ':/usr/lib/x86_64-linux-gnu/qt6/plugins'
        terminal_env['QT_QPA_PLATFORM'] = 'wayland'
        terminal_env['LD_LIBRARY_PATH'] = str(terminal.parents[2] / 'usr/lib/x86_64-linux-gnu') + ':' + str(terminal.parents[2].parent / 'native-qt')
        marker = result_path.parent / 'pty.txt'
        marker.unlink(missing_ok=True)
        command = f"import os,pathlib,time; assert os.isatty(0); pathlib.Path({str(marker)!r}).write_text('real PTY'); time.sleep(2)"
        process = subprocess.Popen([str(terminal), '--separate', '-e', sys.executable, '-c', command], env=terminal_env)
        clients.append(process)
        until(lambda: marker.exists(), 'Konsole executes command on a real PTY')
        until(lambda: any('konsole' in entry['appId'].lower() for entry in bridge.entries), 'Real Konsole Wayland window enumerated')
        until(lambda: process.poll() is not None and not bridge.entries, 'Terminal exits after its real command')
        clients.clear()
    for number in ('one', 'two'):
        client_env = client_environment()
        client_env['LD_LIBRARY_PATH'] = QLibraryInfo.path(QLibraryInfo.LibrariesPath)
        clients.append(subprocess.Popen([sys.executable, '-c', source, number], env=client_env))
    until(lambda: len(bridge.entries) == 2, 'Two real Wayland clients enumerated')
    if layer_session:
        until(lambda: sum(role['desktop'] for role in bridge.environment.get('roles', [])) == report['outputs'], 'Real background desktop role on every output')
        until(lambda: sum(role['dock'] and role['height'] == 72 for role in bridge.environment.get('roles', [])) == report['outputs'], 'Real layer-shell panel role on every output')
        until(lambda: all(abs(item['height'] - item['workHeight'] - 72) <= 1 for item in bridge.environment.get('screenDetails', [])) and bridge.environment.get('screens') == report['outputs'], '72 pixel panel exclusive zone on every output')
    target = next(row['id'] for row in bridge.entries if row['appId'] == 'matrix-fixture-one')
    task = window.findChild(QQuickItem, 'windowTask-' + target)
    if task is None:
        def find_task(item):
            if item.objectName() == 'windowTask-' + target:
                return item
            for child in item.childItems():
                result = find_task(child)
                if result:
                    return result
        until(lambda: find_task(window.contentItem()) is not None, 'Real window task button created')
        task = find_task(window.contentItem())
    point = task.mapToScene(QPointF(task.width() / 2, task.height() / 2)).toPoint()
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
    until(lambda: not bridge.busy, 'Taskbar button dispatched KWin action')
    def row():
        return next((row for row in bridge.entries if row['id'] == target), {})
    def action(operation, predicate, label):
        bridge.action(target, operation)
        until(lambda: not bridge.busy, label + ' command completed')
        if bridge.error:
            raise AssertionError(bridge.error)
        until(predicate, label)
    if session:
        QTest.mouseClick(window, Qt.RightButton, Qt.NoModifier, point)
        popup = window.findChild(QObject, 'sessionLauncher')
        menu = popup.findChild(QObject, 'sessionWindowMenu')
        until(lambda: menu.property('visible'), 'Native task context menu opened')
        item = popup.findChild(QQuickItem, 'windowMinimizeAction')
        position = item.mapToScene(QPointF(item.width()/2, item.height()/2)).toPoint()
        QTest.mouseClick(item.window(), Qt.LeftButton, Qt.NoModifier, position)
        until(lambda: row().get('minimized') and not bridge.busy, 'Context menu minimizes real client')
    action('activate', lambda: row().get('active'), 'Activate real client')
    action('minimize', lambda: row().get('minimized'), 'Minimize real client')
    action('activate', lambda: row().get('active') and not row().get('minimized'), 'Restore and focus real client')
    bounds = row()['workArea']
    action('maximize', lambda: abs(row().get('width', 0) - bounds['width']) <= 2, 'Maximize within virtual output')
    action('maximize', lambda: row().get('width', 0) < 600, 'Restore previous size')
    action('left', lambda: abs(row().get('x', 0) - bounds['x']) <= 2 and abs(row().get('width', 0) - bounds['width'] / 2) <= 2, 'KWin left tile')
    action('right', lambda: abs(row().get('x', 0) - bounds['x'] - bounds['width'] / 2) <= 2 and abs(row().get('width', 0) - bounds['width'] / 2) <= 2, 'KWin right tile')
    action('close', lambda: not row(), 'Close removes real client')
    clients[1].kill()
    until(lambda: not bridge.entries, 'Client crash removes task entry')
    if layer_session and report['outputs'] == 2:
        name = list(scales)[1]
        configure_outputs([f'output.{name}.disable'])
        until(lambda: bridge.environment.get('screens') == 1 and len(session.windows) == 1, 'Virtual output removal releases its surfaces')
        configure_outputs([f'output.{name}.enable'])
        until(lambda: bridge.environment.get('screens') == 2 and len(session.windows) == 2, 'Virtual output reconnect recreates desktop and panel')
        until(lambda: sum(role['dock'] for role in bridge.environment.get('roles', [])) == 2, 'Reconnected output has panel role')
    report['environment'] = bridge.environment
    report['passed'] = True
except BaseException as error:
    report['error'] = repr(error)
    report['environment'] = bridge.environment
    if session:
        report['client_surfaces'] = [{'ratio': surface.devicePixelRatio(), 'size': [surface.width(),surface.height()]} for surfaces in session.windows.values() for surface in surfaces]
    report['client_screens'] = [{'name': screen.name(), 'ratio': screen.devicePixelRatio(), 'geometry': [screen.geometry().width(), screen.geometry().height()]} for screen in app.screens()]
finally:
    backend.shutdown()
    if session:
        session.shutdown()
    else:
        window.close()
        window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    for client in clients:
        if client.poll() is None:
            client.terminate()
        client.wait(timeout=5)
    result_path.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
sys.exit(0 if report['passed'] else 1)
