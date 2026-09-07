# NEODRIFT Interns Audit

A Streamlit web app that reads the NEODRIFT interns order workbook live from
Google Sheets and turns it into a KPI dashboard, automated monthly reports, a
money audit, a returns report, intern scorecards and a configurable exception
engine. Built to be read on a phone as easily as on a laptop.

The app never writes to the sheet. It only reads.

---

## What it shows

| Page | What it answers |
|---|---|
| **Dashboard** | One screen for a stand-up: a month you pick, the month before it, the last 7 days, and the money at risk right now. |
| **Monthly Report** | The automated write-up for one month, with month-on-month deltas and breakdowns by intern, product, status and target. |
| **Overall Audit Report** | Every month in one graded matrix, plus a reconciliation against the workbook's own `Overall Audit Report` tab. |
| **Payments & Money** | What has been paid, what is still owed, and what is exposed because money went out before the review came back. |
| **Returns Report** | Return rate by month, product and intern, with sign-off and pickup gaps. |
| **Intern Report** | Roster status plus a 0–100 scorecard per intern, and a drill-down on any one person. |
| **Products & ASINs** | Product and ASIN performance, target vs actual, SKU spread, and cross-checks against the `ASIN REPORT` tab. |
| **Audit & Exceptions** | Every row-level rule violation, filterable and exportable. |
| **Settings** | The green/amber/red limits and the audit rules — all editable in the browser. |

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
3. Deploy. `requirements.txt` and `.streamlit/config.toml` are picked up
   automatically.

The workbook must stay shared as **Anyone with the link → Viewer**; the app
reads it through Google's public gviz endpoint, so there is no API key or
service account to configure.

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
  metrics.py                KPI computation, periods, breakdowns, variance
  audit.py                  the row-level rule engine
  settings_store.py         default limits, rules, load/save, grading
  ui.py                     responsive KPI cards, chips, charts, exports
app_pages/
  common.py                 cached audit runs and shared KPI blocks
  page_dashboard.py
  page_monthly.py
  page_overall.py
  page_money.py
  page_returns.py
  page_interns.py
  page_products.py
  page_exceptions.py
  page_settings.py
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
