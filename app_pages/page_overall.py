"""Overall Audit Report: the workbook's own monthly aggregate, graded,
recomputed from MAIN, and diffed so any drift between the two is visible.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common
import metrics
import ui
from settings_store import grade

MONTH_TABLE_COLUMNS = [
    ("month_label", "Month"),
    ("total_orders", "Total orders"),
    ("net_orders", "Net orders"),
    ("not_delivered", "Cancelled"),
    ("cancellation_rate", "Cancellation %"),
    ("returned", "Returned"),
    ("return_rate", "Return %"),
    ("review_submitted", "Submitted"),
    ("order_submission_rate", "Submission %"),
    ("review_reflected", "Reflected"),
    ("review_not_reflected", "Not reflected"),
    ("reflection_rate", "Reflection %"),
    ("seller_feedback", "Seller FB"),
    ("seller_feedback_missing", "Seller FB missing"),
    ("checker_pending", "Checker pending"),
    ("order_value", "Order value"),
]

GRADED_COLUMNS = {
    "Cancellation %": "cancellation_rate",
    "Return %": "return_rate",
    "Submission %": "order_submission_rate",
    "Reflection %": "reflection_rate",
}


def render(bundle, config: dict, embedded: bool = False) -> None:
    main = bundle.main
    if not embedded:
        st.title("Overall Audit Report")
    ui.note(
        "Month-by-month summary for the whole book. The app recomputes every "
        "figure from MAIN and compares it with the workbook's own "
        "'Overall Audit Report' tab."
    )
    if main.empty:
        ui.empty_state("No order rows found in the MAIN tab.")
        return

    series = common.monthly_series(main)
    if series.empty:
        ui.empty_state("No dated orders to summarise.")
        return

    all_kpis = metrics.compute_kpis(main)

    # ---- whole-book headline -------------------------------------------
    ui.section("All months combined")
    ui.render_kpis(
        [
            ui.kpi("Months Covered", series["ym"].nunique(), unit="n", tone="neutral",
                   sub=f"{series['month_label'].iloc[0]} to {series['month_label'].iloc[-1]}"),
            ui.kpi("Total Orders", all_kpis["total_orders"], unit="n", tone="neutral"),
            ui.kpi("Net Orders", all_kpis["net_orders"], unit="n", tone="neutral"),
            ui.kpi("", all_kpis["cancellation_rate"], kpi_key="cancellation_rate",
                   config=config, sub=f"{all_kpis['not_delivered']} not delivered"),
            ui.kpi("", all_kpis["reflection_rate"], kpi_key="reflection_rate",
                   config=config,
                   sub=f"{all_kpis['review_reflected']} of {all_kpis['review_submitted']}"),
            ui.kpi("", all_kpis["order_submission_rate"], kpi_key="order_submission_rate",
                   config=config),
            ui.kpi("", all_kpis["return_rate"], kpi_key="return_rate", config=config,
                   sub=f"{all_kpis['returned']} returned"),
            ui.kpi("", all_kpis["seller_feedback_rate"], kpi_key="seller_feedback_rate",
                   config=config),
            ui.kpi("", all_kpis["checker_verified_rate"], kpi_key="checker_verified_rate",
                   config=config, sub=f"{all_kpis['checker_pending']} pending"),
            ui.kpi("Order Value", all_kpis["order_value"], unit="Rs", tone="neutral"),
        ],
        config,
    )

    # ---- graded monthly matrix -----------------------------------------
    ui.section(
        "Monthly matrix (computed live from MAIN)",
        "Colour follows the limits on the Settings page.",
    )
    table = _month_table(series)
    st.dataframe(
        ui.grade_styler(table, GRADED_COLUMNS, config).format(
            {
                "Cancellation %": "{:.1f}", "Return %": "{:.1f}",
                "Submission %": "{:.1f}", "Reflection %": "{:.1f}",
                "Order value": "{:,.0f}",
            },
            na_rep="-",
        ),
        width="stretch", hide_index=True,
    )

    _month_flags(series, config)

    # ---- charts ---------------------------------------------------------
    ui.section("Trends across every month")
    labels = series["month_label"]
    fig = go.Figure()
    fig.add_bar(x=labels, y=series["net_orders"], name="Net orders", marker_color="#0A84FF")
    fig.add_bar(x=labels, y=series["not_delivered"], name="Not delivered", marker_color="#FF3B30")
    fig.update_layout(barmode="stack", title="Net vs not delivered", yaxis_title="Orders")
    ui.show_chart(fig, height=310)

    col_a, col_b = st.columns(2)
    with col_a:
        fig = go.Figure()
        fig.add_scatter(x=labels, y=series["reflection_rate"], name="Reflection %",
                        mode="lines+markers", line=dict(color="#0A84FF", width=2.5))
        ui.threshold_bands(fig, config["kpis"].get("reflection_rate", {}),
                           config.get("display", {}), series["reflection_rate"])
        fig.update_layout(title="Reflection rate", yaxis_title="%")
        ui.show_chart(fig, height=290)
    with col_b:
        fig = go.Figure()
        fig.add_scatter(x=labels, y=series["cancellation_rate"], name="Cancellation %",
                        mode="lines+markers", line=dict(color="#FF3B30", width=2.5))
        ui.threshold_bands(fig, config["kpis"].get("cancellation_rate", {}),
                           config.get("display", {}), series["cancellation_rate"])
        fig.update_layout(title="Cancellation rate", yaxis_title="%")
        ui.show_chart(fig, height=290)

    # ---- reconciliation against the sheet tab --------------------------
    ui.section(
        "Reconciliation with the workbook's own tab",
        "Any non-zero difference means the sheet's aggregate has drifted from MAIN.",
    )
    variance = metrics.audit_variance(main, bundle.overall_audit)
    if variance.empty:
        ui.empty_state(
            "The 'Overall Audit Report' tab could not be read, or has no rows "
            "that overlap the months in MAIN."
        )
    else:
        mismatches = variance[~variance["match"]]
        checks = len(variance)
        if mismatches.empty:
            ui.callout(
                [
                    f"All {checks} checks tie exactly. The app's definitions match the "
                    "workbook's for every month: net orders, cancellations, "
                    "submissions, reflections and seller feedback."
                ],
                "green",
                title="Fully reconciled",
            )
        else:
            ui.callout(
                [
                    f"{len(mismatches)} of {checks} checks differ. The app figure is "
                    "recomputed from MAIN and is the one to trust; the sheet cell is "
                    "probably a stale formula or a hard-coded value."
                ],
                "red",
                title="Drift detected",
            )
            ui.show_table(
                mismatches.rename(columns={
                    "month": "Month", "metric": "Metric",
                    "app_value": "App (from MAIN)", "sheet_value": "Sheet tab",
                    "difference": "Difference",
                })[["Month", "Metric", "App (from MAIN)", "Sheet tab", "Difference"]]
            )

        with st.expander("Show all reconciliation checks"):
            ui.show_table(
                variance.assign(Status=variance["match"].map({True: "tie", False: "differs"}))
                .rename(columns={
                    "month": "Month", "metric": "Metric",
                    "app_value": "App (from MAIN)", "sheet_value": "Sheet tab",
                    "difference": "Difference",
                })[["Month", "Metric", "App (from MAIN)", "Sheet tab",
                    "Difference", "Status"]]
            )

    # ---- the raw sheet tab ---------------------------------------------
    if bundle.overall_audit is not None and not bundle.overall_audit.empty:
        with st.expander("The 'Overall Audit Report' tab as it stands in the sheet"):
            raw = bundle.overall_audit.rename(columns={
                "month_name": "Month", "year": "Year", "total_orders": "Total Orders",
                "net_orders": "Net Orders", "cancelled": "Cancelled",
                "cancellation_rate": "Cancellation %",
                "review_submitted": "Review Submitted",
                "review_reflected": "Review Reflected",
                "review_not_reflected": "Review Not Reflected",
                "reflection_rate": "Reflection Rate %",
                "order_submission_rate": "Order Submission %",
                "seller_feedback": "Seller Feedback",
                "seller_feedback_missing": "Seller FB Not Submitted",
            })
            keep = [c for c in [
                "Month", "Year", "Total Orders", "Net Orders", "Cancelled",
                "Cancellation %", "Review Submitted", "Review Reflected",
                "Review Not Reflected", "Reflection Rate %", "Order Submission %",
                "Seller Feedback", "Seller FB Not Submitted",
            ] if c in raw.columns]
            ui.show_table(raw[keep])

    # ---- export ---------------------------------------------------------
    ui.section("Download")
    ui.download_row(
        {
            "monthly matrix": table,
            "reconciliation": variance,
        },
        excel_name="overall-audit",
        key_prefix="overall",
    )
    ui.source_note(
        f"MAIN tab, {len(main):,} rows. Pulled {bundle.loaded_at:%d %b %Y %H:%M}."
    )


def _month_table(series: pd.DataFrame) -> pd.DataFrame:
    present = [(src, dst) for src, dst in MONTH_TABLE_COLUMNS if src in series.columns]
    out = series[[src for src, _ in present]].copy()
    out.columns = [dst for _, dst in present]
    return out.reset_index(drop=True)


def _month_flags(series: pd.DataFrame, config: dict) -> None:
    """Call out the months that fall in a red band on any headline KPI."""
    specs = config.get("kpis", {})
    watch = []
    for _, row in series.iterrows():
        reds = [
            name
            for name, key in (
                ("reflection", "reflection_rate"),
                ("cancellation", "cancellation_rate"),
                ("returns", "return_rate"),
                ("submission", "order_submission_rate"),
            )
            if grade(row.get(key), specs.get(key, {})) == "red"
        ]
        if reds:
            watch.append(f"<strong>{row['month_label']}</strong>: red on {', '.join(reds)}")
    if watch:
        ui.callout(watch, "red", title="Months in a red band")
    else:
        ui.callout(["No month is in a red band on the headline KPIs."], "green")
