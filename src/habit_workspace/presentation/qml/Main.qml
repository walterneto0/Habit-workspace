import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    property string vaultStatus: qsTr("Persistência local pronta. Use os comandos de diagnóstico para criar, abrir e importar documentos nesta fase.")
    width: 1100
    height: 740
    minimumWidth: 640
    minimumHeight: 480
    visible: true
    title: qsTr("Habit Workspace")
    color: "#101116"
    font.family: "sans-serif"
    font.pixelSize: 14

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - 64, 480)
        spacing: 16

        Label {
            Layout.fillWidth: true
            text: qsTr("Habit Workspace")
            color: "#F2F3F5"
            font.pixelSize: 28
            font.weight: Font.Medium
            wrapMode: Text.WordWrap
            Accessible.name: text
        }

        Label {
            Layout.fillWidth: true
            text: qsTr("Seu espaço pessoal de planejamento.")
            color: "#A7ADB8"
            wrapMode: Text.WordWrap
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: status.implicitHeight + 32
            color: "#1A1D25"
            border.color: "#30343D"
            radius: 10

            Label {
                id: status
                anchors.fill: parent
                anchors.margins: 16
                text: window.vaultStatus
                textFormat: Text.PlainText
                color: "#A7ADB8"
                wrapMode: Text.WordWrap
            }
        }
    }
}
