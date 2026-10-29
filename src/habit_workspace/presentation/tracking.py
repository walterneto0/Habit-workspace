"""Tracking-mode view data: QML receives plain mappings, never domain objects."""

import json
from datetime import date, datetime, time, timedelta

from habit_workspace.application.capture import FieldCell, HabitCell
from habit_workspace.application.layouts import LayoutService
from habit_workspace.domain.layouts import LayoutResolution
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


def instant_label(value: datetime) -> str:
    return value.astimezone().strftime("%d/%m/%Y às %H:%M")


def layout_notice(report, period: PeriodRef, day: date, today: date, current: LayoutResolution):
    """Label, never change, which layout revision tracking shows for ``day``.

    Tracking shows the period's *current* layout (resolved at the present instant);
    capture still targets ``day`` and refuses pre-activation values. When another
    revision was (or will be) in force at the end of that local day, say so instead of
    implying the current layout is "the layout of that day". Pure: no I/O, no writes.
    """
    start = datetime.combine(day, time()).astimezone()
    end = datetime.combine(day + timedelta(days=1), time()).astimezone() - timedelta(microseconds=1)
    try:
        then = LayoutService.resolve_report(report, period, end)
    except ValueError, OSError:
        return (
            "Exibindo o layout atual. Não foi possível identificar a revisão de "
            + long_date(day)
            + "."
        )
    if (then.layout.id, then.layout.version) != (current.layout.id, current.layout.version):
        name = (
            "o layout básico"
            if then.origin == "builtin"
            else f"“{then.layout.name}” · versão {then.layout.version}"
        )
        verb = "será" if day > today else "era"
        return (
            f"Exibindo o layout atual do período. Em {long_date(day)} a revisão vigente "
            f"{verb} {name}. Registros desse dia são preservados; campos criados depois "
            "não aceitam valores anteriores à ativação nem contam como falha."
        )
    effective = current.assignment.effective_at if current.assignment else None
    if effective is not None and start < effective <= end:
        return (
            f"Este layout passou a valer durante este dia, às {effective.astimezone():%H:%M}. "
            "Campos novos desta revisão não contam como falha antes desse momento."
        )
    return ""


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
