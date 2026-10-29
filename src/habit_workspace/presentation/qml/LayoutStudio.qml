import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "StudioLabels.js" as Labels

Rectangle {
    id: root
    required property var studio
    readonly property var state: studio ? studio.state : ({})
    readonly property bool narrow: width < 900
    property bool inspecting: true
    property bool wasPreview: false
    color: Theme.canvas
    visible: !!state.active
    enabled: !state.busy
    function requestAdd(kind, target) {
        libraryDrawer.close();
        if (kind.endsWith("_input")) {
            metricDialog.kind = kind;
            metricDialog.targetIndex = target;
            metricDialog.open();
        } else {
            const before = root.state.blocks.length;
            root.studio.add(kind, "", "", "");
            if (root.state.blocks.length > before && target < before) root.studio.move(before, target);
            inspecting = true;
        }
    }
    function showLibrary() {
        if (width < 1100) libraryDrawer.open();
        else { libraryScroll.contentItem.contentY = 0; library.focusFirst(); }
    }
    onStateChanged: {
        if (!!state.preview !== wasPreview) {
            wasPreview = !!state.preview;
            Qt.callLater(() => { const flickable = canvasScroll.contentItem as Flickable; if (flickable) flickable.contentY = 0; });
        }
    }
    function discard() { if (state.dirty) discardDialog.open(); else studio.discard(); }
    Shortcut { sequence: "Ctrl+Z"; enabled: root.visible && !metricDialog.opened; onActivated: root.studio.command("undo") }
    Shortcut { sequence: "Ctrl+Shift+Z"; enabled: root.visible && !metricDialog.opened; onActivated: root.studio.command("redo") }
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: root.narrow ? 12 : 24
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                UiText { text: qsTr("Layout Studio"); font.pixelSize: 20; font.weight: Font.Medium }
                UiText { Layout.fillWidth: true; text: root.state.periodLabel || ""; color: Theme.secondary }
            }
            ActionButton { objectName: "studio-close"; text: qsTr("Voltar à página"); quiet: true; onClicked: root.discard() }
        }
        Flow {
            Layout.fillWidth: true
            spacing: 8
            ActionButton { objectName: "studio-add"; visible: !root.state.preview; text: qsTr("Adicionar bloco"); onClicked: root.showLibrary() }
            ActionButton { objectName: "studio-start"; visible: !root.state.preview; text: qsTr("Ponto de partida"); onClicked: startDialog.open() }
            ActionButton { objectName: "studio-undo"; text: qsTr("Desfazer"); enabled: !!root.state.undo && !root.state.preview; onClicked: root.studio.command("undo") }
            ActionButton { objectName: "studio-redo"; text: qsTr("Refazer"); enabled: !!root.state.redo && !root.state.preview; onClicked: root.studio.command("redo") }
            ActionButton { objectName: "studio-preview"; text: root.state.preview ? qsTr("Voltar à edição") : qsTr("Prévia"); onClicked: root.studio.command("preview") }
            ActionButton { objectName: "studio-columns"; visible: !root.state.preview; text: root.state.columns === 2 ? qsTr("2 colunas") : qsTr("1 coluna"); hint: qsTr("Alternar entre uma e duas colunas"); onClicked: root.studio.command("columns") }
            ActionButton { objectName: "studio-save"; text: qsTr("Revisar e salvar"); primary: true; onClicked: { root.studio.prepare(); saveDialog.open(); } }
        }
        UiText { Layout.fillWidth: true; visible: !!root.state.message && !metricDialog.opened; text: root.state.message || ""; color: Theme.warning }
        ActionButton { objectName: "studio-back"; visible: !!root.state.nested; text: qsTr("Voltar à seção anterior"); onClicked: root.studio.command("back") }
        UiText { Layout.fillWidth: true; visible: !!root.state.preview; text: qsTr("Prévia · valores de exemplo, sem gravação. Registre hábitos e valores ao voltar à página."); color: Theme.accent }
        RowLayout {
            visible: root.narrow && !root.state.preview
            ActionButton { objectName: "studio-show-canvas"; text: qsTr("Página"); selected: !root.inspecting; onClicked: root.inspecting = false }
            ActionButton { objectName: "studio-show-properties"; text: qsTr("Propriedades"); selected: root.inspecting; onClicked: root.inspecting = true }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 24
            ScrollView {
                id: libraryScroll
                visible: root.width >= 1100 && !root.state.preview
                Layout.preferredWidth: 218
                Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true
                StudioLibrary { id: library; width: parent.width; onRequested: kind => root.requestAdd(kind, root.state.blocks.length) }
            }
            ScrollView {
                id: canvasScroll
                objectName: "studio-canvas-scroll"
                visible: !root.narrow || !root.inspecting || !!root.state.preview
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true
                ColumnLayout {
                    width: parent.width
                    spacing: 16
                    UiText { Layout.fillWidth: true; text: root.state.preview ? qsTr("Sua página") : qsTr("Organize sua página"); font.weight: Font.Medium }
                    UiText { Layout.fillWidth: true; visible: !root.state.preview; text: qsTr("Selecione um bloco para configurar. Use a alça de pontos para arrastar ou os botões de mover nas propriedades."); color: Theme.muted; font.pixelSize: 12 }
                    ColumnLayout {
                        visible: !(root.state.blocks || []).length
                        Layout.fillWidth: true
                        UiText { Layout.fillWidth: true; text: qsTr("Como você quer acompanhar sua rotina?"); font.pixelSize: 18 }
                        UiText { Layout.fillWidth: true; text: qsTr("Comece com uma lista de hábitos ou um campo, como tempo de leitura. Você poderá organizar os blocos depois."); color: Theme.secondary }
                        ActionButton { visible: !root.state.preview; text: qsTr("Adicionar lista de hábitos"); onClicked: root.requestAdd("checklist", 0) }
                    }
                    LayoutComposition {
                        Layout.fillWidth: true
                        objectName: "studio-composition"
                        blocks: root.state.blocks || []
                        preview: !!root.state.preview
                        gridColumns: root.state.columns || 1
                        editing: !root.state.preview
                        selected: root.state.selected === undefined ? -1 : root.state.selected
                        onSelectedBlock: function(index) { root.studio.select(index); root.inspecting = true; }
                        onMovedBlock: function(source, target) { root.studio.move(source, target); }
                        onDroppedKind: function(kind, target) { root.requestAdd(kind, target); }
                    }
                }
            }
            ScrollView {
                visible: !root.state.preview && (!root.narrow || root.inspecting)
                Layout.preferredWidth: root.narrow ? -1 : 292
                Layout.fillWidth: root.narrow
                Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true
                ColumnLayout {
                    width: parent.width
                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: !(root.state.current || {}).id
                        UiText { Layout.fillWidth: true; text: qsTr("Seu layout"); font.pixelSize: 16; font.weight: Font.Medium }
                        UiText { Layout.fillWidth: true; text: qsTr("Selecione um bloco na página para ajustar seu título, conteúdo e largura."); color: Theme.secondary }
                        UiText { Layout.fillWidth: true; text: qsTr("Adicionar um bloco organiza a página. Usar um hábito ou campo existente mantém os mesmos registros."); color: Theme.secondary }
                        ActionButton { text: qsTr("Escolher um ponto de partida"); onClicked: startDialog.open() }
                    }
                    StudioProperties { Layout.fillWidth: true; studio: root.studio }
                }
            }
        }
    }
    Drawer {
        id: libraryDrawer
        interactive: false
        enter: Transition { NumberAnimation { property: "position"; to: 1; duration: Theme.duration } }
        exit: Transition { NumberAnimation { property: "position"; to: 0; duration: Theme.duration } }
        width: Math.min(root.width - 32, 320)
        height: root.height
        edge: Qt.LeftEdge
        modal: true
        background: Rectangle { color: Theme.sidebar }
        contentItem: ScrollView {
            implicitHeight: 0
            implicitWidth: 0
            contentWidth: availableWidth
            clip: true
            padding: 16
            Loader {
                width: parent.width
                active: libraryDrawer.opened
                sourceComponent: StudioLibrary { onRequested: kind => root.requestAdd(kind, root.state.blocks.length) }
            }
        }
    }
    StudioDialog {
        id: metricDialog
        objectName: "metric-dialog"
        property string kind: "text_input"
        property int targetIndex: 0
        anchors.centerIn: parent
        width: Math.min(root.width - 32, 520)
        height: Math.min(root.height - 32, (metricLoader.item ? metricLoader.item.implicitHeight : 0) + header.implicitHeight + footer.implicitHeight + topPadding + bottomPadding + 24)
        title: qsTr("Adicionar campo · ") + Labels.label(kind)
        modal: true
        closePolicy: Popup.NoAutoClose
        onAboutToShow: { metricLoader.active = true; Qt.callLater(() => { if (metricLoader.item) metricLoader.item.focusFirst(); }); }
        onClosed: metricLoader.active = false
        contentItem: ScrollView {
            implicitHeight: 0
            implicitWidth: 0
            contentWidth: availableWidth
            clip: true
            ColumnLayout {
                width: parent.width
                Loader {
                    id: metricLoader
                    Layout.fillWidth: true
                    active: false
                    sourceComponent: MetricSetup { valueType: metricDialog.kind.replace("_input", ""); sources: root.state.sources || [] }
                }
                UiText { Layout.fillWidth: true; text: root.state.message || ""; color: Theme.error; visible: text.length > 0 }
            }
        }
        footer: DialogButtonBox {
            ActionButton { objectName: "metric-cancel"; text: qsTr("Cancelar"); onClicked: metricDialog.close() }
            ActionButton {
                objectName: "metric-create"
                text: qsTr("Adicionar campo")
                primary: true
                onClicked: {
                    const form = metricLoader.item;
                    if (!form || !form.validate()) return;
                    const before = root.state.blocks.length;
                    root.studio.addConfigured(form.effectiveType + "_input", form.sourceId, form.useExisting ? "" : form.name, form.useExisting ? "" : form.tags, form.options());
                    if (root.state.blocks.length > before) {
                        if (metricDialog.targetIndex < before) root.studio.move(before, metricDialog.targetIndex);
                        root.inspecting = true;
                        metricDialog.close();
                    }
                }
            }
        }
    }
    StudioDialog {
        id: startDialog
        anchors.centerIn: parent
        width: Math.min(root.width - 32, 520)
        height: Math.min(root.height - 32, startContent.implicitHeight + header.implicitHeight + footer.implicitHeight + 40)
        title: qsTr("Escolher ponto de partida")
        modal: true
        contentItem: ScrollView {
            implicitHeight: 0
            implicitWidth: 0
            contentWidth: availableWidth
            clip: true
            ColumnLayout {
                id: startContent
                width: parent.width
                UiText { Layout.fillWidth: true; text: qsTr("A escolha substitui os blocos deste rascunho e pode ser desfeita. Os registros existentes serão preservados."); color: Theme.secondary }
                StudioChoice {
                    id: startingPoint
                    objectName: "studio-start-choice"
                    Layout.fillWidth: true
                    label: qsTr("Ponto de partida")
                    textRole: "name"; valueRole: "key"
                    model: [{key: "current", name: "Personalizar layout atual"}, {key: "empty", name: "Começar vazio"}, {key: "default", name: "Usar padrão deste tipo de período"}].concat(root.state.templates || [])
                }
                UiText { Layout.fillWidth: true; text: qsTr("Modelos existentes são copiados para este período. O modelo original e os outros períodos permanecem como estão."); color: Theme.secondary }
            }
        }
        footer: DialogButtonBox {
            ActionButton { text: qsTr("Cancelar"); onClicked: startDialog.close() }
            ActionButton { objectName: "studio-start-apply"; text: qsTr("Usar este layout"); primary: true; onClicked: { root.studio.startFrom(startingPoint.currentValue); if (!root.state.message) { root.inspecting = false; startDialog.close(); } } }
        }
    }
    StudioDialog {
        id: discardDialog
        anchors.centerIn: parent
        width: Math.min(root.width - 32, 440)
        height: Math.min(root.height - 32, 220)
        implicitHeight: 220
        title: qsTr("Descartar alterações não salvas?")
        modal: true
        contentItem: UiText { text: qsTr("A página continuará com o último layout salvo. Seus registros serão preservados.") }
        footer: DialogButtonBox {
            ActionButton { text: qsTr("Continuar editando"); onClicked: discardDialog.close() }
            ActionButton { text: qsTr("Descartar alterações"); onClicked: { discardDialog.close(); root.studio.discard(); } }
        }
    }
    StudioDialog {
        id: saveDialog
        objectName: "studio-save-dialog"
        anchors.centerIn: parent
        width: Math.min(root.width - 32, 560)
        height: Math.min(root.height - 32, summary.implicitHeight + header.implicitHeight + footer.implicitHeight + 40)
        title: qsTr("Revisar alterações do layout")
        modal: true
        contentItem: ScrollView {
            implicitHeight: 0
            implicitWidth: 0
            contentWidth: availableWidth
            clip: true
            UiText { id: summary; width: parent.width; text: root.state.summary || "" }
        }
        footer: DialogButtonBox {
            ActionButton { text: qsTr("Cancelar"); onClicked: saveDialog.close() }
            ActionButton { objectName: "studio-confirm-save"; text: qsTr("Salvar"); primary: true; onClicked: { saveDialog.close(); root.studio.save(); } }
        }
    }
}
