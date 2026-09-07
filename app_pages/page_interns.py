"""Intern Report: roster, per-intern scorecards and a single-intern drill-down."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common
import metrics
import ui

SCOPES = {"All time": "all", "Selected month": "month",
          "Last 90 days": "d90", "Last 30 days": "d30"}

SCORE_COLUMNS = {
    "Reflection %": "reflection_rate",
    "Submission %": "order_submission_rate",
    "Delivery %": "delivery_rate",
    "Checker %": "checker_verified_rate",
    "Cancel %": "cancellation_rate",
    "Return %": "return_rate",
}


def render(bundle, config: dict) -> None:
    main = bundle.main
    roster = bundle.roster
    display = config.get("display", {})
    symbol = display.get("currency_symbol", "Rs")
    min_orders = int(display.get("intern_min_orders_for_grading", 5) or 5)

    st.title("Intern Report")
    ui.note(
        "Scorecards are computed live from MAIN and joined to the "
        "'INTERN REPORT MANUAL' roster for status and tenure. The score weights "
        "reflection 35, submission 25, delivery 20, seller feedback 10, checker 10."
    )
    if main.empty:
        ui.empty_state("No order rows found in the MAIN tab.")
        return

    scope_col, month_col = st.columns([1, 1])
    with scope_col:
        scope_label = st.selectbox("Scope", list(SCOPES.keys()), key="interns_scope")
    with month_col:
        ym = common.month_picker(bundle, "Month (used when scope is a month)",
                                 key="interns_month")
    period = _apply_scope(main, SCOPES[scope_label], ym)
    if period.empty:
        ui.empty_state("No orders in this scope.")
        return

    scored = metrics.attach_roster(
        metrics.score_interns(period, min_orders=min_orders), roster
    )

    # ---- roster headline -------------------------------------------------
    ui.section("Roster")
    if roster is None or roster.empty:
        ui.empty_state("The 'INTERN REPORT MANUAL' tab could not be read.")
        status_counts = pd.Series(dtype=int)
    else:
        status_counts = roster["status"].value_counts()
        ui.render_kpis(
            [
                ui.kpi("On Roster", len(roster), unit="n", tone="neutral"),
                ui.kpi("Active", int(status_counts.get("Active", 0)), unit="n",
                       tone="green"),
                ui.kpi("Completed", int(status_counts.get("Completed", 0)), unit="n",
                       tone="neutral"),
                ui.kpi("Inactive", int(status_counts.get("Inactive", 0)), unit="n",
                       tone="neutral"),
                ui.kpi("Drop Out", int(status_counts.get("Drop Out", 0)), unit="n",
                       tone="amber"),
                ui.kpi("Terminated", int(status_counts.get("Terminate", 0)), unit="n",
                       tone="red"),
                ui.kpi("Placing Orders", period["intern"].nunique(), unit="n",
                       tone="neutral", sub=f"in {scope_label.lower()}"),
            ],
            config,
        )

    off_roster = scored[scored["roster_status"] == "Not on roster"]
    if not off_roster.empty:
        ui.callout(
            [
                f"<strong>Watch:</strong> {len(off_roster)} names placing orders are not on "
                f"the roster: {', '.join(sorted(off_roster['intern'].head(12)))}"
                + ("..." if len(off_roster) > 12 else "")
            ],
            "amber",
            title="Names not on the roster",
        )

    # ---- scorecards -------------------------------------------------------
    ui.section(
        f"Scorecards — {scope_label.lower()}",
        f"Interns with fewer than {min_orders} orders are listed last and marked "
        "as a small sample.",
    )
    if scored.empty:
        ui.empty_state("No intern activity in this scope.")
        return

    graded = scored[~scored["small_sample"]]
    if not graded.empty:
        grade_counts = graded["grade"].value_counts()
        ui.chips(
            [
                (f"A: {int(grade_counts.get('A', 0))}", "green"),
                (f"B: {int(grade_counts.get('B', 0))}", "green"),
                (f"C: {int(grade_counts.get('C', 0))}", "amber"),
                (f"D: {int(grade_counts.get('D', 0))}", "red"),
                (f"E: {int(grade_counts.get('E', 0))}", "red"),
                (f"small sample: {int(scored['small_sample'].sum())}", "grey"),
            ]
        )

    view = _score_view(scored)
    st.dataframe(
        ui.grade_styler(view, SCORE_COLUMNS, config).format(
            {
                **{c: "{:.1f}" for c in SCORE_COLUMNS},
                "Score": "{:.1f}", "Order value": "{:,.0f}",
                "Pending pay": "{:,.0f}",
            },
            na_rep="-",
        ),
        width="stretch", hide_index=True, height=460,
    )

    # ---- leaderboard chart ------------------------------------------------
    if not graded.empty:
        top = graded.head(15)
        fig = go.Figure(go.Bar(
            x=top["score"], y=top["intern"], orientation="h",
            marker_color=[
                "#059669" if s >= 90 else "#0F766E" if s >= 75
                else "#D97706" if s >= 60 else "#DC2626"
                for s in top["score"]
            ],
            text=top["score"].round(1), textposition="auto",
        ))
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(title="Top scores", xaxis_title="Score (0-100)",
                          xaxis_range=[0, 100])
        ui.show_chart(fig, height=max(280, 28 * len(top)), legend=False)

        bottom = graded.tail(10).sort_values("score")
        if len(graded) > 10:
            with st.expander("Lowest scores"):
                ui.show_table(_score_view(bottom))

    # ---- single intern drill-down ------------------------------------------
    ui.section("Drill into one intern")
    names = sorted(period["intern"].replace("", "(blank)").unique())
    who = st.selectbox("Intern", names, key="interns_pick")
    rows = period[period["intern"].replace("", "(blank)") == who]
    _intern_detail(who, rows, main, roster, config, symbol, bundle)

    # ---- roster table + export --------------------------------------------
    if roster is not None and not roster.empty:
        with st.expander("Full roster from the sheet"):
            ros = roster.copy()
            ros["Joining"] = ros["joining_date"].dt.strftime("%d %b %Y")
            ros["Leaving"] = ros["leaving_date"].dt.strftime("%d %b %Y")
            ui.show_table(
                ros.rename(columns={
                    "name": "Name", "status": "Status", "stipend": "Stipend",
                    "remark": "Remark",
                })[["Name", "Status", "Joining", "Leaving", "Stipend", "Remark"]]
            )

    ui.section("Download")
    ui.download_row(
        {"intern scorecards": view},
        excel_name="intern-report", key_prefix="interns",
    )


def _apply_scope(main: pd.DataFrame, scope: str, ym: str) -> pd.DataFrame:
    if scope == "month":
        return metrics.slice_month(main, ym)
    if scope == "d90":
        return metrics.slice_last_days(main, 90)
    if scope == "d30":
        return metrics.slice_last_days(main, 30)
    return main


def _score_view(scored: pd.DataFrame) -> pd.DataFrame:
    out = scored.rename(columns={
        "intern": "Intern", "roster_status": "Status",
        "total_orders": "Orders", "net_orders": "Net",
        "review_submitted": "Submitted", "review_reflected": "Reflected",
        "reflection_rate": "Reflection %", "order_submission_rate": "Submission %",
        "delivery_rate": "Delivery %", "checker_verified_rate": "Checker %",
        "cancellation_rate": "Cancel %", "return_rate": "Return %",
        "order_value": "Order value", "payment_pending_amt": "Pending pay",
        "score": "Score", "grade": "Grade", "small_sample": "Small sample",
    })
    columns = [
        "Intern", "Status", "Orders", "Net", "Submitted", "Reflected",
        "Reflection %", "Submission %", "Delivery %", "Checker %",
        "Cancel %", "Return %", "Order value", "Pending pay",
        "Score", "Grade", "Small sample",
    ]
    return out[[c for c in columns if c in out.columns]].reset_index(drop=True)


def _intern_detail(
    who: str, rows: pd.DataFrame, main: pd.DataFrame,
    roster: pd.DataFrame, config: dict, symbol: str, bundle,
) -> None:
    if rows.empty:
        ui.empty_state("No orders for this intern in the selected scope.")
        return
    kpis = metrics.compute_kpis(rows)

    chips: list[tuple[str, str]] = []
    if roster is not None and not roster.empty:
        match = roster[roster["name"].str.casefold() == who.casefold()]
        if not match.empty:
            record = match.iloc[0]
            chips.append((f"Status: {record['status']}", "grey"))
            if pd.notna(record["joining_date"]):
                chips.append((f"Joined {record['joining_date']:%d %b %Y}", "grey"))
            if pd.notna(record["leaving_date"]):
                chips.append((f"Left {record['leaving_date']:%d %b %Y}", "grey"))
            if pd.notna(record["stipend"]):
                chips.append((f"Stipend {ui.fmt_money(record['stipend'], symbol)}", "grey"))
        else:
            chips.append(("Not on the roster", "amber"))
    chips.append((f"{rows['ym'].nunique()} active months", "grey"))
    ui.chips(chips)

    ui.render_kpis(
        [
            ui.kpi("Orders", kpis["total_orders"], unit="n", tone="neutral"),
            ui.kpi("Net Orders", kpis["net_orders"], unit="n", tone="neutral"),
            ui.kpi("", kpis["reflection_rate"], kpi_key="reflection_rate", config=config,
                   sub=f"{kpis['review_reflected']} of {kpis['review_submitted']}"),
            ui.kpi("", kpis["order_submission_rate"], kpi_key="order_submission_rate",
                   config=config),
            ui.kpi("", kpis["delivery_rate"], kpi_key="delivery_rate", config=config),
            ui.kpi("", kpis["cancellation_rate"], kpi_key="cancellation_rate",
                   config=config, sub=f"{kpis['not_delivered']} not delivered"),
            ui.kpi("", kpis["return_rate"], kpi_key="return_rate", config=config,
                   sub=f"{kpis['returned']} returned"),
            ui.kpi("", kpis["checker_verified_rate"], kpi_key="checker_verified_rate",
                   config=config, sub=f"{kpis['checker_pending']} pending"),
            ui.kpi("Order Value", kpis["order_value"], unit="Rs", tone="neutral"),
            ui.kpi("", kpis["payment_pending_amt"], kpi_key="payment_pending_amt",
                   config=config, sub=f"{kpis['payment_pending_count']} unpaid"),
            ui.kpi("", kpis["paid_unreflected_amt"], kpi_key="paid_unreflected_amt",
                   config=config, sub=f"{kpis['paid_unreflected_count']} orders"),
        ],
        config,
    )

    lines = common.headline_findings(kpis, config)
    if lines:
        ui.callout(lines[:5], common.worst_tone(lines[:5]),
                   title=f"Findings for {who}")

    monthly = rows.groupby("ym", as_index=False).agg(
        Orders=("order_id", "size"),
        Net=("delivered", "sum"),
        Submitted=("review_submitted", "sum"),
        Reflected=("reflected", "sum"),
        Value=("order_price", "sum"),
    )
    if len(monthly) > 1:
        fig = go.Figure()
        fig.add_bar(x=monthly["ym"], y=monthly["Orders"], name="Orders",
                    marker_color="#0F766E")
        fig.add_scatter(x=monthly["ym"], y=monthly["Reflected"], name="Reflected",
                        mode="lines+markers", line=dict(color="#2563EB", width=2))
        fig.update_layout(title=f"{who} by month", yaxis_title="Orders")
        ui.show_chart(fig, height=270)

    _, summary = common.audit_results(bundle, config)
    detail = common.attach_severity(rows, summary)
    detail_view = detail.copy()
    detail_view["Order date"] = detail_view["order_date"].dt.strftime("%d %b %Y")
    detail_view = detail_view.rename(columns={
        "sheet_row": "Sheet row", "order_id": "Order ID", "product": "Product",
        "status": "Amazon status", "payment_state": "Payment",
        "order_price": "Order price", "rules": "Exceptions",
    })[[
        "Sheet row", "Order date", "Order ID", "Product", "Amazon status",
        "Payment", "Order price", "severity", "Exceptions",
    ]]
    st.dataframe(
        ui.severity_styler(detail_view).format({"Order price": "{:,.0f}"}, na_rep="-"),
        width="stretch", hide_index=True, height=360,
    )
