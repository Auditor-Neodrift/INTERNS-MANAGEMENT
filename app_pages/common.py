"""Helpers shared by the pages: cached audit runs and reusable KPI blocks."""
from __future__ import annotations

import json
from datetime import date

import pandas as pd
import streamlit as st

import audit
import metrics
import ui


def _config_key(config: dict) -> str:
    return json.dumps(config, sort_keys=True, default=str)


@st.cache_data(ttl=600, show_spinner=False)
def _evaluate_cached(
    main: pd.DataFrame,
    roster: pd.DataFrame,
    amazon: pd.DataFrame,
    config_json: str,
    today_iso: str,
):
    config = json.loads(config_json)
    return audit.evaluate(
        main, config,
        roster=roster, amazon=amazon,
        today=date.fromisoformat(today_iso),
    )


def audit_results(bundle, config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(findings, row_summary) for the whole of MAIN, cached per config."""
    return _evaluate_cached(
        bundle.main, bundle.roster, bundle.amazon,
        _config_key(config), date.today().isoformat(),
    )


@st.cache_data(ttl=600, show_spinner=False)
def monthly_series(main: pd.DataFrame) -> pd.DataFrame:
    return metrics.monthly_series(main)


@st.cache_data(ttl=600, show_spinner=False)
def weekly_series(main: pd.DataFrame, weeks: int = 12) -> pd.DataFrame:
    return metrics.weekly_series(main, weeks)


def attach_severity(main: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    """Add the audit verdict columns onto MAIN rows."""
    cols = ["severity", "red_count", "amber_count", "total_issues", "rules"]
    present = [c for c in cols if c in summary.columns]
    return main.join(summary[present])


# ---------------------------------------------------------------------------
# Month picker
# ---------------------------------------------------------------------------
def month_picker(
    bundle, label: str = "Report month", key: str = "month", help_text: str | None = None
) -> str:
    """Month selectbox defaulting to the current (or newest available) month."""
    months = bundle.months
    if not months:
        return metrics.current_ym()
    options = ui.month_options(months)
    labels = list(options.keys())
    default = metrics.current_ym(bundle.main)
    default_label = next((lab for lab, ym in options.items() if ym == default), labels[0])
    chosen = st.selectbox(
        label, labels, index=labels.index(default_label), key=key, help=help_text
    )
    return options[chosen]


# ---------------------------------------------------------------------------
# Reusable KPI blocks
# ---------------------------------------------------------------------------
def volume_kpis(kpis: dict, config: dict, prev: dict | None = None) -> list[dict]:
    prev = prev or {}
    return [
        ui.kpi("Total Orders", kpis.get("total_orders"), unit="n", tone="neutral",
               delta=ui.delta_of(kpis.get("total_orders"), prev.get("total_orders")),
               higher_is_better=True,
               help_text="Every order row in MAIN for this period."),
        ui.kpi("Net Orders", kpis.get("net_orders"), unit="n", tone="neutral",
               sub="delivered to buyer",
               delta=ui.delta_of(kpis.get("net_orders"), prev.get("net_orders")),
               higher_is_better=True,
               help_text="Total orders minus orders not marked delivered."),
        ui.kpi("", kpis.get("delivery_rate"), kpi_key="delivery_rate", config=config,
               delta=ui.delta_of(kpis.get("delivery_rate"), prev.get("delivery_rate")),
               higher_is_better=True),
        ui.kpi("", kpis.get("cancellation_rate"), kpi_key="cancellation_rate",
               config=config, sub=f"{kpis.get('not_delivered', 0)} orders",
               delta=ui.delta_of(kpis.get("cancellation_rate"), prev.get("cancellation_rate")),
               higher_is_better=False),
        ui.kpi("Cancelled (true status)", kpis.get("true_cancelled"), unit="n",
               kpi_key=None, config=config, tone="neutral",
               sub="status is exactly Cancelled",
               help_text="Rows whose Amazon status is literally 'Cancelled', as opposed to the wider not-delivered definition."),
        ui.kpi("", kpis.get("return_rate"), kpi_key="return_rate", config=config,
               sub=f"{kpis.get('returned', 0)} returned",
               delta=ui.delta_of(kpis.get("return_rate"), prev.get("return_rate")),
               higher_is_better=False),
    ]


def review_kpis(kpis: dict, config: dict, prev: dict | None = None) -> list[dict]:
    prev = prev or {}
    return [
        ui.kpi("Reviews Submitted", kpis.get("review_submitted"), unit="n",
               tone="neutral", sub="review link present",
               delta=ui.delta_of(kpis.get("review_submitted"), prev.get("review_submitted")),
               higher_is_better=True),
        ui.kpi("", kpis.get("order_submission_rate"), kpi_key="order_submission_rate",
               config=config,
               delta=ui.delta_of(kpis.get("order_submission_rate"), prev.get("order_submission_rate")),
               higher_is_better=True),
        ui.kpi("Reviews Reflected", kpis.get("review_reflected"), unit="n",
               tone="neutral",
               delta=ui.delta_of(kpis.get("review_reflected"), prev.get("review_reflected")),
               higher_is_better=True),
        ui.kpi("", kpis.get("reflection_rate"), kpi_key="reflection_rate", config=config,
               delta=ui.delta_of(kpis.get("reflection_rate"), prev.get("reflection_rate")),
               higher_is_better=True),
        ui.kpi("Not Reflected", kpis.get("review_not_reflected"), unit="n",
               tone="amber" if kpis.get("review_not_reflected") else "green",
               help_text="Submitted reviews that have not gone live."),
        ui.kpi("", kpis.get("seller_feedback_rate"), kpi_key="seller_feedback_rate",
               config=config, sub=f"{kpis.get('seller_feedback', 0)} given",
               delta=ui.delta_of(kpis.get("seller_feedback_rate"), prev.get("seller_feedback_rate")),
               higher_is_better=True),
        ui.kpi("", kpis.get("checker_verified_rate"), kpi_key="checker_verified_rate",
               config=config, sub=f"{kpis.get('checker_pending', 0)} pending",
               delta=ui.delta_of(kpis.get("checker_verified_rate"), prev.get("checker_verified_rate")),
               higher_is_better=True),
    ]


def money_kpis(kpis: dict, config: dict, prev: dict | None = None) -> list[dict]:
    prev = prev or {}
    return [
        ui.kpi("Order Value Funded", kpis.get("order_value"), unit="Rs",
               tone="neutral",
               delta=ui.delta_of(kpis.get("order_value"), prev.get("order_value")),
               higher_is_better=None,
               help_text="Sum of ORDER PRICE - what the company funds for these orders."),
        ui.kpi("", kpis.get("payment_pending_amt"), kpi_key="payment_pending_amt",
               config=config,
               sub=f"{kpis.get('payment_pending_count', 0)} orders unpaid"),
        ui.kpi("", kpis.get("paid_unreflected_amt"), kpi_key="paid_unreflected_amt",
               config=config,
               sub=f"{kpis.get('paid_unreflected_count', 0)} orders"),
        ui.kpi("", kpis.get("paid_undelivered_amt"), kpi_key="paid_undelivered_amt",
               config=config,
               sub=f"{kpis.get('paid_undelivered_count', 0)} orders"),
        ui.kpi("", kpis.get("unreconciled_amt"), kpi_key="unreconciled_amt",
               config=config,
               sub=f"{kpis.get('unreconciled_count', 0)} without Amazon price"),
        ui.kpi("", kpis.get("payment_done_rate"), kpi_key="payment_done_rate",
               config=config, sub=f"{kpis.get('paid_count', 0)} paid"),
        ui.kpi("Avg Order Value", kpis.get("avg_order_value"), unit="Rs",
               tone="neutral",
               delta=ui.delta_of(kpis.get("avg_order_value"), prev.get("avg_order_value")),
               higher_is_better=None),
    ]


# ---------------------------------------------------------------------------
# Comparison table
# ---------------------------------------------------------------------------
COMPARISON_ROWS: list[tuple[str, str, str]] = [
    ("Total orders", "total_orders", "n"),
    ("Net orders (delivered)", "net_orders", "n"),
    ("Not delivered / cancelled", "not_delivered", "n"),
    ("Cancellation %", "cancellation_rate", "%"),
    ("Returned", "returned", "n"),
    ("Return rate", "return_rate", "%"),
    ("Reviews submitted", "review_submitted", "n"),
    ("Order submission %", "order_submission_rate", "%"),
    ("Reviews reflected", "review_reflected", "n"),
    ("Reflection rate", "reflection_rate", "%"),
    ("Seller feedback", "seller_feedback", "n"),
    ("Checker pending", "checker_pending", "n"),
    ("Order value funded", "order_value", "Rs"),
    ("Payment pending", "payment_pending_amt", "Rs"),
    ("Paid but not reflected", "paid_unreflected_amt", "Rs"),
    ("Active interns", "interns_active", "n"),
]


def comparison_table(periods: dict[str, dict], config: dict) -> pd.DataFrame:
    """Metrics down the rows, periods across the columns, pre-formatted."""
    symbol = config.get("display", {}).get("currency_symbol", "Rs")
    rows = []
    for label, key, unit in COMPARISON_ROWS:
        row: dict[str, object] = {"Metric": label}
        for period_name, kpis in periods.items():
            row[period_name] = ui.fmt_value(kpis.get(key), unit, symbol)
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Narrative
# ---------------------------------------------------------------------------
def headline_findings(kpis: dict, config: dict, health: dict | None = None) -> list[str]:
    """Plain-language callouts for the period, worst first."""
    from settings_store import grade

    specs = config.get("kpis", {})
    symbol = config.get("display", {}).get("currency_symbol", "Rs")
    lines: list[tuple[int, str]] = []

    def add(kpi_key: str, template: str, value, *, invert_ok: bool = False) -> None:
        spec = specs.get(kpi_key, {})
        sev = grade(value, spec)
        if sev == "red":
            lines.append((0, f"<strong>Red:</strong> {template}"))
        elif sev == "amber":
            lines.append((1, f"<strong>Watch:</strong> {template}"))
        elif invert_ok and sev == "green":
            lines.append((2, f"<strong>On track:</strong> {template}"))

    add("reflection_rate",
        f"reflection rate is {ui.fmt_pct(kpis.get('reflection_rate'))} "
        f"({kpis.get('review_not_reflected', 0)} submitted reviews have not gone live).",
        kpis.get("reflection_rate"))
    add("cancellation_rate",
        f"{kpis.get('not_delivered', 0)} of {kpis.get('total_orders', 0)} orders were not "
        f"delivered ({ui.fmt_pct(kpis.get('cancellation_rate'))}).",
        kpis.get("cancellation_rate"))
    add("return_rate",
        f"{kpis.get('returned', 0)} orders came back as returns "
        f"({ui.fmt_pct(kpis.get('return_rate'))}, "
        f"{ui.fmt_money(kpis.get('returned_amt'), symbol)} of goods).",
        kpis.get("return_rate"))
    add("paid_unreflected_amt",
        f"{ui.fmt_money(kpis.get('paid_unreflected_amt'), symbol)} is paid out across "
        f"{kpis.get('paid_unreflected_count', 0)} orders whose review has not reflected.",
        kpis.get("paid_unreflected_amt"))
    add("payment_pending_amt",
        f"{ui.fmt_money(kpis.get('payment_pending_amt'), symbol)} of orders is still unpaid "
        f"({kpis.get('payment_pending_count', 0)} orders).",
        kpis.get("payment_pending_amt"))
    add("paid_undelivered_amt",
        f"{ui.fmt_money(kpis.get('paid_undelivered_amt'), symbol)} was paid on "
        f"{kpis.get('paid_undelivered_count', 0)} orders that were cancelled or returned.",
        kpis.get("paid_undelivered_amt"))
    add("checker_verified_rate",
        f"checker has verified {ui.fmt_pct(kpis.get('checker_verified_rate'))} of submissions "
        f"({kpis.get('checker_pending', 0)} waiting).",
        kpis.get("checker_verified_rate"))
    add("unreconciled_amt",
        f"{ui.fmt_money(kpis.get('unreconciled_amt'), symbol)} of orders has no Amazon price "
        "captured yet.",
        kpis.get("unreconciled_amt"))
    add("order_submission_rate",
        f"order submission is {ui.fmt_pct(kpis.get('order_submission_rate'))} of net orders.",
        kpis.get("order_submission_rate"))

    if health and health.get("clean_pct") is not None:
        sev = grade(100 - float(health["clean_pct"]), specs.get("exception_rate", {}))
        if sev in ("red", "amber"):
            word = "Red" if sev == "red" else "Watch"
            lines.append((
                0 if sev == "red" else 1,
                f"<strong>{word}:</strong> {health['red']} rows have a red exception and "
                f"{health['amber']} have a warning; only {ui.fmt_pct(health['clean_pct'])} "
                "of rows are clean.",
            ))

    lines.sort(key=lambda item: item[0])
    return [text for _, text in lines]


def worst_tone(lines: list[str]) -> str:
    joined = " ".join(lines)
    if "Red:" in joined:
        return "red"
    if "Watch:" in joined:
        return "amber"
    return "green"
