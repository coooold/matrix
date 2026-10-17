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
    Theme { id: theme }

    function openLauncher() {
        launcherOpen = true
        search.clear()
        backend.scanHome()
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
            onClicked: if (root.launcherOpen) root.closeLauncher()
        }
    }
    Column {
        anchors { left: parent.left; top: parent.top; margins: 32 }
        spacing: 12
        Text { text: "M A T R I X"; color: theme.text; font.pixelSize: 36; font.weight: Font.Light }
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
        // Consume panel background clicks so only clicks outside dismiss it.
        MouseArea { anchors.fill: parent }
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 24; spacing: 12
            Text { text: "主目录"; color: theme.text; font.pixelSize: 24; Accessible.role: Accessible.Heading }
            TextField {
                id: search
                objectName: "fileSearch"
                Layout.fillWidth: true
                placeholderText: "筛选文件名称…"
                Accessible.name: "筛选主目录文件"
                color: theme.text
                placeholderTextColor: theme.muted
                font.pixelSize: theme.bodySize
                selectByMouse: true
                maximumLength: 256
                onTextChanged: backend.setQuery(text)
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
                KeyNavigation.tab: files
            }
            Text {
                Layout.fillWidth: true
                text: backend.busy ? "正在读取…" : backend.filtering ? "正在筛选…" : "仅预览前 200 项 · " + files.count + " 项匹配"
                color: theme.muted; font.pixelSize: 12
                wrapMode: Text.Wrap
            }
            Text {
                visible: backend.error.length > 0; text: backend.error
                color: theme.error; Layout.fillWidth: true; wrapMode: Text.Wrap
                Accessible.role: Accessible.AlertMessage
            }
            ListView {
                id: files
                objectName: "fileList"
                Layout.fillWidth: true; Layout.fillHeight: true
                clip: true; reuseItems: true
                model: backend.entries
                currentIndex: -1
                activeFocusOnTab: true
                Accessible.role: Accessible.List
                Accessible.name: "主目录文件列表"
                keyNavigationWraps: false
                KeyNavigation.tab: startButton
                Keys.onUpPressed: {
                    if (currentIndex <= 0) search.forceActiveFocus()
                    else decrementCurrentIndex()
                }
                delegate: Rectangle {
                    id: entry
                    required property string modelData
                    required property int index
                    width: ListView.view.width; height: 40; radius: 6
                    color: ListView.isCurrentItem ? theme.raised : "transparent"
                    border.color: ListView.isCurrentItem && files.activeFocus ? theme.accent : "transparent"
                    Accessible.role: Accessible.ListItem
                    Accessible.name: modelData
                    Accessible.focusable: true
                    Accessible.selected: ListView.isCurrentItem
                    Text {
                        anchors { left: parent.left; leftMargin: 12; verticalCenter: parent.verticalCenter }
                        text: entry.modelData; color: theme.text; font.pixelSize: theme.bodySize
                        elide: Text.ElideRight; width: parent.width - 24
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: { files.currentIndex = entry.index; files.forceActiveFocus() }
                    }
                }
                Text {
                    anchors.centerIn: parent
                    visible: files.count === 0 && !backend.busy && !backend.filtering && !backend.error
                    text: search.text.length ? "没有匹配的文件" : "目录为空"
                    color: theme.muted
                    Accessible.role: Accessible.StaticText
                }
            }
        }
    }
    Rectangle {
        id: dock
        anchors { bottom: parent.bottom; bottomMargin: 18; horizontalCenter: parent.horizontalCenter }
        width: 340; height: 64; radius: theme.radius
        color: theme.surface; border.color: theme.border
        Row {
            anchors.centerIn: parent; spacing: 14
            ShellButton {
                id: startButton
                objectName: "startButton"
                theme: themeTokens
                text: "开始"
                onClicked: root.launcherOpen ? root.closeLauncher() : root.openLauncher()
                KeyNavigation.tab: fileButton
            }
            ShellButton {
                id: fileButton
                theme: themeTokens
                text: "文件"
                onClicked: root.openLauncher()
                KeyNavigation.tab: desktopButton
            }
            ShellButton {
                id: desktopButton
                theme: themeTokens
                text: "桌面"
                onClicked: root.closeLauncher()
                KeyNavigation.tab: root.launcherOpen ? search : startButton
            }
        }
    }
    // Avoid a component's theme property shadowing the local Theme id.
    readonly property var themeTokens: theme
    Shortcut { sequence: "Escape"; enabled: root.launcherOpen; onActivated: root.closeLauncher() }
    Shortcut { sequence: "Ctrl+Space"; onActivated: root.launcherOpen ? root.closeLauncher() : root.openLauncher() }
}
