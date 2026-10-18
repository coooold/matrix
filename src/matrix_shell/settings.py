"""Versioned, validated settings persisted atomically outside the GUI thread."""
import json
import os
from pathlib import Path
import tempfile
from PySide6.QtCore import QObject, Signal, Slot, Property, QStandardPaths
from .async_job import LatestWorker

DEFAULTS = {'version': 1, 'accent': '#00d9e8', 'sound': False, 'reducedMotion': False, 'lowEffects': True}
ACCENTS = {'#00d9e8', '#b99aff', '#91caff'}


def read_settings(path):
    if not path.exists():
        return dict(DEFAULTS), ''
    try:
        if path.stat().st_size > 16384:
            raise ValueError('配置文件过大')
        data = json.loads(path.read_text())
        if not isinstance(data, dict) or data.get('version') != 1:
            raise ValueError('不支持的配置版本')
        if data.get('accent') not in ACCENTS or any(type(data.get(k)) is not bool for k in ('sound', 'reducedMotion', 'lowEffects')):
            raise ValueError('配置字段无效')
        return {key: data[key] for key in DEFAULTS}, ''
    except (OSError, ValueError, TypeError) as error:
        return dict(DEFAULTS), f'已回退默认设置：{error}'


def write_settings(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.settings-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(values, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return dict(values)


class Settings(QObject):
    changed = Signal()

    def __init__(self, parent=None, directory=None):
        super().__init__(parent)
        self.path = Path(directory or QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)) / 'settings.json'
        self.worker = LatestWorker(self)
        self.worker.changed.connect(self.changed)
        self.worker.completed.connect(self._loaded)
        self._values = dict(DEFAULTS)
        self._warning = ''
        self._ready = False
        self.worker.submit(lambda: read_settings(self.path))

    @Property('QVariantMap', notify=changed)
    def values(self):
        return dict(self._values)

    @Property(bool, notify=changed)
    def ready(self):
        return self._ready

    @Property(bool, notify=changed)
    def busy(self):
        return self.worker.busy

    @Property(str, notify=changed)
    def error(self):
        return self.worker.error or self._warning

    @Slot(object)
    def _loaded(self, result):
        if isinstance(result, tuple):
            self._values, self._warning = result
        else:
            self._values, self._warning = result, ''
        self._ready = True
        self.changed.emit()

    @Slot(str, 'QVariant')
    def setValue(self, key, value):
        if not self._ready:
            return
        if key == 'accent':
            if value not in ACCENTS:
                return
        elif key not in ('sound', 'reducedMotion', 'lowEffects') or type(value) is not bool:
            return
        self._values = {**self._values, key: value}
        snapshot = dict(self._values)
        self.worker.submit(lambda: write_settings(self.path, snapshot))
        self.changed.emit()

    @Slot()
    def reset(self):
        if not self._ready:
            return
        self._values = dict(DEFAULTS)
        snapshot = dict(self._values)
        self.worker.submit(lambda: write_settings(self.path, snapshot))
        self.changed.emit()
