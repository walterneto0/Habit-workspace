"""Portuguese calendar choices; canonical PeriodRef remains the only conversion."""

import calendar

from PySide6.QtCore import QObject, Slot

from habit_workspace.domain.temporal import PeriodRef
from habit_workspace.presentation.navigation import MONTHS, Navigation, long_date


class PeriodChoices(QObject):
    @Slot(str, result="QVariantMap")
    def describe(self, value):
        if not value:
            return {}
        period = PeriodRef(value)
        day = period.start
        return dict(
            scale=period.scale.value,
            year=f"{day.isocalendar().year if period.scale == 'week' else day.year:04}",
            month=day.month,
            part=day.isocalendar().week
            if period.scale == "week"
            else day.day
            if period.scale == "day"
            else day.month
            if period.scale == "month"
            else 1,
        )

    @Slot(str, result=str)
    def label(self, value):
        if not value:
            return "Escolha um período."
        period = PeriodRef(value)
        if period.scale == "day":
            return long_date(period.start)
        return (
            Navigation(period.start, period.scale.value).title
            + " · "
            + (long_date(period.start) + " — " + long_date(period.end))
        )

    @Slot(str, str, int, result="QVariantList")
    def options(self, scale, year, month):
        if not year.isascii() or not year.isdigit() or not 2 <= int(year) <= 9998:
            return []
        year = int(year)
        match scale:
            case "year":
                values = [(1, f"year/{year:04}", str(year))]
            case "month":
                values = [
                    (m, f"month/{year:04}-{m:02}", f"{name} de {year}")
                    for m, name in enumerate(MONTHS, 1)
                ]
            case "week":
                values = []
                for week in range(1, 54):
                    try:
                        period = PeriodRef(f"week/{year:04}-W{week:02}")
                    except ValueError:
                        continue
                    values.append(
                        (
                            week,
                            str(period),
                            f"Semana {week:02} · {period.start:%d/%m/%Y} — {period.end:%d/%m/%Y}",
                        )
                    )
            case "day" if 1 <= month <= 12:
                values = [
                    (
                        d,
                        f"day/{year:04}-{month:02}-{d:02}",
                        f"{d} de {MONTHS[month - 1].lower()} de {year}",
                    )
                    for d in range(1, calendar.monthrange(year, month)[1] + 1)
                ]
            case _:
                return []
        return [dict(part=part, value=value, label=label) for part, value, label in values]
