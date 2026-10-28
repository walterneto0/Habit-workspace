import QtQuick
import QtQuick.Layouts

Surface {
    id: empty
    property string heading: ""
    property string description: ""
    property string glyph: "note"
    property string action: ""
    signal activated
    padding: 32
    ColumnLayout {
        anchors.fill: parent
        spacing: 12
        Rectangle {
            Layout.alignment: Qt.AlignHCenter
            Layout.bottomMargin: 8
            width: 48
            height: 48
            radius: 14
            color: Theme.accentSurface
            Glyph {
                anchors.centerIn: parent
                width: 24
                height: 24
                name: empty.glyph
                ink: Theme.accent
            }
        }
        UiText {
            Layout.fillWidth: true
            text: empty.heading
            font.pixelSize: 17
            font.weight: Font.Medium
            horizontalAlignment: Text.AlignHCenter
        }
        UiText {
            Layout.fillWidth: true
            text: empty.description
            color: Theme.secondary
            horizontalAlignment: Text.AlignHCenter
            lineHeight: 1.3
        }
        ActionButton {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: 8
            visible: empty.action !== ""
            text: empty.action
            glyph: "download"
            onClicked: empty.activated()
        }
    }
}
