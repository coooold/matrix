import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: dialog
    required property var browser
    required property var theme
    property string selectedName: ""
    parent: Overlay.overlay
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2
    width: Math.min(400, parent.width - 24)
    popupType: Popup.Window
    modal: true
    title: "文件操作"
    standardButtons: Dialog.Close
    background: Rectangle { radius: 16; color: dialog.theme.surface; border.color: dialog.theme.border }
    contentItem: ColumnLayout {
        spacing: 12
        Text { textFormat: Text.PlainText; text: dialog.selectedName || "未选择文件"; color: dialog.theme.text; Layout.fillWidth: true; elide: Text.ElideMiddle }
        TextField { id: nameField; objectName: "newFileName"; Layout.fillWidth: true; placeholderText: "新名称 / 复制目标名称"; maximumLength: 255; Accessible.name: placeholderText }
        RowLayout {
            ShellButton { theme: dialog.theme; text: "新建文件"; enabled: !dialog.browser.busy; onClicked: dialog.browser.createFile(nameField.text) }
            ShellButton { theme: dialog.theme; text: "新建目录"; enabled: !dialog.browser.busy; onClicked: dialog.browser.createFolder(nameField.text) }
        }
        RowLayout {
            ShellButton { theme: dialog.theme; text: "复制文件"; enabled: !dialog.browser.busy && !!dialog.selectedName; onClicked: dialog.browser.copy(dialog.selectedName, nameField.text) }
            ShellButton { theme: dialog.theme; text: "取消复制"; enabled: dialog.browser.busy; onClicked: dialog.browser.cancel() }
        }
        ShellButton { theme: dialog.theme; text: "移到回收站"; implicitWidth: 160; enabled: !dialog.browser.busy && !!dialog.selectedName; onClicked: confirmTrash.open() }
        Text { textFormat: Text.PlainText; text: dialog.browser.error || (dialog.browser.busy ? "正在处理…" : "不会覆盖已存在的文件"); color: dialog.browser.error ? dialog.theme.error : dialog.theme.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
    }
    Dialog {
        id: confirmTrash
        anchors.centerIn: parent
        modal: true
        title: "将所选项目移到回收站？"
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: dialog.browser.trash(dialog.selectedName)
    }
}
