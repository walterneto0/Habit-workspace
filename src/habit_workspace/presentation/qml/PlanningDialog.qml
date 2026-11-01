pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: dialog
    objectName: "planning-dialog"
    required property var backend
    required property var modelState
    readonly property var form: modelState.planningForm || ({})
    readonly property bool wanted: !!form.open
    readonly property bool busy: !!modelState.planningSaving
    modal: true
    anchors.centerIn: parent
    width: Math.min(parent.width - 32, 600)
    height: Math.min(parent.height - 32, 710)
    padding: 20
    closePolicy: Popup.NoAutoClose
    background: Rectangle { color: Theme.surface; border.color: Theme.border; radius: 14 }
    Overlay.modal: Rectangle { color: "#88000000" }
    onWantedChanged: wanted ? open() : close()
    onAboutToShow: {
        titleInput.text = form.title || ""; body.text = form.body || "";
        tags.text = form.tags || ""; start.text = form.start || ""; end.text = form.end || "";
        home.text = form.home || "";
        cadence.currentIndex = Math.max(0, cadence.values.indexOf(form.cadence || "home_only"));
        due.text = form.due || ""; progress.text = form.progress || "";
        status.currentIndex = Math.max(0, ["not_started","in_progress","achieved","paused","abandoned"].indexOf(form.status));
    }
    onOpened: titleInput.forceActiveFocus()
    function save() {
        backend.planningActions.save({home:home.text, cadence:cadence.values[cadence.currentIndex], title:titleInput.text, body:body.text, tags:tags.text, start:start.text, end:end.text, due:due.text, progress:progress.text, status:["not_started","in_progress","achieved","paused","abandoned"][status.currentIndex]});
    }
    header: UiText { padding: 20; text: dialog.form.kind === "goal" ? qsTr("Objetivo · detalhes e edição") : qsTr("Tarefa · detalhes e edição"); font.pixelSize: 20 }
    footer: RowLayout {
        spacing: 8
        Item { Layout.fillWidth: true }
        ActionButton { objectName: "planning-cancel"; text: qsTr("Cancelar / Voltar"); enabled: !dialog.busy; onClicked: dialog.backend.planningActions.cancel() }
        ActionButton { objectName: "planning-save"; text: dialog.busy ? qsTr("Salvando…") : qsTr("Salvar"); primary: true; enabled: !dialog.busy; onClicked: dialog.save() }
    }
    contentItem: ScrollView {
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            width: parent.width
            spacing: 8
            enabled: !dialog.busy
            UiText { text: qsTr("Título") }
            Input { id: titleInput; objectName: "planning-title"; Layout.fillWidth: true; Accessible.name: qsTr("Título"); onAccepted: dialog.save() }
            UiText { text: qsTr("Descrição") }
            TextArea { id: body; objectName: "planning-body"; Layout.fillWidth: true; Layout.preferredHeight: 100; wrapMode: TextEdit.Wrap; Keys.onTabPressed: (event) => { tags.forceActiveFocus(); event.accepted = true; } Keys.onBacktabPressed: (event) => { titleInput.forceActiveFocus(); event.accepted = true; } color: Theme.text; selectByMouse: true; Accessible.name: qsTr("Descrição"); background: Rectangle { color: Theme.canvas; border.color: Theme.border; radius: 6 } }
            UiText { text: qsTr("Tags separadas por vírgula") }
            Input { id: tags; objectName: "planning-tags"; Layout.fillWidth: true; Accessible.name: qsTr("Tags") }
            UiText { Layout.fillWidth: true; text: qsTr("Escopo · início e fim inclusivo (AAAA-MM-DD). Fim vazio = sem término.") }
            Input { id: start; objectName: "planning-start"; Layout.fillWidth: true; Accessible.name: qsTr("Início do escopo") }
            Input { id: end; objectName: "planning-end"; Layout.fillWidth: true; Accessible.name: qsTr("Fim inclusivo do escopo") }
            UiText { visible: dialog.form.kind === "task"; text: qsTr("Prazo opcional · independente do escopo") }
            Input { id: due; objectName: "planning-due"; visible: dialog.form.kind === "task"; Layout.fillWidth: true; placeholderText: "AAAA-MM-DD"; Accessible.name: qsTr("Prazo opcional") }
            Input { id: home; objectName: "goal-home"; visible: dialog.form.kind === "goal"; Layout.fillWidth: true; placeholderText: qsTr("Pertence ao período · year/2026"); Accessible.name: placeholderText }
            StudioChoice {
                id: cadence
                objectName: "goal-cadence"
                visible: dialog.form.kind === "goal"
                Layout.fillWidth: true
                label: qsTr("Acompanhar")
                property var values: {
                    let scale = home.text.split("/")[0];
                    return scale === "year" ? ["home_only","month","week","day"] :
                           scale === "month" ? ["home_only","week","day"] :
                           scale === "week" ? ["home_only","day"] : ["home_only"];
                }
                model: values.map(v => ({home_only:qsTr("Somente neste período"),month:qsTr("Mensal"),week:qsTr("Semanal"),day:qsTr("Diário")}[v]))
            }
            StudioChoice { id: status; objectName: "planning-status"; visible: dialog.form.kind === "goal"; Layout.fillWidth: true; label: qsTr("Status"); model: [qsTr("Não iniciado"),qsTr("Em andamento"),qsTr("Alcançado"),qsTr("Pausado"),qsTr("Abandonado")] }
            Input { id: progress; objectName: "planning-progress"; visible: dialog.form.kind === "goal"; Layout.fillWidth: true; placeholderText: qsTr("Progresso manual 0–100, vazio = não informado"); Accessible.name: placeholderText }
            UiText { Layout.fillWidth: true; visible: dialog.form.kind === "goal"; text: qsTr("Progresso e status são independentes. Tarefas e hábitos não alteram este valor."); color: Theme.secondary }
            UiText { objectName: "planning-error"; Layout.fillWidth: true; text: dialog.form.error || ""; visible: text.length > 0; color: Theme.error; Accessible.role: Accessible.AlertMessage }
        }
    }
}
