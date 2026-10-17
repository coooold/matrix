"""Read-only capability report; does not grant desktop-release acceptance."""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
from PySide6.QtCore import qVersion
import PySide6

ROOT = Path(__file__).resolve().parents[1]
report = {'platform': platform.platform(), 'python': platform.python_version(),
          'qt_client': qVersion(), 'pyside': PySide6.__version__,
          'gpu_device_present': Path('/dev/dri').exists(),
          'flatpak_binary': bool(shutil.which('flatpak')),
          'system_bus_socket': Path('/run/dbus/system_bus_socket').is_socket(),
          'cgroup_writable': os.access('/sys/fs/cgroup', os.W_OK),
          'windows_baseline': 'not available; user requested cloud-only development'}
if shutil.which('unshare'):
    probe = subprocess.run(['unshare', '-Ur', 'true'], capture_output=True, text=True, timeout=5)
    report['user_namespace_probe'] = {'available': probe.returncode == 0, 'diagnostic': probe.stderr.strip()}
prefix = ROOT / '.cache/kwin'
if (prefix / 'root/usr/bin/kwin_wayland').exists():
    env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen',
           'LD_LIBRARY_PATH': f'{prefix}/root/usr/lib/x86_64-linux-gnu:{prefix}/native-qt'}
    version = subprocess.run([str(prefix / 'root/usr/bin/kwin_wayland'), '--version'], env=env, capture_output=True, text=True, timeout=5)
    report['kwin'] = version.stdout.strip()
output = ROOT / 'artifacts/environment.json'
output.parent.mkdir(exist_ok=True)
output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(output.read_text())
