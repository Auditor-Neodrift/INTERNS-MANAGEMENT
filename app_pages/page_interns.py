"""Interns: who is active now, what they produced, and who is due a review.

Tabs: Active now | All interns | Daily activity | Tenure alerts | Scorecards
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common
import metrics
import ui

STATUS_TONE = {
    "active": "green", "completed": "grey", "terminate": "red",
    "terminated": "red", "drop out": "red", "dropout": "red",
    "inactive": "grey", "not on roster": "amber",
}

ROSTER_COLUMNS = [
    ("name", "Intern"),
    ("status", "Status"),
    ("joining_date", "Joining date"),
    ("leaving_date", "End date"),
    ("tenure_days_served", "Tenure (days)"),
    ("stipend", "Stipend"),
    ("orders", "Orders completed"),
    ("cancelled", "Cancelled"),
    ("undelivered", "Undelivered"),
    ("reviews_submitted", "Reviews submitted"),
    ("reviews_reflected", "Reviews reflected"),
    ("reflection_rate", "Reflection %"),
    ("orders_per_day", "Orders/active day"),
]


def render(bundle, config: dict) -> None:
    main = bundle.main
    display = config.get("display", {})
    symbol = display.get("currency_symbol", "Rs")
    tenure_days = int(display.get("tenure_days", 30) or 30)
    idle_days = int(display.get("intern_idle_days", 3) or 3)
    cancel_pct = float(display.get("intern_cancel_alert_pct", 30.0) or 30.0)

    st.title("Interns")
    ui.hero(
        "Who is working right now, and what they have produced",
        "Tenure and stipend come from the roster tab; orders, cancellations and "
        "reviews are counted live from MAIN. Cancelled and undelivered are kept "
        "apart so a real cancellation is never confused with a parcel in transit.",
    )
    if main.empty:
        ui.empty_state("No order rows found in the MAIN tab.")
        return

    interns = metrics.intern_table(
        main, bundle.roster, tenure_days=tenure_days,
        idle_days=idle_days, cancel_pct=cancel_pct,
    )
    alerts = metrics.intern_alerts(interns, tenure_days, idle_days, cancel_pct)
    active = interns[interns["is_active"]]
    urgent = alerts[alerts["severity"] == "red"] if not alerts.empty else alerts

    if not alerts.empty:
        _alert_summary(alerts)

    tabs = st.tabs([
        f"Active now ({len(active)})", "All interns", "Daily activity",
        f"Alerts ({len(alerts)})", "Scorecards",
    ])

    with tabs[0]:
        _active_tab(active, interns, main, config, symbol, tenure_days, urgent)
    with tabs[1]:
        _roster_tab(interns, config, symbol)
    with tabs[2]:
        _daily_tab(main, active, config)
    with tabs[3]:
        _alerts_tab(alerts, tenure_days, idle_days, cancel_pct)
    with tabs[4]:
        _scorecard_tab(bundle, main, config, display)


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
def _alert_summary(alerts: pd.DataFrame) -> None:
    """Category chips only - the urgent detail lives in the bottom-right
    notifications and the Alerts tab, so the top of the page stays readable."""
    counts = alerts["kind"].value_counts()
    ui.chips([
        (f"{int(counts.get('clerical', 0))} clerical errors",
         "red" if counts.get("clerical") else "green"),
        (f"{int(counts.get('idle', 0))} active with no orders",
         "red" if counts.get("idle") else "green"),
        (f"{int(counts.get('cancellation', 0))} high cancellation",
         "red" if counts.get("cancellation") else "green"),
        (f"{int(counts.get('tenure', 0))} tenure reviews due",
         "amber" if counts.get("tenure") else "green"),
    ])


# ---------------------------------------------------------------------------
# Active now
# ---------------------------------------------------------------------------
def _active_tab(
    active: pd.DataFrame, interns: pd.DataFrame, main: pd.DataFrame,
    config: dict, symbol: str, tenure_days: int, urgent: pd.DataFrame,
) -> None:
    if active.empty:
        ui.empty_state("Nobody on the roster is marked Active.")
        return

    last7 = metrics.slice_last_days(main, 7)
    recent = metrics.intern_daily(last7)
    active_names = set(active["name"].str.casefold())
    recent_active = (
        recent[recent["intern"].str.casefold().isin(active_names)]
        if not recent.empty else recent
    )
    orders_7d = int(recent_active["orders"].sum()) if not recent_active.empty else 0
    stipend_total = float(active["stipend"].fillna(0).sum())

    ui.render_kpis(
        [
            ui.kpi("Active Interns", len(active), unit="n", tone="green",
                   sub=f"of {len(interns)} on record"),
            ui.kpi("Orders Last 7 Days", orders_7d, unit="n", tone="neutral",
                   sub="by active interns"),
            ui.kpi("Orders This Tenure", int(active["orders"].sum()), unit="n",
                   tone="neutral"),
            ui.kpi("Reviews Submitted", int(active["reviews_submitted"].sum()),
                   unit="n", tone="neutral"),
            ui.kpi("Cancelled", int(active["cancelled"].sum()), unit="n",
                   tone="red" if active["cancelled"].sum() else "green"),
            ui.kpi("Undelivered", int(active["undelivered"].sum()), unit="n",
                   tone="amber" if active["undelivered"].sum() else "green"),
            ui.kpi("Tenure Elapsed", int(active["tenure_elapsed"].sum()), unit="n",
                   tone="amber" if active["tenure_elapsed"].any() else "green",
                   sub=f"past {tenure_days} days"),
            ui.kpi("Stipend Committed", stipend_total, unit="Rs", tone="neutral",
                   sub=f"{int(active['stipend'].notna().sum())} of {len(active)} recorded"),
        ],
        config,
    )

    flagged = (
        set(urgent["name"]) if urgent is not None and not urgent.empty else set()
    )
    ui.section(
        "Work update per active intern",
        "End date is the date actually recorded on the roster - blank means none "
        "is set. An Active intern with an end date is a clerical error."
        if flagged else None,
    )
    view = _roster_view(active, symbol)
    st.dataframe(
        ui.grade_styler(view, {
            "Reflection %": "reflection_rate",
        }, config).format(
            {"Reflection %": "{:.1f}", "Orders/active day": "{:.2f}"}, na_rep="-"
        ),
        width="stretch", hide_index=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        fig = go.Figure()
        fig.add_bar(x=active["name"], y=active["delivered"], name="Delivered",
                    marker_color="#2E9E5B")
        fig.add_bar(x=active["name"], y=active["undelivered"], name="Undelivered",
                    marker_color="#E08A17")
        fig.add_bar(x=active["name"], y=active["cancelled"], name="Cancelled",
                    marker_color="#E0503C")
        fig.update_layout(barmode="stack", title="Order outcome by intern",
                          yaxis_title="Orders")
        ui.show_chart(fig, height=320)
    with col_b:
        fig = go.Figure()
        fig.add_bar(x=active["name"], y=active["orders"], name="Orders",
                    marker_color="#1B1B1E")
        fig.add_bar(x=active["name"], y=active["reviews_submitted"],
                    name="Reviews submitted", marker_color="#B9A7F5")
        fig.update_layout(barmode="group", title="Orders vs reviews submitted",
                          yaxis_title="Count")
        ui.show_chart(fig, height=320)

    ui.section("Days into tenure")
    prog = active.sort_values("days_since_joining", ascending=False)
    fig = go.Figure(go.Bar(
        x=prog["days_since_joining"], y=prog["name"], orientation="h",
        marker_color=["#E0503C" if e else "#1B1B1E" for e in prog["tenure_elapsed"]],
        text=prog["days_since_joining"].astype("Int64"), textposition="auto",
    ))
    fig.add_vline(x=tenure_days, line_dash="dash", line_color="#93939E")
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(xaxis_title=f"Days since joining (dashed line = {tenure_days})")
    ui.show_chart(fig, height=max(240, 34 * len(prog)), legend=False)


# ---------------------------------------------------------------------------
# All interns
# ---------------------------------------------------------------------------
def _roster_tab(interns: pd.DataFrame, config: dict, symbol: str) -> None:
    statuses = sorted(interns["status"].dropna().unique())
    col_a, col_b = st.columns([2, 1])
    with col_a:
        picked = st.multiselect("Status", statuses, default=[], key="int_status")
    with col_b:
        search = st.text_input("Search name", key="int_search", placeholder="e.g. Bhavya")

    view_src = interns.copy()
    if picked:
        view_src = view_src[view_src["status"].isin(picked)]
    if search.strip():
        view_src = view_src[
            view_src["name"].str.contains(search.strip(), case=False, na=False)
        ]

    counts = interns["status"].value_counts()
    ui.chips([
        (f"{status}: {count}", STATUS_TONE.get(str(status).strip().casefold(), "grey"))
        for status, count in counts.items()
    ])

    ui.render_kpis(
        [
            ui.kpi("Interns Shown", len(view_src), unit="n", tone="neutral"),
            ui.kpi("Orders", int(view_src["orders"].sum()), unit="n", tone="neutral"),
            ui.kpi("Cancelled", int(view_src["cancelled"].sum()), unit="n",
                   tone="red" if view_src["cancelled"].sum() else "green"),
            ui.kpi("Undelivered", int(view_src["undelivered"].sum()), unit="n",
                   tone="amber" if view_src["undelivered"].sum() else "green"),
            ui.kpi("Reviews Submitted", int(view_src["reviews_submitted"].sum()),
                   unit="n", tone="neutral"),
            ui.kpi("Stipend Recorded", float(view_src["stipend"].fillna(0).sum()),
                   unit="Rs", tone="neutral",
                   sub=f"{int(view_src['stipend'].notna().sum())} of {len(view_src)} rows"),
        ],
        config,
    )

    if view_src.empty:
        ui.empty_state("No interns match those filters.")
        return

    view = _roster_view(view_src, symbol)
    st.dataframe(
        ui.grade_styler(view, {"Reflection %": "reflection_rate"}, config).format(
            {"Reflection %": "{:.1f}", "Orders/active day": "{:.2f}"}, na_rep="-"
        ),
        width="stretch", hide_index=True, height=520,
    )
    missing = int(view_src["stipend"].isna().sum())
    if missing:
        ui.callout(
            [
                f"{missing} of {len(view_src)} interns shown have no stipend recorded "
                "in the roster tab, so the stipend totals above understate the real cost."
            ],
            "amber",
        )
    ui.download_row({"interns": view}, excel_name="interns", key_prefix="interns-all")


# ---------------------------------------------------------------------------
# Daily activity
# ---------------------------------------------------------------------------
def _daily_tab(main: pd.DataFrame, active: pd.DataFrame, config: dict) -> None:
    ui.note("How many orders each intern placed on each day.")
    all_names = sorted(main["intern"].replace("", pd.NA).dropna().unique())
    default = [n for n in all_names if n in set(active["name"])][:6]

    col_a, col_b = st.columns([2, 1])
    with col_a:
        chosen = st.multiselect("Interns", all_names, default=default, key="daily_who")
    with col_b:
        window = st.selectbox("Window", ["Last 14 days", "Last 30 days",
                                         "Last 90 days", "All time"],
                              index=1, key="daily_window")

    days = {"Last 14 days": 14, "Last 30 days": 30, "Last 90 days": 90}.get(window)
    scope = metrics.slice_last_days(main, days) if days else main
    daily = metrics.intern_daily(scope, chosen or None)

    if daily.empty:
        ui.empty_state("No orders in this window for the selected interns.")
        return

    ui.render_kpis(
        [
            ui.kpi("Orders", int(daily["orders"].sum()), unit="n", tone="neutral"),
            ui.kpi("Active Days", int(daily["day"].nunique()), unit="n", tone="neutral"),
            ui.kpi("Interns", int(daily["intern"].nunique()), unit="n", tone="neutral"),
            ui.kpi("Busiest Day", int(daily.groupby("day")["orders"].sum().max()),
                   unit="n", tone="neutral", sub="orders in one day"),
            ui.kpi("Cancelled", int(daily["cancelled"].sum()), unit="n",
                   tone="red" if daily["cancelled"].sum() else "green"),
            ui.kpi("Undelivered", int(daily["undelivered"].sum()), unit="n",
                   tone="amber" if daily["undelivered"].sum() else "green"),
        ],
        config,
    )

    fig = go.Figure()
    for name in sorted(daily["intern"].unique()):
        part = daily[daily["intern"] == name].sort_values("day")
        fig.add_scatter(x=part["day"], y=part["orders"], name=name,
                        mode="lines+markers", line=dict(width=2))
    fig.update_layout(title="Orders per day", yaxis_title="Orders")
    ui.show_chart(fig, height=350)

    totals = (
        daily.groupby("day", as_index=False)
        .agg(orders=("orders", "sum"), cancelled=("cancelled", "sum"),
             undelivered=("undelivered", "sum"))
        .sort_values("day")
    )
    fig = go.Figure()
    fig.add_bar(x=totals["day"], y=totals["orders"], name="Orders",
                marker_color="#1B1B1E")
    fig.add_bar(x=totals["day"], y=totals["undelivered"], name="Undelivered",
                marker_color="#E08A17")
    fig.add_bar(x=totals["day"], y=totals["cancelled"], name="Cancelled",
                marker_color="#E0503C")
    fig.update_layout(barmode="overlay", title="Daily totals", yaxis_title="Orders")
    fig.update_traces(opacity=0.85)
    ui.show_chart(fig, height=300)

    table = daily.rename(columns={
        "day": "Day", "intern": "Intern", "orders": "Orders",
        "delivered": "Delivered", "cancelled": "Cancelled",
        "undelivered": "Undelivered", "reviews_submitted": "Reviews",
        "value": "Order value",
    })
    ui.show_table(table, height=420)
    ui.download_row({"daily activity": table}, excel_name="intern-daily",
                    key_prefix="daily")


# ---------------------------------------------------------------------------
# Tenure alerts
# ---------------------------------------------------------------------------
ALERT_GROUPS = [
    ("clerical", "Clerical errors",
     "The roster contradicts itself. Fix these in the sheet first - every other "
     "intern number is derived from these dates."),
    ("idle", "Not ordering",
     "Active for longer than the grace period with no orders placed."),
    ("cancellation", "High cancellation",
     "Cancelled plus undelivered above the configured share of their orders."),
    ("tenure", "Tenure review due",
     "Past the tenure window and still marked Active."),
]


def _alerts_tab(alerts: pd.DataFrame, tenure_days: int, idle_days: int,
                cancel_pct: float) -> None:
    if alerts.empty:
        ui.callout(
            ["No clerical errors, idle interns, high cancellation rates or "
             "overdue tenure reviews."],
            "green", title="Nothing to action",
        )
        return

    ui.note(
        f"Thresholds: tenure {tenure_days} days · idle after {idle_days} days "
        f"with no orders · not-delivered above {cancel_pct:g}%. "
        "All three are editable on the Settings page."
    )

    counts = alerts["kind"].value_counts()
    labels = {"all": f"All ({len(alerts)})"}
    for kind, title, _ in ALERT_GROUPS:
        labels[kind] = f"{title} ({int(counts.get(kind, 0))})"

    keys = ["all"] + [k for k, _, _ in ALERT_GROUPS]
    picked = st.segmented_control(
        "Alert type", keys, format_func=lambda k: labels[k],
        default="all", key="alert_kind", label_visibility="collapsed",
    ) or "all"

    if picked == "all":
        for kind, title, blurb in ALERT_GROUPS:
            sub = alerts[alerts["kind"] == kind]
            if sub.empty:
                continue
            ui.section(f"{title} ({len(sub)})", blurb)
            _render_alert_cards(sub)
        empty = [t for k, t, _ in ALERT_GROUPS if int(counts.get(k, 0)) == 0]
        if empty:
            ui.callout([f"Clear: {', '.join(empty)}."], "green")
    else:
        title, blurb = next((t, b) for k, t, b in ALERT_GROUPS if k == picked)
        sub = alerts[alerts["kind"] == picked]
        ui.section(f"{title} ({len(sub)})", blurb)
        if sub.empty:
            ui.callout([f"No {title.lower()} right now."], "green")
        else:
            _render_alert_cards(sub)

    table = alerts.rename(columns={
        "name": "Intern", "label": "Alert", "severity": "Severity",
        "message": "What is wrong", "detail": "Context", "status": "Status",
        "orders": "Orders", "cancelled": "Cancelled",
        "undelivered": "Undelivered", "reviews_submitted": "Reviews",
        "not_delivered_rate": "Not delivered %",
    })[["Intern", "Alert", "Severity", "What is wrong", "Context", "Status",
        "Orders", "Cancelled", "Undelivered", "Reviews", "Not delivered %"]]
    with st.expander(f"All {len(alerts)} alerts as a table"):
        ui.show_table(table, height=400)
        ui.download_row({"intern alerts": table}, excel_name="intern-alerts",
                        key_prefix="alerts")


def _render_alert_cards(sub: pd.DataFrame) -> None:
    ui.alert_grid(
        [
            {"title": row["name"], "message": row["message"],
             "meta": row["detail"], "tone": row["severity"]}
            for _, row in sub.iterrows()
        ],
        columns=3,
    )


# ---------------------------------------------------------------------------
# Scorecards (weighted score + drill-down)
# ---------------------------------------------------------------------------
def _scorecard_tab(bundle, main: pd.DataFrame, config: dict, display: dict) -> None:
    min_orders = int(display.get("intern_min_orders_for_grading", 5) or 5)
    ui.note(
        "Weighted 0-100 score: reflection 35, submission 25, delivery 20, "
        "seller feedback 10, checker sign-off 10."
    )
    scored = metrics.attach_roster(
        metrics.score_interns(main, min_orders=min_orders), bundle.roster
    )
    if scored.empty:
        ui.empty_state("No intern activity to score.")
        return

    graded = scored[~scored["small_sample"]]
    if not graded.empty:
        counts = graded["grade"].value_counts()
        ui.chips([
            (f"A: {int(counts.get('A', 0))}", "green"),
            (f"B: {int(counts.get('B', 0))}", "green"),
            (f"C: {int(counts.get('C', 0))}", "amber"),
            (f"D: {int(counts.get('D', 0))}", "red"),
            (f"E: {int(counts.get('E', 0))}", "red"),
            (f"small sample: {int(scored['small_sample'].sum())}", "grey"),
        ])
        top = graded.head(15)
        fig = go.Figure(go.Bar(
            x=top["score"], y=top["intern"], orientation="h",
            marker_color=[
                "#2E9E5B" if s >= 90 else "#1B1B1E" if s >= 75
                else "#E08A17" if s >= 60 else "#E0503C" for s in top["score"]
            ],
            text=top["score"].round(1), textposition="auto",
        ))
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(title="Top scores", xaxis_title="Score (0-100)",
                          xaxis_range=[0, 100])
        ui.show_chart(fig, height=max(280, 28 * len(top)), legend=False)

    view = scored.rename(columns={
        "intern": "Intern", "roster_status": "Status", "total_orders": "Orders",
        "review_submitted": "Submitted", "review_reflected": "Reflected",
        "reflection_rate": "Reflection %", "order_submission_rate": "Submission %",
        "delivery_rate": "Delivery %", "checker_verified_rate": "Checker %",
        "score": "Score", "grade": "Grade", "small_sample": "Small sample",
    })
    keep = [c for c in ["Intern", "Status", "Orders", "Submitted", "Reflected",
                        "Reflection %", "Submission %", "Delivery %", "Checker %",
                        "Score", "Grade", "Small sample"] if c in view.columns]
    st.dataframe(
        ui.grade_styler(view[keep], {
            "Reflection %": "reflection_rate",
            "Submission %": "order_submission_rate",
            "Delivery %": "delivery_rate",
            "Checker %": "checker_verified_rate",
        }, config).format(
            {c: "{:.1f}" for c in ["Reflection %", "Submission %", "Delivery %",
                                   "Checker %", "Score"] if c in keep},
            na_rep="-",
        ),
        width="stretch", hide_index=True, height=460,
    )

    ui.section("Drill into one intern")
    names = sorted(main["intern"].replace("", "(blank)").unique())
    who = st.selectbox("Intern", names, key="int_drill")
    rows = main[main["intern"].replace("", "(blank)") == who]
    if rows.empty:
        ui.empty_state("No orders for this intern.")
        return
    kpis = metrics.compute_kpis(rows)
    ui.render_kpis(
        [
            ui.kpi("Orders", kpis["total_orders"], unit="n", tone="neutral"),
            ui.kpi("Delivered", kpis["delivered"], unit="n", tone="neutral"),
            ui.kpi("Cancelled", kpis["true_cancelled"], unit="n",
                   tone="red" if kpis["true_cancelled"] else "green"),
            ui.kpi("Undelivered", kpis["not_delivered"] - kpis["true_cancelled"],
                   unit="n", tone="amber"),
            ui.kpi("Reviews Submitted", kpis["review_submitted"], unit="n",
                   tone="neutral"),
            ui.kpi("", kpis["reflection_rate"], kpi_key="reflection_rate",
                   config=config),
            ui.kpi("Order Value", kpis["order_value"], unit="Rs", tone="neutral"),
        ],
        config,
    )
    _, summary = common.audit_results(bundle, config)
    detail = common.attach_severity(rows, summary)
    detail = detail.assign(
        **{"Order date": detail["order_date"].dt.strftime("%d %b %Y")}
    ).rename(columns={
        "sheet_row": "Sheet row", "order_id": "Order ID", "product": "Product",
        "status": "Amazon status", "payment_state": "Payment",
        "order_price": "Order price", "rules": "Exceptions",
    })[["Sheet row", "Order date", "Order ID", "Product", "Amazon status",
        "Payment", "Order price", "severity", "Exceptions"]]
    st.dataframe(
        ui.severity_styler(detail).format({"Order price": "{:,.0f}"}, na_rep="-"),
        width="stretch", hide_index=True, height=380,
    )


# ---------------------------------------------------------------------------
def _roster_view(frame: pd.DataFrame, symbol: str) -> pd.DataFrame:
    present = [(src, dst) for src, dst in ROSTER_COLUMNS if src in frame.columns]
    out = frame[[src for src, _ in present]].copy()
    out.columns = [dst for _, dst in present]
    for col in ("Joining date", "End date"):
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce").dt.strftime("%d %b %Y")
    if "Tenure (days)" in out.columns:
        out["Tenure (days)"] = pd.to_numeric(
            out["Tenure (days)"], errors="coerce"
        ).astype("Int64")
    return out.reset_index(drop=True)
