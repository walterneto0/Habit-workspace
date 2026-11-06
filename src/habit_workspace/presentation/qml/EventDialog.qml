pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Dialog {
    id: dialog
    objectName: "event-dialog"
    required property var backend
    required property var modelState
    readonly property var form: modelState.eventForm || ({})
    readonly property bool wanted: !!form.open
    property string selectedZone: ""
    property string startChoice: ""
    property string endChoice: ""
    readonly property var zoneOptions: backend ? backend.eventActions.zoneOptions(zoneSearch.text) : []
    readonly property var startOptions: backend && wanted && !allDay.checked ? backend.eventActions.wallOptions(start.text, startTime.text, selectedZone) : []
    readonly property var endOptions: backend && wanted && !allDay.checked ? backend.eventActions.wallOptions(end.text, endTime.text, selectedZone) : []
    function values() { return {title:titleInput.text, body:body.text, tags:tags.text, start:start.text, end:end.text, startTime:startTime.text, endTime:endTime.text, timezone:selectedZone, startChoice:startChoice, endChoice:endChoice, allDay:allDay.checked}; }
    modal: true
    anchors.centerIn: parent
    width: Math.min(parent.width - 32, 660)
    height: Math.min(parent.height - 32, 760)
    padding: 20
    closePolicy: Popup.NoAutoClose
    background: Rectangle { color: Theme.surface; radius: 14; border.color: Theme.border }
    Overlay.modal: Rectangle { color: "#88000000" }
    onWantedChanged: wanted ? open() : close()
    onAboutToShow: {
        titleInput.text = form.title; body.text = form.body; tags.text = form.tags;
        start.text = form.start; end.text = form.end; startTime.text = form.startTime; endTime.text = form.endTime;
        selectedZone = form.timezone; zoneSearch.text = "";
        startChoice = form.startChoice || ""; endChoice = form.endChoice || ""; allDay.checked = form.allDay;
    }
    onOpened: titleInput.forceActiveFocus()
    header: UiText { text: qsTr("Evento · datas concretas"); padding: 20; font.pixelSize: 18 }
    footer: RowLayout {
        Item { Layout.fillWidth: true }
        ActionButton { objectName: "event-cancel"; text: qsTr("Cancelar"); enabled: !dialog.modelState.planningSaving; onClicked: dialog.backend.eventActions.cancel() }
        ActionButton { id: saveButton; objectName: "event-save"; text: dialog.modelState.planningSaving ? qsTr("Salvando…") : qsTr("Salvar"); primary: true; enabled: !dialog.modelState.planningSaving; onClicked: dialog.backend.eventActions.save(dialog.values()) }
    }
    contentItem: ScrollView {
        id: scroll
        objectName: "event-scroll"
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            width: scroll.availableWidth
            spacing: 8
            enabled: !dialog.modelState.planningSaving
            Input { id: titleInput; objectName: "event-titleInput"; Layout.fillWidth: true; placeholderText: qsTr("Título"); Accessible.name: placeholderText }
            StudioCheckBox { id: allDay; objectName: "event-all-day"; text: qsTr("Dia inteiro") }
            UiText { Layout.fillWidth: true; text: qsTr("Datas · DD/MM/AAAA"); color: Theme.secondary }
            Input { id: start; objectName: "event-start"; Layout.fillWidth: true; placeholderText: qsTr("Data inicial · DD/MM/AAAA"); Accessible.name: placeholderText }
            Input { id: end; objectName: "event-end"; Layout.fillWidth: true; placeholderText: allDay.checked ? qsTr("Último dia incluído · DD/MM/AAAA") : qsTr("Data final · DD/MM/AAAA"); Accessible.name: placeholderText }
            Input { id: startTime; objectName: "event-startTime"; Layout.fillWidth: true; visible: !allDay.checked; placeholderText: qsTr("Hora inicial · HH:MM"); Accessible.name: placeholderText }
            Input { id: endTime; objectName: "event-endTime"; Layout.fillWidth: true; visible: !allDay.checked; placeholderText: qsTr("Hora final · HH:MM"); Accessible.name: placeholderText }
            UiText { Layout.fillWidth: true; text: qsTr("Fuso horário · selecione uma cidade ou região") }
            Input { id: zoneSearch; objectName: "event-zone-search"; Layout.fillWidth: true; placeholderText: qsTr("Buscar fuso · ex.: Recife, New York, Lisboa (Lisbon)"); Accessible.name: placeholderText }
            StudioChoice {
                objectName: "event-zone"
                Layout.fillWidth: true
                label: qsTr("Selecionar fuso IANA")
                model: dialog.zoneOptions
                currentIndex: dialog.zoneOptions.indexOf(dialog.selectedZone)
                displayText: currentIndex < 0 ? qsTr("Selecione um resultado da busca") : currentText.replace(/_/g, " ")
                onActivated: dialog.selectedZone = dialog.zoneOptions[currentIndex]
            }
            UiText { objectName: "event-zone-selected"; Layout.fillWidth: true; text: qsTr("Fuso selecionado: ") + dialog.selectedZone }
            UiText { Layout.fillWidth: true; text: dialog.form.zoneNotice || ""; color: Theme.secondary; font.pixelSize: 12 }
            UiText { Layout.fillWidth: true; text: allDay.checked ? qsTr("Dia inteiro usa datas civis neste fuso. As datas não mudam em outro computador.") : qsTr("As horas digitadas pertencem ao fuso selecionado. Alterar o fuso mantém essas horas; revise antes de salvar."); color: Theme.secondary; font.pixelSize: 12 }
            UiText { Layout.fillWidth: true; visible: dialog.startOptions.length === 2; text: qsTr("A hora inicial ocorre duas vezes. Escolha qual ocorrência deseja."); color: Theme.warning }
            StudioChoice {
                objectName: "event-start-choice"
                Layout.fillWidth: true
                visible: dialog.startOptions.length === 2
                label: qsTr("Desambiguar hora inicial")
                model: dialog.startOptions
                textRole: "label"
                currentIndex: dialog.startOptions.findIndex(o => o.value === dialog.startChoice)
                displayText: currentIndex < 0 ? qsTr("Escolha primeira ou segunda ocorrência") : currentText
                onActivated: dialog.startChoice = dialog.startOptions[currentIndex].value
            }
            UiText { Layout.fillWidth: true; visible: dialog.endOptions.length === 2; text: qsTr("A hora final ocorre duas vezes. Escolha qual ocorrência deseja."); color: Theme.warning }
            StudioChoice {
                objectName: "event-end-choice"
                Layout.fillWidth: true
                visible: dialog.endOptions.length === 2
                label: qsTr("Desambiguar hora final")
                model: dialog.endOptions
                textRole: "label"
                currentIndex: dialog.endOptions.findIndex(o => o.value === dialog.endChoice)
                displayText: currentIndex < 0 ? qsTr("Escolha primeira ou segunda ocorrência") : currentText
                onActivated: dialog.endChoice = dialog.endOptions[currentIndex].value
            }
            Input { id: tags; objectName: "event-tags"; Layout.fillWidth: true; placeholderText: qsTr("Tags separadas por vírgula"); Accessible.name: placeholderText }
            TextArea {
                id: body
                objectName: "event-body"
                Layout.fillWidth: true
                Layout.preferredHeight: 130
                placeholderText: qsTr("Descrição Markdown")
                Accessible.name: placeholderText
                wrapMode: TextEdit.Wrap
                textFormat: TextEdit.PlainText
                color: Theme.text
                Keys.onTabPressed: (event) => { saveButton.forceActiveFocus(); event.accepted = true; }
                Keys.onBacktabPressed: (event) => { tags.forceActiveFocus(); event.accepted = true; }
            }
            UiText { objectName: "event-error"; Layout.fillWidth: true; text: dialog.form.error || ""; Accessible.role: Accessible.AlertMessage; color: Theme.warning }
        }
    }
}
