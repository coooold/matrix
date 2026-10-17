import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: panel
    required property var system
    required property var theme
    parent: Overlay.overlay
    x: (parent.width - width) / 2; y: (parent.height - height) / 2
    width: Math.min(620, parent.width - 24); height: Math.min(540, parent.height - 40)
    popupType: Popup.Window
    modal: true
    title: "系统状态"
    standardButtons: Dialog.Close
    property bool holdingLease: false
    onOpened: { if (!holdingLease) { holdingLease = true; system.acquire() } }
    onClosed: { if (holdingLease) { holdingLease = false; system.release() } }
    Component.onDestruction: if (holdingLease && system) system.release()
    background: Rectangle { color: panel.theme.surface; radius: 16; border.color: panel.theme.border }
    contentItem: ColumnLayout {
        Text { textFormat: Text.PlainText;
            text: "CPU " + (panel.system.values.cpuPercent === null || panel.system.values.cpuPercent === undefined ? "采样中" : panel.system.values.cpuPercent.toFixed(1) + "%")
            color: panel.theme.text
        }
        Text { textFormat: Text.PlainText;
            text: "内存 " + ((panel.system.values.memoryUsedKiB || 0) / 1048576).toFixed(2) + " / " + ((panel.system.values.memoryTotalKiB || 0) / 1048576).toFixed(2) + " GiB"
            color: panel.theme.text
        }
        Text { textFormat: Text.PlainText;
            Layout.fillWidth: true; wrapMode: Text.Wrap
            text: "电池 " + (panel.system.values.batteryPercent === null || panel.system.values.batteryPercent === undefined ? "不可用" : panel.system.values.batteryPercent + "%") + " · 音量不可用\n默认路由接口：" + ((panel.system.values.routeInterfaces || []).join(", ") || "无") + "（不代表互联网连通）"
            color: panel.theme.muted
        }
        Text { textFormat: Text.PlainText; text: panel.system.error; color: panel.theme.error; visible: !!text; wrapMode: Text.Wrap; Layout.fillWidth: true }
        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true
            clip: true; reuseItems: true
            model: panel.system.values.processes || []
            delegate: RowLayout {
                required property var modelData
                width: ListView.view.width; height: 44
                Text { textFormat: Text.PlainText; text: modelData.pid + " · " + modelData.name; color: panel.theme.text; Layout.fillWidth: true; elide: Text.ElideRight }
                Text { textFormat: Text.PlainText; text: (modelData.rssKiB / 1024).toFixed(1) + " MiB"; color: panel.theme.muted }
                ShellButton {
                    theme: panel.theme; text: "结束"; implicitWidth: 64; implicitHeight: 32
                    enabled: modelData.terminable
                    onClicked: { confirm.pid = modelData.pid; confirm.open() }
                }
            }
        }
    }
    Dialog {
        id: confirm
        property int pid: 0
        anchors.centerIn: parent
        modal: true
        title: "结束进程 " + pid + "？"
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: panel.system.terminate(pid)
    }
}
