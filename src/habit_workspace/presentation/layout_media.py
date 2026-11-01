"""GUI-side media requests; decoding uses the existing serialized vault worker."""

from habit_workspace.domain.documents import DocumentError
from habit_workspace.presentation.layout_assets import (
    _CACHE_BYTES,
    cached_source,
    image_revision,
)


class LayoutMedia:
    def __init__(self, workspace, context="page", notify=None):
        self.workspace = workspace
        self.context, self.notify = context, notify or workspace._publish
        self.results = {}
        self.signature = None
        self.generation = 0
        self.begin()

    def reset(self):
        self.results.clear()
        self.signature = None
        self.generation += 1

    def begin(self):
        self.wanted, self.pending, self.total = set(), {}, 0

    def source(self, path):
        key = image_revision(self.workspace.session.root, path)
        self.wanted.add(key)
        source, error = self.results.get(key, (None, ""))
        if error:
            raise DocumentError(error)
        if source is None:
            source = cached_source(key)
        if source is None:
            self.pending[path] = key
            return ""
        if self.total + len(source) > _CACHE_BYTES:
            raise DocumentError("Limite de prévia de imagens atingido (64 MiB).")
        self.total += len(source)
        return source

    def finish(self):
        self.results = {k: v for k, v in self.results.items() if k in self.wanted}
        signature = tuple(sorted(self.pending.items()))
        if signature != self.signature:
            self.signature = signature
            self.generation += 1
            if signature:
                self.workspace.actions.tasks.media(
                    dict(
                        context=self.context, generation=self.generation, paths=tuple(self.pending)
                    )
                )

    def completed(self, result):
        _, generation, rows = result
        if generation != self.generation:
            return
        # Keep only the current display's bounded results; never store Qt objects.
        total = sum(len(source or "") for source, _ in self.results.values())
        for _, key, source, error in rows:
            if key not in self.wanted:
                continue
            total += len(source)
            if total > _CACHE_BYTES:
                source, error = "", "Limite de prévia de imagens atingido (64 MiB)."
            self.results[key] = source, error
        self.signature = None
        self.notify()
