"""Explicit user operations for trusted session lock and user Flatpak packages."""
import asyncio
import os
import re
import shutil
import subprocess
import threading
import time
from dbus_next import Message, MessageType
from dbus_next.aio import MessageBus
from PySide6.QtCore import QObject, Signal, Slot, Property
from .async_job import LatestWorker


async def lock_session():
    bus = await MessageBus().connect()
    async def call(member):
        reply = await asyncio.wait_for(bus.call(Message(destination='org.freedesktop.ScreenSaver',
            path='/ScreenSaver', interface='org.freedesktop.ScreenSaver', member=member)), timeout=5)
        if reply.message_type == MessageType.ERROR:
            raise RuntimeError('可信会话锁定服务不可用：' + str(reply.body))
        return reply.body
    try:
        await call('Lock')
        for _ in range(30):
            if (await call('GetActive')) == [True]:
                return '会话服务报告已锁定'
            await asyncio.sleep(.1)
        raise RuntimeError('会话服务未确认锁定，不能视为已锁屏')
    finally:
        bus.disconnect()


def flatpak_command(arguments, cancel=None, timeout=120):
    executable = shutil.which('flatpak')
    if not executable:
        raise RuntimeError('Flatpak 不可用；需在目标发行版安装受支持的 Flatpak 后端')
    process = subprocess.Popen([executable, '--user', *arguments], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    end = time.monotonic() + timeout
    while True:
        try:
            output, error = process.communicate(timeout=.1)
            break
        except subprocess.TimeoutExpired:
            if (cancel and cancel.is_set()) or time.monotonic() > end:
                process.terminate()
                try:
                    process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                raise RuntimeError('操作已取消或超时；请刷新实际安装状态')
    if process.returncode:
        raise RuntimeError(error.strip() or f'Flatpak 操作失败（{process.returncode}）')
    return output


def packages():
    output = flatpak_command(['list', '--app', '--columns=application,name,version'])
    return [dict(zip(('id', 'name', 'version'), (line.split('\t') + ['', ''])[:3])) for line in output.splitlines() if line.strip()]


class HostServices(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = LatestWorker(self)
        self.worker.changed.connect(self.changed)
        self.worker.completed.connect(self._loaded)
        self._entries = []
        self._message = ''
        self._cancel = threading.Event()

    @Property(bool, notify=changed)
    def busy(self):
        return self.worker.busy

    @Property(str, notify=changed)
    def message(self):
        return self.worker.error or self._message

    @Property('QVariantList', notify=changed)
    def entries(self):
        return self._entries

    @Slot(object)
    def _loaded(self, result):
        if isinstance(result, list):
            self._entries = result
            self._message = f'{len(result)} 个用户应用'
        else:
            self._message = str(result)
        self.changed.emit()

    @Slot()
    def lock(self):
        if not self.busy:
            self.worker.submit(lambda: asyncio.run(lock_session()))

    @Slot()
    def refreshPackages(self):
        if not self.busy:
            self.worker.submit(packages)

    @Slot(str, str)
    def install(self, remote, appid):
        if self.busy:
            return
        if not re.fullmatch(r'[A-Za-z0-9_-]+', remote) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*(\.[A-Za-z0-9_-]+){2,}', appid):
            self._message = '远端名称或应用 ID 无效'
            self.changed.emit()
            return
        self._cancel = threading.Event()
        def operation():
            remotes = flatpak_command(['remotes', '--columns=name']).splitlines()
            if remote not in remotes:
                raise RuntimeError('请先在目标系统配置受信任的 Flatpak 远端')
            flatpak_command(['install', '--noninteractive', '--assumeyes', remote, appid], self._cancel, 1800)
            return packages()
        self.worker.submit(operation)

    @Slot(str)
    def uninstall(self, appid):
        if self.busy or not any(entry['id'] == appid for entry in self._entries):
            return
        self._cancel = threading.Event()
        def operation():
            flatpak_command(['uninstall', '--noninteractive', '--assumeyes', appid], self._cancel, 120)
            return packages()
        self.worker.submit(operation)

    @Slot()
    def cancel(self):
        self._cancel.set()
