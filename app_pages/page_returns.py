"""Returns Report.

The workbook has no standalone "returns report" tab - the return trail lives
in MAIN across AMAZON STATUS, RETURN PICKUP BY and RETURN CHECKER. This page
assembles those into the returns report, by month, product, intern and
sign-off state.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common
import metrics
import ui

SCOPES = {"All time": "all", "Selected month": "month",
          "Last 90 days": "d90", "Last 30 days": "d30"}


def render(bundle, config: dict, embedded: bool = False) -> None:
    main = bundle.main
    symbol = config.get("display", {}).get("currency_symbol", "Rs")

    if not embedded:

        st.title("Returns Report")
    ui.note(
        "Built from the return trail inside MAIN: an Amazon status of "
        "'Returned to Seller' or 'Returning to Seller', plus the "
        "RETURN PICKUP BY and RETURN CHECKER columns."
    )
    if main.empty:
        ui.empty_state("No order rows found in the MAIN tab.")
        return

    scope_col, month_col = st.columns([1, 1])
    with scope_col:
        scope_label = st.selectbox("Scope", list(SCOPES.keys()), key="returns_scope")
    with month_col:
        ym = common.month_picker(bundle, "Month (used when scope is a month)",
                                 key="returns_month")
    scope = SCOPES[scope_label]

    period = _apply_scope(main, scope, ym)
    if period.empty:
        ui.empty_state("No orders in this scope.")
        return

    returns = period[period["returned"]]
    kpis = metrics.compute_kpis(period)

    signed_off = returns[returns["return_checker"].str.upper() == "OK"]
    no_signoff = returns[returns["return_checker"].str.upper() != "OK"]
    no_pickup = returns[returns["return_pickup_by"] == ""]
    paid_returns = returns[returns["is_paid"]]

    # ---- headline -------------------------------------------------------
    ui.section(f"Returns position — {scope_label.lower()}")
    ui.render_kpis(
        [
            ui.kpi("Returned Orders", len(returns), unit="n",
                   tone="amber" if len(returns) else "green",
                   sub=f"of {len(period)} orders in scope"),
            ui.kpi("", kpis["return_rate"], kpi_key="return_rate", config=config),
            ui.kpi("Returns Value", kpis["returned_amt"], unit="Rs",
                   tone="amber" if kpis["returned_amt"] else "green",
                   sub="order value that came back"),
            ui.kpi("Checker Signed Off", len(signed_off), unit="n",
                   tone="green" if len(no_signoff) == 0 else "amber",
                   sub=f"{len(no_signoff)} still unsigned"),
            ui.kpi("No Pickup Partner", len(no_pickup), unit="n",
                   tone="amber" if len(no_pickup) else "green",
                   sub="RETURN PICKUP BY is blank"),
            ui.kpi("Paid Despite Return", len(paid_returns), unit="n",
                   tone="red" if len(paid_returns) else "green",
                   sub=ui.fmt_money(paid_returns["order_price"].sum(), symbol)),
        ],
        config,
    )

    findings = []
    if len(no_signoff):
        findings.append(
            f"<strong>Red:</strong> {len(no_signoff)} returned orders worth "
            f"{ui.fmt_money(no_signoff['order_price'].sum(), symbol)} have no "
            "RETURN CHECKER sign-off."
        )
    if len(paid_returns):
        findings.append(
            f"<strong>Red:</strong> {ui.fmt_money(paid_returns['order_price'].sum(), symbol)} "
            f"was paid across {len(paid_returns)} orders that came back as returns."
        )
    if len(no_pickup):
        findings.append(
            f"<strong>Watch:</strong> {len(no_pickup)} returns have no pickup partner "
            "recorded, so the reverse leg is untracked."
        )
    if not returns.empty and not findings:
        findings.append("Every return in this scope is signed off and tracked.")
    ui.callout(
        findings or ["No returns recorded in this scope."],
        common.worst_tone(findings) if findings else "green",
        title="Returns findings",
    )

    # ---- monthly trend ---------------------------------------------------
    ui.section("Returns by month", "Whole book, regardless of the scope above.")
    series = common.monthly_series(main)
    if not series.empty:
        labels = series["month_label"]
        fig = go.Figure()
        fig.add_bar(x=labels, y=series["returned"], name="Returned orders",
                    marker_color="#D97706")
        fig.add_scatter(x=labels, y=series["return_rate"], name="Return rate %",
                        mode="lines+markers", yaxis="y2",
                        line=dict(color="#DC2626", width=2))
        fig.update_layout(
            yaxis_title="Returned orders",
            yaxis2=dict(title="%", overlaying="y", side="right",
                        showgrid=False, rangemode="tozero"),
        )
        ui.show_chart(fig, height=320)

        table = series[[
            "month_label", "total_orders", "returned", "return_rate", "returned_amt",
        ]].rename(columns={
            "month_label": "Month", "total_orders": "Orders",
            "returned": "Returned", "return_rate": "Return %",
            "returned_amt": "Returns value",
        })
        st.dataframe(
            ui.grade_styler(table, {"Return %": "return_rate"}, config).format(
                {"Return %": "{:.1f}", "Returns value": "{:,.0f}"}, na_rep="-"
            ),
            width="stretch", hide_index=True,
        )

    if returns.empty:
        return

    # ---- breakdowns ------------------------------------------------------
    ui.section("Where returns concentrate")
    tab_product, tab_intern, tab_status, tab_rows = st.tabs(
        ["By product", "By intern", "Return status detail", "All returned rows"]
    )

    with tab_product:
        prod = metrics.by_dimension(period, "product")
        prod = prod[prod["returned"] > 0]
        if prod.empty:
            ui.empty_state("No product has a return in this scope.")
        else:
            view = prod[[
                "product", "total_orders", "returned", "return_rate", "returned_amt",
            ]].rename(columns={
                "product": "Product", "total_orders": "Orders",
                "returned": "Returned", "return_rate": "Return %",
                "returned_amt": "Returns value",
            }).sort_values("Returned", ascending=False)
            fig = go.Figure(go.Bar(
                x=view["Returned"].head(12), y=view["Product"].head(12),
                orientation="h", marker_color="#D97706",
                text=view["Returned"].head(12), textposition="auto",
            ))
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(xaxis_title="Returned orders")
            ui.show_chart(fig, height=max(250, 30 * min(12, len(view))), legend=False)
            st.dataframe(
                ui.grade_styler(view, {"Return %": "return_rate"}, config).format(
                    {"Return %": "{:.1f}", "Returns value": "{:,.0f}"}, na_rep="-"
                ),
                width="stretch", hide_index=True,
            )

    with tab_intern:
        per = metrics.by_dimension(period, "intern")
        per = per[per["returned"] > 0]
        if per.empty:
            ui.empty_state("No intern has a return in this scope.")
        else:
            view = per[[
                "intern", "total_orders", "returned", "return_rate", "returned_amt",
            ]].rename(columns={
                "intern": "Intern", "total_orders": "Orders",
                "returned": "Returned", "return_rate": "Return %",
                "returned_amt": "Returns value",
            }).sort_values("Returned", ascending=False)
            st.dataframe(
                ui.grade_styler(view, {"Return %": "return_rate"}, config).format(
                    {"Return %": "{:.1f}", "Returns value": "{:,.0f}"}, na_rep="-"
                ),
                width="stretch", hide_index=True,
            )

    with tab_status:
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Amazon return status**")
            ui.show_table(
                returns.groupby("status", as_index=False)
                .agg(Orders=("order_id", "size"), Value=("order_price", "sum"))
                .sort_values("Orders", ascending=False)
                .rename(columns={"status": "Status"})
            )
            st.markdown("**Pickup partner**")
            pickup = returns.assign(
                partner=returns["return_pickup_by"].replace("", "(blank)")
            )
            ui.show_table(
                pickup.groupby("partner", as_index=False)
                .agg(Orders=("order_id", "size"))
                .sort_values("Orders", ascending=False)
                .rename(columns={"partner": "Return pickup by"})
            )
        with col_b:
            st.markdown("**Checker sign-off**")
            signoff = returns.assign(
                state=returns["return_checker"].replace("", "(not signed off)")
            )
            ui.show_table(
                signoff.groupby("state", as_index=False)
                .agg(Orders=("order_id", "size"), Value=("order_price", "sum"))
                .sort_values("Orders", ascending=False)
                .rename(columns={"state": "Return checker"})
            )
            st.markdown("**Payment state on returned orders**")
            ui.show_table(
                returns.groupby("payment_state", as_index=False)
                .agg(Orders=("order_id", "size"), Value=("order_price", "sum"))
                .sort_values("Orders", ascending=False)
                .rename(columns={"payment_state": "Payment"})
            )

    with tab_rows:
        only_open = st.toggle("Only returns without sign-off", value=False,
                              key="returns_only_open")
        shown = no_signoff if only_open else returns
        ui.show_table(_returns_view(shown), height=420)

    # ---- export -----------------------------------------------------------
    ui.section("Download")
    ui.download_row(
        {
            "returned rows": _returns_view(returns),
            "returns without signoff": _returns_view(no_signoff),
        },
        excel_name="returns-report",
        key_prefix="returns",
    )


def _apply_scope(main: pd.DataFrame, scope: str, ym: str) -> pd.DataFrame:
    if scope == "month":
        return metrics.slice_month(main, ym)
    if scope == "d90":
        return metrics.slice_last_days(main, 90)
    if scope == "d30":
        return metrics.slice_last_days(main, 30)
    return main


def _returns_view(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    out = df.copy()
    out["Order date"] = out["order_date"].dt.strftime("%d %b %Y")
    return out.rename(columns={
        "sheet_row": "Sheet row", "order_id": "Order ID", "intern": "Intern",
        "product": "Product", "status": "Amazon status",
        "return_pickup_by": "Pickup by", "return_checker": "Return checker",
        "payment_state": "Payment", "order_price": "Order price",
        "dispatched_sku": "Dispatched SKU",
    })[[
        "Sheet row", "Order date", "Order ID", "Intern", "Product",
        "Amazon status", "Pickup by", "Return checker", "Payment",
        "Order price", "Dispatched SKU",
    ]].reset_index(drop=True)
