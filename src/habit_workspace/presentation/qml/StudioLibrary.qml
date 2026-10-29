import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "StudioLabels.js" as Labels

ColumnLayout {
    id: root
    signal requested(string kind)
    function focusFirst() { search.forceActiveFocus(); }
    function matches(kind) { return Labels.label(kind).toLocaleLowerCase().includes(search.text.trim().toLocaleLowerCase()); }
    spacing: 8
    UiText { Layout.fillWidth: true; text: qsTr("Adicionar bloco"); font.weight: Font.Medium; font.pixelSize: 16 }
    UiText { Layout.fillWidth: true; text: qsTr("Escolha o que deseja acompanhar ou mostrar na página."); color: Theme.secondary }
    Input { id: search; objectName: "library-search"; Layout.fillWidth: true; placeholderText: qsTr("Buscar bloco"); Accessible.name: placeholderText }
    Repeater {
        model: [
            {title: "Acompanhamento", detail: "Hábitos existentes, sem duplicar registros.", kinds: ["checklist", "list", "table"]},
            {title: "Conteúdo", detail: "Organize e contextualize sua rotina.", kinds: ["note", "image", "section"]},
            {title: "Campos de dados", detail: "Use um campo existente ou crie o seu.", kinds: ["text_input", "integer_input", "number_input", "duration_input", "date_input", "time_input", "boolean_input", "selection_input", "rating_input"]},
            {title: "Visualizações", detail: "Gráficos: configuração disponível; resultados na Fase 8.", kinds: ["chart"]}
        ]
        delegate: ColumnLayout {
            required property var modelData
            visible: modelData.kinds.some(root.matches)
            Layout.fillWidth: true
            spacing: 4
            UiText { Layout.fillWidth: true; Layout.topMargin: 12; text: modelData.title; font.weight: Font.Medium; color: Theme.secondary }
            UiText { Layout.fillWidth: true; text: modelData.detail; color: Theme.muted; font.pixelSize: 12 }
            Repeater {
                model: modelData.kinds.filter(root.matches)
                delegate: ActionButton {
                    id: button
                    required property string modelData
                    property string paletteKind: modelData
                    objectName: "palette-" + modelData
                    Layout.fillWidth: true
                    quiet: true
                    alignLeft: true
                    text: Labels.label(modelData)
                    hint: ({checklist: "Selecione vários hábitos, tags ou hábitos da data de acompanhamento.", list: "Lista geral: edição de itens disponível na Fase 7.", table: "Organize campos em colunas. Edição de linhas ainda indisponível.", note: "Exiba uma nota existente. Edição de notas na Fase 7.", image: "Exiba uma imagem local já no cofre. Importação de mídia na Fase 7.", section: "Agrupe blocos em uma seção com uma ou duas colunas.", chart: "Configure fontes e período. Cálculos e gráficos na Fase 8."})[modelData] || text + " · usar existente ou criar novo"
                    onClicked: root.requested(modelData)
                    Item {
                        id: proxy
                        width: 1; height: 1
                        Drag.active: pointer.drag.active
                        Drag.source: button
                        Drag.keys: ["layout-block"]
                    }
                    MouseArea {
                        id: pointer
                        anchors.fill: parent
                        drag.target: proxy
                        onPressed: function(mouse) { button.forceActiveFocus(); proxy.x = mouse.x; proxy.y = mouse.y; }
                        onReleased: { proxy.Drag.drop(); proxy.x = 0; proxy.y = 0; }
                        onClicked: button.clicked()
                    }
                }
            }
            UiText {
                Layout.fillWidth: true
                visible: modelData.title === "Acompanhamento" || modelData.title === "Conteúdo"
                text: modelData.title === "Acompanhamento" ? qsTr("Lista e tabela: estrutura disponível; edição de itens ainda indisponível.") : qsTr("Notas e imagens existentes podem ser exibidas. Edição e importação na Fase 7.")
                color: Theme.muted
                font.pixelSize: 12
            }
        }
    }
}
