pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: browser
    required property var backend
    required property var modelState
    property string selectedDate: modelState.anchor
    property string preview: ""
    property bool datePicked: false
    property var selectedRows: []
    property string previousPeriod: modelState.period
    Connections {
        target: browser.backend
        function onChanged() {
            if (browser.previousPeriod !== browser.modelState.period) {
                browser.previousPeriod = browser.modelState.period;
                browser.selectedDate = browser.modelState.anchor;
                browser.datePicked = false;
                browser.preview = "";
                browser.selectedRows = [];
            }
            if (browser.datePicked) {
                browser.preview = browser.backend.eventActions.dayPreview(browser.selectedDate);
                browser.selectedRows = browser.backend.eventActions.dayRows(browser.selectedDate);
            }
        }
    }
    spacing: 16
    RowLayout {
        Layout.fillWidth: true
        UiText {
            Layout.fillWidth: true
            text: Qt.formatDate(new Date(browser.selectedDate + "T12:00:00"), "dd/MM/yyyy")
            color: Theme.secondary
        }
        ActionButton {
            id: createButton
            objectName: "calendar-new"
            text: browser.datePicked ? qsTr("Novo nesta data") : qsTr("Novo neste período")
            glyph: "plus"
            primary: true
            enabled: browser.modelState.hasVault
            onClicked: calendarCreate.open()
            Menu {
                id: calendarCreate
                y: createButton.height
                palette.window: Theme.surface
                palette.text: Theme.text
                palette.windowText: Theme.text
                palette.highlight: Theme.accentSurface
                palette.highlightedText: Theme.text
                function prepare() {
                    if (browser.datePicked)
                        browser.backend.navigate("day", browser.selectedDate);
                }
                MenuItem {
                    objectName: "calendar-new-task"
                    text: qsTr("Tarefa")
                    onTriggered: {
                        calendarCreate.prepare();
                        browser.backend.planningActions.create("task");
                    }
                }
                MenuItem {
                    objectName: "calendar-new-goal"
                    text: qsTr("Objetivo")
                    onTriggered: {
                        calendarCreate.prepare();
                        browser.backend.planningActions.create("goal");
                    }
                }
                MenuItem {
                    objectName: "calendar-new-event"
                    text: qsTr("Evento")
                    onTriggered: {
                        calendarCreate.prepare();
                        browser.backend.eventActions.create();
                    }
                }
                MenuItem {
                    text: qsTr("Hábito")
                    onTriggered: {
                        calendarCreate.prepare();
                        browser.backend.newHabit();
                    }
                }
                MenuItem {
                    objectName: "calendar-new-note"
                    text: qsTr("Nota")
                    onTriggered: {
                        calendarCreate.prepare();
                        browser.backend.contentActions.create();
                    }
                }
                MenuItem {
                    text: qsTr("Avaliação")
                    onTriggered: {
                        calendarCreate.prepare();
                        browser.backend.contentActions.createReview();
                    }
                }
            }
        }
        ActionButton {
            objectName: "calendar-open-day"
            text: qsTr("Abrir dia")
            onClicked: browser.backend.navigate("day", browser.selectedDate)
        }
    }
    UiText {
        Layout.fillWidth: true
        visible: browser.preview.length > 0 && browser.selectedRows.length === 0
        text: browser.preview
        color: Theme.secondary
    }
    GridLayout {
        Layout.fillWidth: true
        visible: browser.modelState.view === "year" && browser.modelState.children.length > 0
        columns: browser.width > 720 ? 3 : browser.width > 400 ? 2 : 1
        columnSpacing: 12
        rowSpacing: 12
        Repeater {
            model: browser.modelState.children
            delegate: Button {
                id: periodCard
                required property var modelData
                Layout.fillWidth: true
                Layout.preferredHeight: 84
                padding: 16
                hoverEnabled: true
                Accessible.name: modelData.label + ", " + modelData.detail
                onClicked: browser.backend.navigate(modelData.view, modelData.date)
                contentItem: ColumnLayout {
                    spacing: 6
                    UiText {
                        Layout.fillWidth: true
                        text: periodCard.modelData.label
                        font.weight: Font.Medium
                    }
                    UiText {
                        Layout.fillWidth: true
                        text: periodCard.modelData.detail
                        font.pixelSize: 12
                        color: Theme.secondary
                    }
                }
                background: Rectangle {
                    radius: 10
                    color: periodCard.down || periodCard.hovered ? Theme.hover : Theme.surface
                    border.color: periodCard.activeFocus ? Theme.accent : Theme.border
                    border.width: periodCard.activeFocus ? 2 : 1
                    Behavior on color {
                        ColorAnimation {
                            duration: Theme.duration
                        }
                    }
                }
            }
        }
    }
    Surface {
        Layout.fillWidth: true
        visible: browser.modelState.calendar.length > 0
        padding: browser.width > 650 ? 12 : 4
        background: Rectangle {
            color: "transparent"
        }
        ColumnLayout {
            anchors.fill: parent
            spacing: 12
            RowLayout {
                Layout.fillWidth: true
                UiText {
                    text: Qt.formatDate(new Date(browser.modelState.anchor + "T12:00:00"), "MMMM yyyy")
                    font.weight: Font.Medium
                    Layout.fillWidth: true
                }
                UiText {
                    text: qsTr("Semana ISO · seg–dom")
                    color: Theme.muted
                    font.pixelSize: 11
                }
            }
            GridLayout {
                Layout.fillWidth: true
                columns: 8
                columnSpacing: 4
                rowSpacing: 4
                Repeater {
                    model: [qsTr("Sem."), qsTr("Seg"), qsTr("Ter"), qsTr("Qua"), qsTr("Qui"), qsTr("Sex"), qsTr("Sáb"), qsTr("Dom")]
                    delegate: UiText {
                        required property string modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: 28
                        text: modelData
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        color: Theme.muted
                        font.pixelSize: 11
                    }
                }
                Repeater {
                    model: 48
                    delegate: ActionButton {
                        required property int index
                        objectName: (weekCell ? "calendar-week-" : "calendar-day-") + cell.date
                        readonly property bool weekCell: index % 8 === 0
                        readonly property var cell: browser.modelState.calendar[Math.floor(index / 8) * 7 + Math.max(0, index % 8 - 1)]
                        Layout.fillWidth: true
                        Layout.preferredWidth: 38
                        Layout.preferredHeight: browser.width > 600 ? 46 : 38
                        implicitWidth: 32
                        horizontalPadding: 0
                        text: weekCell ? String(cell.week).padStart(2, "0") : String(cell.day)
                        property string daySummary: ""
                        hint: weekCell ? qsTr("Abrir semana %1").arg(cell.week) : cell.label + "\n" + daySummary
                        onHoveredChanged: if (hovered && !weekCell)
                            daySummary = browser.backend.eventActions.dayPreview(cell.date)
                        onActiveFocusChanged: if (activeFocus && !weekCell)
                            daySummary = browser.backend.eventActions.dayPreview(cell.date)
                        quiet: true
                        selected: !weekCell && cell.date === browser.modelState.today
                        opacity: weekCell || !cell.inMonth ? 0.7 : 1
                        onClicked: {
                            if (weekCell)
                                browser.backend.navigate("week", cell.date);
                            else {
                                browser.datePicked = true;
                                browser.selectedDate = cell.date;
                                browser.preview = browser.backend.eventActions.dayPreview(cell.date);
                                browser.selectedRows = browser.backend.eventActions.dayRows(cell.date);
                            }
                        }
                    }
                }
            }
            UiText {
                Layout.fillWidth: true
                text: qsTr("Passe o mouse ou selecione um dia para ver seus registros. Use Novo nesta data para adicionar.")
                color: Theme.muted
                font.pixelSize: 12
            }
        }
    }
    Repeater {
        model: browser.selectedRows
        delegate: ActionButton {
            required property var modelData
            Layout.fillWidth: true
            alignLeft: true
            quiet: true
            objectName: "agenda-open-" + modelData.source_id + "-" + modelData.display_day
            text: modelData.title + " · " + modelData.time_label + " · " + modelData.status_label
            onClicked: browser.backend.eventActions.openOccurrence(modelData.source_kind, modelData.source_id, modelData.display_day)
        }
    }
}
