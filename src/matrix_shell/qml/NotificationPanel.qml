import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: panel
    required property var center
    required property var theme
    parent: Overlay.overlay
    x: (parent.width - width) / 2; y: (parent.height - height) / 2
    width: Math.min(480, parent.width - 24); height: Math.min(540, parent.height - 40)
    title: "通知中心"
    popupType: Popup.Window
    modal: true
    standardButtons: Dialog.Close
    background: Rectangle { color: panel.theme.surface; radius: 16; border.color: panel.theme.border }
    contentItem: ColumnLayout {
        RowLayout {
            ShellCheckBox { theme: panel.theme; text: "勿扰"; checked: panel.center.doNotDisturb; onClicked: panel.center.setDoNotDisturb(checked); Accessible.name: text }
            ShellButton { theme: panel.theme; text: "连接服务"; enabled: !panel.center.online; onClicked: panel.center.start() }
            ShellButton { theme: panel.theme; text: "清空"; onClicked: panel.center.clear() }
        }
        Text {
            Layout.fillWidth: true; wrapMode: Text.Wrap
            text: panel.center.error || (panel.center.online ? "通知服务已连接" : "尚未连接通知服务")
            color: panel.center.error ? panel.theme.error : panel.theme.muted
        }
        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true
            clip: true; reuseItems: true; spacing: 12
            model: panel.center.entries
            delegate: ColumnLayout {
                id: notification
                required property var modelData
                width: ListView.view.width
                Text { text: modelData.app + " · " + modelData.summary; textFormat: Text.PlainText; color: panel.theme.text; Layout.fillWidth: true; wrapMode: Text.Wrap }
                Text { text: modelData.body; textFormat: Text.PlainText; color: panel.theme.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
                RowLayout {
                    Repeater {
                        model: modelData.active ? modelData.actions : []
                        delegate: ShellButton {
                            required property var modelData
                            theme: panel.theme; text: modelData.label
                            onClicked: panel.center.invokeAction(notification.modelData.id, modelData.key)
                        }
                    }
                }
            }
        }
    }
}
