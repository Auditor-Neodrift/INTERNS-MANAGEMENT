"""Reflection rate report: orders whose review never went live.

The report itself is derived from MAIN - a review link is present, the
reflection flag is still false, and the order is past the SLA window. Nothing
here writes to the audit workbook.

What the team adds on top of that - the executive's reason for the order not
reflecting, and the checker's sign-off on that reason - has nowhere to live in
the source sheet, and the sheet is read-only to this app by design. So notes
are kept in a side store, keyed by order ID:

  * a worksheet in the same side workbook the influencer leads use, whenever a
    service account is configured. Durable, shared, and openable in Sheets.
  * otherwise a local JSON file, so the tab is usable immediately.

The local file is a real fallback, not a pretence: on Streamlit Cloud the
container filesystem is rebuilt on every reboot and redeploy, so notes written
there survive the session but not the next restart. `store_state()` reports
which backend is live so the page can say so plainly rather than implying a
durability it does not have.

A note on the clock: the sheet records an ORDER DATE but no delivery date and
no review submission date, so "15 days after delivery / submission" is
measured from the order date. That is the same basis the reflect_sla audit
rule already uses, and it is stated on the page.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

WORKSHEET_NAME = "REFLECTION NOTES"
LOCAL_PATH = Path(__file__).resolve().parent.parent / "config" / "reflection_notes.json"

# Stored per order ID. `checked` is the checker's audit of the remark, so it
# deliberately sits last in the UI - the executive writes, the checker signs.
COLUMNS = ["order_id", "remark", "checked", "checked_by", "updated_at", "updated_by"]

DEFAULT_SLA_DAYS = 15


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------
def report(
    main: pd.DataFrame,
    sla_days: int = DEFAULT_SLA_DAYS,
    delivered_only: bool = False,
) -> pd.DataFrame:
    """Orders past the SLA with a review submitted that never reflected.

    `delivered_only` narrows to parcels Amazon confirmed as delivered. Left
    off by default: a review can be submitted on an order whose status never
    updated, and those are exactly the rows worth chasing.
    """
    empty = pd.DataFrame(columns=[
        "order_id", "asin", "intern", "product", "order_date", "age_days",
        "status", "review_link", "payment_state", "order_price", "sheet_row",
    ])
    if main is None or main.empty:
        return empty

    mask = (
        main["review_submitted"]
        & ~main["reflected"]
        & (main["age_days"].fillna(-1) >= float(sla_days))
    )
    if delivered_only:
        mask = mask & main["delivered"]

    cols = [c for c in empty.columns if c in main.columns]
    out = main.loc[mask, cols].copy()
    if out.empty:
        return empty
    return out.sort_values("age_days", ascending=False).reset_index(drop=True)


def merge_notes(rows: pd.DataFrame, notes: pd.DataFrame) -> pd.DataFrame:
    """Attach the stored remark and checker flag to each order."""
    out = rows.copy()
    if out.empty:
        for col in ("remark", "checked", "checked_by", "updated_at", "updated_by"):
            out[col] = pd.Series(dtype="object")
        out["checked"] = out["checked"].astype(bool)
        return out

    out["order_id"] = out["order_id"].astype(str).str.strip()
    if notes is None or notes.empty:
        out["remark"] = ""
        out["checked"] = False
        out["checked_by"] = ""
        out["updated_at"] = pd.NaT
        out["updated_by"] = ""
        return out

    side = notes.copy()
    side["order_id"] = side["order_id"].astype(str).str.strip()
    side = side.drop_duplicates("order_id", keep="last")
    out = out.merge(side, on="order_id", how="left")
    out["remark"] = out["remark"].fillna("")
    out["checked"] = out["checked"].fillna(False).astype(bool)
    out["checked_by"] = out["checked_by"].fillna("")
    out["updated_by"] = out["updated_by"].fillna("")
    return out


def open_errors(merged: pd.DataFrame) -> pd.DataFrame:
    """Rows the checker has not signed off. This is the alert count."""
    if merged is None or merged.empty:
        return merged if merged is not None else pd.DataFrame()
    return merged[~merged["checked"].astype(bool)]


def summarise(merged: pd.DataFrame) -> dict[str, Any]:
    """Headline counts for the tab and the alert pill."""
    if merged is None or merged.empty:
        return {"total": 0, "checked": 0, "unchecked": 0, "no_remark": 0,
                "value": 0.0, "oldest_days": None, "interns": 0}
    checked = merged["checked"].astype(bool)
    remark = merged["remark"].astype(str).str.strip()
    ages = pd.to_numeric(merged.get("age_days"), errors="coerce")
    return {
        "total": int(len(merged)),
        "checked": int(checked.sum()),
        "unchecked": int((~checked).sum()),
        "no_remark": int((remark == "").sum()),
        "value": float(pd.to_numeric(
            merged.get("order_price"), errors="coerce").fillna(0).sum()),
        "oldest_days": int(ages.max()) if ages.notna().any() else None,
        "interns": int(merged["intern"].astype(str).str.strip()
                       .replace("", pd.NA).nunique(dropna=True)),
    }


# ---------------------------------------------------------------------------
# Note store - shared worksheet when configured, local JSON otherwise
# ---------------------------------------------------------------------------
def _empty_notes() -> pd.DataFrame:
    frame = pd.DataFrame(columns=COLUMNS)
    frame["checked"] = frame["checked"].astype(bool)
    frame["updated_at"] = pd.Series(dtype="datetime64[ns]")
    return frame


def sheet_id() -> str:
    """A dedicated sheet if given, else the influencer side workbook."""
    for key in ("REFLECTION_SHEET_ID", "INFLUENCER_SHEET_ID"):
        try:
            value = str(st.secrets.get(key, "") or "").strip()
        except Exception:
            value = ""
        if value:
            return value
    return ""


def _service_account_info() -> dict | None:
    try:
        info = st.secrets.get("gcp_service_account")
    except Exception:
        return None
    if not info:
        return None
    data = dict(info)
    return data if data.get("client_email") and data.get("private_key") else None


def is_shared() -> bool:
    """True when notes go to a worksheet everyone can see."""
    return bool(sheet_id()) and _service_account_info() is not None


def service_account_email() -> str:
    return str((_service_account_info() or {}).get("client_email", ""))


def sheet_url() -> str:
    key = sheet_id()
    return f"https://docs.google.com/spreadsheets/d/{key}/edit" if key else ""


def store_state() -> dict[str, Any]:
    """Which backend is live, and how durable it is. The page prints this."""
    if is_shared():
        return {
            "backend": "sheet",
            "durable": True,
            "label": "Shared Google Sheet",
            "detail": "Remarks and sign-offs are saved to the "
                      f"'{WORKSHEET_NAME}' worksheet, so the whole team sees "
                      "the same notes.",
        }
    return {
        "backend": "local",
        "durable": False,
        "label": "This server only",
        "detail": "No service account is connected, so notes are written to "
                  f"{LOCAL_PATH.name} on the server running the app. They "
                  "survive a page refresh but are lost when the app restarts "
                  "or redeploys, and other people do not see them.",
    }


@st.cache_resource(show_spinner=False)
def _worksheet(_key: str, _email: str):
    import gspread
    from google.oauth2.service_account import Credentials

    info = _service_account_info()
    if not info:
        raise RuntimeError("Service account credentials are not configured.")
    creds = Credentials.from_service_account_info(
        info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
        ],
    )
    book = gspread.authorize(creds).open_by_key(sheet_id())
    try:
        sheet = book.worksheet(WORKSHEET_NAME)
    except Exception:
        sheet = book.add_worksheet(title=WORKSHEET_NAME, rows=2000,
                                   cols=len(COLUMNS))
        sheet.update([COLUMNS], "A1")
        return sheet
    if [h.strip() for h in sheet.row_values(1)] != COLUMNS:
        sheet.update([COLUMNS], "A1")
    return sheet


def _coerce(frame: pd.DataFrame) -> pd.DataFrame:
    for col in COLUMNS:
        if col not in frame.columns:
            frame[col] = ""
    frame = frame[COLUMNS].copy()
    frame["order_id"] = frame["order_id"].astype(str).str.strip()
    frame = frame[frame["order_id"] != ""]
    frame["checked"] = (
        frame["checked"].astype(str).str.strip().str.upper()
        .isin(["TRUE", "YES", "1", "Y"])
    )
    # A row edited for its remark alone never gets a checked_by, so it arrives
    # as NaN. Left alone that stringifies to the literal "nan", because NaN is
    # truthy - so the text columns are normalised here, at the one point every
    # backend passes through.
    for col in ("remark", "checked_by", "updated_by"):
        frame[col] = frame[col].fillna("").astype(str)
    frame["updated_at"] = pd.to_datetime(frame["updated_at"], errors="coerce",
                                         format="mixed")
    return frame.reset_index(drop=True)


@st.cache_data(ttl=60, show_spinner=False)
def _fetch_sheet(_key: str, _email: str, _bust: int) -> pd.DataFrame:
    records = _worksheet(_key, _email).get_all_records(expected_headers=COLUMNS)
    frame = pd.DataFrame(records)
    return _empty_notes() if frame.empty else _coerce(frame)


def _read_local() -> pd.DataFrame:
    if not LOCAL_PATH.exists():
        return _empty_notes()
    try:
        raw = json.loads(LOCAL_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _empty_notes()
    rows = [dict(v, order_id=k) for k, v in (raw or {}).items()]
    return _coerce(pd.DataFrame(rows)) if rows else _empty_notes()


def _write_local(notes: pd.DataFrame) -> tuple[bool, str]:
    payload = {
        str(row["order_id"]): {
            "remark": str(row.get("remark", "") or ""),
            "checked": bool(row.get("checked", False)),
            "checked_by": str(row.get("checked_by", "") or ""),
            "updated_at": (
                pd.Timestamp(row["updated_at"]).isoformat()
                if pd.notna(row.get("updated_at")) else ""
            ),
            "updated_by": str(row.get("updated_by", "") or ""),
        }
        for _, row in notes.iterrows()
    }
    try:
        LOCAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOCAL_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True),
                              encoding="utf-8")
        return True, str(LOCAL_PATH)
    except OSError as exc:
        return False, str(exc)


def load_notes() -> pd.DataFrame:
    """Every stored note, whichever backend is live."""
    if not is_shared():
        return _read_local()
    try:
        return _fetch_sheet(sheet_id(), service_account_email(),
                            st.session_state.get("_reflect_version", 0))
    except Exception as exc:  # noqa: BLE001 - surfaced by the page
        st.session_state["_reflect_error"] = f"{type(exc).__name__}: {exc}"
        return _read_local()


def invalidate() -> None:
    st.session_state["_reflect_version"] = (
        st.session_state.get("_reflect_version", 0) + 1
    )


def save_notes(changes: dict[str, dict[str, Any]], updated_by: str
               ) -> tuple[int, str]:
    """Upsert the changed order IDs. Returns (rows written, message).

    Only the rows the editor actually touched are passed in, so an unchanged
    remark is never rewritten and `updated_at` stays meaningful.
    """
    changes = {
        str(k).strip(): v for k, v in (changes or {}).items() if str(k).strip()
    }
    if not changes:
        return 0, "Nothing to save."

    now = pd.Timestamp(datetime.now()).floor("s")
    current = load_notes()
    merged = {
        str(row["order_id"]): row.to_dict() for _, row in current.iterrows()
    }
    for order_id, fields in changes.items():
        row = merged.get(order_id, {"order_id": order_id})
        if "remark" in fields:
            row["remark"] = str(fields["remark"] or "")
        if "checked" in fields:
            row["checked"] = bool(fields["checked"])
            row["checked_by"] = updated_by if row["checked"] else ""
        row["updated_at"] = now
        row["updated_by"] = updated_by
        merged[order_id] = row

    frame = _coerce(pd.DataFrame(list(merged.values())))

    if not is_shared():
        ok, detail = _write_local(frame)
        return (len(changes), f"Saved {len(changes)} row(s) locally.") if ok \
            else (0, f"Could not write {detail}")

    try:
        body = [COLUMNS] + [
            [
                str(row["order_id"]),
                str(row["remark"] or ""),
                "TRUE" if row["checked"] else "FALSE",
                str(row["checked_by"] or ""),
                pd.Timestamp(row["updated_at"]).strftime("%Y-%m-%d %H:%M:%S")
                if pd.notna(row["updated_at"]) else "",
                str(row["updated_by"] or ""),
            ]
            for _, row in frame.iterrows()
        ]
        sheet = _worksheet(sheet_id(), service_account_email())
        sheet.clear()
        sheet.update(body, "A1")
        invalidate()
        return len(changes), f"Saved {len(changes)} row(s) to {WORKSHEET_NAME}."
    except Exception as exc:  # noqa: BLE001 - surfaced by the page
        return 0, f"Could not save: {type(exc).__name__}: {exc}"


def diff_edits(before: pd.DataFrame, after: pd.DataFrame
               ) -> dict[str, dict[str, Any]]:
    """Which order IDs had their remark or checker flag changed."""
    changes: dict[str, dict[str, Any]] = {}
    if after is None or after.empty:
        return changes
    prior = {
        str(row["order_id"]): row
        for _, row in (before if before is not None else pd.DataFrame()).iterrows()
    }
    for _, row in after.iterrows():
        order_id = str(row.get("order_id", "")).strip()
        if not order_id:
            continue
        was = prior.get(order_id)
        old_remark = str(was["remark"]).strip() if was is not None else ""
        old_checked = bool(was["checked"]) if was is not None else False
        new_remark = str(row.get("remark", "") or "").strip()
        new_checked = bool(row.get("checked", False))
        field: dict[str, Any] = {}
        if new_remark != old_remark:
            field["remark"] = new_remark
        if new_checked != old_checked:
            field["checked"] = new_checked
        if field:
            changes[order_id] = field
    return changes
