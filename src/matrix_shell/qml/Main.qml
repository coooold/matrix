import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import QtQuick.Controls

Window {
    id: root
    required property var backend
    width: 1280; height: 800
    minimumWidth: 360; minimumHeight: 480
    visible: true
    title: "Matrix · Desktop Preview"
    color: theme.background
    property bool launcherOpen: false
    property bool settingsOpen: false
    property string launcherMode: "apps"
    readonly property var sourceModel: launcherMode === "apps" ? backend.applications : backend
    readonly property bool sourceBusy: sourceModel.busy || (launcherMode === "files" && backend.filtering)
    Theme { id: theme; accent: backend.settings.values.accent }

    function activateEntry(index) {
        if (index >= 0 && index < files.count && launcherMode === "apps")
            backend.applications.launch(backend.applications.entries[index].id)
        else if (index >= 0 && index < files.count && launcherMode === "files")
            backend.fileBrowser.open(backend.entries[index])
    }
    Connections {
        target: backend.applications
        function onLaunched(ident) { root.closeLauncher(); backend.feedback() }
    }

    function openLauncher(mode = "apps") {
        settingsOpen = false
        launcherMode = mode
        launcherOpen = true
        search.clear()
        if (mode === "apps") backend.applications.refresh()
        else backend.scanHome()
        backend.feedback()
        search.forceActiveFocus()
    }
    function closeLauncher() {
        launcherOpen = false
        startButton.forceActiveFocus()
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0; color: "#132b46" }
            GradientStop { position: 1; color: theme.background }
        }
        MouseArea {
            anchors.fill: parent
            onClicked: { if (root.launcherOpen) root.closeLauncher(); root.settingsOpen = false }
        }
    }
    Rectangle {
        anchors { right: parent.right; bottom: parent.bottom; margins: 100 }
        width: Math.min(320, root.width / 2); height: width; radius: width / 2
        color: "#bc13fe"; opacity: 0.06
        visible: !backend.settings.values.lowEffects
    }
    Column {
        anchors { left: parent.left; top: parent.top; margins: 32 }
        spacing: 12
        Text { text: "M A T R I X"; color: theme.text; font.pixelSize: 36; font.weight: Font.Light }
        Text { visible: !!backend.windows.error; text: "窗口服务不可用，请检查 KWin 会话"; color: theme.error; font.pixelSize: theme.bodySize }
        Text { text: "让每一次操作都从容流畅"; color: theme.muted; font.pixelSize: theme.bodySize }
    }
    Rectangle {
        id: launcher
        objectName: "launcher"
        width: Math.min(440, root.width - 32)
        height: Math.min(460, dock.y - 32)
        radius: theme.radius
        anchors { bottom: dock.top; bottomMargin: theme.spacing; horizontalCenter: parent.horizontalCenter }
        color: theme.surface; border.color: theme.border
        visible: root.launcherOpen
        scale: root.launcherOpen ? 1 : 0.98
        Behavior on scale { enabled: !backend.settings.values.reducedMotion; NumberAnimation { duration: 160 } }
        // Consume panel background clicks so only clicks outside dismiss it.
        MouseArea { anchors.fill: parent }
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 24; spacing: 12
            RowLayout {
                Layout.fillWidth: true
                Text { text: root.launcherMode === "apps" ? "应用程序" : "主目录"; color: theme.text; font.pixelSize: 24; Accessible.role: Accessible.Heading; Layout.fillWidth: true }
                ShellButton { theme: root.themeTokens; text: "刷新"; implicitWidth: 64; implicitHeight: 36; onClicked: root.launcherMode === "apps" ? backend.applications.refresh() : backend.scanHome() }
            }
            Text {
                visible: root.launcherMode === "files"
                text: backend.fileBrowser.path
                color: theme.muted; Layout.fillWidth: true; elide: Text.ElideMiddle
                Accessible.name: text
            }
            RowLayout {
                visible: root.launcherMode === "files"
                ShellButton { theme: root.themeTokens; text: "上级"; implicitWidth: 72; implicitHeight: 32; onClicked: backend.fileBrowser.parentDirectory() }
                ShellButton { theme: root.themeTokens; text: "更多"; implicitWidth: 72; implicitHeight: 32; enabled: backend.fileBrowser.more && !backend.busy; onClicked: backend.fileBrowser.loadMore() }
                ShellButton { theme: root.themeTokens; text: "操作"; implicitWidth: 72; implicitHeight: 32; onClicked: { fileActions.selectedName = files.currentIndex >= 0 ? backend.entries[files.currentIndex] : ""; fileActions.open() } }
            }
            TextField {
                id: search
                objectName: "fileSearch"
                Layout.fillWidth: true
                placeholderText: root.launcherMode === "apps" ? "搜索名称或类别…" : "筛选文件名称…"
                Accessible.name: root.launcherMode === "apps" ? "搜索应用程序" : "筛选主目录文件"
                color: theme.text
                placeholderTextColor: theme.muted
                font.pixelSize: theme.bodySize
                selectByMouse: true
                maximumLength: 256
                onTextChanged: root.sourceModel.setQuery(text)
                background: Rectangle {
                    implicitHeight: 44; radius: 10
                    color: theme.background
                    border.width: search.activeFocus ? 2 : 1
                    border.color: search.activeFocus ? theme.accent : theme.border
                }
                Keys.onDownPressed: {
                    if (files.count > 0) {
                        files.currentIndex = 0
                        files.forceActiveFocus()
                    }
                }
                Keys.onReturnPressed: root.activateEntry(files.currentIndex >= 0 ? files.currentIndex : 0)
                KeyNavigation.tab: files
            }
            Text {
                Layout.fillWidth: true
                text: root.sourceBusy ? "正在读取…" : root.launcherMode === "apps" ? files.count + " 个应用 · 按 Enter 启动" : files.count + " 项匹配" + (backend.fileBrowser.more ? " · 还有更多" : "")
                color: theme.muted; font.pixelSize: 12
                wrapMode: Text.Wrap
            }
            Text {
                visible: root.sourceModel.error.length > 0; text: root.sourceModel.error
                color: theme.error; Layout.fillWidth: true; wrapMode: Text.Wrap
                Accessible.role: Accessible.AlertMessage
            }
            ListView {
                id: files
                objectName: "fileList"
                Layout.fillWidth: true; Layout.fillHeight: true
                clip: true; reuseItems: true
                model: root.sourceModel.entries
                currentIndex: -1
                activeFocusOnTab: true
                Accessible.role: Accessible.List
                Accessible.name: root.launcherMode === "apps" ? "应用列表" : "主目录文件列表"
                keyNavigationWraps: false
                KeyNavigation.tab: startButton
                Keys.onReturnPressed: root.activateEntry(currentIndex)
                Keys.onUpPressed: {
                    if (currentIndex <= 0) search.forceActiveFocus()
                    else decrementCurrentIndex()
                }
                delegate: Rectangle {
                    id: entry
                    required property var modelData
                    required property int index
                    width: ListView.view.width; height: 40; radius: 6
                    color: ListView.isCurrentItem ? theme.raised : "transparent"
                    border.color: ListView.isCurrentItem && files.activeFocus ? theme.accent : "transparent"
                    Accessible.role: Accessible.ListItem
                    Accessible.name: root.launcherMode === "apps" ? modelData.name : modelData
                    Accessible.focusable: true
                    Accessible.selected: ListView.isCurrentItem
                    Text {
                        anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
                        textFormat: Text.PlainText
                        text: root.launcherMode === "apps" ? entry.modelData.name : entry.modelData; color: theme.text; font.pixelSize: theme.bodySize
                        elide: Text.ElideRight; width: parent.width - 24
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: { files.currentIndex = entry.index; files.forceActiveFocus(); if (root.launcherMode === "apps") root.activateEntry(entry.index) }
                        onDoubleClicked: if (root.launcherMode === "files") root.activateEntry(entry.index)
                    }
                }
                Text {
                    anchors.centerIn: parent
                    visible: files.count === 0 && !root.sourceBusy && !root.sourceModel.error
                    text: search.text.length ? "没有匹配的项目" : root.launcherMode === "apps" ? "没有可用应用" : "目录为空"
                    color: theme.muted
                    Accessible.role: Accessible.StaticText
                }
            }
        }
    }
    Rectangle {
        anchors { bottom: dock.top; bottomMargin: 12; horizontalCenter: parent.horizontalCenter }
        width: Math.min(800, root.width - 24); height: 48; radius: 12
        color: theme.surface; border.color: theme.border
        visible: backend.windows.online && backend.windows.entries.length > 0 && !root.launcherOpen
        ListView {
            anchors.fill: parent; anchors.margins: 4
            orientation: ListView.Horizontal; spacing: 8; clip: true
            model: backend.windows.entries
            delegate: ShellButton {
                id: task
                required property var modelData
                objectName: "windowTask-" + modelData.id
                theme: root.themeTokens; width: 180; height: 40
                text: (modelData.active ? "● " : "") + modelData.title
                Accessible.name: modelData.title
                Accessible.description: modelData.minimized ? "已最小化" : modelData.active ? "当前窗口" : "运行中"
                onClicked: backend.windows.action(modelData.id, modelData.active && !modelData.minimized ? "minimize" : "activate")
                TapHandler { acceptedButtons: Qt.RightButton; onTapped: taskMenu.popup() }
                Menu {
                    id: taskMenu
                    MenuItem { text: "最大化 / 还原"; onTriggered: backend.windows.action(task.modelData.id, "maximize") }
                    MenuItem { text: "贴靠左侧"; onTriggered: backend.windows.action(task.modelData.id, "left") }
                    MenuItem { text: "贴靠右侧"; onTriggered: backend.windows.action(task.modelData.id, "right") }
                    MenuItem { text: "关闭"; onTriggered: backend.windows.action(task.modelData.id, "close") }
                }
            }
        }
    }
    Rectangle {
        id: dock
        anchors { bottom: parent.bottom; bottomMargin: 18; horizontalCenter: parent.horizontalCenter }
        width: Math.min(600, root.width - 24); height: 64; radius: theme.radius
        color: theme.surface; border.color: theme.border
        Row {
            anchors.centerIn: parent; spacing: 8
            ShellButton {
                id: startButton
                objectName: "startButton"
                theme: themeTokens
                implicitWidth: root.dockButtonWidth
                text: "开始"
                onClicked: root.launcherOpen ? root.closeLauncher() : root.openLauncher()
                KeyNavigation.tab: fileButton
            }
            ShellButton {
                id: fileButton
                theme: themeTokens
                objectName: "fileButton"
                implicitWidth: root.dockButtonWidth
                text: "文件"
                onClicked: root.openLauncher("files")
                KeyNavigation.tab: settingsButton
            }
            ShellButton {
                id: settingsButton
                theme: themeTokens
                implicitWidth: root.dockButtonWidth
                text: "设置"
                onClicked: { root.launcherOpen = false; root.settingsOpen = !root.settingsOpen }
                KeyNavigation.tab: systemButton
            }
            ShellButton {
                id: systemButton
                theme: themeTokens; implicitWidth: root.dockButtonWidth; text: "系统"
                onClicked: systemPanel.open()
                KeyNavigation.tab: notificationButton
            }
            ShellButton {
                id: notificationButton
                theme: themeTokens; implicitWidth: root.dockButtonWidth; text: "通知"
                onClicked: notificationPanel.open()
                KeyNavigation.tab: desktopButton
            }
            ShellButton {
                id: desktopButton
                theme: themeTokens
                implicitWidth: root.dockButtonWidth
                text: "桌面"
                onClicked: root.closeLauncher()
                KeyNavigation.tab: root.launcherOpen ? search : startButton
            }
        }
    }
    StorePanel { id: storePanel; services: backend.services; theme: root.themeTokens }
    SystemPanel { id: systemPanel; system: backend.system; theme: root.themeTokens }
    NotificationPanel { id: notificationPanel; center: backend.notifications; theme: root.themeTokens }
    FileActions { id: fileActions; browser: backend.fileBrowser; theme: root.themeTokens }
    Rectangle {
        anchors { right: parent.right; top: parent.top; margins: 24 }
        width: Math.min(320, root.width - 48); height: 100; radius: 12
        color: theme.surface; border.color: theme.accent
        visible: !!backend.notifications.latest.id
        Column {
            anchors.fill: parent; anchors.margins: 16; spacing: 8
            Text { text: backend.notifications.latest.summary || ""; textFormat: Text.PlainText; color: theme.text; width: parent.width; elide: Text.ElideRight }
            Text { text: backend.notifications.latest.body || ""; textFormat: Text.PlainText; color: theme.muted; width: parent.width; maximumLineCount: 2; wrapMode: Text.Wrap; elide: Text.ElideRight }
        }
    }
    SettingsPanel {
        objectName: "settingsPanel"
        anchors.centerIn: parent
        visible: root.settingsOpen
        settings: backend.settings
        services: backend.services
        onManageApplications: storePanel.open()
        theme: root.themeTokens
        onDismissed: { root.settingsOpen = false; startButton.forceActiveFocus() }
    }
    // Avoid a component's theme property shadowing the local Theme id.
    readonly property var themeTokens: theme
    readonly property int dockButtonWidth: Math.floor((dock.width - 56) / 6)
    Shortcut { sequence: "Escape"; enabled: (root.launcherOpen || root.settingsOpen) && !fileActions.visible && !systemPanel.visible && !notificationPanel.visible && !storePanel.visible; onActivated: { root.settingsOpen = false; root.closeLauncher() } }
    Shortcut { sequence: "Ctrl+Space"; onActivated: root.launcherOpen ? root.closeLauncher() : root.openLauncher() }
}
