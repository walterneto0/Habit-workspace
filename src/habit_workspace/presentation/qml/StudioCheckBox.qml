import QtQuick
import QtQuick.Controls

CheckBox {
    id: control
    implicitHeight: 36
    implicitWidth: label.implicitWidth + 40
    focusPolicy: Qt.StrongFocus
    Accessible.name: text
    indicator: Rectangle {
        x: 4
        y: (control.height - height) / 2
        width: 22
        height: 22
        radius: 4
        color: control.checked ? Theme.accent : Theme.canvas
        border.color: control.checked || control.activeFocus ? Theme.accent : Theme.secondary
        UiText {
            anchors.centerIn: parent
            text: control.checked ? "✓" : ""
            color: Theme.canvas
            font.weight: Font.Bold
        }
    }
    contentItem: UiText {
        id: label
        leftPadding: 34
        text: control.text
        color: control.enabled ? Theme.text : Theme.secondary
        verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        color: control.hovered ? Theme.hover : "transparent"
        border.width: control.activeFocus ? 2 : 0
        border.color: Theme.accent
        radius: 6
    }
}
