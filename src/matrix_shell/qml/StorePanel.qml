import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: panel
    required property var services
    required property var theme
    parent: Overlay.overlay
    popupType: Popup.Window
    x: (parent.width - width) / 2; y: (parent.height - height) / 2
    width: Math.min(560, Screen.width - 32); height: Math.min(500, Screen.height - 80)
    title: "应用管理 · Flatpak 用户安装"
    modal: true; standardButtons: Dialog.Close
    background: Rectangle { color: panel.theme.surface; radius: 16; border.color: panel.theme.border }
    onOpened: services.refreshPackages()
    contentItem: ColumnLayout {
        TextField { id: remote; text: "flathub"; placeholderText: "已配置的受信任远端"; Accessible.name: placeholderText; Layout.fillWidth: true }
        TextField { id: appid; placeholderText: "应用 ID，例如 org.kde.kcalc"; Accessible.name: placeholderText; Layout.fillWidth: true }
        RowLayout {
            ShellButton { theme: panel.theme; text: "安装"; enabled: !panel.services.busy; onClicked: panel.services.install(remote.text, appid.text) }
            ShellButton { theme: panel.theme; text: "刷新"; enabled: !panel.services.busy; onClicked: panel.services.refreshPackages() }
            ShellButton { theme: panel.theme; text: "取消"; enabled: panel.services.busy; onClicked: panel.services.cancel() }
        }
        Text { textFormat: Text.PlainText; text: panel.services.busy ? "正在执行真实软件包操作…" : panel.services.message; color: panel.theme.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true
            clip: true; reuseItems: true
            model: panel.services.entries
            delegate: RowLayout {
                required property var modelData
                width: ListView.view.width; height: 44
                Text { textFormat: Text.PlainText; text: modelData.name + " · " + modelData.version; color: panel.theme.text; elide: Text.ElideRight; Layout.fillWidth: true }
                ShellButton { theme: panel.theme; text: "卸载"; enabled: !panel.services.busy; onClicked: { confirm.appid = modelData.id; confirm.open() } }
            }
        }
    }
    Dialog { id: confirm; property string appid; title: "卸载 " + appid + "？"; modal: true; standardButtons: Dialog.Ok | Dialog.Cancel; onAccepted: panel.services.uninstall(appid) }
}
