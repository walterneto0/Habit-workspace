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

        Flow {
            visible: root.modelState.view === "planning"
            Layout.fillWidth: true
            spacing: 8
            ActionButton {
                id: newButton
                objectName: "planning-new"
                text: qsTr("Novo")
                glyph: "plus"
                primary: true
                onClicked: createMenu.open()
                Menu {
                    id: createMenu
                    y: newButton.height + 4
                    palette.window: Theme.surface
                    palette.text: Theme.text
                    palette.windowText: Theme.text
                    palette.highlight: Theme.accentSurface
                    palette.highlightedText: Theme.text
                    MenuItem {
                        objectName: "new-task"
                        text: qsTr("Tarefa")
                        enabled: !root.modelState.planningSaving
                        onTriggered: root.backend.planningActions.create("task")
                    }
                    MenuItem {
                        objectName: "new-goal"
                        text: qsTr("Objetivo")
                        enabled: !root.modelState.planningSaving
                        onTriggered: root.backend.planningActions.create("goal")
                    }
                    MenuItem {
                        objectName: "new-event"
                        text: qsTr("Evento")
                        onTriggered: root.backend.eventActions.create()
                    }
                    MenuSeparator {}
                    MenuItem {
                        text: qsTr("Nota")
                        onTriggered: root.backend.contentActions.create()
                    }
                    MenuItem {
                        text: qsTr("Avaliação do período")
                        onTriggered: root.backend.contentActions.createReview()
                    }
                }
            }
            ActionButton {
                objectName: "planning-all"
                quiet: true
                visible: root.modelState.view !== "planning"
                text: qsTr("Ver tudo")
                onClicked: root.backend.navigate("planning", "")
            }
            StudioCheckBox {
                text: qsTr("Mostrar concluídas")
                checked: root.showCompleted
                onToggled: root.showCompleted = checked
            }
        }
        Input {
            visible: root.modelState.view === "planning"
            objectName: "planning-search"
            Layout.fillWidth: true
            placeholderText: qsTr("Buscar tarefas, objetivos e eventos por título, descrição ou tag")
            Accessible.name: placeholderText
            text: root.modelState.query || ""
            onTextEdited: root.backend.setQuery(text)
        }
        Repeater {
            model: root.modelState.eventResults || []
            delegate: ActionButton {
                required property var modelData
                Layout.fillWidth: true
                text: qsTr("Evento · ") + modelData.title
                onClicked: root.backend.eventActions.open("event", modelData.id)
            }
        }
        UiText {
            Layout.fillWidth: true
            text: qsTr("Tarefas e objetivos · situação atual")
            color: Theme.secondary
            font.pixelSize: 12
        }
        UiText {
            Layout.fillWidth: true
            visible: !root.rows.length
            text: qsTr("Nenhum item encontrado. Crie uma tarefa ou objetivo, ou ajuste a busca.")
            color: Theme.secondary
        }
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
        UiText {
            visible: !!root.modelState.planningSaving
            text: qsTr("Salvando…")
            Accessible.role: Accessible.AlertMessage
        }
    }
}
