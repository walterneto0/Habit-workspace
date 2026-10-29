import QtQuick
import QtQuick.Controls

Dialog {
    palette.window: Theme.surface
    palette.windowText: Theme.text
    palette.text: Theme.text
    palette.base: Theme.canvas
    palette.button: Theme.surface
    palette.buttonText: Theme.text
    palette.highlight: Theme.accentSurface
    palette.highlightedText: Theme.text
    padding: 16
    background: Rectangle {
        color: Theme.surface
        border.color: Theme.border
        radius: 10
    }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.duration } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: Theme.duration } }
}
