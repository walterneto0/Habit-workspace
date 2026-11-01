pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root
    required property var backend
    property string label: qsTr("Período")
    property bool optional: false
    property string scale: ""
    property int selectedPart: 0
    property string initialYear: ""
    property int initialMonth: 1
    readonly property var options: backend ? backend.periodChoices.options(scale, year.text, month.currentIndex + 1) : []
    readonly property var selected: options.find(o => o.part === selectedPart)
    readonly property string period: scale === "year" ? (options.length ? options[0].value : "") : (selected ? selected.value : "")
    readonly property bool valid: !!period || (optional && !scale)
    onScaleChanged: type.currentIndex = ["", "year", "month", "week", "day"].indexOf(scale)
    function setPeriod(value, today) {
        const parts = backend.periodChoices.describe(value);
        initialYear = parts.year || today.substring(0, 4);
        initialMonth = parts.month || Number(today.substring(5, 7));
        year.text = initialYear;
        month.currentIndex = initialMonth - 1;
        selectedPart = parts.part || 0;
        scale = parts.scale || "";
        type.currentIndex = ["", "year", "month", "week", "day"].indexOf(scale);
    }
    spacing: 6
    UiText { Layout.fillWidth: true; text: root.label }
    StudioChoice {
        id: type
        objectName: root.objectName + "-type"
        Layout.fillWidth: true
        label: root.label + qsTr(" · tipo")
        model: [root.optional ? qsTr("Sem período associado") : qsTr("Escolha o tipo de período"), qsTr("Ano"), qsTr("Mês"), qsTr("Semana"), qsTr("Dia")]
        currentIndex: ["", "year", "month", "week", "day"].indexOf(root.scale)
        onModelChanged: currentIndex = ["", "year", "month", "week", "day"].indexOf(root.scale)
        onActivated: {
            root.scale = ["", "year", "month", "week", "day"][currentIndex];
            root.selectedPart = 0;
        }
    }
    Input {
        id: year
        objectName: root.objectName + "-year"
        Layout.fillWidth: true
        visible: !!root.scale
        placeholderText: root.scale === "week" ? qsTr("Ano da semana · ex.: 2026") : qsTr("Ano · ex.: 2026")
        Accessible.name: placeholderText
        inputMethodHints: Qt.ImhDigitsOnly
        maximumLength: 4
    }
    StudioChoice {
        id: month
        objectName: root.objectName + "-month"
        Layout.fillWidth: true
        visible: root.scale === "day"
        label: qsTr("Mês do dia")
        model: [qsTr("Janeiro"),qsTr("Fevereiro"),qsTr("Março"),qsTr("Abril"),qsTr("Maio"),qsTr("Junho"),qsTr("Julho"),qsTr("Agosto"),qsTr("Setembro"),qsTr("Outubro"),qsTr("Novembro"),qsTr("Dezembro")]
    }
    StudioChoice {
        objectName: root.objectName + "-choice"
        Layout.fillWidth: true
        visible: !!root.scale && root.scale !== "year"
        label: root.label + qsTr(" · escolha")
        model: root.options
        textRole: "label"
        currentIndex: root.options.findIndex(o => o.part === root.selectedPart)
        displayText: currentIndex < 0 ? qsTr("Escolha o período") : currentText
        onActivated: root.selectedPart = root.options[currentIndex].part
    }
    UiText {
        objectName: root.objectName + "-range"
        Layout.fillWidth: true
        text: root.period && root.backend ? root.backend.periodChoices.label(root.period) : root.optional && !root.scale ? qsTr("Sem período associado") : qsTr("Escolha um período válido antes de salvar.")
        color: root.valid ? Theme.secondary : Theme.warning
    }
}
