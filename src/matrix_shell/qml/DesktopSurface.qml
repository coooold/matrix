import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LayerShell

Window {
    id: desktop
    required property var backend
    visible: false
    title: "Matrix Desktop"
    width: 1280; height: 800
    color: "#090e1b"
    LayerShell.Window.scope: "desktop"
    LayerShell.Window.layer: LayerShell.Window.LayerBackground
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorBottom | LayerShell.Window.AnchorLeft | LayerShell.Window.AnchorRight
    LayerShell.Window.exclusionZone: -1
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone
    Rectangle {
        anchors.fill: parent
        gradient: Gradient { GradientStop { position: 0; color: "#11243a" } GradientStop { position: 1; color: "#090e1b" } }
    }
    Rectangle {
        anchors { bottom: parent.bottom; right: parent.right; margins: 100 }
        width: Math.min(320, parent.width / 2); height: width; radius: width / 2
        visible: !backend.settings.values.lowEffects
        color: "#bc13fe"; opacity: 0.06
    }
    Column {
        anchors { left: parent.left; top: parent.top; margins: 40 }
        spacing: 12
        Text { text: "M A T R I X"; color: "#edf4ff"; font.pixelSize: 36 }
        Text { text: "Wayland · KWin"; color: backend.settings.values.accent; font.pixelSize: 16 }
    }
}
