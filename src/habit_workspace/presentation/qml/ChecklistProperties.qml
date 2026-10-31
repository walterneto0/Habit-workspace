import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    required property var studio
    required property var current
    required property var sources
    property var tagOptions: []
    readonly property var selection: (current.config || {}).selection || ({})
    readonly property var selectedIds: selection.source_ids || ((current.binding || {}).source_id ? [current.binding.source_id] : [])
    readonly property string mode: selection.mode || "manual"
    property bool choosingTags: false
    property bool includeBooleanFields: false
    readonly property var habits: sources.filter(s => s.kind === "habit" || s.kind === "task" || (includeBooleanFields && s.kind === "metric_definition" && s.type === "boolean"))
    spacing: 8
    function labelFor(id) { const source = sources.find(s => s.id === id); return source ? source.name : qsTr("Referência ausente: ") + id; }
    UiText { Layout.fillWidth: true; text: qsTr("Hábitos e tarefas da checklist"); font.weight: Font.Medium }
    StudioChoice {
        objectName: "checklist-mode"
        Layout.fillWidth: true
        label: qsTr("Seleção dos hábitos")
        model: [qsTr("Seleção manual"), qsTr("Tags dinâmicas"), qsTr("Contextual · data selecionada")]
        currentIndex: root.choosingTags || root.mode === "by_tags" ? 1 : root.mode === "all" ? 2 : 0
        onActivated: {
            root.choosingTags = currentIndex === 1;
            if (currentIndex !== 1) root.studio.edit("selection_mode", currentIndex === 2 ? "all" : "manual");
        }
    }
    ColumnLayout {
        Layout.fillWidth: true
        visible: root.mode === "manual" && !root.choosingTags
        StudioCheckBox {
            text: qsTr("Incluir campos Sim/Não")
            checked: root.includeBooleanFields
            onToggled: root.includeBooleanFields = checked
        }
        Input {
            id: search
            objectName: "checklist-search"
            Layout.fillWidth: true
            placeholderText: qsTr("Buscar hábitos ou tarefas pelo nome")
            Accessible.name: placeholderText
        }
        StudioChoice {
            id: candidate
            objectName: "checklist-candidate"
            Layout.fillWidth: true
            label: root.includeBooleanFields ? qsTr("Hábito ou campo Sim/Não existente") : qsTr("Hábito existente")
            model: root.habits.filter(s => !root.selectedIds.includes(s.id) && s.name.toLowerCase().includes(search.text.toLowerCase()))
            textRole: "name"
        }
        ActionButton {
            objectName: "checklist-add"
            Layout.fillWidth: true
            text: qsTr("Adicionar à checklist")
            enabled: candidate.currentIndex >= 0 && candidate.currentIndex < candidate.model.length
            onClicked: root.studio.edit("source", candidate.model[candidate.currentIndex].id)
        }
        UiText { Layout.fillWidth: true; visible: root.selectedIds.length === 0; text: qsTr("Selecione um ou mais hábitos. A ordem fica salva no layout."); color: Theme.secondary }
        Repeater {
            model: root.selectedIds
            delegate: ColumnLayout {
                required property string modelData
                required property int index
                Layout.fillWidth: true
                spacing: 4
                UiText { Layout.fillWidth: true; text: (index + 1) + ". " + root.labelFor(modelData) }
                RowLayout {
                    ActionButton { objectName: "checklist-up-" + modelData; text: "↑"; hint: qsTr("Mover acima: ") + root.labelFor(modelData); enabled: index > 0; onClicked: root.studio.edit("source_up", modelData) }
                    ActionButton { objectName: "checklist-down-" + modelData; text: "↓"; hint: qsTr("Mover abaixo: ") + root.labelFor(modelData); enabled: index < root.selectedIds.length - 1; onClicked: root.studio.edit("source_down", modelData) }
                    ActionButton { objectName: "checklist-remove-" + modelData; text: qsTr("Remover"); hint: qsTr("Remover da checklist: ") + root.labelFor(modelData); onClicked: root.studio.edit("remove_source", modelData) }
                }
            }
        }
    }
    ColumnLayout {
        Layout.fillWidth: true
        visible: root.choosingTags || root.mode === "by_tags"
        Flow {
            Layout.fillWidth: true
            spacing: 4
            Repeater {
                model: root.tagOptions
                delegate: ActionButton {
                    required property string modelData
                    text: "#" + modelData
                    selected: tags.text.split(",").map(t => t.trim()).includes(modelData)
                    hint: qsTr("Selecionar tag: ") + modelData
                    onClicked: {
                        let values = tags.text.split(",").map(t => t.trim()).filter(t => t.length);
                        if (values.includes(modelData)) values = values.filter(t => t !== modelData);
                        else values.push(modelData);
                        tags.text = values.join(", ");
                    }
                }
            }
        }
        Input {
            id: tags
            objectName: "checklist-tags"
            Layout.fillWidth: true
            placeholderText: qsTr("Tags separadas por vírgula")
            Accessible.name: placeholderText
            text: (root.selection.tags || []).join(", ")
            onAccepted: applyTags.clicked()
        }
        ActionButton {
            id: applyTags
            objectName: "checklist-apply-tags"
            Layout.fillWidth: true
            text: qsTr("Aplicar tags")
            enabled: tags.text.trim().length > 0
            onClicked: { root.studio.edit("tags", tags.text); root.choosingTags = false; }
        }
        UiText { Layout.fillWidth: true; text: qsTr("Qualquer tag (OU): inclui hábitos com pelo menos uma das tags. Novos hábitos correspondentes aparecem automaticamente nas datas programadas."); color: Theme.secondary }
    }
    UiText {
        Layout.fillWidth: true
        visible: root.mode === "all" && !root.choosingTags
        text: qsTr("Mostra hábitos programados para a data de acompanhamento, respeitando escopo e recorrência. Em semanas e meses, escolha o dia no cabeçalho.")
        color: Theme.secondary
    }
    UiText { Layout.fillWidth: true; text: qsTr("Remover da seleção preserva o hábito e todos os registros."); color: Theme.muted; font.pixelSize: 12 }
}
