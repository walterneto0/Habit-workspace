pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Selected capture date and the canonical habits relevant to the open period.
ColumnLayout {
    id: root
    required property var backend
    required property var modelState
    readonly property var tracking: modelState.tracking || ({})
    readonly property var habits: modelState.habits || ({})
    property bool showDefinitions: false
    spacing: 12
    Surface {
        Layout.fillWidth: true
        ColumnLayout {
            anchors.fill: parent
            spacing: 10
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Glyph { name: "day"; ink: Theme.accent }
                UiText { text: qsTr("Modo de acompanhamento"); font.weight: Font.Medium }
                UiText {
                    Layout.fillWidth: true
                    text: qsTr("· valores reais do dia, sem abrir o Layout Studio")
                    color: Theme.muted
                    font.pixelSize: 12
                    elide: Text.ElideRight
                    wrapMode: Text.NoWrap
                }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                ActionButton {
                    objectName: "capture-previous"
                    visible: !root.tracking.fixed
                    glyph: "left"
                    compact: true
                    enabled: !!root.tracking.canPrevious
                    hint: qsTr("Dia anterior (Alt+Shift+←)")
                    onClicked: root.backend.moveCaptureDate(-1)
                }
                UiText {
                    objectName: "capture-date"
                    Layout.fillWidth: true
                    text: (root.tracking.label || "") + (root.tracking.isToday ? qsTr(" · hoje") : root.tracking.isFuture ? qsTr(" · futuro") : "")
                    font.weight: Font.Medium
                }
                ActionButton {
                    objectName: "capture-next"
                    visible: !root.tracking.fixed
                    glyph: "right"
                    compact: true
                    enabled: !!root.tracking.canNext
                    hint: qsTr("Próximo dia (Alt+Shift+→)")
                    onClicked: root.backend.moveCaptureDate(1)
                }
                Input {
                    id: jump
                    objectName: "capture-jump"
                    visible: !root.tracking.fixed
                    Layout.preferredWidth: 140
                    placeholderText: qsTr("AAAA-MM-DD")
                    Accessible.name: qsTr("Ir para data dentro do período")
                    onAccepted: root.backend.setCaptureDate(text)
                }
                ActionButton {
                    visible: !root.tracking.fixed && !root.tracking.isToday
                    text: qsTr("Hoje")
                    onClicked: root.backend.setCaptureDate(root.modelState.today)
                }
            }
            UiText {
                Layout.fillWidth: true
                visible: !!root.tracking.isFuture
                text: qsTr("Datas futuras ficam pendentes; nada é registrado ou considerado falha.")
                color: Theme.secondary
                font.pixelSize: 12
            }
        }
    }
    Surface {
        Layout.fillWidth: true
        ColumnLayout {
            anchors.fill: parent
            spacing: 10
            RowLayout {
                Layout.fillWidth: true
                UiText { Layout.fillWidth: true; text: qsTr("Hábitos deste período") + " · " + (root.habits.rows || []).length; font.weight: Font.Medium }
                ActionButton {
                    objectName: "toggle-habit-definitions"
                    text: root.showDefinitions ? qsTr("Recolher") : qsTr("Ver definições")
                    visible: (root.habits.rows || []).length > 0
                    onClicked: root.showDefinitions = !root.showDefinitions
                }
                ActionButton {
                    objectName: "new-habit"
                    glyph: "plus"
                    text: qsTr("Novo hábito")
                    onClicked: root.backend.newHabit()
                }
            }
            UiText {
                Layout.fillWidth: true
                visible: (root.habits.rows || []).length === 0
                text: root.habits.error || qsTr("Crie seu primeiro hábito. Depois, use Concluir para registrar o dia selecionado.")
                color: root.habits.error ? Theme.error : Theme.secondary
            }
            Repeater {
                model: root.habits.rows || []
                delegate: ColumnLayout {
                    id: habitRow
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 10
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        UiText { Layout.fillWidth: true; text: habitRow.modelData.name; font.weight: Font.Medium }
                        UiText {
                            Layout.fillWidth: true
                            visible: root.showDefinitions
                            text: habitRow.modelData.recurrence + " · " + habitRow.modelData.scope + (habitRow.modelData.tags ? " · #" + habitRow.modelData.tags.split(", ").join(" #") : "")
                            color: Theme.secondary
                            font.pixelSize: 12
                        }
                        UiText {
                            Layout.fillWidth: true
                            text: qsTr("Data selecionada: ") + habitRow.modelData.stateLabel + (habitRow.modelData.outside ? qsTr(" · %1 registro(s) fora da programação atual, preservado(s)").arg(habitRow.modelData.outside) : "")
                            color: Theme.muted
                            font.pixelSize: 12
                        }
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 6
                        ActionButton {
                            objectName: "quick-complete-" + habitRow.modelData.id
                            text: habitRow.modelData.cell.recorded === "done" ? qsTr("Concluído") : qsTr("Concluir")
                            selected: habitRow.modelData.cell.recorded === "done"
                            enabled: !!habitRow.modelData.cell.editable && !root.tracking.saving
                            Accessible.name: habitRow.modelData.name + " · " + root.tracking.label + " · " + text
                            onClicked: root.backend.captureActions.setCheckin(habitRow.modelData.id, "done", habitRow.modelData.cell.token)
                        }
                        ActionButton {
                            objectName: "quick-clear-" + habitRow.modelData.id
                            text: qsTr("Limpar registro")
                            visible: !!habitRow.modelData.cell.recorded
                            enabled: !!habitRow.modelData.cell.editable && !root.tracking.saving
                            onClicked: root.backend.captureActions.setCheckin(habitRow.modelData.id, "", habitRow.modelData.cell.token)
                        }
                        ActionButton {
                            objectName: "habit-details-" + habitRow.modelData.id
                            text: qsTr("Ver detalhes")
                            onClicked: root.backend.showHabit(habitRow.modelData.id)
                        }
                        ActionButton {
                            objectName: "edit-habit-" + habitRow.modelData.id
                            visible: root.showDefinitions
                            text: qsTr("Editar hábito")
                            enabled: !root.tracking.saving
                            onClicked: root.backend.editHabit(habitRow.modelData.id)
                        }
                    }
                    UiText {
                        objectName: "quick-feedback-" + habitRow.modelData.id
                        Layout.fillWidth: true
                        visible: (root.tracking.feedback || {}).target === habitRow.modelData.id
                        text: visible ? root.tracking.feedback.text : ""
                        color: root.tracking.feedback && root.tracking.feedback.error ? Theme.error : Theme.secondary
                        Accessible.role: Accessible.AlertMessage
                    }
                }
            }
            UiText {
                Layout.fillWidth: true
                visible: (root.habits.unresolved || []).length > 0
                text: qsTr("Check-ins de hábitos ausentes (rótulo salvo; nada foi recriado):\n") + (root.habits.unresolved || []).join("\n")
                color: Theme.warning
                font.pixelSize: 12
            }
        }
    }
}
