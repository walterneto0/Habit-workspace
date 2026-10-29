import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "StudioLabels.js" as Labels

ColumnLayout {
    id: root
    property string valueType: "text"
    property var sources: []
    property string initialName: ""
    property string initialTags: ""
    property bool advanced: false
    property bool submitted: false
    readonly property string effectiveType: ["integer", "number"].includes(valueType) ? numberType.currentValue || valueType : valueType
    readonly property bool numeric: ["integer", "number", "duration", "rating"].includes(effectiveType)
    readonly property var compatibleSources: sources.filter(s => Labels.compatible(effectiveType + "_input", s))
    property bool useExisting: false
    Component.onCompleted: useExisting = compatibleSources.length > 0
    readonly property string sourceId: useExisting && existing.currentIndex >= 0 ? existing.currentValue || "" : ""
    readonly property string name: fieldName.text.trim()
    readonly property string tags: fieldTags.text
    readonly property string nameError: submitted && !name ? qsTr("Informe um nome para o campo.") : ""
    readonly property string optionsError: {
        if (!submitted || effectiveType !== "selection") return "";
        const values = choices.text.split("\n").map(s => s.trim()).filter(s => s);
        return !values.length ? qsTr("Adicione pelo menos uma opção.") : new Set(values).size !== values.length ? qsTr("Cada opção precisa ter um nome diferente.") : "";
    }
    readonly property string limitsError: {
        if (!submitted || !numeric) return "";
        const low = minimum.text.trim().replace(",", "."), high = maximum.text.trim().replace(",", ".");
        if ((low && !isFinite(Number(low))) || (high && !isFinite(Number(high)))) return qsTr("Use números válidos nos limites.");
        if (low && high && Number(low) > Number(high)) return qsTr("O máximo deve ser maior ou igual ao mínimo.");
        return "";
    }
    function validate() {
        submitted = true;
        if (useExisting) return sourceId.length > 0;
        if (nameError) { fieldName.forceActiveFocus(); return false; }
        if (optionsError) { choices.forceActiveFocus(); return false; }
        if (limitsError) { advanced = true; minimum.forceActiveFocus(); return false; }
        return true;
    }
    function focusFirst() { if (useExisting) sourceSearch.forceActiveFocus(); else fieldName.forceActiveFocus(); }
    function options() {
        return {unit: numeric ? unit.text.trim() : "", minimum: numeric ? minimum.text.trim().replace(",", ".") : "", maximum: numeric ? maximum.text.trim().replace(",", ".") : "", options: effectiveType === "selection" ? choices.text : "", aggregation: aggregation.currentValue, temporal_policy: policy.currentValue, weekly_attribution: policy.currentValue === "weekly" ? attribution.currentValue : "separate"};
    }
    spacing: 8
    RowLayout {
        Layout.fillWidth: true
        ActionButton { objectName: "metric-existing"; Layout.fillWidth: true; text: qsTr("Usar existente"); selected: root.useExisting; onClicked: { root.useExisting = true; root.focusFirst(); } }
        ActionButton { objectName: "metric-new"; Layout.fillWidth: true; text: qsTr("Criar novo"); selected: !root.useExisting; onClicked: { root.useExisting = false; root.focusFirst(); } }
    }
    UiText { Layout.fillWidth: true; text: root.useExisting ? qsTr("O bloco usa o mesmo campo e seus registros. Nenhuma definição será duplicada.") : qsTr("Crie um campo para acompanhar sua rotina. Os valores serão preenchidos na página após salvar o layout."); color: Theme.secondary }
    ColumnLayout {
        visible: root.useExisting
        Layout.fillWidth: true
        UiText { text: qsTr("Buscar campo compatível") }
        Input { id: sourceSearch; objectName: "metric-source-search"; Layout.fillWidth: true; placeholderText: qsTr("Buscar pelo nome") }
        StudioChoice {
            id: existing
            objectName: "metric-source"
            Layout.fillWidth: true
            label: qsTr("Campo existente")
            model: root.compatibleSources.filter(s => s.name.toLowerCase().includes(sourceSearch.text.toLowerCase()))
            textRole: "name"
            valueRole: "id"
        }
        UiText { Layout.fillWidth: true; visible: existing.count === 0; text: qsTr("Nenhum campo compatível encontrado. Tente outro nome ou escolha Criar novo."); color: Theme.secondary }
        UiText { visible: root.submitted && !root.sourceId; text: qsTr("Selecione um campo existente."); color: Theme.error; Layout.fillWidth: true }
    }
    ColumnLayout {
        Layout.fillWidth: true
        visible: !root.useExisting
        spacing: 8
        UiText { text: qsTr("Nome do campo *") }
        Input { id: fieldName; objectName: "metric-name"; Layout.fillWidth: true; placeholderText: qsTr("Ex.: Tempo de leitura"); text: root.initialName; Accessible.name: qsTr("Nome do campo, obrigatório") }
        UiText { objectName: "metric-name-error"; visible: !!root.nameError; text: root.nameError; color: Theme.error; Layout.fillWidth: true }
        StudioChoice {
            id: numberType
            objectName: "metric-number-type"
            visible: ["integer", "number"].includes(root.valueType)
            Layout.fillWidth: true
            model: Labels.choices(["integer", "number"])
            textRole: "name"; valueRole: "value"
            currentIndex: root.valueType === "number" ? 1 : 0
            label: qsTr("Tipo de número")
        }
        UiText { visible: root.numeric; text: qsTr("Unidade (opcional)") }
        Input { id: unit; objectName: "metric-unit"; visible: root.numeric; Layout.fillWidth: true; placeholderText: root.valueType === "duration" ? qsTr("Ex.: minutos ou horas") : qsTr("Ex.: páginas, pontos"); Accessible.name: qsTr("Unidade, opcional") }
        UiText { visible: root.effectiveType === "selection"; text: qsTr("Opções * · uma por linha") }
        TextArea {
            id: choices
            objectName: "metric-options"
            visible: root.effectiveType === "selection"
            Layout.fillWidth: true
            Layout.preferredHeight: 90
            Accessible.name: qsTr("Opções, uma por linha, obrigatório")
            color: Theme.text
            wrapMode: TextEdit.Wrap
            background: Rectangle { color: Theme.canvas; border.color: choices.activeFocus ? Theme.accent : Theme.border; border.width: choices.activeFocus ? 2 : 1; radius: 6 }
        }
        UiText { visible: !!root.optionsError; text: root.optionsError; Layout.fillWidth: true; color: Theme.error }
        UiText { Layout.fillWidth: true; visible: ["date", "time", "boolean", "text"].includes(root.effectiveType); text: ({date: "Data no formato AAAA-MM-DD.", time: "Horário no formato HH:MM.", boolean: "Uma resposta Sim/Não. Para acompanhar um hábito, use Lista de hábitos.", text: "Texto livre para um registro breve."})[root.effectiveType] || ""; color: Theme.secondary }
        ActionButton { objectName: "metric-advanced"; text: root.advanced ? qsTr("▾ Opções avançadas") : qsTr("▸ Opções avançadas"); quiet: true; onClicked: root.advanced = !root.advanced }
        ColumnLayout {
            visible: root.advanced
            Layout.fillWidth: true
            UiText { text: qsTr("Tags (opcional)") }
            Input { id: fieldTags; objectName: "metric-tags"; Layout.fillWidth: true; placeholderText: qsTr("Ex.: saúde, estudos"); text: root.initialTags }
            UiText { visible: root.numeric; text: qsTr("Limites (opcional)") }
            RowLayout {
                visible: root.numeric
                Layout.fillWidth: true
                Input { id: minimum; objectName: "metric-minimum"; Layout.fillWidth: true; placeholderText: qsTr("Mínimo"); Accessible.name: placeholderText; inputMethodHints: Qt.ImhFormattedNumbersOnly }
                Input { id: maximum; objectName: "metric-maximum"; Layout.fillWidth: true; placeholderText: qsTr("Máximo"); Accessible.name: placeholderText; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            }
            UiText { visible: !!root.limitsError; text: root.limitsError; color: Theme.error; Layout.fillWidth: true }
            UiText { text: qsTr("Como resumir os valores") }
            StudioChoice { id: aggregation; Layout.fillWidth: true; label: qsTr("Agregação"); model: Labels.choices(root.numeric ? ["none", "sum", "mean", "min", "max"] : ["none", "count"]); textRole: "name"; valueRole: "value" }
            UiText { Layout.fillWidth: true; text: qsTr("Define a regra para consultas aos valores. Gráficos serão exibidos na Fase 8."); color: Theme.secondary }
            UiText { text: qsTr("Frequência do registro") }
            StudioChoice { id: policy; Layout.fillWidth: true; label: qsTr("Frequência"); model: Labels.choices(["daily", "weekly"]); textRole: "name"; valueRole: "value" }
            UiText { visible: policy.currentValue === "weekly"; Layout.fillWidth: true; text: qsTr("Campos semanais ainda não permitem registrar valores na interface. Se a semana cruzar meses, escolha a atribuição abaixo."); color: Theme.warning }
            StudioChoice { id: attribution; visible: policy.currentValue === "weekly"; Layout.fillWidth: true; label: qsTr("Mês da semana"); model: Labels.choices(["separate", "start", "end", "completion"]); textRole: "name"; valueRole: "value" }
        }
    }
}
