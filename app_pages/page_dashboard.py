"""Dashboard: one screen the team can audit from.

Summarises a month you pick, the month before it, and the last seven days,
with a health banner, trends, and the biggest exposures right now.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import audit
import common
import metrics
import ui


def render(bundle, config: dict) -> None:
    main = bundle.main
    display = config.get("display", {})
    symbol = display.get("currency_symbol", "Rs")
    week_days = int(display.get("week_days", 7) or 7)

    st.title("Interns Order Audit Dashboard")
    ui.hero(
        "One screen to run the stand-up from",
        "A month you pick, the month before it, the last seven days, who is "
        "active right now, and the money at risk.",
    )
    if main.empty:
        ui.empty_state("No order rows found in the MAIN tab.")
        return

    findings, summary = common.audit_results(bundle, config)
    health = audit.health_score(summary)

    # ---- period slices -------------------------------------------------
    picker_col, _spacer = st.columns([1, 2])
    with picker_col:
        selected_ym = common.month_picker(
            bundle, "Report month", key="dash_month",
            help_text="Drives the selected-month column and the month KPI block.",
        )
    previous_ym = metrics.previous_ym(selected_ym)

    sel = metrics.slice_month(main, selected_ym)
    prev = metrics.slice_month(main, previous_ym)
    last_week = metrics.slice_last_days(main, week_days)
    prior_week = metrics.slice_prior_days(main, week_days)

    k_sel = metrics.compute_kpis(sel)
    k_prev = metrics.compute_kpis(prev)
    k_week = metrics.compute_kpis(last_week)
    k_prior = metrics.compute_kpis(prior_week)
    k_all = metrics.compute_kpis(main)

    sel_label = pd.to_datetime(selected_ym + "-01").strftime("%B %Y")
    prev_label = pd.to_datetime(previous_ym + "-01").strftime("%B %Y")

    ui.chips(
        [
            (f"{sel_label}: {k_sel.get('total_orders', 0)} orders", "grey"),
            (f"Last {week_days} days: {k_week.get('total_orders', 0)} orders", "grey"),
            (f"{health['red']} red rows", "red" if health["red"] else "green"),
            (f"{health['amber']} warnings", "amber" if health["amber"] else "green"),
            (f"{ui.fmt_pct(health['clean_pct'])} rows clean", "green"),
        ]
    )

    # ---- health banner -------------------------------------------------
    lines = common.headline_findings(k_sel, config, health)
    if lines:
        ui.callout(lines[:6], common.worst_tone(lines[:6]),
                   title=f"What needs attention in {sel_label}")
    else:
        ui.callout([f"Every tracked KPI for {sel_label} is inside its green band."],
                   "green", title="All clear")

    # ---- headline exposure across the whole book -----------------------
    ui.section(
        "Money at risk (all time)",
        "Across every month in MAIN, not just the selected period.",
    )
    ui.render_kpis(
        [
            ui.kpi("", k_all.get("paid_unreflected_amt"), kpi_key="paid_unreflected_amt",
                   config=config,
                   sub=f"{k_all.get('paid_unreflected_count', 0)} orders paid, review not live"),
            ui.kpi("", k_all.get("payment_pending_amt"), kpi_key="payment_pending_amt",
                   config=config,
                   sub=f"{k_all.get('payment_pending_count', 0)} orders still to pay"),
            ui.kpi("", k_all.get("paid_undelivered_amt"), kpi_key="paid_undelivered_amt",
                   config=config,
                   sub=f"{k_all.get('paid_undelivered_count', 0)} cancelled or returned"),
            ui.kpi("", k_all.get("unreconciled_amt"), kpi_key="unreconciled_amt",
                   config=config,
                   sub=f"{k_all.get('unreconciled_count', 0)} rows without Amazon price"),
            ui.kpi("Returns Value", k_all.get("returned_amt"), unit="Rs", tone="neutral",
                   sub=f"{k_all.get('returned', 0)} returned orders"),
            ui.kpi("Total Order Value", k_all.get("order_value"), unit="Rs",
                   tone="neutral", sub=f"{k_all.get('total_orders', 0)} orders funded"),
        ],
        config,
    )

    # ---- who is active right now ---------------------------------------
    tenure_days = int(display.get("tenure_days", 30) or 30)
    interns = metrics.intern_table(main, bundle.roster, tenure_days=tenure_days)
    active = interns[interns["is_active"]]
    due = metrics.tenure_alerts(interns, tenure_days=tenure_days)

    ui.section(
        "Active interns",
        "From the roster tab, with work counted live. Full detail on the Interns page.",
    )
    if active.empty:
        ui.empty_state("Nobody on the roster is marked Active.")
    else:
        week_orders = metrics.intern_daily(metrics.slice_last_days(main, week_days))
        names = set(active["name"].str.casefold())
        week_orders = (
            week_orders[week_orders["intern"].str.casefold().isin(names)]
            if not week_orders.empty else week_orders
        )
        ui.render_kpis(
            [
                ui.kpi("Active Interns", len(active), unit="n", tone="green"),
                ui.kpi(f"Their Orders ({week_days}d)",
                       int(week_orders["orders"].sum()) if not week_orders.empty else 0,
                       unit="n", tone="neutral"),
                ui.kpi("Orders This Tenure", int(active["orders"].sum()),
                       unit="n", tone="neutral"),
                ui.kpi("Reviews Submitted", int(active["reviews_submitted"].sum()),
                       unit="n", tone="neutral"),
                ui.kpi("Cancelled", int(active["cancelled"].sum()), unit="n",
                       tone="red" if active["cancelled"].sum() else "green"),
                ui.kpi("Undelivered", int(active["undelivered"].sum()), unit="n",
                       tone="amber" if active["undelivered"].sum() else "green"),
                ui.kpi("Tenure Review Due", len(due), unit="n",
                       tone="amber" if len(due) else "green",
                       sub=f"past {tenure_days} days"),
            ],
            config,
        )
        if not due.empty:
            ui.alert_card(
                f"{len(due)} intern(s) need a tenure review",
                f"This intern's {tenure_days}-day tenure period is over. Please "
                "review their performance and take the required action.",
                meta=", ".join(due["name"].head(8)) + "  ·  see the Interns page",
                tone="amber",
            )

    # ---- three period blocks -------------------------------------------
    ui.section(
        "Period summaries",
        f"Selected month, the month before it, and the last {week_days} days.",
    )
    tab_sel, tab_prev, tab_week, tab_cmp = st.tabs(
        [sel_label, prev_label, f"Last {week_days} days", "Side by side"]
    )

    with tab_sel:
        _period_block(k_sel, k_prev, config, f"vs {prev_label}")
    with tab_prev:
        _period_block(k_prev, metrics.compute_kpis(
            metrics.slice_month(main, metrics.previous_ym(previous_ym))
        ), config, "vs the month before")
    with tab_week:
        _period_block(k_week, k_prior, config,
                      f"vs the previous {week_days} days")
    with tab_cmp:
        table = common.comparison_table(
            {
                sel_label: k_sel,
                prev_label: k_prev,
                f"Last {week_days}d": k_week,
                f"Prior {week_days}d": k_prior,
                "All time": k_all,
            },
            config,
        )
        ui.show_table(table)
        ui.source_note(
            "Percentages use the same definitions as the workbook's Overall Audit "
            "Report tab: net orders exclude anything not marked delivered."
        )

    # ---- trends --------------------------------------------------------
    ui.section("Trends", "Every month present in MAIN.")
    series = common.monthly_series(main)
    if not series.empty:
        _trend_charts(series, config, selected_ym)

    # ---- daily pulse for the selected month ----------------------------
    if not sel.empty:
        ui.section(f"Daily pulse - {sel_label}")
        daily = metrics.daily_series(sel)
        fig = go.Figure()
        fig.add_bar(x=daily["day"], y=daily["orders"], name="Orders",
                    marker_color="#0F766E")
        fig.add_scatter(x=daily["day"], y=daily["delivered"], name="Delivered",
                        mode="lines+markers", line=dict(color="#2563EB", width=2))
        fig.update_layout(yaxis_title="Orders")
        ui.show_chart(fig, height=280)

    # ---- what to chase -------------------------------------------------
    ui.section("Top exceptions to chase", "Ranked by exposed order value.")
    rules = audit.rule_summary(findings, config)
    if rules.empty or rules["rows_flagged"].sum() == 0:
        ui.empty_state("No audit rule is firing on the current data.")
    else:
        live = rules[rules["rows_flagged"] > 0].copy()
        live["Exposed"] = live["value_flagged"].map(
            lambda v: ui.fmt_money(v, symbol, compact=True)
        )
        live["Severity"] = live["severity"].str.upper()
        ui.show_table(
            live.rename(columns={
                "rule": "Rule", "group": "Area",
                "rows_flagged": "Rows", "limit": "Limit",
            })[["Rule", "Area", "Severity", "Rows", "Exposed", "Limit"]]
            .sort_values("Rows", ascending=False)
            .head(10)
        )
        ui.source_note(
            "Full row-level detail, with filters and export, is on the "
            "Audit & Exceptions page."
        )

    # ---- mix -----------------------------------------------------------
    ui.section(f"Order mix - {sel_label}")
    col_a, col_b = st.columns(2)
    with col_a:
        status = metrics.status_breakdown(sel)
        if not status.empty:
            fig = go.Figure(go.Bar(
                x=status["orders"], y=status["status"], orientation="h",
                marker_color="#0F766E",
                text=status["orders"], textposition="auto",
            ))
            fig.update_layout(title="Amazon status", xaxis_title="Orders")
            fig.update_yaxes(autorange="reversed")
            ui.show_chart(fig, height=max(240, 34 * len(status)), legend=False)
    with col_b:
        pay = metrics.payment_breakdown(sel)
        if not pay.empty:
            tone_map = {"PAID": "#059669", "PENDING": "#D97706",
                        "CANCELLED": "#DC2626", "HOLD": "#7C3AED",
                        "UNKNOWN": "#64748B"}
            fig = go.Figure(go.Bar(
                x=pay["orders"], y=pay["payment_state"], orientation="h",
                marker_color=[tone_map.get(s, "#64748B") for s in pay["payment_state"]],
                text=pay["orders"], textposition="auto",
            ))
            fig.update_layout(title="Payment state", xaxis_title="Orders")
            fig.update_yaxes(autorange="reversed")
            ui.show_chart(fig, height=max(240, 34 * len(pay)), legend=False)

    ui.source_note(
        f"MAIN tab, {len(main):,} order rows, "
        f"{main['order_date'].min():%d %b %Y} to {main['order_date'].max():%d %b %Y}. "
        f"Pulled {bundle.loaded_at:%d %b %Y %H:%M}."
    )


def _period_block(kpis: dict, prev: dict, config: dict, delta_note: str) -> None:
    if kpis.get("is_empty", True) or not kpis.get("total_orders"):
        ui.empty_state("No orders in this period.")
        return
    ui.note(f"Deltas are {delta_note}.")
    st.markdown("**Volume and fulfilment**")
    ui.render_kpis(common.volume_kpis(kpis, config, prev), config)
    st.markdown("**Review pipeline**")
    ui.render_kpis(common.review_kpis(kpis, config, prev), config)
    st.markdown("**Money**")
    ui.render_kpis(common.money_kpis(kpis, config, prev), config)


def _trend_charts(series: pd.DataFrame, config: dict, selected_ym: str) -> None:
    display = config.get("display", {})
    labels = series["month_label"]

    fig = go.Figure()
    fig.add_bar(x=labels, y=series["net_orders"], name="Net orders",
                marker_color="#0F766E")
    fig.add_bar(x=labels, y=series["not_delivered"], name="Not delivered",
                marker_color="#DC2626")
    fig.add_scatter(x=labels, y=series["review_submitted"], name="Reviews submitted",
                    mode="lines+markers", line=dict(color="#2563EB", width=2))
    fig.update_layout(barmode="stack", yaxis_title="Orders", title="Volume by month")
    ui.show_chart(fig, height=320)

    col_a, col_b = st.columns(2)
    with col_a:
        fig = go.Figure()
        fig.add_scatter(x=labels, y=series["reflection_rate"], name="Reflection %",
                        mode="lines+markers", line=dict(color="#0F766E", width=2.5))
        fig.add_scatter(x=labels, y=series["order_submission_rate"],
                        name="Submission %", mode="lines+markers",
                        line=dict(color="#2563EB", width=2, dash="dot"))
        ui.threshold_bands(fig, config.get("kpis", {}).get("reflection_rate", {}),
                           display, series["reflection_rate"])
        fig.update_layout(title="Reflection and submission", yaxis_title="%")
        ui.show_chart(fig, height=300)
    with col_b:
        fig = go.Figure()
        fig.add_scatter(x=labels, y=series["cancellation_rate"], name="Cancellation %",
                        mode="lines+markers", line=dict(color="#DC2626", width=2.5))
        fig.add_scatter(x=labels, y=series["return_rate"], name="Return %",
                        mode="lines+markers", line=dict(color="#D97706", width=2))
        ui.threshold_bands(fig, config.get("kpis", {}).get("cancellation_rate", {}),
                           display, series["cancellation_rate"])
        fig.update_layout(title="Cancellation and returns", yaxis_title="%")
        ui.show_chart(fig, height=300)

    fig = go.Figure()
    fig.add_bar(x=labels, y=series["order_value"], name="Order value funded",
                marker_color="#0F766E")
    fig.add_scatter(x=labels, y=series["paid_unreflected_amt"],
                    name="Paid but not reflected", mode="lines+markers",
                    line=dict(color="#DC2626", width=2))
    fig.update_layout(title="Money by month", yaxis_title=display.get("currency_symbol", "Rs"))
    ui.show_chart(fig, height=300)
