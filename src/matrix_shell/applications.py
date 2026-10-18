"""XDG desktop entry discovery; execution is delegated to GIO, never a shell."""
import configparser
import locale
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer
from .async_job import LatestWorker
from .qt_runtime import client_environment


def application_directories():
    home = Path(os.environ.get('XDG_DATA_HOME') or str(Path.home() / '.local/share'))
    if not home.is_absolute():
        home = Path.home() / '.local/share'
    system = [Path(p) for p in (os.environ.get('XDG_DATA_DIRS') or '/usr/local/share:/usr/share').split(':') if p]
    directories = [p / 'applications' for p in [home, *system] if p.is_absolute()]
    directories.extend([home / 'flatpak/exports/share/applications', Path('/var/lib/flatpak/exports/share/applications')])
    return list(dict.fromkeys(directories))


def localized_name(section, language):
    language = language.split('.')[0]
    for key in (f'Name[{language}]', f'Name[{language.split("_")[0]}]', 'Name'):
        if section.get(key):
            return section[key].strip()
    return ''


def discover(directories, desktop, language):
    seen, apps = set(), []
    desktops = set(desktop.split(':'))
    for directory in directories:
        if not directory.exists():
            continue
        for path in sorted(directory.rglob('*.desktop')):
            ident = str(path.relative_to(directory)).replace('/', '-')
            if ident in seen:
                continue
            # Higher-priority Hidden entries mask lower-priority copies.
            seen.add(ident)
            parser = configparser.ConfigParser(interpolation=None, strict=False)
            parser.optionxform = str
            try:
                if path.stat().st_size > 256 * 1024:
                    continue
                parser.read_string(path.read_text(encoding='utf-8'))
                section = parser['Desktop Entry']
                if section.get('Type') != 'Application' or not (section.get('Exec') or section.getboolean('DBusActivatable', fallback=False)):
                    continue
                if section.getboolean('Hidden', fallback=False) or section.getboolean('NoDisplay', fallback=False):
                    continue
                only = set(filter(None, section.get('OnlyShowIn', '').split(';')))
                excluded = set(filter(None, section.get('NotShowIn', '').split(';')))
                if (only and not only.intersection(desktops)) or excluded.intersection(desktops):
                    continue
                executable = section.get('TryExec')
                if executable and not shutil.which(executable):
                    continue
                name = localized_name(section, language)
                if not name:
                    continue
                apps.append({'id': ident, 'name': name, 'categories': section.get('Categories', ''),
                             'path': str(path.resolve()), 'terminal': section.getboolean('Terminal', fallback=False)})
            except (OSError, ValueError, configparser.Error, KeyError):
                continue
    return sorted(apps, key=lambda item: (item['name'].casefold(), item['id']))


def launch_gio(operation, target):
    # GUI children may retain their stderr. A regular temporary file allows us
    # to wait for GIO itself without waiting for the entire GUI process lifetime.
    log_directory = os.environ.get('MATRIX_LAUNCH_LOG_DIR')
    if log_directory:
        Path(log_directory).mkdir(mode=0o700, parents=True, exist_ok=True)
    log_factory = (lambda: tempfile.NamedTemporaryFile(mode='w+t', prefix='gio-', suffix='.log', dir=log_directory, delete=False)) if log_directory else (lambda: tempfile.TemporaryFile(mode='w+t'))
    with log_factory() as error_log:
        result = subprocess.run(['gio', operation, str(target)], env=client_environment(),
                                stdout=subprocess.DEVNULL, stderr=error_log, timeout=15)
        if result.returncode:
            error_log.seek(0)
            raise RuntimeError(error_log.read(16384).strip() or '无法启动应用')


class ApplicationCatalog(QObject):
    changed = Signal()
    launched = Signal(str)

    def __init__(self, parent=None, directories=None, desktop=None, language=None):
        super().__init__(parent)
        self.directories = list(directories) if directories is not None else application_directories()
        self.desktop = desktop if desktop is not None else os.environ.get('XDG_CURRENT_DESKTOP', 'Matrix:KDE')
        self.language = language or locale.getlocale()[0] or 'en_US'
        self.worker = LatestWorker(self)
        self.worker.changed.connect(self.changed)
        self.worker.completed.connect(self._loaded)
        self.launcher = LatestWorker(self)
        self.launcher.changed.connect(self.changed)
        self.launcher.completed.connect(self._launched)
        self._entries = []
        self._query = ''
        self._launch_error = ''
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.refresh)

    @Slot(object)
    def _launched(self, ident):
        self.launched.emit(str(ident))

    @Property('QVariantList', notify=changed)
    def entries(self):
        return self._entries

    @Property(bool, notify=changed)
    def busy(self):
        return self.worker.busy or self.timer.isActive()

    @Property(bool, notify=changed)
    def launching(self):
        return self.launcher.busy

    @Property(str, notify=changed)
    def error(self):
        return self._launch_error or self.launcher.error or self.worker.error

    @Slot(str)
    def setQuery(self, query):
        self.worker.invalidate()
        self._query = query[:256].casefold()
        self.timer.start()
        self.changed.emit()

    @Slot()
    def refresh(self):
        query = self._query
        directories, desktop, language = self.directories[:], self.desktop, self.language
        self.worker.submit(lambda: [app for app in discover(directories, desktop, language)
                                   if query in (app['name'] + ' ' + app['categories']).casefold()])

    @Slot(object)
    def _loaded(self, entries):
        self._entries = entries
        self.changed.emit()

    @Slot(str)
    def launch(self, ident):
        if self.launcher.busy:
            return
        # Only launch entries present in the displayed discovery snapshot.
        entry = next((app for app in self._entries if app['id'] == ident), None)
        self._launch_error = ''
        if entry is None:
            self._launch_error = '应用已不可用，请刷新列表'
            self.changed.emit()
            return
        path = entry['path']

        def execute():
            launch_gio('launch', path)
            return ident

        self.launcher.submit(execute)
