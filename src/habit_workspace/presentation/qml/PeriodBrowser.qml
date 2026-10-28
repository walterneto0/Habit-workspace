pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: browser
    required property var backend
    required property var modelState
    spacing: 16
    GridLayout {
        Layout.fillWidth: true
        visible: browser.modelState.children.length > 0
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
        visible: browser.modelState.view === "month" || browser.modelState.view === "calendar"
        padding: browser.width > 650 ? 24 : 12
        ColumnLayout {
            anchors.fill: parent
            spacing: 12
            RowLayout {
                Layout.fillWidth: true
                UiText {
                    text: qsTr("Calendário")
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
                        hint: weekCell ? qsTr("Abrir semana %1").arg(cell.week) : cell.label
                        quiet: true
                        selected: !weekCell && cell.date === browser.modelState.today
                        opacity: weekCell || !cell.inMonth ? 0.7 : 1
                        onClicked: browser.backend.navigate(weekCell ? "week" : "day", cell.date)
                    }
                }
            }
            UiText {
                Layout.fillWidth: true
                text: qsTr("Selecione um dia ou o número de uma semana para abrir o período.")
                color: Theme.muted
                font.pixelSize: 12
            }
        }
    }
}
