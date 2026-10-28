"""Virtual desktop routes only; not the Phase 3 scope/recurrence domain model."""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

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
        d = self.anchor
        match self.scale:
            case "year":
                return f"year/{d.year:04}"
            case "month":
                return f"month/{d.year:04}-{d.month:02}"
            case "week":
                year, week, _ = d.isocalendar()
                return f"week/{year:04}-W{week:02}"
            case "day":
                return f"day/{d.isoformat()}"
        return ""

    @property
    def start(self) -> date:
        d = self.anchor
        match self.scale:
            case "year":
                return d.replace(month=1, day=1)
            case "month":
                return d.replace(day=1)
            case "week":
                return d - timedelta(days=d.weekday())
        return d

    @property
    def end(self) -> date:
        match self.scale:
            case "year":
                return self.anchor.replace(month=12, day=31)
            case "month":
                return self.anchor.replace(
                    day=calendar.monthrange(self.anchor.year, self.anchor.month)[1]
                )
            case "week":
                return self.start + timedelta(days=6)
        return self.anchor

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
            "statistics": "Estatísticas",
            "settings": "Configurações",
        }.get(self.view, "")

    def select(self, view: str, value: str = "") -> None:
        if view not in (*SCALES, "overview", "calendar", "notes", "statistics", "settings"):
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
