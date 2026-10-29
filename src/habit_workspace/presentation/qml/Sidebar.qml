pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: sidebar
    required property var backend
    required property var modelState
    property bool collapsed: false
    signal vaultRequested
    color: Theme.sidebar
    clip: true
    Rectangle {
        anchors.right: parent.right
        width: 1
        height: parent.height
        color: Theme.border
    }
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: sidebar.collapsed ? 12 : 16
        spacing: 8
        ActionButton {
            alignLeft: true
            Layout.fillWidth: true
            Layout.topMargin: 6
            Layout.bottomMargin: 16
            text: sidebar.modelState.vaultName
            glyph: "folder"
            compact: sidebar.collapsed
            hint: sidebar.modelState.hasVault ? qsTr("Trocar cofre · Ctrl+O") : qsTr("Criar ou abrir cofre · Ctrl+O")
            quiet: true
            onClicked: sidebar.vaultRequested()
        }
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ColumnLayout {
                width: parent.width
                spacing: 4
                Repeater {
                    model: [
                        {
                            view: "overview",
                            label: qsTr("Visão geral"),
                            icon: "grid"
                        },
                        {
                            view: "calendar",
                            label: qsTr("Calendário"),
                            icon: "calendar"
                        },
                        {
                            view: "statistics",
                            label: qsTr("Estatísticas"),
                            icon: "chart"
                        },
                        {
                            view: "habits",
                            label: qsTr("Hábitos"),
                            icon: "day"
                        },
                        {
                            view: "notes",
                            label: qsTr("Documentos e notas"),
                            icon: "note"
                        }
                    ]
                    delegate: ActionButton {
                        alignLeft: true
                        required property var modelData
                        Layout.fillWidth: true
                        objectName: "nav-" + modelData.view
                        text: modelData.label
                        hint: modelData.label
                        glyph: modelData.icon
                        compact: sidebar.collapsed
                        quiet: true
                        selected: sidebar.modelState.view === modelData.view
                        onClicked: sidebar.backend.navigate(modelData.view)
                    }
                }
                UiText {
                    Layout.topMargin: 24
                    Layout.bottomMargin: 8
                    Layout.leftMargin: 12
                    text: sidebar.collapsed ? "···" : qsTr("ESPAÇO TEMPORAL")
                    color: Theme.muted
                    font.pixelSize: 10
                    font.letterSpacing: 1.1
                }
                Repeater {
                    model: [
                        {
                            view: "year",
                            label: qsTr("Anos"),
                            icon: "grid"
                        },
                        {
                            view: "month",
                            label: qsTr("Meses"),
                            icon: "calendar"
                        },
                        {
                            view: "week",
                            label: qsTr("Semanas"),
                            icon: "week"
                        },
                        {
                            view: "day",
                            label: qsTr("Dias"),
                            icon: "day"
                        }
                    ]
                    delegate: ActionButton {
                        alignLeft: true
                        required property var modelData
                        Layout.fillWidth: true
                        objectName: "nav-" + modelData.view
                        text: modelData.label
                        hint: modelData.label
                        glyph: modelData.icon
                        compact: sidebar.collapsed
                        quiet: true
                        selected: sidebar.modelState.view === modelData.view
                        onClicked: sidebar.backend.navigate(modelData.view)
                    }
                }
            }
        }
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.border
        }
        ActionButton {
            alignLeft: true
            Layout.fillWidth: true
            text: qsTr("Configurações")
            glyph: "settings"
            compact: sidebar.collapsed
            quiet: true
            selected: sidebar.modelState.view === "settings"
            onClicked: sidebar.backend.navigate("settings")
        }
        UiText {
            visible: !sidebar.collapsed
            Layout.leftMargin: 12
            Layout.bottomMargin: 6
            text: qsTr("LOCAL · SEM CONTA")
            color: Theme.muted
            font.pixelSize: 10
            font.letterSpacing: 1
        }
    }
}
