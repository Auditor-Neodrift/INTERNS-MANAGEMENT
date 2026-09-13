"""Gemini-inspired visual theme for the app.

Design notes:
  * Surfaces are white cards floating on a cool grey page, corners 16-28px.
  * The signature blue -> purple -> pink gradient is used sparingly: page
    titles, the active tab underline, primary buttons and card accents.
  * Everything enters with a short motion-blur reveal (blur + lift + fade),
    staggered down the page so a screen resolves rather than snapping in.
  * Honours prefers-reduced-motion: the blur and lift are dropped entirely.
"""
from __future__ import annotations

CSS = """
<style>
  :root {
    --g-blue: #4285F4;
    --g-purple: #9B72CB;
    --g-pink: #D96570;
    --g-grad: linear-gradient(95deg, #4285F4 0%, #7C6BD1 42%, #9B72CB 68%, #D96570 100%);
    --g-grad-soft: linear-gradient(95deg, rgba(66,133,244,.13) 0%, rgba(155,114,203,.13) 55%, rgba(217,101,112,.13) 100%);

    --g-bg: #F0F4F9;
    --g-surface: #FFFFFF;
    --g-surface-2: #F7F9FC;
    --g-border: #DDE3EA;
    --g-border-soft: #E8EDF3;

    --g-text: #1F1F1F;
    --g-text-2: #444746;
    --g-text-3: #6B7280;

    --g-green: #1E8E3E;
    --g-amber: #E37400;
    --g-red: #D93025;
    --g-green-bg: #E6F4EA;
    --g-amber-bg: #FEF7E0;
    --g-red-bg: #FCE8E6;
    --g-grey-bg: #EDF1F6;

    --g-r: 16px;
    --g-r-lg: 26px;
    --g-shadow: 0 1px 2px rgba(31,31,31,.05), 0 4px 14px rgba(31,31,31,.05);
    --g-shadow-hi: 0 2px 6px rgba(31,31,31,.07), 0 10px 28px rgba(31,31,31,.08);
    --g-ease: cubic-bezier(.2, 0, 0, 1);
  }

  /* ---------- page shell ---------- */
  .stApp { background: var(--g-bg); }
  [data-testid="stMain"] .block-container {
    padding-top: 1.6rem; padding-bottom: 4rem; max-width: 1480px;
  }
  footer, #MainMenu { visibility: hidden; }

  h1, h2, h3, h4 { color: var(--g-text); letter-spacing: -.018em; font-weight: 500; }
  [data-testid="stMain"] h1 {
    font-size: 2.05rem; line-height: 1.18; margin-bottom: .2rem;
    background: var(--g-grad);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent; color: transparent;
    width: fit-content; padding-right: .1em;
  }
  [data-testid="stMain"] h3 { font-size: 1.12rem; margin-top: 1.7rem; }

  /* ---------- motion blur reveal ---------- */
  @keyframes gBlurIn {
    0%   { opacity: 0; transform: translateY(16px) scale(.992); filter: blur(12px); }
    55%  { opacity: 1; }
    100% { opacity: 1; transform: none; filter: blur(0); }
  }
  @keyframes gBlurInSoft {
    0%   { opacity: 0; transform: translateY(8px); filter: blur(7px); }
    100% { opacity: 1; transform: none; filter: blur(0); }
  }
  [data-testid="stMain"] [data-testid="stElementContainer"],
  [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
    animation: gBlurIn .52s var(--g-ease) both;
  }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(1)  { animation-delay: .00s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(2)  { animation-delay: .03s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(3)  { animation-delay: .06s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(4)  { animation-delay: .09s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(5)  { animation-delay: .12s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(6)  { animation-delay: .15s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(7)  { animation-delay: .18s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(8)  { animation-delay: .21s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(n+9) { animation-delay: .24s }
  [data-baseweb="tab-panel"] { animation: gBlurInSoft .42s var(--g-ease) both; }

  /* ---------- KPI cards ---------- */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(176px, 1fr));
    gap: .7rem; margin: .5rem 0 1.15rem 0;
  }
  .kpi-card {
    position: relative; overflow: hidden;
    background: var(--g-surface);
    border: 1px solid var(--g-border-soft);
    border-radius: var(--g-r);
    padding: .85rem .95rem .8rem;
    box-shadow: var(--g-shadow);
    transition: transform .32s var(--g-ease), box-shadow .32s var(--g-ease),
                filter .32s var(--g-ease);
    animation: gBlurInSoft .5s var(--g-ease) both;
    min-width: 0;
  }
  .kpi-card::before {
    content: ""; position: absolute; inset: 0 0 auto 0; height: 3px;
    background: var(--accent, var(--g-blue)); opacity: .9;
  }
  .kpi-card:hover { transform: translateY(-2px); box-shadow: var(--g-shadow-hi); }
  .kpi-grid .kpi-card:nth-child(1) { animation-delay: .00s }
  .kpi-grid .kpi-card:nth-child(2) { animation-delay: .04s }
  .kpi-grid .kpi-card:nth-child(3) { animation-delay: .08s }
  .kpi-grid .kpi-card:nth-child(4) { animation-delay: .12s }
  .kpi-grid .kpi-card:nth-child(5) { animation-delay: .16s }
  .kpi-grid .kpi-card:nth-child(6) { animation-delay: .20s }
  .kpi-grid .kpi-card:nth-child(n+7) { animation-delay: .24s }

  .kpi-label {
    font-size: .705rem; font-weight: 500; text-transform: uppercase;
    letter-spacing: .055em; color: var(--g-text-3); margin-bottom: .3rem;
    line-height: 1.28; overflow-wrap: break-word;
  }
  .kpi-value {
    font-size: 1.62rem; font-weight: 500; line-height: 1.14;
    color: var(--accent, var(--g-text)); letter-spacing: -.02em;
    overflow-wrap: break-word;
  }
  .kpi-sub { font-size: .745rem; color: var(--g-text-3); margin-top: .25rem; line-height: 1.35; }
  .kpi-delta { font-size: .76rem; font-weight: 500; margin-top: .25rem; }
  .kpi-delta.up { color: var(--g-green); }
  .kpi-delta.down { color: var(--g-red); }
  .kpi-delta.flat { color: var(--g-text-3); }

  /* ---------- chips ---------- */
  .chip {
    display: inline-block; padding: .26rem .7rem; border-radius: 999px;
    font-size: .745rem; font-weight: 500; margin: .14rem .3rem .14rem 0;
    border: 1px solid transparent; white-space: nowrap;
    transition: transform .22s var(--g-ease);
  }
  .chip:hover { transform: translateY(-1px); }
  .chip-red   { background: var(--g-red-bg);   color: #B3261E; border-color: #F5C9C5; }
  .chip-amber { background: var(--g-amber-bg); color: #A65B00; border-color: #FBE3A6; }
  .chip-green { background: var(--g-green-bg); color: #14682D; border-color: #B7E1C3; }
  .chip-grey  { background: var(--g-grey-bg);  color: var(--g-text-2); border-color: var(--g-border); }

  /* ---------- callouts ---------- */
  .callout {
    border-radius: var(--g-r); padding: .95rem 1.1rem; margin: .45rem 0 1.15rem 0;
    font-size: .9rem; border: 1px solid var(--g-border-soft);
    background: var(--g-surface); box-shadow: var(--g-shadow);
    animation: gBlurInSoft .5s var(--g-ease) both; color: var(--g-text-2);
  }
  .callout strong { color: var(--g-text); font-weight: 500; }
  .callout.red   { background: var(--g-red-bg);   border-color: #F5C9C5; }
  .callout.amber { background: var(--g-amber-bg); border-color: #FBE3A6; }
  .callout.green { background: var(--g-green-bg); border-color: #B7E1C3; }
  .callout ul { margin: .35rem 0 0 1.15rem; padding: 0; }
  .callout li { margin: .22rem 0; line-height: 1.5; }

  .section-note { color: var(--g-text-3); font-size: .87rem; margin: -.3rem 0 .8rem 0; }
  .src-note { color: #97A1AE; font-size: .77rem; margin-top: .5rem; }

  /* ---------- tabs ---------- */
  [data-baseweb="tab-list"] {
    gap: .3rem; background: transparent; border-bottom: 1px solid var(--g-border-soft);
    padding-bottom: 0; margin-bottom: .3rem; overflow-x: auto;
  }
  [data-baseweb="tab"] {
    background: transparent !important; border-radius: 999px 999px 0 0;
    padding: .5rem .95rem !important; font-size: .9rem; font-weight: 500;
    color: var(--g-text-3); transition: color .26s var(--g-ease), background .26s var(--g-ease);
    white-space: nowrap;
  }
  [data-baseweb="tab"]:hover { color: var(--g-text); background: rgba(66,133,244,.06) !important; }
  [data-baseweb="tab"][aria-selected="true"] { color: var(--g-blue); }
  [data-baseweb="tab-highlight"] { background: var(--g-grad) !important; height: 3px; border-radius: 3px; }
  [data-baseweb="tab-border"] { display: none; }

  /* ---------- controls ---------- */
  .stButton > button, .stDownloadButton > button, .stLinkButton > a {
    border-radius: 999px !important; font-weight: 500; border: 1px solid var(--g-border);
    transition: transform .24s var(--g-ease), box-shadow .24s var(--g-ease),
                filter .24s var(--g-ease);
  }
  .stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {
    transform: translateY(-1px); box-shadow: var(--g-shadow);
  }
  .stButton > button[kind="primary"] {
    background: var(--g-grad) !important; border: none !important; color: #fff !important;
  }
  .stButton > button[kind="primary"]:hover { filter: brightness(1.06); }

  [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
  [data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
  .stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input {
    border-radius: 12px !important; background: var(--g-surface) !important;
    border-color: var(--g-border) !important;
  }

  [data-testid="stExpander"] {
    border: 1px solid var(--g-border-soft) !important; border-radius: var(--g-r) !important;
    background: var(--g-surface); box-shadow: var(--g-shadow); overflow: hidden;
  }
  [data-testid="stExpander"] summary:hover { background: var(--g-surface-2); }

  [data-testid="stDataFrame"], [data-testid="stTable"] {
    border-radius: var(--g-r); overflow: hidden; border: 1px solid var(--g-border-soft);
    box-shadow: var(--g-shadow); background: var(--g-surface);
  }
  [data-testid="stMetric"] {
    background: var(--g-surface); border: 1px solid var(--g-border-soft);
    border-radius: var(--g-r); padding: .75rem .9rem; box-shadow: var(--g-shadow);
  }
  [data-testid="stForm"] {
    border: 1px solid var(--g-border-soft) !important; border-radius: var(--g-r-lg) !important;
    background: var(--g-surface); box-shadow: var(--g-shadow); padding: 1.15rem !important;
  }

  /* ---------- sidebar ---------- */
  [data-testid="stSidebar"] { background: var(--g-surface); border-right: 1px solid var(--g-border-soft); }
  [data-testid="stSidebarNav"] a { border-radius: 999px !important; transition: background .24s var(--g-ease); }

  /* ---------- hero ---------- */
  .g-hero {
    background: var(--g-grad-soft); border: 1px solid var(--g-border-soft);
    border-radius: var(--g-r-lg); padding: 1.1rem 1.3rem; margin-bottom: 1.1rem;
    animation: gBlurIn .6s var(--g-ease) both;
  }
  .g-hero-title { font-size: 1.02rem; font-weight: 500; color: var(--g-text); margin-bottom: .2rem; }
  .g-hero-sub { font-size: .87rem; color: var(--g-text-2); line-height: 1.5; }

  /* ---------- reminder banner ---------- */
  .g-alert {
    display: flex; gap: .85rem; align-items: flex-start;
    background: var(--g-surface); border: 1px solid #FBE3A6; border-left: 4px solid var(--g-amber);
    border-radius: var(--g-r); padding: .9rem 1.05rem; margin: .4rem 0 .7rem 0;
    box-shadow: var(--g-shadow); animation: gBlurInSoft .5s var(--g-ease) both;
  }
  .g-alert.red { border-color: #F5C9C5; border-left-color: var(--g-red); }
  .g-alert-body { flex: 1; min-width: 0; }
  .g-alert-title { font-weight: 500; color: var(--g-text); font-size: .93rem; margin-bottom: .18rem; }
  .g-alert-text { font-size: .85rem; color: var(--g-text-2); line-height: 1.5; }
  .g-alert-meta { font-size: .77rem; color: var(--g-text-3); margin-top: .3rem; }

  /* ---------- phones ---------- */
  @media (max-width: 640px) {
    [data-testid="stMain"] .block-container {
      padding-left: .8rem; padding-right: .8rem; padding-top: 1rem;
    }
    .kpi-grid { grid-template-columns: repeat(auto-fit, minmax(136px, 1fr)); gap: .5rem; }
    .kpi-card { padding: .6rem .65rem; border-radius: 13px; }
    .kpi-value { font-size: 1.2rem; }
    .kpi-label { font-size: .655rem; }
    [data-testid="stMain"] h1 { font-size: 1.45rem !important; }
    [data-testid="stMain"] h3 { font-size: 1rem !important; }
    [data-baseweb="tab"] { padding: .45rem .7rem !important; font-size: .84rem; }
    .g-hero { padding: .9rem 1rem; border-radius: 18px; }
  }

  @media (prefers-reduced-motion: reduce) {
    *, [data-testid="stMain"] [data-testid="stElementContainer"],
    .kpi-card, .callout, .g-hero, .g-alert, [data-baseweb="tab-panel"] {
      animation: none !important; transition: none !important; filter: none !important;
    }
  }
</style>
"""
