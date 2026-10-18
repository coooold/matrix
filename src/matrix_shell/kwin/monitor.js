// KWin 6.3 supported scripting API. Coalesce state changes; no per-frame polling.
const flush = new QTimer();
flush.singleShot = true;
flush.interval = 0;
function publish() {
    const rows = workspace.windowList().filter(w => w.normalWindow && w.desktopFileName !== "matrix-shell").map(w => { const bounds = workspace.clientArea(KWin.MaximizeArea, w); return ({
        workArea: {x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height},
        id: w.internalId.toString(), title: w.caption, appId: w.desktopFileName,
        minimized: w.minimized, active: w.active, maximized: Number(w.maximizeMode),
        x: w.x, y: w.y, width: w.width, height: w.height
    }); });
    callDBus("org.matrixdesktop.Shell1", "/org/matrixdesktop/Shell1", "org.matrixdesktop.Shell1", "Publish", JSON.stringify(rows));
    const area = workspace.clientArea(KWin.MaximizeArea, workspace.screens[0], workspace.currentDesktop);
    const environment = {
        roles: workspace.windowList().map(w => ({title: w.caption, desktop: w.desktopWindow, dock: w.dock, notification: w.notification, x:w.x, y:w.y, width:w.width, height:w.height})),
        workArea: {x:area.x, y:area.y, width:area.width, height:area.height},
        screens: workspace.screens.length,
        screenDetails: workspace.screens.map(output => { const geometry = output.geometry; const bounds = workspace.clientArea(KWin.MaximizeArea, output, workspace.currentDesktop); return {name:output.name, scale:output.devicePixelRatio, x:geometry.x, y:geometry.y, width:geometry.width, height:geometry.height, workHeight:bounds.height}; })
    };
    callDBus("org.matrixdesktop.Shell1", "/org/matrixdesktop/Shell1", "org.matrixdesktop.Shell1", "Environment", JSON.stringify(environment));
}
flush.timeout.connect(publish);
function schedule() { flush.start(); }
function watch(window) {
    window.captionChanged.connect(schedule);
    window.minimizedChanged.connect(schedule);
    window.maximizedChanged.connect(schedule);
    window.quickTileModeChanged.connect(schedule);
    window.activeChanged.connect(schedule);
    window.moveResizedChanged.connect(schedule);
    window.desktopFileNameChanged.connect(schedule);
    schedule();
}
workspace.windowList().forEach(watch);
workspace.windowAdded.connect(watch);
workspace.windowRemoved.connect(schedule);
workspace.windowActivated.connect(schedule);
schedule();

workspace.screensChanged.connect(schedule);

workspace.screens.forEach(output => { output.scaleChanged.connect(schedule); output.geometryChanged.connect(schedule); });
