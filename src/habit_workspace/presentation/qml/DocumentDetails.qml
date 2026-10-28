pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: details
    required property var backend
    required property var document
    spacing: 20
    UiText {
        text: qsTr("Propriedades")
        font.pixelSize: 15
        font.weight: Font.Medium
    }
    Repeater {
        model: [
            {
                label: qsTr("TIPO"),
                value: details.document.kind || ""
            },
            {
                label: qsTr("PERÍODO"),
                value: details.document.period || qsTr("Sem período vinculado")
            },
            {
                label: qsTr("TAGS"),
                value: details.document.tags || qsTr("Sem tags")
            },
            {
                label: qsTr("IDENTIDADE"),
                value: details.document.id || ""
            },
            {
                label: qsTr("ARQUIVO"),
                value: details.document.path || ""
            }
        ]
        delegate: ColumnLayout {
            required property var modelData
            Layout.fillWidth: true
            spacing: 6
            UiText {
                text: parent.modelData.label
                color: Theme.muted
                font.pixelSize: 10
                font.letterSpacing: 1
            }
            UiText {
                Layout.fillWidth: true
                text: parent.modelData.value
                wrapMode: Text.WrapAnywhere
                color: Theme.secondary
            }
        }
    }
    ActionButton {
        Layout.fillWidth: true
        text: qsTr("Revelar pasta do arquivo")
        glyph: "folder"
        onClicked: details.backend.revealSelected()
    }
    UiText {
        Layout.fillWidth: true
        text: qsTr("O arquivo é a fonte original. Mover ou renomear não altera sua identidade.")
        font.pixelSize: 12
        color: Theme.muted
    }
}
