"""Small real standalone Qt applications; terminal integration uses Konsole."""
import argparse
import ast
from decimal import Decimal, localcontext, DivisionByZero, InvalidOperation, Overflow
import operator
import os
from pathlib import Path
import tempfile
from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer, QUrl, QStandardPaths
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from .async_job import LatestWorker
from .qt_runtime import isolate_plugins


def calculate(expression):
    if len(expression) > 256:
        raise ValueError('表达式过长')
    tree = ast.parse(expression, mode='eval')
    if sum(1 for _ in ast.walk(tree)) > 64:
        raise ValueError('表达式过于复杂')
    operations = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (float, int):
            value = Decimal(ast.get_source_segment(expression, node).replace('_', ''))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        elif isinstance(node, ast.BinOp) and type(node.op) in operations:
            value = operations[type(node.op)](visit(node.left), visit(node.right))
        else:
            raise ValueError('仅支持数字、括号和 + - × ÷')
        if not value.is_finite():
            raise ValueError('结果超出范围')
        return value
    try:
        with localcontext() as context:
            context.prec = 34
            context.Emax, context.Emin = 100, -100
            return format(visit(tree.body).normalize(), 'f')
    except DivisionByZero:
        raise ZeroDivisionError('不能除以零') from None
    except (InvalidOperation, Overflow):
        raise ValueError('结果超出计算器范围') from None


def save_note(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.matrix-note-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return None


class CoreModel(QObject):
    changed = Signal()

    def __init__(self, kind, file=None):
        super().__init__()
        self._kind = kind
        self.worker = LatestWorker(self)
        self.worker.changed.connect(self.changed)
        self.worker.completed.connect(self._loaded)
        self.file = Path(file) if file else Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / 'note.txt'
        self._text, self._result, self._url = '', '', QUrl.fromLocalFile(str(self.file.absolute())).toString() if file else ''
        self._ready = kind != 'notes'
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(300)
        self.timer.timeout.connect(self.save)
        if kind == 'notes':
            def read():
                if not self.file.exists():
                    return ''
                if self.file.stat().st_size > 2 * 1024 * 1024:
                    raise ValueError('笔记文件超过 2 MiB，请使用外部编辑器')
                return self.file.read_text()
            self.worker.submit(read)

    @Property(str, constant=True)
    def kind(self):
        return self._kind

    @Property(str, notify=changed)
    def text(self):
        return self._text

    @Property(str, notify=changed)
    def result(self):
        return self._result

    @Property(str, notify=changed)
    def resourceUrl(self):
        return self._url

    @Property(bool, notify=changed)
    def ready(self):
        return self._ready

    @Property(str, notify=changed)
    def status(self):
        return self.worker.error or ('正在处理…' if self.worker.busy or self.timer.isActive() else '已就绪')

    @Slot(object)
    def _loaded(self, value):
        if self._kind == 'notes' and not self._ready:
            self._text, self._ready = value, True
        elif self._kind == 'calculator':
            self._result = value
        self.changed.emit()

    @Slot(str)
    def evaluate(self, expression):
        self._result = ""
        self.worker.submit(lambda: calculate(expression))

    @Slot(str)
    def setText(self, text):
        if self._ready and self._kind == 'notes':
            self._text = text
            self.timer.start()
            self.changed.emit()

    @Slot()
    def save(self):
        if self._kind == 'notes' and self._ready:
            text = self._text
            self.worker.submit(lambda: save_note(self.file, text))

    @Slot(QUrl)
    def selectFile(self, url):
        if url.isLocalFile():
            self._url = url.toString()
            self.changed.emit()

    def shutdown(self):
        if self.timer.isActive():
            self.timer.stop()
            self.save()
        self.worker.shutdown()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=['calculator', 'notes', 'image', 'music'])
    parser.add_argument('path', type=Path, nargs='?')
    parser.add_argument('--file', type=Path)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    plugins = isolate_plugins()
    app = QGuiApplication([])
    app.setApplicationName('Matrix-' + args.kind)
    app.setDesktopFileName('org.matrixdesktop.' + args.kind)
    model = CoreModel(args.kind, args.file or args.path)
    app.aboutToQuit.connect(model.shutdown)
    engine = QQmlApplicationEngine()
    engine.setInitialProperties({'model': model})
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / 'qml/CoreApp.qml')))
    if not engine.rootObjects():
        return 1
    if args.smoke:
        QTimer.singleShot(500, app.quit)
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
