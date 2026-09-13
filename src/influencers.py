"""Influencer lead store.

Leads live in their own Google Sheet, written through a service account. That
keeps the audit workbook untouched while still letting the team open the leads
in Sheets and edit by hand.

Duplicate detection works on a canonical form of the profile URL rather than
the raw string, so these all collapse to the same lead:

    https://www.instagram.com/moto.wrist?igshid=abc
    instagram.com/moto.wrist/
    https://m.instagram.com/Moto.Wrist

Configure with two secrets: INFLUENCER_SHEET_ID and a [gcp_service_account]
block. Until both are present the page explains the setup instead of failing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, date
from typing import Any
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

WORKSHEET_NAME = "INFLUENCER LEADS"

COLUMNS = [
    "lead_id", "profile_url", "canonical", "platform", "handle",
    "sourced_by", "sourced_at", "status",
    "contact_name", "phone", "email",
    "quoted_rate", "agreed_rate",
    "follow_up_notes", "next_follow_up",
    "updated_at", "updated_by",
]

PIPELINE_STATUSES = [
    "New", "Sourced", "Contacted", "Negotiating",
    "Agreed", "Collab done", "On hold", "Rejected",
]
OPEN_STATUSES = {"New", "Sourced", "Contacted", "Negotiating"}

ADMIN_FIELDS = [
    "status", "contact_name", "phone", "email",
    "quoted_rate", "agreed_rate", "follow_up_notes", "next_follow_up",
]

# host fragment -> platform label
_PLATFORMS = {
    "instagram": "Instagram",
    "youtube": "YouTube",
    "youtu.be": "YouTube",
    "tiktok": "TikTok",
    "facebook": "Facebook",
    "fb.watch": "Facebook",
    "twitter": "X",
    "x.com": "X",
    "linkedin": "LinkedIn",
    "snapchat": "Snapchat",
    "threads": "Threads",
}
# Segments that mean the link points at a piece of content, not a profile.
_CONTENT_SEGMENTS = {
    "p", "reel", "reels", "tv", "stories", "story",
    "watch", "shorts", "video", "posts", "status",
}
# Segments that merely wrap the handle - the next segment is the real one.
_CONTAINER_SEGMENTS = {"channel", "c", "user", "profile", "in", "pub", "@"}


# ---------------------------------------------------------------------------
# URL canonicalisation
# ---------------------------------------------------------------------------
@dataclass
class Profile:
    raw: str
    canonical: str = ""
    platform: str = ""
    handle: str = ""
    ok: bool = False
    error: str = ""


def normalise_profile(raw: str) -> Profile:
    """Reduce a profile link to platform + handle, ignoring tracking noise."""
    text = str(raw or "").strip()
    if not text:
        return Profile(raw=text, error="Enter a profile link.")

    candidate = text if "://" in text else f"https://{text}"
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return Profile(raw=text, error="That does not look like a valid link.")

    host = (parsed.netloc or "").lower().split(":")[0]
    host = re.sub(r"^(www\.|m\.|mobile\.)", "", host)
    if not host or "." not in host:
        return Profile(raw=text, error="That does not look like a valid link.")

    platform = ""
    for fragment, label in _PLATFORMS.items():
        if fragment in host:
            platform = label
            break
    if not platform:
        platform = host.split(".")[0].title()

    segments = [s for s in (parsed.path or "").split("/") if s]
    handle = ""
    for seg in segments:
        cleaned = seg.lstrip("@").strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in _CONTENT_SEGMENTS and host != "youtu.be":
            return Profile(
                raw=text, platform=platform,
                error=(
                    "That is a link to a post or video, not a profile. "
                    "Open the creator's profile and copy that link instead."
                ),
            )
        if lowered in _CONTAINER_SEGMENTS:
            continue
        handle = cleaned
        break
    if not handle and host == "youtu.be":
        handle = segments[0] if segments else ""

    if not handle:
        return Profile(
            raw=text, platform=platform,
            error="No profile name found in that link - check it points at a profile.",
        )

    handle_key = handle.lower().rstrip(".")
    return Profile(
        raw=text,
        canonical=f"{platform.lower()}:{handle_key}",
        platform=platform,
        handle=handle,
        ok=True,
    )


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def sheet_id() -> str:
    try:
        return str(st.secrets.get("INFLUENCER_SHEET_ID", "") or "").strip()
    except Exception:
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


def is_configured() -> bool:
    return bool(sheet_id()) and _service_account_info() is not None


def service_account_email() -> str:
    info = _service_account_info() or {}
    return str(info.get("client_email", ""))


def sheet_url() -> str:
    key = sheet_id()
    return f"https://docs.google.com/spreadsheets/d/{key}/edit" if key else ""


@st.cache_resource(show_spinner=False)
def _worksheet(_key: str, _email: str):
    """Authorise once per session and return the leads worksheet."""
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
        sheet = book.add_worksheet(title=WORKSHEET_NAME, rows=1000, cols=len(COLUMNS))
        sheet.update([COLUMNS], "A1")
        return sheet

    header = sheet.row_values(1)
    if [h.strip() for h in header] != COLUMNS:
        sheet.update([COLUMNS], "A1")
    return sheet


def worksheet():
    return _worksheet(sheet_id(), service_account_email())


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------
def _empty() -> pd.DataFrame:
    frame = pd.DataFrame(columns=COLUMNS)
    for col in ("quoted_rate", "agreed_rate"):
        frame[col] = pd.Series(dtype=float)
    for col in ("sourced_at", "next_follow_up", "updated_at"):
        frame[col] = pd.Series(dtype="datetime64[ns]")
    return frame


@st.cache_data(ttl=60, show_spinner=False)
def _fetch(_key: str, _email: str, _bust: int) -> pd.DataFrame:
    records = worksheet().get_all_records(expected_headers=COLUMNS)
    frame = pd.DataFrame(records)
    if frame.empty:
        return _empty()
    for col in COLUMNS:
        if col not in frame.columns:
            frame[col] = ""
    frame = frame[COLUMNS]
    frame = frame[frame["lead_id"].astype(str).str.strip() != ""]
    for col in ("quoted_rate", "agreed_rate"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    for col in ("sourced_at", "updated_at"):
        frame[col] = pd.to_datetime(frame[col], errors="coerce", format="mixed")
    frame["next_follow_up"] = pd.to_datetime(
        frame["next_follow_up"], errors="coerce", format="mixed"
    )
    frame["status"] = frame["status"].replace("", "New")
    return frame.reset_index(drop=True)


def load_leads() -> pd.DataFrame:
    """All leads, or an empty frame when the store is not configured."""
    if not is_configured():
        return _empty()
    try:
        return _fetch(sheet_id(), service_account_email(),
                      st.session_state.get("_leads_version", 0))
    except Exception as exc:  # noqa: BLE001 - surfaced by the page
        st.session_state["_leads_error"] = f"{type(exc).__name__}: {exc}"
        return _empty()


def invalidate() -> None:
    st.session_state["_leads_version"] = st.session_state.get("_leads_version", 0) + 1


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------
def find_duplicate(leads: pd.DataFrame, profile: Profile) -> pd.Series | None:
    """The existing lead matching this profile, if any."""
    if leads.empty or not profile.ok:
        return None
    match = leads[
        leads["canonical"].astype(str).str.strip().str.lower() == profile.canonical
    ]
    if match.empty:
        return None
    return match.sort_values("sourced_at", na_position="last").iloc[0]


def _next_lead_id(leads: pd.DataFrame) -> str:
    numbers = (
        leads["lead_id"].astype(str).str.extract(r"(\d+)", expand=False)
        .pipe(pd.to_numeric, errors="coerce").dropna()
        if not leads.empty else pd.Series(dtype=float)
    )
    nxt = int(numbers.max()) + 1 if len(numbers) else 1
    return f"LD{nxt:05d}"


def add_lead(
    profile: Profile, sourced_by: str, status: str = "New"
) -> tuple[bool, str, pd.Series | None]:
    """Append a new lead. Returns (added, message, duplicate_row)."""
    if not profile.ok:
        return False, profile.error or "That link could not be read.", None
    if not is_configured():
        return False, "The lead store is not configured yet.", None

    leads = load_leads()
    duplicate = find_duplicate(leads, profile)
    if duplicate is not None:
        return False, "This influencer has already been sourced.", duplicate

    now = datetime.now()
    row = {
        "lead_id": _next_lead_id(leads),
        "profile_url": profile.raw,
        "canonical": profile.canonical,
        "platform": profile.platform,
        "handle": profile.handle,
        "sourced_by": sourced_by,
        "sourced_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "status": status if status in PIPELINE_STATUSES else "New",
        "contact_name": "", "phone": "", "email": "",
        "quoted_rate": "", "agreed_rate": "",
        "follow_up_notes": "", "next_follow_up": "",
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "updated_by": sourced_by,
    }
    try:
        worksheet().append_row(
            [row[c] for c in COLUMNS], value_input_option="USER_ENTERED"
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"Could not save the lead ({type(exc).__name__}: {exc})", None

    invalidate()
    return True, f"Added as {row['lead_id']}.", None


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value != value:
        return ""
    if isinstance(value, (datetime, date, pd.Timestamp)):
        if isinstance(value, pd.Timestamp) and pd.isna(value):
            return ""
        return pd.Timestamp(value).strftime("%Y-%m-%d")
    return str(value)


def update_leads(changes: dict[str, dict[str, Any]], updated_by: str) -> tuple[int, str]:
    """Apply admin edits. `changes` is {lead_id: {column: value}}."""
    if not changes:
        return 0, "Nothing to save."
    if not is_configured():
        return 0, "The lead store is not configured yet."

    try:
        sheet = worksheet()
        ids = sheet.col_values(1)
        row_of = {str(v).strip(): i + 1 for i, v in enumerate(ids) if str(v).strip()}
        index_of = {name: i for i, name in enumerate(COLUMNS)}
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        payload = []
        for lead_id, fields in changes.items():
            row_no = row_of.get(str(lead_id).strip())
            if not row_no:
                continue
            for column, value in fields.items():
                if column not in index_of:
                    continue
                col_no = index_of[column] + 1
                payload.append({
                    "range": gspread_a1(row_no, col_no),
                    "values": [[_cell(value)]],
                })
            payload.append({
                "range": gspread_a1(row_no, index_of["updated_at"] + 1),
                "values": [[stamp]],
            })
            payload.append({
                "range": gspread_a1(row_no, index_of["updated_by"] + 1),
                "values": [[updated_by]],
            })
        if not payload:
            return 0, "No matching leads were found to update."
        sheet.batch_update(payload, value_input_option="USER_ENTERED")
    except Exception as exc:  # noqa: BLE001
        return 0, f"Could not save changes ({type(exc).__name__}: {exc})"

    invalidate()
    return len(changes), f"Saved {len(changes)} lead(s)."


def gspread_a1(row: int, col: int) -> str:
    letters = ""
    while col > 0:
        col, rem = divmod(col - 1, 26)
        letters = chr(65 + rem) + letters
    return f"{letters}{row}"


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def summarise(leads: pd.DataFrame) -> dict[str, Any]:
    if leads.empty:
        return {"total": 0, "open": 0, "agreed": 0, "rejected": 0,
                "interns": 0, "avg_agreed": None, "due_follow_ups": 0}
    today = pd.Timestamp(date.today())
    follow = leads["next_follow_up"]
    return {
        "total": int(len(leads)),
        "open": int(leads["status"].isin(OPEN_STATUSES).sum()),
        "agreed": int(leads["status"].isin(["Agreed", "Collab done"]).sum()),
        "rejected": int((leads["status"] == "Rejected").sum()),
        "interns": int(leads["sourced_by"].replace("", pd.NA).nunique()),
        "avg_agreed": (
            float(leads["agreed_rate"].dropna().mean())
            if leads["agreed_rate"].notna().any() else None
        ),
        "due_follow_ups": int((follow.notna() & (follow <= today)).sum()),
    }
