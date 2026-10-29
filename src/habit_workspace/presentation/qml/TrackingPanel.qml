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
                text: root.habits.error || qsTr("Nenhum hábito ativo neste período. Crie um e vincule-o a uma checklist no Layout Studio.")
                color: root.habits.error ? Theme.error : Theme.secondary
            }
            Repeater {
                model: root.showDefinitions ? (root.habits.rows || []) : []
                delegate: RowLayout {
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
                    ActionButton {
                        objectName: "edit-habit-" + habitRow.modelData.id
                        text: qsTr("Editar")
                        hint: qsTr("Editar nome, tags, escopo e recorrência de ") + habitRow.modelData.name
                        onClicked: root.backend.editHabit(habitRow.modelData.id)
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
