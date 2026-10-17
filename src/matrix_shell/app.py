import argparse
import sys
from pathlib import Path
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from .backend import DesktopBackend


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true', help='Load QML, render frames and exit')
    args = parser.parse_args()
    app = QGuiApplication([sys.argv[0]])
    app.setApplicationName('Matrix')
    engine = QQmlApplicationEngine()
    backend = DesktopBackend()
    engine.setInitialProperties({'backend': backend})
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / 'qml' / 'Main.qml')))
    if not engine.rootObjects():
        return 1
    if args.smoke:
        window = engine.rootObjects()[0]
        frames = []
        window.frameSwapped.connect(lambda: frames.append(True))
        QTimer.singleShot(1500, lambda: app.exit(0 if frames else 2))
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
