"""Live loaders for the NEODRIFT interns Google Sheet.

The workbook is shared as "anyone with the link", so it is read through the
public gviz endpoint - no service account or API key needed. The sheet key is
taken from the URL:

    https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit

Override the default with a `SHEET_ID` entry in .streamlit/secrets.toml or an
INTERNS_SHEET_ID environment variable.
"""
from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st

DEFAULT_SHEET_ID = "1JEzjLW3yHsk3-rfQH67wrbI1hZmX3UIdqQAvEskWaPk"

TAB_MAIN = "MAIN"
TAB_OVERALL_AUDIT = "Overall Audit Report"
TAB_INTERN_ROSTER = "INTERN REPORT MANUAL"
TAB_ASIN = "ASIN REPORT"
TAB_TARGETS = "MONTHLY TARGETS REPORT"
TAB_CHECKER = "CHECKER"
TAB_AMAZON = "AMAZON ORDER REPORT PASTING"

REQUEST_TIMEOUT = 60

# Amazon statuses that mean the parcel never stayed with the buyer.
RETURN_STATUSES = (
    "Shipped - Returned to Seller",
    "Shipped - Returning to Seller",
)
IN_TRANSIT_STATUSES = (
    "Shipped",
    "Shipped - Out for Delivery",
    "Shipped - Picked Up",
    "Pending",
    "Pending - Waiting for Pick Up",
)
DELIVERED_PREFIX = "Shipped - Delivered"


def sheet_id() -> str:
    """Resolve the sheet key from secrets, then env, then the built-in default."""
    try:
        if "SHEET_ID" in st.secrets:
            return str(st.secrets["SHEET_ID"]).strip()
    except Exception:
        pass
    return os.environ.get("INTERNS_SHEET_ID", DEFAULT_SHEET_ID).strip()


def sheet_url() -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id()}/edit"


def _gviz_csv(tab: str, headers: int = 1) -> str:
    url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id()}/gviz/tq"
        f"?tqx=out:csv&headers={headers}&sheet={quote(tab)}"
    )
    resp = requests.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    text = resp.text
    if text.lstrip().startswith("<") or "signin" in text[:400].lower():
        raise RuntimeError(
            f"Tab '{tab}' could not be read. Confirm the workbook is shared as "
            "'Anyone with the link - Viewer'."
        )
    return text


def _read_tab(tab: str, headers: int = 1) -> pd.DataFrame:
    """Every column comes back as text; typing happens in the normalisers.

    headers=0 returns a purely positional frame (RangeIndex columns, every
    sheet row kept as data) for tabs whose header row is not a clean header.
    """
    csv_text = _gviz_csv(tab, headers)
    return pd.read_csv(
        io.StringIO(csv_text),
        dtype=str,
        keep_default_na=False,
        header=0 if headers else None,
    )


def _blank_to_na(df: pd.DataFrame) -> pd.DataFrame:
    return df.replace({"": pd.NA})


def _txt(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def _num(series: pd.Series) -> pd.Series:
    """Tolerate ' 1,234.00 ', 'Rs 957' and stray symbols."""
    cleaned = (
        series.fillna("")
        .astype(str)
        .str.replace(r"[^\d.\-]", "", regex=True)
        .replace({"": None, "-": None, ".": None})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def _bool(series: pd.Series) -> pd.Series:
    return _txt(series).str.upper().isin(["TRUE", "YES", "1", "Y"])


def _dates(series: pd.Series) -> pd.Series:
    """MAIN and the roster use day-first text dates."""
    raw = _txt(series).replace({"": None})
    out = pd.to_datetime(raw, format="%d/%m/%Y", errors="coerce")
    gaps = out.isna() & raw.notna()
    if gaps.any():
        out.loc[gaps] = pd.to_datetime(raw[gaps], format="%d-%m-%Y", errors="coerce")
    gaps = out.isna() & raw.notna()
    if gaps.any():
        out.loc[gaps] = pd.to_datetime(raw[gaps], errors="coerce", dayfirst=True)
    return out


def classify_payment(value: str) -> str:
    """Fold ~32 free-text payment spellings into four buckets."""
    text = str(value or "").strip().lower()
    if text in ("", "nan", "none"):
        return "PENDING"
    if "cancel" in text:
        return "CANCELLED"
    if "hold" in text:
        return "HOLD"
    if "paid" in text or "settled" in text:
        return "PAID"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# MAIN - the transactional order ledger, and the base for every metric
# ---------------------------------------------------------------------------
def normalise_main(raw: pd.DataFrame) -> pd.DataFrame:
    df = _blank_to_na(raw.copy())
    df.columns = [str(c).strip() for c in df.columns]

    # The sheet has ~660 pre-formatted empty rows below the data.
    key_cols = [c for c in ("ORDER ID", "ASIN", "ORDER DATE") if c in df.columns]
    if key_cols:
        df = df[df[key_cols].notna().any(axis=1)]
    df = df.reset_index(drop=True)
    df["sheet_row"] = df.index + 2  # +1 header, +1 to 1-base

    out = pd.DataFrame(index=df.index)
    out["sheet_row"] = df["sheet_row"]
    out["s_no"] = _num(df.get("S.NO", pd.Series(dtype=str)))
    out["asin"] = _txt(df.get("ASIN", pd.Series(dtype=str)))
    out["product"] = _txt(df.get("PRODUCT NAME", pd.Series(dtype=str)))
    out["intern"] = _txt(df.get("Interns Name", pd.Series(dtype=str)))
    out["order_date"] = _dates(df.get("ORDER DATE", pd.Series(dtype=str)))
    out["order_id"] = _txt(df.get("ORDER ID", pd.Series(dtype=str)))
    out["order_sku"] = _txt(df.get("ORDER SKU", pd.Series(dtype=str)))
    out["order_price"] = _num(df.get("ORDER PRICE", pd.Series(dtype=str)))
    out["review_price"] = _num(df.get("REVIEW PRICE", pd.Series(dtype=str)))
    out["payment_raw"] = _txt(df.get("REVIEW PAYMENT", pd.Series(dtype=str)))
    out["reflected"] = _bool(df.get("REVIEW REFLECTED (FORM)", pd.Series(dtype=str)))
    out["seller_feedback"] = _bool(df.get("SELLER FEEDBACK", pd.Series(dtype=str)))
    out["checker_ok"] = _bool(df.get("CHECKER (SHIVAM GOMAT)", pd.Series(dtype=str)))
    out["review_link"] = _txt(df.get("REIVEW LINK (ST)", pd.Series(dtype=str)))
    out["order_name"] = _txt(df.get("ORDER NAME", pd.Series(dtype=str)))
    out["status"] = _txt(df.get("AMAZON STATUS", pd.Series(dtype=str)))
    out["return_pickup_by"] = _txt(df.get("RETURN PICKUP BY", pd.Series(dtype=str)))
    out["return_checker"] = _txt(df.get("RETURN CHECKER", pd.Series(dtype=str)))
    out["dispatched_sku"] = _txt(df.get("DISPATCHED SKU", pd.Series(dtype=str)))
    out["amazon_price"] = _num(df.get("AMAZON PRICE", pd.Series(dtype=str)))
    out["freebie"] = _txt(df.get("Additional Freebie", pd.Series(dtype=str)))

    # ---- derived flags. These definitions are reconciled exactly against the
    # ---- workbook's own "Overall Audit Report" tab for all 12 live months.
    out["payment_state"] = out["payment_raw"].apply(classify_payment)
    out["is_paid"] = out["payment_state"] == "PAID"
    out["is_payment_pending"] = out["payment_state"].isin(["PENDING", "HOLD", "UNKNOWN"])
    out["delivered"] = out["status"].str.startswith(DELIVERED_PREFIX)
    out["not_delivered"] = ~out["delivered"]          # the sheet calls this "Cancelled"
    out["true_cancelled"] = out["status"].str.casefold() == "cancelled"
    out["returned"] = out["status"].isin(RETURN_STATUSES)
    out["in_transit"] = out["status"].isin(IN_TRANSIT_STATUSES)
    out["status_blank"] = out["status"] == ""
    out["review_submitted"] = out["review_link"] != ""
    out["review_not_reflected"] = out["review_submitted"] & ~out["reflected"]

    out["year"] = out["order_date"].dt.year
    out["month"] = out["order_date"].dt.month
    out["ym"] = out["order_date"].dt.strftime("%Y-%m")
    out["month_label"] = out["order_date"].dt.strftime("%B %Y")
    out["iso_week"] = out["order_date"].dt.strftime("%G-W%V")
    out["age_days"] = (pd.Timestamp(date.today()) - out["order_date"]).dt.days

    # Value at risk: the order value is what the company actually funds.
    out["value"] = out["order_price"].fillna(0.0)
    out["price_gap"] = out["order_price"] - out["amazon_price"]
    return out


# ---------------------------------------------------------------------------
# Overall Audit Report - the workbook's own monthly aggregate
# ---------------------------------------------------------------------------
OAR_COLUMNS = [
    "Month Number", "Year", "Months", "Submission", "Reflection Rate %",
    "Order Submission %", "Net Orders", "Total Orders", "Cancellation%",
    "Cancelled", "Review Submitted", "Review Reflected",
    "Review Not Reflected", "Seller Feedback", "Seller Feedback Not Submitted",
]


def normalise_overall_audit(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    if len(df.columns) >= len(OAR_COLUMNS):
        df = df.iloc[:, : len(OAR_COLUMNS)]
        df.columns = OAR_COLUMNS
    df = _blank_to_na(df)
    df = df[_num(df["Total Orders"]).notna()].reset_index(drop=True)
    if df.empty:
        return pd.DataFrame(columns=["ym"] + OAR_COLUMNS)

    out = pd.DataFrame(index=df.index)
    out["month_number"] = _num(df["Month Number"]).astype("Int64")
    out["year"] = _num(df["Year"]).astype("Int64")
    out["month_name"] = _txt(df["Months"])
    for src, dst in [
        ("Net Orders", "net_orders"), ("Total Orders", "total_orders"),
        ("Cancelled", "cancelled"), ("Review Submitted", "review_submitted"),
        ("Review Reflected", "review_reflected"),
        ("Review Not Reflected", "review_not_reflected"),
        ("Seller Feedback", "seller_feedback"),
        ("Seller Feedback Not Submitted", "seller_feedback_missing"),
        ("Submission", "submission"),
    ]:
        out[dst] = _num(df[src])
    for src, dst in [
        ("Reflection Rate %", "reflection_rate"),
        ("Order Submission %", "order_submission_rate"),
        ("Cancellation%", "cancellation_rate"),
    ]:
        out[dst] = _num(df[src].astype(str).str.replace("%", "", regex=False))

    out["ym"] = (
        out["year"].astype(str) + "-" + out["month_number"].astype(str).str.zfill(2)
    )
    return out


# ---------------------------------------------------------------------------
# Intern roster
# ---------------------------------------------------------------------------
def normalise_roster(raw: pd.DataFrame) -> pd.DataFrame:
    df = _blank_to_na(raw.copy())
    df.columns = [str(c).strip() for c in df.columns]
    cols = list(df.columns)

    def pick(name: str, index: int) -> pd.Series:
        if name in df.columns:
            return df[name]
        if index < len(cols):
            return df[cols[index]]
        return pd.Series([pd.NA] * len(df), index=df.index)

    out = pd.DataFrame(index=df.index)
    out["status"] = _txt(pick("Status", 0)).str.title()
    out["name"] = _txt(pick("Name", 1))
    out["joining_date"] = _dates(pick("Joining Date", 2))
    out["leaving_date"] = _dates(pick("Leaving Date", 3))
    out["stipend"] = _num(pick("Stipend", 4))
    out["remark"] = _txt(pick("Remark", 5))
    out = out[out["name"] != ""].reset_index(drop=True)
    out["is_active"] = out["status"].str.lower().eq("active")
    return out


# ---------------------------------------------------------------------------
# ASIN report
# ---------------------------------------------------------------------------
def normalise_asin(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    cols = list(df.columns)
    if len(cols) < 4:
        return pd.DataFrame(columns=["asin", "sku", "product", "orders"])
    out = pd.DataFrame()
    out["asin"] = _txt(df[cols[0]])
    out["sku"] = _txt(df[cols[1]])
    out["product"] = _txt(df[cols[2]])
    out["orders"] = _num(df[cols[3]])
    out = out[(out["asin"] != "") & out["orders"].notna()].reset_index(drop=True)
    return out


# ---------------------------------------------------------------------------
# Monthly targets - a product x month grid, read positionally
# ---------------------------------------------------------------------------
MONTH_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


_MONTH_PREFIX = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


def _month_from_text(text: str) -> int | None:
    key = str(text or "").strip().upper()[:3]
    return _MONTH_PREFIX.get(key)


def _contiguous_runs(columns: list[int]) -> list[list[int]]:
    runs: list[list[int]] = []
    for col in sorted(columns):
        if runs and col == runs[-1][-1] + 1:
            runs[-1].append(col)
        else:
            runs.append([col])
    return runs


def normalise_targets(raw: pd.DataFrame) -> pd.DataFrame:
    """Parse the two side-by-side product x month grids on this tab.

    The tab holds a productwise *actuals* grid (Jan..Dec) and, to its right,
    a productwise *target* grid covering a shorter run of months. gviz blanks
    text headers over numeric columns, so the block layout is recovered from
    the data: contiguous non-empty column runs are the blocks, and whichever
    month names do survive in the header row fix each block's column offset.

    Returns a long frame: product, month_number, value, kind
    ('sheet_actual' for the left grid, 'target' for the ones to its right).
    """
    empty = pd.DataFrame(
        columns=["product", "month_number", "value", "kind", "year", "month_name"]
    )
    df = raw.copy()
    if df.empty or len(df.columns) < 3:
        return empty
    df.columns = range(len(df.columns))

    year = None
    for candidate in df.iloc[: min(3, len(df)), 0].tolist():
        digits = "".join(ch for ch in str(candidate) if ch.isdigit())
        if len(digits) == 4 and digits.startswith("20"):
            year = int(digits)
            break

    first_col = _txt(df[0]).str.upper()
    header_rows = df.index[first_col == "PRODUCTS"].tolist()
    header_idx = header_rows[0] if header_rows else 0
    body = df.loc[header_idx + 1 :]
    body = body[~first_col.loc[body.index].isin(["", "TOTAL", "NAN"])]
    if body.empty:
        return empty

    # Columns carrying any numeric data, grouped into contiguous blocks.
    data_cols = [
        col for col in df.columns
        if col != 0 and pd.to_numeric(
            _txt(body[col]).str.replace(",", "", regex=False).replace({"": None}),
            errors="coerce",
        ).notna().any()
    ]
    header_months = {
        col: _month_from_text(df.at[header_idx, col])
        for col in df.columns if col != 0
    }
    header_cols = [col for col, month in header_months.items() if month]
    runs = _contiguous_runs(sorted(set(data_cols) | set(header_cols)))
    if not runs:
        return empty

    records: list[dict] = []
    for block_no, run in enumerate(runs):
        offsets = [col - header_months[col] for col in run if header_months.get(col)]
        if offsets:
            offset = int(pd.Series(offsets).mode().iloc[0])
        else:
            offset = run[0] - 1  # assume the block starts at January
        kind = "sheet_actual" if block_no == 0 else "target"
        for col in run:
            month = header_months.get(col) or (col - offset)
            if not 1 <= month <= 12:
                continue
            for idx in body.index:
                product = str(body.at[idx, 0]).strip()
                val = pd.to_numeric(
                    str(body.at[idx, col]).replace(",", ""), errors="coerce"
                )
                if product and pd.notna(val):
                    records.append(
                        {
                            "product": product,
                            "month_number": int(month),
                            "value": float(val),
                            "kind": kind,
                        }
                    )
    out = pd.DataFrame(records)
    if out.empty:
        return empty
    out = out.drop_duplicates(["product", "month_number", "kind"], keep="first")
    out["year"] = year
    out["month_name"] = out["month_number"].map(lambda m: MONTH_ORDER[m - 1])
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# CHECKER - the team's existing manual red-flag list
# ---------------------------------------------------------------------------
def normalise_checker(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    cols = list(df.columns)
    if len(cols) < 3:
        return pd.DataFrame(columns=["intern", "issue", "order_id", "order_sku"])
    out = pd.DataFrame()
    out["intern"] = _txt(df[cols[0]])
    out["issue"] = _txt(df[cols[1]])
    out["order_id"] = _txt(df[cols[2]])
    out["order_sku"] = _txt(df[cols[3]]) if len(cols) > 3 else ""
    out = out[(out["order_id"] != "") | (out["issue"] != "")].reset_index(drop=True)
    return out


# ---------------------------------------------------------------------------
# Amazon order report - reconciliation source
# ---------------------------------------------------------------------------
def normalise_amazon(raw: pd.DataFrame) -> pd.DataFrame:
    df = _blank_to_na(raw.copy())
    df.columns = [str(c).strip().lower() for c in df.columns]
    if "amazon-order-id" not in df.columns:
        return pd.DataFrame(columns=["order_id", "purchase_date", "status", "price"])
    out = pd.DataFrame(index=df.index)
    out["order_id"] = _txt(df["amazon-order-id"])
    out["purchase_date"] = pd.to_datetime(
        df.get("purchase-date"), errors="coerce", utc=True, format="mixed"
    ).dt.tz_localize(None)
    out["status"] = _txt(df.get("order-status", pd.Series(dtype=str)))
    out["item_status"] = _txt(df.get("item-status", pd.Series(dtype=str)))
    out["price"] = _num(df.get("item-price", pd.Series(dtype=str)))
    out["asin"] = _txt(df.get("asin", pd.Series(dtype=str)))
    out["sku"] = _txt(df.get("sku", pd.Series(dtype=str)))
    out["product"] = _txt(df.get("product-name", pd.Series(dtype=str)))
    out["ship_state"] = _txt(df.get("ship-state", pd.Series(dtype=str)))
    out["ship_city"] = _txt(df.get("ship-city", pd.Series(dtype=str)))
    out = out[out["order_id"] != ""].reset_index(drop=True)
    return out


# ---------------------------------------------------------------------------
# Bundle
# ---------------------------------------------------------------------------
@dataclass
class SheetData:
    main: pd.DataFrame
    overall_audit: pd.DataFrame
    roster: pd.DataFrame
    asin: pd.DataFrame
    targets: pd.DataFrame
    checker: pd.DataFrame
    amazon: pd.DataFrame
    loaded_at: datetime
    warnings: list[str] = field(default_factory=list)

    @property
    def months(self) -> list[str]:
        """Months present in MAIN, newest first."""
        vals = self.main["ym"].dropna().unique().tolist()
        return sorted(vals, reverse=True)


_LOADERS = [
    ("main", TAB_MAIN, normalise_main, 1, True),
    ("overall_audit", TAB_OVERALL_AUDIT, normalise_overall_audit, 1, False),
    ("roster", TAB_INTERN_ROSTER, normalise_roster, 1, False),
    ("asin", TAB_ASIN, normalise_asin, 1, False),
    ("targets", TAB_TARGETS, normalise_targets, 0, False),
    ("checker", TAB_CHECKER, normalise_checker, 1, False),
    ("amazon", TAB_AMAZON, normalise_amazon, 1, False),
]


def _empty_like(key: str) -> pd.DataFrame:
    return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner=False)
def load_sheet_data(_ttl_key: int = 0) -> SheetData:
    """Fetch and normalise every tab the app needs.

    A failure on MAIN is fatal; a failure on any secondary tab degrades to an
    empty frame plus a warning so the rest of the dashboard still renders.
    """
    frames: dict[str, pd.DataFrame] = {}
    warnings: list[str] = []
    for key, tab, normaliser, headers, required in _LOADERS:
        try:
            frames[key] = normaliser(_read_tab(tab, headers))
        except Exception as exc:  # noqa: BLE001 - surfaced to the user as a warning
            if required:
                raise
            frames[key] = _empty_like(key)
            warnings.append(f"Tab '{tab}' could not be read ({type(exc).__name__}): {exc}")
    return SheetData(loaded_at=datetime.now(), warnings=warnings, **frames)


def get_data(ttl_minutes: int = 10) -> SheetData:
    """Bucket `now` into ttl_minutes so the cache key rolls over on schedule."""
    bucket = int(datetime.now().timestamp() // max(60 * int(ttl_minutes or 1), 60))
    return load_sheet_data(bucket)
