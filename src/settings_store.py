"""Configurable thresholds: KPI colour bands + row-level audit rules.

Everything the Settings page can edit lives here as a plain dict so it can be
serialised to config/thresholds.json, downloaded, and committed to the repo.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "thresholds.json"

# ---------------------------------------------------------------------------
# KPI colour bands
#   mode = higher_better -> green if v >= green, amber if v >= amber, else red
#   mode = lower_better  -> green if v <= green, amber if v <= amber, else red
#   mode = between       -> green if min <= v <= max, amber if within `slack`
#                           of that window, else red
# ---------------------------------------------------------------------------
DEFAULT_KPIS: dict[str, dict[str, Any]] = {
    "reflection_rate": {
        "label": "Reflection Rate", "unit": "%", "mode": "higher_better",
        "green": 90.0, "amber": 75.0,
        "help": "Reviews reflected / reviews submitted. Are submitted reviews actually going live?",
    },
    "order_submission_rate": {
        "label": "Order Submission %", "unit": "%", "mode": "between",
        "min": 90.0, "max": 105.0, "slack": 10.0,
        "help": "Reviews submitted / net orders. Above 100% means more submissions than net orders, so check for double counting.",
    },
    "cancellation_rate": {
        "label": "Cancellation / Not-Delivered %", "unit": "%", "mode": "lower_better",
        "green": 10.0, "amber": 20.0,
        "help": "Orders not marked 'Shipped - Delivered to Buyer', over total orders. This is the sheet's own Cancellation% definition.",
    },
    "true_cancel_rate": {
        "label": "True Cancelled %", "unit": "%", "mode": "lower_better",
        "green": 3.0, "amber": 7.0,
        "help": "Only rows whose Amazon status is exactly 'Cancelled'.",
    },
    "return_rate": {
        "label": "Return Rate", "unit": "%", "mode": "lower_better",
        "green": 5.0, "amber": 10.0,
        "help": "Orders with a return status, over total orders.",
    },
    "delivery_rate": {
        "label": "Delivery Rate", "unit": "%", "mode": "higher_better",
        "green": 90.0, "amber": 80.0,
        "help": "Orders delivered to buyer, over total orders.",
    },
    "seller_feedback_rate": {
        "label": "Seller Feedback Rate", "unit": "%", "mode": "higher_better",
        "green": 60.0, "amber": 35.0,
        "help": "Seller feedback given, over reviews submitted.",
    },
    "checker_verified_rate": {
        "label": "Checker Verified %", "unit": "%", "mode": "higher_better",
        "green": 90.0, "amber": 70.0,
        "help": "Rows signed off by the checker, over reviews submitted. Low means a verification backlog.",
    },
    "payment_done_rate": {
        "label": "Payment Completion %", "unit": "%", "mode": "higher_better",
        "green": 95.0, "amber": 85.0,
        "help": "Orders with payment marked Paid or Settled, over total orders.",
    },
    "payment_pending_amt": {
        "label": "Payment Pending", "unit": "Rs", "mode": "lower_better",
        "green": 5000.0, "amber": 25000.0,
        "help": "Order value we still owe: payment neither Paid nor Cancelled.",
    },
    "paid_unreflected_amt": {
        "label": "Paid but Review Not Reflected", "unit": "Rs", "mode": "lower_better",
        "green": 10000.0, "amber": 50000.0,
        "help": "Money already paid out where the review has not reflected. This is the main recovery exposure.",
    },
    "paid_undelivered_amt": {
        "label": "Paid but Not Delivered", "unit": "Rs", "mode": "lower_better",
        "green": 5000.0, "amber": 20000.0,
        "help": "Money paid on orders that were cancelled or returned.",
    },
    "unreconciled_amt": {
        "label": "Unreconciled with Amazon", "unit": "Rs", "mode": "lower_better",
        "green": 5000.0, "amber": 25000.0,
        "help": "Order value of rows with no Amazon Price captured.",
    },
    "exception_rate": {
        "label": "Rows with Exceptions %", "unit": "%", "mode": "lower_better",
        "green": 10.0, "amber": 25.0,
        "help": "Share of orders tripping at least one audit rule.",
    },
    "target_achievement": {
        "label": "Target Achievement %", "unit": "%", "mode": "higher_better",
        "green": 90.0, "amber": 70.0,
        "help": "Actual orders vs the Monthly Targets Report, per product.",
    },
}

# ---------------------------------------------------------------------------
# Row-level audit rules. `severity` drives the red / amber colouring.
# ---------------------------------------------------------------------------
DEFAULT_RULES: dict[str, dict[str, Any]] = {
    "missing_mandatory": {
        "label": "Mandatory field blank", "severity": "red", "enabled": True,
        "group": "Data integrity", "params": {},
        "help": "Order ID, ASIN, intern name or order date is empty.",
    },
    "duplicate_order_id": {
        "label": "Duplicate Order ID", "severity": "red", "enabled": True,
        "group": "Data integrity", "params": {},
        "help": "The same Amazon order ID appears on more than one row.",
    },
    "future_order_date": {
        "label": "Order date in the future", "severity": "red", "enabled": True,
        "group": "Data integrity", "params": {},
        "help": "Order date is later than today.",
    },
    "order_price_range": {
        "label": "Order price outside expected range", "severity": "amber", "enabled": True,
        "group": "Data integrity", "params": {"min": 150.0, "max": 3000.0},
        "help": "Order price below the minimum or above the maximum. Catches typos and stray decimals.",
    },
    "status_blank": {
        "label": "Amazon status blank", "severity": "amber", "enabled": True,
        "group": "Fulfilment", "params": {"days": 3},
        "help": "No Amazon status this many days after the order date.",
    },
    "stuck_in_transit": {
        "label": "Stuck in transit", "severity": "amber", "enabled": True,
        "group": "Fulfilment", "params": {"days": 14},
        "help": "Still Shipped / Pending / Out for Delivery this many days after ordering.",
    },
    "review_link_sla": {
        "label": "Review not submitted within SLA", "severity": "red", "enabled": True,
        "group": "Review pipeline", "params": {"days": 10},
        "help": "Order delivered but no review link this many days after the order date.",
    },
    "reflect_sla": {
        "label": "Review submitted but not reflected within SLA", "severity": "amber", "enabled": True,
        "group": "Review pipeline", "params": {"days": 15},
        "help": "Review link present but reflection still false after this many days.",
    },
    "reflected_without_link": {
        "label": "Marked reflected without a review link", "severity": "red", "enabled": True,
        "group": "Review pipeline", "params": {},
        "help": "Reflection is TRUE but there is no review link, so it cannot be verified.",
    },
    "checker_pending": {
        "label": "Checker sign-off pending", "severity": "amber", "enabled": True,
        "group": "Review pipeline", "params": {"days": 20},
        "help": "Review submitted this many days ago and the checker has still not verified it.",
    },
    "seller_feedback_missing": {
        "label": "Seller feedback missing on a reflected order", "severity": "amber", "enabled": True,
        "group": "Review pipeline", "params": {},
        "help": "Review reflected but no seller feedback recorded.",
    },
    "payment_pending_age": {
        "label": "Payment pending too long", "severity": "red", "enabled": True,
        "group": "Money", "params": {"days": 15},
        "help": "Payment still not Paid or Settled this many days after the order date.",
    },
    "payment_unknown": {
        "label": "Payment status unrecognised or on hold", "severity": "amber", "enabled": True,
        "group": "Money", "params": {},
        "help": "Payment text does not resolve to Paid, Pending or Cancelled.",
    },
    "paid_not_reflected": {
        "label": "Paid but review not reflected", "severity": "red", "enabled": True,
        "group": "Money", "params": {"days": 15},
        "help": "Money paid out this many days ago and the review still has not reflected.",
    },
    "paid_not_delivered": {
        "label": "Paid but order not delivered", "severity": "red", "enabled": True,
        "group": "Money", "params": {},
        "help": "Payment marked Paid on an order that was cancelled or returned.",
    },
    "amazon_price_missing": {
        "label": "Amazon price not captured", "severity": "amber", "enabled": True,
        "group": "Money", "params": {"days": 7},
        "help": "Delivered order with no Amazon price this many days after ordering.",
    },
    "amazon_price_gap": {
        "label": "Order vs Amazon price mismatch", "severity": "amber", "enabled": True,
        "group": "Money", "params": {"tolerance": 50.0},
        "help": "Absolute difference between order price and Amazon price exceeds the tolerance.",
    },
    "return_no_signoff": {
        "label": "Return without checker sign-off", "severity": "red", "enabled": True,
        "group": "Returns", "params": {},
        "help": "Return status recorded but the return checker column is not OK.",
    },
    "return_no_pickup": {
        "label": "Return with no pickup partner", "severity": "amber", "enabled": True,
        "group": "Returns", "params": {},
        "help": "Return status recorded but 'Return Pickup By' is blank.",
    },
    "unknown_intern": {
        "label": "Intern not on the roster", "severity": "amber", "enabled": True,
        "group": "Interns", "params": {},
        "help": "Intern name in MAIN has no match in the Intern Report Manual roster.",
    },
    "order_outside_tenure": {
        "label": "Order outside the intern tenure", "severity": "amber", "enabled": True,
        "group": "Interns", "params": {"grace_days": 7},
        "help": "Order date falls before joining or after leaving, beyond the grace period.",
    },
    "not_in_amazon_report": {
        "label": "Order ID missing from the Amazon report", "severity": "amber", "enabled": True,
        "group": "Reconciliation", "params": {},
        "help": "Order ID in MAIN has no match in 'Amazon Order Report Pasting'.",
    },
}

DEFAULT_DISPLAY: dict[str, Any] = {
    "green_hex": "#059669",
    "amber_hex": "#D97706",
    "red_hex": "#DC2626",
    "neutral_hex": "#64748B",
    "cache_ttl_minutes": 10,
    "week_days": 7,
    "currency_symbol": "Rs",
    "intern_min_orders_for_grading": 5,
    "tenure_days": 30,
    "intern_idle_days": 3,
    "intern_cancel_alert_pct": 30.0,
}

DEFAULTS: dict[str, Any] = {
    "kpis": DEFAULT_KPIS,
    "rules": DEFAULT_RULES,
    "display": DEFAULT_DISPLAY,
}


def default_config() -> dict[str, Any]:
    return copy.deepcopy(DEFAULTS)


def _merge(base: dict, override: dict) -> dict:
    """Deep-merge saved values onto defaults so new keys survive an old config file."""
    out = copy.deepcopy(base)
    for key, val in (override or {}).items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = _merge(out[key], val)
        else:
            out[key] = val
    return out


def load_config() -> dict[str, Any]:
    cfg = default_config()
    if CONFIG_PATH.exists():
        try:
            saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            cfg = _merge(cfg, saved)
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg: dict[str, Any]) -> tuple[bool, str]:
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        return True, str(CONFIG_PATH)
    except OSError as exc:
        return False, str(exc)


def config_from_json(raw: str) -> dict[str, Any]:
    return _merge(default_config(), json.loads(raw))


def grade(value: float | None, spec: dict[str, Any]) -> str:
    """Return 'green', 'amber', 'red' or 'neutral' for a KPI value."""
    if value is None:
        return "neutral"
    try:
        val = float(value)
    except (TypeError, ValueError):
        return "neutral"
    if val != val:  # NaN
        return "neutral"

    mode = spec.get("mode", "higher_better")
    if mode == "higher_better":
        if val >= float(spec.get("green", 0)):
            return "green"
        if val >= float(spec.get("amber", 0)):
            return "amber"
        return "red"
    if mode == "lower_better":
        if val <= float(spec.get("green", 0)):
            return "green"
        if val <= float(spec.get("amber", 0)):
            return "amber"
        return "red"
    if mode == "between":
        lo, hi = float(spec.get("min", 0)), float(spec.get("max", 100))
        slack = float(spec.get("slack", 0))
        if lo <= val <= hi:
            return "green"
        if lo - slack <= val <= hi + slack:
            return "amber"
        return "red"
    return "neutral"
