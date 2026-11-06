"""Bounded read-only agenda; event dates always use the saved IANA timezone."""

from datetime import UTC, date, timedelta
from itertools import groupby

from habit_workspace.domain.events import Timed, event_from_mapping
from habit_workspace.vault.habits import habit_from_document

STATUS_LABELS = {
    "done": "Concluído",
    "missed": "Falha declarada",
    "skipped": "Dispensado",
    "unrecorded": "Sem registro",
    "pending": "Pendente",
    "future": "Futuro",
    "completed": "Concluída",
    "conflict": "Conflito · confira as pendências",
}
WEEKDAYS = (
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
)
MONTHS = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


def agenda_groups(rows):
    """Group an already sorted, bounded projection without another source query."""
    groups = []
    for key, values in groupby(rows, key=lambda row: row["display_day"]):
        day = date.fromisoformat(key)
        groups.append(
            dict(
                day=key,
                label=(
                    f"{WEEKDAYS[day.weekday()]}, {day.day} de {MONTHS[day.month - 1]} de {day.year}"
                ),
                rows=list(values),
            )
        )
    return groups


def agenda_rows(report, period, today, *, offset_days=0, window_days=31):
    if not 1 <= window_days <= 31 or offset_days < 0:
        raise ValueError("Agenda windows must be between 1 and 31 days")
    start = period.start + timedelta(days=offset_days)
    end = min(period.end_exclusive, start + timedelta(days=window_days))
    conflicts = {c.document_id for c in report.conflicts}
    records = {}
    record_ids = {}
    for loaded in report.documents:
        for record in loaded.document.metadata["hw"].get("checkins", []):
            records.setdefault((record["habit_id"], record["date"]), []).append(
                (record, loaded.document.id in conflicts)
            )
            record_ids[record["id"]] = record_ids.get(record["id"], 0) + 1
    rows, seen = [], set()

    def append_row(
        kind,
        identifier,
        day,
        title,
        status="",
        *,
        clock="",
        end_time="",
        zone="",
        rank=3,
        label="",
        all_day=False,
        missing=False,
        conflict=False,
        sort_instant=0,
    ):
        key = (kind, identifier, day)
        if key in seen:
            return
        seen.add(key)
        rows.append(
            dict(
                source_kind=kind,
                source_id=str(identifier),
                display_day=day.isoformat(),
                title=title,
                status=status,
                status_label=STATUS_LABELS.get(status, status),
                timezone=zone,
                time=clock,
                end_time=end_time,
                time_label=label,
                all_day=all_day,
                conflict=conflict,
                missing=missing,
                target=str(identifier),
                rank=rank,
                sort_instant=sort_instant,
            )
        )

    for loaded in report.documents:
        doc = loaded.document
        if doc.kind not in ("event", "task", "habit"):
            continue
        hw = doc.metadata["hw"]
        event = event_from_mapping(hw) if doc.kind == "event" else None
        habit = habit_from_document(doc) if doc.kind == "habit" else None
        day = start
        while day < end:
            conflict = doc.id in conflicts
            if event and event.intersects_day(day):
                t = event.timing
                if isinstance(t, Timed):
                    first, last = t.starts_at, t.ends_at
                    clock = first.strftime("%H:%M") if first.date() == day else "00:00"
                    end_time = last.strftime("%H:%M") if last.date() == day else "24:00"
                    label = f"{clock} → {end_time}"
                    if first.date() < day:
                        label = "Continuação · " + label.lower()
                    if last.date() > day and last.time().isoformat() != "00:00:00":
                        label += " · segue no próximo dia"
                    if first.date() != last.date():
                        label += f" ({first:%d/%m/%Y %H:%M} → {last:%d/%m/%Y %H:%M})"
                    append_row(
                        "event",
                        doc.id,
                        day,
                        doc.title,
                        clock=clock,
                        end_time=end_time,
                        zone=t.timezone,
                        rank=1,
                        label=label,
                        conflict=conflict,
                        sort_instant=first.astimezone(UTC).timestamp(),
                    )
                else:
                    label = "Dia inteiro"
                    if (t.end_date_exclusive - t.start_date).days > 1:
                        last_day = t.end_date_exclusive - timedelta(days=1)
                        label += f" · {t.start_date:%d/%m/%Y} a {last_day:%d/%m/%Y}"
                    append_row(
                        "event",
                        doc.id,
                        day,
                        doc.title,
                        zone=t.timezone,
                        rank=0,
                        label=label,
                        all_day=True,
                        conflict=conflict,
                    )
            elif habit and habit.is_scheduled(day):
                entries = records.get((str(doc.id), day.isoformat()), [])
                conflict = (
                    conflict
                    or len(entries) > 1
                    or any(c or record_ids[r["id"]] > 1 for r, c in entries)
                )
                status = (
                    "conflict"
                    if conflict
                    else entries[0][0]["state"]
                    if entries
                    else "unrecorded"
                    if day < today
                    else "pending"
                    if day == today
                    else "future"
                )
                append_row("habit", doc.id, day, doc.title, status, conflict=conflict)
            elif doc.kind == "task" and hw.get("due_date") == day.isoformat():
                append_row("task", doc.id, day, doc.title, hw["status"], rank=2, conflict=conflict)
            day += timedelta(days=1)
    # Imported snapshots disclose missing dependencies, never infer a schedule.
    known = {str(d.document.id) for d in report.documents if d.document.kind == "habit"}
    for (identifier, date_text), entries in records.items():
        day = date.fromisoformat(date_text)
        if identifier not in known and start <= day < end:
            record = entries[0][0]
            append_row(
                "habit",
                identifier,
                day,
                record["label_snapshot"],
                record["state"],
                missing=True,
                conflict=len(entries) > 1 or any(c for _, c in entries),
                label="Hábito ausente · registro salvo, programação indisponível",
            )
    return sorted(
        rows,
        key=lambda r: (r["display_day"], r["rank"], r["time"], r["sort_instant"], r["source_id"]),
    )
