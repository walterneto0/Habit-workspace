import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    required property var studio
    readonly property var state: studio ? studio.state : ({})
    readonly property var current: state.current || ({})
    readonly property var config: current.config || ({})
    readonly property var selection: config.selection || ({})
    readonly property var sources: state.sources || []
    readonly property var metrics: sources.filter(s => s.kind === "metric_definition")
    readonly property bool chart: current.type === "chart"
    visible: !!current.id
    spacing: 8
    function labelFor(id) { const s = sources.find(s => s.id === id); return s ? s.name : qsTr("Referência ausente: ") + id; }
    UiText { Layout.fillWidth: true; text: qsTr("Propriedades"); font.weight: Font.Medium }
    UiText { text: qsTr("Título") }
    Input { objectName: "studio-title"; Layout.fillWidth: true; text: root.current.title || ""; Accessible.name: qsTr("Título do componente"); onEditingFinished: root.studio.edit("title", text) }
    Flow {
        Layout.fillWidth: true
        spacing: 6
        Repeater {
            model: [{a:"up",t:"Mover acima"},{a:"down",t:"Mover abaixo"},{a:"width",t:"Meia / inteira"},{a:"duplicate",t:"Duplicar"},{a:"remove",t:"Remover"}]
            delegate: ActionButton {
                required property var modelData
                objectName: "studio-" + modelData.a
                text: modelData.t
                onClicked: root.studio.command(modelData.a)
            }
        }
    }
    UiText { Layout.fillWidth: true; text: root.current.bindingLabel || ""; visible: text.length > 0; color: Theme.secondary }
    Input {
        Layout.fillWidth: true
        visible: (root.current.type || "").endsWith("_input")
        placeholderText: qsTr("Texto de orientação")
        text: root.config.placeholder || ""
        onEditingFinished: root.studio.edit("placeholder", text)
    }
    StudioCheckBox {
        visible: (root.current.type || "").endsWith("_input")
        text: qsTr("Obrigatório")
        checked: !!root.config.required
        onToggled: root.studio.edit("required", checked ? "true" : "false")
    }
    UiText {
        Layout.fillWidth: true
        visible: !!(root.state.field || {}).id
        text: { const f = root.state.field || {}; return qsTr("Definição vinculada: ") + (f.value_type || "") + " · " + (f.unit || "") + "\n" + (f.temporal_policy || "") + " · " + (f.aggregation || "") + "\n" + (f.options || []).join(", ") + (f.minimum !== null && f.minimum !== undefined ? "\nMínimo: " + f.minimum : "") + (f.maximum !== null && f.maximum !== undefined ? " · Máximo: " + f.maximum : ""); }
        color: Theme.secondary
    }
    Loader {
        Layout.fillWidth: true
        active: root.current.type === "checklist"
        sourceComponent: Component {
            ChecklistProperties { studio: root.studio; current: root.current; sources: root.sources; tagOptions: root.state.habitTags || [] }
        }
    }
    UiText { visible: root.current.type !== "checklist" && root.current.type !== "section" && root.current.type !== "image"; text: qsTr("Fonte por nome (UUID preservado)") }
    Input { id: sourceSearch; Layout.fillWidth: true; visible: root.current.type !== "checklist" && root.current.type !== "section" && root.current.type !== "image"; placeholderText: qsTr("Buscar fonte") }
    StudioChoice {
        id: source
        objectName: "studio-source"
        visible: sourceSearch.visible
        Layout.fillWidth: true
        label: qsTr("Fonte existente")
        model: root.sources.filter(s => s.name.toLowerCase().includes(sourceSearch.text.toLowerCase()))
        textRole: "name"
    }
    ActionButton {
        visible: sourceSearch.visible
        Layout.fillWidth: true
        objectName: "studio-bind"
        text: root.current.type === "table" ? qsTr("Adicionar coluna") : root.chart ? qsTr("Adicionar à seleção manual") : qsTr("Vincular fonte")
        enabled: source.currentIndex >= 0
        onClicked: root.studio.edit("source", source.model[source.currentIndex].id)
    }
    Repeater {
        model: root.current.type === "table" ? (root.config.columns || []) : []
        delegate: ColumnLayout {
            required property var modelData
            required property int index
            Layout.fillWidth: true
            UiText { text: qsTr("Coluna ") + (index + 1) + " · " + modelData.value_type }
            Input { objectName: "column-label-" + index; Layout.fillWidth: true; text: modelData.label; Accessible.name: qsTr("Nome da coluna ") + (index + 1); onEditingFinished: root.studio.columnEdit(index, "label", text) }
            StudioChoice {
                Layout.fillWidth: true
                model: root.metrics
                textRole: "name"
                label: qsTr("Métrica da coluna ") + (index + 1)
                currentIndex: root.metrics.findIndex(s => s.id === modelData.field_id)
                onActivated: root.studio.columnEdit(index, "source", model[currentIndex].id)
            }
            Flow {
                Layout.fillWidth: true
                spacing: 4
                ActionButton { objectName: "column-up-" + index; text: qsTr("↑"); hint: qsTr("Mover coluna acima"); onClicked: root.studio.columnEdit(index, "up", "") }
                ActionButton { objectName: "column-down-" + index; text: qsTr("↓"); hint: qsTr("Mover coluna abaixo"); onClicked: root.studio.columnEdit(index, "down", "") }
                ActionButton { objectName: "column-remove-" + index; text: qsTr("Excluir coluna"); onClicked: root.studio.columnEdit(index, "remove", "") }
            }
        }
    }
    ActionButton {
        objectName: "studio-enter"
        visible: root.current.type === "section"
        Layout.fillWidth: true
        text: qsTr("Editar conteúdo da seção")
        onClicked: root.studio.command("enter")
    }
    UiText { Layout.fillWidth: true; visible: root.current.type === "section"; text: qsTr("Abra a seção para adicionar, configurar e reordenar qualquer componente. O controle de colunas se aplica à seção aberta."); color: Theme.secondary }
    ColumnLayout {
        visible: root.chart
        Layout.fillWidth: true
        UiText { text: qsTr("Seleção: ") + (root.selection.mode === "by_tags" ? qsTr("tags dinâmicas · qualquer") : qsTr("IDs fixos")) }
        Repeater {
            model: root.chart ? (root.selection.source_ids || []) : []
            delegate: ActionButton {
                required property string modelData
                Layout.fillWidth: true
                text: qsTr("Remover: ") + root.labelFor(modelData)
                onClicked: root.studio.edit("remove_source", modelData)
            }
        }
        ActionButton { text: qsTr("Usar seleção manual vazia"); onClicked: root.studio.edit("clear_sources", "") }
        Input { objectName: "chart-tags"; Layout.fillWidth: true; placeholderText: qsTr("Tags dinâmicas, separadas por vírgula"); text: (root.selection.tags || []).join(", "); onEditingFinished: { if (text.length) root.studio.edit("tags", text); } }
        UiText { Layout.fillWidth: true; text: qsTr("Tipos aceitos (vazio aceita todos). Agregação numérica exige tipos numéricos."); color: Theme.secondary }
        Flow {
            Layout.fillWidth: true
            Repeater {
                model: ["habit", "boolean", "integer", "number", "duration", "rating", "text", "date", "time", "selection"]
                delegate: StudioCheckBox {
                    required property string modelData
                    objectName: "chart-type-" + modelData
                    text: modelData
                    checked: (root.selection.value_types || []).includes(modelData)
                    onToggled: {
                        let types = (root.selection.value_types || []).slice();
                        if (checked) types.push(modelData); else types = types.filter(t => t !== modelData);
                        root.studio.edit("types", types.join(","));
                        checked = Qt.binding(() => (root.selection.value_types || []).includes(modelData));
                    }
                }
            }
        }
        UiText { text: qsTr("Agregação") }
        StudioChoice { objectName: "chart-aggregation"; Layout.fillWidth: true; model: ["count", "states", "sum", "mean", "min", "max"]; label: qsTr("Agregação"); currentIndex: model.indexOf(root.config.aggregation); onActivated: root.studio.edit("aggregation", currentText) }
        UiText { text: qsTr("Visualização") }
        StudioChoice { objectName: "chart-visualization"; Layout.fillWidth: true; model: ["bar", "line", "total"]; label: qsTr("Visualização"); currentIndex: model.indexOf(root.config.visualization); onActivated: root.studio.edit("visualization", currentText) }
        UiText { Layout.fillWidth: true; text: qsTr("Período concreto: year/2026, month/2026-10 ou week/2026-W44. Vazio segue a página.") }
        Input { objectName: "chart-period"; Layout.fillWidth: true; Accessible.name: qsTr("Período do gráfico"); text: root.config.period || ""; onEditingFinished: root.studio.edit("period", text) }
    }
    ColumnLayout {
        visible: root.current.type === "image"
        Layout.fillWidth: true
        Input { Layout.fillWidth: true; placeholderText: qsTr("Caminho relativo da imagem local"); text: root.config.path || ""; onEditingFinished: root.studio.edit("path", text) }
        Input { Layout.fillWidth: true; placeholderText: qsTr("Descrição acessível da imagem"); text: root.config.alt || ""; onEditingFinished: root.studio.edit("alt", text) }
        StudioChoice { Layout.fillWidth: true; model: ["contain", "cover"]; label: qsTr("Ajuste da imagem"); currentIndex: model.indexOf(root.config.fit); onActivated: root.studio.edit("fit", currentText) }
    }
}
