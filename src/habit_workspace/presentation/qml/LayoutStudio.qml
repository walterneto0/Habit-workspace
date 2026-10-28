import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    required property var studio
    readonly property var state: studio ? studio.state : ({})
    function requestAdd(kind, target) {
        const sourceId = source.model[source.currentIndex] ? source.model[source.currentIndex].id : "";
        if (kind.endsWith("_input") && !sourceId) {
            metricDialog.kind = kind;
            metricDialog.targetIndex = target;
            metricDialog.open();
        } else {
            const before = root.state.blocks.length;
            root.studio.add(kind, sourceId, paletteFieldName.text, paletteTags.text);
            if (root.state.blocks.length > before && target < before) root.studio.move(before, target);
        }
    }
    color: Theme.canvas
    visible: !!state.active
    enabled: !state.busy
    // Controls inherit a theme palette through this pane.

    property bool wasPreview: false
    onStateChanged: {
        if (!!state.preview !== wasPreview) {
            wasPreview = !!state.preview;
            Qt.callLater(() => { const flickable = canvasScroll.contentItem as Flickable; if (flickable) flickable.contentY = 0; });
        }
    }
    function discard() { if (state.dirty) discardDialog.open(); else studio.discard(); }
    Shortcut { sequence: "Ctrl+Z"; enabled: root.visible; onActivated: root.studio.command("undo") }
    Shortcut { sequence: "Ctrl+Shift+Z"; enabled: root.visible; onActivated: root.studio.command("redo") }
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12
        UiText { text: qsTr("Layout Studio · ") + (root.state.period || ""); font.pixelSize: 20 }
        Flow {
            Layout.fillWidth: true
            spacing: 8
            ActionButton { objectName: "studio-undo"; text: qsTr("Desfazer"); enabled: !!root.state.undo; onClicked: root.studio.command("undo") }
            ActionButton { objectName: "studio-redo"; text: qsTr("Refazer"); enabled: !!root.state.redo; onClicked: root.studio.command("redo") }
            ActionButton { objectName: "studio-preview"; text: root.state.preview ? qsTr("Voltar à edição") : qsTr("Prévia"); onClicked: root.studio.command("preview") }
            ActionButton { objectName: "studio-columns"; enabled: !root.state.preview; text: qsTr("Colunas: ") + root.state.columns; onClicked: root.studio.command("columns") }
            ActionButton { objectName: "studio-close"; text: qsTr("Fechar"); onClicked: root.discard() }
            ActionButton { objectName: "studio-save"; text: qsTr("Revisar e salvar"); primary: true; onClicked: { root.studio.prepare(); saveDialog.open(); } }
        }
        UiText { Layout.fillWidth: true; visible: !!root.state.message; text: root.state.message || ""; color: Theme.warning }
        ActionButton { objectName: "studio-back"; visible: !!root.state.nested; text: qsTr("Voltar à seção anterior"); onClicked: root.studio.command("back") }
        UiText { Layout.fillWidth: true; visible: !!root.state.preview; text: qsTr("Prévia — exemplos fictícios, sem gravação de valores."); color: Theme.accent }
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16
            ScrollView {
                visible: !root.state.preview
                Layout.preferredWidth: root.width < 1100 ? 170 : 210
                Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true
                ColumnLayout {
                    width: parent.width
                    UiText { text: qsTr("Biblioteca"); font.weight: Font.Medium }
                    UiText { Layout.fillWidth: true; text: qsTr("Inputs: escolha a fonte ou nomeie explicitamente um novo campo antes de adicionar."); color: Theme.secondary }
                    StudioChoice {
                        id: source
                        Layout.fillWidth: true
                        model: [{id: "", name: "Criar novo campo"}].concat(root.state.sources || [])
                        textRole: "name"
                        label: qsTr("Fonte existente ou novo campo")
                    }
                    Input { id: paletteFieldName; Layout.fillWidth: true; placeholderText: qsTr("Nome do novo campo"); Accessible.name: placeholderText }
                    Input { id: paletteTags; Layout.fillWidth: true; placeholderText: qsTr("Tags, separadas por vírgula"); Accessible.name: placeholderText }
                    Repeater {
                        model: (root.state.palette || []).length
                        delegate: ActionButton {
                            id: paletteButton
                            objectName: "palette-" + modelData
                            required property int index
                            readonly property string modelData: root.state.palette[index]
                            property string paletteKind: modelData
                            Item {
                                id: paletteProxy
                                Drag.active: paletteMouse.drag.active
                                width: 1; height: 1
                                Drag.source: paletteButton
                                Drag.keys: ["layout-block"]
                            }
                            MouseArea {
                                id: paletteMouse
                                anchors.fill: parent
                                drag.target: paletteProxy
                                onPressed: function(mouse) { paletteButton.forceActiveFocus(); paletteProxy.x = mouse.x; paletteProxy.y = mouse.y; }
                                onReleased: { paletteProxy.Drag.drop(); paletteProxy.x = 0; paletteProxy.y = 0; }
                                onClicked: paletteButton.clicked()
                            }
                            Layout.fillWidth: true
                            text: ({checklist:"Checklist", list:"Lista", table:"Tabela", chart:"Gráfico", note:"Nota", image:"Imagem", section:"Seção", number_input:"Número", integer_input:"Inteiro", text_input:"Texto", boolean_input:"Booleano", rating_input:"Avaliação", date_input:"Data", time_input:"Horário", duration_input:"Duração", selection_input:"Seleção"})[modelData] || modelData
                            onClicked: root.requestAdd(modelData, root.state.blocks.length)
                        }
                    }
                }
            }
            ScrollView {
                id: canvasScroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true
                ColumnLayout {
                    width: parent.width
                    UiText { visible: !(root.state.blocks || []).length; text: qsTr("Layout vazio. Adicione um componente.") }
                    LayoutComposition {
                        Layout.fillWidth: true
                        objectName: "studio-composition"
                        blocks: root.state.blocks || []
                        preview: !!root.state.preview
                        gridColumns: root.state.columns || 1
                        editing: !root.state.preview
                        selected: root.state.selected === undefined ? -1 : root.state.selected
                        onSelectedBlock: function(index) { root.studio.select(index); }
                        onMovedBlock: function(source, target) { root.studio.move(source, target); }
                        onDroppedKind: function(kind, target) {
                            root.requestAdd(kind, target);
                        }
                    }
                    Loader {
                        Layout.fillWidth: true
                        active: root.width < 1200 && !root.state.preview
                        sourceComponent: propertiesPanel
                    }
                }
            }
            ScrollView {
                visible: root.width >= 1200 && !root.state.preview
                Layout.preferredWidth: 260
                Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true
                Loader { width: parent.width; active: root.width >= 1200 && !root.state.preview; sourceComponent: propertiesPanel }
            }
        }
    }
    Component {
        id: propertiesPanel
        StudioProperties { studio: root.studio }
    }
    Dialog {
        id: metricDialog
        property string kind: "text_input"
        property int targetIndex: 0
        anchors.centerIn: parent
        width: Math.min(root.width - 32, 520)
        height: Math.min(root.height - 32, 680)
        title: qsTr("Configurar novo campo")
        modal: true
        onOpened: metricLoader.active = true
        onClosed: metricLoader.active = false
        contentItem: ColumnLayout {
            UiText { Layout.fillWidth: true; text: root.state.message || ""; color: Theme.error; visible: text.length > 0 }
            ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            clip: true
            Loader {
                id: metricLoader
                width: parent.width
                active: false
                sourceComponent: MetricSetup { valueType: metricDialog.kind.replace("_input", ""); initialName: paletteFieldName.text; initialTags: paletteTags.text }
            }
        }
        }
        footer: DialogButtonBox {
            ActionButton { text: qsTr("Cancelar"); onClicked: metricDialog.close() }
            ActionButton {
                objectName: "metric-create"
                text: qsTr("Adicionar campo")
                primary: true
                onClicked: {
                    const before = root.state.blocks.length;
                    const form = metricLoader.item;
                    root.studio.addConfigured(metricDialog.kind, "", form.name, form.tags, form.options());
                    if (root.state.blocks.length > before) {
                        if (metricDialog.targetIndex < before) root.studio.move(before, metricDialog.targetIndex);
                        metricDialog.close();
                    }
                }
            }
        }
    }
    Dialog {
        id: discardDialog
        anchors.centerIn: parent
        title: qsTr("Descartar alterações não salvas?")
        modal: true
        standardButtons: Dialog.Discard | Dialog.Cancel
        onDiscarded: root.studio.discard()
    }
    Dialog {
        id: saveDialog
        objectName: "studio-save-dialog"
        anchors.centerIn: parent
        width: Math.min(root.width - 32, 560)
        title: qsTr("Salvar nova revisão imutável")
        modal: true
        standardButtons: Dialog.Save | Dialog.Cancel
        contentItem: UiText { text: root.state.summary || "" }
        onAccepted: root.studio.save()
    }
}
