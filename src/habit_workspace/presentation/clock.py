"""Local civil time for the presentation layer, injectable so tests never wait for midnight.

``today`` is the local civil date used for pending/past/future states and capture
eligibility; ``now`` is the aware instant used to resolve layouts and stamp records.
Both are re-read on every call, so suspend/resume, manual clock changes and NTP
corrections are observed the next time the controller checks. A change of the
operating-system time zone is observed only as far as the C library reports it to
this process (on some platforms a restart is needed); see the 6.5A report.
"""

import time
from datetime import date, datetime, timedelta


class SystemClock:
    def now(self) -> datetime:
        return datetime.now().astimezone()

    def today(self) -> date:
        return self.now().date()


class PinnedDateClock(SystemClock):
    """Legacy ``today=`` injection: a fixed civil date with real instants."""

    def __init__(self, day: date):
        self.day = day

    def today(self) -> date:
        return self.day


class ManualClock:
    """Deterministic clock for tests and benchmarks.

    Starts at ``start`` (a date means local noon) and flows with real elapsed time so
    consecutive activations stay strictly ordered; ``set`` jumps explicitly, e.g. over
    midnight or across a simulated suspend.
    """

    def __init__(self, start: date | datetime):
        self.set(start)

    def set(self, value: date | datetime) -> None:
        if not isinstance(value, datetime):
            value = datetime(value.year, value.month, value.day, 12)
        self._base = value if value.utcoffset() is not None else value.astimezone()
        self._started = time.monotonic()

    def advance(self, **delta) -> None:
        self.set(self.now() + timedelta(**delta))

    def now(self) -> datetime:
        return self._base + timedelta(seconds=time.monotonic() - self._started)

    def today(self) -> date:
        return self.now().date()
