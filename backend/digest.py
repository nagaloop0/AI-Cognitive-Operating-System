"""
Day digest: turns one local day of raw `app_activity` rows into a short, exact report
(minutes per app, top window titles, breaks, app switches, longest focus block).
No AI here: the numbers are plain arithmetic, so they can be trusted and tested.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, tzinfo

from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.models import AppActivity, TitleCategory
from backend.privacy import PRIVATE_APP_GROUP, PRIVATE_TITLE, is_private_app, redact
from backend.timeutil import as_utc, format_minutes, local_day_bounds, local_tz

BREAK_GAP_SECONDS = 60          # a gap longer than this between two windows counts as a break
SWITCH_GAP_SECONDS = 300        # two apps further apart than this are not a "switch" (same rule as the pattern engine)
FOCUS_GAP_SECONDS = 120         # short interruptions shorter than this do not end a focus block
MAX_APPS = 8
TITLES_PER_APP = 3


class AppUsage(BaseModel):
    app_name: str
    minutes: int
    top_titles: list[str]


class FocusBlock(BaseModel):
    app_name: str
    minutes: int
    start: datetime
    end: datetime


class DayDigest(BaseModel):
    day: date
    active_minutes: int
    break_minutes: int
    app_switches: int
    first_activity: datetime | None
    last_activity: datetime | None
    apps: list[AppUsage]
    longest_focus: FocusBlock | None
    category_minutes: dict[str, int]

    @property
    def is_empty(self) -> bool:
        return self.active_minutes == 0

    def to_prompt_text(self) -> str:
        """Compact plain text for the language model. Titles are already redacted."""
        if self.is_empty:
            return f"Date: {self.day:%A %Y-%m-%d}\nNo activity recorded."
        lines = [
            f"Date: {self.day:%A %Y-%m-%d}",
            f"Active time: {format_minutes(self.active_minutes)}; breaks: {format_minutes(self.break_minutes)}; "
            f"app switches: {self.app_switches}",
            f"First activity {self.first_activity:%H:%M}, last activity {self.last_activity:%H:%M}",
        ]
        if self.longest_focus:
            f = self.longest_focus
            lines.append(f"Longest focus: {format_minutes(f.minutes)} in {f.app_name} ({f.start:%H:%M}-{f.end:%H:%M})")
        if self.category_minutes:
            split = ", ".join(f"{name} {format_minutes(m)}" for name, m in self.category_minutes.items())
            lines.append(f"Time by category: {split}")
        lines.append("Apps (minutes; most used window titles):")
        for app in self.apps:
            titles = "; ".join(app.top_titles) if app.top_titles else "-"
            lines.append(f"- {app.app_name}: {app.minutes} min | {titles}")
        return "\n".join(lines)


@dataclass
class _Segment:
    app_name: str
    title: str
    start: datetime
    end: datetime

    @property
    def seconds(self) -> float:
        return (self.end - self.start).total_seconds()


def load_segments(db: Session, start_utc: datetime, end_utc: datetime) -> list[_Segment]:
    """Activity rows overlapping [start_utc, end_utc), clipped to that window, oldest first."""
    rows = (
        db.query(AppActivity)
        .filter(AppActivity.start_time >= start_utc - timedelta(days=1), AppActivity.start_time < end_utc)
        .order_by(AppActivity.start_time.asc())
        .all()
    )
    segments = []
    for row in rows:
        if not row.app_name or not row.start_time:
            continue
        start = as_utc(row.start_time)
        end = as_utc(row.end_time) if row.end_time else start + timedelta(seconds=row.duration_seconds or 0)
        start, end = max(start, start_utc), min(end, end_utc)
        if end > start:
            segments.append(_Segment(row.app_name, row.window_title or "", start, end))
    return segments


def build_day_digest(db: Session, day: date, private_apps: list[str], tz: tzinfo | None = None) -> DayDigest:
    tz = tz or local_tz()
    start_utc, end_utc = local_day_bounds(day, tz)
    segments = load_segments(db, start_utc, end_utc)
    # Private apps are reported only as one total, never by name or title
    for seg in segments:
        if is_private_app(seg.app_name, private_apps):
            seg.app_name, seg.title = PRIVATE_APP_GROUP, PRIVATE_TITLE

    if not segments:
        return DayDigest(day=day, active_minutes=0, break_minutes=0, app_switches=0, first_activity=None,
                         last_activity=None, apps=[], longest_focus=None, category_minutes={})

    return DayDigest(
        day=day,
        active_minutes=round(sum(s.seconds for s in segments) / 60),
        break_minutes=round(_break_seconds(segments) / 60),
        app_switches=_count_switches(segments),
        first_activity=segments[0].start.astimezone(tz),
        last_activity=max(s.end for s in segments).astimezone(tz),
        apps=_app_usage(segments),
        longest_focus=_longest_focus(segments, tz),
        category_minutes=_category_minutes(db, segments),
    )


def _break_seconds(segments: list[_Segment]) -> float:
    total = 0.0
    latest_end = segments[0].end
    for seg in segments[1:]:
        gap = (seg.start - latest_end).total_seconds()
        if gap > BREAK_GAP_SECONDS:
            total += gap
        latest_end = max(latest_end, seg.end)
    return total


def _count_switches(segments: list[_Segment]) -> int:
    switches = 0
    for prev, curr in zip(segments, segments[1:]):
        if prev.app_name != curr.app_name and (curr.start - prev.end).total_seconds() <= SWITCH_GAP_SECONDS:
            switches += 1
    return switches


def _app_usage(segments: list[_Segment]) -> list[AppUsage]:
    app_seconds: dict[str, float] = defaultdict(float)
    title_seconds: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for seg in segments:
        app_seconds[seg.app_name] += seg.seconds
        title = redact(seg.title)
        if title and title != PRIVATE_TITLE:
            title_seconds[seg.app_name][title] += seg.seconds

    ranked = sorted(app_seconds.items(), key=lambda item: item[1], reverse=True)
    usage = [
        AppUsage(
            app_name=app,
            minutes=round(seconds / 60),
            top_titles=[t for t, _ in sorted(title_seconds[app].items(), key=lambda i: i[1], reverse=True)[:TITLES_PER_APP]],
        )
        for app, seconds in ranked[:MAX_APPS]
    ]
    rest = sum(seconds for _, seconds in ranked[MAX_APPS:])
    if rest:
        usage.append(AppUsage(app_name="Other apps", minutes=round(rest / 60), top_titles=[]))
    return [u for u in usage if u.minutes > 0]


def _longest_focus(segments: list[_Segment], tz: tzinfo) -> FocusBlock | None:
    best: tuple[str, datetime, datetime, float] | None = None
    block_app, block_start, block_end, block_seconds = segments[0].app_name, segments[0].start, segments[0].end, segments[0].seconds
    for seg in segments[1:]:
        same_block = seg.app_name == block_app and (seg.start - block_end).total_seconds() <= FOCUS_GAP_SECONDS
        if same_block:
            block_end, block_seconds = max(block_end, seg.end), block_seconds + seg.seconds
            continue
        if best is None or block_seconds > best[3]:
            best = (block_app, block_start, block_end, block_seconds)
        block_app, block_start, block_end, block_seconds = seg.app_name, seg.start, seg.end, seg.seconds
    if best is None or block_seconds > best[3]:
        best = (block_app, block_start, block_end, block_seconds)

    app, start, end, seconds = best
    if seconds < 60:
        return None
    return FocusBlock(app_name=app, minutes=round(seconds / 60), start=start.astimezone(tz), end=end.astimezone(tz))


def _category_minutes(db: Session, segments: list[_Segment]) -> dict[str, int]:
    """Minutes per category for titles that are already categorized (see backend/categories.py)."""
    labels = {(row.app_name, row.window_title): row.category for row in db.query(TitleCategory).all()}
    if not labels:
        return {}
    seconds: dict[str, float] = defaultdict(float)
    for seg in segments:
        category = labels.get((seg.app_name, seg.title))
        if category:
            seconds[category] += seg.seconds
    minutes = {name: round(s / 60) for name, s in sorted(seconds.items(), key=lambda i: i[1], reverse=True)}
    return {name: m for name, m in minutes.items() if m > 0}
