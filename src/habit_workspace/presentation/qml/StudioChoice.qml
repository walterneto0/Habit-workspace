import QtQuick
import QtQuick.Controls

ComboBox {
    id: control
    property string label: ""
    implicitHeight: 38
    Accessible.name: label
    focusPolicy: Qt.StrongFocus
    palette.text: Theme.text
    palette.buttonText: Theme.text
    palette.button: Theme.surface
    palette.base: Theme.surface
    palette.highlight: Theme.accentSurface
    palette.highlightedText: Theme.text
    background: Rectangle {
        radius: 6
        color: Theme.surface
        border.color: control.activeFocus ? Theme.accent : Theme.border
        border.width: control.activeFocus ? 2 : 1
    }
}
