pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root
    required property var row
    property bool busy: false
    signal edit()
    signal complete()
    spacing: 4
    UiText { Layout.fillWidth: true; text: (root.row.followup_period ? qsTr("Acompanhamento do objetivo · ") : root.row.kind === "goal" ? ((root.row.home_period_ref || "").startsWith("year/") ? qsTr("Objetivo anual · ") : qsTr("Objetivo · ")) : qsTr("Tarefa · ")) + root.row.title; font.weight: Font.Medium }
    UiText { Layout.fillWidth: true; text: root.row.conflict ? qsTr("Referência ausente, incompatível ou UUID ambíguo") : root.row.category + " · " + root.row.scope; color: root.row.conflict ? Theme.warning : Theme.secondary; font.pixelSize: 12 }
    UiText {
        Layout.fillWidth: true
        text: ({pending:qsTr("Pendente"),completed:qsTr("Concluída"),not_started:qsTr("Não iniciado"),in_progress:qsTr("Em andamento"),achieved:qsTr("Alcançado"),paused:qsTr("Pausado"),abandoned:qsTr("Abandonado")}[root.row.status] || "") + (root.row.due ? qsTr(" · Prazo: ") + root.row.due : "") + (root.row.overdue ? qsTr(" · Atrasada hoje") : "") + (root.row.kind === "goal" ? qsTr(" · Progresso manual: ") + (root.row.progress === null || root.row.progress === undefined ? qsTr("não informado") : root.row.progress + "%") : "")
        color: root.row.overdue ? Theme.warning : Theme.secondary
    }
    Flow {
        Layout.fillWidth: true
        spacing: 8
        ActionButton { objectName: "planning-edit-" + root.row.id; text: qsTr("Detalhes / Editar"); enabled: !root.busy && !root.row.conflict; Accessible.name: text + " · " + root.row.title; onClicked: root.edit() }
        ActionButton { objectName: "planning-complete-" + root.row.id; visible: root.row.kind === "task"; text: root.row.status === "completed" ? qsTr("Reabrir") : qsTr("Concluir"); enabled: !root.busy && !root.row.conflict; Accessible.name: text + " · " + root.row.title; onClicked: root.complete() }
    }
}
