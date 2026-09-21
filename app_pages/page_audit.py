"""Orders & Audit - the order-side reporting, consolidated into tabs.

Tabs: Monthly report | Overall report | Reflection rate report | Returns |
      Products & ASINs | Exceptions

Each tab delegates to the module that owns that report, so the reporting logic
lives in one place and this file only handles the tab shell.
"""
from __future__ import annotations

import streamlit as st

import page_exceptions
import page_monthly
import page_overall
import page_products
import page_reflection
import page_returns
import ui


def render(bundle, config: dict) -> None:
    st.title("Orders & Audit")
    ui.hero(
        "Every order-side report in one place",
        "Monthly and all-time reporting, returns, product performance and the "
        "row-level exception engine. All figures are recomputed live from the "
        "MAIN tab and reconciled against the workbook's own totals.",
    )

    tabs = st.tabs([
        "Monthly report", "Overall report", "Reflection rate report",
        "Returns", "Products & ASINs", "Exceptions",
    ])
    with tabs[0]:
        page_monthly.render(bundle, config, embedded=True)
    with tabs[1]:
        page_overall.render(bundle, config, embedded=True)
    with tabs[2]:
        page_reflection.render(bundle, config, embedded=True)
    with tabs[3]:
        page_returns.render(bundle, config, embedded=True)
    with tabs[4]:
        page_products.render(bundle, config, embedded=True)
    with tabs[5]:
        page_exceptions.render(bundle, config, embedded=True)
