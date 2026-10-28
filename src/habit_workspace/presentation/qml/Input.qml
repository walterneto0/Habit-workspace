import QtQuick
import QtQuick.Controls

TextField {
    id: field
    implicitHeight: 38
    color: Theme.text
    placeholderTextColor: Theme.muted
    selectionColor: Theme.accentSurface
    selectedTextColor: Theme.text
    font.pixelSize: 13
    padding: 10
    Accessible.name: placeholderText
    background: Rectangle {
        radius: 6
        color: Theme.canvas
        border.color: field.activeFocus ? Theme.accent : Theme.border
        border.width: field.activeFocus ? 2 : 1
    }
}
