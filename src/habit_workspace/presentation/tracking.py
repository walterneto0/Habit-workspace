"""Tracking-mode view data: QML receives plain mappings, never domain objects."""

import json
from datetime import date

from habit_workspace.application.capture import FieldCell, HabitCell
from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.presentation.navigation import WEEKDAYS, long_date

STATE_LABELS = {
    "done": "Concluído",
    "skipped": "Dispensado",
    "missed": "Não cumprido (declarado)",
    "not_scheduled": "Não programado nesta data",
    "future": "Futuro · sem registro",
    "pending": "Pendente hoje · sem registro",
    "unrecorded": "Sem registro (não é falha)",
}
TYPE_HINTS = {
    "integer": "Número inteiro",
    "number": "Número",
    "duration": "Duração",
    "rating": "Avaliação",
    "text": "Texto",
    "date": "AAAA-MM-DD",
    "time": "HH:MM",
}


def token(value) -> str:
    """Opaque echo of the displayed canonical value, used for stale-write detection."""
    return json.dumps(value)


def display(value) -> str:
    if value is None:
        return ""
    if type(value) is bool:
        return "Sim" if value else "Não"
    if type(value) is float:
        return f"{value:g}".replace(".", ",")
    return str(value)


def cell_mapping(cell: HabitCell | FieldCell) -> dict:
    if isinstance(cell, HabitCell):
        return dict(
            kind="habit",
            id=str(cell.habit_id),
            name=cell.name,
            state=cell.state,
            stateLabel=STATE_LABELS.get(cell.state, cell.state),
            recorded=cell.recorded or "",
            token=token(cell.recorded),
            editable=cell.editable,
            note=cell.note,
        )
    return dict(
        kind="field",
        id=str(cell.field_id),
        name=cell.name,
        valueType=cell.value_type,
        value=display(cell.value),
        boolean=cell.value if type(cell.value) is bool else None,
        recorded=cell.value is not None,
        token=token(cell.value),
        editable=cell.editable,
        note=cell.note,
        unit=cell.unit or "",
        options=list(cell.options),
        hint=TYPE_HINTS.get(cell.value_type, ""),
        bounds=" · ".join(
            label + display(bound)
            for label, bound in (("mín. ", cell.minimum), ("máx. ", cell.maximum))
            if bound is not None
        ),
    )


def default_day(period: PeriodRef, today: date) -> date:
    if period.start <= today <= period.end:
        return today
    return period.end if period.end < today else period.start


def date_state(period: PeriodRef, day: date, today: date) -> dict:
    return dict(
        date=day.isoformat(),
        label=WEEKDAYS[day.weekday()] + ", " + long_date(day),
        isToday=day == today,
        isFuture=day > today,
        canPrevious=day > period.start,
        canNext=day < period.end,
        fixed=period.start == period.end,
    )


def habit_properties(habit) -> dict:
    """Shared display labels for the canonical definition, independent of its path."""
    from datetime import timedelta

    end = habit.scope.end_exclusive
    return dict(
        id=str(habit.id),
        name=habit.name,
        tags=", ".join(habit.tags),
        scope=habit.scope.start.isoformat()
        + " → "
        + ((end - timedelta(days=1)).isoformat() if end else "sem término"),
        recurrence="Diário"
        if habit.recurrence.kind == "daily"
        else ", ".join(WEEKDAYS[d - 1] for d in habit.recurrence.days),
    )
