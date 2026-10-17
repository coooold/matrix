import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

FocusScope {
    id: content
    required property var backend
    required property var theme
    property string mode: "apps"
    readonly property var source: mode === "apps" ? backend.applications : backend
    signal dismissed()
    function refresh() {
        query.clear()
        if (mode === "apps") backend.applications.refresh()
        else backend.scanHome()
        query.forceActiveFocus()
    }
    function activate(index) {
        if (index < 0 || index >= rows.count) return
        if (mode === "apps") backend.applications.launch(source.entries[index].id)
        else backend.fileBrowser.open(source.entries[index])
    }
    Connections { target: content.backend.applications; function onLaunched(ident) { if (content.mode === "apps") content.dismissed() } }
    ColumnLayout {
        anchors.fill: parent; spacing: 10
        Text { textFormat: Text.PlainText; text: content.mode === "apps" ? "应用程序" : "文件"; color: content.theme.text; font.pixelSize: 24; Accessible.role: Accessible.Heading }
        Text { textFormat: Text.PlainText; visible: content.mode === "files"; text: content.backend.fileBrowser.path; color: content.theme.muted; Layout.fillWidth: true; elide: Text.ElideMiddle }
        RowLayout {
            visible: content.mode === "files"
            ShellButton { theme: content.theme; text: "上级"; onClicked: content.backend.fileBrowser.parentDirectory() }
            ShellButton { theme: content.theme; text: "更多"; enabled: content.backend.fileBrowser.more; onClicked: content.backend.fileBrowser.loadMore() }
            ShellButton { theme: content.theme; text: "操作"; onClicked: { fileActions.selectedName = rows.currentIndex >= 0 ? content.source.entries[rows.currentIndex] : ""; fileActions.open() } }
        }
        SearchField {
            theme: content.theme
            id: query
            Layout.fillWidth: true
            placeholderText: "搜索…"; maximumLength: 256
            Accessible.name: "搜索"; selectByMouse: true
            onTextChanged: content.source.setQuery(text)
            Keys.onDownPressed: if (rows.count) { rows.currentIndex = 0; rows.forceActiveFocus() }
            Keys.onReturnPressed: content.activate(rows.currentIndex >= 0 ? rows.currentIndex : 0)
        }
        Text { textFormat: Text.PlainText; text: content.source.busy ? "正在读取…" : content.source.error; color: content.source.error ? content.theme.error : content.theme.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
        ListView {
            id: rows
            Layout.fillWidth: true; Layout.fillHeight: true
            clip: true; reuseItems: true; currentIndex: -1; spacing: 4
            model: content.source.entries
            Keys.onReturnPressed: content.activate(currentIndex)
            Keys.onUpPressed: if (currentIndex <= 0) query.forceActiveFocus(); else decrementCurrentIndex()
            delegate: ShellButton {
                required property var modelData
                required property int index
                objectName: content.mode === "apps" ? "sessionApp-" + modelData.id : "sessionFile-" + modelData
                listItem: true; highlighted: ListView.isCurrentItem
                theme: content.theme; width: ListView.view.width; height: 42
                text: content.mode === "apps" ? modelData.name : modelData
                onClicked: { rows.currentIndex = index; content.activate(index) }
            }
            Text { textFormat: Text.PlainText; anchors.centerIn: parent; visible: !rows.count && !content.source.busy; text: "没有匹配的项目"; color: content.theme.muted }
        }
    }
    FileActions { id: fileActions; popupType: Popup.Item; browser: content.backend.fileBrowser; theme: content.theme }
}
