pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Create or edit one canonical habit. Validation and persistence stay in Python.
Dialog {
    id: dialog
    objectName: "habit-dialog"
    required property var backend
    required property var modelState
    readonly property var form: modelState.habitForm || ({})
    readonly property bool wanted: !!form.open
    property string scopeMode: "period"
    property string recurrence: "daily"
    property var days: []
    modal: true
    anchors.centerIn: parent
    width: Math.min(parent.width - 32, 560)
    height: Math.min(parent.height - 32, content.implicitHeight + 48)
    padding: 24
    closePolicy: Popup.CloseOnEscape
    background: Rectangle {
        color: Theme.surface
        border.color: Theme.border
        radius: 14
    }
    Overlay.modal: Rectangle {
        color: "#88000000"
    }
    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.reducedMotion ? 0 : 180 }
    }
    exit: Transition {
        NumberAnimation { property: "opacity"; from: 1; to: 0; duration: Theme.reducedMotion ? 0 : 150 }
    }
    onWantedChanged: wanted ? open() : close()
    onAboutToShow: {
        name.text = form.name || "";
        tags.text = form.tags || "";
        start.text = form.start || "";
        end.text = form.end || "";
        scopeMode = form.scopeMode || "period";
        recurrence = form.recurrence || "daily";
        days = (form.days || []).slice();
        bind.checked = !!form.bind;
    }
    onOpened: name.forceActiveFocus()
    onClosed: if (wanted) backend.cancelHabit()
    function values(acknowledge) {
        return {name: name.text, tags: tags.text, scopeMode: scopeMode, start: start.text, end: end.text, recurrence: recurrence, days: days, bind: bind.checked, acknowledge: acknowledge};
    }
    function toggleDay(day) {
        const next = days.slice();
        const at = next.indexOf(day);
        if (at >= 0) next.splice(at, 1); else next.push(day);
        days = next;
    }
    contentItem: ScrollView {
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            id: content
            width: parent.width
            spacing: 12
            RowLayout {
                Layout.fillWidth: true
                UiText {
                    Layout.fillWidth: true
                    text: dialog.form.mode === "edit" ? qsTr("Editar hábito") : qsTr("Novo hábito")
                    font.pixelSize: 20
                    font.weight: Font.Medium
                }
                ActionButton { glyph: "close"; compact: true; hint: qsTr("Cancelar"); onClicked: dialog.close() }
            }
            UiText {
                Layout.fillWidth: true
                text: qsTr("Uma única definição canônica com UUID próprio. Aparece em todas as páginas do seu escopo, sem duplicar arquivos.")
                color: Theme.secondary
            }
            UiText { text: qsTr("Nome (obrigatório)") }
            Input { id: name; objectName: "habit-name"; Layout.fillWidth: true; placeholderText: qsTr("Ex.: Estudar Python"); onAccepted: save.clicked() }
            UiText { text: qsTr("Tags") }
            Input { id: tags; objectName: "habit-tags"; Layout.fillWidth: true; placeholderText: qsTr("Separadas por vírgula, ex.: estudos, programação") }
            UiText { text: qsTr("Escopo temporal") }
            Flow {
                Layout.fillWidth: true
                spacing: 6
                ActionButton {
                    objectName: "habit-scope-period"
                    visible: dialog.form.mode !== "edit"
                    text: qsTr("Período da página · ") + (dialog.form.periodLabel || "")
                    selected: dialog.scopeMode === "period"
                    onClicked: dialog.scopeMode = "period"
                }
                ActionButton {
                    objectName: "habit-scope-custom"
                    text: qsTr("Personalizar datas")
                    selected: dialog.scopeMode === "custom"
                    onClicked: dialog.scopeMode = "custom"
                }
            }
            UiText {
                Layout.fillWidth: true
                visible: dialog.scopeMode === "period"
                text: qsTr("Padrão sugerido pela página de origem: ") + (dialog.form.start || "") + " → " + (dialog.form.end || "") + qsTr(". A origem não limita o hábito para sempre; você pode alterar depois.")
                color: Theme.secondary
            }
            RowLayout {
                Layout.fillWidth: true
                visible: dialog.scopeMode === "custom"
                Input { id: start; objectName: "habit-start"; Layout.fillWidth: true; placeholderText: qsTr("Início AAAA-MM-DD"); Accessible.name: qsTr("Data inicial do escopo") }
                Input { id: end; objectName: "habit-end"; Layout.fillWidth: true; placeholderText: qsTr("Fim inclusivo (vazio = sem término)"); Accessible.name: qsTr("Data final inclusiva do escopo") }
            }
            UiText { text: qsTr("Recorrência") }
            Flow {
                Layout.fillWidth: true
                spacing: 6
                ActionButton { objectName: "habit-daily"; text: qsTr("Todos os dias"); selected: dialog.recurrence === "daily"; onClicked: dialog.recurrence = "daily" }
                ActionButton { objectName: "habit-weekdays"; text: qsTr("Dias da semana"); selected: dialog.recurrence === "weekdays"; onClicked: dialog.recurrence = "weekdays" }
            }
            Flow {
                Layout.fillWidth: true
                visible: dialog.recurrence === "weekdays"
                spacing: 4
                Repeater {
                    model: [qsTr("Seg"), qsTr("Ter"), qsTr("Qua"), qsTr("Qui"), qsTr("Sex"), qsTr("Sáb"), qsTr("Dom")]
                    delegate: StudioCheckBox {
                        required property string modelData
                        required property int index
                        objectName: "habit-day-" + (index + 1)
                        text: modelData
                        checked: dialog.days.includes(index + 1)
                        onToggled: {
                            dialog.toggleDay(index + 1);
                            checked = Qt.binding(() => dialog.days.includes(index + 1));
                        }
                    }
                }
            }
            StudioCheckBox {
                id: bind
                objectName: "habit-bind"
                visible: !!dialog.form.canBind
                text: qsTr("Adicionar checklist vinculada no Layout Studio desta página")
            }
            UiText {
                objectName: "habit-error"
                Layout.fillWidth: true
                visible: text.length > 0
                text: dialog.form.error || ""
                color: dialog.form.impact ? Theme.warning : Theme.error
                Accessible.role: Accessible.AlertMessage
            }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                ActionButton { text: qsTr("Cancelar"); onClicked: dialog.close() }
                ActionButton {
                    id: save
                    objectName: "habit-save"
                    primary: true
                    text: dialog.form.impact ? qsTr("Confirmar e preservar registros") : dialog.form.mode === "edit" ? qsTr("Salvar alterações") : qsTr("Criar hábito")
                    onClicked: dialog.backend.saveHabit(dialog.values(!!dialog.form.impact))
                }
            }
        }
    }
}
