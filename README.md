# NEODRIFT Interns Audit

A Streamlit web app that reads the NEODRIFT interns order workbook live from
Google Sheets and turns it into a KPI dashboard, automated monthly reports, a
money audit, a returns report, intern scorecards and a configurable exception
engine. Built to be read on a phone as easily as on a laptop.

The app only ever **reads** the audit workbook — it never writes to it.
The one thing it writes is influencer leads, and those go to a **separate**
Google Sheet of their own.

---

## What it shows

| Area | Tabs | What it answers |
|---|---|---|
| **Dashboard** | — | A month you pick, the month before it, the last 7 days, who is active now, and the money at risk. |
| **Interns** | Active now · All interns · Daily activity · Tenure alerts · Scorecards | How many interns are active, what each produced per day, and who is past their tenure window. |
| **Orders & Audit** | Monthly · Overall · Returns · Products & ASINs · Exceptions | All order-side reporting and the row-level exception engine. |
| **Payments & Money** | — | What has been paid, what is owed, and what is exposed. |
| **Influencers** | Submit a lead · Pipeline · Follow-ups · Setup | Sourcing with duplicate detection, plus the admin pipeline. |
| **Settings** | KPI limits · Audit rules · Display & data · Save/load | Every green/amber/red limit and audit rule. |

Every table exports to CSV, and each page offers a combined Excel workbook.

---

## Metric definitions

The core definitions were reconciled row-for-row against the workbook's own
`Overall Audit Report` tab across all 12 live months, and **all 72 checks tie
exactly**. The app therefore agrees with the sheet — and where the sheet later
drifts, the Overall Audit Report page flags the difference.

| Metric | Definition |
|---|---|
| Total orders | Order rows in `MAIN` for the period |
| Not delivered / **Cancelled** | Amazon status is not `Shipped - Delivered to Buyer` |
| Net orders | Total orders − not delivered |
| True cancelled | Amazon status is literally `Cancelled` |
| Returned | Status is `Shipped - Returned to Seller` or `Returning to Seller` |
| Reviews submitted | `REIVEW LINK (ST)` is non-empty |
| Reviews reflected | `REVIEW REFLECTED (FORM)` is TRUE |
| Reflection rate | Reflected ÷ submitted |
| Order submission % | Submitted ÷ net orders |
| Cancellation % | Not delivered ÷ total orders |
| Seller feedback missing | Submitted − seller feedback |
| Checker pending | Submitted − `CHECKER (SHIVAM GOMAT)` |

> **Note on "Cancelled".** The workbook's `Cancellation%` counts every order not
> marked delivered — in-transit and pending orders included, not just genuine
> cancellations. The app keeps that definition so the numbers match, and adds a
> separate **True Cancelled %** for the strict reading. In a part-way-through
> month the loose figure looks alarming simply because orders have not been
> delivered yet.

### Money

`ORDER PRICE` is what the company funds per order, so it is the value used
throughout. The free-text `REVIEW PAYMENT` column (32 distinct spellings) is
folded into five states:

- **PAID** — text contains "paid" or "settled"
- **CANCELLED** — text contains "cancel"
- **HOLD** — text contains "hold"
- **PENDING** — blank
- **UNKNOWN** — anything else, surfaced so the wording can be cleaned up

Three separate exposures are tracked, because they need different actions:

1. **Payment pending** — we still owe this money.
2. **Paid but review not reflected** — money is out, the deliverable is not back.
3. **Paid but not delivered** — money went out on a cancelled or returned order.

---

## Sheet tabs used

| Tab | Used for |
|---|---|
| `MAIN` | Required. Every metric is computed from here. |
| `Overall Audit Report` | Reconciliation against the app's own figures. |
| `INTERN REPORT MANUAL` | Intern roster: status, joining and leaving dates, stipend. |
| `ASIN REPORT` | ASIN-level cross-check. |
| `MONTHLY TARGETS REPORT` | Productwise targets and the sheet's own productwise actuals. |
| `CHECKER` | The team's existing manual red-flag list. |
| `AMAZON ORDER REPORT PASTING` | Order-ID reconciliation against the Amazon export. |

If a tab other than `MAIN` cannot be read, the app degrades gracefully: that
section shows an empty state and the sidebar lists the warning.

Two notes on the source data:

- There is **no tab named "returns report"**. The return trail lives in `MAIN`
  across `AMAZON STATUS`, `RETURN PICKUP BY` and `RETURN CHECKER`, and the
  Returns Report page assembles the report from those columns.
- The `INTERN REPORT` tab is a multi-block manual layout, so intern metrics are
  computed live from `MAIN` and joined to the cleaner `INTERN REPORT MANUAL`
  roster instead. That keeps the figures current and complete.

The Amazon export covers only a rolling ~30-day window, so the order-ID
reconciliation rule is automatically limited to orders inside the window the
export actually covers.

---

## Settings: greens, reds and limits

Everything on the Settings page applies immediately across the app.

**KPI colour bands** — each KPI takes a direction and its limits:

- *Higher is better* — green at or above X, amber at or above Y, else red
- *Lower is better* — green at or below X, amber at or below Y, else red
- *Must stay between* — green inside min–max, amber within a slack either side,
  else red

**Audit rules** — 22 row-level rules across data integrity, fulfilment, the
review pipeline, money, returns, interns and reconciliation. Each can be
switched off, flipped between red and amber, and retuned (days allowed, price
min/max, price tolerance, tenure grace).

### Making settings permanent

Edits are live for the session straight away. **Save** writes
`config/thresholds.json`, which survives a local restart.

On Streamlit Community Cloud the filesystem resets whenever the app restarts,
so a save there is temporary. To make settings permanent:

1. Settings → *Save, load, reset* → **Download thresholds.json**
2. Commit it to the repo at `config/thresholds.json`
3. Push — the app loads it on boot

Saved files are deep-merged onto the defaults, so an older file keeps working
after new KPIs or rules are added.

---

## Interns

The **Interns** area answers "who is working and how are they doing".

Per intern: joining date, end date, tenure length, stipend, orders completed,
cancelled, undelivered, reviews submitted and reflected, plus current status.

**Cancelled and undelivered are separate columns, deliberately.**

| Column | Meaning |
|---|---|
| Cancelled | Amazon status is literally `Cancelled` — the order was called off |
| Undelivered | Every other non-delivered state: returns, stuck in transit, no status yet |

Lumping them together flatters a parcel that is merely late and punishes an
intern for a customer's cancellation. They sum to the not-delivered total used
elsewhere in the app.

**Tenure reminder.** Any *Active* intern whose joining date is more than 30 days
ago raises a standing reminder on the Dashboard and the Interns page:

> This intern's 30-day tenure period is over. Please review their performance
> and take the required action.

It is a persistent banner rather than a modal, so it survives a page refresh and
cannot be dismissed by accident. The 30-day window is editable under
Settings → *Display & data*.

**Daily activity** shows orders per intern per day over a window you choose, so
a drop-off is visible within days rather than at month end.

> Stipend comes from the roster tab and is currently filled for 32 of 85
> interns, none of them the 9 active ones. Those totals will understate the real
> cost until the column is filled in.

## Influencers

Interns paste a profile link; the app canonicalises it and checks it against
every existing lead before saving. These all resolve to the same lead:

```
https://www.instagram.com/moto.wrist?igshid=abc
instagram.com/Moto.Wrist/
https://m.instagram.com/moto.wrist
```

A duplicate is rejected on screen with the lead ID, the intern who sourced it
first, the date, and its current pipeline status. A new lead is saved with the
intern's name, a timestamp and status `New`. Links to a post or reel are
rejected with a prompt to use the profile link instead.

Admins manage contact details, quoted and agreed rates, pipeline status,
follow-up notes and next follow-up dates in an editable grid, filter by status,
intern, platform, rate and date, and export the filtered set.

Leads live in **their own Google Sheet**, written through a service account.
Setup is on the Influencers → *Setup* tab; until it is connected the page
explains what is needed instead of failing.

## Access control

The app is gated behind Google sign-in. Nothing loads — no data, no navigation
— until an approved account signs in. Three addresses are allowed:

- `auditorneodrift@gmail.com`
- `neodriftoffice@gmail.com`
- `admin@neodrift.in`

The list lives in `src/auth.py`, so it is version-controlled and cannot be
changed from inside the running app. Signing in with Google is not enough on
its own: the address must also be on the list, or the visitor gets a refusal
screen. Override the list per-deployment with an `ALLOWED_EMAILS` secret.

**Setup (once).** Create an OAuth client in the
[Google Cloud console](https://console.cloud.google.com/apis/credentials) →
*Create credentials* → *OAuth client ID* → *Web application*, and register your
redirect URI (`https://YOUR-APP.streamlit.app/oauth2callback`, and
`http://localhost:8501/oauth2callback` for local runs). Then copy
`.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` locally, or paste
its contents into Streamlit Cloud → app settings → **Secrets**, filling in the
client ID, client secret and a random `cookie_secret`.

While the Google consent screen is in *Testing*, each of the three accounts must
also be added as a Test user.

`.streamlit/secrets.toml` is gitignored — the real credentials are never
committed.

## Running it locally

```bash
pip install -r requirements.txt
```

```bash
streamlit run streamlit_app.py
```

## Deploying on Streamlit Community Cloud

1. Push this repository to GitHub.
2. On [share.streamlit.io](https://share.streamlit.io) choose **New app**, pick
   the repo and branch, and set the main file to `streamlit_app.py`.
3. Add the `[auth]` secrets from **Access control** above, then deploy.
   `requirements.txt` and `.streamlit/config.toml` are picked up automatically.

The workbook must stay shared as **Anyone with the link → Viewer**; the app
reads it through Google's public gviz endpoint, so there is no API key or
service account needed for the sheet itself. The OAuth credentials above are
only for signing users in.

### Pointing at a different workbook

The sheet key is taken from the `/d/<SHEET_ID>/` part of the sheet URL. To
override the built-in default, either add a secret (Streamlit Cloud → app
settings → Secrets, or a local `.streamlit/secrets.toml`):

```toml
SHEET_ID = "your_sheet_id_here"
```

or set the `INTERNS_SHEET_ID` environment variable.

`.streamlit/secrets.toml` is gitignored.

---

## Project layout

```
streamlit_app.py            entry point, navigation, sidebar
requirements.txt
.streamlit/config.toml      theme
config/thresholds.json      saved KPI limits and audit rules
src/
  data.py                   Google Sheets loaders and normalisation
  metrics.py                KPIs, periods, breakdowns, intern table, tenure
  audit.py                  the row-level rule engine
  influencers.py            lead store: URL canonicalisation, read/write
  settings_store.py         default limits, rules, load/save, grading
  theme.py                  Gemini-style CSS and the motion-blur reveal
  ui.py                     responsive KPI cards, chips, charts, exports
  auth.py                   Google sign-in gate and email allow-list
app_pages/
  common.py                 cached audit runs and shared KPI blocks
  page_dashboard.py         Dashboard
  page_interns.py           Interns (5 tabs)
  page_audit.py             Orders & Audit shell (5 tabs)
  page_monthly.py           - embedded: monthly report
  page_overall.py           - embedded: overall report
  page_returns.py           - embedded: returns
  page_products.py          - embedded: products & ASINs
  page_exceptions.py        - embedded: exceptions
  page_money.py             Payments & Money
  page_influencers.py       Influencers (4 tabs)
  page_settings.py          Settings
```

## Notes

- Sheet reads are cached; the window is set on Settings → *Display & data*
  (default 10 minutes). **Refresh data** in the sidebar forces a re-read.
- KPI rows are a wrapping CSS grid rather than `st.columns`, because columns
  squeeze on a narrow screen instead of reflowing. Cards drop to two per row on
  a phone and wide tables scroll horizontally.
- The intern score weights reflection 35, submission 25, delivery 20, seller
  feedback 10 and checker sign-off 10. Interns below the minimum order count
  (Settings → *Display & data*) are listed last and marked as a small sample
  rather than dropped.
