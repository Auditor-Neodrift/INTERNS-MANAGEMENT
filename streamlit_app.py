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
    initial_sidebar_state="collapsed",
)

import auth  # noqa: E402
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
        module = __import__(module_name)
        getattr(module, func_name)(bundle, get_config())

    runner.__name__ = f"page_{module_name}"
    return runner


PAGES = [
    # The default page is served at "/", so it takes no url_path of its own.
    st.Page(_page("page_dashboard"), title="Dashboard",
            icon=":material/dashboard:", default=True),
    st.Page(_page("page_monthly"), title="Monthly Report",
            icon=":material/calendar_month:", url_path="monthly"),
    st.Page(_page("page_overall"), title="Overall Audit Report",
            icon=":material/table_chart:", url_path="overall"),
    st.Page(_page("page_money"), title="Payments & Money",
            icon=":material/payments:", url_path="money"),
    st.Page(_page("page_returns"), title="Returns Report",
            icon=":material/assignment_return:", url_path="returns"),
    st.Page(_page("page_interns"), title="Intern Report",
            icon=":material/groups:", url_path="interns"),
    st.Page(_page("page_products"), title="Products & ASINs",
            icon=":material/inventory_2:", url_path="products"),
    st.Page(_page("page_exceptions"), title="Audit & Exceptions",
            icon=":material/rule:", url_path="exceptions"),
    st.Page(_page("page_settings"), title="Settings",
            icon=":material/settings:", url_path="settings"),
]

st.navigation(PAGES).run()
