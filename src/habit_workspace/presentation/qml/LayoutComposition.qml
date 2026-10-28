import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

GridLayout {
    id: root
    property var blocks: []
    property int gridColumns: 1
    property bool editing: false
    property bool preview: false
    property int selected: -1
    signal selectedBlock(int index)
    signal movedBlock(int source, int target)
    signal droppedKind(string kind, int target)
    columns: width < 420 ? 1 : gridColumns
    columnSpacing: 16
    rowSpacing: 16
    Repeater {
        model: root.blocks.length
        delegate: Rectangle {
            id: card
            objectName: "layout-card-" + index
            required property int index
            readonly property var modelData: root.blocks[index] || ({config: {}, title: "", type: "", width: 1, row: 0, column: 0})
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            Layout.columnSpan: Math.min(root.columns, modelData.width)
            Layout.row: root.columns === root.gridColumns ? modelData.row : index
            Layout.column: root.columns === root.gridColumns ? modelData.column : 0
            implicitHeight: content.implicitHeight + 32
            implicitWidth: 160
            radius: 10
            color: Theme.surface
            border.color: root.editing && root.selected === index ? Theme.accent : Theme.border
            border.width: root.editing && root.selected === index ? 2 : 1
            DropArea {
                id: dropTarget
                objectName: "layout-drop-" + card.index
                property bool valid: false
                property int dropWidth: 1
                anchors.fill: parent
                enabled: root.editing
                keys: ["layout-block"]
                onEntered: function(drag) { dropWidth = drag.source && drag.source.blockWidth ? drag.source.blockWidth : 1; valid = drag.source && (drag.source.paletteKind !== undefined || (drag.source.blockIndex !== undefined && drag.source.blockIndex !== card.index)); }
                onDropped: function(drop) {
                    if (!valid) { drop.accepted = false; return; }
                    const source = drop.source;
                    if (source.blockIndex !== undefined) {
                        const from = source.blockIndex;
                        Qt.callLater(() => root.movedBlock(from, card.index));
                    } else if (source.paletteKind !== undefined) {
                        const kind = source.paletteKind;
                        Qt.callLater(() => root.droppedKind(kind, card.index));
                    }
                    drop.acceptProposedAction();
                }
                Rectangle {
                    anchors.fill: parent
                    visible: dropTarget.containsDrag
                    color: "transparent"
                    border.width: 3
                    border.color: dropTarget.valid ? Theme.accent : Theme.error
                    z: 5
                    UiText { anchors.top: parent.top; anchors.horizontalCenter: parent.horizontalCenter; text: dropTarget.valid ? qsTr("Inserir antes · largura: ") + dropTarget.dropWidth + qsTr(" coluna(s)") : qsTr("Destino inválido · mesmo componente"); color: dropTarget.valid ? Theme.accent : Theme.error }
                }
            }
            ColumnLayout {
                id: content
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12
                ActionButton {
                    id: handle
                    objectName: "layout-handle-" + card.index
                    property int blockIndex: card.index
                    property int blockWidth: card.modelData.width
                    visible: root.editing
                    Item {
                        id: dragProxy
                        Drag.active: dragMouse.drag.active
                        width: 1; height: 1
                        Drag.source: handle
                        Drag.keys: ["layout-block"]
                    }
                    MouseArea {
                        id: dragMouse
                        anchors.fill: parent
                        drag.target: dragProxy
                        onPressed: function(mouse) { handle.forceActiveFocus(); dragProxy.x = mouse.x; dragProxy.y = mouse.y; }
                        onReleased: { dragProxy.Drag.drop(); dragProxy.x = 0; dragProxy.y = 0; }
                        onClicked: handle.clicked()
                    }
                    Layout.fillWidth: true
                    text: qsTr("Selecionar · ") + card.modelData.title
                    onClicked: root.selectedBlock(card.index)
                }
                UiText { Layout.fillWidth: true; text: card.modelData.title; font.weight: Font.Medium }
                UiText { Layout.fillWidth: true; text: card.modelData.bindingLabel || ""; visible: text.length > 0; color: Theme.secondary }
                StudioCheckBox {
                    visible: card.modelData.type === "checklist" || card.modelData.type === "boolean_input"
                    enabled: false
                    text: qsTr("Sem registro · captura na Fase 6")
                }
                Input {
                    Layout.fillWidth: true
                    visible: ["text_input", "integer_input", "number_input", "date_input", "time_input", "duration_input"].includes(card.modelData.type)
                    readOnly: true
                    text: root.preview ? ({text_input:"Texto de exemplo", integer_input:"3", number_input:"3.5", date_input:"2026-10-29", time_input:"09:30", duration_input:"25"}[card.modelData.type] || "") : ""
                    placeholderText: card.modelData.config.placeholder || ({date_input:"AAAA-MM-DD", time_input:"HH:MM", duration_input:"Duração", integer_input:"Inteiro", number_input:"Número", text_input:"Texto"}[card.modelData.type] || "") + qsTr(" · sem registro")
                    Accessible.name: card.modelData.title
                }
                StudioChoice {
                    Layout.fillWidth: true
                    visible: card.modelData.type === "selection_input"
                    enabled: false
                    label: card.modelData.title
                    model: root.preview ? [qsTr("Exemplo fictício")].concat(card.modelData.options || []) : [qsTr("Sem registro")].concat(card.modelData.options || [])
                }
                Slider {
                    Layout.fillWidth: true
                    visible: card.modelData.type === "rating_input"
                    enabled: false
                    from: card.modelData.minimum === undefined ? 1 : card.modelData.minimum
                    to: card.modelData.maximum === undefined ? 5 : card.modelData.maximum
                    value: root.preview ? (from + to) / 2 : from
                    Accessible.name: card.modelData.title + qsTr(" · avaliação sem registro")
                }
                UiText {
                    Layout.fillWidth: true
                    visible: !!card.modelData.config.required
                    text: qsTr("Obrigatório quando a captura estiver disponível")
                    color: Theme.secondary
                }
                UiText {
                    Layout.fillWidth: true
                    text: card.modelData.imageSource ? (card.modelData.config.alt || "") : card.modelData.detail || ({note: qsTr("Nota sem conteúdo vinculado. Edição na Fase 7."), list: qsTr("Lista vazia · captura na Fase 7."), table: qsTr("Tabela sem colunas configuradas."), chart: qsTr("Nenhuma fonte selecionada."), image: qsTr("Imagem indisponível. Importação de mídia na Fase 7."), section: qsTr("Seção")}[card.modelData.type] || qsTr("Captura de valores disponível na Fase 6."))
                    textFormat: Text.PlainText
                    color: Theme.secondary
                }
                Flow {
                    Layout.fillWidth: true
                    visible: card.modelData.type === "table"
                    spacing: 8
                    Repeater {
                        model: card.modelData.type === "table" ? (card.modelData.config.columns || []) : []
                        delegate: Rectangle {
                            required property var modelData
                            width: Math.min(180, parent.width)
                            height: 66
                            color: Theme.canvas
                            radius: 6
                            UiText { anchors.fill: parent; anchors.margins: 8; text: modelData.label + "\n" + modelData.value_type; color: Theme.secondary }
                        }
                    }
                }
                Image {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 160
                    visible: !!card.modelData.imageSource
                    source: card.modelData.imageSource || ""
                    fillMode: card.modelData.config.fit === "cover" ? Image.PreserveAspectCrop : Image.PreserveAspectFit
                    Accessible.name: card.modelData.config.alt || card.modelData.title
                    clip: true
                }
                Rectangle {
                    visible: card.modelData.type === "chart"
                    Layout.fillWidth: true
                    implicitHeight: 96
                    color: Theme.canvas
                    radius: 6
                    UiText { anchors.fill: parent; anchors.margins: 12; text: qsTr("Prévia de configuração — sem resultados calculados\n") + (card.modelData.config.aggregation || "") + " · " + (card.modelData.config.period || qsTr("período da página")); color: Theme.muted }
                }
                Loader {
                    Layout.fillWidth: true
                    active: card.modelData.type === "section"
                    source: active ? "LayoutComposition.qml" : ""
                    onLoaded: {
                        item.blocks = Qt.binding(() => card.modelData.children || []);
                        item.gridColumns = Qt.binding(() => card.modelData.config.columns || 1);
                        item.preview = Qt.binding(() => root.preview);
                    }
                }
            }
        }
    }
    Rectangle {
        objectName: "layout-append"
        visible: root.editing
        Layout.fillWidth: true
        Layout.columnSpan: root.columns
        Layout.column: 0
        Layout.row: root.blocks.length ? Math.max(...root.blocks.map(b => root.columns === root.gridColumns ? b.row : root.blocks.indexOf(b))) + 1 : 0
        implicitHeight: 72
        color: appendDrop.containsDrag ? Theme.accentSurface : Theme.canvas
        border.color: appendDrop.containsDrag ? Theme.accent : Theme.border
        radius: 6
        UiText { anchors.fill: parent; anchors.margins: 12; text: appendDrop.containsDrag ? qsTr("Soltar no final · encaixe na grade; ajuste a largura em Propriedades") : qsTr("Arraste um componente aqui ou use os botões da biblioteca."); color: Theme.secondary }
        DropArea {
            id: appendDrop
            objectName: "layout-append-drop"
            anchors.fill: parent
            keys: ["layout-block"]
            onDropped: function(drop) {
                const source = drop.source;
                if (source && source.blockIndex !== undefined) {
                    const from = source.blockIndex;
                    Qt.callLater(() => root.movedBlock(from, root.blocks.length - 1));
                } else if (source && source.paletteKind !== undefined) {
                    const kind = source.paletteKind;
                    Qt.callLater(() => root.droppedKind(kind, root.blocks.length));
                } else { drop.accepted = false; return; }
                drop.acceptProposedAction();
            }
        }
    }

}
