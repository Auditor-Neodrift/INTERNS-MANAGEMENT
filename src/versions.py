"""Release history and the rollback path.

Every release is also pushed as its own git branch, because Streamlit Cloud
deploys a *branch* - not a tag or a commit. That makes rolling back a single
dropdown change in the app's settings rather than a git operation.

Honest limitation: the picker in the header cannot hot-swap the running code.
One deployment serves one branch. What the picker does is show the history,
name the branch for each release, and hand you the exact rollback steps.
"""
from __future__ import annotations

CURRENT = "2.3"

# Newest first. Keep the last five; older entries can be trimmed.
VERSIONS: list[dict] = [
    {
        "version": "2.3",
        "name": "Flux dashboard UI",
        "branch": "v2.3",
        "date": "14 Sep 2026",
        "changes": [
            "Rebuilt the interface in the Flux style: charcoal pill sidebar, "
            "warm off-white canvas, white cards with icon badges and large "
            "tight numerals, lime and violet accents.",
            "Added this version picker with per-release rollback instructions.",
            "KPI cards gained an icon, a delta badge and a unit suffix.",
        ],
    },
    {
        "version": "2.2",
        "name": "Intern alerts + iOS glass",
        "branch": "v2.2",
        "date": "14 Sep 2026",
        "changes": [
            "Clerical-error, idle-intern and high-cancellation alerts, all with "
            "limits editable in Settings.",
            "End date now shows the date actually recorded instead of a "
            "joining + 30 days guess.",
            "iOS glass theme and a centred sign-in card.",
        ],
    },
    {
        "version": "2.1",
        "name": "Interns + influencers",
        "branch": "v2.1",
        "date": "14 Sep 2026",
        "changes": [
            "Active Interns dashboard, per-intern daily activity and the "
            "30-day tenure reminder.",
            "Influencer sourcing with duplicate detection and an admin pipeline.",
            "Navigation consolidated from nine flat pages into six tabbed areas.",
        ],
    },
]


def all_versions(limit: int = 5) -> list[dict]:
    return VERSIONS[:limit]


def latest() -> dict:
    return VERSIONS[0]


def get(version: str) -> dict | None:
    return next((v for v in VERSIONS if v["version"] == version), None)


def label(version: dict) -> str:
    """'2.3 - Flux dashboard UI (Latest)' for the picker."""
    suffix = "  ·  Latest" if version["version"] == CURRENT else ""
    return f"v{version['version']}  ·  {version['name']}{suffix}"


def rollback_steps(version: dict) -> list[str]:
    branch = version["branch"]
    return [
        "Open your app on share.streamlit.io and choose "
        "<strong>Settings &rarr; General</strong>.",
        f"Change <strong>Branch</strong> from <code>main</code> to "
        f"<code>{branch}</code> and save.",
        "The app redeploys in under a minute. Your secrets are untouched.",
        f"To come back to the newest build, set the branch to <code>main</code> "
        f"again (currently v{CURRENT}).",
    ]
