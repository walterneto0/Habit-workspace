"""Revision-aware event operations, submitted through the serialized vault worker."""

from copy import deepcopy
from uuid import uuid4

from habit_workspace.domain.documents import Document, require
from habit_workspace.domain.events import event_from_mapping
from habit_workspace.domain.habits import normalize_tags


class EventService:
    def __init__(self, session):
        self.session = session

    def create(self, *, title, timing, body="", tags=(), origin_page_id=None):
        hw = dict(
            schema_version=4,
            kind="event",
            id=str(uuid4()),
            title=title,
            timing=deepcopy(timing),
            tags=list(normalize_tags(tags)),
        )
        if origin_page_id:
            hw["origin_page_id"] = str(origin_page_id)
        doc = Document.from_metadata({"hw": hw}, body)
        return self.session.create_document(f"Items/Events/{doc.id}.md", doc)

    def update(self, loaded, *, title, timing, body, tags=()):
        event_from_mapping(loaded.document.metadata["hw"])
        doc = deepcopy(loaded.document)
        old = doc.metadata["hw"]["timing"]
        extensions = {
            k: v
            for k, v in old.items()
            if k
            not in {"kind", "timezone", "starts_at", "ends_at", "start_date", "end_date_exclusive"}
        }
        doc.metadata["hw"].update(
            title=title, timing=extensions | deepcopy(timing), tags=list(normalize_tags(tags))
        )
        doc.body = body
        return self.session.save(loaded, doc)

    def open(self, identifier):
        loaded = self.session.load(identifier)
        require(loaded.document.kind == "event", "Expected event")
        return loaded

    def search(self, query=""):
        return tuple(
            d
            for d in self.session.scan().documents
            if d.document.kind == "event"
            and query.casefold()
            in " ".join(
                (d.document.title, d.document.body, *d.document.metadata["hw"].get("tags", []))
            ).casefold()
        )
