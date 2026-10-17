"""Opt-in KWin scripting bridge. Only the compositor may publish window state."""
import asyncio
import json
from pathlib import Path
import tempfile
import threading
import uuid
from dbus_next import Message, MessageType
from dbus_next.aio import MessageBus
from dbus_next.constants import NameFlag, RequestNameReply
from dbus_next.service import ServiceInterface, method
from PySide6.QtCore import QObject, Signal, Slot, Property

SERVICE = 'org.matrixdesktop.Shell1'
PATH = '/org/matrixdesktop/Shell1'
OPERATIONS = {
    'activate': 'w.minimized = false; workspace.activeWindow = w;',
    'minimize': 'w.minimized = true;',
    'maximize': 'workspace.activeWindow = w; workspace.slotWindowMaximize();',
    'left': 'workspace.activeWindow = w; workspace.slotWindowQuickTileLeft();',
    'right': 'workspace.activeWindow = w; workspace.slotWindowQuickTileRight();',
    'close': 'w.closeWindow();',
}


class BridgeInterface(ServiceInterface):
    def __init__(self, publish, complete, environment):
        super().__init__(SERVICE)
        self.publish, self.complete, self.environment = publish, complete, environment

    @method()
    def Publish(self, snapshot: 's'):
        self.publish(json.loads(snapshot))

    @method()
    def Environment(self, snapshot: 's'):
        self.environment(json.loads(snapshot))

    @method()
    def Complete(self, token: 's', error: 's'):
        self.complete(token, error)


class KWinBridge(QObject):
    changed = Signal()
    _snapshot = Signal(object)
    _environment = Signal(object)
    _status = Signal(bool, str)
    _action_done = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries = []
        self._details = {}
        self._online = False
        self._error = ''
        self._busy = False
        self._thread = None
        self._loop = None
        self._bus = None
        self._stop = None
        self._stop_requested = threading.Event()
        self._completions = {}
        self._snapshot.connect(self._received)
        self._environment.connect(self._received_environment)
        self._status.connect(self._connected)
        self._action_done.connect(self._finished)

    @Property('QVariantMap', notify=changed)
    def environment(self):
        return self._details

    @Slot(object)
    def _received_environment(self, value):
        self._details = value
        self.changed.emit()

    @Property('QVariantList', notify=changed)
    def entries(self):
        return self._entries[:]

    @Property(bool, notify=changed)
    def online(self):
        return self._online

    @Property(bool, notify=changed)
    def busy(self):
        return self._busy

    @Property(str, notify=changed)
    def error(self):
        return self._error

    @Slot(object)
    def _received(self, snapshot):
        self._entries = snapshot
        self.changed.emit()

    @Slot(bool, str)
    def _connected(self, online, error):
        self._online, self._error = online, error
        if not online:
            self._entries = []
        self.changed.emit()

    @Slot(str)
    def _finished(self, error):
        self._busy = False
        self._error = error
        self.changed.emit()

    @Slot()
    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_requested.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            asyncio.run(self._serve())
        except Exception as error:
            self._status.emit(False, str(error))
        finally:
            self._loop = self._bus = None

    async def _call(self, destination, path, interface, member, signature='', body=None):
        reply = await asyncio.wait_for(self._bus.call(Message(destination=destination, path=path,
            interface=interface, member=member, signature=signature, body=body or [])), timeout=5)
        if reply.message_type == MessageType.ERROR:
            raise RuntimeError(str(reply.body))
        return reply.body

    async def _serve(self):
        self._bus = await asyncio.wait_for(MessageBus().connect(), timeout=5)
        monitor_name = 'matrix-monitor-' + uuid.uuid4().hex
        try:
            owner = (await self._call('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus', 'GetNameOwner', 's', ['org.kde.KWin']))[0]
            def authorize(message):
                if message.path == PATH and message.message_type == MessageType.METHOD_CALL and message.sender != owner:
                    return Message.new_error(message, 'org.freedesktop.DBus.Error.AccessDenied', 'Only KWin may publish desktop state')
            self._bus.add_message_handler(authorize)
            if await self._bus.request_name(SERVICE, NameFlag.DO_NOT_QUEUE) != RequestNameReply.PRIMARY_OWNER:
                raise RuntimeError('已有 Matrix 窗口桥接服务')
            def complete(token, error):
                future = self._completions.get(token)
                if future and not future.done():
                    future.set_result(error)
            self._bus.export(PATH, BridgeInterface(self._snapshot.emit, complete, self._environment.emit))
            self._loop = asyncio.get_running_loop()
            self._stop = self._loop.create_future()
            monitor = Path(__file__).parent / 'kwin/monitor.js'
            script = (await self._call('org.kde.KWin', '/Scripting', 'org.kde.kwin.Scripting', 'loadScript', 'ss', [str(monitor), monitor_name]))[0]
            if script < 0:
                raise RuntimeError('KWin 无法加载窗口状态脚本')
            await self._call('org.kde.KWin', f'/Scripting/Script{script}', 'org.kde.kwin.Script', 'run')
            self._status.emit(True, '')
            if not self._stop_requested.is_set():
                await self._stop
        finally:
            try:
                await self._call('org.kde.KWin', '/Scripting', 'org.kde.kwin.Scripting', 'unloadScript', 's', [monitor_name])
            except Exception:
                pass
            self._bus.disconnect()
            self._status.emit(False, '')

    @Slot(str, str)
    def action(self, ident, operation):
        if not self._online or self._busy or operation not in OPERATIONS:
            return
        if not any(entry['id'] == ident for entry in self._entries):
            self._error = '窗口已不可用'
            self.changed.emit()
            return
        self._busy = True
        self.changed.emit()
        future = asyncio.run_coroutine_threadsafe(self._perform(ident, operation), self._loop)
        def done(result):
            try:
                self._action_done.emit(result.result())
            except Exception as error:
                self._action_done.emit(str(error))
        future.add_done_callback(done)

    async def _perform(self, ident, operation):
        token = uuid.uuid4().hex
        name = 'matrix-action-' + token
        future = self._loop.create_future()
        self._completions[token] = future
        source = f'''let error = "";
try {{
    const w = workspace.windowList().find(w => w.internalId.toString() === {json.dumps(ident)});
    if (!w) throw new Error("window unavailable");
    {OPERATIONS[operation]}
}} catch (failure) {{ error = String(failure); }}
callDBus("{SERVICE}", "{PATH}", "{SERVICE}", "Complete", "{token}", error);
'''
        # JSON escaping and a fixed operation table prevent source injection.
        with tempfile.TemporaryDirectory(prefix='matrix-kwin-') as directory:
            script_path = Path(directory) / 'action.js'
            script_path.write_text(source)
            try:
                script = (await self._call('org.kde.KWin', '/Scripting', 'org.kde.kwin.Scripting', 'loadScript', 'ss', [str(script_path), name]))[0]
                if script < 0:
                    raise RuntimeError('无法加载窗口控制脚本')
                await self._call('org.kde.KWin', f'/Scripting/Script{script}', 'org.kde.kwin.Script', 'run')
                return await asyncio.wait_for(future, timeout=5)
            finally:
                self._completions.pop(token, None)
                await self._call('org.kde.KWin', '/Scripting', 'org.kde.kwin.Scripting', 'unloadScript', 's', [name])

    def shutdown(self):
        self._stop_requested.set()
        if self._loop and self._stop:
            self._loop.call_soon_threadsafe(lambda: self._stop.set_result(None) if not self._stop.done() else None)
        if self._thread:
            self._thread.join(timeout=7)
