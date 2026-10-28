pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: listing
    required property var backend
    required property var modelState
    signal importRequested
    signal propertiesRequested
    spacing: 12
    RowLayout {
        Layout.fillWidth: true
        UiText {
            text: qsTr("Documentos")
            font.weight: Font.Medium
            Layout.fillWidth: true
        }
        UiText {
            text: String(listing.modelState.documents.length)
            color: Theme.muted
        }
    }
    EmptyState {
        Layout.fillWidth: true
        visible: listing.modelState.documents.length === 0
        heading: listing.modelState.query ? qsTr("Nenhum resultado") : listing.modelState.period ? qsTr("Um espaço para este período") : qsTr("Seu cofre está pronto para começar")
        description: listing.modelState.query ? qsTr("Tente outro título, tag ou identificador.") : listing.modelState.period ? qsTr("Nenhum documento vinculado. Você pode explorar os períodos livremente ou importar uma página existente.") : qsTr("Importe uma nota ou página do Habit Workspace. Seus arquivos continuam locais e legíveis em outros editores.")
        action: listing.modelState.hasVault && !listing.modelState.query ? qsTr("Importar documento") : ""
        onActivated: listing.importRequested()
    }
    Repeater {
        model: listing.modelState.documents
        delegate: Button {
            id: documentRow
            required property var modelData
            Layout.fillWidth: true
            implicitHeight: Math.max(68, rowContent.implicitHeight + 24)
            padding: 12
            hoverEnabled: true
            Accessible.name: modelData.title + ", " + modelData.kind + (modelData.conflict ? qsTr(", conflito de identidade") : "")
            onClicked: listing.backend.selectDocument(modelData.id)
            contentItem: RowLayout {
                id: rowContent
                spacing: 12
                Glyph {
                    name: "note"
                    ink: documentRow.modelData.conflict ? Theme.warning : Theme.secondary
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    UiText {
                        Layout.fillWidth: true
                        text: documentRow.modelData.title
                        font.weight: Font.Medium
                    }
                    UiText {
                        Layout.fillWidth: true
                        text: documentRow.modelData.kind + " · " + documentRow.modelData.path
                        color: Theme.muted
                        font.pixelSize: 11
                        wrapMode: Text.WrapAnywhere
                    }
                    UiText {
                        Layout.fillWidth: true
                        visible: documentRow.modelData.conflict || documentRow.modelData.missing > 0
                        text: documentRow.modelData.conflict ? qsTr("Conflito de identidade · compare os arquivos") : qsTr("%1 referência(s) indisponível(is)").arg(documentRow.modelData.missing)
                        color: Theme.warning
                        font.pixelSize: 11
                    }
                }
                Glyph {
                    name: "right"
                    width: 14
                    height: 14
                }
            }
            background: Rectangle {
                radius: 8
                color: documentRow.hovered ? Theme.hover : listing.modelState.selected.id === documentRow.modelData.id ? Theme.accentSurface : Theme.surface
                border.color: documentRow.activeFocus ? Theme.accent : Theme.border
                border.width: documentRow.activeFocus ? 2 : 1
                Behavior on color {
                    ColorAnimation {
                        duration: Theme.duration
                    }
                }
            }
        }
    }
    Surface {
        Layout.fillWidth: true
        visible: !!listing.modelState.selected.id
        ColumnLayout {
            anchors.fill: parent
            spacing: 16
            RowLayout {
                Layout.fillWidth: true
                UiText {
                    Layout.fillWidth: true
                    text: listing.modelState.selected.title || ""
                    font.pixelSize: 17
                    font.weight: Font.Medium
                }
                ActionButton {
                    glyph: "info"
                    compact: true
                    hint: qsTr("Propriedades do documento")
                    onClicked: listing.propertiesRequested()
                }
                ActionButton {
                    glyph: "close"
                    compact: true
                    quiet: true
                    hint: qsTr("Fechar prévia")
                    onClicked: listing.backend.clearSelection()
                }
            }
            UiText {
                text: qsTr("PRÉVIA DE LEITURA")
                font.pixelSize: 10
                font.letterSpacing: 1
                color: Theme.muted
            }
            UiText {
                Layout.fillWidth: true
                text: listing.modelState.selected.excerpt || qsTr("Este documento não contém texto de nota.")
                color: Theme.secondary
                lineHeight: 1.4
                wrapMode: Text.WrapAnywhere
            }
            UiText {
                visible: !!listing.modelState.selected.truncated
                Layout.fillWidth: true
                text: qsTr("Prévia abreviada. O texto completo está preservado no arquivo original.")
                color: Theme.muted
            }
            Repeater {
                model: listing.modelState.selected.records || []
                delegate: RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    UiText {
                        Layout.fillWidth: true
                        text: parent.modelData.label
                    }
                    UiText {
                        text: parent.modelData.value
                        color: Theme.secondary
                        Layout.maximumWidth: listing.width / 2
                    }
                }
            }
            UiText {
                Layout.fillWidth: true
                visible: (listing.modelState.selected.missing || 0) > 0
                text: qsTr("Há referências indisponíveis. Os rótulos e registros acima são os que vieram no documento; as fontes ausentes não foram recriadas.")
                color: Theme.warning
            }
        }
    }
}
