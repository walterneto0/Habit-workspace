"""Qt editor adapter. Only trusted component mappings reach bundled QML."""

from dataclasses import asdict, replace
from datetime import datetime
from uuid import UUID, uuid4

from PySide6.QtCore import Property, QObject, QRunnable, QThreadPool, Signal, Slot

from habit_workspace.application.layout_draft import LayoutDraft
from habit_workspace.application.layouts import LayoutService, unique_layout
from habit_workspace.application.vault import VaultSession
from habit_workspace.domain.layouts import (
    REGISTRY,
    AssignmentHistory,
    Binding,
    ChartConfig,
    ChecklistConfig,
    Component,
    Grid,
    ImageConfig,
    InputConfig,
    LayoutTemplate,
    NoteConfig,
    SectionConfig,
    TableColumn,
    TableConfig,
    builtin,
    resolve_layout,
)
from habit_workspace.domain.metrics import FieldDefinition, SourceSelection, field_from_mapping
from habit_workspace.vault.layouts import component_mapping, layout_references

BLOCK_LABELS = {
    "checklist": "Hábitos",
    "list": "Lista geral",
    "table": "Tabela",
    "note": "Nota",
    "image": "Imagem",
    "section": "Seção",
    "chart": "Gráfico",
    "integer_input": "Número inteiro",
    "number_input": "Número decimal",
    "duration_input": "Duração",
    "text_input": "Texto",
    "boolean_input": "Sim/Não",
    "date_input": "Data",
    "time_input": "Horário",
    "selection_input": "Escolha única",
    "rating_input": "Avaliação",
}

BUILTIN_NOTE_IDS = {builtin(scale).blocks[0].id for scale in ("year", "month", "week", "day")}


def block_title(block):
    """Localize built-in copy without changing user-written titles or files."""
    return "Notas" if block.title == "Notes" and block.id in BUILTIN_NOTE_IDS else block.title


class JobSignals(QObject):
    done = Signal(str)


class SaveJob(QRunnable):
    def __init__(self, root, period, layout, instant, fields, report, original):
        super().__init__()
        self.signals = JobSignals()
        self.args = root, period, layout, instant, fields, report, original

    def run(self):
        root, period, layout, instant, fields, report, original = self.args
        try:
            session = VaultSession.open(root)
            LayoutService(session).save_revision(
                period,
                layout,
                instant,
                new_fields=fields,
                expected_report=report,
                original_layout=original,
            )
            self.signals.done.emit("Salvo. " + (session.index_error or ""))
        except Exception as error:
            self.signals.done.emit(
                "Falha ao publicar. Arquivos intermediários são preservados; "
                "tente novamente ou reabra para comparar. " + str(error)
            )


def composition(layout, report, root=None, draft_fields=None, capture=None):
    """capture: optional CaptureSnapshot that adds tracking-mode values per block."""
    rows = []
    draft_fields = draft_fields or {}
    documents = {str(d.document.id): d.document for d in report.documents}
    for block, position in zip(layout.blocks, layout.positions(), strict=True):
        row = component_mapping(block)
        row["typeLabel"] = BLOCK_LABELS.get(block.type, block.type)
        row["title"] = block_title(block)
        row.update(row=position.row, column=position.column, detail="", bindingLabel="")
        if capture is not None:
            from habit_workspace.presentation.tracking import cell_mapping

            row["capture"] = [
                cell_mapping(c) | {"date": capture.day.isoformat()} for c in capture.block(block)
            ]
        if block.binding:
            doc = documents.get(str(block.binding.source_id))
            row["bindingLabel"] = (
                doc.title if doc else "Referência ausente: " + str(block.binding.source_id)
            )
            if block.type == "note" and doc:
                row["detail"] = doc.body[:6000]
            field = draft_fields.get(block.binding.source_id)
            if field:
                row["bindingLabel"] = field.name + " · novo campo (rascunho)"
            elif doc and doc.kind == "metric_definition":
                field = field_from_mapping(doc.metadata["hw"])
            if field:
                row["options"] = list(field.options)
                if field.minimum is not None:
                    row["minimum"] = field.minimum
                if field.maximum is not None:
                    row["maximum"] = field.maximum
        selection = getattr(block.config, "selection", None)
        if selection:
            row["detail"] = (
                "Seleção fixa: "
                + ", ".join(
                    documents[str(i)].title if str(i) in documents else "Referência ausente"
                    for i in selection.source_ids
                )
                if selection.mode == "manual"
                else "Hábitos da data de acompanhamento"
                if selection.mode == "all"
                else "Tags dinâmicas (qualquer): " + ", ".join(selection.tags)
            )
        if block.type == "table":
            row["detail"] = " | ".join(
                c.label + " · " + BLOCK_LABELS[c.value_type + "_input"]
                for c in block.config.columns
            )
        references = []
        if selection and selection.mode == "manual":
            references.extend(selection.source_ids)
        if block.type == "table":
            references.extend(c.field_id for c in block.config.columns)
        missing = [str(i) for i in references if str(i) not in documents and i not in draft_fields]
        if missing:
            row["detail"] += "\nReferências ausentes: " + ", ".join(dict.fromkeys(missing))
        if block.type == "image" and root:
            from habit_workspace.presentation.layout_assets import image_source

            try:
                row["imageSource"] = image_source(root, block.config.path)
            except (ValueError, OSError) as error:
                row["detail"] = "Imagem indisponível: " + str(error)
        if block.type == "section":
            nested = LayoutTemplate(
                uuid4(), 1, "Seção", block.config.children, grid=Grid(block.config.columns)
            )
            row["children"] = composition(nested, report, root, draft_fields, capture)
        rows.append(row)
    return rows


class LayoutStudio(QObject):
    changed = Signal()

    def __init__(self, workspace):
        super().__init__(workspace)
        self.workspace = workspace
        self.draft = None
        self.selected = -1
        self.preview = False
        self.message = ""
        self.fields = {}
        self.instant = None
        self.busy = False
        self.job = None

    @Property("QVariantMap", notify=changed)
    def state(self):
        if not self.draft:
            return {"active": False, "dirty": False, "busy": False}
        layout = self.draft.layout
        view = layout if self.preview else self.draft.view
        blocks = composition(view, self.report, self.workspace.session.root, self.fields)
        old = {b.id: b for b in self.draft.original.walk()}
        new = {b.id: b for b in layout.walk()}
        refs = {r.target_id for r in layout_references(layout)}
        fields = [f.name for key, f in self.fields.items() if key in refs]
        current = blocks[self.selected] if 0 <= self.selected < len(blocks) else {}
        source_id = current.get("binding", {}).get("source_id")
        field = self.source_field(source_id) if source_id else None
        added = [block_title(b) for b in layout.walk() if b.id not in old]
        removed = [block_title(b) for b in self.draft.original.walk() if b.id not in new]
        modified = [block_title(b) for b in layout.walk() if b.id in old and b != old[b.id]]
        reordered = [k for k in new if k in old] != [k for k in old if k in new]
        activation = (
            self.instant.strftime("%d/%m/%Y às %H:%M:%S %z")
            if self.instant
            else "revisar salvamento"
        )
        period_label = self.workspace.navigation.title
        if self.period.scale == "week":
            period_label += f" · {self.period.start:%d/%m} a {self.period.end:%d/%m}"
        return dict(
            field=asdict(field)
            | {
                "id": str(field.id),
                "active_from": field.active_from.isoformat(),
                "options": list(field.options),
                "tags": list(field.tags),
            }
            if field
            else {},
            active=True,
            dirty=self.draft.dirty,
            busy=self.busy,
            preview=self.preview,
            blocks=blocks,
            columns=view.grid.columns,
            nested=bool(self.draft.scope),
            selected=self.selected,
            current=blocks[self.selected] if 0 <= self.selected < len(blocks) else {},
            undo=bool(self.draft.past),
            redo=bool(self.draft.future),
            period=str(self.period),
            periodLabel=period_label,
            templates=[
                {
                    "key": f"{d.layout.id}:{d.layout.version}",
                    "name": f"{d.layout.name} · versão {d.layout.version}",
                }
                for d in self.report.layouts
            ],
            message=self.message,
            palette=list(REGISTRY.kinds),
            habitTags=sorted(
                {
                    tag
                    for loaded in self.report.documents
                    if loaded.document.kind == "habit"
                    for tag in loaded.document.metadata["hw"].get("tags", ())
                }
            ),
            sources=[
                dict(
                    id=str(d.document.id),
                    name=d.document.title,
                    kind=d.document.kind,
                    type=d.document.metadata["hw"].get("value_type", ""),
                )
                for d in self.report.documents
                if d.document.kind in ("metric_definition", "habit", "note")
            ]
            + [
                dict(
                    id=str(f.id),
                    name=f.name + " · rascunho",
                    kind="metric_definition",
                    type=f.value_type,
                )
                for f in self.fields.values()
            ],
            summary=f"Somente este período: {period_label}.\n\n"
            f"Adicionados: {', '.join(added) or 'nenhum'}.\n"
            f"Removidos: {', '.join(removed) or 'nenhum'}.\n"
            f"Modificados: {', '.join(modified) or 'nenhum'}.\n"
            + (
                "Ordem alterada: " + ", ".join(block_title(b) for b in layout.blocks) + ".\n"
                if reordered
                else ""
            )
            + (
                f"Colunas: {layout.grid.columns}.\n"
                if layout.grid != self.draft.original.grid
                else ""
            )
            + f"Novos campos: {', '.join(fields) or 'nenhum'}.\n\n"
            f"Ativo a partir de: {activation}.\n"
            "Os registros históricos serão preservados. "
            "Modelos e outros períodos não serão alterados. "
            "Novos campos ficam disponíveis a partir da ativação; "
            "seleções manuais permanecem fixas.",
        )

    @Slot(str)
    def startFrom(self, key):
        """Replace only the draft composition; publication keeps its existing assignment path."""
        if not self.draft or self.busy or self.preview:
            return
        try:
            layout = self.draft.original
            if key == "empty":
                layout = replace(layout, blocks=(), grid=Grid())
            elif key == "default":
                defaults = self.report.defaults
                history = (
                    defaults[0].history(self.period.scale) if defaults else AssignmentHistory()
                )
                active = history.at(datetime.now().astimezone())
                if active:
                    unique_layout(self.report, active.layout_id, active.version)
                result = resolve_layout(
                    self.period,
                    datetime.now().astimezone(),
                    AssignmentHistory(),
                    history,
                    tuple(d.layout for d in self.report.layouts),
                )
                if result.issues:
                    raise ValueError(
                        "O modelo padrão está indisponível. "
                        "Reabra o Studio após resolver as pendências."
                    )
                layout = result.layout
            elif key != "current":
                identifier, version = key.split(":")
                loaded = unique_layout(self.report, UUID(identifier), int(version))
                if loaded is None:
                    raise ValueError(
                        "Modelo não encontrado. Reabra o Studio para atualizar a lista."
                    )
                layout = loaded.layout
            self.draft.scope.clear()
            self.draft.apply(replace(self.draft.layout, blocks=layout.blocks, grid=layout.grid))
            self.selected = -1
            self.instant = None
            self.message = ""
        except ValueError as error:
            self.message = "Não foi possível usar este modelo. " + str(error)
        self.changed.emit()

    @Slot()
    def open(self):
        if self.draft or not self.workspace.session or not self.workspace.navigation.period:
            return
        try:
            self.report = self.workspace.session.report
            self.period = self.workspace.navigation.period_ref
            result = LayoutService.resolve_report(
                self.report, self.period, datetime.now().astimezone()
            )
            self.original = (
                unique_layout(self.report, result.layout.id, result.layout.version)
                if result.origin != "builtin"
                else None
            )
            self.resolution = result
            self.draft = LayoutDraft(result.layout)
            self.fields = {}
            self.instant = None
            self.target = None
            self.selected = -1
            self.message = "\n".join(result.issues)
            self.changed.emit()
        except (ValueError, OSError) as error:
            self.workspace._notice_message("Não foi possível abrir o Studio. " + str(error), True)

    @Slot()
    def discard(self):
        if not self.busy:
            self.draft = None
            self.preview = False
            self.changed.emit()

    @Slot(int)
    def select(self, index):
        self.selected = index
        self.changed.emit()

    def source_field(self, source_id):
        if not source_id:
            return None
        if UUID(source_id) in self.fields:
            return self.fields[UUID(source_id)]
        doc = next(
            (d.document for d in self.report.documents if str(d.document.id) == source_id), None
        )
        return (
            field_from_mapping(doc.metadata["hw"])
            if doc and doc.kind == "metric_definition"
            else None
        )

    def source_info(self, source_id):
        field = self.source_field(source_id)
        if field:
            return field.id, field.name, "metric", field.value_type
        doc = next(d.document for d in self.report.documents if str(d.document.id) == source_id)
        return doc.id, doc.title, doc.kind, "habit" if doc.kind == "habit" else "text"

    @Slot(str, str, str, str)
    def add(self, kind, source_id="", name="", tags=""):
        self.addConfigured(kind, source_id, name, tags, {})

    @Slot(str, str, str, str, "QVariantMap")
    def addConfigured(self, kind, source_id, name, tags, options):
        if not self.draft or self.busy or self.preview:
            return
        try:
            definition = REGISTRY.get(kind)
            binding = None
            field = None
            if kind.endswith("_input") or (kind == "checklist" and name.strip() and not source_id):
                value_type = kind.removesuffix("_input") if kind.endswith("_input") else "boolean"
                if source_id:
                    binding = Binding(UUID(source_id), "metric")
                    _, _, source_kind, actual = self.source_info(source_id)
                    if source_kind != "metric" or (
                        actual != value_type
                        and not (value_type == "number" and actual == "integer")
                    ):
                        raise ValueError("Escolha uma métrica de tipo compatível.")
                elif name.strip():
                    field = FieldDefinition(
                        uuid4(),
                        name,
                        value_type,
                        datetime.now().astimezone(),
                        tags=tuple(t.strip() for t in tags.split(",") if t.strip()),
                        unit=options.get("unit") or None,
                        minimum=float(options["minimum"]) if options.get("minimum") else None,
                        maximum=float(options["maximum"]) if options.get("maximum") else None,
                        options=tuple(
                            v.strip() for v in options.get("options", "").splitlines() if v.strip()
                        ),
                        aggregation=options.get("aggregation", "none"),
                        temporal_policy=options.get("temporal_policy", "daily"),
                        weekly_attribution=options.get("weekly_attribution", "separate"),
                    )
                    binding = Binding(field.id, "metric")
                else:
                    raise ValueError(
                        "Escolha uma fonte existente ou informe o nome de um novo campo."
                    )
                config = (
                    InputConfig(value_type) if kind.endswith("_input") else definition.config_type()
                )
            elif kind == "checklist":
                config = ChecklistConfig(SourceSelection("manual", value_types=("habit",)))
            elif kind == "chart":
                config = ChartConfig(SourceSelection("manual"))
            elif kind == "image":
                config = ImageConfig("Assets/placeholder.png")
            else:
                config = definition.config_type()
            if source_id and kind in ("checklist", "list", "note"):
                _, _, source_kind, actual = self.source_info(source_id)
                if source_kind not in definition.bindings:
                    raise ValueError("Fonte incompatível com este componente.")
                if kind == "checklist" and source_kind == "metric" and actual != "boolean":
                    raise ValueError("Checklist exige campo booleano ou hábito.")
                binding = Binding(UUID(source_id), source_kind)
                if kind == "checklist":
                    config = ChecklistConfig()
            block = Component(
                uuid4(),
                kind,
                name or (self.source_info(source_id)[1] if source_id else BLOCK_LABELS[kind]),
                config,
                binding=binding,
            )
            self.draft.apply_view(self.draft.view.insert(len(self.draft.view.blocks), block))
            if field:
                self.fields[field.id] = field
            self.selected = len(self.draft.view.blocks) - 1
            self.instant = None
            self.message = ""
        except (ValueError, StopIteration) as error:
            self.message = "Não foi possível adicionar. " + str(error)
        self.changed.emit()

    @Slot(int, int)
    def move(self, source, target):
        if not self.draft or self.preview or self.busy:
            return
        try:
            if not 0 <= source < len(self.draft.view.blocks):
                raise ValueError("Componente inexistente")
            block = self.draft.view.blocks[source]
            self.draft.apply_view(self.draft.view.move(block.id, target))
            self.selected = target
            self.instant = None
        except (IndexError, ValueError) as error:
            self.message = "Destino inválido: " + str(error)
        self.changed.emit()

    @Slot(str)
    def command(self, action):
        if not self.draft or self.busy:
            return
        try:
            if action == "preview":
                self.preview = not self.preview
            elif not self.preview:
                if action == "back" and self.draft.scope:
                    identifier = self.draft.scope.pop()
                    self.selected = next(
                        i for i, b in enumerate(self.draft.view.blocks) if b.id == identifier
                    )
                elif action == "enter" and 0 <= self.selected < len(self.draft.view.blocks):
                    block = self.draft.view.blocks[self.selected]
                    if isinstance(block.config, SectionConfig):
                        self.draft.scope.append(block.id)
                        self.selected = -1
                elif action in ("undo", "redo"):
                    getattr(self.draft, action)()
                elif action == "columns":
                    columns = 3 - self.draft.view.grid.columns
                    from habit_workspace.domain.layouts import Placement

                    blocks = tuple(
                        replace(b, placement=Placement(min(b.placement.width, columns)))
                        for b in self.draft.view.blocks
                    )
                    self.draft.apply_view(
                        replace(self.draft.view, grid=Grid(columns), blocks=blocks)
                    )
                elif 0 <= self.selected < len(self.draft.view.blocks):
                    block = self.draft.view.blocks[self.selected]
                    if action == "remove":
                        self.draft.apply_view(self.draft.view.remove(block.id))
                        self.selected = min(self.selected, len(self.draft.view.blocks) - 1)
                    elif action == "duplicate":
                        self.draft.duplicate(block.id)
                    elif action == "width":
                        self.draft.resize(
                            block.id, min(3 - block.placement.width, self.draft.view.grid.columns)
                        )
                    elif action in ("up", "down"):
                        index = self.selected + (-1 if action == "up" else 1)
                        if 0 <= index < len(self.draft.view.blocks):
                            self.draft.apply_view(self.draft.view.move(block.id, index))
                            self.selected = index
                self.instant = None
            self.message = ""
        except ValueError as error:
            self.message = "Operação inválida: " + str(error)
        self.changed.emit()

    @Slot(str, str)
    def edit(self, key, value):
        if (
            not self.draft
            or self.busy
            or self.preview
            or not 0 <= self.selected < len(self.draft.view.blocks)
        ):
            return
        try:
            block = self.draft.view.blocks[self.selected]
            if key == "title":
                self.draft.update(block.id, title=value)
            elif isinstance(block.config, ChecklistConfig) and key in (
                "source",
                "remove_source",
                "source_up",
                "source_down",
                "selection_mode",
                "tags",
            ):
                self._edit_checklist(block, key, value)
            elif key in ("placeholder", "required") and isinstance(block.config, InputConfig):
                self.draft.update(
                    block.id,
                    config=replace(
                        block.config, **{key: value == "true" if key == "required" else value}
                    ),
                )
            elif key == "tags" and isinstance(block.config, ChartConfig):
                self.draft.update(
                    block.id,
                    config=replace(
                        block.config,
                        selection=SourceSelection(
                            "by_tags",
                            tags=tuple(t.strip() for t in value.split(",") if t.strip()),
                            value_types=block.config.selection.value_types,
                        ),
                    ),
                )
            elif key == "source":
                source_id, name, kind, actual = self.source_info(value)
                if isinstance(block.config, ChartConfig):
                    if kind not in ("metric", "habit"):
                        raise ValueError("Gráficos exigem uma métrica ou hábito.")
                    selection = block.config.selection
                    ids = selection.source_ids if selection.mode == "manual" else ()
                    self.draft.update(
                        block.id,
                        config=replace(
                            block.config,
                            selection=SourceSelection(
                                "manual",
                                tuple(dict.fromkeys((*ids, source_id))),
                                value_types=selection.value_types,
                            ),
                        ),
                    )
                elif isinstance(block.config, TableConfig):
                    if kind != "metric":
                        raise ValueError("Colunas exigem uma métrica tipada.")
                    column = TableColumn(uuid4(), name, actual, source_id)
                    self.draft.update(block.id, config=TableConfig((*block.config.columns, column)))
                else:
                    candidate = replace(block, binding=Binding(source_id, kind))
                    if isinstance(block.config, InputConfig):
                        accepted = {block.config.value_type}
                        if block.config.value_type == "number":
                            accepted.add("integer")
                        if actual not in accepted:
                            raise ValueError("Tipo de fonte incompatível.")
                    if block.type == "checklist" and kind == "metric" and actual != "boolean":
                        raise ValueError("Checklist exige campo booleano.")
                    self.draft.update(block.id, binding=candidate.binding)
            elif key == "clear_sources" and isinstance(block.config, ChartConfig):
                self.draft.update(
                    block.id,
                    config=replace(
                        block.config,
                        selection=SourceSelection(
                            "manual", value_types=block.config.selection.value_types
                        ),
                    ),
                )
            elif key in ("types", "remove_source") and isinstance(block.config, ChartConfig):
                selection = block.config.selection
                selection = replace(
                    selection,
                    **(
                        {"value_types": tuple(t.strip() for t in value.split(",") if t.strip())}
                        if key == "types"
                        else {
                            "source_ids": tuple(i for i in selection.source_ids if str(i) != value)
                        }
                    ),
                )
                self.draft.update(block.id, config=replace(block.config, selection=selection))
            elif key in ("aggregation", "visualization", "period") and isinstance(
                block.config, ChartConfig
            ):
                from habit_workspace.domain.temporal import PeriodRef

                changes = {key: value}
                if key == "period":
                    changes = dict(
                        period=PeriodRef(value) if value else None, follow_page_period=not value
                    )
                self.draft.update(block.id, config=replace(block.config, **changes))
            elif key == "child" and isinstance(block.config, SectionConfig):
                child = Component(uuid4(), "note", "Nota da seção", NoteConfig())
                self.draft.update(
                    block.id, config=replace(block.config, children=(*block.config.children, child))
                )
            elif key in ("path", "alt", "fit") and isinstance(block.config, ImageConfig):
                self.draft.update(block.id, config=replace(block.config, **{key: value}))
            self.instant = None
            self.message = ""
        except (ValueError, StopIteration, KeyError) as error:
            self.message = "Propriedade inválida: " + str(error)
        self.changed.emit()

    def _edit_checklist(self, block, key, value):
        selection = block.config.selection
        if selection is None:
            selection = SourceSelection(
                "manual",
                (block.binding.source_id,) if block.binding else (),
                value_types=("habit", "boolean")
                if block.binding and block.binding.kind == "metric"
                else ("habit",),
            )
        if key == "source":
            identifier, _, kind, actual = self.source_info(value)
            if kind != "habit" and not (kind == "metric" and actual == "boolean"):
                raise ValueError("Checklist exige hábitos ou campos booleanos.")
            ids = selection.source_ids if selection.mode == "manual" else ()
            types = tuple(dict.fromkeys((*selection.value_types, actual)))
            selection = SourceSelection(
                "manual", tuple(dict.fromkeys((*ids, identifier))), value_types=types
            )
        elif key == "tags":
            selection = SourceSelection(
                "by_tags", tags=tuple(value.split(",")), value_types=("habit",)
            )
        elif key == "selection_mode":
            if value not in ("manual", "all"):
                raise ValueError("Selecione as tags antes de aplicar o modo dinâmico.")
            selection = SourceSelection(
                value,
                selection.source_ids if value == "manual" else (),
                value_types=selection.value_types if value == "manual" else ("habit",),
            )
        elif key == "remove_source":
            selection = replace(
                selection, source_ids=tuple(i for i in selection.source_ids if str(i) != value)
            )
        else:
            ids = list(selection.source_ids)
            index = ids.index(UUID(value))
            target = index + (-1 if key == "source_up" else 1)
            if 0 <= target < len(ids):
                ids.insert(target, ids.pop(index))
            selection = replace(selection, source_ids=tuple(ids))
        self.draft.update(block.id, binding=None, config=ChecklistConfig(selection))

    @Slot(int, str, str)
    def columnEdit(self, index, action, value):
        if not self.draft or self.busy or self.preview:
            return
        try:
            block = self.draft.view.blocks[self.selected]
            columns = list(block.config.columns)
            column = columns[index]
            if action == "label":
                columns[index] = replace(column, label=value)
            elif action == "source":
                identifier, _, kind, value_type = self.source_info(value)
                if kind != "metric":
                    raise ValueError("Colunas exigem uma métrica tipada.")
                columns[index] = replace(column, field_id=identifier, value_type=value_type)
            elif action == "remove":
                columns.pop(index)
            elif action in ("up", "down"):
                target = index + (-1 if action == "up" else 1)
                if 0 <= target < len(columns):
                    columns.insert(target, columns.pop(index))
            self.draft.update(block.id, config=TableConfig(tuple(columns)))
            self.instant = None
            self.message = ""
        except (ValueError, IndexError, AttributeError, StopIteration) as error:
            self.message = "Coluna inválida: " + str(error)
        self.changed.emit()

    @Slot()
    def prepare(self):
        if self.draft and not self.busy:
            if self.instant is None:
                self.instant = datetime.now().astimezone()
            self.changed.emit()

    @Slot()
    def save(self):
        if not self.draft or self.busy or self.instant is None:
            return
        layout = self.draft.layout
        if self.resolution.origin == "explicit":
            layout = replace(
                layout,
                version=1
                + max(d.layout.version for d in self.report.layouts if d.layout.id == layout.id),
            )
        else:
            if self.target is None:
                self.target = uuid4()
            layout = replace(layout, id=self.target, version=1)
        refs = {r.target_id for r in layout_references(layout)}
        fields = tuple(
            replace(f, active_from=self.instant) for key, f in self.fields.items() if key in refs
        )
        self.busy = True
        self.job = SaveJob(
            self.workspace.session.root,
            self.period,
            layout,
            self.instant,
            fields,
            self.report,
            self.original,
        )
        self.job.signals.done.connect(self._saved)
        QThreadPool.globalInstance().start(self.job)
        self.changed.emit()

    @Slot(str)
    def _saved(self, message):
        self.busy = False
        if message.startswith("Salvo."):
            self.discard()
            self.workspace.reindex()
            self.workspace._notice_message(message)
        else:
            self.message = message
        self.changed.emit()
