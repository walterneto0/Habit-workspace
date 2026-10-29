pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    required property var backend
    readonly property var modelState: backend.state
    readonly property bool narrow: width < 1000
    readonly property bool sidebarCollapsed: narrow || modelState.sidebarCollapsed
    property bool showProperties: true
    property string previousView: ""
    width: 1200
    height: 800
    minimumWidth: 640
    minimumHeight: 480
    visible: true
    title: modelState.hasVault ? modelState.vaultName + " — Habit Workspace" : "Habit Workspace"
    color: Theme.canvas
    font.family: "sans-serif"
    font.pixelSize: 13
    Component.onCompleted: {
        Theme.dark = modelState.theme !== "light";
        Theme.reducedMotion = modelState.reducedMotion;
    }
    Connections {
        target: window.backend
        function onChanged() {
            Theme.dark = window.modelState.theme !== "light";
            Theme.reducedMotion = window.modelState.reducedMotion;
            if (Theme.reducedMotion) {
                pageEntrance.stop();
                pageContent.opacity = 1;
            }
            if (window.previousView !== window.modelState.view + window.modelState.period) {
                window.previousView = window.modelState.view + window.modelState.period;
                const flickable = workspaceScroll.contentItem as Flickable;
                if (flickable)
                    flickable.contentY = 0;
                if (!Theme.reducedMotion)
                    pageEntrance.restart();
            }
        }
    }
    LayoutStudio {
        id: studioView
        anchors.fill: parent
        z: 20
        studio: window.backend.layoutStudio
    }
    // Tab navigation must reveal controls below the viewport, including in dialogs.
    onActiveFocusItemChanged: Qt.callLater(ensureFocusVisible)
    function ensureFocusVisible() {
        const focused = activeFocusItem;
        if (!focused)
            return;
        let ancestor = focused.parent;
        while (ancestor) {
            const flickable = ancestor as Flickable;
            if (flickable) {
                const point = focused.mapToItem(flickable.contentItem, 0, 0);
                if (point.y < flickable.contentY)
                    flickable.contentY = Math.max(0, point.y - 8);
                else if (point.y + focused.height > flickable.contentY + flickable.height)
                    flickable.contentY = Math.min(flickable.contentHeight - flickable.height, point.y + focused.height - flickable.height + 8);
                return;
            }
            ancestor = ancestor.parent;
        }
    }
    function openVault() {
        backend.dismissNotice();
        vaultDialog.open();
    }
    function openImport() {
        if (modelState.hasVault) {
            backend.dismissNotice();
            importDialog.open();
        }
    }
    function properties() {
        if (width < 1280)
            propertiesDrawer.open();
        else
            showProperties = !showProperties;
    }

    Shortcut {
        sequence: "Ctrl+B"
        onActivated: window.backend.setSidebarCollapsed(!window.modelState.sidebarCollapsed)
    }
    Shortcut {
        sequence: "Ctrl+O"
        onActivated: window.openVault()
    }
    Shortcut {
        sequence: "Ctrl+I"
        enabled: window.modelState.hasVault
        onActivated: window.openImport()
    }
    Shortcut {
        sequence: "Ctrl+T"
        onActivated: window.backend.goToday()
    }
    Shortcut {
        sequence: "Ctrl+K"
        enabled: search.visible
        onActivated: search.forceActiveFocus()
    }
    Shortcut {
        sequence: "Alt+Left"
        enabled: !!window.modelState.period
        onActivated: window.backend.movePeriod(-1)
    }
    Shortcut {
        sequence: "Alt+Right"
        enabled: !!window.modelState.period
        onActivated: window.backend.movePeriod(1)
    }
    Shortcut {
        sequence: "Alt+Shift+Left"
        enabled: window.modelState.hasVault && !!window.modelState.period
        onActivated: window.backend.moveCaptureDate(-1)
    }
    Shortcut {
        sequence: "Alt+Shift+Right"
        enabled: window.modelState.hasVault && !!window.modelState.period
        onActivated: window.backend.moveCaptureDate(1)
    }
    Shortcut {
        sequence: "Escape"
        enabled: !vaultDialog.visible && !importDialog.visible && !propertiesDrawer.visible
        onActivated: window.backend.clearSelection()
    }

    onClosing: function(close) { if (backend.layoutStudio.state.active) { close.accepted = false; studioView.discard(); } }

    RowLayout {
        anchors.fill: parent
        spacing: 0
        Sidebar {
            backend: window.backend
            modelState: window.modelState
            collapsed: window.sidebarCollapsed
            Layout.fillHeight: true
            Layout.preferredWidth: window.sidebarCollapsed ? 64 : 224
            Behavior on Layout.preferredWidth {
                NumberAnimation {
                    duration: Theme.reducedMotion ? 0 : 190
                    easing.type: Easing.OutCubic
                }
            }
            onVaultRequested: window.openVault()
        }
        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 60
                color: Theme.canvas
                Rectangle {
                    anchors.bottom: parent.bottom
                    height: 1
                    width: parent.width
                    color: Theme.border
                }
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 20
                    anchors.rightMargin: 20
                    spacing: 12
                    ActionButton {
                        glyph: "sidebar"
                        compact: true
                        quiet: true
                        hint: window.narrow ? qsTr("Barra compacta nesta largura") : qsTr("Alternar barra lateral · Ctrl+B")
                        enabled: !window.narrow
                        onClicked: window.backend.setSidebarCollapsed(!window.modelState.sidebarCollapsed)
                    }
                    UiText {
                        Layout.fillWidth: true
                        text: window.modelState.hasVault ? window.modelState.vaultName : qsTr("Habit Workspace")
                        color: Theme.secondary
                        elide: Text.ElideRight
                        wrapMode: Text.NoWrap
                    }
                    ActionButton {
                        glyph: "sun"
                        compact: true
                        quiet: true
                        hint: Theme.dark ? qsTr("Usar tema claro") : qsTr("Usar tema escuro")
                        onClicked: window.backend.setTheme(Theme.dark ? "light" : "dark")
                    }
                    ActionButton {
                        text: qsTr("Importar")
                        glyph: "download"
                        compact: window.width < 820
                        enabled: window.modelState.hasVault
                        hint: qsTr("Importar documento · Ctrl+I")
                        onClicked: window.openImport()
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0
                ScrollView {
                    id: workspaceScroll
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: availableWidth
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ColumnLayout {
                        id: page
                        width: workspaceScroll.availableWidth
                        spacing: 0
                        Item {
                            Layout.preferredHeight: window.narrow ? 24 : 36
                        }
                        ColumnLayout {
                            id: pageContent
                            Layout.alignment: Qt.AlignHCenter
                            Layout.preferredWidth: Math.min(page.width - (window.narrow ? 40 : 64), 1000)
                            Layout.maximumWidth: Math.min(page.width - (window.narrow ? 40 : 64), 1000)
                            spacing: 24
                            Flow {
                                Layout.fillWidth: true
                                spacing: 4
                                visible: !!window.modelState.period
                                Repeater {
                                    model: window.modelState.breadcrumbs
                                    delegate: ActionButton {
                                        required property var modelData
                                        text: modelData.label
                                        selected: window.modelState.period === modelData.period
                                        quiet: true
                                        implicitHeight: 30
                                        onClicked: window.backend.navigate(modelData.view, modelData.date)
                                    }
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                UiText {
                                    Layout.fillWidth: true
                                    text: !window.modelState.hasVault && window.modelState.view === "overview" ? qsTr("Tudo começa com um espaço seu.") : window.modelState.title
                                    font.pixelSize: window.narrow ? 24 : 28
                                    font.weight: Font.DemiBold
                                    font.letterSpacing: -0.5
                                }
                                UiText {
                                    Layout.fillWidth: true
                                    text: window.modelState.period ? window.modelState.range : window.modelState.view === "overview" ? (window.modelState.hasVault ? qsTr("Seu planejamento, no seu tempo.  ·  ") + window.modelState.todayLabel : qsTr("Planeje com calma. Mantenha seus arquivos por perto.")) : window.modelState.view === "notes" ? qsTr("Documentos e notas do seu cofre, organizados por título e tags.") : window.modelState.view === "habits" ? qsTr("Definições canônicas · escopo, recorrência e tags.") : window.modelState.view === "settings" ? qsTr("Ajuste seu espaço de trabalho.") : qsTr("Uma visão do que importa, com dados do seu cofre.")
                                    color: Theme.secondary
                                    lineHeight: 1.3
                                }
                            }
                            Flow {
                                Layout.fillWidth: true
                                visible: !!window.modelState.period
                                spacing: 8
                                ActionButton {
                                    glyph: "left"
                                    compact: true
                                    hint: qsTr("Período anterior · Alt+←")
                                    onClicked: window.backend.movePeriod(-1)
                                }
                                ActionButton {
                                    text: qsTr("Hoje")
                                    onClicked: window.backend.goToday()
                                }
                                ActionButton {
                                    glyph: "right"
                                    compact: true
                                    hint: qsTr("Próximo período · Alt+→")
                                    onClicked: window.backend.movePeriod(1)
                                }
                                Input {
                                    id: jumpDate
                                    width: 184
                                    placeholderText: qsTr("Data: AAAA-MM-DD")
                                    Accessible.name: qsTr("Ir para uma data, formato ano-mês-dia; pressione Enter")
                                    onAccepted: window.backend.navigate(window.modelState.view, text)
                                }
                            }
                            Surface {
                                Layout.fillWidth: true
                                visible: !!window.modelState.notice
                                padding: 12
                                RowLayout {
                                    anchors.fill: parent
                                    spacing: 12
                                    Glyph {
                                        name: window.modelState.noticeError ? "info" : "check"
                                        ink: window.modelState.noticeError ? Theme.error : Theme.success
                                    }
                                    UiText {
                                        Layout.fillWidth: true
                                        text: window.modelState.notice
                                        color: window.modelState.noticeError ? Theme.error : Theme.secondary
                                        wrapMode: Text.WrapAnywhere
                                    }
                                    ActionButton {
                                        glyph: "close"
                                        compact: true
                                        quiet: true
                                        hint: qsTr("Dispensar mensagem")
                                        onClicked: window.backend.dismissNotice()
                                    }
                                }
                            }
                            Surface {
                                Layout.fillWidth: true
                                visible: !window.modelState.hasVault && window.modelState.view !== "settings" && window.modelState.view !== "statistics"
                                padding: window.narrow ? 24 : 32
                                ColumnLayout {
                                    anchors.fill: parent
                                    spacing: 20
                                    Rectangle {
                                        width: 56
                                        height: 56
                                        radius: 14
                                        color: Theme.accentSurface
                                        Glyph {
                                            anchors.centerIn: parent
                                            width: 28
                                            height: 28
                                            name: "folder"
                                            ink: Theme.accent
                                        }
                                    }
                                    UiText {
                                        Layout.fillWidth: true
                                        text: qsTr("Um cofre para suas ideias e seus dias")
                                        font.pixelSize: 20
                                        font.weight: Font.Medium
                                    }
                                    UiText {
                                        Layout.fillWidth: true
                                        text: qsTr("Escolha uma pasta para guardar seu planejamento. Você controla seus arquivos, pode abrir em outros editores e levar para outro computador.")
                                        color: Theme.secondary
                                        lineHeight: 1.4
                                    }
                                    Flow {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        ActionButton {
                                            primary: true
                                            text: qsTr("Criar cofre")
                                            glyph: "plus"
                                            onClicked: {
                                                vaultDialog.creating = true;
                                                window.openVault();
                                            }
                                        }
                                        ActionButton {
                                            text: qsTr("Abrir cofre existente")
                                            glyph: "folder"
                                            onClicked: {
                                                vaultDialog.creating = false;
                                                window.openVault();
                                            }
                                        }
                                    }
                                    UiText {
                                        Layout.fillWidth: true
                                        text: qsTr("LOCAL POR ESCOLHA. SEU POR INTEIRO.")
                                        font.pixelSize: 10
                                        font.letterSpacing: 1.2
                                        color: Theme.muted
                                    }
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                visible: window.modelState.view === "overview"
                                spacing: 16
                                RowLayout {
                                    Layout.fillWidth: true
                                    UiText {
                                        Layout.fillWidth: true
                                        text: qsTr("Explore seu tempo")
                                        font.weight: Font.Medium
                                    }
                                    UiText {
                                        text: qsTr("ANO → DIA")
                                        font.pixelSize: 10
                                        font.letterSpacing: 1
                                        color: Theme.muted
                                    }
                                }
                                GridLayout {
                                    Layout.fillWidth: true
                                    columns: pageContent.width > 650 ? 3 : 1
                                    columnSpacing: 12
                                    rowSpacing: 12
                                    Repeater {
                                        model: [
                                            {
                                                view: "month",
                                                title: qsTr("Este mês"),
                                                detail: qsTr("Veja o calendário e suas semanas"),
                                                icon: "calendar"
                                            },
                                            {
                                                view: "week",
                                                title: qsTr("Esta semana"),
                                                detail: qsTr("Encontre espaço entre os dias"),
                                                icon: "week"
                                            },
                                            {
                                                view: "day",
                                                title: qsTr("Hoje"),
                                                detail: qsTr("Abra o dia de hoje"),
                                                icon: "day"
                                            }
                                        ]
                                        delegate: ActionButton {
                                            required property var modelData
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 64
                                            text: modelData.title
                                            glyph: modelData.icon
                                            hint: modelData.detail
                                            onClicked: window.backend.navigate(modelData.view, window.modelState.today)
                                        }
                                    }
                                }
                            }
                            PeriodBrowser {
                                Layout.fillWidth: true
                                backend: window.backend
                                modelState: window.modelState
                                visible: !!window.modelState.period
                            }
                            ColumnLayout {
                                Layout.fillWidth: true
                                visible: window.modelState.hasVault && !!window.modelState.period
                                spacing: 12
                                TrackingPanel {
                                    Layout.fillWidth: true
                                    backend: window.backend
                                    modelState: window.modelState
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    UiText { Layout.fillWidth: true; text: qsTr("Layout ativo desde: ") + (window.modelState.composition.activation || ""); color: Theme.secondary }
                                    ActionButton {
                                        text: qsTr("Editar layout no Studio")
                                        objectName: "open-layout-studio"
                                        onClicked: window.backend.layoutStudio.open()
                                    }
                                }
                                UiText { Layout.fillWidth: true; text: (window.modelState.composition.issues || []).concat(window.modelState.composition.captureError ? [window.modelState.composition.captureError] : []).join("\n"); color: Theme.warning; visible: text.length > 0 }
                                LayoutComposition {
                                    objectName: "tracking-composition"
                                    Layout.fillWidth: true
                                    tracking: true
                                    feedback: (window.modelState.tracking || {}).feedback || ({})
                                    blocks: window.modelState.composition.blocks || []
                                    gridColumns: window.modelState.composition.columns || 1
                                    onCheckin: (habitId, state, token) => window.backend.setCheckin(habitId, state, token)
                                    onObserve: (fieldId, blockId, text, token) => window.backend.saveObservation(fieldId, blockId, text, token)
                                    onObserveBoolean: (fieldId, blockId, value, token) => window.backend.setBooleanObservation(fieldId, blockId, value, token)
                                    onClearValue: (fieldId, token) => window.backend.clearObservation(fieldId, token)
                                }
                            }
                            Input {
                                id: search
                                objectName: "document-search"
                                Layout.fillWidth: true
                                visible: window.modelState.hasVault && window.modelState.view !== "settings" && window.modelState.view !== "statistics"
                                placeholderText: qsTr("Buscar título, tag ou ID nesta página…  Ctrl+K")
                                text: window.modelState.query
                                onTextEdited: window.backend.setQuery(text)
                            }
                            DocumentList {
                                Layout.fillWidth: true
                                visible: window.modelState.hasVault && window.modelState.view !== "settings" && window.modelState.view !== "statistics"
                                backend: window.backend
                                modelState: window.modelState
                                onImportRequested: window.openImport()
                                onPropertiesRequested: window.properties()
                            }
                            EmptyState {
                                Layout.fillWidth: true
                                visible: window.modelState.view === "statistics"
                                glyph: "chart"
                                heading: qsTr("Estatísticas chegam em uma próxima etapa")
                                description: qsTr("Gráficos e resumos serão calculados a partir dos seus registros. O motor de análises será desenvolvido na Fase 8; não há métricas calculadas nesta versão.")
                            }
                            SettingsPage {
                                Layout.fillWidth: true
                                visible: window.modelState.view === "settings"
                                backend: window.backend
                                modelState: window.modelState
                                onVaultRequested: window.openVault()
                                onImportRequested: window.openImport()
                            }
                            Surface {
                                Layout.fillWidth: true
                                visible: window.modelState.issues.length > 0
                                ColumnLayout {
                                    anchors.fill: parent
                                    spacing: 16
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Glyph {
                                            name: "info"
                                            ink: Theme.warning
                                        }
                                        UiText {
                                            Layout.fillWidth: true
                                            text: qsTr("Pendências do cofre")
                                            color: Theme.warning
                                            font.weight: Font.Medium
                                        }
                                        ActionButton {
                                            text: qsTr("Reindexar")
                                            onClicked: window.backend.reindex()
                                        }
                                    }
                                    Repeater {
                                        model: window.modelState.issues
                                        delegate: ColumnLayout {
                                            required property var modelData
                                            Layout.fillWidth: true
                                            spacing: 6
                                            UiText {
                                                Layout.fillWidth: true
                                                text: parent.modelData.title
                                                font.weight: Font.Medium
                                                wrapMode: Text.WrapAnywhere
                                            }
                                            UiText {
                                                Layout.fillWidth: true
                                                text: parent.modelData.detail
                                                color: Theme.secondary
                                                font.pixelSize: 12
                                                wrapMode: Text.WrapAnywhere
                                            }
                                        }
                                    }
                                }
                            }
                            UiText {
                                Layout.fillWidth: true
                                text: window.modelState.hasVault ? qsTr("%1 documento(s) no cofre · Arquivos locais · Sem sincronização").arg(window.modelState.documentCount) : qsTr("Explore o calendário sem criar arquivos. Abra um cofre quando quiser começar.")
                                color: Theme.muted
                                font.pixelSize: 11
                                wrapMode: Text.Wrap
                            }
                        }
                        Item {
                            Layout.preferredHeight: 36
                        }
                    }
                }
                Rectangle {
                    Layout.fillHeight: true
                    Layout.preferredWidth: 280
                    visible: window.width >= 1280 && window.showProperties && !!window.modelState.selected.id
                    color: Theme.sidebar
                    Rectangle {
                        width: 1
                        height: parent.height
                        color: Theme.border
                    }
                    ScrollView {
                        anchors.fill: parent
                        anchors.margins: 20
                        contentWidth: availableWidth
                        clip: true
                        DocumentDetails {
                            width: parent.width
                            backend: window.backend
                            document: window.modelState.selected
                        }
                    }
                }
            }
        }
    }
    NumberAnimation {
        id: pageEntrance
        target: pageContent
        property: "opacity"
        from: 0.55
        to: 1
        duration: 160
    }
    VaultDialog {
        id: vaultDialog
        backend: window.backend
        modelState: window.modelState
    }
    HabitDialog {
        backend: window.backend
        modelState: window.modelState
    }
    ImportDialog {
        id: importDialog
        backend: window.backend
        modelState: window.modelState
    }
    Drawer {
        id: propertiesDrawer
        edge: Qt.RightEdge
        width: Math.min(window.width - 48, 320)
        height: window.height
        modal: true
        leftPadding: 24
        rightPadding: 24
        topPadding: 24
        bottomPadding: 24
        background: Rectangle {
            color: Theme.sidebar
            border.color: Theme.border
        }
        enter: Transition {
            NumberAnimation {
                property: "position"
                duration: Theme.reducedMotion ? 0 : 180
            }
        }
        exit: Transition {
            NumberAnimation {
                property: "position"
                duration: Theme.reducedMotion ? 0 : 150
            }
        }
        contentItem: ColumnLayout {
            ActionButton {
                Layout.alignment: Qt.AlignRight
                glyph: "close"
                compact: true
                hint: qsTr("Fechar propriedades")
                onClicked: propertiesDrawer.close()
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: availableWidth
                clip: true
                DocumentDetails {
                    width: parent.width
                    backend: window.backend
                    document: window.modelState.selected
                }
            }
        }
    }
}
