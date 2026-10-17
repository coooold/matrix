import QtQuick
import QtQuick.Controls

TextField {
    id: field
    required property var theme
    implicitHeight: 44
    color: theme.text
    placeholderTextColor: theme.muted
    font.pixelSize: theme.bodySize
    selectByMouse: true
    leftPadding: 12; rightPadding: 12
    background: Rectangle {
        radius: 10; color: field.theme.background
        border.width: field.activeFocus ? 2 : 1
        border.color: field.activeFocus ? field.theme.accent : field.theme.border
    }
}
