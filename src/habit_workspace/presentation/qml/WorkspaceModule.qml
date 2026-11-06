import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    property string title: ""
    property string moduleKey: ""
    property bool collapsed: false
    property bool expanded: false
    signal maximizeRequested
    default property alias contents: body.data
    implicitHeight: shell.implicitHeight + 32
    color: Theme.surface
    radius: 12
    border.color: Theme.border
    ColumnLayout {
        id: shell
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16
        RowLayout {
            Layout.fillWidth: true
            Rectangle {
                width: 3
                height: 20
                radius: 1
                color: Theme.accent
            }
            UiText {
                text: root.title
                font.weight: Font.DemiBold
                Layout.fillWidth: true
            }
            ActionButton {
                objectName: root.moduleKey + "-collapse"
                text: root.collapsed ? qsTr("Mostrar") : qsTr("Recolher")
                quiet: true
                onClicked: root.collapsed = !root.collapsed
            }
            ActionButton {
                objectName: root.moduleKey + "-expand"
                text: root.expanded ? qsTr("Restaurar") : qsTr("Ampliar")
                quiet: true
                onClicked: {
                    root.collapsed = false;
                    root.maximizeRequested();
                }
            }
        }
        ColumnLayout {
            id: body
            Layout.fillWidth: true
            visible: !root.collapsed
            spacing: 12
        }
    }
}
