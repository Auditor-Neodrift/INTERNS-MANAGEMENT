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
import ui  # noqa: E402

ui.inject_css()

# ---------------------------------------------------------------------------
# Nothing below this line runs until an allow-listed Google account signs in.
# ---------------------------------------------------------------------------
auth.require_login()

# ---------------------------------------------------------------------------
# Config lives in session state so edits on the Settings page apply everywhere
# ---------------------------------------------------------------------------
if "config" not in st.session_state:
    st.session_state["config"] = settings_store.load_config()


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


def version_bar() -> None:
    """ChatGPT-style release picker, top-left of the content area.

    It cannot hot-swap the running code - one deployment serves one branch -
    so selecting an older release shows what is in it and how to switch to it.
    """
    options = versions.all_versions(5)
    labels = [versions.label(v) for v in options]
    picker, _rest = st.columns([1.35, 2.65])
    with picker:
        chosen_label = st.selectbox(
            "Version", labels, index=0, key="version_pick",
            label_visibility="collapsed",
        )
    chosen = options[labels.index(chosen_label)]

    if chosen["version"] == versions.CURRENT:
        st.markdown(
            f'<div class="flux-ver-note">Running v{versions.CURRENT}, the newest '
            f'build<span class="flux-ver-pill">Latest</span></div>',
            unsafe_allow_html=True,
        )
        return

    with st.expander(
        f"What is in v{chosen['version']}, and how to switch to it", expanded=True
    ):
        st.markdown(f"**{chosen['name']}** · released {chosen['date']}")
        ui.callout(chosen["changes"], "grey", title="What this release contains")
        ui.callout(
            versions.rollback_steps(chosen), "amber",
            title=f"Roll the live app back to v{chosen['version']}",
        )
        st.caption(
            f"You are still running v{versions.CURRENT}. Selecting a release here "
            "does not change the running app - Streamlit serves one branch at a "
            "time, so the switch happens in the app settings."
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
def _page(module_name: str, func_name: str = "render"):
    def runner():
        bundle = load_data()
        sidebar(bundle)
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
