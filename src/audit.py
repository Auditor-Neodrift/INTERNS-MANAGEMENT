"""Row-level audit rule engine.

Each rule is a function that takes the normalised MAIN frame and returns a
boolean mask of offending rows. Severity, on/off and every numeric limit come
from the config the Settings page edits, so the team can retune the app
without touching code.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

import pandas as pd

FINDING_COLUMNS = [
    "sheet_row", "order_date", "ym", "order_id", "intern", "product",
    "status", "payment_state", "order_price", "rule_id", "rule",
    "severity", "group", "detail",
]


@dataclass
class AuditContext:
    """Everything a rule needs beyond MAIN itself."""
    roster: pd.DataFrame | None = None
    amazon: pd.DataFrame | None = None
    today: date | None = None

    def __post_init__(self) -> None:
        self.today = self.today or date.today()

    # -- roster helpers ----------------------------------------------------
    @property
    def roster_keys(self) -> set[str]:
        if self.roster is None or self.roster.empty:
            return set()
        return set(_name_key(self.roster["name"]))

    @property
    def roster_tenure(self) -> pd.DataFrame:
        if self.roster is None or self.roster.empty:
            return pd.DataFrame(columns=["_key", "joining_date", "leaving_date"])
        ros = self.roster.copy()
        ros["_key"] = _name_key(ros["name"])
        return ros.drop_duplicates("_key", keep="first")[
            ["_key", "joining_date", "leaving_date"]
        ]

    # -- amazon helpers ----------------------------------------------------
    @property
    def amazon_ids(self) -> set[str]:
        if self.amazon is None or self.amazon.empty:
            return set()
        return set(self.amazon["order_id"])

    @property
    def amazon_window(self) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
        """The Amazon report is a rolling export, so reconciliation only
        applies to orders inside the window it actually covers."""
        if self.amazon is None or self.amazon.empty:
            return None, None
        dates = self.amazon["purchase_date"].dropna()
        if dates.empty:
            return None, None
        return dates.min().normalize(), dates.max().normalize()


def _name_key(series: pd.Series) -> pd.Series:
    return (
        series.fillna("").astype(str).str.strip().str.casefold()
        .str.replace(r"\s+", " ", regex=True)
    )


def _false(df: pd.DataFrame) -> pd.Series:
    return pd.Series(False, index=df.index)


def _older_than(df: pd.DataFrame, days: float) -> pd.Series:
    """Rows whose order date is at least `days` old. Undated rows never age in."""
    return df["age_days"].fillna(-1) >= float(days)


# ---------------------------------------------------------------------------
# Rules. Signature: (df, params, ctx) -> boolean mask
# ---------------------------------------------------------------------------
def _r_missing_mandatory(df, params, ctx):
    return (
        (df["order_id"] == "")
        | (df["asin"] == "")
        | (df["intern"] == "")
        | df["order_date"].isna()
    )


def _r_duplicate_order_id(df, params, ctx):
    has_id = df["order_id"] != ""
    return has_id & df["order_id"].duplicated(keep=False)


def _r_future_order_date(df, params, ctx):
    return df["order_date"] > pd.Timestamp(ctx.today)


def _r_order_price_range(df, params, ctx):
    low = float(params.get("min", 0))
    high = float(params.get("max", 10**9))
    price = df["order_price"]
    return price.notna() & ((price < low) | (price > high))


def _r_status_blank(df, params, ctx):
    return df["status_blank"] & _older_than(df, params.get("days", 3))


def _r_stuck_in_transit(df, params, ctx):
    return df["in_transit"] & _older_than(df, params.get("days", 14))


def _r_review_link_sla(df, params, ctx):
    return (
        df["delivered"]
        & ~df["review_submitted"]
        & _older_than(df, params.get("days", 10))
    )


def _r_reflect_sla(df, params, ctx):
    return (
        df["review_submitted"]
        & ~df["reflected"]
        & _older_than(df, params.get("days", 15))
    )


def _r_reflected_without_link(df, params, ctx):
    return df["reflected"] & ~df["review_submitted"]


def _r_checker_pending(df, params, ctx):
    return (
        df["review_submitted"]
        & ~df["checker_ok"]
        & _older_than(df, params.get("days", 20))
    )


def _r_seller_feedback_missing(df, params, ctx):
    return df["reflected"] & ~df["seller_feedback"]


def _r_payment_pending_age(df, params, ctx):
    return df["is_payment_pending"] & _older_than(df, params.get("days", 15))


def _r_payment_unknown(df, params, ctx):
    return df["payment_state"].isin(["UNKNOWN", "HOLD"])


def _r_paid_not_reflected(df, params, ctx):
    return (
        df["is_paid"]
        & ~df["reflected"]
        & _older_than(df, params.get("days", 15))
    )


def _r_paid_not_delivered(df, params, ctx):
    return df["is_paid"] & df["not_delivered"]


def _r_amazon_price_missing(df, params, ctx):
    return (
        df["delivered"]
        & df["amazon_price"].isna()
        & _older_than(df, params.get("days", 7))
    )


def _r_amazon_price_gap(df, params, ctx):
    tolerance = float(params.get("tolerance", 50))
    gap = df["price_gap"]
    return gap.notna() & (gap.abs() > tolerance)


def _r_return_no_signoff(df, params, ctx):
    return df["returned"] & (df["return_checker"].str.upper() != "OK")


def _r_return_no_pickup(df, params, ctx):
    return df["returned"] & (df["return_pickup_by"] == "")


def _r_unknown_intern(df, params, ctx):
    keys = ctx.roster_keys
    if not keys:
        return _false(df)
    named = df["intern"] != ""
    return named & ~_name_key(df["intern"]).isin(keys)


def _r_order_outside_tenure(df, params, ctx):
    tenure = ctx.roster_tenure
    if tenure.empty:
        return _false(df)
    grace = pd.Timedelta(days=float(params.get("grace_days", 7)))
    joined = df.assign(_key=_name_key(df["intern"])).merge(
        tenure, on="_key", how="left"
    )
    joined.index = df.index
    before = joined["joining_date"].notna() & (
        df["order_date"] < joined["joining_date"] - grace
    )
    after = joined["leaving_date"].notna() & (
        df["order_date"] > joined["leaving_date"] + grace
    )
    return df["order_date"].notna() & (before | after)


def _r_not_in_amazon_report(df, params, ctx):
    ids = ctx.amazon_ids
    start, end = ctx.amazon_window
    if not ids or start is None:
        return _false(df)
    in_window = df["order_date"].between(start, end)
    return in_window & (df["order_id"] != "") & ~df["order_id"].isin(ids)


RULE_FUNCS: dict[str, Callable] = {
    "missing_mandatory": _r_missing_mandatory,
    "duplicate_order_id": _r_duplicate_order_id,
    "future_order_date": _r_future_order_date,
    "order_price_range": _r_order_price_range,
    "status_blank": _r_status_blank,
    "stuck_in_transit": _r_stuck_in_transit,
    "review_link_sla": _r_review_link_sla,
    "reflect_sla": _r_reflect_sla,
    "reflected_without_link": _r_reflected_without_link,
    "checker_pending": _r_checker_pending,
    "seller_feedback_missing": _r_seller_feedback_missing,
    "payment_pending_age": _r_payment_pending_age,
    "payment_unknown": _r_payment_unknown,
    "paid_not_reflected": _r_paid_not_reflected,
    "paid_not_delivered": _r_paid_not_delivered,
    "amazon_price_missing": _r_amazon_price_missing,
    "amazon_price_gap": _r_amazon_price_gap,
    "return_no_signoff": _r_return_no_signoff,
    "return_no_pickup": _r_return_no_pickup,
    "unknown_intern": _r_unknown_intern,
    "order_outside_tenure": _r_order_outside_tenure,
    "not_in_amazon_report": _r_not_in_amazon_report,
}


def _detail(rule_id: str, params: dict) -> str:
    """A short human-readable statement of the limit that was breached."""
    if "days" in params:
        return f"older than {params['days']:g} days"
    if "tolerance" in params:
        return f"difference over Rs {params['tolerance']:g}"
    if "min" in params and "max" in params:
        return f"outside Rs {params['min']:g} - Rs {params['max']:g}"
    if "grace_days" in params:
        return f"grace {params['grace_days']:g} days"
    return ""


def evaluate(
    main: pd.DataFrame,
    config: dict,
    roster: pd.DataFrame | None = None,
    amazon: pd.DataFrame | None = None,
    today: date | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run every enabled rule.

    Returns (findings, row_summary):
      findings    - one row per (order row, tripped rule)
      row_summary - one row per order row, with red/amber counts and the
                    worst severity, indexed like `main`
    """
    rules_cfg = config.get("rules", {})
    ctx = AuditContext(roster=roster, amazon=amazon, today=today)

    empty_findings = pd.DataFrame(columns=FINDING_COLUMNS)
    summary = pd.DataFrame(
        {
            "red_count": pd.Series(0, index=main.index, dtype=int),
            "amber_count": pd.Series(0, index=main.index, dtype=int),
        }
    )
    if main.empty:
        summary["severity"] = pd.Series(dtype=object)
        summary["rules"] = pd.Series(dtype=object)
        summary["total_issues"] = pd.Series(dtype=int)
        return empty_findings, summary

    frames: list[pd.DataFrame] = []
    rule_lists: list[pd.Series] = []

    for rule_id, spec in rules_cfg.items():
        func = RULE_FUNCS.get(rule_id)
        if func is None or not spec.get("enabled", True):
            continue
        params = spec.get("params", {}) or {}
        try:
            mask = func(main, params, ctx).fillna(False).astype(bool)
        except Exception:  # a malformed limit must not take the page down
            continue
        if not mask.any():
            continue

        severity = str(spec.get("severity", "amber")).lower()
        hit = main.loc[mask]
        frame = pd.DataFrame(
            {
                "sheet_row": hit["sheet_row"],
                "order_date": hit["order_date"],
                "ym": hit["ym"],
                "order_id": hit["order_id"],
                "intern": hit["intern"],
                "product": hit["product"],
                "status": hit["status"],
                "payment_state": hit["payment_state"],
                "order_price": hit["order_price"],
                "rule_id": rule_id,
                "rule": spec.get("label", rule_id),
                "severity": severity,
                "group": spec.get("group", "Other"),
                "detail": _detail(rule_id, params),
            }
        )
        frames.append(frame)
        summary[f"{severity}_count"] += mask.astype(int)
        rule_lists.append(
            pd.Series(spec.get("label", rule_id), index=hit.index, dtype=object)
        )

    findings = (
        pd.concat(frames, ignore_index=True) if frames else empty_findings
    )

    if rule_lists:
        stacked = pd.concat(rule_lists)
        summary["rules"] = (
            stacked.groupby(level=0).agg(lambda vals: "; ".join(sorted(set(vals))))
            .reindex(main.index).fillna("")
        )
    else:
        summary["rules"] = ""

    summary["severity"] = "ok"
    summary.loc[summary["amber_count"] > 0, "severity"] = "amber"
    summary.loc[summary["red_count"] > 0, "severity"] = "red"
    summary["total_issues"] = summary["red_count"] + summary["amber_count"]
    return findings, summary


def rule_summary(findings: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Counts and exposed value per rule, including rules with zero hits."""
    rules_cfg = config.get("rules", {})
    rows = []
    for rule_id, spec in rules_cfg.items():
        if rule_id not in RULE_FUNCS:
            continue
        hit = (
            findings[findings["rule_id"] == rule_id]
            if not findings.empty else findings
        )
        rows.append(
            {
                "rule_id": rule_id,
                "rule": spec.get("label", rule_id),
                "group": spec.get("group", "Other"),
                "severity": str(spec.get("severity", "amber")).lower(),
                "enabled": bool(spec.get("enabled", True)),
                "rows_flagged": int(len(hit)),
                "value_flagged": float(
                    hit["order_price"].fillna(0).sum() if len(hit) else 0.0
                ),
                "limit": _detail(rule_id, spec.get("params", {}) or {}),
                "help": spec.get("help", ""),
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(
        ["enabled", "rows_flagged"], ascending=[False, False]
    ).reset_index(drop=True)


def health_score(summary: pd.DataFrame) -> dict[str, float | int]:
    """A single clean-rows percentage for the dashboard headline."""
    total = int(len(summary))
    if not total:
        return {"total": 0, "clean": 0, "clean_pct": None, "red": 0, "amber": 0}
    red = int((summary["severity"] == "red").sum())
    amber = int((summary["severity"] == "amber").sum())
    clean = total - red - amber
    return {
        "total": total,
        "clean": clean,
        "clean_pct": round(100.0 * clean / total, 2),
        "red": red,
        "amber": amber,
        "red_pct": round(100.0 * red / total, 2),
        "amber_pct": round(100.0 * amber / total, 2),
    }
