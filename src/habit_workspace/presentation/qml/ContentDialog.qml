pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Dialog {
    id: dialog
    objectName: "content-dialog"
    required property var backend
    required property var modelState
    readonly property var form: modelState.contentForm || ({})
    readonly property int imageRevision: form.imageRevision || 0
    onImageRevisionChanged: { if (wanted && imageRevision) body.text = form.body || ""; }
    function values() { return {title:titleInput.text, body:body.text, period:period.text, rating:rating.text}; }
    FileDialog {
        id: imagePicker
        objectName: "note-image-picker"
        title: qsTr("Selecionar imagem local · até 2 MiB e 4 milhões de pixels")
        nameFilters: [qsTr("Imagens (*.png *.jpg *.jpeg *.webp *.gif)")]
        onAccepted: dialog.backend.contentActions.importImage(selectedFile.toString(), alt.text, dialog.values())
    }
    readonly property bool wanted: !!form.open
    readonly property bool busy: !!modelState.planningSaving
    implicitWidth: 820
    modal: true
    anchors.centerIn: parent
    width: Math.min(parent.width - 32, 820)
    height: Math.min(parent.height - 32, 760)
    padding: 20
    closePolicy: Popup.NoAutoClose
    background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: 14 }
    Overlay.modal: Rectangle { color: "#88000000" }
    onWantedChanged: wanted ? open() : close()
    onAboutToShow: {
        titleInput.text = form.title || "";
        body.text = form.body || "";
        period.text = form.period || "";
        preview.checked = false;
        rating.text = form.rating || "";
        alt.text = "";
    }
    onOpened: body.forceActiveFocus()
    header: UiText {
        padding: 20
        text: dialog.form.followup ? qsTr("Acompanhamento do objetivo · ") + dialog.form.followup :
              dialog.form.region ? qsTr("Texto da página · região Markdown") : dialog.form.kind === "review" ? qsTr("Avaliação do período · Markdown") : qsTr("Nota independente · Markdown")
        font.pixelSize: 18
    }
    footer: RowLayout {
        Item { Layout.fillWidth: true }
        ActionButton { objectName: "content-cancel"; text: qsTr("Cancelar / Voltar"); enabled: !dialog.busy; onClicked: dialog.backend.contentActions.cancel() }
        ActionButton {
            id: saveButton; objectName: "content-save"; text: dialog.busy ? qsTr("Salvando…") : qsTr("Salvar")
            enabled: !dialog.busy && !dialog.form.readonly
            primary: true
            onClicked: dialog.backend.contentActions.save(dialog.values())
        }
    }
    contentItem: ColumnLayout {
        implicitWidth: 400
        enabled: !dialog.busy
        Input { id: titleInput; objectName: "content-title"; Layout.fillWidth: true; visible: !dialog.form.region && !dialog.form.followup; placeholderText: qsTr("Título"); Accessible.name: placeholderText }
        Input { id: period; objectName: "content-period"; Layout.fillWidth: true; visible: !dialog.form.region && !dialog.form.followup; placeholderText: (dialog.form.kind === "review" ? qsTr("Período obrigatório: ") : qsTr("Período opcional: ")) + "year/2026, month/2026-10, week/2026-W44, day/2026-10-29"; Accessible.name: placeholderText }
        Input { id: rating; objectName: "review-rating"; Layout.fillWidth: true; visible: dialog.form.kind === "review"; placeholderText: qsTr("Avaliação manual opcional · inteiro de 1 a 5"); Accessible.name: placeholderText }
        RowLayout {
            Layout.fillWidth: true
            visible: !dialog.form.followup
            Input { id: alt; objectName: "image-alt"; Layout.fillWidth: true; placeholderText: qsTr("Descrição alternativa da imagem"); Accessible.name: placeholderText }
            ActionButton { objectName: "content-image-select"; text: qsTr("Inserir imagem local"); enabled: !dialog.form.readonly; onClicked: imagePicker.open() }
        }
        CheckBox { id: preview; objectName: "content-preview"; onToggled: { if (checked) dialog.backend.contentActions.previewImages(body.text); } text: qsTr("Prévia segura · Markdown sem recursos ativos") }
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            TextArea {
                id: body
                objectName: "content-body"
                Keys.onTabPressed: (event) => { saveButton.forceActiveFocus(); event.accepted = true; }
                Keys.onBacktabPressed: (event) => { preview.forceActiveFocus(); event.accepted = true; }
                textFormat: TextEdit.PlainText
                readOnly: preview.checked || !!dialog.form.readonly
                wrapMode: TextEdit.Wrap
                selectByMouse: true
                color: Theme.text
                Accessible.name: qsTr("Conteúdo Markdown completo")
                background: Rectangle { color: Theme.canvas; border.color: body.activeFocus ? Theme.accent : Theme.border }
            }
        }
        ScrollView {
            visible: preview.checked
            Layout.fillWidth: true
            Layout.preferredHeight: preview.checked ? 180 : 0
            contentWidth: availableWidth
            LocalImages { width: parent.width; images: dialog.form.images || [] }
        }
        UiText { Layout.fillWidth: true; text: dialog.form.error || ""; visible: text.length > 0; color: Theme.error; Accessible.role: Accessible.AlertMessage }
    }
}
