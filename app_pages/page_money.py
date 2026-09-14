"""Payments & Money: what has been paid, what is still owed, and what is at
risk because money went out before the deliverable came back.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common
import metrics
import ui

SCOPES = {
    "All time": "all",
    "Selected month": "month",
    "Last 90 days": "d90",
    "Last 30 days": "d30",
}


def render(bundle, config: dict) -> None:
    main = bundle.main
    symbol = config.get("display", {}).get("currency_symbol", "Rs")

    st.title("Payments & Money")
    ui.hero(
        "What has been paid, what is owed, and what is exposed",
        "Order value is what the company funds per order. Payment state is read "
        "from the free-text REVIEW PAYMENT column and folded into PAID, PENDING, "
        "CANCELLED, HOLD or UNKNOWN.",
    )
    if main.empty:
        ui.empty_state("No order rows found in the MAIN tab.")
        return

    scope_col, month_col = st.columns([1, 1])
    with scope_col:
        scope_label = st.selectbox("Scope", list(SCOPES.keys()), key="money_scope")
    scope = SCOPES[scope_label]
    with month_col:
        ym = common.month_picker(bundle, "Month (used when scope is a month)",
                                 key="money_month")

    period = _apply_scope(main, scope, ym)
    if period.empty:
        ui.empty_state("No orders in this scope.")
        return
    kpis = metrics.compute_kpis(period)

    # ---- the four money questions --------------------------------------
    ui.section(
        f"Money position — {scope_label.lower()}",
        f"{len(period):,} orders, {ui.fmt_money(kpis['order_value'], symbol)} of order value.",
    )
    ui.render_kpis(
        [
            ui.kpi("Order Value Funded", kpis["order_value"], unit="Rs", tone="neutral",
                   sub=f"{kpis['total_orders']} orders"),
            ui.kpi("Already Paid Out", kpis["paid_amt"], unit="Rs", tone="neutral",
                   sub=f"{kpis['paid_count']} orders marked Paid or Settled"),
            ui.kpi("", kpis["payment_pending_amt"], kpi_key="payment_pending_amt",
                   config=config, sub=f"{kpis['payment_pending_count']} orders we still owe"),
            ui.kpi("", kpis["payment_done_rate"], kpi_key="payment_done_rate",
                   config=config),
            ui.kpi("Payment Cancelled", kpis["payment_cancelled_amt"], unit="Rs",
                   tone="neutral",
                   sub=f"{kpis['payment_cancelled_count']} orders written off"),
            ui.kpi("Review Incentives", kpis["review_incentive_amt"], unit="Rs",
                   tone="neutral",
                   help_text="Sum of the REVIEW PRICE column, on top of the order value."),
        ],
        config,
    )

    ui.section(
        "Exposure — money out, deliverable not back",
        "These are the recovery conversations to have.",
    )
    ui.render_kpis(
        [
            ui.kpi("", kpis["paid_unreflected_amt"], kpi_key="paid_unreflected_amt",
                   config=config, sub=f"{kpis['paid_unreflected_count']} orders"),
            ui.kpi("", kpis["paid_undelivered_amt"], kpi_key="paid_undelivered_amt",
                   config=config, sub=f"{kpis['paid_undelivered_count']} orders"),
            ui.kpi("", kpis["unreconciled_amt"], kpi_key="unreconciled_amt",
                   config=config, sub=f"{kpis['unreconciled_count']} rows"),
            ui.kpi("Returns Value", kpis["returned_amt"], unit="Rs",
                   tone="amber" if kpis["returned"] else "green",
                   sub=f"{kpis['returned']} returned orders"),
            ui.kpi("Amazon Credited", kpis["amazon_value"], unit="Rs", tone="neutral",
                   help_text="Sum of the AMAZON PRICE column where it is filled in."),
            ui.kpi("Order vs Amazon Gap", kpis["price_gap_amt"], unit="Rs",
                   tone="neutral",
                   help_text="Order price minus Amazon price, summed over rows that have both."),
        ],
        config,
    )

    lines = common.headline_findings(kpis, config)
    money_lines = [
        line for line in lines
        if any(word in line for word in ("paid", "unpaid", "Amazon price", "returns"))
    ]
    if money_lines:
        ui.callout(money_lines, common.worst_tone(money_lines),
                   title="Money findings")

    # ---- trend ----------------------------------------------------------
    ui.section("Money by month", "Whole book, regardless of the scope above.")
    series = common.monthly_series(main)
    if not series.empty:
        labels = series["month_label"]
        fig = go.Figure()
        fig.add_bar(x=labels, y=series["order_value"], name="Order value funded",
                    marker_color="#2F6BFF")
        fig.add_bar(x=labels, y=series["paid_unreflected_amt"],
                    name="Paid but not reflected", marker_color="#BD2D46")
        fig.add_scatter(x=labels, y=series["payment_pending_amt"],
                        name="Payment pending", mode="lines+markers",
                        line=dict(color="#965708", width=2))
        fig.update_layout(barmode="group", yaxis_title=symbol)
        ui.show_chart(fig, height=330)

        table = series[[
            "month_label", "total_orders", "order_value", "paid_amt",
            "payment_pending_amt", "payment_pending_count",
            "paid_unreflected_amt", "paid_unreflected_count",
            "paid_undelivered_amt", "unreconciled_amt", "returned_amt",
        ]].rename(columns={
            "month_label": "Month", "total_orders": "Orders",
            "order_value": "Order value", "paid_amt": "Paid",
            "payment_pending_amt": "Pending", "payment_pending_count": "Pending #",
            "paid_unreflected_amt": "Paid, not reflected",
            "paid_unreflected_count": "Paid, not reflected #",
            "paid_undelivered_amt": "Paid, not delivered",
            "unreconciled_amt": "No Amazon price", "returned_amt": "Returns value",
        })
        st.dataframe(
            ui.grade_styler(table, {
                "Pending": "payment_pending_amt",
                "Paid, not reflected": "paid_unreflected_amt",
                "Paid, not delivered": "paid_undelivered_amt",
                "No Amazon price": "unreconciled_amt",
            }, config).format(
                {c: "{:,.0f}" for c in table.columns if c not in ("Month",)},
                na_rep="-",
            ),
            width="stretch", hide_index=True,
        )

    # ---- worklists -------------------------------------------------------
    ui.section("Worklists", "Each tab is an actionable list you can export.")
    tabs = st.tabs([
        "Payment pending", "Paid but not reflected", "Paid but not delivered",
        "No Amazon price", "Price mismatch", "By intern", "Payment text",
    ])

    pending = period[period["is_payment_pending"]]
    with tabs[0]:
        _worklist(
            pending, symbol,
            f"{len(pending)} orders worth {ui.fmt_money(pending['order_price'].sum(), symbol)} "
            "are neither Paid nor Cancelled.",
            "Nothing outstanding in this scope.",
            extra=["payment_raw", "age_days"],
        )

    paid_unreflected = period[period["is_paid"] & ~period["reflected"]]
    with tabs[1]:
        _worklist(
            paid_unreflected, symbol,
            f"{len(paid_unreflected)} orders worth "
            f"{ui.fmt_money(paid_unreflected['order_price'].sum(), symbol)} were paid but "
            "the review has not reflected. Split by whether a review was even submitted.",
            "Every paid order has a reflected review.",
            extra=["review_submitted", "age_days"],
        )
        if not paid_unreflected.empty:
            no_link = int((~paid_unreflected["review_submitted"]).sum())
            ui.chips([
                (f"{no_link} with no review submitted at all", "red"),
                (f"{len(paid_unreflected) - no_link} submitted but not live", "amber"),
            ])

    paid_undelivered = period[period["is_paid"] & period["not_delivered"]]
    with tabs[2]:
        _worklist(
            paid_undelivered, symbol,
            f"{len(paid_undelivered)} orders worth "
            f"{ui.fmt_money(paid_undelivered['order_price'].sum(), symbol)} were paid on "
            "orders that never reached the buyer.",
            "No payments on undelivered orders.",
            extra=["age_days"],
        )

    unreconciled = period[period["amazon_price"].isna()]
    with tabs[3]:
        _worklist(
            unreconciled, symbol,
            f"{len(unreconciled)} orders worth "
            f"{ui.fmt_money(unreconciled['order_price'].sum(), symbol)} have no AMAZON PRICE, "
            "so they cannot be reconciled against the Amazon settlement.",
            "Every order has an Amazon price.",
            extra=["age_days"],
        )

    tolerance = float(
        config.get("rules", {}).get("amazon_price_gap", {})
        .get("params", {}).get("tolerance", 50)
    )
    gap = period[period["price_gap"].notna() & (period["price_gap"].abs() > tolerance)]
    with tabs[4]:
        _worklist(
            gap, symbol,
            f"{len(gap)} orders differ from the Amazon price by more than "
            f"{ui.fmt_money(tolerance, symbol)} (tolerance set in Settings).",
            f"No order differs from its Amazon price by more than {ui.fmt_money(tolerance, symbol)}.",
            extra=["amazon_price", "price_gap"],
        )

    with tabs[5]:
        per_intern = metrics.by_dimension(period, "intern")
        if per_intern.empty:
            ui.empty_state("No intern rows in this scope.")
        else:
            view = per_intern[[
                "intern", "total_orders", "order_value", "paid_amt",
                "payment_pending_amt", "paid_unreflected_amt",
                "paid_undelivered_amt", "unreconciled_amt",
            ]].rename(columns={
                "intern": "Intern", "total_orders": "Orders",
                "order_value": "Order value", "paid_amt": "Paid",
                "payment_pending_amt": "Pending",
                "paid_unreflected_amt": "Paid, not reflected",
                "paid_undelivered_amt": "Paid, not delivered",
                "unreconciled_amt": "No Amazon price",
            }).sort_values("Paid, not reflected", ascending=False)
            st.dataframe(
                view.style.format(
                    {c: "{:,.0f}" for c in view.columns if c != "Intern"}, na_rep="-"
                ),
                width="stretch", hide_index=True,
            )

    with tabs[6]:
        ui.note(
            "The raw REVIEW PAYMENT text, and how each spelling was classified. "
            "Anything landing in UNKNOWN needs the wording cleaned up in the sheet."
        )
        raw = (
            period.groupby(["payment_raw", "payment_state"], as_index=False)
            .agg(Orders=("order_id", "size"), Value=("order_price", "sum"))
            .sort_values("Orders", ascending=False)
        )
        raw["payment_raw"] = raw["payment_raw"].replace("", "(blank)")
        ui.show_table(raw.rename(columns={
            "payment_raw": "Text in the sheet", "payment_state": "Read as",
        }))

    # ---- export ---------------------------------------------------------
    ui.section("Download")
    ui.download_row(
        {
            "payment pending": _worklist_frame(pending),
            "paid not reflected": _worklist_frame(paid_unreflected),
            "paid not delivered": _worklist_frame(paid_undelivered),
            "no amazon price": _worklist_frame(unreconciled),
        },
        excel_name="money-audit",
        key_prefix="money",
    )


def _apply_scope(main: pd.DataFrame, scope: str, ym: str) -> pd.DataFrame:
    if scope == "month":
        return metrics.slice_month(main, ym)
    if scope == "d90":
        return metrics.slice_last_days(main, 90)
    if scope == "d30":
        return metrics.slice_last_days(main, 30)
    return main


BASE_COLUMNS = [
    ("sheet_row", "Sheet row"), ("order_date", "Order date"),
    ("order_id", "Order ID"), ("intern", "Intern"), ("product", "Product"),
    ("status", "Amazon status"), ("payment_state", "Payment"),
    ("order_price", "Order price"),
]
EXTRA_LABELS = {
    "payment_raw": "Payment text", "age_days": "Age (days)",
    "review_submitted": "Review submitted", "amazon_price": "Amazon price",
    "price_gap": "Gap",
}


def _worklist_frame(df: pd.DataFrame, extra: list[str] | None = None) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    columns = list(BASE_COLUMNS) + [
        (col, EXTRA_LABELS.get(col, col)) for col in (extra or [])
    ]
    present = [(src, dst) for src, dst in columns if src in df.columns]
    out = df[[src for src, _ in present]].copy()
    out.columns = [dst for _, dst in present]
    if "Order date" in out.columns:
        out["Order date"] = pd.to_datetime(out["Order date"]).dt.strftime("%d %b %Y")
    return out.reset_index(drop=True)


def _worklist(
    df: pd.DataFrame, symbol: str, summary: str, empty_message: str,
    extra: list[str] | None = None,
) -> None:
    if df.empty:
        ui.callout([empty_message], "green")
        return
    ui.note(summary)
    view = _worklist_frame(df.sort_values("order_price", ascending=False), extra)
    numeric = [c for c in ("Order price", "Amazon price", "Gap") if c in view.columns]
    st.dataframe(
        view.style.format({c: "{:,.0f}" for c in numeric}, na_rep="-"),
        width="stretch", hide_index=True, height=420,
    )
