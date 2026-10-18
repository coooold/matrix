from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ['packaging/windows/entry.py'],
    pathex=['src'],
    datas=collect_data_files('matrix_shell'),
    hiddenimports=['PySide6.QtQuick', 'PySide6.QtQuickControls2', 'PySide6.QtMultimedia'],
    excludes=['matrix_shell.kwin_bridge', 'matrix_shell.notifications',
              'matrix_shell.host_services', 'matrix_shell.system_status', 'dbus_next'],
)
pyz = PYZ(a.pure)
# Windows Media Foundation is available on the supported Windows editions.
# Do not ship the unused FFmpeg backend and its separately licensed codecs.
a.binaries = [entry for entry in a.binaries if not any(
    token in entry[0].lower() for token in ('ffmpegmediaplugin', 'avcodec-', 'avformat-',
        'avutil-', 'swresample-', 'swscale-', 'avfilter-', 'avdevice-', 'postproc-'))]
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='MatrixPreview',
          console=False, debug=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name='MatrixPreview', upx=False)
