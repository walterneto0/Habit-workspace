pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Surface {
    id: root
    required property var backend
    required property var modelState
    property bool showCompleted: true
    readonly property var rows: (modelState.planning || []).filter(r => showCompleted || r.status !== "completed")
    ColumnLayout {
        anchors.fill: parent
        spacing: 10
        UiText { text: qsTr("Planejamento pessoal"); font.weight: Font.Medium }
        Flow {
            Layout.fillWidth: true
            spacing: 8
            ActionButton { objectName: "new-task"; text: qsTr("Nova tarefa"); enabled: !root.modelState.planningSaving; onClicked: root.backend.planningActions.create("task") }
            ActionButton { objectName: "new-goal"; text: qsTr("Novo objetivo"); enabled: !root.modelState.planningSaving; onClicked: root.backend.planningActions.create("goal") }
            ActionButton { objectName: "planning-all"; text: qsTr("Todos os períodos e pendências"); onClicked: root.backend.navigate("planning", "") }
            ActionButton { text: root.showCompleted ? qsTr("Ocultar concluídas") : qsTr("Mostrar concluídas"); onClicked: root.showCompleted = !root.showCompleted }
        }
        ActionButton { objectName: "new-event"; text: qsTr("Novo evento"); onClicked: root.backend.eventActions.create() }
        UiText { visible: !!root.modelState.period; text: qsTr("Agenda · datas no fuso de cada evento"); font.weight: Font.Medium }
        Flow {
            visible: !!root.modelState.period
            Layout.fillWidth: true
            spacing: 8
            ActionButton { objectName: "agenda-previous"; enabled: !!(root.modelState.agendaWindow || {}).previous; text: qsTr("31 dias anteriores"); onClicked: root.backend.eventActions.page(-1) }
            ActionButton { objectName: "agenda-next"; enabled: !!(root.modelState.agendaWindow || {}).next; text: qsTr("Próximos 31 dias"); onClicked: root.backend.eventActions.page(1) }
        }
        UiText { Layout.fillWidth: true; visible: !!root.modelState.period && !(root.modelState.agenda || []).length; text: qsTr("Nenhuma entrada de agenda nesta janela de datas."); color: Theme.secondary }
        UiText { Layout.fillWidth: true; visible: !!root.modelState.period; text: (root.modelState.agendaWindow || {}).label || ""; color: Theme.secondary }
        Repeater {
            model: root.modelState.agendaGroups || []
            delegate: ColumnLayout {
                id: dayGroup
                required property var modelData
                Layout.fillWidth: true
                spacing: 6
                UiText { objectName: "agenda-day-" + dayGroup.modelData.day; Layout.fillWidth: true; text: dayGroup.modelData.label; font.weight: Font.Medium }
                Repeater {
                    model: dayGroup.modelData.rows
                    delegate: ColumnLayout {
                        id: entry
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 2
                        ActionButton {
                            objectName: "agenda-open-" + entry.modelData.source_id + "-" + entry.modelData.display_day
                            Layout.fillWidth: true
                            alignLeft: true
                            text: (entry.modelData.source_kind === "event" ? (entry.modelData.all_day ? qsTr("Evento · dia inteiro") : qsTr("Evento")) : entry.modelData.source_kind === "task" ? qsTr("Prazo da tarefa") : qsTr("Hábito programado")) + " · " + entry.modelData.title
                            hint: text + " · " + dayGroup.modelData.label
                            onClicked: root.backend.eventActions.openOccurrence(entry.modelData.source_kind, entry.modelData.source_id, entry.modelData.display_day)
                        }
                        UiText {
                            objectName: "agenda-detail-" + entry.modelData.source_id + "-" + entry.modelData.display_day
                            Layout.fillWidth: true
                            text: [entry.modelData.time_label, entry.modelData.timezone, entry.modelData.status_label,
                                   entry.modelData.conflict ? qsTr("UUID ou registro ambíguo · confira as pendências") : "",
                                   entry.modelData.missing ? qsTr("Dependência ausente · nada foi recriado") : ""].filter(Boolean).join(" · ")
                            color: entry.modelData.conflict || entry.modelData.missing ? Theme.warning : Theme.secondary
                            font.pixelSize: 12
                        }
                    }
                }
            }
        }
        Input { objectName: "planning-search"; Layout.fillWidth: true; placeholderText: qsTr("Buscar tarefas, objetivos e eventos por título, descrição ou tag"); Accessible.name: placeholderText; text: root.modelState.query || ""; onTextEdited: root.backend.setQuery(text) }
        Repeater {
            model: root.modelState.eventResults || []
            delegate: ActionButton {
                required property var modelData
                Layout.fillWidth: true
                text: qsTr("Evento · ") + modelData.title
                onClicked: root.backend.eventActions.open("event", modelData.id)
            }
        }
        UiText { Layout.fillWidth: true; text: qsTr("O escopo organiza o contexto. O prazo é independente. Estados exibidos são os atuais, inclusive em períodos passados."); color: Theme.secondary; font.pixelSize: 12 }
        UiText { Layout.fillWidth: true; visible: !root.rows.length; text: qsTr("Nenhum item encontrado. Crie uma tarefa ou objetivo, ou ajuste a busca."); color: Theme.secondary }
        Repeater {
            model: root.rows
            delegate: PlanningRow {
                required property var modelData
                Layout.fillWidth: true
                row: modelData
                busy: !!root.modelState.planningSaving
                onEdit: root.backend.planningActions.edit(row.id)
                onComplete: root.backend.planningActions.complete(row.id, row.status !== "completed", row.token)
            }
        }
        UiText { visible: !!root.modelState.planningSaving; text: qsTr("Salvando…"); Accessible.role: Accessible.AlertMessage }
    }
}
