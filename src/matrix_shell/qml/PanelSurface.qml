import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.layershell 1.0 as LayerShell

Window {
    id: panel
    required property var backend
    property bool primaryScreen: true
    visible: false
    title: "Matrix Panel"
    width: 1280; height: 72
    color: theme.surface
    Theme { id: theme; accent: backend.settings.values.accent }
    LayerShell.Window.scope: "dock"
    LayerShell.Window.layer: LayerShell.Window.LayerTop
    LayerShell.Window.anchors: LayerShell.Window.AnchorBottom | LayerShell.Window.AnchorLeft | LayerShell.Window.AnchorRight
    LayerShell.Window.exclusionZone: 72
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityOnDemand
    RowLayout {
        anchors.fill: parent; anchors.margins: 12; spacing: 8
        ShellButton { objectName: "sessionStartButton"; theme: themeTokens; text: "开始"; onClicked: { launcher.mode = "apps"; launcher.open() } }
        ShellButton { theme: themeTokens; text: "文件"; onClicked: { launcher.mode = "files"; launcher.open() } }
        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true
            orientation: ListView.Horizontal; spacing: 8; clip: true
            model: backend.windows.entries
            delegate: ShellButton {
                id: task
                required property var modelData
                objectName: "windowTask-" + modelData.id
                theme: themeTokens; width: 160; height: 44
                text: (modelData.active ? "● " : "") + modelData.title
                Accessible.name: modelData.title
                onClicked: backend.windows.action(modelData.id, modelData.active && !modelData.minimized ? "minimize" : "activate")
                TapHandler {
                    acceptedButtons: Qt.RightButton
                    onTapped: { launcher.windowId = task.modelData.id; launcher.mode = "window-actions"; launcher.open() }
                }
            }
        }
        ShellButton { theme: themeTokens; text: "设置"; onClicked: { launcher.mode = "settings"; launcher.open() } }
        ShellButton { theme: themeTokens; text: "系统"; onClicked: { launcher.mode = "system"; launcher.open() } }
        ShellButton { theme: themeTokens; text: "通知"; onClicked: { launcher.mode = "notifications"; launcher.open() } }
        Text { id: clock; color: theme.text; text: Qt.formatDateTime(new Date(), "hh:mm") }
    }
    Timer { interval: 1000; running: true; repeat: true; onTriggered: clock.text = Qt.formatDateTime(new Date(), "hh:mm") }
    readonly property var themeTokens: theme
    ToastSurface { center: backend.notifications; settings: backend.settings; screen: panel.screen; primaryScreen: panel.primaryScreen }
    OverlaySurface { id: launcher; screen: panel.screen; transientParent: panel; backend: panel.backend }

}
