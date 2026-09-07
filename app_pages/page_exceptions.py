"""Audit & Exceptions: every row-level rule violation, filterable and exportable."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import audit
import common
import ui


def render(bundle, config: dict) -> None:
    main = bundle.main
    symbol = config.get("display", {}).get("currency_symbol", "Rs")

    st.title("Audit & Exceptions")
    ui.note(
        "Every enabled rule from the Settings page, applied to each order row. "
        "Red means fix it; amber means check it. Turn rules off or retune their "
        "limits on the Settings page."
    )
    if main.empty:
        ui.empty_state("No order rows found in the MAIN tab.")
        return

    findings, summary = common.audit_results(bundle, config)
    health = audit.health_score(summary)
    exception_rate = (
        None if health["clean_pct"] is None else round(100 - health["clean_pct"], 2)
    )

    # ---- health ----------------------------------------------------------
    ui.section("Data health across all months")
    ui.render_kpis(
        [
            ui.kpi("Rows Audited", health["total"], unit="n", tone="neutral"),
            ui.kpi("Clean Rows", health["clean"], unit="n",
                   tone="green" if health["clean"] else "red",
                   sub=ui.fmt_pct(health["clean_pct"])),
            ui.kpi("Rows with Red", health["red"], unit="n",
                   tone="red" if health["red"] else "green",
                   sub=ui.fmt_pct(health.get("red_pct"))),
            ui.kpi("Rows with Warning", health["amber"], unit="n",
                   tone="amber" if health["amber"] else "green",
                   sub=ui.fmt_pct(health.get("amber_pct"))),
            ui.kpi("", exception_rate, kpi_key="exception_rate", config=config),
            ui.kpi("Total Findings", len(findings), unit="n", tone="neutral",
                   sub="a row can trip several rules"),
            ui.kpi("Value on Red Rows", _value_on(summary, main, "red"), unit="Rs",
                   tone="red" if health["red"] else "green"),
        ],
        config,
    )

    rules = audit.rule_summary(findings, config)
    disabled = rules[~rules["enabled"]] if not rules.empty else pd.DataFrame()
    if not disabled.empty:
        ui.callout(
            [
                f"{len(disabled)} rules are switched off: "
                + ", ".join(sorted(disabled["rule"]))
            ],
            "grey",
            title="Rules currently disabled",
        )

    # ---- rule summary -----------------------------------------------------
    ui.section("Rules and how many rows they catch")
    if rules.empty:
        ui.empty_state("No rules are configured.")
    else:
        live = rules[rules["rows_flagged"] > 0]
        if not live.empty:
            fig = go.Figure(go.Bar(
                x=live["rows_flagged"], y=live["rule"], orientation="h",
                marker_color=[
                    "#DC2626" if s == "red" else "#D97706" for s in live["severity"]
                ],
                text=live["rows_flagged"], textposition="auto",
            ))
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(xaxis_title="Rows flagged")
            ui.show_chart(fig, height=max(300, 27 * len(live)), legend=False)

        view = rules.copy()
        view["Exposed"] = view["value_flagged"].map(
            lambda v: ui.fmt_money(v, symbol, compact=True)
        )
        view["On"] = view["enabled"].map({True: "yes", False: "no"})
        ui.show_table(
            view.rename(columns={
                "rule": "Rule", "group": "Area", "severity": "Severity",
                "rows_flagged": "Rows", "limit": "Limit", "help": "What it checks",
            })[["Rule", "Area", "Severity", "On", "Rows", "Exposed", "Limit",
                "What it checks"]]
        )

    # ---- by area and by month ---------------------------------------------
    if not findings.empty:
        col_a, col_b = st.columns(2)
        with col_a:
            area = (
                findings.groupby(["group", "severity"], as_index=False)
                .agg(Rows=("order_id", "size"))
            )
            fig = go.Figure()
            for sev, colour in (("red", "#DC2626"), ("amber", "#D97706")):
                part = area[area["severity"] == sev]
                if not part.empty:
                    fig.add_bar(x=part["group"], y=part["Rows"],
                                name=sev.upper(), marker_color=colour)
            fig.update_layout(barmode="stack", title="Findings by area",
                              yaxis_title="Findings")
            ui.show_chart(fig, height=300)
        with col_b:
            per_month = (
                findings.groupby(["ym", "severity"], as_index=False)
                .agg(Rows=("order_id", "size"))
                .sort_values("ym")
            )
            fig = go.Figure()
            for sev, colour in (("red", "#DC2626"), ("amber", "#D97706")):
                part = per_month[per_month["severity"] == sev]
                if not part.empty:
                    fig.add_bar(x=part["ym"], y=part["Rows"],
                                name=sev.upper(), marker_color=colour)
            fig.update_layout(barmode="stack", title="Findings by month",
                              yaxis_title="Findings")
            ui.show_chart(fig, height=300)

    # ---- filterable finding list -------------------------------------------
    ui.section("Filter the findings")
    if findings.empty:
        ui.callout(["No audit rule is firing on the current data."], "green")
        return

    row_a = st.columns([1, 1, 1])
    with row_a[0]:
        months = ["All months"] + sorted(findings["ym"].dropna().unique(), reverse=True)
        pick_month = st.selectbox("Month", months, key="exc_month")
    with row_a[1]:
        severities = ["All", "red", "amber"]
        pick_sev = st.selectbox("Severity", severities, key="exc_sev")
    with row_a[2]:
        areas = ["All areas"] + sorted(findings["group"].dropna().unique())
        pick_area = st.selectbox("Area", areas, key="exc_area")

    row_b = st.columns([2, 2])
    with row_b[0]:
        rule_names = sorted(findings["rule"].dropna().unique())
        pick_rules = st.multiselect("Rules", rule_names, key="exc_rules")
    with row_b[1]:
        interns = sorted(findings["intern"].replace("", "(blank)").dropna().unique())
        pick_interns = st.multiselect("Interns", interns, key="exc_interns")

    view = findings.copy()
    if pick_month != "All months":
        view = view[view["ym"] == pick_month]
    if pick_sev != "All":
        view = view[view["severity"] == pick_sev]
    if pick_area != "All areas":
        view = view[view["group"] == pick_area]
    if pick_rules:
        view = view[view["rule"].isin(pick_rules)]
    if pick_interns:
        view = view[view["intern"].replace("", "(blank)").isin(pick_interns)]

    ui.chips(
        [
            (f"{len(view):,} findings", "grey"),
            (f"{view['order_id'].nunique():,} distinct orders", "grey"),
            (f"{ui.fmt_money(view['order_price'].sum(), symbol, compact=True)} exposed",
             "red" if len(view) else "green"),
        ]
    )

    display_view = view.copy()
    display_view["Order date"] = pd.to_datetime(
        display_view["order_date"]
    ).dt.strftime("%d %b %Y")
    display_view = display_view.rename(columns={
        "sheet_row": "Sheet row", "order_id": "Order ID", "intern": "Intern",
        "product": "Product", "status": "Amazon status",
        "payment_state": "Payment", "order_price": "Order price",
        "rule": "Rule", "group": "Area", "detail": "Limit",
    })[[
        "Sheet row", "Order date", "Order ID", "Intern", "Product",
        "Amazon status", "Payment", "Order price", "Rule", "Area",
        "severity", "Limit",
    ]]
    st.dataframe(
        ui.severity_styler(display_view).format({"Order price": "{:,.0f}"}, na_rep="-"),
        width="stretch", hide_index=True, height=480,
    )

    # ---- worst rows --------------------------------------------------------
    ui.section("Rows with the most problems")
    worst = common.attach_severity(main, summary)
    worst = worst[worst["total_issues"] > 0].nlargest(25, "total_issues")
    if not worst.empty:
        wv = worst.copy()
        wv["Order date"] = wv["order_date"].dt.strftime("%d %b %Y")
        wv = wv.rename(columns={
            "sheet_row": "Sheet row", "order_id": "Order ID", "intern": "Intern",
            "product": "Product", "order_price": "Order price",
            "red_count": "Red", "amber_count": "Warnings", "rules": "Exceptions",
        })[[
            "Sheet row", "Order date", "Order ID", "Intern", "Product",
            "Order price", "Red", "Warnings", "severity", "Exceptions",
        ]]
        st.dataframe(
            ui.severity_styler(wv).format({"Order price": "{:,.0f}"}, na_rep="-"),
            width="stretch", hide_index=True, height=400,
        )

    # ---- the team's own CHECKER tab ----------------------------------------
    if bundle.checker is not None and not bundle.checker.empty:
        ui.section(
            "The team's own CHECKER tab",
            "Manually flagged orders, shown alongside what this app's rules found.",
        )
        chk = bundle.checker.copy()
        flagged_ids = set(findings["order_id"])
        chk["Also flagged here"] = chk["order_id"].isin(flagged_ids).map(
            {True: "yes", False: "no"}
        )
        ui.show_table(
            chk.rename(columns={
                "intern": "Intern", "issue": "Issue",
                "order_id": "Order ID", "order_sku": "Order SKU",
            })[["Intern", "Issue", "Order ID", "Order SKU", "Also flagged here"]],
            height=340,
        )

    ui.section("Download")
    ui.download_row(
        {
            "filtered findings": display_view,
            "all findings": findings,
            "rule summary": rules,
        },
        excel_name="exceptions", key_prefix="exceptions",
    )


def _value_on(summary: pd.DataFrame, main: pd.DataFrame, severity: str) -> float:
    if summary.empty or "severity" not in summary.columns:
        return 0.0
    index = summary.index[summary["severity"] == severity]
    return float(main.loc[index, "order_price"].fillna(0).sum())
