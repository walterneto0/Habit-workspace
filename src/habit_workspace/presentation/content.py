"""Draft-preserving forms for canonical notes, regions and goal follow-ups."""

from PySide6.QtCore import QObject, Slot

from habit_workspace.application.content import regions
from habit_workspace.application.layouts import period_page
from habit_workspace.domain.temporal import PeriodRef


class ContentActions(QObject):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.workspace = workspace
        self.form, self.loaded = {}, None
        self.image_target = None

    def _open(self, loaded=None, region="", followup="", kind="note"):
        w = self.workspace
        if w.actions.busy or w._guard_studio():
            return
        self.loaded = loaded
        doc = loaded.document if loaded else None
        body, error = doc.body if doc else "", ""
        if region:
            try:
                body = regions(body)[region][2]
            except (ValueError, KeyError) as caught:
                error = "Região indisponível; original somente para leitura. " + str(caught)
        if followup:
            body = next(
                (
                    r["commentary"]
                    for r in doc.metadata["hw"].get("followups", [])
                    if r["period"] == followup
                ),
                "",
            )
        self.form = dict(
            kind=doc.kind.value if doc else kind,
            rating=str(doc.metadata["hw"].get("assessment", {}).get("rating") or "") if doc else "",
            imageRevision=0,
            images=[],
            open=True,
            title=doc.title if doc else "",
            body=body,
            period=doc.metadata["hw"].get("period", "") if doc else w.navigation.period or "",
            region=region,
            followup=followup,
            error=error,
            readonly=bool(error),
        )
        w._publish()

    @Slot()
    def create(self):
        if self.workspace.session:
            self._open()

    @Slot()
    def createReview(self):
        if self.workspace.session:
            self._open(kind="review")

    def _find(self, identifier):
        w = self.workspace
        matches = [d for d in w.session.report.documents if str(d.document.id) == identifier]
        if len(matches) != 1 or any(
            str(c.document_id) == identifier for c in w.session.report.conflicts
        ):
            raise ValueError("Referência ausente ou UUID ambíguo.")
        return matches[0]

    @Slot(str)
    def goPeriod(self, value):
        try:
            period = PeriodRef(value)
            self.workspace.navigate(period.scale.value, period.start.isoformat())
        except ValueError as error:
            self.workspace._notice_message(str(error), True)

    @Slot(str)
    def edit(self, identifier):
        try:
            loaded = self._find(identifier)
            if loaded.document.kind in ("note", "review"):
                self._open(loaded)
        except ValueError as error:
            self.workspace._notice_message(str(error), True)

    @Slot(str, str)
    def followup(self, identifier, period):
        try:
            self._open(self._find(identifier), followup=str(PeriodRef(period)))
        except ValueError as error:
            self.workspace._notice_message(str(error), True)

    @Slot(str, str)
    def region(self, identifier, linked):
        try:
            if linked:
                self.edit(linked)
                return
            w = self.workspace
            page = period_page(w.session.report, w.navigation.period_ref)
            if page is None:
                raise ValueError(
                    "Página ou região ausente; crie os marcadores no arquivo antes de editar."
                )
            self._open(self._find(str(page.document.id)), region=identifier)
        except ValueError as error:
            self.workspace._notice_message(str(error), True)

    @Slot()
    def cancel(self):
        if not self.workspace.actions.busy:
            self.form, self.loaded = {}, None
            self.workspace._publish()

    @Slot("QVariantMap")
    def save(self, values):
        w = self.workspace
        if not self.form or self.form.get("readonly") or w.actions.busy:
            return
        self.form = self.form | dict(values)
        if (
            not self.form.get("region")
            and not self.form.get("followup")
            and (
                self.form.get("periodValid") is False
                or (self.form.get("kind") == "review" and not self.form.get("period"))
            )
        ):
            self.form["error"] = "Escolha um período exato válido; rascunho preservado."
            w._publish()
            return
        if w.actions.tasks.capture(
            "content_save", dict(loaded=self.loaded, values=dict(self.form))
        ):
            w._notice_message("Salvando…")

    @Slot(str)
    def previewImages(self, body):
        w = self.workspace
        if self.form and not w.actions.busy:
            w.actions.tasks.capture("content_media", dict(body=body))
            w._publish()

    @Slot(str, str, "QVariantMap")
    def importImage(self, source, alt, values):
        w = self.workspace
        if not self.form or w.actions.busy or self.form.get("readonly"):
            return
        self.form = self.form | dict(values)
        self.image_target = ("content", alt)
        self._import(source)

    def import_for_layout(self, source):
        w = self.workspace
        studio = w.studio
        if not studio.draft or studio.busy or w.actions.busy or studio.preview:
            return
        if not 0 <= studio.selected < len(studio.draft.view.blocks):
            return
        block = studio.draft.view.blocks[studio.selected]
        if block.type != "image":
            return
        self.image_target = ("layout", studio.draft, block.id)
        studio.busy = True
        studio.changed.emit()
        self._import(source)

    def _import(self, source):
        from habit_workspace.presentation.controllers import local_path

        try:
            path = local_path(source)
            if self.workspace.actions.tasks.capture("image_import", dict(source=path)):
                self.workspace._publish()
        except (ValueError, OSError) as error:
            self.media_completed("image_import", None, error)

    def media_completed(self, kind, result, error):
        w = self.workspace
        if kind == "content_media":
            if self.form:
                self.form["images"] = result or []
                if error:
                    self.form["error"] = str(error)
        else:
            target, self.image_target = self.image_target, None
            if target and target[0] == "layout":
                from dataclasses import replace

                studio = w.studio
                studio.busy = False
                if not error and studio.draft is target[1]:
                    block = next((b for b in studio.draft.view.blocks if b.id == target[2]), None)
                    if block:
                        studio.draft.update(block.id, config=replace(block.config, path=result))
                        studio.instant = None
                studio.message = (
                    "Imagem não importada: " + str(error)
                    if error
                    else "Imagem importada. Revise a descrição e salve o layout."
                )
                studio.changed.emit()
            elif target and self.form:
                if error:
                    self.form["error"] = "Imagem não importada; rascunho preservado. " + str(error)
                else:
                    from habit_workspace.presentation.layout_assets import image_markdown

                    self.form["body"] += "\n" + image_markdown(result, target[1]) + "\n"
                    self.form["imageRevision"] += 1
                    w.actions.tasks.capture("content_media", dict(body=self.form["body"]))
        w._publish()

    def completed(self, error):
        if error:
            self.form["error"] = "Não salvo; rascunho preservado. " + str(error)
        else:
            self.form, self.loaded = {}, None
        self.workspace._notice_message(
            "Não salvo; rascunho preservado." if error else "Salvo.", bool(error)
        )
