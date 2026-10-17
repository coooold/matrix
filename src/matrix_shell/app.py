import argparse
import os
import sys
from pathlib import Path
from PySide6.QtCore import QTimer, QUrl, QLibraryInfo
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from .backend import DesktopBackend
from .qt_runtime import isolate_plugins


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true', help='Load QML, render frames and exit')
    parser.add_argument('--config-dir', type=Path, help='Override user settings directory')
    parser.add_argument('--notifications', action='store_true', help='Request the freedesktop notification name without replacing an existing owner')
    parser.add_argument('--session', action='store_true', help='Opt-in layer-shell desktop session; requires LayerShellQt QML module')
    parser.add_argument('--kwin', action='store_true', help='Enable the KWin 6 scripting window bridge')
    args = parser.parse_args()
    try:
        plugins = isolate_plugins(args.session)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 1
    if args.session:
        if not (os.environ.get('WAYLAND_DISPLAY') or os.environ.get('WAYLAND_SOCKET')):
            print('A running Wayland session is required; use tools/cloud_check.py for an isolated KWin test.', file=sys.stderr)
            return 2
        os.environ['XDG_CURRENT_DESKTOP'] = 'Matrix:KDE'
    app = QGuiApplication([sys.argv[0]])
    app.setApplicationName('Matrix')
    app.setDesktopFileName('matrix-shell')
    engine = QQmlApplicationEngine()
    backend = DesktopBackend(config_dir=args.config_dir)
    app.aboutToQuit.connect(backend.shutdown)
    if args.kwin or args.session:
        backend.windows.start()
    if args.notifications:
        backend.notifications.start()
    sounds = []
    def play_feedback():
        from PySide6.QtMultimedia import QSoundEffect, QMediaDevices
        if not QMediaDevices.audioOutputs():
            return
        if not sounds:
            effect = QSoundEffect(app)
            effect.setSource(QUrl.fromLocalFile(str(Path(__file__).parent / 'sounds/click.wav')))
            effect.setVolume(0.12)
            sounds.append(effect)
        sounds[0].play()
    backend.feedbackRequested.connect(play_feedback)
    backend.settings.changed.connect(lambda: sounds[0].stop() if sounds and not backend.settings.values['sound'] else None)
    engine.setInitialProperties({'backend': backend})
    session = None
    if args.session:
        from .session import DesktopSession
        app.setQuitOnLastWindowClosed(False)
        try:
            session = DesktopSession(engine, backend)
        except RuntimeError as error:
            print(error, file=sys.stderr)
            backend.shutdown()
            return 1
        app.aboutToQuit.connect(session.shutdown)
        roots = [window for windows in session.windows.values() for window in windows]
    else:
        engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / 'qml' / 'Main.qml')))
        roots = engine.rootObjects()
    if not roots:
        backend.shutdown()
        return 1
    if args.smoke:
        window = roots[0]
        frames = []
        window.frameSwapped.connect(lambda: frames.append(True))
        window.requestUpdate()
        def finish_smoke():
            healthy = bool(frames) and (not (args.kwin or args.session) or backend.windows.online) and (not args.notifications or backend.notifications.online)
            if not healthy:
                print('Smoke failed:', backend.windows.error, backend.notifications.error, file=sys.stderr)
            app.exit(0 if healthy else 2)
        QTimer.singleShot(1500, finish_smoke)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
