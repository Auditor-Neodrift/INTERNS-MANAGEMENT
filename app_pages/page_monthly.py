"""Monthly Report: the automated audit write-up for one selected month."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import audit
import common
import metrics
import ui


def render(bundle, config: dict, embedded: bool = False) -> None:
    main = bundle.main
    display = config.get("display", {})
    symbol = display.get("currency_symbol", "Rs")

    if not embedded:

        st.title("Monthly Report")
    ui.note(
        "Everything on this page is computed live from the MAIN tab for the month "
        "you pick. Green, amber and red follow the limits set on the Settings page."
    )
    if main.empty:
        ui.empty_state("No order rows found in the MAIN tab.")
        return

    picker, compare = st.columns([1, 1])
    with picker:
        ym = common.month_picker(bundle, "Report month", key="monthly_month")
    prev_ym = metrics.previous_ym(ym)
    with compare:
        options = ui.month_options(bundle.months)
        default = next((lab for lab, v in options.items() if v == prev_ym), None)
        labels = ["(previous month)"] + list(options.keys())
        chosen = st.selectbox(
            "Compare against", labels,
            index=labels.index(default) if default else 0,
            key="monthly_compare",
        )
        baseline_ym = prev_ym if chosen == "(previous month)" else options[chosen]

    period = metrics.slice_month(main, ym)
    baseline = metrics.slice_month(main, baseline_ym)
    kpis = metrics.compute_kpis(period)
    base_kpis = metrics.compute_kpis(baseline)

    label = pd.to_datetime(ym + "-01").strftime("%B %Y")
    base_label = (
        pd.to_datetime(baseline_ym + "-01").strftime("%B %Y")
        if baseline_ym else "n/a"
    )

    if period.empty:
        ui.empty_state(f"No orders recorded for {label}.")
        return

    findings, summary = common.audit_results(bundle, config)
    month_summary = summary.loc[period.index]
    health = audit.health_score(month_summary)
    month_findings = findings[findings["ym"] == ym]

    # ---- executive summary --------------------------------------------
    st.subheader(f"{label} at a glance")
    ui.chips(
        [
            (f"{kpis['total_orders']} orders", "grey"),
            (f"{kpis['net_orders']} net", "grey"),
            (f"{ui.fmt_money(kpis['order_value'], symbol, compact=True)} funded", "grey"),
            (f"{kpis['interns_active']} interns", "grey"),
            (f"{kpis['products']} products", "grey"),
            (f"{health['red']} red rows", "red" if health["red"] else "green"),
            (f"{health['amber']} warnings", "amber" if health["amber"] else "green"),
        ]
    )
    lines = common.headline_findings(kpis, config, health)
    ui.callout(
        lines or [f"Every tracked KPI for {label} is inside its green band."],
        common.worst_tone(lines) if lines else "green",
        title="Automated findings",
    )

    st.markdown(f"**Volume and fulfilment** — deltas vs {base_label}")
    ui.render_kpis(common.volume_kpis(kpis, config, base_kpis), config)
    st.markdown(f"**Review pipeline** — deltas vs {base_label}")
    ui.render_kpis(common.review_kpis(kpis, config, base_kpis), config)
    st.markdown(f"**Money** — deltas vs {base_label}")
    ui.render_kpis(common.money_kpis(kpis, config, base_kpis), config)

    # ---- month vs baseline table ---------------------------------------
    ui.section("Month on month", f"{label} against {base_label}.")
    ui.show_table(
        common.comparison_table({label: kpis, base_label: base_kpis}, config)
    )

    # ---- breakdowns ----------------------------------------------------
    tab_interns, tab_products, tab_status, tab_targets, tab_rows = st.tabs(
        ["By intern", "By product", "Status & payment", "Targets", "Order rows"]
    )

    with tab_interns:
        scored = metrics.attach_roster(
            metrics.score_interns(
                period,
                min_orders=int(display.get("intern_min_orders_for_grading", 5) or 5),
            ),
            bundle.roster,
        )
        if scored.empty:
            ui.empty_state("No intern activity this month.")
        else:
            view = scored.assign(
                Orders=scored["total_orders"],
                Net=scored["net_orders"],
                Submitted=scored["review_submitted"],
                Reflected=scored["review_reflected"],
            )[
                ["intern", "roster_status", "Orders", "Net", "Submitted", "Reflected",
                 "reflection_rate", "order_submission_rate", "delivery_rate",
                 "checker_verified_rate", "score", "grade"]
            ].rename(columns={
                "intern": "Intern", "roster_status": "Status",
                "reflection_rate": "Reflection %",
                "order_submission_rate": "Submission %",
                "delivery_rate": "Delivery %",
                "checker_verified_rate": "Checker %",
                "score": "Score", "grade": "Grade",
            })
            st.dataframe(
                ui.grade_styler(view, {
                    "Reflection %": "reflection_rate",
                    "Submission %": "order_submission_rate",
                    "Delivery %": "delivery_rate",
                    "Checker %": "checker_verified_rate",
                }, config).format({
                    "Reflection %": "{:.1f}", "Submission %": "{:.1f}",
                    "Delivery %": "{:.1f}", "Checker %": "{:.1f}", "Score": "{:.1f}",
                }, na_rep="-"),
                width="stretch", hide_index=True,
            )

    with tab_products:
        prod = metrics.by_dimension(period, "product")
        if prod.empty:
            ui.empty_state("No product data this month.")
        else:
            fig = go.Figure(go.Bar(
                x=prod["total_orders"].head(15),
                y=prod["product"].head(15),
                orientation="h", marker_color="#0F766E",
                text=prod["total_orders"].head(15), textposition="auto",
            ))
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(title="Orders by product", xaxis_title="Orders")
            ui.show_chart(fig, height=max(260, 30 * min(15, len(prod))), legend=False)
            ui.show_table(_product_view(prod, symbol))

    with tab_status:
        col_a, col_b = st.columns(2)
        with col_a:
            status = metrics.status_breakdown(period)
            ui.show_table(status.rename(columns={
                "status": "Amazon status", "orders": "Orders",
                "value": "Order value", "share_pct": "Share %",
            }))
        with col_b:
            pay = metrics.payment_breakdown(period)
            ui.show_table(pay.rename(columns={
                "payment_state": "Payment state", "orders": "Orders",
                "value": "Order value", "share_pct": "Share %",
            }))
        ui.source_note(
            "Payment state folds the free-text REVIEW PAYMENT column into "
            "PAID / PENDING / CANCELLED / HOLD / UNKNOWN."
        )

    with tab_targets:
        tv = metrics.targets_vs_actual(main, bundle.targets, ym)
        with_target = tv[tv["has_target"]] if not tv.empty and "has_target" in tv else pd.DataFrame()
        if with_target.empty:
            ui.empty_state(
                f"The Monthly Targets Report tab has no target set for {label}. "
                "Targets on that tab currently cover July only."
            )
        else:
            ui.render_kpis(
                [
                    ui.kpi("", _overall_achievement(with_target),
                           kpi_key="target_achievement", config=config,
                           sub=f"{len(with_target)} products with a target"),
                    ui.kpi("Target Orders", with_target["target"].sum(), unit="n",
                           tone="neutral"),
                    ui.kpi("Actual Orders", with_target["actual"].sum(), unit="n",
                           tone="neutral"),
                ],
                config,
            )
            view = with_target.rename(columns={
                "product": "Product", "target": "Target", "actual": "Actual",
                "delivered_actual": "Delivered", "variance": "Variance",
                "achievement_pct": "Achievement %",
            })[["Product", "Target", "Actual", "Delivered", "Variance", "Achievement %"]]
            st.dataframe(
                ui.grade_styler(view, {"Achievement %": "target_achievement"}, config)
                .format({"Achievement %": "{:.1f}", "Target": "{:.0f}",
                         "Actual": "{:.0f}", "Delivered": "{:.0f}",
                         "Variance": "{:+.0f}"}, na_rep="-"),
                width="stretch", hide_index=True,
            )

        pv = metrics.productwise_actual_variance(main, bundle.targets, ym)
        if not pv.empty:
            mismatched = pv[~pv["match"]]
            ui.section(
                "Does the sheet's own productwise grid tie to MAIN?",
                "Left-hand grid of the Monthly Targets Report tab vs a live count.",
            )
            if mismatched.empty:
                ui.callout(["Every product ties exactly to MAIN for this month."],
                           "green")
            else:
                ui.callout(
                    [
                        f"{len(mismatched)} product rows do not tie. Usually a spelling "
                        "variant in PRODUCT NAME splitting one product into two."
                    ],
                    "amber",
                )
                ui.show_table(
                    mismatched.rename(columns={
                        "product": "Product", "sheet_orders": "Sheet grid",
                        "app_orders": "Live from MAIN", "difference": "Difference",
                    })[["Product", "Sheet grid", "Live from MAIN", "Difference"]]
                )

    with tab_rows:
        rows = common.attach_severity(period, summary)
        only_flagged = st.toggle("Only rows with an exception", value=False,
                                 key="monthly_only_flagged")
        if only_flagged:
            rows = rows[rows["severity"] != "ok"]
        view = _row_view(rows)
        st.dataframe(
            ui.severity_styler(view).format({"Order price": "{:,.0f}"}, na_rep="-"),
            width="stretch", hide_index=True, height=460,
        )
        ui.source_note(f"{len(view):,} rows. 'Sheet row' is the row number in the MAIN tab.")

    # ---- exceptions for the month --------------------------------------
    ui.section(f"Exceptions raised in {label}")
    if month_findings.empty:
        ui.callout(["No audit rule fired for this month."], "green")
    else:
        grouped = (
            month_findings.groupby(["group", "rule", "severity"], as_index=False)
            .agg(Rows=("order_id", "size"), Exposed=("order_price", "sum"))
            .sort_values("Rows", ascending=False)
        )
        grouped["Exposed"] = grouped["Exposed"].map(
            lambda v: ui.fmt_money(v, symbol, compact=True)
        )
        ui.show_table(grouped.rename(columns={
            "group": "Area", "rule": "Rule", "severity": "Severity",
        }))

    # ---- exports -------------------------------------------------------
    ui.section("Download this report")
    ui.download_row(
        {
            "summary": common.comparison_table({label: kpis, base_label: base_kpis}, config),
            "order rows": _row_view(common.attach_severity(period, summary)),
            "exceptions": month_findings,
        },
        excel_name=f"monthly-{ym}",
        key_prefix=f"monthly-{ym}",
    )


def _overall_achievement(with_target: pd.DataFrame) -> float | None:
    target = float(with_target["target"].sum())
    if not target:
        return None
    return round(100.0 * float(with_target["actual"].sum()) / target, 1)


def _product_view(prod: pd.DataFrame, symbol: str) -> pd.DataFrame:
    return prod.assign(
        **{
            "Order value": prod["order_value"].map(lambda v: ui.fmt_money(v, symbol)),
        }
    ).rename(columns={
        "product": "Product", "total_orders": "Orders", "net_orders": "Net",
        "returned": "Returned", "review_submitted": "Submitted",
        "review_reflected": "Reflected", "reflection_rate": "Reflection %",
        "return_rate": "Return %",
    })[[
        "Product", "Orders", "Net", "Returned", "Submitted", "Reflected",
        "Reflection %", "Return %", "Order value",
    ]]


def _row_view(rows: pd.DataFrame) -> pd.DataFrame:
    out = rows.copy()
    out["Order date"] = out["order_date"].dt.strftime("%d %b %Y")
    return out.rename(columns={
        "sheet_row": "Sheet row", "order_id": "Order ID", "intern": "Intern",
        "product": "Product", "asin": "ASIN", "status": "Amazon status",
        "payment_state": "Payment", "order_price": "Order price",
        "severity": "severity", "rules": "Exceptions",
    })[[
        "Sheet row", "Order date", "Order ID", "Intern", "Product", "ASIN",
        "Amazon status", "Payment", "Order price", "severity", "Exceptions",
    ]]
