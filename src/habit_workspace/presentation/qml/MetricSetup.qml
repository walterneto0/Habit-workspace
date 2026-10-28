import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    property string valueType: "text"
    property string initialName: ""
    property string initialTags: ""
    readonly property bool numeric: ["integer", "number", "duration", "rating"].includes(valueType)
    readonly property string name: fieldName.text
    readonly property string tags: fieldTags.text
    function options() {
        return {unit: numeric ? unit.text : "", minimum: numeric ? minimum.text : "", maximum: numeric ? maximum.text : "", options: valueType === "selection" ? choices.text : "", aggregation: aggregation.currentText, temporal_policy: policy.currentText, weekly_attribution: policy.currentText === "weekly" ? attribution.currentText : "separate"};
    }
    UiText { Layout.fillWidth: true; text: qsTr("Novo campo · ") + root.valueType + qsTr(". A definição recebe UUID próprio e será ativada ao salvar.") }
    Input { id: fieldName; objectName: "metric-name"; Layout.fillWidth: true; placeholderText: qsTr("Nome do campo (obrigatório)"); text: root.initialName }
    Input { id: fieldTags; Layout.fillWidth: true; placeholderText: qsTr("Tags separadas por vírgula"); text: root.initialTags }
    UiText { visible: root.numeric; text: qsTr("Unidade e limites opcionais") }
    Input { id: unit; visible: root.numeric; Layout.fillWidth: true; placeholderText: root.valueType === "duration" ? qsTr("Unidade de duração, ex.: minutos") : qsTr("Unidade, ex.: pontos") }
    RowLayout {
        visible: root.numeric
        Layout.fillWidth: true
        Input { id: minimum; objectName: "metric-minimum"; Layout.fillWidth: true; placeholderText: qsTr("Mínimo"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
        Input { id: maximum; objectName: "metric-maximum"; Layout.fillWidth: true; placeholderText: qsTr("Máximo"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
    }
    UiText { visible: root.valueType === "selection"; text: qsTr("Opções únicas, uma por linha (obrigatório)") }
    TextArea {
        id: choices
        objectName: "metric-options"
        visible: root.valueType === "selection"
        Layout.fillWidth: true
        Layout.preferredHeight: 100
        Accessible.name: qsTr("Opções de seleção, uma por linha")
        color: Theme.text
        wrapMode: TextEdit.Wrap
        background: Rectangle { color: Theme.canvas; border.color: choices.activeFocus ? Theme.accent : Theme.border; border.width: choices.activeFocus ? 2 : 1; radius: 6 }
    }
    UiText { Layout.fillWidth: true; visible: ["date", "time", "boolean", "text"].includes(root.valueType); text: ({date: qsTr("Data civil no formato AAAA-MM-DD."), time: qsTr("Horário local no formato HH:MM, sem fuso."), boolean: qsTr("Valor verdadeiro/falso. Não cria um hábito."), text: qsTr("Texto livre. Sem agregação numérica.")})[root.valueType] || ""; color: Theme.secondary }
    UiText { text: qsTr("Agregação do campo") }
    StudioChoice { id: aggregation; Layout.fillWidth: true; label: qsTr("Agregação do novo campo"); model: root.numeric ? ["none", "sum", "mean", "min", "max"] : ["none", "count"] }
    UiText { text: qsTr("Política temporal") }
    StudioChoice { id: policy; Layout.fillWidth: true; label: qsTr("Política temporal"); model: ["daily", "weekly"] }
    UiText { visible: policy.currentText === "weekly"; Layout.fillWidth: true; text: qsTr("Semana entre meses: separate mantém separada; start/end atribui pelo início/fim; completion pela conclusão.") }
    StudioChoice { id: attribution; visible: policy.currentText === "weekly"; Layout.fillWidth: true; label: qsTr("Atribuição mensal da semana"); model: ["separate", "start", "end", "completion"] }
}
