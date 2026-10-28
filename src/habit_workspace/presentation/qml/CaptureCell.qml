import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// One tracking-mode entry: a habit check-in or a typed field observation.
// Holds no canonical data; every action is a request to the Python services.
ColumnLayout {
    id: root
    property var cell: ({})
    property string blockId: ""
    property var feedback: ({})
    property bool showName: true
    readonly property bool habit: cell.kind === "habit"
    readonly property string valueType: cell.valueType || ""
    readonly property string current: cell.value || ""
    readonly property bool mine: feedback.target === cell.id
    signal checkin(string habitId, string state, string token)
    signal observe(string fieldId, string blockId, string text, string token)
    signal observeBoolean(string fieldId, string blockId, string value, string token)
    signal clearValue(string fieldId, string token)
    spacing: 6
    onCurrentChanged: valueInput.text = current
    Component.onCompleted: valueInput.text = current
    function stateColor(state) {
        return ({done: Theme.success, skipped: Theme.secondary, missed: Theme.warning})[state] || Theme.muted;
    }
    function submit() {
        root.observe(root.cell.id, root.blockId, valueInput.text, root.cell.token);
    }
    RowLayout {
        Layout.fillWidth: true
        spacing: 8
        Rectangle {
            visible: root.habit
            Layout.preferredWidth: 8
            Layout.preferredHeight: 8
            radius: 4
            color: root.stateColor(root.cell.state)
        }
        UiText {
            Layout.fillWidth: true
            text: (root.showName ? root.cell.name : "") + (root.cell.unit ? (root.showName ? " · " : "") + root.cell.unit : "")
            font.weight: root.showName ? Font.Medium : Font.Normal
            color: root.showName ? Theme.text : Theme.secondary
        }
        UiText {
            visible: root.habit
            text: root.cell.stateLabel || ""
            color: root.stateColor(root.cell.state)
            font.pixelSize: 12
        }
        UiText {
            visible: !root.habit && !root.cell.editable && !!root.cell.recorded
            text: qsTr("Valor salvo: ") + root.current
            color: Theme.secondary
            font.pixelSize: 12
        }
    }
    Flow {
        Layout.fillWidth: true
        visible: root.habit && root.cell.editable
        spacing: 6
        Repeater {
            model: [
                {state: "done", label: qsTr("Concluído")},
                {state: "skipped", label: qsTr("Dispensado")},
                {state: "missed", label: qsTr("Não cumprido")}
            ]
            delegate: ActionButton {
                required property var modelData
                objectName: "checkin-" + modelData.state + "-" + root.cell.id
                text: modelData.label
                selected: root.cell.recorded === modelData.state
                hint: selected ? qsTr("Registrado como ") + modelData.label : qsTr("Registrar como ") + modelData.label
                Accessible.name: root.cell.name + " · " + hint
                onClicked: root.checkin(root.cell.id, modelData.state, root.cell.token)
            }
        }
        ActionButton {
            objectName: "checkin-clear-" + root.cell.id
            visible: !!root.cell.recorded
            quiet: true
            text: qsTr("Limpar registro")
            hint: qsTr("Remove o registro explícito; o dia volta a ficar sem registro, sem contar como falha")
            onClicked: root.checkin(root.cell.id, "", root.cell.token)
        }
    }
    Flow {
        Layout.fillWidth: true
        visible: !root.habit && root.cell.editable && root.valueType === "boolean"
        spacing: 6
        ActionButton {
            objectName: "boolean-true-" + root.cell.id
            text: qsTr("Sim")
            selected: root.cell.boolean === true
            onClicked: root.observeBoolean(root.cell.id, root.blockId, "true", root.cell.token)
        }
        ActionButton {
            objectName: "boolean-false-" + root.cell.id
            text: qsTr("Não")
            selected: root.cell.boolean === false
            onClicked: root.observeBoolean(root.cell.id, root.blockId, "false", root.cell.token)
        }
        ActionButton {
            visible: root.cell.recorded === true
            quiet: true
            text: qsTr("Limpar")
            onClicked: root.clearValue(root.cell.id, root.cell.token)
        }
    }
    RowLayout {
        Layout.fillWidth: true
        visible: !root.habit && root.cell.editable && root.valueType !== "boolean"
        spacing: 6
        Input {
            id: valueInput
            objectName: "observation-input-" + root.cell.id
            Layout.fillWidth: true
            visible: root.valueType !== "selection"
            placeholderText: (root.cell.hint || "") + (root.cell.bounds ? " · " + root.cell.bounds : "") + qsTr(" · sem registro")
            inputMethodHints: ["integer", "number", "duration", "rating"].includes(root.valueType) ? Qt.ImhFormattedNumbersOnly : Qt.ImhNone
            Accessible.name: root.cell.name + qsTr(" · valor do dia")
            onAccepted: root.submit()
        }
        StudioChoice {
            id: choice
            Layout.fillWidth: true
            visible: root.valueType === "selection"
            label: root.cell.name
            model: root.cell.options || []
            currentIndex: (root.cell.options || []).indexOf(root.current)
            onActivated: root.observe(root.cell.id, root.blockId, currentText, root.cell.token)
        }
        ActionButton {
            objectName: "observation-save-" + root.cell.id
            visible: root.valueType !== "selection"
            text: qsTr("Salvar")
            hint: qsTr("Salvar valor do dia selecionado (Enter)")
            onClicked: root.submit()
        }
        ActionButton {
            objectName: "observation-clear-" + root.cell.id
            visible: root.cell.recorded === true
            quiet: true
            text: qsTr("Limpar")
            hint: qsTr("Remover o valor salvo deste dia")
            onClicked: root.clearValue(root.cell.id, root.cell.token)
        }
    }
    UiText {
        Layout.fillWidth: true
        visible: text.length > 0
        text: root.cell.note || ""
        color: Theme.secondary
        font.pixelSize: 12
    }
    UiText {
        objectName: "capture-feedback-" + root.cell.id
        Layout.fillWidth: true
        visible: root.mine
        text: root.mine ? root.feedback.text : ""
        color: root.feedback.error ? Theme.error : Theme.success
        font.pixelSize: 12
        Accessible.role: Accessible.AlertMessage
    }
}
