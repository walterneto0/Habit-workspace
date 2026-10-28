from dataclasses import replace
from uuid import uuid4

from habit_workspace.application.layout_draft import LayoutDraft
from habit_workspace.domain.layouts import Component, Grid, LayoutTemplate, NoteConfig


def test_operations_are_isolated_and_reversible():
    original = LayoutTemplate(uuid4(), 1, "Teste", grid=Grid(2))
    draft = LayoutDraft(original)
    block = Component(uuid4(), "note", "Nota", NoteConfig())
    draft.apply(original.insert(0, block))
    draft.duplicate(block.id)
    assert len({b.id for b in draft.layout.walk()}) == 2
    clone = draft.layout.blocks[1]
    draft.apply(draft.layout.move(clone.id, 0))
    draft.resize(clone.id, 2)
    assert draft.layout.positions()[0].width == 2
    final = draft.layout
    draft.undo()
    draft.redo()
    assert draft.layout == final
    draft.apply(draft.layout.remove(block.id))
    assert original.blocks == ()
    draft.undo()
    assert draft.layout == final
    draft.undo()
    draft.apply(replace(draft.layout, name="Outro"))
    assert not draft.future


def test_property_edits_preserve_explicit_placement():
    from habit_workspace.domain.layouts import (
        Component,
        Grid,
        LayoutTemplate,
        NoteConfig,
        Placement,
    )

    block = Component(uuid4(), "note", "Before", NoteConfig(), Placement(1, 3, 1))
    draft = LayoutDraft(LayoutTemplate(uuid4(), 1, "Positioned", (block,), grid=Grid(2)))
    draft.update(block.id, title="After")
    assert draft.layout.blocks[0].placement == block.placement
