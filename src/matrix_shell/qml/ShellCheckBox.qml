import QtQuick
import QtQuick.Controls

CheckBox {
    id: control
    required property var theme
    implicitHeight: 36
    Accessible.name: text
    indicator: Rectangle {
        x: 0; y: (control.height - height) / 2
        width: 22; height: 22; radius: 6
        color: control.checked ? control.theme.accent : control.theme.raised
        border.width: control.activeFocus ? 2 : 1
        border.color: control.activeFocus ? control.theme.text : control.theme.border
        Text { textFormat: Text.PlainText; anchors.centerIn: parent; visible: control.checked; text: "✓"; color: control.theme.background; font.pixelSize: 17 }
    }
    contentItem: Text { textFormat: Text.PlainText;
        text: control.text; color: control.theme.text; font.pixelSize: control.theme.bodySize
        leftPadding: control.indicator.width + 12; verticalAlignment: Text.AlignVCenter
    }
}
