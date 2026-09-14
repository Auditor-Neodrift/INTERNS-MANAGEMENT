"""Release history and the rollback path.

Every release is also pushed as its own git branch, because Streamlit Cloud
deploys a *branch* - not a tag or a commit. That makes rolling back a single
dropdown change in the app's settings rather than a git operation.

Honest limitation: the picker in the header cannot hot-swap the running code.
One deployment serves one branch. What the picker does is show the history,
name the branch for each release, and hand you the exact rollback steps.
"""
from __future__ import annotations

CURRENT = "2.8"

# Newest first. Keep the last five; older entries can be trimmed.
VERSIONS: list[dict] = [
    {
        "version": "2.8",
        "name": "Four themes, crystal glass",
        "branch": "v2.8",
        "date": "15 Sep 2026",
        "changes": [
            "Theme switch pinned to the top-right of every page: Dark Glass, "
            "Light Glass, Dark and Light.",
            "Glass is now crystal - roughly half opacity at 26px blur - and "
            "covers the sidebar and tables as well as the cards.",
            "Settings can set a background image per mode, by path, URL or "
            "upload.",
        ],
    },
    {
        "version": "2.7",
        "name": "Photo backdrop, dark glass",
        "branch": "v2.7",
        "date": "15 Sep 2026",
        "changes": [
            "The bubble photograph is now the app backdrop, served statically "
            "and pre-blurred at build time.",
            "Because the image is near-black the theme flips to dark glass: "
            "dark translucent panels, light text, cool rim lights.",
            "Every pill, card, tab and toast is frosted over the photo; tables "
            "stay near-opaque so data reads cleanly.",
        ],
    },
    {
        "version": "2.6",
        "name": "Glassmorphism UI",
        "branch": "v2.6",
        "date": "15 Sep 2026",
        "changes": [
            "Rebuilt the styling to the uxpilot glassmorphism rules: vibrant "
            "gradient backdrop, frosted panels at 18px blur, one light "
            "direction, rim-lit edges.",
            "Glass is applied selectively - sidebar, cards, alerts, tabs - "
            "while tables and forms stay near-opaque so data reads cleanly.",
            "Charts follow ggplot's grammar on glass: tinted panel, white "
            "gridlines, no spines or ticks.",
            "Green and amber darkened to clear WCAG AA on glass.",
        ],
    },
    {
        "version": "2.5",
        "name": "Cleaner version menu",
        "branch": "v2.5",
        "date": "14 Sep 2026",
        "changes": [
            "Version toggle is bare text with no pill or border; the menu lists "
            "version names only, with Latest marking the newest.",
            "Rollback detail moved out of the menu and under the toggle, so the "
            "list stays a list.",
        ],
    },
    {
        "version": "2.4",
        "name": "Alert triage + version toggle",
        "branch": "v2.4",
        "date": "14 Sep 2026",
        "changes": [
            "Alerts tab gained a sub-category toggle and lays its cards out "
            "three across instead of one long column.",
            "Urgent alerts now pin to the bottom-right as small dismissible "
            "notifications on every page except Interns, which already lists them.",
            "Version toggle is plain text with a chevron, no longer clipped at "
            "the top of the page.",
        ],
    },
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
