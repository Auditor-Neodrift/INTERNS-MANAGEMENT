"""Products & ASINs: product mix, ASIN performance, targets and SKU spread."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common
import metrics
import ui

SCOPES = {"All time": "all", "Selected month": "month",
          "Last 90 days": "d90", "Last 30 days": "d30"}

GRADED = {
    "Reflection %": "reflection_rate",
    "Cancel %": "cancellation_rate",
    "Return %": "return_rate",
    "Delivery %": "delivery_rate",
}


def render(bundle, config: dict) -> None:
    main = bundle.main
    st.title("Products & ASINs")
    ui.note(
        "Product and ASIN performance counted live from MAIN, with the "
        "'ASIN REPORT' and 'MONTHLY TARGETS REPORT' tabs used for cross-checks."
    )
    if main.empty:
        ui.empty_state("No order rows found in the MAIN tab.")
        return

    scope_col, month_col = st.columns([1, 1])
    with scope_col:
        scope_label = st.selectbox("Scope", list(SCOPES.keys()), key="products_scope")
    with month_col:
        ym = common.month_picker(bundle, "Month (used when scope is a month)",
                                 key="products_month")
    period = _apply_scope(main, SCOPES[scope_label], ym)
    if period.empty:
        ui.empty_state("No orders in this scope.")
        return

    kpis = metrics.compute_kpis(period)
    by_product = metrics.by_dimension(period, "product")
    by_asin = metrics.by_dimension(period, "asin")

    ui.section(f"Catalogue coverage — {scope_label.lower()}")
    ui.render_kpis(
        [
            ui.kpi("Distinct Products", kpis["products"], unit="n", tone="neutral"),
            ui.kpi("Distinct ASINs", kpis["asins"], unit="n", tone="neutral"),
            ui.kpi("Distinct SKUs", period["order_sku"].replace("", pd.NA).nunique(),
                   unit="n", tone="neutral"),
            ui.kpi("Orders", kpis["total_orders"], unit="n", tone="neutral"),
            ui.kpi("Order Value", kpis["order_value"], unit="Rs", tone="neutral"),
            ui.kpi("Avg Order Value", kpis["avg_order_value"], unit="Rs", tone="neutral"),
        ],
        config,
    )

    tabs = st.tabs([
        "By product", "By ASIN", "Targets", "SKU spread", "ASIN REPORT cross-check",
    ])

    # ---- products ---------------------------------------------------------
    with tabs[0]:
        if by_product.empty:
            ui.empty_state("No product data in this scope.")
        else:
            top = by_product.head(15)
            fig = go.Figure()
            fig.add_bar(x=top["net_orders"], y=top["product"], orientation="h",
                        name="Net", marker_color="#0F766E")
            fig.add_bar(x=top["not_delivered"], y=top["product"], orientation="h",
                        name="Not delivered", marker_color="#DC2626")
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(barmode="stack", xaxis_title="Orders")
            ui.show_chart(fig, height=max(280, 30 * len(top)))
            _graded_table(by_product, "product", "Product", config)

    # ---- asins ------------------------------------------------------------
    with tabs[1]:
        if by_asin.empty:
            ui.empty_state("No ASIN data in this scope.")
        else:
            names = period.groupby("asin")["product"].first().rename("Product")
            table = by_asin.join(names, on="asin")
            top = table.head(15)
            fig = go.Figure(go.Bar(
                x=top["total_orders"],
                y=top["asin"] + " — " + top["Product"].fillna(""),
                orientation="h", marker_color="#2563EB",
                text=top["total_orders"], textposition="auto",
            ))
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(xaxis_title="Orders")
            ui.show_chart(fig, height=max(280, 30 * len(top)), legend=False)
            _graded_table(table, "asin", "ASIN", config, extra_first=["Product"])

    # ---- targets ----------------------------------------------------------
    with tabs[2]:
        tv = metrics.targets_vs_actual(main, bundle.targets, ym)
        month_label = pd.to_datetime(ym + "-01").strftime("%B %Y")
        with_target = (
            tv[tv["has_target"]] if not tv.empty and "has_target" in tv else pd.DataFrame()
        )
        if with_target.empty:
            ui.empty_state(
                f"No target is set for {month_label} on the Monthly Targets Report tab. "
                "That tab's target grid currently covers July only."
            )
        else:
            ui.note(f"Targets for {month_label}, actuals counted live from MAIN.")
            fig = go.Figure()
            fig.add_bar(x=with_target["product"], y=with_target["target"],
                        name="Target", marker_color="#94A3B8")
            fig.add_bar(x=with_target["product"], y=with_target["actual"],
                        name="Actual", marker_color="#0F766E")
            fig.update_layout(barmode="group", yaxis_title="Orders")
            ui.show_chart(fig, height=300)
            view = with_target.rename(columns={
                "product": "Product", "target": "Target", "actual": "Actual",
                "delivered_actual": "Delivered", "variance": "Variance",
                "achievement_pct": "Achievement %",
            })[["Product", "Target", "Actual", "Delivered", "Variance", "Achievement %"]]
            st.dataframe(
                ui.grade_styler(view, {"Achievement %": "target_achievement"}, config)
                .format({"Achievement %": "{:.1f}", "Variance": "{:+.0f}",
                         "Target": "{:.0f}", "Actual": "{:.0f}",
                         "Delivered": "{:.0f}"}, na_rep="-"),
                width="stretch", hide_index=True,
            )

        pv = metrics.productwise_actual_variance(main, bundle.targets, ym)
        if not pv.empty:
            st.markdown("**Sheet's productwise grid vs a live count**")
            mismatched = pv[~pv["match"]]
            if mismatched.empty:
                ui.callout([f"Every product ties for {month_label}."], "green")
            else:
                ui.callout(
                    [
                        f"{len(mismatched)} products do not tie for {month_label}. "
                        "The usual cause is a spelling variant in PRODUCT NAME, which "
                        "makes the sheet's own grid undercount."
                    ],
                    "amber",
                )
            ui.show_table(
                pv.rename(columns={
                    "product": "Product", "sheet_orders": "Sheet grid",
                    "app_orders": "Live from MAIN", "difference": "Difference",
                })[["Product", "Sheet grid", "Live from MAIN", "Difference"]]
            )

    # ---- sku spread --------------------------------------------------------
    with tabs[3]:
        sku = (
            period.assign(sku=period["order_sku"].replace("", "(blank)"))
            .groupby("sku", as_index=False)
            .agg(Orders=("order_id", "size"), Value=("order_price", "sum"),
                 Returned=("returned", "sum"))
            .sort_values("Orders", ascending=False)
        )
        ui.note(f"{len(sku):,} distinct ORDER SKU values in this scope.")
        ui.show_table(sku.rename(columns={"sku": "Order SKU"}), height=420)

        blank_dispatch = int((period["dispatched_sku"] == "").sum())
        if blank_dispatch:
            ui.callout(
                [
                    f"<strong>Watch:</strong> {blank_dispatch} orders have no "
                    "DISPATCHED SKU recorded."
                ],
                "amber",
            )

    # ---- asin report cross-check --------------------------------------------
    with tabs[4]:
        asin_tab = bundle.asin
        if asin_tab is None or asin_tab.empty:
            ui.empty_state("The 'ASIN REPORT' tab could not be read.")
        else:
            ui.note(
                "The ASIN REPORT tab is an all-time ASIN count. Compared here "
                "against an all-time count from MAIN."
            )
            live = (
                main.groupby("asin", as_index=False)
                .agg(app_orders=("order_id", "size"))
            )
            sheet = (
                asin_tab.groupby("asin", as_index=False)
                .agg(sheet_orders=("orders", "sum"),
                     product=("product", "first"))
            )
            merged = sheet.merge(live, on="asin", how="outer")
            merged[["sheet_orders", "app_orders"]] = merged[
                ["sheet_orders", "app_orders"]
            ].fillna(0)
            merged["difference"] = merged["app_orders"] - merged["sheet_orders"]
            merged["match"] = merged["difference"] == 0
            mismatched = merged[~merged["match"]]
            if mismatched.empty:
                ui.callout(
                    [f"All {len(merged)} ASINs tie between the ASIN REPORT tab and MAIN."],
                    "green",
                )
            else:
                ui.callout(
                    [
                        f"{len(mismatched)} of {len(merged)} ASINs differ. A positive "
                        "difference means MAIN has orders the ASIN REPORT tab has not "
                        "picked up."
                    ],
                    "amber",
                )
            ui.show_table(
                merged.sort_values("difference", key=lambda s: s.abs(), ascending=False)
                .rename(columns={
                    "asin": "ASIN", "product": "Product",
                    "sheet_orders": "ASIN REPORT tab", "app_orders": "Live from MAIN",
                    "difference": "Difference",
                })[["ASIN", "Product", "ASIN REPORT tab", "Live from MAIN", "Difference"]],
                height=420,
            )

    ui.section("Download")
    ui.download_row(
        {
            "by product": _plain(by_product, "product", "Product"),
            "by asin": _plain(by_asin, "asin", "ASIN"),
        },
        excel_name="products", key_prefix="products",
    )


def _apply_scope(main: pd.DataFrame, scope: str, ym: str) -> pd.DataFrame:
    if scope == "month":
        return metrics.slice_month(main, ym)
    if scope == "d90":
        return metrics.slice_last_days(main, 90)
    if scope == "d30":
        return metrics.slice_last_days(main, 30)
    return main


RENAMES = {
    "total_orders": "Orders", "net_orders": "Net", "not_delivered": "Not delivered",
    "returned": "Returned", "review_submitted": "Submitted",
    "review_reflected": "Reflected", "reflection_rate": "Reflection %",
    "cancellation_rate": "Cancel %", "return_rate": "Return %",
    "delivery_rate": "Delivery %", "order_value": "Order value",
    "avg_order_value": "Avg value",
}
ORDER = [
    "Orders", "Net", "Not delivered", "Returned", "Submitted", "Reflected",
    "Reflection %", "Delivery %", "Cancel %", "Return %", "Order value", "Avg value",
]


def _plain(df: pd.DataFrame, key: str, label: str,
           extra_first: list[str] | None = None) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    out = df.rename(columns={**RENAMES, key: label})
    columns = [label] + (extra_first or []) + ORDER
    return out[[c for c in columns if c in out.columns]].reset_index(drop=True)


def _graded_table(df: pd.DataFrame, key: str, label: str, config: dict,
                  extra_first: list[str] | None = None) -> None:
    view = _plain(df, key, label, extra_first)
    st.dataframe(
        ui.grade_styler(view, GRADED, config).format(
            {
                **{c: "{:.1f}" for c in GRADED if c in view.columns},
                "Order value": "{:,.0f}", "Avg value": "{:,.0f}",
            },
            na_rep="-",
        ),
        width="stretch", hide_index=True, height=430,
    )
