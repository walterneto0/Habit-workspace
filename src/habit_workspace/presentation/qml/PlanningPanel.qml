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
        Input { objectName: "planning-search"; Layout.fillWidth: true; placeholderText: qsTr("Buscar tarefas e objetivos por título, descrição ou tag"); Accessible.name: placeholderText; text: root.modelState.query || ""; onTextEdited: root.backend.setQuery(text) }
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
