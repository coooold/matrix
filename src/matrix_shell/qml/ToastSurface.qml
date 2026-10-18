import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import org.kde.layershell 1.0 as LayerShell

Window {
    id: toast
    required property var center
    required property var settings
    property bool primaryScreen: true
    width: Math.min(360, screen.width - 40)
    height: (center.latest.actions || []).length ? 164 : 120
    visible: primaryScreen && !!center.latest.id
    color: theme.surface
    title: "Matrix 通知"
    Theme { id: theme; accent: toast.settings.values.accent }
    LayerShell.Window.scope: "notification"
    LayerShell.Window.layer: LayerShell.Window.LayerTop
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorRight
    LayerShell.Window.margins.top: 20
    LayerShell.Window.margins.right: 20
    LayerShell.Window.exclusionZone: 0
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 16; spacing: 8
        Accessible.role: Accessible.AlertMessage
        Accessible.name: (toast.center.latest.summary || "") + " " + (toast.center.latest.body || "")
        Text { text: toast.center.latest.summary || ""; textFormat: Text.PlainText; color: theme.text; font.pixelSize: 16; Layout.fillWidth: true; elide: Text.ElideRight }
        Text { text: toast.center.latest.body || ""; textFormat: Text.PlainText; color: theme.muted; Layout.fillWidth: true; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
        RowLayout {
            Repeater {
                model: (toast.center.latest.actions || []).slice(0, 2)
                delegate: ShellButton { required property var modelData; theme: toast.themeTokens; text: modelData.label; onClicked: toast.center.invokeAction(toast.center.latest.id, modelData.key) }
            }
        }
        Item { Layout.fillHeight: true }
    }
    readonly property var themeTokens: theme
}
