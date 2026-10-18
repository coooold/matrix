import QtQuick
import QtQuick.Controls

Button {
    id: control
    required property var theme
    property bool listItem: false
    implicitWidth: 88
    implicitHeight: 44
    font.pixelSize: theme.bodySize
    hoverEnabled: true
    Accessible.name: text
    background: Rectangle {
        radius: 12
        color: control.down ? control.theme.hover : control.hovered ? control.theme.hover : control.highlighted ? control.theme.raised : control.listItem ? control.theme.surface : control.theme.raised
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus || control.highlighted ? control.theme.accent : "transparent"
    }
    contentItem: Text { textFormat: Text.PlainText;
        text: control.text
        color: control.theme.text
        font: control.font
        elide: Text.ElideRight
        horizontalAlignment: control.listItem ? Text.AlignLeft : Text.AlignHCenter
        leftPadding: control.listItem ? 12 : 0
        verticalAlignment: Text.AlignVCenter
    }
}
