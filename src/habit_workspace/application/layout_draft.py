"""Isolated immutable editor snapshots; no filesystem or Qt dependencies."""

from dataclasses import replace
from uuid import UUID, uuid4

from habit_workspace.domain.layouts import LayoutTemplate, Placement, SectionConfig
from habit_workspace.domain.layouts.components import flow


class LayoutDraft:
    def __init__(self, layout: LayoutTemplate):
        self.original = self.layout = layout
        self.past = []
        self.future = []
        self.scope = []

    @property
    def view(self):
        layout = self.layout
        valid = []
        for identifier in self.scope:
            block = next((b for b in layout.blocks if b.id == identifier), None)
            if block is None or not isinstance(block.config, SectionConfig):
                break
            valid.append(identifier)
            layout = replace(
                layout,
                blocks=block.config.children,
                grid=replace(layout.grid, columns=block.config.columns),
            )
        self.scope = valid
        return layout

    def apply_view(self, layout):
        def merge(parent, path):
            if not path:
                return layout
            blocks = []
            for block in parent.blocks:
                if block.id == path[0]:
                    child = merge(
                        replace(
                            parent,
                            blocks=block.config.children,
                            grid=replace(parent.grid, columns=block.config.columns),
                        ),
                        path[1:],
                    )
                    block = replace(
                        block,
                        config=replace(
                            block.config, children=child.blocks, columns=child.grid.columns
                        ),
                    )
                blocks.append(block)
            return replace(parent, blocks=tuple(blocks))

        self.apply(merge(self.layout, self.scope))

    @property
    def dirty(self):
        return self.layout != self.original

    def apply(self, layout):
        if layout != self.layout:
            self.past.append(self.layout)
            self.layout = layout
            self.future.clear()

    def undo(self):
        if self.past:
            self.future.append(self.layout)
            self.layout = self.past.pop()

    def redo(self):
        if self.future:
            self.past.append(self.layout)
            self.layout = self.future.pop()

    def update(self, identifier: UUID, **changes):
        blocks = tuple(replace(b, **changes) if b.id == identifier else b for b in self.view.blocks)
        # Only placement operations reflow imported explicit grid positions.
        if "placement" in changes:
            blocks = flow(blocks)
        self.apply_view(replace(self.view, blocks=blocks))

    def resize(self, identifier, width):
        self.update(identifier, placement=Placement(width))

    def duplicate(self, identifier):
        def clone(block):
            config = block.config
            if isinstance(config, SectionConfig):
                config = replace(config, children=tuple(clone(c) for c in config.children))
            return replace(block, id=uuid4(), config=config)

        index = next(i for i, b in enumerate(self.view.blocks) if b.id == identifier)
        self.apply_view(self.view.insert(index + 1, clone(self.view.blocks[index])))
