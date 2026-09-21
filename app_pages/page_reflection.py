"""Reflection rate report: order-ID-wise worklist of reviews that never went
live, with the executive's reason and the checker's sign-off.

The list itself is read from MAIN and never written back. The two editable
columns - Remark and Checker - live in a side store, because the app is a
viewer on the audit workbook by design.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import reflection
import ui

# Order ID, ASIN, intern and product first, as asked; the dates explain why
# the row is here; Remark then Checker last, so the executive writes and the
# checker signs off on what was written.
VIEW_COLUMNS = [
    "order_id", "asin", "intern", "product",
    "order_date", "age_days", "status", "payment_state",
    "remark", "checked",
]

EXPORT_RENAMES = {
    "order_id": "Order ID", "asin": "ASIN", "intern": "Intern",
    "product": "Product", "order_date": "Order date", "age_days": "Days old",
    "status": "Amazon status", "payment_state": "Payment",
    "order_price": "Order value", "review_link": "Review link",
    "remark": "Remark", "checked": "Checker verified",
    "checked_by": "Checked by", "updated_at": "Updated at",
    "updated_by": "Updated by",
}


def render(bundle, config: dict, embedded: bool = False) -> None:
    display = config.get("display", {})
    symbol = display.get("currency_symbol", "Rs")
    sla_days = int(display.get("reflection_sla_days",
                               reflection.DEFAULT_SLA_DAYS) or 15)
    delivered_only = bool(display.get("reflection_delivered_only", False))

    if not embedded:
        st.title("Reflection rate report")
    ui.hero(
        "Orders whose review never reflected",
        f"Every order with a review link where the reflection flag is still "
        f"false more than {sla_days} days on. Write the reason against the "
        "order ID; the checker signs it off last.",
    )

    main = bundle.main
    if main is None or main.empty:
        ui.empty_state("No order rows found in the MAIN tab.")
        return

    rows = reflection.report(main, sla_days, delivered_only)
    notes = reflection.load_notes()
    merged = reflection.merge_notes(rows, notes)
    stats = reflection.summarise(merged)

    _scope_note(sla_days, delivered_only)
    _store_note()

    if merged.empty:
        ui.callout(
            [f"No order has been waiting more than {sla_days} days with a "
             "review submitted and not reflected."],
            "green", title="Nothing outstanding",
        )
        return

    ui.render_kpis(
        [
            ui.kpi("Not reflected", stats["total"], unit="n", tone="neutral",
                   sub=f"past {sla_days} days · {stats['interns']} interns"),
            ui.kpi("Awaiting checker", stats["unchecked"], unit="n",
                   tone="red" if stats["unchecked"] else "green",
                   sub="rows the checker has not signed off",
                   help_text="This is the count shown as a red pill on the "
                             "Interns → Alerts tab."),
            ui.kpi("Checker verified", stats["checked"], unit="n",
                   tone="green" if stats["checked"] else "neutral",
                   sub=f"{_pct(stats['checked'], stats['total'])} of the list"),
            ui.kpi("No reason written", stats["no_remark"], unit="n",
                   tone="amber" if stats["no_remark"] else "green",
                   sub="executive has not filled the remark yet"),
            ui.kpi("Order value at risk", stats["value"], unit="Rs",
                   tone="neutral", sub="value of the unreflected orders"),
            ui.kpi("Oldest", stats["oldest_days"], unit="n", tone="neutral",
                   sub="days since the order date"),
        ],
        config,
    )

    view = _filters(merged)
    if view.empty:
        ui.empty_state("No rows match these filters.")
        return

    st.markdown("")
    _editor(view, merged, symbol)

    with st.expander(f"Export all {len(merged)} rows"):
        export = merged.rename(columns=EXPORT_RENAMES)
        keep = [c for c in EXPORT_RENAMES.values() if c in export.columns]
        ui.download_row({"reflection report": export[keep]},
                        excel_name="reflection-rate-report",
                        key_prefix="reflect_dl")


# ---------------------------------------------------------------------------
# Notes above the table
# ---------------------------------------------------------------------------
def _scope_note(sla_days: int, delivered_only: bool) -> None:
    scope = ("Delivered orders only. " if delivered_only
             else "Delivered and undelivered orders. ")
    ui.note(
        f"{scope}The workbook records an order date but no delivery date and "
        f"no review submission date, so the {sla_days}-day clock runs from the "
        "order date. Both the window and the delivered-only switch are on the "
        "Settings page."
    )


def _store_note() -> None:
    state = reflection.store_state()
    if state["durable"]:
        ui.callout([state["detail"]], "green", title="Notes are shared")
        return
    ui.callout(
        [state["detail"],
         "To make them permanent and shared, add a <code>gcp_service_account</code> "
         "block and an <code>INFLUENCER_SHEET_ID</code> (or "
         "<code>REFLECTION_SHEET_ID</code>) to the app secrets. Nothing about "
         "the audit workbook changes."],
        "amber", title="Remarks are not permanently stored yet",
    )
    if st.session_state.get("_reflect_error"):
        ui.note(f"Last store error: {st.session_state['_reflect_error']}")


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
def _filters(merged: pd.DataFrame) -> pd.DataFrame:
    left, mid, right = st.columns([1.1, 1.1, 1])
    with left:
        interns = sorted(
            v for v in merged["intern"].astype(str).str.strip().unique() if v
        )
        picked = st.multiselect("Intern", interns, key="reflect_intern")
    with mid:
        products = sorted(
            v for v in merged["product"].astype(str).str.strip().unique() if v
        )
        prod = st.multiselect("Product", products, key="reflect_product")
    with right:
        state = st.selectbox(
            "Checker", ["Awaiting checker", "All", "Verified"],
            key="reflect_state",
        )

    search_col, age_col = st.columns([1.4, 1])
    with search_col:
        term = st.text_input("Search order ID or ASIN", key="reflect_search",
                             placeholder="402-… or B0G…")
    with age_col:
        ages = pd.to_numeric(merged["age_days"], errors="coerce")
        top = int(ages.max()) if ages.notna().any() else 0
        floor = int(ages.min()) if ages.notna().any() else 0
        min_age = (
            st.slider("Minimum days old", floor, top, floor, key="reflect_age")
            if top > floor else floor
        )

    view = merged
    if picked:
        view = view[view["intern"].astype(str).str.strip().isin(picked)]
    if prod:
        view = view[view["product"].astype(str).str.strip().isin(prod)]
    if state == "Awaiting checker":
        view = view[~view["checked"].astype(bool)]
    elif state == "Verified":
        view = view[view["checked"].astype(bool)]
    if term.strip():
        needle = term.strip().lower()
        view = view[
            view["order_id"].astype(str).str.lower().str.contains(needle, na=False)
            | view["asin"].astype(str).str.lower().str.contains(needle, na=False)
        ]
    view = view[pd.to_numeric(view["age_days"], errors="coerce").fillna(-1) >= min_age]
    return view.reset_index(drop=True)


# ---------------------------------------------------------------------------
# The editable worklist
# ---------------------------------------------------------------------------
def _editor(view: pd.DataFrame, merged: pd.DataFrame, symbol: str) -> None:
    ui.section(
        f"Worklist — {len(view)} of {len(merged)} orders",
        "Fill the remark against the order, then the checker ticks the last "
        "column once the reason has been audited. Everything else is read "
        "from the sheet and cannot be edited here.",
    )

    src = view[[c for c in VIEW_COLUMNS if c in view.columns]].copy()
    src["order_date"] = pd.to_datetime(src["order_date"], errors="coerce").dt.date
    src["age_days"] = pd.to_numeric(src["age_days"], errors="coerce")
    src["remark"] = src["remark"].fillna("").astype(str)
    src["checked"] = src["checked"].fillna(False).astype(bool)

    edited = st.data_editor(
        src,
        width="stretch", hide_index=True, height=460, key="reflect_editor",
        column_config={
            "order_id": st.column_config.TextColumn("Order ID", disabled=True,
                                                    width="medium"),
            "asin": st.column_config.TextColumn("ASIN", disabled=True),
            "intern": st.column_config.TextColumn("Intern", disabled=True),
            "product": st.column_config.TextColumn("Product", disabled=True,
                                                   width="medium"),
            "order_date": st.column_config.DateColumn("Order date",
                                                      disabled=True),
            "age_days": st.column_config.NumberColumn("Days old", disabled=True,
                                                      format="%d"),
            "status": st.column_config.TextColumn("Amazon status",
                                                  disabled=True),
            "payment_state": st.column_config.TextColumn("Payment",
                                                         disabled=True),
            "remark": st.column_config.TextColumn(
                "Remark — reason for no reflection", width="large",
                help="Why has this order's review not reflected?"),
            "checked": st.column_config.CheckboxColumn(
                "Checker verified",
                help="Tick once the remark has been audited. Unticked rows "
                     "are the error count on the Alerts tab."),
        },
    )

    changes = reflection.diff_edits(view, edited)
    left, right = st.columns([1, 3])
    with left:
        save = st.button(
            f"Save {len(changes)} change(s)" if changes else "Save changes",
            type="primary", width="stretch", disabled=not changes,
            icon=":material/save:", key="reflect_save",
        )
    with right:
        if changes:
            ui.note(f"{len(changes)} row(s) edited and not yet saved.")

    if save and changes:
        written, message = reflection.save_notes(changes, _who())
        if written:
            st.success(message, icon=":material/check_circle:")
            st.rerun()
        else:
            st.error(message, icon=":material/error:")


def _who() -> str:
    try:
        return str(getattr(st.user, "email", "") or "") or "unknown"
    except Exception:
        return "unknown"


def _pct(part: int, whole: int) -> str:
    return f"{(100.0 * part / whole):.0f}%" if whole else "-"
