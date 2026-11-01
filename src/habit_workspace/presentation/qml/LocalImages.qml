pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root
    property var images: []
    Repeater {
        model: root.images
        delegate: ColumnLayout {
            required property var modelData
            Layout.fillWidth: true
            Image {
                objectName: "local-image"
                readonly property bool decoded: status === Image.Ready
                Layout.fillWidth: true
                Layout.preferredHeight: modelData.source ? 160 : 0
                source: modelData.source || ""
                fillMode: Image.PreserveAspectFit
                Accessible.name: modelData.alt || qsTr("Imagem local")
            }
            UiText {
                Layout.fillWidth: true
                text: modelData.error || modelData.alt || ""
                color: modelData.error ? Theme.warning : Theme.secondary
            }
        }
    }
}
