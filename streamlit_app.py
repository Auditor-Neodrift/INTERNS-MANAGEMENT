"""NEODRIFT Interns Audit - Streamlit entry point.

Reads the interns order workbook live from Google Sheets and turns it into a
KPI dashboard, month-by-month automated reports, money and returns audits,
intern scorecards and a configurable exception engine.

Run locally:   streamlit run streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
for folder in (ROOT / "src", ROOT / "app_pages"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

st.set_page_config(
    page_title="NEODRIFT Interns Audit",
    page_icon=":material/fact_check:",
    layout="wide",
    initial_sidebar_state="expanded",
)

import auth  # noqa: E402
import versions  # noqa: E402
import data as data_mod  # noqa: E402
import settings_store  # noqa: E402
import metrics  # noqa: E402
import theme as theme_mod  # noqa: E402
import ui  # noqa: E402


# ---------------------------------------------------------------------------
# Nothing below this line runs until an allow-listed Google account signs in.
# ---------------------------------------------------------------------------
auth.require_login()

# ---------------------------------------------------------------------------
# Config lives in session state so edits on the Settings page apply everywhere
# ---------------------------------------------------------------------------
if "config" not in st.session_state:
    st.session_state["config"] = settings_store.load_config()

ui.inject_css(st.session_state["config"])


def get_config() -> dict:
    return st.session_state["config"]


def load_data():
    """Load the workbook, or render a blocking error page and stop."""
    cfg = get_config()
    ttl = int(cfg.get("display", {}).get("cache_ttl_minutes", 10) or 10)
    try:
        return data_mod.get_data(ttl)
    except Exception as exc:  # noqa: BLE001
        st.error(
            f"Could not read the Google Sheet.\n\n**{type(exc).__name__}:** {exc}",
            icon=":material/error:",
        )
        st.markdown(
            "**Checklist**\n\n"
            "1. The workbook must be shared as *Anyone with the link - Viewer*.\n"
            "2. The `MAIN` tab must exist and keep its current column headers.\n"
            f"3. Sheet in use: [{data_mod.sheet_id()}]({data_mod.sheet_url()})\n"
            "4. Override the key with `SHEET_ID` in secrets or `INTERNS_SHEET_ID` in the environment."
        )
        if st.button("Retry", type="primary"):
            st.cache_data.clear()
            st.rerun()
        st.stop()


def theme_switch() -> None:
    """Theme picker, pinned to the top-right corner of every page.

    Rendered inside a container the CSS fixes to the viewport, so it stays put
    while the page scrolls. The container is exempted from the reveal
    animation and backdrop-filter, either of which would otherwise become the
    containing block and drop it back into the flow.
    """
    display = get_config().setdefault("display", {})
    current = display.get("theme", theme_mod.DEFAULT_THEME)
    dock = st.container(key="theme_dock")
    with dock:
        chosen = st.segmented_control(
            "Theme", theme_mod.THEME_ORDER,
            format_func=lambda k: theme_mod.THEME_LABELS[k],
            default=current, key="theme_pick", label_visibility="collapsed",
        )
    if chosen and chosen != current:
        display["theme"] = chosen
        st.rerun()


def version_bar() -> None:
    """Release picker: plain text plus a chevron, ChatGPT style.

    The menu holds nothing but version names, with the newest labelled Latest.
    Anything explanatory sits below the toggle instead, so the list stays a
    list. Selecting a release cannot hot-swap the running code - one
    deployment serves one branch - so an older pick reveals how to point the
    deployment at it.
    """
    options = versions.all_versions(5)
    running = versions.get(versions.CURRENT) or options[0]
    viewing = st.session_state.get("version_view", versions.CURRENT)
    shown = versions.get(viewing) or running

    st.markdown('<div class="flux-verbar"></div>', unsafe_allow_html=True)
    left, _rest = st.columns([1, 3])
    with left:
        with st.popover(f"v{shown['version']}  ⌄", width="content"):
            for version in options:
                is_latest = version["version"] == versions.CURRENT
                label = f"v{version['version']}"
                if is_latest:
                    label += "   Latest"
                if st.button(label, key=f"ver_{version['version']}",
                             width="stretch"):
                    st.session_state["version_view"] = version["version"]
                    st.rerun()

    if shown["version"] != versions.CURRENT:
        st.markdown(
            f'<div class="flux-ver-note">Viewing v{shown["version"]} · '
            f'{shown["name"]} · the app is running v{versions.CURRENT}</div>',
            unsafe_allow_html=True,
        )
        with st.expander(f"How to switch the live app to v{shown['version']}"):
            for line in shown["changes"]:
                st.markdown(f"- {line}")
            ui.callout(
                versions.rollback_steps(shown), "amber",
                title=f"Point the deployment at v{shown['version']}",
            )
            st.caption(
                f"Still running v{versions.CURRENT}. Streamlit serves one branch "
                "at a time, so the switch happens in the app settings."
            )


def sidebar(bundle) -> None:
    """Shared sidebar: freshness, refresh, scope of the data."""
    with st.sidebar:
        st.markdown("### NEODRIFT Audit")
        st.caption(f"Data pulled {bundle.loaded_at:%d %b %Y, %H:%M}")
        if st.button("Refresh data", width="stretch",
                     icon=":material/refresh:"):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        main = bundle.main
        st.metric("Orders in MAIN", f"{len(main):,}")
        if not main.empty:
            st.caption(
                f"{main['order_date'].min():%d %b %Y} to "
                f"{main['order_date'].max():%d %b %Y}  |  "
                f"{main['ym'].nunique()} months"
            )
        st.caption(f"Interns on roster: {len(bundle.roster):,}")
        st.link_button("Open Google Sheet", data_mod.sheet_url(),
                       width="stretch")

        st.divider()
        auth.sidebar_account()
        st.caption(f"App version v{versions.CURRENT}")

        if bundle.warnings:
            st.divider()
            st.warning("Some tabs were skipped", icon=":material/warning:")
            for line in bundle.warnings:
                st.caption(line)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def notifications(bundle) -> None:
    """Pin the most urgent intern alerts to the bottom-right of every page."""
    cfg = get_config().get("display", {})
    try:
        interns = metrics.intern_table(
            bundle.main, bundle.roster,
            tenure_days=int(cfg.get("tenure_days", 30) or 30),
            idle_days=int(cfg.get("intern_idle_days", 3) or 3),
            cancel_pct=float(cfg.get("intern_cancel_alert_pct", 30.0) or 30.0),
        )
        alerts = metrics.intern_alerts(
            interns,
            int(cfg.get("tenure_days", 30) or 30),
            int(cfg.get("intern_idle_days", 3) or 3),
            float(cfg.get("intern_cancel_alert_pct", 30.0) or 30.0),
        )
    except Exception:  # never let a notification break the page
        return
    if alerts.empty:
        return
    reds = alerts[alerts["severity"] == "red"]
    if reds.empty:
        return
    ui.toast_stack(
        [
            {"title": f"{row['name']} · {row['label']}",
             "message": row["message"], "tone": "red"}
            for _, row in reds.head(3).iterrows()
        ],
        total=int(len(reds)),
    )


def _page(module_name: str, func_name: str = "render"):
    def runner():
        bundle = load_data()
        sidebar(bundle)
        theme_switch()
        version_bar()
        try:
            email = str(getattr(st.user, "email", "") or "")
            name = str(getattr(st.user, "name", "") or "") or email.split("@")[0]
        except Exception:
            email, name = "", ""
        if email:
            ui.top_bar(name or email, email,
                       right=f"<b>{bundle.loaded_at:%d %b %Y}</b> · data pulled "
                             f"{bundle.loaded_at:%H:%M}")
        module = __import__(module_name)
        getattr(module, func_name)(bundle, get_config())
        # The Interns page already lists every alert in full, so the pinned
        # notifications would only repeat it and cover the controls.
        if module_name != "page_interns":
            notifications(bundle)

    runner.__name__ = f"page_{module_name}"
    return runner


# Six areas, each with its own tabs, rather than a long flat page list.
PAGES = [
    st.Page(_page("page_dashboard"), title="Dashboard",
            icon=":material/dashboard:", default=True),
    st.Page(_page("page_interns"), title="Interns",
            icon=":material/groups:", url_path="interns"),
    st.Page(_page("page_audit"), title="Orders & Audit",
            icon=":material/fact_check:", url_path="audit"),
    st.Page(_page("page_money"), title="Payments & Money",
            icon=":material/payments:", url_path="money"),
    st.Page(_page("page_influencers"), title="Influencers",
            icon=":material/campaign:", url_path="influencers"),
    st.Page(_page("page_settings"), title="Settings",
            icon=":material/settings:", url_path="settings"),
]

st.navigation(PAGES).run()
