import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: panel
    required property var settings
    required property var theme
    property var services: null
    signal manageApplications()
    signal dismissed()
    width: Math.min(440, parent.width - 32)
    height: Math.min(440, parent.height - 100)
    color: theme.surface
    border.color: theme.border
    radius: theme.radius
    MouseArea { anchors.fill: parent }
    ScrollView {
        anchors.fill: parent; anchors.margins: 20
        contentWidth: availableWidth
        ColumnLayout {
            width: parent.width
            spacing: 12
            Text { textFormat: Text.PlainText; text: "个性化"; color: panel.theme.text; font.pixelSize: 24; Accessible.role: Accessible.Heading }
            Text { textFormat: Text.PlainText; text: "强调色"; color: panel.theme.muted }
            Row {
                spacing: 8
                Repeater {
                    model: ["#00d9e8", "#b99aff", "#91caff"]
                    delegate: Button {
                        required property string modelData
                        width: 64; height: 36
                        enabled: panel.settings.ready
                        Accessible.name: "强调色 " + modelData
                        onClicked: panel.settings.setValue("accent", modelData)
                        background: Rectangle {
                            color: modelData; radius: 8
                            border.width: parent.activeFocus || panel.settings.values.accent === modelData ? 3 : 0
                            border.color: panel.theme.text
                        }
                    }
                }
            }
            Repeater {
                model: [{key: "sound", label: "提示音"}, {key: "reducedMotion", label: "减少动态效果"}, {key: "lowEffects", label: "低特效模式"}]
                delegate: ShellCheckBox {
                    theme: panel.theme
                    required property var modelData
                    objectName: "setting-" + modelData.key
                    text: modelData.label
                    enabled: panel.settings.ready
                    checked: panel.settings.values[modelData.key]
                    onClicked: panel.settings.setValue(modelData.key, checked)
                    Accessible.name: text
                }
            }
            Text { textFormat: Text.PlainText;
                Layout.fillWidth: true; wrapMode: Text.Wrap
                text: panel.settings.error || (panel.settings.busy ? "正在保存…" : "已保存到本机")
                color: panel.settings.error ? panel.theme.error : panel.theme.muted
            }
            Text { textFormat: Text.PlainText; visible: !!panel.services; text: panel.services ? panel.services.message : ""; color: panel.theme.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
            Row {
                visible: !!panel.services; spacing: 12
                ShellButton { theme: panel.theme; text: "锁定会话"; onClicked: panel.services.lock() }
                ShellButton { theme: panel.theme; text: "应用管理"; onClicked: panel.manageApplications() }
            }
            Row {
                spacing: 12
                ShellButton { theme: panel.theme; text: "恢复默认"; enabled: panel.settings.ready; onClicked: panel.settings.reset() }
                ShellButton { theme: panel.theme; text: "完成"; onClicked: panel.dismissed() }
            }
        }
    }
}
