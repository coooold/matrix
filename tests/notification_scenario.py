"""Run under dbus-run-session: real wire protocol, no system notification takeover."""
import asyncio
import sys
import threading
import time
from pathlib import Path
from dbus_next.aio import MessageBus
from PySide6.QtCore import QCoreApplication, QTimer
from matrix_shell.notifications import NotificationCenter

app = QCoreApplication([])
center = NotificationCenter()
results, errors = [], []


def client_thread():
    async def test():
        bus = await MessageBus().connect()
        try:
            introspection = await bus.introspect('org.freedesktop.Notifications', '/org/freedesktop/Notifications')
            proxy = bus.get_proxy_object('org.freedesktop.Notifications', '/org/freedesktop/Notifications', introspection)
            interface = proxy.get_interface('org.freedesktop.Notifications')
            assert (await interface.call_get_server_information())[0] == 'Matrix'
            assert 'actions' in await interface.call_get_capabilities()
            closed, actions = [], []
            interface.on_notification_closed(lambda ident, reason: closed.append((ident, reason)))
            interface.on_action_invoked(lambda ident, key: actions.append((ident, key)))
            ident = await interface.call_notify('Fixture', 0, '', 'One', 'Body', ['open', 'Open'], {}, 0)
            replaced = await interface.call_notify('Fixture', ident, '', 'Updated', 'Body', ['open', 'Open'], {}, 0)
            assert replaced == ident
            results.append(('action', ident))
            end = time.monotonic() + 5
            while not actions and time.monotonic() < end:
                await asyncio.sleep(.01)
            assert actions == [(ident, 'open')]
            assert closed == [(ident, 2)]
            ident2 = await interface.call_notify('Fixture', 0, '', 'Close', 'Body', [], {}, 0)
            await interface.call_close_notification(ident2)
            end = time.monotonic() + 5
            while (ident2, 3) not in closed and time.monotonic() < end:
                await asyncio.sleep(.01)
            assert (ident2, 3) in closed
            ident3 = await interface.call_notify('Fixture', 0, '', 'Expire', 'Body', [], {}, 50)
            end = time.monotonic() + 5
            while (ident3, 1) not in closed and time.monotonic() < end:
                await asyncio.sleep(.01)
            assert (ident3, 1) in closed
            results.append(('done', None))
        finally:
            bus.disconnect()
    try:
        asyncio.run(test())
    except BaseException as error:
        errors.append(repr(error))
        results.append(('done', None))


thread = None
conflict = NotificationCenter()
handled = set()


def poll():
    global thread
    if center.online and thread is None:
        center.setDoNotDisturb(True)
        thread = threading.Thread(target=client_thread)
        thread.start()
        conflict.start()
    for kind, ident in results[:]:
        if kind == 'action' and ident not in handled:
            entry = next((row for row in center.entries if row['id'] == ident), None)
            if entry and entry['summary'] == 'Updated':
                assert center.latest == {}, 'DND must suppress popups'
                center.invokeAction(ident, 'open')
                handled.add(ident)
        if kind == 'done':
            assert conflict.error and not conflict.online
            assert len(center.entries) == 3
            center.clear()
            assert center.entries == []
            app.exit(1 if errors else 0)


center.start()
timer = QTimer()
timer.setInterval(10)
timer.timeout.connect(poll)
timer.start()
QTimer.singleShot(12000, lambda: app.exit(2))
code = app.exec()
center.shutdown()
conflict.shutdown()
if thread:
    thread.join(timeout=2)
print('DBus notification scenarios:', errors or 'passed')
sys.exit(code)
