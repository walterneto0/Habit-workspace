import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: settings
    required property var backend
    required property var modelState
    signal vaultRequested
    signal importRequested
    spacing: 16
    Surface {
        Layout.fillWidth: true
        ColumnLayout {
            anchors.fill: parent
            spacing: 16
            UiText {
                text: qsTr("Aparência")
                font.pixelSize: 16
                font.weight: Font.Medium
            }
            UiText {
                Layout.fillWidth: true
                text: qsTr("Um espaço confortável para o seu ritmo.")
                color: Theme.secondary
            }
            Flow {
                Layout.fillWidth: true
                spacing: 8
                ActionButton {
                    text: qsTr("Escuro")
                    selected: settings.modelState.theme === "dark"
                    onClicked: settings.backend.setTheme("dark")
                }
                ActionButton {
                    text: qsTr("Claro")
                    glyph: "sun"
                    selected: settings.modelState.theme === "light"
                    onClicked: settings.backend.setTheme("light")
                }
                ActionButton {
                    text: settings.modelState.reducedMotion ? qsTr("Movimento reduzido: ativado") : qsTr("Reduzir movimento")
                    glyph: settings.modelState.reducedMotion ? "check" : ""
                    selected: settings.modelState.reducedMotion
                    onClicked: settings.backend.setReducedMotion(!settings.modelState.reducedMotion)
                }
            }
        }
    }
    Surface {
        Layout.fillWidth: true
        ColumnLayout {
            anchors.fill: parent
            spacing: 12
            UiText {
                text: qsTr("Cofre local")
                font.pixelSize: 16
                font.weight: Font.Medium
            }
            UiText {
                Layout.fillWidth: true
                text: settings.modelState.hasVault ? settings.modelState.vaultName : qsTr("Nenhum cofre aberto")
                font.weight: Font.Medium
            }
            UiText {
                Layout.fillWidth: true
                text: settings.modelState.vaultPath
                color: Theme.secondary
                wrapMode: Text.WrapAnywhere
            }
            Flow {
                Layout.fillWidth: true
                spacing: 8
                ActionButton {
                    text: qsTr("Criar ou abrir")
                    glyph: "folder"
                    onClicked: settings.vaultRequested()
                }
                ActionButton {
                    text: qsTr("Importar arquivo")
                    glyph: "download"
                    enabled: settings.modelState.hasVault
                    onClicked: settings.importRequested()
                }
                ActionButton {
                    text: qsTr("Reindexar")
                    enabled: settings.modelState.hasVault
                    onClicked: settings.backend.reindex()
                }
                ActionButton {
                    text: qsTr("Abrir pasta")
                    enabled: settings.modelState.hasVault
                    onClicked: settings.backend.revealVault()
                }
            }
            UiText {
                Layout.fillWidth: true
                text: qsTr("Exportar com dependências e backup local integrado chegam na Fase 9. Por enquanto, feche o aplicativo e copie a pasta inteira para fazer uma cópia de segurança.")
                color: Theme.secondary
            }
        }
    }
    Surface {
        Layout.fillWidth: true
        ColumnLayout {
            anchors.fill: parent
            spacing: 12
            UiText {
                text: qsTr("Privacidade, com clareza")
                font.pixelSize: 16
                font.weight: Font.Medium
            }
            UiText {
                Layout.fillWidth: true
                text: qsTr("Sem conta, sem telemetria e sem nuvem. O aplicativo funciona offline.\n\nSeus documentos são arquivos de texto, sem criptografia. Quem tem acesso ao dispositivo pode lê-los. Armazenamento local não garante anonimato e não substitui backup.")
                color: Theme.secondary
                lineHeight: 1.3
            }
        }
    }
    Surface {
        Layout.fillWidth: true
        ColumnLayout {
            anchors.fill: parent
            spacing: 12
            UiText {
                text: qsTr("Atalhos")
                font.pixelSize: 16
                font.weight: Font.Medium
            }
            UiText {
                Layout.fillWidth: true
                text: qsTr("Ctrl+B   Recolher ou expandir a barra lateral\nCtrl+O   Criar, abrir ou trocar cofre\nCtrl+I   Importar documento\nCtrl+K   Buscar nos documentos da página\nAlt+← / Alt+→   Período anterior / seguinte\nCtrl+T   Ir para hoje\nEsc   Fechar diálogo ou prévia\nTab / Shift+Tab   Navegar entre controles")
                color: Theme.secondary
                lineHeight: 1.5
            }
        }
    }
}
