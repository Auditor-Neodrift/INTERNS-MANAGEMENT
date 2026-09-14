"""Influencer sourcing and pipeline.

Tabs: Submit a lead | Pipeline | Follow-ups | Setup
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import influencers as inf
import ui

STATUS_TONE = {
    "New": "grey", "Sourced": "grey", "Contacted": "amber",
    "Negotiating": "amber", "Agreed": "green", "Collab done": "green",
    "On hold": "amber", "Rejected": "red",
}

EDITABLE = [
    "status", "contact_name", "phone", "email",
    "quoted_rate", "agreed_rate", "follow_up_notes", "next_follow_up",
]

DISPLAY_NAMES = {
    "lead_id": "Lead ID", "profile_url": "Profile", "platform": "Platform",
    "handle": "Handle", "sourced_by": "Sourced by", "sourced_at": "Sourced at",
    "status": "Status", "contact_name": "Contact", "phone": "Phone",
    "email": "Email", "quoted_rate": "Quoted rate", "agreed_rate": "Agreed rate",
    "follow_up_notes": "Notes", "next_follow_up": "Next follow-up",
    "updated_at": "Updated at", "updated_by": "Updated by",
}


def render(bundle, config: dict) -> None:
    symbol = config.get("display", {}).get("currency_symbol", "Rs")
    st.title("Influencers")
    ui.hero(
        "Source influencers without duplicating work",
        "Paste a profile link and the app checks it against every lead already "
        "in the system before saving. Duplicates are rejected with the name of "
        "the intern who found it first.",
    )

    configured = inf.is_configured()
    leads = inf.load_leads() if configured else inf._empty()
    error = st.session_state.pop("_leads_error", None)
    if error:
        st.error(f"Could not read the lead sheet. {error}", icon=":material/error:")

    tabs = st.tabs(["Submit a lead", "Pipeline", "Follow-ups", "Setup"])
    with tabs[0]:
        _submit_tab(leads, configured)
    with tabs[1]:
        _pipeline_tab(leads, configured, symbol, config)
    with tabs[2]:
        _followups_tab(leads, configured, symbol)
    with tabs[3]:
        _setup_tab(configured)


def _who() -> str:
    try:
        return str(getattr(st.user, "email", "") or "unknown")
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------
def _submit_tab(leads: pd.DataFrame, configured: bool) -> None:
    if not configured:
        ui.callout(
            ["Connect the lead sheet on the Setup tab before submitting leads."],
            "amber", title="Not connected yet",
        )
        return

    ui.note("Paste the influencer's profile link. The check runs as you type.")
    col_a, col_b = st.columns([3, 2])
    with col_a:
        raw = st.text_input(
            "Influencer profile link", key="lead_url",
            placeholder="https://www.instagram.com/their.handle",
        )
    with col_b:
        sourced_by = st.text_input(
            "Sourced by", key="lead_by", value=st.session_state.get("lead_by_last", ""),
            placeholder="Intern name",
        )

    profile = inf.normalise_profile(raw) if raw.strip() else None
    duplicate = inf.find_duplicate(leads, profile) if profile and profile.ok else None

    # ---- live verdict
    if profile is None:
        st.caption("Nothing entered yet.")
    elif not profile.ok:
        st.warning(profile.error, icon=":material/link_off:")
    elif duplicate is not None:
        _duplicate_card(duplicate)
    else:
        st.success(
            f"New lead. {profile.platform} · {profile.handle}",
            icon=":material/check_circle:",
        )

    can_add = bool(profile and profile.ok and duplicate is None and sourced_by.strip())
    if st.button("Add lead", type="primary", disabled=not can_add,
                 icon=":material/add:", key="lead_add"):
        added, message, existing = inf.add_lead(profile, sourced_by.strip())
        if added:
            st.session_state["lead_by_last"] = sourced_by.strip()
            st.success(f"{profile.platform} · {profile.handle} — {message}",
                       icon=":material/check:")
            st.rerun()
        elif existing is not None:
            _duplicate_card(existing)
        else:
            st.error(message, icon=":material/error:")

    if profile and profile.ok and duplicate is None and not sourced_by.strip():
        st.caption("Enter who sourced it to enable the button.")

    # ---- recent
    ui.section("Recently added")
    if leads.empty:
        ui.empty_state("No leads yet. The first one you add will show here.")
        return
    recent = leads.sort_values("sourced_at", ascending=False, na_position="last").head(15)
    ui.show_table(_view(recent, ["lead_id", "platform", "handle", "sourced_by",
                                 "sourced_at", "status", "profile_url"]))


def _duplicate_card(row: pd.Series) -> None:
    sourced_at = row.get("sourced_at")
    when = (
        pd.Timestamp(sourced_at).strftime("%d %b %Y")
        if pd.notna(sourced_at) else "an earlier date"
    )
    by = str(row.get("sourced_by") or "an unknown intern")
    ui.alert_card(
        "Already sourced - this lead was rejected",
        f"{row.get('platform', '')} · {row.get('handle', '')} is already in the "
        f"system as {row.get('lead_id', '')}, currently "
        f"{row.get('status', 'New')}.",
        meta=f"First sourced by {by} on {when}",
        tone="red",
    )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def _pipeline_tab(leads: pd.DataFrame, configured: bool, symbol: str,
                  config: dict) -> None:
    if not configured:
        ui.callout(["Connect the lead sheet on the Setup tab."], "amber")
        return
    if leads.empty:
        ui.empty_state("No leads yet.")
        return

    stats = inf.summarise(leads)
    ui.render_kpis(
        [
            ui.kpi("Total Leads", stats["total"], unit="n", tone="neutral"),
            ui.kpi("Open", stats["open"], unit="n", tone="amber" if stats["open"] else "green",
                   sub="new, contacted or negotiating"),
            ui.kpi("Agreed", stats["agreed"], unit="n", tone="green"),
            ui.kpi("Rejected", stats["rejected"], unit="n", tone="grey"),
            ui.kpi("Interns Sourcing", stats["interns"], unit="n", tone="neutral"),
            ui.kpi("Avg Agreed Rate", stats["avg_agreed"], unit="Rs", tone="neutral"),
            ui.kpi("Follow-ups Due", stats["due_follow_ups"], unit="n",
                   tone="red" if stats["due_follow_ups"] else "green"),
        ],
        config,
    )

    # ---- filters
    row_a = st.columns([1, 1, 1])
    with row_a[0]:
        pick_status = st.multiselect("Status", inf.PIPELINE_STATUSES, key="inf_status")
    with row_a[1]:
        who = sorted(leads["sourced_by"].replace("", "(blank)").dropna().unique())
        pick_who = st.multiselect("Sourced by", who, key="inf_who")
    with row_a[2]:
        platforms = sorted(leads["platform"].replace("", "(blank)").dropna().unique())
        pick_platform = st.multiselect("Platform", platforms, key="inf_platform")

    row_b = st.columns([2, 2])
    with row_b[0]:
        rates = leads["agreed_rate"].dropna()
        hi = int(rates.max()) if len(rates) else 100000
        rate_range = st.slider(
            "Agreed rate", 0, max(hi, 1000), (0, max(hi, 1000)),
            step=500, key="inf_rate",
        )
        include_unrated = st.checkbox("Include leads with no agreed rate",
                                      value=True, key="inf_unrated")
    with row_b[1]:
        dates = leads["sourced_at"].dropna()
        lo_d = dates.min().date() if len(dates) else date.today() - timedelta(days=30)
        hi_d = dates.max().date() if len(dates) else date.today()
        picked_dates = st.date_input("Sourced between", value=(lo_d, hi_d),
                                     key="inf_dates")

    view = leads.copy()
    if pick_status:
        view = view[view["status"].isin(pick_status)]
    if pick_who:
        view = view[view["sourced_by"].replace("", "(blank)").isin(pick_who)]
    if pick_platform:
        view = view[view["platform"].replace("", "(blank)").isin(pick_platform)]

    rate = view["agreed_rate"]
    in_range = rate.between(rate_range[0], rate_range[1])
    view = view[in_range | (rate.isna() & include_unrated)]

    if isinstance(picked_dates, (tuple, list)) and len(picked_dates) == 2:
        start, end = picked_dates
        sourced = view["sourced_at"]
        view = view[
            sourced.isna()
            | (
                (sourced >= pd.Timestamp(start))
                & (sourced < pd.Timestamp(end) + pd.Timedelta(days=1))
            )
        ]

    ui.chips([(f"{len(view)} of {len(leads)} leads", "grey")])

    # ---- funnel
    counts = leads["status"].value_counts().reindex(inf.PIPELINE_STATUSES).fillna(0)
    fig = go.Figure(go.Bar(
        x=counts.values, y=counts.index, orientation="h",
        marker_color=["#10754F" if s in ("Agreed", "Collab done")
                      else "#BD2D46" if s == "Rejected"
                      else "#965708" if s in ("Contacted", "Negotiating", "On hold")
                      else "#2F6BFF" for s in counts.index],
        text=counts.values.astype(int), textposition="auto",
    ))
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(title="Pipeline", xaxis_title="Leads")
    ui.show_chart(fig, height=300, legend=False)

    if view.empty:
        ui.empty_state("No leads match those filters.")
        return

    # ---- editable grid
    ui.section("Manage leads", "Edit any cell, then save. Changes write to the sheet.")
    editor_src = view[["lead_id", "platform", "handle", "sourced_by",
                       "sourced_at"] + EDITABLE].copy()
    editor_src["sourced_at"] = pd.to_datetime(
        editor_src["sourced_at"], errors="coerce"
    ).dt.strftime("%d %b %Y")
    editor_src["next_follow_up"] = pd.to_datetime(
        editor_src["next_follow_up"], errors="coerce"
    ).dt.date

    edited = st.data_editor(
        editor_src,
        width="stretch", hide_index=True, height=460, key="inf_editor",
        column_config={
            "lead_id": st.column_config.TextColumn("Lead ID", disabled=True),
            "platform": st.column_config.TextColumn("Platform", disabled=True),
            "handle": st.column_config.TextColumn("Handle", disabled=True),
            "sourced_by": st.column_config.TextColumn("Sourced by", disabled=True),
            "sourced_at": st.column_config.TextColumn("Sourced at", disabled=True),
            "status": st.column_config.SelectboxColumn(
                "Status", options=inf.PIPELINE_STATUSES, required=True),
            "contact_name": st.column_config.TextColumn("Contact"),
            "phone": st.column_config.TextColumn("Phone"),
            "email": st.column_config.TextColumn("Email"),
            "quoted_rate": st.column_config.NumberColumn(
                f"Quoted ({symbol})", min_value=0, step=500, format="%d"),
            "agreed_rate": st.column_config.NumberColumn(
                f"Agreed ({symbol})", min_value=0, step=500, format="%d"),
            "follow_up_notes": st.column_config.TextColumn("Notes", width="medium"),
            "next_follow_up": st.column_config.DateColumn("Next follow-up"),
        },
    )

    changes = _diff(editor_src, edited)
    col_a, col_b = st.columns([1, 3])
    with col_a:
        if st.button(f"Save {len(changes)} change(s)", type="primary",
                     disabled=not changes, icon=":material/save:", key="inf_save"):
            count, message = inf.update_leads(changes, _who())
            if count:
                st.success(message, icon=":material/check:")
                st.rerun()
            else:
                st.error(message, icon=":material/error:")
    with col_b:
        if changes:
            st.caption(f"Unsaved: {', '.join(sorted(changes))}")

    ui.section("Export")
    export = _view(view, list(DISPLAY_NAMES))
    ui.download_row({"influencer leads": export}, excel_name="influencer-leads",
                    key_prefix="inf")


def _diff(before: pd.DataFrame, after: pd.DataFrame) -> dict[str, dict]:
    """Only the cells the admin actually changed, keyed by lead_id."""
    changes: dict[str, dict] = {}
    if after is None or after.empty:
        return changes
    old = before.set_index("lead_id")
    new = after.set_index("lead_id")
    for lead_id in new.index:
        if lead_id not in old.index:
            continue
        for column in EDITABLE:
            a, b = old.at[lead_id, column], new.at[lead_id, column]
            if pd.isna(a) and pd.isna(b):
                continue
            if pd.isna(a) != pd.isna(b) or str(a) != str(b):
                changes.setdefault(str(lead_id), {})[column] = b
    return changes


# ---------------------------------------------------------------------------
# Follow-ups
# ---------------------------------------------------------------------------
def _followups_tab(leads: pd.DataFrame, configured: bool, symbol: str) -> None:
    if not configured:
        ui.callout(["Connect the lead sheet on the Setup tab."], "amber")
        return
    if leads.empty:
        ui.empty_state("No leads yet.")
        return

    today = pd.Timestamp(date.today())
    follow = leads["next_follow_up"]
    overdue = leads[follow.notna() & (follow < today)]
    due_today = leads[follow.notna() & (follow == today)]
    upcoming = leads[follow.notna() & (follow > today)
                     & (follow <= today + pd.Timedelta(days=7))]
    unscheduled = leads[follow.isna() & leads["status"].isin(inf.OPEN_STATUSES)]

    ui.chips([
        (f"{len(overdue)} overdue", "red" if len(overdue) else "green"),
        (f"{len(due_today)} due today", "amber" if len(due_today) else "green"),
        (f"{len(upcoming)} next 7 days", "grey"),
        (f"{len(unscheduled)} open with no date", "amber" if len(unscheduled) else "green"),
    ])

    for label, frame, tone in (
        ("Overdue", overdue, "red"),
        ("Due today", due_today, "amber"),
        ("Next 7 days", upcoming, "grey"),
        ("Open, no follow-up date", unscheduled, "amber"),
    ):
        ui.section(f"{label} ({len(frame)})")
        if frame.empty:
            ui.callout([f"Nothing {label.lower()}."], "green")
            continue
        cols = ["lead_id", "platform", "handle", "status", "sourced_by",
                "next_follow_up", "follow_up_notes", "quoted_rate",
                "agreed_rate", "profile_url"]
        ui.show_table(_view(frame.sort_values("next_follow_up", na_position="last"), cols))


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
def _setup_tab(configured: bool) -> None:
    if configured:
        ui.callout(
            [
                f"Connected to the lead sheet. Service account: "
                f"<code>{inf.service_account_email()}</code>",
                f"Leads are stored in the <strong>{inf.WORKSHEET_NAME}</strong> tab.",
            ],
            "green", title="Connected",
        )
        st.link_button("Open the lead sheet", inf.sheet_url())
        if st.button("Reload leads", icon=":material/refresh:", key="inf_reload"):
            inf.invalidate()
            st.rerun()
        return

    st.markdown(
        """
Leads need their own Google Sheet plus a service account that can write to it.

**1. Create the sheet.** Make a new blank Google Sheet, name it something like
*NEODRIFT Influencer Leads*, and copy its key from the URL:
`docs.google.com/spreadsheets/d/`**`<KEY>`**`/edit`

**2. Create a service account.** In the
[Google Cloud console](https://console.cloud.google.com/iam-admin/serviceaccounts)
→ *Create service account* → give it any name → *Done*. Open it, go to **Keys**
→ *Add key* → *Create new key* → **JSON**, and download the file. Make sure the
[Google Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com)
is enabled for that project.

**3. Share the sheet with it.** Open the JSON, copy the `client_email` value
(it ends in `.iam.gserviceaccount.com`), then share your new sheet with that
address as **Editor**. This is the step people miss.

**4. Add both to Streamlit secrets** — app settings → *Secrets*:

```toml
INFLUENCER_SHEET_ID = "your_new_sheet_key"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
client_email = "...@....iam.gserviceaccount.com"
client_id = "..."
token_uri = "https://oauth2.googleapis.com/token"
```

Paste the `private_key` exactly as it appears in the JSON, keeping the `\\n`
sequences. The app creates the **INFLUENCER LEADS** tab and its header row on
first use.
"""
    )
    ui.callout(
        [
            "The service account is separate from the Google login. Sign-in "
            "decides who may open the app; this account is how the app writes "
            "rows to the sheet.",
        ],
        "grey",
    )


# ---------------------------------------------------------------------------
def _view(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    present = [c for c in columns if c in frame.columns]
    out = frame[present].copy()
    for col in ("sourced_at", "updated_at", "next_follow_up"):
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce").dt.strftime("%d %b %Y")
    return out.rename(columns=DISPLAY_NAMES).reset_index(drop=True)
