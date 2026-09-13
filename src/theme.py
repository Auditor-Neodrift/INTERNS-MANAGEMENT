"""Flux-style dashboard theme.

Design notes:
  * Charcoal sidebar with pill navigation against a warm off-white canvas;
    content sits on solid white cards with 22px corners.
  * Accents are lime (#D9F154) for positive deltas and badges, soft violet
    (#B9A7F5) for secondary data, near-black for emphasis cards.
  * Numbers are the loudest thing on screen: large, tight, near-black, with
    the unit dropped to a small muted suffix beside them.
  * Content still arrives with the motion-blur reveal, staggered down the page.
    prefers-reduced-motion drops the blur and the lift.
"""
from __future__ import annotations

CSS = """
<style>
  :root {
    --flux-ink: #17171A;
    --flux-ink-2: #5A5A63;
    --flux-ink-3: #93939E;

    --flux-canvas: #F1F1EE;
    --flux-card: #FFFFFF;
    --flux-dark: #1B1B1E;
    --flux-line: #EAEAE5;
    --flux-line-2: #E3E3DD;

    --flux-lime: #D9F154;
    --flux-lime-deep: #C2DB33;
    --flux-lime-ink: #2E3606;
    --flux-violet: #B9A7F5;
    --flux-violet-soft: #E6E0FB;

    --flux-green: #2E9E5B;
    --flux-amber: #E08A17;
    --flux-red: #E0503C;
    --flux-green-bg: #E6F5EC;
    --flux-amber-bg: #FDF2E0;
    --flux-red-bg: #FCEAE7;
    --flux-grey-bg: #F1F1EE;

    --r: 22px;
    --r-lg: 28px;
    --r-sm: 14px;
    --shadow: 0 1px 2px rgba(23,23,26,.03), 0 6px 18px rgba(23,23,26,.05);
    --shadow-hi: 0 2px 6px rgba(23,23,26,.06), 0 14px 34px rgba(23,23,26,.09);
    --ease: cubic-bezier(.32, .72, 0, 1);
    --font: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  }

  /* ---------- canvas ---------- */
  .stApp { background: var(--flux-canvas); }
  .stApp, [data-testid="stMain"] { font-family: var(--font); }
  [data-testid="stMain"] .block-container {
    padding-top: 2.4rem; padding-bottom: 4rem; max-width: 1520px;
  }
  footer, #MainMenu { visibility: hidden; }

  h1, h2, h3, h4 { color: var(--flux-ink); letter-spacing: -.032em; font-weight: 600; }
  [data-testid="stMain"] h1 { font-size: 2.55rem; line-height: 1.06; margin-bottom: .15rem; }
  [data-testid="stMain"] h3 { font-size: 1.1rem; margin-top: 1.9rem; letter-spacing: -.022em; }
  [data-testid="stMain"] p, [data-testid="stMain"] li,
  [data-testid="stMain"] label { color: var(--flux-ink-2); }

  /* ---------- dark sidebar ---------- */
  [data-testid="stSidebar"] {
    background: var(--flux-dark);
    border-right: none;
    border-radius: 0 26px 26px 0;
  }
  [data-testid="stSidebar"] * { color: #E8E8E4; }
  [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h2 {
    color: #FFFFFF; font-size: 1.05rem; letter-spacing: -.02em;
  }
  [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
  [data-testid="stSidebar"] small { color: #8B8B93 !important; }
  [data-testid="stSidebarNav"] { padding-top: .3rem; }
  [data-testid="stSidebarNav"] a {
    border-radius: 999px !important; margin: .16rem .35rem;
    padding: .52rem .85rem !important;
    transition: background .3s var(--ease), color .3s var(--ease);
  }
  [data-testid="stSidebarNav"] a span { color: #C9C9CF !important; font-weight: 500; }
  [data-testid="stSidebarNav"] a:hover { background: rgba(255,255,255,.08) !important; }
  [data-testid="stSidebarNav"] a[aria-current="page"] {
    background: #FFFFFF !important;
  }
  [data-testid="stSidebarNav"] a[aria-current="page"] span,
  [data-testid="stSidebarNav"] a[aria-current="page"] * { color: var(--flux-ink) !important; font-weight: 600; }
  [data-testid="stSidebar"] .stButton > button,
  [data-testid="stSidebar"] .stLinkButton > a {
    background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.14);
    color: #E8E8E4 !important;
  }
  [data-testid="stSidebar"] .stButton > button:hover { background: rgba(255,255,255,.14); }
  [data-testid="stSidebar"] [data-testid="stMetricValue"] { color: #FFFFFF; }
  [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.1); }

  /* ---------- motion blur ---------- */
  @keyframes fluxIn {
    0%   { opacity: 0; transform: translateY(16px) scale(.99); filter: blur(12px); }
    58%  { opacity: 1; }
    100% { opacity: 1; transform: none; filter: blur(0); }
  }
  @keyframes fluxInSoft {
    0%   { opacity: 0; transform: translateY(8px); filter: blur(7px); }
    100% { opacity: 1; transform: none; filter: blur(0); }
  }
  [data-testid="stMain"] [data-testid="stElementContainer"],
  [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
    animation: fluxIn .55s var(--ease) both;
  }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(1) { animation-delay: .00s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(2) { animation-delay: .035s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(3) { animation-delay: .07s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(4) { animation-delay: .105s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(5) { animation-delay: .14s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(6) { animation-delay: .175s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(n+7) { animation-delay: .21s }
  [data-baseweb="tab-panel"] { animation: fluxInSoft .42s var(--ease) both; }

  /* ---------- top bar ---------- */
  .flux-top {
    display: flex; align-items: center; gap: .8rem; flex-wrap: wrap;
    margin: .1rem 0 1.1rem 0;
  }
  .flux-user { display: flex; align-items: center; gap: .65rem; }
  .flux-avatar {
    width: 44px; height: 44px; border-radius: 50%; flex: 0 0 44px;
    background: linear-gradient(140deg, var(--flux-violet), var(--flux-lime));
    display: flex; align-items: center; justify-content: center;
    color: var(--flux-ink); font-weight: 700; font-size: .92rem;
    letter-spacing: -.02em; border: 2px solid #FFFFFF;
    box-shadow: var(--shadow);
  }
  .flux-user-name { font-size: .93rem; font-weight: 600; color: var(--flux-ink); line-height: 1.25; }
  .flux-user-mail { font-size: .78rem; color: var(--flux-ink-3); line-height: 1.25; }
  .flux-spacer { flex: 1 1 auto; }
  .flux-datepill {
    display: inline-flex; align-items: center; gap: .5rem;
    background: var(--flux-card); border: 1px solid var(--flux-line-2);
    border-radius: 999px; padding: .5rem 1rem; box-shadow: var(--shadow);
    font-size: .84rem; color: var(--flux-ink-2); font-weight: 500;
  }
  .flux-datepill b { color: var(--flux-ink); font-weight: 600; }

  /* ---------- hero ---------- */
  .g-hero {
    background: var(--flux-card); border: 1px solid var(--flux-line);
    border-radius: var(--r-lg); padding: 1.15rem 1.35rem; margin-bottom: 1.1rem;
    box-shadow: var(--shadow); animation: fluxIn .6s var(--ease) both;
  }
  .g-hero-title { font-size: 1.04rem; font-weight: 600; color: var(--flux-ink); margin-bottom: .22rem; }
  .g-hero-sub { font-size: .875rem; color: var(--flux-ink-2); line-height: 1.55; }

  /* ---------- KPI cards ---------- */
  .kpi-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(196px, 1fr));
    gap: .8rem; margin: .55rem 0 1.25rem 0;
  }
  .kpi-card {
    position: relative; background: var(--flux-card);
    border: 1px solid var(--flux-line); border-radius: var(--r);
    padding: 1.05rem 1.15rem 1rem; min-width: 0; box-shadow: var(--shadow);
    transition: transform .38s var(--ease), box-shadow .38s var(--ease);
    animation: fluxInSoft .5s var(--ease) both;
  }
  .kpi-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-hi); }
  .kpi-grid .kpi-card:nth-child(1) { animation-delay: .00s }
  .kpi-grid .kpi-card:nth-child(2) { animation-delay: .045s }
  .kpi-grid .kpi-card:nth-child(3) { animation-delay: .09s }
  .kpi-grid .kpi-card:nth-child(4) { animation-delay: .135s }
  .kpi-grid .kpi-card:nth-child(5) { animation-delay: .18s }
  .kpi-grid .kpi-card:nth-child(6) { animation-delay: .225s }
  .kpi-grid .kpi-card:nth-child(n+7) { animation-delay: .27s }

  .kpi-head { display: flex; align-items: center; gap: .55rem; margin-bottom: .95rem; }
  .kpi-dot {
    width: 30px; height: 30px; border-radius: 50%; flex: 0 0 30px;
    background: var(--flux-grey-bg); display: flex; align-items: center;
    justify-content: center; font-size: .82rem; line-height: 1;
    border: 1px solid var(--flux-line-2);
  }
  .kpi-label {
    font-size: .845rem; font-weight: 500; color: var(--flux-ink-2);
    line-height: 1.3; overflow-wrap: break-word; letter-spacing: -.005em;
  }
  .kpi-value {
    font-size: 2.05rem; font-weight: 600; line-height: 1.05;
    color: var(--flux-ink); letter-spacing: -.045em;
    overflow-wrap: break-word; display: flex; align-items: baseline;
    gap: .42rem; flex-wrap: wrap;
  }
  .kpi-unit { font-size: .82rem; font-weight: 500; color: var(--flux-ink-3); letter-spacing: 0; }
  .kpi-badge {
    display: inline-block; font-size: .715rem; font-weight: 600;
    padding: .18rem .5rem; border-radius: 999px; letter-spacing: -.01em;
    background: var(--flux-lime); color: var(--flux-lime-ink);
  }
  .kpi-badge.down { background: var(--flux-red-bg); color: #A6301F; }
  .kpi-badge.flat { background: var(--flux-grey-bg); color: var(--flux-ink-2); }
  .kpi-sub { font-size: .775rem; color: var(--flux-ink-3); margin-top: .4rem; line-height: 1.4; }
  .kpi-card.is-red   { background: var(--flux-red-bg);   border-color: #F6D5CF; }
  .kpi-card.is-amber { background: var(--flux-amber-bg); border-color: #F7E2BE; }
  .kpi-card.is-green { background: var(--flux-green-bg); border-color: #CCE9D8; }

  /* ---------- chips ---------- */
  .chip {
    display: inline-block; padding: .3rem .8rem; border-radius: 999px;
    font-size: .765rem; font-weight: 500; margin: .16rem .34rem .16rem 0;
    border: 1px solid transparent; white-space: nowrap;
    transition: transform .28s var(--ease);
  }
  .chip:hover { transform: translateY(-1px); }
  .chip-red   { background: var(--flux-red-bg);   color: #A6301F; border-color: #F6D5CF; }
  .chip-amber { background: var(--flux-amber-bg); color: #96590A; border-color: #F7E2BE; }
  .chip-green { background: var(--flux-green-bg); color: #1F7343; border-color: #CCE9D8; }
  .chip-grey  { background: var(--flux-card);     color: var(--flux-ink-2); border-color: var(--flux-line-2); }

  /* ---------- callouts ---------- */
  .callout {
    border-radius: var(--r); padding: 1.05rem 1.2rem; margin: .5rem 0 1.2rem 0;
    font-size: .895rem; color: var(--flux-ink-2);
    background: var(--flux-card); border: 1px solid var(--flux-line);
    box-shadow: var(--shadow); animation: fluxInSoft .5s var(--ease) both;
  }
  .callout strong { color: var(--flux-ink); font-weight: 600; }
  .callout.red   { background: var(--flux-red-bg);   border-color: #F6D5CF; }
  .callout.amber { background: var(--flux-amber-bg); border-color: #F7E2BE; }
  .callout.green { background: var(--flux-green-bg); border-color: #CCE9D8; }
  .callout ul { margin: .4rem 0 0 1.15rem; padding: 0; }
  .callout li { margin: .24rem 0; line-height: 1.55; }

  .section-note { color: var(--flux-ink-3); font-size: .865rem; margin: -.3rem 0 .8rem 0; }
  .src-note { color: #A4A4AE; font-size: .775rem; margin-top: .5rem; }

  /* ---------- alert ---------- */
  .g-alert {
    display: flex; gap: .9rem; align-items: flex-start;
    border-radius: var(--r); padding: 1rem 1.15rem; margin: .45rem 0 .7rem 0;
    border: 1px solid #F7E2BE; border-left: 4px solid var(--flux-amber);
    background: var(--flux-amber-bg);
    animation: fluxInSoft .5s var(--ease) both;
  }
  .g-alert.red { border-color: #F6D5CF; border-left-color: var(--flux-red); background: var(--flux-red-bg); }
  .g-alert-body { flex: 1; min-width: 0; }
  .g-alert-title { font-weight: 600; color: var(--flux-ink); font-size: .93rem; margin-bottom: .2rem; }
  .g-alert-text { font-size: .855rem; color: var(--flux-ink-2); line-height: 1.55; }
  .g-alert-meta { font-size: .775rem; color: var(--flux-ink-3); margin-top: .32rem; }

  /* ---------- tabs ---------- */
  [data-baseweb="tab-list"] {
    gap: .2rem; border-bottom: none; padding: .28rem;
    margin-bottom: .65rem; overflow-x: auto; border-radius: 999px;
    background: var(--flux-card); border: 1px solid var(--flux-line);
    width: fit-content; max-width: 100%; box-shadow: var(--shadow);
  }
  [data-baseweb="tab"] {
    background: transparent !important; border-radius: 999px !important;
    padding: .44rem 1.05rem !important; font-size: .865rem; font-weight: 500;
    color: var(--flux-ink-2); white-space: nowrap;
    transition: background .32s var(--ease), color .32s var(--ease);
  }
  [data-baseweb="tab"]:hover { color: var(--flux-ink); background: var(--flux-canvas) !important; }
  [data-baseweb="tab"][aria-selected="true"] {
    color: #FFFFFF; background: var(--flux-dark) !important; font-weight: 600;
  }
  [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none; }

  /* ---------- controls ---------- */
  .stButton > button, .stDownloadButton > button, .stLinkButton > a {
    border-radius: 999px !important; font-weight: 500;
    border: 1px solid var(--flux-line-2); background: var(--flux-card);
    transition: transform .28s var(--ease), box-shadow .28s var(--ease),
                filter .28s var(--ease);
  }
  .stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {
    transform: translateY(-1px); box-shadow: var(--shadow);
  }
  .stButton > button:active { transform: scale(.978); }
  [data-testid="stMain"] .stButton > button[kind="primary"] {
    background: var(--flux-dark) !important; border: none !important;
    color: #FFFFFF !important;
  }
  [data-testid="stMain"] .stButton > button[kind="primary"]:hover { filter: brightness(1.25); }

  [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
  [data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
  .stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input {
    border-radius: var(--r-sm) !important; background: var(--flux-card) !important;
    border-color: var(--flux-line-2) !important;
  }

  [data-testid="stExpander"] {
    border: 1px solid var(--flux-line) !important; border-radius: var(--r) !important;
    background: var(--flux-card); box-shadow: var(--shadow); overflow: hidden;
  }
  [data-testid="stExpander"] summary:hover { background: var(--flux-canvas); }
  [data-testid="stDataFrame"], [data-testid="stTable"] {
    border-radius: var(--r); overflow: hidden; border: 1px solid var(--flux-line);
    box-shadow: var(--shadow); background: var(--flux-card);
  }
  [data-testid="stMetric"] {
    background: var(--flux-card); border: 1px solid var(--flux-line);
    border-radius: var(--r); padding: .85rem 1rem; box-shadow: var(--shadow);
  }
  [data-testid="stForm"] {
    border: 1px solid var(--flux-line) !important; border-radius: var(--r-lg) !important;
    background: var(--flux-card); box-shadow: var(--shadow); padding: 1.2rem !important;
  }

  /* ---------- version picker ---------- */
  .flux-ver-note {
    display: inline-block; font-size: .735rem; color: var(--flux-ink-3);
    margin-top: .1rem;
  }
  .flux-ver-pill {
    display: inline-block; font-size: .68rem; font-weight: 600;
    padding: .14rem .48rem; border-radius: 999px; margin-left: .3rem;
    background: var(--flux-lime); color: var(--flux-lime-ink);
  }


  /* ---------- alert grid: three across ---------- */
  .alert-grid {
    display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: .7rem; margin: .4rem 0 1rem 0;
  }
  .alert-mini {
    background: var(--flux-card); border: 1px solid var(--flux-line);
    border-left: 4px solid var(--flux-amber); border-radius: var(--r-sm);
    padding: .8rem .9rem; min-width: 0; box-shadow: var(--shadow);
    animation: fluxInSoft .48s var(--ease) both;
    transition: transform .3s var(--ease), box-shadow .3s var(--ease);
  }
  .alert-mini:hover { transform: translateY(-2px); box-shadow: var(--shadow-hi); }
  .alert-mini.red { border-left-color: var(--flux-red); background: var(--flux-red-bg); border-color: #F6D5CF; }
  .alert-mini.amber { border-left-color: var(--flux-amber); background: var(--flux-amber-bg); border-color: #F7E2BE; }
  .alert-mini-name { font-size: .875rem; font-weight: 600; color: var(--flux-ink); margin-bottom: .2rem; }
  .alert-mini-msg { font-size: .795rem; color: var(--flux-ink-2); line-height: 1.45; }
  .alert-mini-meta { font-size: .715rem; color: var(--flux-ink-3); margin-top: .32rem; line-height: 1.4; }
  .alert-grid .alert-mini:nth-child(1) { animation-delay: .00s }
  .alert-grid .alert-mini:nth-child(2) { animation-delay: .04s }
  .alert-grid .alert-mini:nth-child(3) { animation-delay: .08s }
  .alert-grid .alert-mini:nth-child(n+4) { animation-delay: .12s }
  @media (max-width: 1100px) { .alert-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  @media (max-width: 700px)  { .alert-grid { grid-template-columns: 1fr; } }

  /* A filtered or transformed ancestor becomes the containing block for
     position:fixed, which would anchor the toast stack to its wrapper instead
     of the viewport. Neutralise the reveal on whichever container holds it. */
  [data-testid="stElementContainer"]:has(.toast-stack),
  [data-testid="stVerticalBlockBorderWrapper"]:has(.toast-stack),
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .toast-stack) {
    animation: none !important; filter: none !important; transform: none !important;
  }

  /* ---------- bottom-right notification stack ---------- */
  .toast-stack {
    position: fixed; right: 18px; bottom: 18px; z-index: 9990;
    display: flex; flex-direction: column; gap: .45rem;
    width: 296px; max-width: calc(100vw - 36px); pointer-events: none;
  }
  .toast-stack > * { pointer-events: auto; }
  .toast-head {
    align-self: flex-end; font-size: .68rem; font-weight: 600;
    letter-spacing: .05em; text-transform: uppercase; color: var(--flux-ink-3);
    background: var(--flux-card); border: 1px solid var(--flux-line);
    border-radius: 999px; padding: .2rem .6rem; box-shadow: var(--shadow);
  }
  .toast-x { display: none; }
  .toast {
    display: flex; gap: .55rem; align-items: flex-start;
    background: var(--flux-card); border: 1px solid var(--flux-line);
    border-left: 3px solid var(--flux-red); border-radius: var(--r-sm);
    padding: .6rem .7rem; box-shadow: var(--shadow-hi);
    animation: toastIn .5s var(--ease) both;
  }
  .toast.amber { border-left-color: var(--flux-amber); }
  .toast-x:checked + .toast { display: none; }
  .toast-body { flex: 1; min-width: 0; }
  .toast-title {
    font-size: .775rem; font-weight: 600; color: var(--flux-ink);
    line-height: 1.3; margin-bottom: .1rem;
  }
  .toast-text {
    font-size: .715rem; color: var(--flux-ink-2); line-height: 1.4;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .toast-close {
    cursor: pointer; color: var(--flux-ink-3); font-size: .95rem;
    line-height: 1; padding: 0 .1rem; flex: 0 0 auto; user-select: none;
    transition: color .2s var(--ease);
  }
  .toast-close:hover { color: var(--flux-ink); }
  @keyframes toastIn {
    0%   { opacity: 0; transform: translateX(26px) scale(.96); filter: blur(8px); }
    100% { opacity: 1; transform: none; filter: blur(0); }
  }
  .toast-stack .toast:nth-of-type(1) { animation-delay: .05s }
  .toast-stack .toast:nth-of-type(2) { animation-delay: .13s }
  .toast-stack .toast:nth-of-type(3) { animation-delay: .21s }
  @media (max-width: 640px) {
    .toast-stack { width: calc(100vw - 24px); right: 12px; bottom: 12px; gap: .35rem; }
    .toast-text { -webkit-line-clamp: 1; }
  }

  /* ---------- version toggle: plain text + chevron, no pill ---------- */
  .flux-verbar { height: .35rem; }
  [data-testid="stPopoverButton"] {
    background: transparent !important; border: none !important;
    box-shadow: none !important; border-radius: 10px !important;
    padding: .24rem .45rem .24rem .3rem !important;
    font-size: 1.16rem !important; font-weight: 600 !important;
    letter-spacing: -.028em; color: var(--flux-ink) !important;
    transition: background .25s var(--ease), opacity .25s var(--ease);
    background-color: transparent !important;
  }
  [data-testid="stPopoverButton"]:hover {
    background: rgba(23,23,26,.055) !important; color: var(--flux-ink) !important;
  }
  [data-testid="stPopoverButton"]:focus,
  [data-testid="stPopoverButton"]:active {
    box-shadow: none !important; border: none !important;
  }

  /* Menu rows: plain left-aligned text, no pill, with the Latest tag styled
     from the trailing word so the label stays a single button string. */
  [data-testid="stPopoverBody"] .stButton > button,
  [data-testid="stPopoverBody"] button[data-testid^="stBaseButton"] {
    background: transparent !important; border: none !important;
    box-shadow: none !important; border-radius: 9px !important;
    justify-content: flex-start !important; text-align: left !important;
    padding: .42rem .6rem !important; margin: 0 !important;
    font-size: .93rem !important; font-weight: 500 !important;
    color: var(--flux-ink) !important; min-height: 0 !important;
  }
  [data-testid="stPopoverBody"] .stButton > button:hover {
    background: rgba(23,23,26,.06) !important;
  }
  [data-testid="stPopoverBody"] .stButton > button p {
    font-size: .93rem !important; font-weight: 500 !important;
    white-space: pre !important; color: var(--flux-ink) !important;
  }
  /* Streamlit centres the label in a nested flex wrapper inside the button,
     which overrides the button's own alignment - so unset it there too. */
  [data-testid="stPopoverBody"] .stButton > button > div,
  [data-testid="stPopoverBody"] .stButton > button > div > span {
    justify-content: flex-start !important; width: 100% !important;
  }
  [data-testid="stPopoverBody"] [data-testid="stVerticalBlock"] { gap: .1rem !important; }
  [data-testid="stPopoverBody"] { padding: .45rem !important; min-width: 190px; }

  /* The popover panel renders in a portal outside stMain, so primary buttons
     there miss the stMain rule and fall back to white-on-white. */
  button[data-testid="stBaseButton-primary"] {
    background: var(--flux-dark) !important; color: #FFFFFF !important;
    border: none !important;
  }
  [data-baseweb="popover"] button { font-size: .875rem !important; font-weight: 500 !important; }
  [data-baseweb="popover"] [data-testid="stButton"] button {
    justify-content: flex-start !important; text-align: left !important;
  }
  .ver-check { font-size: 1.05rem; color: var(--flux-ink); text-align: center; line-height: 1; }

  /* ---------- segmented sub-nav ---------- */
  [data-testid="stSegmentedControl"] button {
    border-radius: 999px !important; font-weight: 500; font-size: .85rem;
    border-color: var(--flux-line-2) !important;
  }
  [data-testid="stSegmentedControl"] button[aria-checked="true"],
  [data-testid="stSegmentedControl"] button[aria-pressed="true"] {
    background: var(--flux-dark) !important; color: #FFFFFF !important;
    border-color: var(--flux-dark) !important;
  }

  /* ---------- centred sign-in ---------- */
  .signin-wrap {
    display: flex; align-items: center; justify-content: center;
    min-height: 62vh; padding: 1rem 0;
  }
  .signin-card {
    width: 100%; max-width: 430px; text-align: center;
    border-radius: var(--r-lg); padding: 2.4rem 2rem 1.9rem;
    background: var(--flux-card); border: 1px solid var(--flux-line);
    box-shadow: var(--shadow-hi); animation: fluxIn .65s var(--ease) both;
  }
  .signin-mark {
    width: 62px; height: 62px; margin: 0 auto 1.15rem; border-radius: 19px;
    background: linear-gradient(140deg, var(--flux-violet), var(--flux-lime));
    display: flex; align-items: center; justify-content: center;
    color: var(--flux-ink); font-size: 1.45rem; font-weight: 700; letter-spacing: -.035em;
    box-shadow: var(--shadow);
  }
  .signin-title { font-size: 1.45rem; font-weight: 600; color: var(--flux-ink);
                  letter-spacing: -.032em; margin-bottom: .45rem; }
  .signin-sub { font-size: .9rem; color: var(--flux-ink-2); line-height: 1.6;
                margin: 0 auto 1.4rem; max-width: 330px; }
  .signin-foot { font-size: .775rem; color: var(--flux-ink-3); margin-top: 1.15rem;
                 padding-top: 1rem; border-top: 1px solid var(--flux-line); }

  /* ---------- phones ---------- */
  @media (max-width: 640px) {
    [data-testid="stMain"] .block-container {
      padding-left: .75rem; padding-right: .75rem; padding-top: 2rem;
    }
    .kpi-grid { grid-template-columns: repeat(auto-fit, minmax(146px, 1fr)); gap: .55rem; }
    .kpi-card { padding: .8rem .85rem; border-radius: 17px; }
    .kpi-value { font-size: 1.5rem; }
    .kpi-head { margin-bottom: .65rem; }
    .kpi-dot { width: 26px; height: 26px; flex: 0 0 26px; font-size: .72rem; }
    .kpi-label { font-size: .765rem; }
    [data-testid="stMain"] h1 { font-size: 1.72rem !important; }
    [data-testid="stMain"] h3 { font-size: 1rem !important; }
    [data-baseweb="tab"] { padding: .4rem .8rem !important; font-size: .82rem; }
    .g-hero { padding: .95rem 1.05rem; border-radius: 20px; }
    .flux-avatar { width: 38px; height: 38px; flex: 0 0 38px; font-size: .82rem; }
    .signin-card { padding: 1.9rem 1.3rem 1.6rem; border-radius: 24px; }
  }

  @media (prefers-reduced-motion: reduce) {
    *, [data-testid="stMain"] [data-testid="stElementContainer"],
    .kpi-card, .callout, .g-hero, .g-alert, .signin-card,
    [data-baseweb="tab-panel"] {
      animation: none !important; transition: none !important; filter: none !important;
    }
  }
</style>
"""
