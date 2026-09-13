"""iOS-style glass theme.

Design notes:
  * A soft tinted wallpaper sits behind everything so frosted panels have
    something to refract; every surface is translucent white over it, with
    backdrop-filter blur + saturate doing the glass.
  * Corners are iOS-large (18-28px), controls are full pills, and the palette
    is the system one: blue #0A84FF, green #34C759, orange #FF9F0A, red #FF3B30.
  * Type is the SF stack, falling back to the system UI font elsewhere.
  * Content arrives with a motion-blur reveal (blur + lift + fade), staggered
    down the page. prefers-reduced-motion drops the blur and lift entirely.
  * backdrop-filter is progressively enhanced: without it the panels stay
    readable, just more opaque.
"""
from __future__ import annotations

CSS = """
<style>
  :root {
    --ios-blue: #0A84FF;
    --ios-indigo: #5E5CE6;
    --ios-purple: #BF5AF2;
    --ios-pink: #FF375F;
    --ios-green: #34C759;
    --ios-orange: #FF9F0A;
    --ios-red: #FF3B30;

    --glass: rgba(255, 255, 255, .62);
    --glass-strong: rgba(255, 255, 255, .78);
    --glass-soft: rgba(255, 255, 255, .45);
    --glass-line: rgba(255, 255, 255, .72);
    --glass-edge: rgba(120, 135, 165, .20);
    --blur: saturate(180%) blur(22px);

    --ink: #1C1C1E;
    --ink-2: #3A3A3C;
    --ink-3: #6E6E73;

    --tint-green: rgba(52, 199, 89, .16);
    --tint-orange: rgba(255, 159, 10, .18);
    --tint-red: rgba(255, 59, 48, .15);
    --tint-grey: rgba(120, 135, 165, .13);

    --r: 20px;
    --r-lg: 28px;
    --shadow: 0 1px 1px rgba(28,28,30,.04), 0 8px 24px rgba(28,28,30,.07);
    --shadow-hi: 0 2px 4px rgba(28,28,30,.06), 0 16px 40px rgba(28,28,30,.11);
    --ease: cubic-bezier(.32, .72, 0, 1);

    --font: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display",
            "Segoe UI Variable", "Segoe UI", Inter, system-ui, sans-serif;
  }

  /* ---------- wallpaper ---------- */
  .stApp {
    background:
      radial-gradient(1100px 620px at 8% -8%,  rgba(10,132,255,.20), transparent 60%),
      radial-gradient(900px 560px at 96% 4%,   rgba(191,90,242,.17), transparent 62%),
      radial-gradient(1000px 680px at 48% 108%, rgba(255,55,95,.13), transparent 60%),
      linear-gradient(168deg, #F7F8FC 0%, #EEF1F8 52%, #F4F1F8 100%);
    background-attachment: fixed;
  }
  .stApp, [data-testid="stMain"] { font-family: var(--font); }

  [data-testid="stMain"] .block-container {
    padding-top: 1.5rem; padding-bottom: 4rem; max-width: 1480px;
  }
  footer, #MainMenu { visibility: hidden; }

  h1, h2, h3, h4 { color: var(--ink); letter-spacing: -.022em; font-weight: 600; }
  [data-testid="stMain"] h1 { font-size: 2.1rem; line-height: 1.14; margin-bottom: .2rem; }
  [data-testid="stMain"] h3 { font-size: 1.14rem; margin-top: 1.8rem; }
  [data-testid="stMain"] p, [data-testid="stMain"] li,
  [data-testid="stMain"] label { color: var(--ink-2); }

  /* ---------- motion blur ---------- */
  @keyframes glassIn {
    0%   { opacity: 0; transform: translateY(18px) scale(.988); filter: blur(14px); }
    58%  { opacity: 1; }
    100% { opacity: 1; transform: none; filter: blur(0); }
  }
  @keyframes glassInSoft {
    0%   { opacity: 0; transform: translateY(9px); filter: blur(8px); }
    100% { opacity: 1; transform: none; filter: blur(0); }
  }
  [data-testid="stMain"] [data-testid="stElementContainer"],
  [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
    animation: glassIn .58s var(--ease) both;
  }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(1) { animation-delay: .00s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(2) { animation-delay: .035s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(3) { animation-delay: .07s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(4) { animation-delay: .105s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(5) { animation-delay: .14s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(6) { animation-delay: .175s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(7) { animation-delay: .21s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(n+8) { animation-delay: .245s }
  [data-baseweb="tab-panel"] { animation: glassInSoft .44s var(--ease) both; }

  /* ---------- glass surfaces ---------- */
  .kpi-card, .callout, .g-hero, .g-alert,
  [data-testid="stExpander"], [data-testid="stDataFrame"],
  [data-testid="stTable"], [data-testid="stMetric"], [data-testid="stForm"] {
    background: var(--glass);
    -webkit-backdrop-filter: var(--blur); backdrop-filter: var(--blur);
    border: 1px solid var(--glass-edge);
    box-shadow: var(--shadow), inset 0 1px 0 var(--glass-line);
  }
  @supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
    .kpi-card, .callout, .g-hero, .g-alert,
    [data-testid="stExpander"], [data-testid="stDataFrame"],
    [data-testid="stTable"], [data-testid="stMetric"], [data-testid="stForm"] {
      background: rgba(255, 255, 255, .93);
    }
  }

  /* ---------- KPI cards ---------- */
  .kpi-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(178px, 1fr));
    gap: .72rem; margin: .55rem 0 1.2rem 0;
  }
  .kpi-card {
    position: relative; overflow: hidden; border-radius: var(--r);
    padding: .9rem 1rem .85rem; min-width: 0;
    transition: transform .4s var(--ease), box-shadow .4s var(--ease);
    animation: glassInSoft .52s var(--ease) both;
  }
  .kpi-card::before {
    content: ""; position: absolute; inset: 0 0 auto 0; height: 3px;
    background: var(--accent, var(--ios-blue)); opacity: .95;
  }
  .kpi-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-hi), inset 0 1px 0 var(--glass-line); }
  .kpi-grid .kpi-card:nth-child(1) { animation-delay: .00s }
  .kpi-grid .kpi-card:nth-child(2) { animation-delay: .045s }
  .kpi-grid .kpi-card:nth-child(3) { animation-delay: .09s }
  .kpi-grid .kpi-card:nth-child(4) { animation-delay: .135s }
  .kpi-grid .kpi-card:nth-child(5) { animation-delay: .18s }
  .kpi-grid .kpi-card:nth-child(6) { animation-delay: .225s }
  .kpi-grid .kpi-card:nth-child(n+7) { animation-delay: .27s }

  .kpi-label {
    font-size: .695rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: .06em; color: var(--ink-3); margin-bottom: .3rem;
    line-height: 1.3; overflow-wrap: break-word;
  }
  .kpi-value {
    font-size: 1.68rem; font-weight: 600; line-height: 1.12;
    color: var(--accent, var(--ink)); letter-spacing: -.028em;
    overflow-wrap: break-word;
  }
  .kpi-sub { font-size: .745rem; color: var(--ink-3); margin-top: .26rem; line-height: 1.35; }
  .kpi-delta { font-size: .765rem; font-weight: 600; margin-top: .26rem; }
  .kpi-delta.up { color: var(--ios-green); }
  .kpi-delta.down { color: var(--ios-red); }
  .kpi-delta.flat { color: var(--ink-3); }

  /* ---------- chips ---------- */
  .chip {
    display: inline-block; padding: .28rem .75rem; border-radius: 999px;
    font-size: .75rem; font-weight: 600; margin: .15rem .32rem .15rem 0;
    border: 1px solid var(--glass-edge); white-space: nowrap;
    -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px);
    transition: transform .3s var(--ease);
  }
  .chip:hover { transform: translateY(-1px) scale(1.02); }
  .chip-red   { background: var(--tint-red);    color: #B3261E; }
  .chip-amber { background: var(--tint-orange); color: #9A5B00; }
  .chip-green { background: var(--tint-green);  color: #1B7A38; }
  .chip-grey  { background: var(--tint-grey);   color: var(--ink-2); }

  /* ---------- callouts ---------- */
  .callout {
    border-radius: var(--r); padding: 1rem 1.15rem; margin: .5rem 0 1.2rem 0;
    font-size: .9rem; color: var(--ink-2);
    animation: glassInSoft .52s var(--ease) both;
  }
  .callout strong { color: var(--ink); font-weight: 600; }
  .callout.red   { background: var(--tint-red); }
  .callout.amber { background: var(--tint-orange); }
  .callout.green { background: var(--tint-green); }
  .callout ul { margin: .4rem 0 0 1.15rem; padding: 0; }
  .callout li { margin: .24rem 0; line-height: 1.55; }

  .section-note { color: var(--ink-3); font-size: .875rem; margin: -.3rem 0 .8rem 0; }
  .src-note { color: #98A0AE; font-size: .775rem; margin-top: .5rem; }

  /* ---------- hero ---------- */
  .g-hero {
    border-radius: var(--r-lg); padding: 1.2rem 1.4rem; margin-bottom: 1.15rem;
    background: linear-gradient(125deg, rgba(10,132,255,.13), rgba(191,90,242,.12) 55%, rgba(255,55,95,.10));
    animation: glassIn .62s var(--ease) both;
  }
  .g-hero-title { font-size: 1.06rem; font-weight: 600; color: var(--ink); margin-bottom: .22rem; }
  .g-hero-sub { font-size: .88rem; color: var(--ink-2); line-height: 1.55; }

  /* ---------- alert ---------- */
  .g-alert {
    display: flex; gap: .9rem; align-items: flex-start;
    border-radius: var(--r); padding: .95rem 1.1rem; margin: .45rem 0 .7rem 0;
    border-left: 4px solid var(--ios-orange); background: var(--tint-orange);
    animation: glassInSoft .52s var(--ease) both;
  }
  .g-alert.red { border-left-color: var(--ios-red); background: var(--tint-red); }
  .g-alert-body { flex: 1; min-width: 0; }
  .g-alert-title { font-weight: 600; color: var(--ink); font-size: .94rem; margin-bottom: .2rem; }
  .g-alert-text { font-size: .86rem; color: var(--ink-2); line-height: 1.55; }
  .g-alert-meta { font-size: .775rem; color: var(--ink-3); margin-top: .32rem; }

  /* ---------- tabs as a segmented control ---------- */
  [data-baseweb="tab-list"] {
    gap: .18rem; border-bottom: none; padding: .26rem;
    margin-bottom: .6rem; overflow-x: auto; border-radius: 999px;
    background: var(--glass-soft);
    -webkit-backdrop-filter: var(--blur); backdrop-filter: var(--blur);
    border: 1px solid var(--glass-edge);
    box-shadow: inset 0 1px 0 var(--glass-line);
    width: fit-content; max-width: 100%;
  }
  [data-baseweb="tab"] {
    background: transparent !important; border-radius: 999px !important;
    padding: .42rem 1rem !important; font-size: .875rem; font-weight: 600;
    color: var(--ink-3); white-space: nowrap;
    transition: background .34s var(--ease), color .34s var(--ease);
  }
  [data-baseweb="tab"]:hover { color: var(--ink); }
  [data-baseweb="tab"][aria-selected="true"] {
    color: var(--ink); background: var(--glass-strong) !important;
    box-shadow: 0 1px 3px rgba(28,28,30,.10);
  }
  [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none; }

  /* ---------- controls ---------- */
  .stButton > button, .stDownloadButton > button, .stLinkButton > a {
    border-radius: 999px !important; font-weight: 600;
    border: 1px solid var(--glass-edge);
    background: var(--glass-strong);
    -webkit-backdrop-filter: blur(14px); backdrop-filter: blur(14px);
    transition: transform .3s var(--ease), box-shadow .3s var(--ease),
                filter .3s var(--ease);
  }
  .stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {
    transform: translateY(-1px); box-shadow: var(--shadow);
  }
  .stButton > button:active { transform: scale(.975); }
  .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--ios-blue), var(--ios-indigo)) !important;
    border: none !important; color: #fff !important;
    box-shadow: 0 4px 14px rgba(10,132,255,.32);
  }
  .stButton > button[kind="primary"]:hover { filter: brightness(1.07); }

  [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
  [data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
  .stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input {
    border-radius: 14px !important;
    background: var(--glass-strong) !important;
    border-color: var(--glass-edge) !important;
    -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px);
  }

  [data-testid="stExpander"] { border-radius: var(--r) !important; overflow: hidden; }
  [data-testid="stExpander"] summary:hover { background: var(--glass-soft); }
  [data-testid="stDataFrame"], [data-testid="stTable"] {
    border-radius: var(--r); overflow: hidden;
  }
  [data-testid="stMetric"] { border-radius: var(--r); padding: .8rem .95rem; }
  [data-testid="stForm"] { border-radius: var(--r-lg) !important; padding: 1.2rem !important; }

  /* ---------- sidebar ---------- */
  [data-testid="stSidebar"] {
    background: var(--glass);
    -webkit-backdrop-filter: var(--blur); backdrop-filter: var(--blur);
    border-right: 1px solid var(--glass-edge);
  }
  [data-testid="stSidebarNav"] a {
    border-radius: 999px !important; transition: background .3s var(--ease);
  }

  /* ---------- centred sign-in ---------- */
  .signin-wrap {
    display: flex; align-items: center; justify-content: center;
    min-height: 62vh; padding: 1rem 0;
  }
  .signin-card {
    width: 100%; max-width: 430px; text-align: center;
    border-radius: var(--r-lg); padding: 2.3rem 2rem 1.9rem;
    background: var(--glass);
    -webkit-backdrop-filter: var(--blur); backdrop-filter: var(--blur);
    border: 1px solid var(--glass-edge);
    box-shadow: var(--shadow-hi), inset 0 1px 0 var(--glass-line);
    animation: glassIn .68s var(--ease) both;
  }
  .signin-mark {
    width: 62px; height: 62px; margin: 0 auto 1.1rem;
    border-radius: 19px;
    background: linear-gradient(135deg, var(--ios-blue), var(--ios-indigo) 55%, var(--ios-purple));
    box-shadow: 0 8px 22px rgba(10,132,255,.34);
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-size: 1.5rem; font-weight: 700; letter-spacing: -.03em;
  }
  .signin-title {
    font-size: 1.42rem; font-weight: 600; color: var(--ink);
    letter-spacing: -.024em; margin-bottom: .45rem;
  }
  .signin-sub {
    font-size: .9rem; color: var(--ink-2); line-height: 1.6;
    margin: 0 auto 1.4rem; max-width: 330px;
  }
  .signin-foot {
    font-size: .775rem; color: var(--ink-3); margin-top: 1.15rem;
    padding-top: 1rem; border-top: 1px solid var(--glass-edge);
  }
  .signin-wrap + div [data-testid="stElementContainer"] { animation: none; }

  /* ---------- phones ---------- */
  @media (max-width: 640px) {
    [data-testid="stMain"] .block-container {
      padding-left: .8rem; padding-right: .8rem; padding-top: 1rem;
    }
    .kpi-grid { grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: .55rem; }
    .kpi-card { padding: .65rem .7rem; border-radius: 16px; }
    .kpi-value { font-size: 1.24rem; }
    .kpi-label { font-size: .65rem; }
    [data-testid="stMain"] h1 { font-size: 1.5rem !important; }
    [data-testid="stMain"] h3 { font-size: 1.02rem !important; }
    [data-baseweb="tab"] { padding: .38rem .78rem !important; font-size: .82rem; }
    .g-hero { padding: .95rem 1.05rem; border-radius: 20px; }
    .signin-card { padding: 1.9rem 1.3rem 1.6rem; border-radius: 24px; }
    .signin-title { font-size: 1.24rem; }
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
