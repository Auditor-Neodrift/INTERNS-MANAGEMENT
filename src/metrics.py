"""KPI computation.

Every metric here is derived from the MAIN tab. The core definitions were
reconciled row-for-row against the workbook's own "Overall Audit Report" tab
across all 12 live months, so the numbers this app shows and the numbers the
sheet shows agree - and where they do not, the Overall Audit page flags it.

Definitions that matter:
  net orders   = total orders - orders not marked "Shipped - Delivered to Buyer"
  cancelled    = orders not marked delivered  (the sheet's own "Cancellation%")
  submitted    = a review link is present
  reflection % = reflected / submitted
  submission % = submitted / net orders
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd


def _pct(numerator: float, denominator: float) -> float | None:
    if not denominator:
        return None
    return round(100.0 * float(numerator) / float(denominator), 2)


def _money(series: pd.Series) -> float:
    return float(series.fillna(0).sum())


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Element-wise divide that yields NaN instead of raising on a zero divisor.

    pandas 3 evaluates both arms of np.where, so the division has to be
    masked rather than selected after the fact.
    """
    num = pd.to_numeric(numerator, errors="coerce").astype(float)
    den = pd.to_numeric(denominator, errors="coerce").astype(float)
    return num.divide(den.where(den != 0))


def compute_kpis(df: pd.DataFrame) -> dict[str, object]:
    """Full KPI set for any slice of MAIN (a month, a week, an intern, all time)."""
    total = int(len(df))
    if total == 0:
        return {"total_orders": 0, "is_empty": True}

    delivered = int(df["delivered"].sum())
    not_delivered = int(df["not_delivered"].sum())
    net_orders = total - not_delivered
    true_cancelled = int(df["true_cancelled"].sum())
    returned = int(df["returned"].sum())
    in_transit = int(df["in_transit"].sum())
    status_blank = int(df["status_blank"].sum())

    submitted = int(df["review_submitted"].sum())
    reflected = int(df["reflected"].sum())
    not_reflected = max(submitted - reflected, 0)
    seller_fb = int(df["seller_feedback"].sum())
    checker_ok = int(df["checker_ok"].sum())

    paid = df[df["is_paid"]]
    pending = df[df["is_payment_pending"]]
    cancelled_pay = df[df["payment_state"] == "CANCELLED"]

    paid_unreflected = paid[~paid["reflected"]]
    paid_undelivered = paid[paid["not_delivered"]]
    unreconciled = df[df["amazon_price"].isna()]

    order_value = _money(df["order_price"])
    amazon_value = _money(df["amazon_price"])

    return {
        "is_empty": False,
        # ---- volume
        "total_orders": total,
        "net_orders": net_orders,
        "delivered": delivered,
        "not_delivered": not_delivered,
        "true_cancelled": true_cancelled,
        "returned": returned,
        "in_transit": in_transit,
        "status_blank": status_blank,
        # ---- review pipeline
        "review_submitted": submitted,
        "review_reflected": reflected,
        "review_not_reflected": not_reflected,
        "review_not_submitted": max(net_orders - submitted, 0),
        "seller_feedback": seller_fb,
        "seller_feedback_missing": max(submitted - seller_fb, 0),
        "checker_ok": checker_ok,
        "checker_pending": max(submitted - checker_ok, 0),
        # ---- rates
        "reflection_rate": _pct(reflected, submitted),
        "order_submission_rate": _pct(submitted, net_orders),
        "cancellation_rate": _pct(not_delivered, total),
        "true_cancel_rate": _pct(true_cancelled, total),
        "return_rate": _pct(returned, total),
        "delivery_rate": _pct(delivered, total),
        "seller_feedback_rate": _pct(seller_fb, submitted),
        "checker_verified_rate": _pct(checker_ok, submitted),
        "payment_done_rate": _pct(len(paid), total),
        # ---- money
        "order_value": order_value,
        "amazon_value": amazon_value,
        "avg_order_value": round(order_value / total, 2) if total else None,
        "paid_count": int(len(paid)),
        "paid_amt": _money(paid["order_price"]),
        "payment_pending_count": int(len(pending)),
        "payment_pending_amt": _money(pending["order_price"]),
        "payment_cancelled_count": int(len(cancelled_pay)),
        "payment_cancelled_amt": _money(cancelled_pay["order_price"]),
        "paid_unreflected_count": int(len(paid_unreflected)),
        "paid_unreflected_amt": _money(paid_unreflected["order_price"]),
        "paid_undelivered_count": int(len(paid_undelivered)),
        "paid_undelivered_amt": _money(paid_undelivered["order_price"]),
        "unreconciled_count": int(len(unreconciled)),
        "unreconciled_amt": _money(unreconciled["order_price"]),
        "returned_amt": _money(df[df["returned"]]["order_price"]),
        "price_gap_amt": float(df["price_gap"].fillna(0).sum()),
        "review_incentive_amt": _money(df["review_price"]),
        # ---- coverage
        "interns_active": int(df["intern"].replace("", np.nan).nunique()),
        "products": int(df["product"].replace("", np.nan).nunique()),
        "asins": int(df["asin"].replace("", np.nan).nunique()),
    }


# ---------------------------------------------------------------------------
# Period slicing
# ---------------------------------------------------------------------------
def slice_month(main: pd.DataFrame, ym: str) -> pd.DataFrame:
    return main[main["ym"] == ym]


def previous_ym(ym: str) -> str:
    year, month = int(ym[:4]), int(ym[5:7])
    return f"{year - 1}-12" if month == 1 else f"{year}-{month - 1:02d}"


def current_ym(main: pd.DataFrame | None = None) -> str:
    """Today's month, or the newest month that actually has rows."""
    today = f"{date.today():%Y-%m}"
    if main is None or main.empty:
        return today
    months = set(main["ym"].dropna())
    if today in months:
        return today
    return max(months) if months else today


def slice_last_days(main: pd.DataFrame, days: int, end: date | None = None) -> pd.DataFrame:
    end = end or date.today()
    start = pd.Timestamp(end) - pd.Timedelta(days=days - 1)
    return main[(main["order_date"] >= start) & (main["order_date"] <= pd.Timestamp(end))]


def slice_prior_days(main: pd.DataFrame, days: int, end: date | None = None) -> pd.DataFrame:
    """The window immediately before slice_last_days, for week-on-week deltas."""
    end = end or date.today()
    this_start = pd.Timestamp(end) - pd.Timedelta(days=days - 1)
    prior_end = this_start - pd.Timedelta(days=1)
    prior_start = prior_end - pd.Timedelta(days=days - 1)
    return main[(main["order_date"] >= prior_start) & (main["order_date"] <= prior_end)]


# ---------------------------------------------------------------------------
# Series
# ---------------------------------------------------------------------------
def monthly_series(main: pd.DataFrame) -> pd.DataFrame:
    """One row per month with the full KPI set, oldest first."""
    rows = []
    for ym in sorted(main["ym"].dropna().unique()):
        group = main[main["ym"] == ym]
        kpis = compute_kpis(group)
        kpis["ym"] = ym
        kpis["month_label"] = group["month_label"].iloc[0]
        rows.append(kpis)
    out = pd.DataFrame(rows)
    return out if out.empty else out.set_index("ym", drop=False)


def weekly_series(main: pd.DataFrame, weeks: int = 12) -> pd.DataFrame:
    rows = []
    for wk in sorted(main["iso_week"].dropna().unique()):
        group = main[main["iso_week"] == wk]
        kpis = compute_kpis(group)
        kpis["iso_week"] = wk
        kpis["week_start"] = group["order_date"].min()
        rows.append(kpis)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values("iso_week").tail(weeks).reset_index(drop=True)


def daily_series(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["order_date", "orders", "value"])
    out = (
        df.groupby(df["order_date"].dt.date)
        .agg(
            orders=("order_id", "size"),
            value=("order_price", "sum"),
            delivered=("delivered", "sum"),
            not_delivered=("not_delivered", "sum"),
            reflected=("reflected", "sum"),
        )
        .reset_index()
        .rename(columns={"order_date": "day"})
    )
    return out


# ---------------------------------------------------------------------------
# Breakdowns
# ---------------------------------------------------------------------------
def by_dimension(df: pd.DataFrame, column: str, min_orders: int = 1) -> pd.DataFrame:
    """Per-intern / per-product / per-ASIN scorecard with the same definitions."""
    if df.empty:
        return pd.DataFrame()
    rows = []
    for key, group in df.groupby(df[column].replace("", "(blank)")):
        if len(group) < min_orders:
            continue
        kpis = compute_kpis(group)
        kpis[column] = key
        rows.append(kpis)
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values("total_orders", ascending=False).reset_index(drop=True)


def status_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["status", "orders", "value"])
    out = (
        df.assign(status=df["status"].replace("", "(blank / not updated)"))
        .groupby("status")
        .agg(orders=("order_id", "size"), value=("order_price", "sum"))
        .reset_index()
        .sort_values("orders", ascending=False)
    )
    out["share_pct"] = (100 * out["orders"] / len(df)).round(2)
    return out


def payment_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["payment_state", "orders", "value"])
    out = (
        df.groupby("payment_state")
        .agg(orders=("order_id", "size"), value=("order_price", "sum"))
        .reset_index()
        .sort_values("orders", ascending=False)
    )
    out["share_pct"] = (100 * out["orders"] / len(df)).round(2)
    return out


# ---------------------------------------------------------------------------
# Intern grading
# ---------------------------------------------------------------------------
def score_interns(df: pd.DataFrame, min_orders: int = 5) -> pd.DataFrame:
    """A single 0-100 score so the team can rank interns at a glance.

    Weighted: reflection 35, submission 25, delivery 20, seller feedback 10,
    checker sign-off 10. Interns below `min_orders` are kept but marked as a
    small sample rather than silently dropped.
    """
    scored = by_dimension(df, "intern", min_orders=1)
    if scored.empty:
        return scored

    def band(series: pd.Series, cap: float = 100.0) -> pd.Series:
        return series.astype(float).clip(upper=cap).fillna(0.0)

    scored["score"] = (
        0.35 * band(scored["reflection_rate"])
        + 0.25 * band(scored["order_submission_rate"])
        + 0.20 * band(scored["delivery_rate"])
        + 0.10 * band(scored["seller_feedback_rate"])
        + 0.10 * band(scored["checker_verified_rate"])
    ).round(1)

    scored["small_sample"] = scored["total_orders"] < min_orders
    scored["grade"] = pd.cut(
        scored["score"],
        bins=[-0.01, 40, 60, 75, 90, 100.01],
        labels=["E", "D", "C", "B", "A"],
    )
    return scored.sort_values(
        ["small_sample", "score"], ascending=[True, False]
    ).reset_index(drop=True)


def attach_roster(scored: pd.DataFrame, roster: pd.DataFrame) -> pd.DataFrame:
    """Join roster status onto per-intern rows using a normalised name key."""
    if scored.empty:
        return scored
    out = scored.copy()
    out["_key"] = out["intern"].str.lower().str.strip()
    if roster is None or roster.empty:
        out["roster_status"] = "Not on roster"
        out["joining_date"] = pd.NaT
        out["leaving_date"] = pd.NaT
        return out.drop(columns=["_key"])

    ros = roster.copy()
    ros["_key"] = ros["name"].str.lower().str.strip()
    ros = ros.drop_duplicates("_key", keep="first")
    out = out.merge(
        ros[["_key", "status", "joining_date", "leaving_date", "stipend"]],
        on="_key", how="left",
    )
    out["roster_status"] = out["status"].fillna("Not on roster")
    return out.drop(columns=["_key", "status"])


# ---------------------------------------------------------------------------
# Targets vs actuals
# ---------------------------------------------------------------------------
def _norm_product(series: pd.Series) -> pd.Series:
    return (
        series.astype(str).str.upper().str.strip()
        .str.replace(r"[^A-Z0-9]+", " ", regex=True)
        .str.strip()
    )


def _targets_block(targets: pd.DataFrame, kind: str, ym: str) -> pd.DataFrame:
    """One month's slice of either grid on the Monthly Targets Report tab."""
    if targets is None or targets.empty or "kind" not in targets.columns:
        return pd.DataFrame(columns=["product", "value"])
    year, month = int(ym[:4]), int(ym[5:7])
    block = targets[(targets["kind"] == kind) & (targets["month_number"] == month)].copy()
    if "year" in block.columns and block["year"].notna().any():
        same_year = block[block["year"] == year]
        if not same_year.empty:
            block = same_year
    return block


def targets_vs_actual(main: pd.DataFrame, targets: pd.DataFrame, ym: str) -> pd.DataFrame:
    """Product-level target vs actual for one month.

    Targets come from the right-hand grid of the Monthly Targets Report tab;
    actuals are counted live from MAIN.
    """
    tgt = _targets_block(targets, "target", ym)
    actual = main[main["ym"] == ym].copy()
    if tgt.empty and actual.empty:
        return pd.DataFrame()

    if tgt.empty:
        tgt_agg = pd.DataFrame(columns=["_key", "product", "target"])
    else:
        tgt["_key"] = _norm_product(tgt["product"])
        tgt_agg = (
            tgt.groupby(["_key", "product"], as_index=False)["value"].max()
            .rename(columns={"value": "target"})
        )

    if actual.empty:
        act_agg = pd.DataFrame(columns=["_key", "actual", "delivered_actual"])
    else:
        actual["_key"] = _norm_product(actual["product"])
        act_agg = (
            actual.groupby("_key")
            .agg(actual=("order_id", "size"), delivered_actual=("delivered", "sum"))
            .reset_index()
        )
        names = actual.groupby("_key")["product"].first().rename("actual_product")
        act_agg = act_agg.merge(names, on="_key", how="left")

    out = tgt_agg.merge(act_agg, on="_key", how="outer")
    if "actual_product" in out.columns:
        out["product"] = out["product"].fillna(out["actual_product"])
        out = out.drop(columns=["actual_product"])
    out["product"] = out["product"].fillna("(unnamed)")
    out["has_target"] = out["target"].notna() & (out["target"] > 0)
    for col in ("target", "actual", "delivered_actual"):
        out[col] = out[col].fillna(0)
    out["variance"] = out["actual"] - out["target"]
    out["achievement_pct"] = _safe_ratio(100 * out["actual"], out["target"]).round(1)
    return (
        out.drop(columns=["_key"])
        .sort_values(["has_target", "actual"], ascending=[False, False])
        .reset_index(drop=True)
    )


def productwise_actual_variance(main: pd.DataFrame, targets: pd.DataFrame, ym: str) -> pd.DataFrame:
    """Does the sheet's own productwise actuals grid tie back to MAIN?"""
    block = _targets_block(targets, "sheet_actual", ym)
    live = main[main["ym"] == ym].copy()
    if block.empty and live.empty:
        return pd.DataFrame()

    if block.empty:
        sheet_agg = pd.DataFrame(columns=["_key", "product", "sheet_orders"])
    else:
        block["_key"] = _norm_product(block["product"])
        sheet_agg = (
            block.groupby(["_key", "product"], as_index=False)["value"].max()
            .rename(columns={"value": "sheet_orders"})
        )

    if live.empty:
        live_agg = pd.DataFrame(columns=["_key", "app_orders"])
    else:
        live["_key"] = _norm_product(live["product"])
        live_agg = (
            live.groupby("_key").agg(app_orders=("order_id", "size")).reset_index()
        )
        names = live.groupby("_key")["product"].first().rename("live_product")
        live_agg = live_agg.merge(names, on="_key", how="left")

    out = sheet_agg.merge(live_agg, on="_key", how="outer")
    if "live_product" in out.columns:
        out["product"] = out["product"].fillna(out["live_product"])
        out = out.drop(columns=["live_product"])
    out["product"] = out["product"].fillna("(unnamed)")
    out[["sheet_orders", "app_orders"]] = out[["sheet_orders", "app_orders"]].fillna(0)
    out["difference"] = out["app_orders"] - out["sheet_orders"]
    out["match"] = out["difference"] == 0
    return (
        out.drop(columns=["_key"])
        .sort_values("difference", key=lambda s: s.abs(), ascending=False)
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Variance against the workbook's own aggregate tab
# ---------------------------------------------------------------------------
_VARIANCE_FIELDS = [
    ("total_orders", "total_orders", "Total Orders"),
    ("net_orders", "net_orders", "Net Orders"),
    ("not_delivered", "cancelled", "Cancelled (not delivered)"),
    ("review_submitted", "review_submitted", "Review Submitted"),
    ("review_reflected", "review_reflected", "Review Reflected"),
    ("seller_feedback", "seller_feedback", "Seller Feedback"),
]


def audit_variance(main: pd.DataFrame, overall: pd.DataFrame) -> pd.DataFrame:
    """Recompute each month from MAIN and diff it against the sheet's own tab."""
    if overall is None or overall.empty:
        return pd.DataFrame()
    rows = []
    computed = monthly_series(main)
    for _, sheet_row in overall.iterrows():
        ym = sheet_row.get("ym")
        if ym not in computed.index:
            continue
        mine = computed.loc[ym]
        for mine_key, sheet_key, label in _VARIANCE_FIELDS:
            sheet_val = sheet_row.get(sheet_key)
            if pd.isna(sheet_val):
                continue
            rows.append(
                {
                    "ym": ym,
                    "month": sheet_row.get("month_name", ym),
                    "metric": label,
                    "app_value": int(mine[mine_key]),
                    "sheet_value": int(sheet_val),
                    "difference": int(mine[mine_key]) - int(sheet_val),
                }
            )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["match"] = out["difference"] == 0
    return out
