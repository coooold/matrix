import QtQuick
import QtQuick.Window
import QtQuick.Controls
import org.kde.layershell 1.0 as LayerShell

Window {
    id: surface
    objectName: "sessionLauncher"
    required property var backend
    property string mode: "apps"
    property string windowId: ""
    visible: false
    width: 1280; height: 800
    color: "transparent"
    title: "Matrix 菜单"
    LayerShell.Window.scope: "on-screen-display"
    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorBottom | LayerShell.Window.AnchorLeft | LayerShell.Window.AnchorRight
    LayerShell.Window.exclusionZone: -1
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityExclusive
    Theme { id: theme; accent: backend.settings.values.accent }
    function open() {
        visible = true
        if (mode === "apps" || mode === "files") Qt.callLater(launcher.refresh)
        else if (mode === "system") systemPanel.open()
        else if (mode === "notifications") notifications.open()
        else if (mode === "store") storePanel.open()
        else if (mode === "window-actions") windowMenu.open()
    }
    function dismiss() { visible = false }
    Shortcut { sequence: "Escape"; enabled: surface.visible; onActivated: surface.dismiss() }
    MouseArea { anchors.fill: parent; onClicked: surface.dismiss() }
    Rectangle {
        id: launcherPanel
        objectName: "sessionLauncherPanel"
        anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom; bottomMargin: 88 }
        width: Math.min(480, parent.width - 32); height: Math.min(500, parent.height - 112)
        visible: surface.mode === "apps" || surface.mode === "files"
        color: theme.surface; radius: 16; border.color: theme.accent
        MouseArea { anchors.fill: parent }
        LauncherContent {
            id: launcher
            anchors.fill: parent; anchors.margins: 20
            backend: surface.backend; theme: themeTokens; mode: surface.mode
            onDismissed: surface.dismiss()
        }
    }
    SettingsPanel {
        visible: surface.mode === "settings"
        anchors.centerIn: parent
        settings: backend.settings; services: backend.services; theme: themeTokens
        onDismissed: surface.dismiss()
        onManageApplications: { surface.mode = "store"; storePanel.open() }
    }
    Menu {
        id: windowMenu
        objectName: "sessionWindowMenu"
        popupType: Popup.Item
        x: (surface.width - width) / 2; y: surface.height - height - 88
        onClosed: if (surface.mode === "window-actions") surface.dismiss()
        MenuItem { objectName: "windowMinimizeAction"; text: "最小化"; onTriggered: { backend.windows.action(surface.windowId, "minimize"); windowMenu.close() } }
        MenuItem { text: "最大化 / 还原"; onTriggered: { backend.windows.action(surface.windowId, "maximize"); windowMenu.close() } }
        MenuItem { text: "贴靠左侧"; onTriggered: { backend.windows.action(surface.windowId, "left"); windowMenu.close() } }
        MenuItem { text: "贴靠右侧"; onTriggered: { backend.windows.action(surface.windowId, "right"); windowMenu.close() } }
        MenuItem { text: "关闭"; onTriggered: { backend.windows.action(surface.windowId, "close"); windowMenu.close() } }
    }
    SystemPanel { id: systemPanel; popupType: Popup.Item; system: backend.system; theme: themeTokens; onClosed: if (surface.mode === "system") surface.dismiss() }
    NotificationPanel { id: notifications; popupType: Popup.Item; center: backend.notifications; theme: themeTokens; onClosed: if (surface.mode === "notifications") surface.dismiss() }
    StorePanel { id: storePanel; popupType: Popup.Item; services: backend.services; theme: themeTokens; onClosed: if (surface.mode === "store") surface.dismiss() }
    readonly property var themeTokens: theme
}
