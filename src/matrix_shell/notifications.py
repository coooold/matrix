"""Freedesktop notification endpoint on a private asyncio bus thread."""
import asyncio
import threading
from dbus_next.aio import MessageBus
from dbus_next.constants import NameFlag, RequestNameReply
from dbus_next.service import ServiceInterface, method, signal
from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer


class NotificationInterface(ServiceInterface):
    def __init__(self, deliver):
        super().__init__('org.freedesktop.Notifications')
        self.deliver = deliver
        self.serial = 0
        self.active = set()

    @method()
    def GetCapabilities(self) -> 'as':
        return ['body', 'actions']

    @method()
    def GetServerInformation(self) -> 'ssss':
        return ['Matrix', 'Matrix project', '0.1.0', '1.2']

    @method()
    def Notify(self, app_name: 's', replaces_id: 'u', app_icon: 's', summary: 's', body: 's',
               actions: 'as', hints: 'a{sv}', expire_timeout: 'i') -> 'u':
        if replaces_id in self.active:
            ident = replaces_id
        else:
            self.serial += 1
            ident = self.serial
        self.active.add(ident)
        pairs = [{'key': actions[index], 'label': actions[index + 1]} for index in range(0, min(len(actions) - 1, 32), 2)]
        self.deliver({'id': ident, 'app': app_name[:256], 'summary': summary[:512], 'body': body[:8192],
                      'actions': pairs, 'timeout': expire_timeout, 'active': True})
        return ident

    @method()
    def CloseNotification(self, ident: 'u'):
        if ident in self.active:
            self.deliver({'close': ident, 'reason': 3})

    @signal()
    def NotificationClosed(self, ident, reason) -> 'uu':
        return [ident, reason]

    @signal()
    def ActionInvoked(self, ident, key) -> 'us':
        return [ident, key]


class BusRuntime:
    def __init__(self, deliver, status):
        self.deliver, self.status = deliver, status
        self.thread = None
        self.stop_requested = threading.Event()
        self.loop = self.stop_future = self.interface = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_requested.clear()
        self.thread = threading.Thread(target=self._thread, daemon=True)
        self.thread.start()

    def _thread(self):
        try:
            asyncio.run(self._serve())
        except Exception as error:
            self.status(False, str(error))
        finally:
            self.interface = None
            self.loop = None

    async def _serve(self):
        bus = await asyncio.wait_for(MessageBus().connect(), timeout=5)
        try:
            result = await bus.request_name('org.freedesktop.Notifications', NameFlag.DO_NOT_QUEUE)
            if result != RequestNameReply.PRIMARY_OWNER:
                raise RuntimeError('已有通知服务，Matrix 未接管服务')
            self.loop = asyncio.get_running_loop()
            self.stop_future = self.loop.create_future()
            self.interface = NotificationInterface(self.deliver)
            bus.export('/org/freedesktop/Notifications', self.interface)
            self.status(True, '')
            if not self.stop_requested.is_set():
                await self.stop_future
        finally:
            bus.disconnect()
            self.status(False, '')

    def closed(self, ident, reason):
        def emit():
            if self.interface and ident in self.interface.active:
                self.interface.active.remove(ident)
                self.interface.NotificationClosed(ident, reason)
        if self.loop:
            self.loop.call_soon_threadsafe(emit)

    def action(self, ident, key):
        def emit():
            if self.interface and ident in self.interface.active:
                self.interface.ActionInvoked(ident, key)
        if self.loop:
            self.loop.call_soon_threadsafe(emit)

    def stop(self):
        self.stop_requested.set()
        if self.loop and self.stop_future:
            def stop():
                if not self.stop_future.done():
                    self.stop_future.set_result(None)
            self.loop.call_soon_threadsafe(stop)
        if self.thread:
            self.thread.join(timeout=6)


class NotificationCenter(QObject):
    changed = Signal()
    notificationArrived = Signal()
    _message = Signal(object)
    _status = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.runtime = BusRuntime(self._message.emit, self._status.emit)
        self._message.connect(self._receive)
        self._status.connect(self._connected)
        self._entries = []
        self._latest = {}
        self._timers = {}
        self._dnd = False
        self._online = False
        self._error = ''

    @Property('QVariantList', notify=changed)
    def entries(self):
        return self._entries[:]

    @Property('QVariantMap', notify=changed)
    def latest(self):
        return self._latest

    @Property(bool, notify=changed)
    def online(self):
        return self._online

    @Property(bool, notify=changed)
    def doNotDisturb(self):
        return self._dnd

    @Property(str, notify=changed)
    def error(self):
        return self._error

    @Slot()
    def start(self):
        self._error = ''
        self.runtime.start()

    @Slot(bool, str)
    def _connected(self, online, error):
        self._online, self._error = online, error
        self.changed.emit()

    @Slot(bool)
    def setDoNotDisturb(self, value):
        self._dnd = value
        if value:
            self._latest = {}
        self.changed.emit()

    @Slot(object)
    def _receive(self, message):
        if 'close' in message:
            self.close(message['close'], message['reason'])
            return
        ident = message['id']
        self._entries = [message] + [entry for entry in self._entries if entry['id'] != ident]
        # Eviction also closes active notifications; no leaking IDs or timers.
        for entry in self._entries[100:]:
            self.close(entry['id'], 1)
        self._entries = self._entries[:100]
        if ident in self._timers:
            timer = self._timers.pop(ident)
            timer.stop()
            timer.deleteLater()
        timeout = message['timeout']
        if timeout != 0:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: self.close(ident, 1))
            timer.start(5000 if timeout < 0 else min(timeout, 86400000))
            self._timers[ident] = timer
        if not self._dnd:
            self._latest = message
            self.notificationArrived.emit()
        self.changed.emit()

    @Slot(int, int)
    def close(self, ident, reason=2):
        for entry in self._entries:
            if entry['id'] == ident:
                entry['active'] = False
        if ident in self._timers:
            timer = self._timers.pop(ident)
            timer.stop()
            timer.deleteLater()
        if self._latest.get('id') == ident:
            self._latest = {}
        self.runtime.closed(ident, reason)
        self.changed.emit()

    @Slot(int, str)
    def invokeAction(self, ident, key):
        entry = next((entry for entry in self._entries if entry['id'] == ident and entry['active']), None)
        if entry and any(action['key'] == key for action in entry['actions']):
            self.runtime.action(ident, key)
            self.close(ident, 2)

    @Slot()
    def clear(self):
        for entry in self._entries:
            if entry['active']:
                self.close(entry['id'], 2)
        self._entries = []
        self.changed.emit()

    def shutdown(self):
        self.runtime.stop()
