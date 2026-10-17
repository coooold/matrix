import os
from pathlib import Path
import subprocess
import sys


def test_real_image_decode_and_media_play_pause_mute(tmp_path):
    script = r'''
import sys, time, wave
from pathlib import Path
from PySide6.QtCore import QObject, QUrl, QMetaObject, QCoreApplication, QEvent
from PySide6.QtGui import QGuiApplication, QImage, QColor
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtMultimedia import QMediaPlayer
from matrix_shell.core_apps import CoreModel
from matrix_shell.qt_runtime import isolate_plugins
import matrix_shell.core_apps as module
plugins = isolate_plugins()
app = QGuiApplication([])
fixture = Path(sys.argv[1])
image = QImage(4, 3, QImage.Format_RGB32)
image.fill(QColor('blue'))
image.save(str(fixture / 'image.png'))
with wave.open(str(fixture / 'sample.wav'), 'wb') as stream:
    stream.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
    stream.writeframes(bytes(22050 * 2 * 3))
def wait(predicate):
    end = time.monotonic() + 6
    while not predicate() and time.monotonic() < end:
        app.processEvents()
        time.sleep(.005)
    assert predicate()
for kind, name in [('image', 'image.png'), ('music', 'sample.wav')]:
    model = CoreModel(kind, fixture / name)
    engine = QQmlApplicationEngine()
    engine.setInitialProperties({'model': model})
    engine.load(QUrl.fromLocalFile(str(Path(module.__file__).parent / 'qml/CoreApp.qml')))
    assert engine.rootObjects()
    window = engine.rootObjects()[0]
    if kind == 'image':
        wait(lambda: window.property('imageReady'))
        assert window.property('imageWidth') == 4
    else:
        wait(lambda: window.property('mediaDurationMs') == 3000)
        player = window.findChild(QObject, 'mediaPlayer')
        QMetaObject.invokeMethod(player, 'play')
        wait(lambda: window.property('mediaPlaying'))
        QMetaObject.invokeMethod(player, 'pause')
        wait(lambda: window.property('mediaPaused'))
        window.findChild(QObject, 'audioOutput').setProperty('muted', True)
        assert window.property('mediaMuted')
    model.shutdown()
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
'''
    result = subprocess.run([sys.executable, '-c', script, str(tmp_path)],
                            env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
                            capture_output=True, text=True, timeout=18)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'TypeError' not in result.stderr
    assert 'ReferenceError' not in result.stderr
