import QtQuick
import QtQuick.Controls

Button {
    id: control
    required property var theme
    implicitWidth: 88
    implicitHeight: 44
    font.pixelSize: theme.bodySize
    hoverEnabled: true
    Accessible.name: text
    background: Rectangle {
        radius: 12
        color: control.down ? control.theme.hover : control.hovered ? control.theme.hover : control.theme.raised
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus ? control.theme.accent : "transparent"
    }
    contentItem: Text {
        text: control.text
        color: control.theme.text
        font: control.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
