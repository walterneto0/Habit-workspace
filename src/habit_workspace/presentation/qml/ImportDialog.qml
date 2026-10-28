import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Dialog {
    id: dialog
    objectName: "import-dialog"
    required property var backend
    required property var modelState
    property bool asNote: false
    modal: true
    anchors.centerIn: parent
    width: Math.min(parent.width - 32, 580)
    height: Math.min(parent.height - 32, content.implicitHeight + 48 + actionFooter.implicitHeight)
    padding: 24
    closePolicy: Popup.CloseOnEscape
    background: Rectangle {
        color: Theme.surface
        border.color: Theme.border
        radius: 14
    }
    Overlay.modal: Rectangle {
        color: "#88000000"
    }
    enter: Transition {
        NumberAnimation {
            property: "opacity"
            from: 0
            to: 1
            duration: Theme.reducedMotion ? 0 : 180
        }
    }
    exit: Transition {
        NumberAnimation {
            property: "opacity"
            from: 1
            to: 0
            duration: Theme.reducedMotion ? 0 : 150
        }
    }
    onOpened: choose.forceActiveFocus()
    onClosed: dialog.backend.cancelImport()
    contentItem: ScrollView {
        clip: true
        contentWidth: availableWidth
        ColumnLayout {
            id: content
            width: parent.width
            spacing: 16
            RowLayout {
                Layout.fillWidth: true
                UiText {
                    Layout.fillWidth: true
                    text: qsTr("Importar documento")
                    font.pixelSize: 20
                    font.weight: Font.Medium
                }
                ActionButton {
                    glyph: "close"
                    compact: true
                    quiet: true
                    hint: qsTr("Cancelar importação")
                    onClicked: dialog.close()
                }
            }
            UiText {
                Layout.fillWidth: true
                text: qsTr("Revise antes de adicionar ao cofre. O arquivo de origem será preservado.")
                color: Theme.secondary
            }
            UiText {
                text: qsTr("Tipo de arquivo")
            }
            Flow {
                Layout.fillWidth: true
                spacing: 8
                ActionButton {
                    text: qsTr("Habit Workspace")
                    selected: !dialog.asNote
                    onClicked: {
                        dialog.asNote = false;
                        dialog.backend.cancelImport();
                    }
                }
                ActionButton {
                    text: qsTr("Markdown comum como nota")
                    selected: dialog.asNote
                    onClicked: {
                        dialog.asNote = true;
                        dialog.backend.cancelImport();
                    }
                }
            }
            ActionButton {
                id: choose
                Layout.fillWidth: true
                text: qsTr("Escolher arquivo .md")
                glyph: "folder"
                onClicked: picker.open()
            }
            ColumnLayout {
                Layout.fillWidth: true
                visible: !!dialog.modelState.importPreview.title
                spacing: 12
                UiText {
                    Layout.fillWidth: true
                    text: dialog.modelState.importPreview.title || ""
                    font.pixelSize: 16
                    font.weight: Font.Medium
                }
                UiText {
                    Layout.fillWidth: true
                    text: (dialog.modelState.importPreview.kind || "") + " · " + (dialog.modelState.importPreview.id || "")
                    color: Theme.muted
                    wrapMode: Text.WrapAnywhere
                }
                UiText {
                    Layout.fillWidth: true
                    text: dialog.modelState.importPreview.path || ""
                    color: Theme.muted
                    wrapMode: Text.WrapAnywhere
                    font.pixelSize: 11
                }
                UiText {
                    Layout.fillWidth: true
                    text: dialog.modelState.importPreview.excerpt || ""
                    color: Theme.secondary
                    wrapMode: Text.WrapAnywhere
                }
                UiText {
                    Layout.fillWidth: true
                    text: dialog.modelState.importPreview.conflict ? qsTr("Conflito de UUID. Compare este arquivo com o original no seu editor. A importação não substituirá nenhum deles.") : dialog.modelState.importPreview.identical ? qsTr("Arquivo idêntico já presente. Não será criada outra cópia.") : qsTr("%1 referência(s) indisponível(is). Dependências não acompanham um arquivo isolado.").arg(dialog.modelState.importPreview.missingCount || 0)
                    color: dialog.modelState.importPreview.conflict || dialog.modelState.importPreview.missingCount > 0 ? Theme.warning : Theme.secondary
                }
            }
            UiText {
                Layout.fillWidth: true
                visible: dialog.modelState.noticeError
                text: dialog.modelState.notice
                color: Theme.error
                wrapMode: Text.WrapAnywhere
            }
        }
    }
    footer: Item {
        id: actionFooter
        implicitHeight: dialog.modelState.importPreview.title ? 60 : 0
        visible: !!dialog.modelState.importPreview.title
        ActionButton {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 24
            anchors.rightMargin: 24
            text: qsTr("Confirmar importação")
            primary: true
            enabled: !dialog.modelState.importPreview.conflict
            onClicked: {
                if (dialog.backend.confirmImport())
                    dialog.close();
            }
        }
    }
    FileDialog {
        id: picker
        title: qsTr("Selecionar documento")
        nameFilters: [qsTr("Documentos Markdown (*.md)")]
        acceptLabel: qsTr("Revisar arquivo")
        rejectLabel: qsTr("Cancelar")
        onAccepted: dialog.backend.previewImport(selectedFile.toString(), dialog.asNote)
    }
}
