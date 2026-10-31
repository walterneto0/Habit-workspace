"""Virtual desktop routes backed by the shared civil-period domain."""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

from habit_workspace.domain.temporal import PeriodRef

MONTHS = (
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)
WEEKDAYS = (
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
)
SCALES = ("year", "month", "week", "day")


def long_date(value: date) -> str:
    return f"{value.day} de {MONTHS[value.month - 1].lower()} de {value.year}"


@dataclass
class Navigation:
    anchor: date
    view: str = "overview"

    @property
    def scale(self) -> str:
        return "month" if self.view == "calendar" else self.view

    @property
    def period(self) -> str:
        return str(self.period_ref) if self.period_ref else ""

    @property
    def period_ref(self) -> PeriodRef | None:
        if self.scale in SCALES:
            return PeriodRef.containing(self.scale, self.anchor)
        return None

    @property
    def start(self) -> date:
        return self.period_ref.start if self.period_ref else self.anchor

    @property
    def end(self) -> date:
        return self.period_ref.end if self.period_ref else self.anchor

    @property
    def title(self) -> str:
        d = self.anchor
        match self.scale:
            case "year":
                return str(d.year)
            case "month":
                return f"{MONTHS[d.month - 1]} de {d.year}"
            case "week":
                year, week, _ = d.isocalendar()
                return f"Semana {week:02} · {year}"
            case "day":
                return long_date(d)
        return {
            "overview": "Visão geral",
            "notes": "Documentos e notas",
            "planning": "Planejamento",
            "habits": "Hábitos",
            "statistics": "Estatísticas",
            "settings": "Configurações",
        }.get(self.view, "")

    def select(self, view: str, value: str = "") -> None:
        if view not in (
            *SCALES,
            "overview",
            "calendar",
            "notes",
            "planning",
            "habits",
            "statistics",
            "settings",
        ):
            raise ValueError("Destino de navegação desconhecido.")
        target = date.fromisoformat(value) if value else self.anchor
        # Leave one year at either end for complete adjacent calendar weeks.
        if not 2 <= target.year <= 9998:
            raise ValueError("A navegação aceita anos de 2 a 9998.")
        self.anchor, self.view = target, view

    def move(self, amount: int) -> None:
        d = self.anchor
        match self.scale:
            case "year" | "month":
                months = amount * (12 if self.scale == "year" else 1)
                year, month = divmod(d.year * 12 + d.month - 1 + months, 12)
                target = date(year, month + 1, min(d.day, calendar.monthrange(year, month + 1)[1]))
            case "week" | "day":
                target = d + timedelta(days=amount * (7 if self.scale == "week" else 1))
            case _:
                return
        self.select(self.view, target.isoformat())

    def breadcrumbs(self) -> list[dict]:
        return [
            {
                "view": scale,
                "date": self.anchor.isoformat(),
                "label": Navigation(self.anchor, scale).title,
                "period": Navigation(self.anchor, scale).period,
            }
            for scale in SCALES
        ]

    def calendar(self) -> list[dict]:
        first = self.anchor.replace(day=1)
        start = first - timedelta(days=first.weekday())
        return [
            {
                "date": (d := start + timedelta(days=i)).isoformat(),
                "day": d.day,
                "label": long_date(d),
                "inMonth": d.month == first.month,
                "week": d.isocalendar().week,
            }
            for i in range(42)
        ]

    def children(self) -> list[dict]:
        if self.scale == "year":
            return [
                {
                    "view": "month",
                    "date": date(self.anchor.year, m, 1).isoformat(),
                    "label": MONTHS[m - 1],
                    "detail": f"{self.anchor.year} · {m:02}",
                }
                for m in range(1, 13)
            ]
        if self.scale == "week":
            return [
                {
                    "view": "day",
                    "date": (d := self.start + timedelta(days=i)).isoformat(),
                    "label": WEEKDAYS[i],
                    "detail": long_date(d),
                }
                for i in range(7)
            ]
        return []
