"""
Fake activity for the public demo: one invented work week of a fictional developer.
Every app and window title here is made up. Nothing comes from a real database.
"""
from datetime import date, timedelta

DEMO_DAYS = [date(2026, 10, 26) + timedelta(days=i) for i in range(5)]  # Monday to Friday
DEMO_TODAY = date(2026, 10, 31)  # "yesterday" in the example questions = Friday
DEMO_TIMEZONE = "Europe/Berlin"

# (start "HH:MM", app, window title, minutes)
MORNING = [
    ("08:55", "Mail", "Inbox (4)", 6),
    ("09:01", "Slack", "#backend - Team", 4),
    ("09:05", "Code", "orders.py — shop-api", 38),
    ("09:43", "Google Chrome", "SQLAlchemy relationships - Documentation", 9),
    ("09:52", "Code", "test_orders.py — shop-api", 7),
    ("10:00", "zoom.us", "Zoom Meeting", 15),
    ("10:15", "Code", "orders.py — shop-api", 52),
    ("11:07", "Terminal", "shop-api — pytest", 6),
    ("11:13", "Google Chrome", "Pull request #48: Add order search - GitHub", 12),
    ("11:25", "WhatsApp", "(private)", 5),
    ("11:30", "Code", "DashboardView.vue — shop-web", 55),
]
AFTERNOON = [
    ("13:20", "Slack", "#frontend - Team", 6),
    ("13:26", "Code", "DashboardView.vue — shop-web", 48),
    ("14:14", "Google Chrome", "Vue Router guide", 11),
    ("14:25", "Terminal", "shop-web — npm run dev", 4),
    ("14:29", "Code", "CartView.vue — shop-web", 41),
    ("15:10", "Google Chrome", "Champions League highlights - YouTube", 14),
    ("15:24", "Spotify", "Focus playlist", 3),
    ("15:27", "Code", "docker-compose.yml — shop-api", 25),
    ("15:52", "Google Chrome", "Python asyncio explained - YouTube", 18),
    ("16:10", "Google Chrome", "Sprint board - Jira", 9),
    ("16:19", "Code", "test_orders.py — shop-api", 34),
]

# Small per-day changes, so the days and their summaries differ
DAY_CHANGES = {
    0: {"skip": set(), "extra": [("16:53", "Google Chrome", "Pull request #48: Add order search - GitHub", 20)]},
    1: {"skip": {"15:10"}, "extra": [("16:53", "Code", "orders.py — shop-api", 45)]},
    2: {"skip": {"11:30", "13:26"}, "extra": [("11:30", "zoom.us", "Zoom Meeting", 45),
                                             ("13:26", "Google Chrome", "Champions League highlights - YouTube", 35)]},
    3: {"skip": {"09:43"}, "extra": [("16:53", "Code", "DashboardView.vue — shop-web", 50)]},
    4: {"skip": {"14:29", "15:27", "16:19", "16:10"}, "extra": []},  # short Friday
}


def activities_for(day_index: int) -> list[tuple[str, str, str, int]]:
    """The day's blocks, sorted by start time."""
    change = DAY_CHANGES[day_index]
    blocks = [b for b in MORNING + AFTERNOON if b[0] not in change["skip"]] + change["extra"]
    return sorted(blocks)


def all_titles() -> set[str]:
    titles = {b[2] for b in MORNING + AFTERNOON}
    for change in DAY_CHANGES.values():
        titles |= {b[2] for b in change["extra"]}
    return titles
