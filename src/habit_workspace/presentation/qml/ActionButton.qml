import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Button {
    id: control
    property string glyph: ""
    property string hint: text
    property bool primary: false
    property bool quiet: false
    property bool selected: false
    property bool compact: false
    property bool alignLeft: false
    implicitHeight: 36
    implicitWidth: compact ? 36 : content.implicitWidth + 24
    padding: 8
    horizontalPadding: compact ? 8 : 12
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: hint
    opacity: enabled ? 1 : 0.45
    ToolTip {
        id: tip
        parent: control
        visible: control.hovered && control.hint.length > 0
        text: control.hint
        delay: 650
        timeout: 4000
        padding: 8
        width: Math.min(360, implicitWidth)
        contentItem: UiText {
            text: tip.text
            font.pixelSize: 12
            wrapMode: Text.WrapAnywhere
        }
        background: Rectangle {
            color: Theme.surface
            border.color: Theme.border
            radius: 6
        }
        enter: Transition {
            NumberAnimation {
                property: "opacity"
                from: 0
                to: 1
                duration: Theme.duration
            }
        }
        exit: Transition {
            NumberAnimation {
                property: "opacity"
                from: 1
                to: 0
                duration: Theme.duration
            }
        }
    }
    contentItem: RowLayout {
        id: content
        spacing: 8
        Glyph {
            visible: control.glyph !== ""
            name: control.glyph
            ink: control.primary ? Theme.onPrimary : control.selected ? Theme.accent : Theme.secondary
            Layout.preferredWidth: 16
            Layout.preferredHeight: 16
        }
        UiText {
            visible: !control.compact && control.text !== ""
            text: control.text
            color: control.primary ? Theme.onPrimary : control.selected ? Theme.accent : Theme.text
            font.weight: Font.Medium
            wrapMode: Text.NoWrap
            elide: Text.ElideRight
            Layout.fillWidth: true
            horizontalAlignment: control.alignLeft ? Text.AlignLeft : Text.AlignHCenter
        }
    }
    background: Rectangle {
        radius: 6
        color: control.down ? Theme.border : control.primary ? Theme.primaryFill : control.selected ? Theme.accentSurface : control.hovered ? Theme.hover : control.quiet ? "transparent" : Theme.surface
        border.width: control.activeFocus ? 2 : control.quiet && !control.selected ? 0 : 1
        border.color: control.activeFocus ? Theme.accent : control.primary ? Theme.primaryFill : Theme.border
        Behavior on color {
            ColorAnimation {
                duration: Theme.duration
            }
        }
    }
}
