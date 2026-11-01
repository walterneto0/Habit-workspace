"""Canonical Markdown editing with structurally checked region boundaries."""

import re
from copy import deepcopy
from uuid import UUID, uuid4

from habit_workspace.domain.documents import Document, require
from habit_workspace.domain.temporal import PeriodRef

OPEN = re.compile(r'<!-- hw:content id="([0-9a-fA-F-]{36})" -->')
TOKEN = re.compile(r"<!--\s*/?hw:content")


def regions(body):
    result, active = {}, None
    for match in TOKEN.finditer(body):
        offset = match.start()
        opening = OPEN.match(body, offset)
        if opening:
            require(active is None, "Marcadores aninhados.")
            key = str(UUID(opening[1]))
            require(key not in result, "Identidade de região duplicada.")
            active = (key, opening.end())
        else:
            require(body.startswith("<!-- /hw:content -->", offset), "Marcador inválido.")
            require(active is not None, "Fechamento sem abertura.")
            key, start = active
            result[key] = (start, offset, body[start:offset])
            active = None
    require(active is None, "Região sem fechamento.")
    return result


def replace_region(body, identifier, text):
    found = regions(body)
    require(identifier in found, "Região ausente; conteúdo preservado.")
    start, end, _ = found[identifier]
    candidate = body[:start] + text + body[end:]
    require(set(regions(candidate)) == set(found), "O texto não pode alterar marcadores.")
    return candidate


class ContentService:
    def __init__(self, session):
        self.session = session

    def create(self, title, body, period="", *, kind="note", rating=None):
        require(bool(title.strip()), "Informe um título.")
        require(kind in ("note", "review"), "Expected note or review")
        hw = dict(schema_version=4, kind=kind, id=str(uuid4()), title=title)
        if period:
            hw["period"] = str(PeriodRef(period))
        if kind == "review":
            hw["assessment"] = {"rating": rating}
        doc = Document.from_metadata({"hw": hw}, body)
        folder = "Reviews" if kind == "review" else "Notes"
        return self.session.create_document(f"{folder}/{doc.id}.md", doc)

    def save(self, loaded, title, body, period="", region="", *, rating=None):
        doc = deepcopy(loaded.document)
        body = body.replace("\r\n", "\n").replace("\n", doc.newline)
        if region:
            doc.body = replace_region(doc.body, region, body)
        else:
            require(doc.kind in ("note", "review"), "Esperada nota ou avaliação.")
            require(bool(title.strip()), "Informe um título.")
            doc.metadata["hw"]["title"] = title
            if period:
                doc.metadata["hw"]["period"] = str(PeriodRef(period))
            else:
                doc.metadata["hw"].pop("period", None)
            if doc.kind == "review":
                doc.metadata["hw"].setdefault("assessment", {})["rating"] = rating
            doc.body = body
        return self.session.save(loaded, doc)
