pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Dialog {
    id: dialog
    objectName: "vault-dialog"
    required property var backend
    required property var modelState
    property bool creating: false
    modal: true
    anchors.centerIn: parent
    width: Math.min(parent.width - 32, 540)
    height: Math.min(parent.height - 32, content.implicitHeight + 48)
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
    onOpened: directory.forceActiveFocus()
    contentItem: ScrollView {
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            id: content
            width: parent.width
            spacing: 16
            RowLayout {
                Layout.fillWidth: true
                UiText {
                    Layout.fillWidth: true
                    text: qsTr("Seu espaço, seus arquivos")
                    font.pixelSize: 20
                    font.weight: Font.Medium
                }
                ActionButton {
                    glyph: "close"
                    compact: true
                    quiet: true
                    hint: qsTr("Fechar")
                    onClicked: dialog.close()
                }
            }
            UiText {
                Layout.fillWidth: true
                text: qsTr("Escolha uma pasta neste dispositivo. Nenhuma conta necessária.")
                color: Theme.secondary
            }
            RowLayout {
                ActionButton {
                    text: qsTr("Abrir existente")
                    selected: !dialog.creating
                    onClicked: dialog.creating = false
                }
                ActionButton {
                    text: qsTr("Criar cofre")
                    selected: dialog.creating
                    onClicked: dialog.creating = true
                }
            }
            UiText {
                text: qsTr("Nome do cofre")
                visible: dialog.creating
            }
            Input {
                id: vaultName
                objectName: "vault-name"
                Layout.fillWidth: true
                visible: dialog.creating
                placeholderText: qsTr("Ex.: Meu espaço")
                maximumLength: 100
            }
            UiText {
                text: dialog.creating ? qsTr("Pasta nova ou vazia") : qsTr("Pasta do cofre")
            }
            RowLayout {
                Layout.fillWidth: true
                Input {
                    id: directory
                    objectName: "vault-directory"
                    Layout.fillWidth: true
                    placeholderText: qsTr("Caminho da pasta local")
                    onAccepted: submit.clicked()
                }
                ActionButton {
                    glyph: "folder"
                    compact: true
                    hint: qsTr("Escolher pasta")
                    onClicked: folderPicker.open()
                }
            }
            UiText {
                Layout.fillWidth: true
                visible: dialog.modelState.noticeError
                text: dialog.modelState.notice
                color: Theme.error
                wrapMode: Text.WrapAnywhere
            }
            ActionButton {
                id: submit
                objectName: "vault-submit"
                Layout.fillWidth: true
                primary: true
                enabled: directory.text.trim().length > 0 && (!dialog.creating || vaultName.text.trim().length > 0)
                text: dialog.creating ? qsTr("Criar cofre nesta pasta") : qsTr("Abrir cofre")
                onClicked: {
                    if (!enabled)
                        return;
                    const ok = dialog.creating ? dialog.backend.createVault(directory.text, vaultName.text) : dialog.backend.openVault(directory.text);
                    if (ok)
                        dialog.close();
                }
            }
            UiText {
                visible: dialog.modelState.recentVaults.length > 0
                text: qsTr("ABERTOS RECENTEMENTE")
                color: Theme.muted
                font.pixelSize: 10
                font.letterSpacing: 1
            }
            Repeater {
                model: dialog.modelState.recentVaults
                delegate: ActionButton {
                    required property string modelData
                    Layout.fillWidth: true
                    text: modelData
                    hint: qsTr("Abrir %1").arg(modelData)
                    glyph: "folder"
                    quiet: true
                    onClicked: {
                        if (dialog.backend.openVault(modelData))
                            dialog.close();
                    }
                }
            }
        }
    }
    FolderDialog {
        id: folderPicker
        title: dialog.creating ? qsTr("Escolher uma pasta vazia") : qsTr("Abrir cofre existente")
        acceptLabel: qsTr("Selecionar pasta")
        rejectLabel: qsTr("Cancelar")
        onAccepted: directory.text = selectedFolder.toString()
    }
}
