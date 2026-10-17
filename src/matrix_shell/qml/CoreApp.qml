import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtMultimedia

Window {
    id: window
    required property var model
    width: 640; height: 480; minimumWidth: 360; minimumHeight: 320
    visible: true
    title: ({calculator: "Matrix 计算器", notes: "Matrix 笔记", image: "Matrix 图片", music: "Matrix 音频"})[model.kind]
    color: theme.background
    Theme { id: theme }
    FileDialog { id: picker; onAccepted: model.selectFile(selectedFile) }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 24; spacing: 16
        Text { text: window.title; color: theme.text; font.pixelSize: 24 }
        RowLayout {
            visible: model.kind === "calculator"
            SearchField { theme: themeTokens; id: expression; objectName: "expression"; Layout.fillWidth: true; placeholderText: "(2 + 3) * 4"; maximumLength: 256; Accessible.name: "算式"; onAccepted: model.evaluate(text) }
            ShellButton { theme: themeTokens; text: "计算"; onClicked: model.evaluate(expression.text) }
        }
        Text { visible: model.kind === "calculator"; text: model.result; color: theme.accent; font.pixelSize: 32; Accessible.name: "计算结果 " + text }
        ScrollView {
            visible: model.kind === "notes"
            Layout.fillWidth: true; Layout.fillHeight: true
            TextArea {
                objectName: "noteEditor"
                enabled: model.ready
                text: model.text
                color: theme.text; wrapMode: TextEdit.Wrap
                Accessible.name: "笔记内容"
                selectByMouse: true
                textFormat: TextEdit.PlainText
                onTextChanged: if (activeFocus && model.ready) model.setText(text)
            }
        }
        Image {
            id: image
            objectName: "imageView"
            visible: model.kind === "image"
            Layout.fillWidth: true; Layout.fillHeight: true
            asynchronous: true; cache: true; fillMode: Image.PreserveAspectFit
            source: model.kind === "image" ? model.resourceUrl : ""
            Text { anchors.centerIn: parent; visible: parent.status === Image.Error; text: "无法解码图片"; color: theme.error }
        }
        RowLayout {
            visible: model.kind === "music"
            ShellButton { theme: themeTokens; text: "播放"; onClicked: player.play() }
            ShellButton { theme: themeTokens; text: "暂停"; onClicked: player.pause() }
            ShellCheckBox { theme: themeTokens; text: "静音"; checked: output.muted; onClicked: output.muted = checked; Accessible.name: text }
            Text { text: (player.position / 1000).toFixed(1) + "s"; color: theme.muted }
        }
        ShellButton { visible: model.kind === "image" || model.kind === "music"; theme: themeTokens; text: "打开文件"; onClicked: picker.open() }
        Text { Layout.fillWidth: true; wrapMode: Text.Wrap; text: player.errorString || model.status; color: player.errorString ? theme.error : theme.muted }
        Item { Layout.fillHeight: true; visible: model.kind !== "notes" && model.kind !== "image" }
    }
    readonly property bool imageReady: image.status === Image.Ready
    readonly property int imageWidth: image.sourceSize.width
    readonly property int mediaDurationMs: player.duration
    readonly property int mediaPositionMs: player.position
    readonly property bool mediaPlaying: player.playbackState === MediaPlayer.PlayingState
    readonly property bool mediaPaused: player.playbackState === MediaPlayer.PausedState
    readonly property bool mediaMuted: output.muted
    readonly property var themeTokens: theme
    AudioOutput { id: output; objectName: "audioOutput" }
    MediaPlayer { id: player; objectName: "mediaPlayer"; audioOutput: output; source: model.kind === "music" ? model.resourceUrl : "" }
}
