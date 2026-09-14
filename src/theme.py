"""Glassmorphism theme, built to the rules in uxpilot.ai/blogs/glassmorphism-ui.

How the article's rules are applied here:

  * Backdrop. Glass needs something worth refracting, so the canvas is a fixed
    vibrant gradient in the recommended families (blues/teals, purples/magentas)
    kept low-saturation where panels sit, so text never crosses a hard
    light-to-dark jump.
  * Blur. 18px on primary panels, 12px on dense ones - inside the article's
    10-30px band and close to its 5-15px performance advice. Heavier values
    read muddy and cost more to paint.
  * Selective use. The article is emphatic that glass belongs on "a few key
    elements... not every component". Here it is the sidebar, stat cards, hero,
    alerts, toasts, the tab strip and the sign-in card. Dense reading surfaces
    (tables, expanders, forms) use a near-opaque 0.86 tint so data stays sharp,
    and body copy sits on no glass at all.
  * Contrast. The canvas is deliberately mid-tone so the frost reads, which
    also darkens every panel sitting on it - so the glass alpha and the text
    tokens were solved together rather than picked by eye. Worst case is the
    darkest backdrop point (#A8B1F2) under a .68 panel, giving #E3E6FB. On
    that: ink 14.2:1, ink-2 7.3:1, ink-3 4.5:1, red 4.7:1, amber 4.6:1,
    green 4.6:1 - all clearing WCAG AA 4.5:1 for small text. Contrast comes
    from raising panel opacity, never from washing the wallpaper back out.
  * Light direction. One source, top-left. Every panel carries the same inset
    rim light on its top edge; shadows all fall the same way.
  * Motion. The article warns against animating blur on blurred elements, so
    glass panels reveal with opacity and lift only. The motion-blur entrance is
    kept for non-glass content, where it costs nothing to composite.
  * Fallback. @supports swaps in an opaque background where backdrop-filter is
    unsupported, and translateZ(0) pushes compositing to the GPU.
"""
from __future__ import annotations

CSS = """
<style>
  :root {
    /* ink - checked against the lightest glass these can sit on */
    --ink:    #14182B;   /* 14.2:1 on the darkest panel */
    --ink-2:  #414862;   /*  7.3:1 */
    --ink-3:  #5F6780;   /*  4.5:1 */

    /* glass */
    --glass:        rgba(255, 255, 255, .68);
    --glass-strong: rgba(255, 255, 255, .84);
    --glass-dense:  rgba(255, 255, 255, .90);
    --glass-quiet:  rgba(255, 255, 255, .50);
    --edge:         rgba(255, 255, 255, .62);
    --edge-soft:    rgba(140, 155, 190, .22);
    --rim:          inset 0 1px 0 rgba(255, 255, 255, .75);

    --blur:       saturate(165%) blur(18px);
    --blur-dense: saturate(140%) blur(12px);
    --blur-light: saturate(150%) blur(10px);

    /* accents - the article's recommended families */
    --blue:    #2F6BFF;
    --teal:    #14B8C4;
    --violet:  #7C5CFF;
    --magenta: #E0479E;

    --green: #10754F;
    --amber: #965708;
    --red:   #BD2D46;
    --green-tint: rgba(16, 117, 79, .16);
    --amber-tint: rgba(150, 87, 8, .15);
    --red-tint:   rgba(189, 45, 70, .14);
    --grey-tint:  rgba(120, 138, 175, .13);

    --r: 20px;
    --r-lg: 28px;
    --r-sm: 14px;

    /* one light source, top-left: every shadow falls the same way */
    --shadow:    0 2px 6px rgba(18, 24, 48, .05), 0 12px 30px rgba(18, 24, 48, .09);
    --shadow-hi: 0 4px 10px rgba(18, 24, 48, .07), 0 20px 46px rgba(18, 24, 48, .13);
    --ease: cubic-bezier(.32, .72, 0, 1);
    --font: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  }

  /* ---------- backdrop ----------
     Calm where panels sit, colour pushed to the edges, so no text ever
     crosses a hard light-to-dark transition. */
  .stApp {
    background:
      radial-gradient(1200px 680px at  4% -6%, rgba(47, 107, 255, .26), transparent 62%),
      radial-gradient(1000px 620px at 98%  2%, rgba(124, 92, 255, .24), transparent 64%),
      radial-gradient(1100px 700px at 12% 104%, rgba(20, 184, 196, .22), transparent 62%),
      radial-gradient( 900px 560px at 88% 96%, rgba(224, 71, 158, .20), transparent 62%),
      linear-gradient(162deg, #D4DDF2 0%, #CBD5EC 46%, #D2C9EE 100%);
    background-attachment: fixed;
  }
  .stApp, [data-testid="stMain"] { font-family: var(--font); }
  [data-testid="stMain"] .block-container {
    padding-top: 2.4rem; padding-bottom: 4rem; max-width: 1520px;
  }
  footer, #MainMenu { visibility: hidden; }

  h1, h2, h3, h4 { color: var(--ink); letter-spacing: -.028em; font-weight: 600; }
  [data-testid="stMain"] h1 {
    font-size: 2.5rem; line-height: 1.07; margin-bottom: .15rem;
    text-shadow: 0 1px 0 rgba(255, 255, 255, .6);
  }
  [data-testid="stMain"] h3 { font-size: 1.1rem; margin-top: 1.9rem; letter-spacing: -.02em; }
  [data-testid="stMain"] p, [data-testid="stMain"] li,
  [data-testid="stMain"] label { color: var(--ink-2); }

  /* ---------- the glass recipe, in one place ---------- */
  .kpi-card, .callout, .g-hero, .g-alert, .alert-mini, .toast,
  [data-baseweb="tab-list"], [data-testid="stPopoverBody"], .signin-card {
    -webkit-backdrop-filter: var(--blur); backdrop-filter: var(--blur);
    background: var(--glass);
    border: 1px solid var(--edge);
    box-shadow: var(--shadow), var(--rim);
    transform: translateZ(0);            /* composite on the GPU */
  }
  /* Dense reading surfaces stay near-opaque: data legibility beats effect. */
  [data-testid="stDataFrame"], [data-testid="stTable"],
  [data-testid="stExpander"], [data-testid="stForm"], [data-testid="stMetric"] {
    -webkit-backdrop-filter: var(--blur-dense); backdrop-filter: var(--blur-dense);
    background: var(--glass-dense);
    border: 1px solid var(--edge-soft);
    box-shadow: var(--shadow), var(--rim);
  }
  @supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
    .kpi-card, .callout, .g-hero, .g-alert, .alert-mini, .toast,
    [data-baseweb="tab-list"], [data-testid="stPopoverBody"], .signin-card,
    [data-testid="stDataFrame"], [data-testid="stTable"],
    [data-testid="stExpander"], [data-testid="stForm"], [data-testid="stMetric"] {
      background: rgba(255, 255, 255, .92);
    }
  }

  /* ---------- sidebar ---------- */
  [data-testid="stSidebar"] {
    -webkit-backdrop-filter: var(--blur); backdrop-filter: var(--blur);
    background: rgba(255, 255, 255, .62);
    border-right: 1px solid var(--edge);
    box-shadow: 1px 0 0 rgba(255, 255, 255, .5);
  }
  [data-testid="stSidebar"] * { color: var(--ink-2); }
  [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h2 {
    color: var(--ink); font-size: 1.05rem; letter-spacing: -.02em;
  }
  [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
  [data-testid="stSidebar"] small { color: var(--ink-3) !important; }
  [data-testid="stSidebarNav"] { padding-top: .3rem; }
  [data-testid="stSidebarNav"] a {
    border-radius: 999px !important; margin: .16rem .4rem;
    padding: .52rem .9rem !important;
    transition: background .3s var(--ease), box-shadow .3s var(--ease);
  }
  [data-testid="stSidebarNav"] a span { color: var(--ink-2) !important; font-weight: 500; }
  [data-testid="stSidebarNav"] a:hover { background: rgba(255, 255, 255, .5) !important; }
  [data-testid="stSidebarNav"] a[aria-current="page"] {
    background: rgba(255, 255, 255, .82) !important;
    box-shadow: 0 1px 3px rgba(18, 24, 48, .1), var(--rim);
  }
  [data-testid="stSidebarNav"] a[aria-current="page"] span,
  [data-testid="stSidebarNav"] a[aria-current="page"] * {
    color: var(--ink) !important; font-weight: 600;
  }
  [data-testid="stSidebar"] .stButton > button,
  [data-testid="stSidebar"] .stLinkButton > a {
    background: rgba(255, 255, 255, .62); border: 1px solid var(--edge);
    color: var(--ink) !important;
  }
  [data-testid="stSidebar"] .stButton > button:hover { background: rgba(255, 255, 255, .85); }
  [data-testid="stSidebar"] [data-testid="stMetric"] {
    background: rgba(255, 255, 255, .6); border-color: var(--edge);
  }
  [data-testid="stSidebar"] [data-testid="stMetricValue"] { color: var(--ink); }
  [data-testid="stSidebar"] hr { border-color: rgba(140, 155, 190, .25); }

  /* ---------- motion ----------
     Glass panels lift and fade only. Animating blur on something that is
     already running a backdrop-filter is the article's explicit warning, so
     the blur entrance is reserved for plain content. */
  @keyframes riseIn {
    0%   { opacity: 0; transform: translateY(14px) scale(.994); filter: blur(10px); }
    60%  { opacity: 1; }
    100% { opacity: 1; transform: none; filter: blur(0); }
  }
  @keyframes liftIn {
    0%   { opacity: 0; transform: translateY(12px) translateZ(0); }
    100% { opacity: 1; transform: translateZ(0); }
  }
  [data-testid="stMain"] [data-testid="stElementContainer"],
  [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
    animation: riseIn .55s var(--ease) both;
  }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(1) { animation-delay: .00s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(2) { animation-delay: .04s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(3) { animation-delay: .08s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(4) { animation-delay: .12s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(5) { animation-delay: .16s }
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(n+6) { animation-delay: .2s }
  [data-baseweb="tab-panel"] { animation: liftIn .4s var(--ease) both; }

  /* ---------- top bar ---------- */
  .flux-top {
    display: flex; align-items: center; gap: .8rem; flex-wrap: wrap;
    margin: .1rem 0 1.1rem 0;
  }
  .flux-user { display: flex; align-items: center; gap: .65rem; }
  .flux-avatar {
    width: 44px; height: 44px; border-radius: 50%; flex: 0 0 44px;
    background: linear-gradient(140deg, var(--blue), var(--violet) 55%, var(--magenta));
    display: flex; align-items: center; justify-content: center;
    color: #FFFFFF; font-weight: 700; font-size: .92rem;
    letter-spacing: -.02em; border: 2px solid rgba(255, 255, 255, .8);
    box-shadow: var(--shadow);
  }
  .flux-user-name { font-size: .93rem; font-weight: 600; color: var(--ink); line-height: 1.25; }
  .flux-user-mail { font-size: .78rem; color: var(--ink-3); line-height: 1.25; }
  .flux-spacer { flex: 1 1 auto; }
  .flux-datepill {
    display: inline-flex; align-items: center; gap: .5rem;
    -webkit-backdrop-filter: var(--blur-light); backdrop-filter: var(--blur-light);
    background: var(--glass-strong); border: 1px solid var(--edge);
    border-radius: 999px; padding: .5rem 1rem;
    box-shadow: var(--shadow), var(--rim);
    font-size: .84rem; color: var(--ink-2); font-weight: 500;
  }
  .flux-datepill b { color: var(--ink); font-weight: 600; }

  /* ---------- hero ---------- */
  .g-hero {
    border-radius: var(--r-lg); padding: 1.2rem 1.4rem; margin-bottom: 1.1rem;
    animation: liftIn .5s var(--ease) both;
  }
  .g-hero-title { font-size: 1.05rem; font-weight: 600; color: var(--ink); margin-bottom: .22rem; }
  .g-hero-sub { font-size: .875rem; color: var(--ink-2); line-height: 1.55; }

  /* ---------- stat cards ---------- */
  .kpi-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(196px, 1fr));
    gap: .8rem; margin: .55rem 0 1.25rem 0;
  }
  .kpi-card {
    position: relative; border-radius: var(--r);
    padding: 1.05rem 1.15rem 1rem; min-width: 0;
    transition: transform .4s var(--ease), box-shadow .4s var(--ease),
                background .4s var(--ease);
    animation: liftIn .46s var(--ease) both;
  }
  .kpi-card:hover {
    transform: translateY(-3px) translateZ(0);
    box-shadow: var(--shadow-hi), var(--rim);
    background: var(--glass-strong);
  }
  .kpi-grid .kpi-card:nth-child(1) { animation-delay: .00s }
  .kpi-grid .kpi-card:nth-child(2) { animation-delay: .045s }
  .kpi-grid .kpi-card:nth-child(3) { animation-delay: .09s }
  .kpi-grid .kpi-card:nth-child(4) { animation-delay: .135s }
  .kpi-grid .kpi-card:nth-child(5) { animation-delay: .18s }
  .kpi-grid .kpi-card:nth-child(n+6) { animation-delay: .22s }

  .kpi-head { display: flex; align-items: center; gap: .55rem; margin-bottom: .95rem; }
  .kpi-dot {
    width: 30px; height: 30px; border-radius: 50%; flex: 0 0 30px;
    background: rgba(255, 255, 255, .6); display: flex; align-items: center;
    justify-content: center; font-size: .82rem; line-height: 1;
    border: 1px solid var(--edge); box-shadow: var(--rim);
  }
  .kpi-label {
    font-size: .845rem; font-weight: 500; color: var(--ink-2);
    line-height: 1.3; overflow-wrap: break-word; letter-spacing: -.004em;
  }
  .kpi-value {
    font-size: 2.05rem; font-weight: 600; line-height: 1.05;
    color: var(--ink); letter-spacing: -.042em;
    text-shadow: 0 1px 0 rgba(255, 255, 255, .55);
    overflow-wrap: break-word; display: flex; align-items: baseline;
    gap: .42rem; flex-wrap: wrap;
  }
  .kpi-unit { font-size: .82rem; font-weight: 500; color: var(--ink-3); letter-spacing: 0; }
  .kpi-badge {
    display: inline-block; font-size: .715rem; font-weight: 600;
    padding: .18rem .52rem; border-radius: 999px; letter-spacing: -.01em;
    background: var(--green-tint); color: var(--green);
    border: 1px solid rgba(18, 135, 90, .2);
  }
  .kpi-badge.down { background: var(--red-tint); color: var(--red); border-color: rgba(201, 48, 74, .2); }
  .kpi-badge.flat { background: var(--grey-tint); color: var(--ink-2); border-color: var(--edge-soft); }
  .kpi-sub { font-size: .775rem; color: var(--ink-3); margin-top: .4rem; line-height: 1.4; }
  .kpi-card.is-red   { background: linear-gradient(180deg, var(--red-tint), rgba(255,255,255,.5)); }
  .kpi-card.is-amber { background: linear-gradient(180deg, var(--amber-tint), rgba(255,255,255,.5)); }
  .kpi-card.is-green { background: linear-gradient(180deg, var(--green-tint), rgba(255,255,255,.5)); }

  /* ---------- chips ---------- */
  .chip {
    display: inline-block; padding: .3rem .8rem; border-radius: 999px;
    font-size: .765rem; font-weight: 600; margin: .16rem .34rem .16rem 0;
    border: 1px solid var(--edge); white-space: nowrap;
    -webkit-backdrop-filter: var(--blur-light); backdrop-filter: var(--blur-light);
    box-shadow: var(--rim);
    transition: transform .3s var(--ease);
  }
  .chip:hover { transform: translateY(-1px); }
  .chip-red   { background: var(--red-tint);   color: var(--red); }
  .chip-amber { background: var(--amber-tint); color: var(--amber); }
  .chip-green { background: var(--green-tint); color: var(--green); }
  .chip-grey  { background: var(--glass-strong); color: var(--ink-2); }

  /* ---------- callouts ---------- */
  .callout {
    border-radius: var(--r); padding: 1.05rem 1.2rem; margin: .5rem 0 1.2rem 0;
    font-size: .895rem; color: var(--ink-2);
    animation: liftIn .46s var(--ease) both;
  }
  .callout strong { color: var(--ink); font-weight: 600; }
  .callout.red   { background: linear-gradient(180deg, var(--red-tint), rgba(255,255,255,.52)); }
  .callout.amber { background: linear-gradient(180deg, var(--amber-tint), rgba(255,255,255,.52)); }
  .callout.green { background: linear-gradient(180deg, var(--green-tint), rgba(255,255,255,.52)); }
  .callout ul { margin: .4rem 0 0 1.15rem; padding: 0; }
  .callout li { margin: .24rem 0; line-height: 1.55; }

  .section-note { color: var(--ink-3); font-size: .865rem; margin: -.3rem 0 .8rem 0; }
  .src-note { color: var(--ink-3); font-size: .775rem; margin-top: .5rem; opacity: .85; }

  /* ---------- alerts ---------- */
  .g-alert {
    display: flex; gap: .9rem; align-items: flex-start;
    border-radius: var(--r); padding: 1rem 1.15rem; margin: .45rem 0 .7rem 0;
    border-left: 4px solid var(--amber);
    background: linear-gradient(180deg, var(--amber-tint), rgba(255,255,255,.5));
    animation: liftIn .46s var(--ease) both;
  }
  .g-alert.red {
    border-left-color: var(--red);
    background: linear-gradient(180deg, var(--red-tint), rgba(255,255,255,.5));
  }
  .g-alert-body { flex: 1; min-width: 0; }
  .g-alert-title { font-weight: 600; color: var(--ink); font-size: .93rem; margin-bottom: .2rem; }
  .g-alert-text { font-size: .855rem; color: var(--ink-2); line-height: 1.55; }
  .g-alert-meta { font-size: .775rem; color: var(--ink-3); margin-top: .32rem; }

  .alert-grid {
    display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: .7rem; margin: .4rem 0 1rem 0;
  }
  .alert-mini {
    border-radius: var(--r-sm); border-left: 4px solid var(--amber);
    padding: .85rem .95rem; min-width: 0;
    animation: liftIn .44s var(--ease) both;
    transition: transform .32s var(--ease), box-shadow .32s var(--ease);
    background: linear-gradient(180deg, var(--amber-tint), rgba(255,255,255,.5));
  }
  .alert-mini:hover { transform: translateY(-2px) translateZ(0); box-shadow: var(--shadow-hi), var(--rim); }
  .alert-mini.red {
    border-left-color: var(--red);
    background: linear-gradient(180deg, var(--red-tint), rgba(255,255,255,.5));
  }
  .alert-mini-name { font-size: .875rem; font-weight: 600; color: var(--ink); margin-bottom: .2rem; }
  .alert-mini-msg { font-size: .795rem; color: var(--ink-2); line-height: 1.45; }
  .alert-mini-meta { font-size: .715rem; color: var(--ink-3); margin-top: .32rem; line-height: 1.4; }
  .alert-grid .alert-mini:nth-child(1) { animation-delay: .00s }
  .alert-grid .alert-mini:nth-child(2) { animation-delay: .04s }
  .alert-grid .alert-mini:nth-child(3) { animation-delay: .08s }
  .alert-grid .alert-mini:nth-child(n+4) { animation-delay: .12s }
  @media (max-width: 1100px) { .alert-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  @media (max-width: 700px)  { .alert-grid { grid-template-columns: 1fr; } }

  /* A filtered or transformed ancestor becomes the containing block for
     position:fixed - and backdrop-filter does it too - so the toast stack
     would anchor to its wrapper instead of the viewport. */
  [data-testid="stElementContainer"]:has(.toast-stack),
  [data-testid="stVerticalBlockBorderWrapper"]:has(.toast-stack),
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .toast-stack) {
    animation: none !important; filter: none !important; transform: none !important;
    backdrop-filter: none !important; -webkit-backdrop-filter: none !important;
  }

  /* ---------- toasts ---------- */
  .toast-stack {
    position: fixed; right: 18px; bottom: 18px; z-index: 9990;
    display: flex; flex-direction: column; gap: .45rem;
    width: 300px; max-width: calc(100vw - 36px); pointer-events: none;
  }
  .toast-stack > * { pointer-events: auto; }
  .toast-head {
    align-self: flex-end; font-size: .68rem; font-weight: 600;
    letter-spacing: .05em; text-transform: uppercase; color: var(--ink-2);
    -webkit-backdrop-filter: var(--blur-light); backdrop-filter: var(--blur-light);
    background: var(--glass-strong); border: 1px solid var(--edge);
    border-radius: 999px; padding: .22rem .62rem; box-shadow: var(--shadow), var(--rim);
  }
  .toast-x { display: none; }
  .toast {
    display: flex; gap: .55rem; align-items: flex-start;
    border-left: 3px solid var(--red); border-radius: var(--r-sm);
    padding: .65rem .75rem; box-shadow: var(--shadow-hi), var(--rim);
    background: linear-gradient(180deg, var(--red-tint), rgba(255,255,255,.62));
    animation: toastIn .46s var(--ease) both;
  }
  .toast.amber {
    border-left-color: var(--amber);
    background: linear-gradient(180deg, var(--amber-tint), rgba(255,255,255,.62));
  }
  .toast-x:checked + .toast { display: none; }
  .toast-body { flex: 1; min-width: 0; }
  .toast-title { font-size: .775rem; font-weight: 600; color: var(--ink); line-height: 1.3; margin-bottom: .1rem; }
  .toast-text {
    font-size: .715rem; color: var(--ink-2); line-height: 1.4;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  }
  .toast-close {
    cursor: pointer; color: var(--ink-3); font-size: .95rem; line-height: 1;
    padding: 0 .1rem; flex: 0 0 auto; user-select: none;
    transition: color .2s var(--ease);
  }
  .toast-close:hover { color: var(--ink); }
  @keyframes toastIn {
    0%   { opacity: 0; transform: translateX(22px) translateZ(0); }
    100% { opacity: 1; transform: translateZ(0); }
  }
  @media (max-width: 640px) {
    .toast-stack { width: calc(100vw - 24px); right: 12px; bottom: 12px; gap: .35rem; }
    .toast-text { -webkit-line-clamp: 1; }
  }

  /* ---------- tabs ---------- */
  [data-baseweb="tab-list"] {
    gap: .2rem; border-bottom: none; padding: .28rem;
    margin-bottom: .65rem; overflow-x: auto; border-radius: 999px;
    width: fit-content; max-width: 100%;
  }
  [data-baseweb="tab"] {
    background: transparent !important; border-radius: 999px !important;
    padding: .44rem 1.05rem !important; font-size: .865rem; font-weight: 500;
    color: var(--ink-2); white-space: nowrap;
    transition: background .32s var(--ease), color .32s var(--ease);
  }
  [data-baseweb="tab"]:hover { color: var(--ink); background: rgba(255, 255, 255, .5) !important; }
  [data-baseweb="tab"][aria-selected="true"] {
    color: #FFFFFF; font-weight: 600;
    background: linear-gradient(135deg, var(--blue), var(--violet)) !important;
    box-shadow: 0 3px 10px rgba(47, 107, 255, .34);
  }
  [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none; }

  /* ---------- controls ---------- */
  .stButton > button, .stDownloadButton > button, .stLinkButton > a {
    border-radius: 999px !important; font-weight: 500;
    border: 1px solid var(--edge);
    -webkit-backdrop-filter: var(--blur-light); backdrop-filter: var(--blur-light);
    background: var(--glass-strong); color: var(--ink);
    box-shadow: var(--rim);
    transition: transform .28s var(--ease), box-shadow .28s var(--ease), filter .28s var(--ease);
  }
  .stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {
    transform: translateY(-1px); box-shadow: var(--shadow), var(--rim);
  }
  .stButton > button:active { transform: scale(.978); }
  [data-testid="stMain"] .stButton > button[kind="primary"],
  button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, var(--blue), var(--violet)) !important;
    border: none !important; color: #FFFFFF !important;
    box-shadow: 0 4px 14px rgba(47, 107, 255, .32);
  }
  [data-testid="stMain"] .stButton > button[kind="primary"]:hover { filter: brightness(1.07); }

  [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
  [data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
  .stTextInput input, .stNumberInput input, .stTextArea textarea, .stDateInput input {
    border-radius: var(--r-sm) !important;
    background: var(--glass-strong) !important;
    border-color: var(--edge) !important;
    -webkit-backdrop-filter: var(--blur-light); backdrop-filter: var(--blur-light);
  }

  [data-testid="stExpander"] { border-radius: var(--r) !important; overflow: hidden; }
  [data-testid="stExpander"] summary:hover { background: rgba(255, 255, 255, .5); }
  [data-testid="stDataFrame"], [data-testid="stTable"] { border-radius: var(--r); overflow: hidden; }
  [data-testid="stMetric"] { border-radius: var(--r); padding: .85rem 1rem; }
  [data-testid="stForm"] { border-radius: var(--r-lg) !important; padding: 1.2rem !important; }

  [data-testid="stSegmentedControl"] button {
    border-radius: 999px !important; font-weight: 500; font-size: .85rem;
    border-color: var(--edge) !important; background: var(--glass-strong) !important;
  }
  [data-testid="stSegmentedControl"] button[aria-checked="true"],
  [data-testid="stSegmentedControl"] button[aria-pressed="true"] {
    background: linear-gradient(135deg, var(--blue), var(--violet)) !important;
    color: #FFFFFF !important; border-color: transparent !important;
  }

  /* ---------- version toggle ---------- */
  .flux-verbar { height: .35rem; }
  [data-testid="stPopoverButton"] {
    background: transparent !important; border: none !important;
    box-shadow: none !important; border-radius: 10px !important;
    padding: .24rem .45rem .24rem .3rem !important;
    font-size: 1.16rem !important; font-weight: 600 !important;
    letter-spacing: -.026em; color: var(--ink) !important;
    transition: background .25s var(--ease);
    -webkit-backdrop-filter: none !important; backdrop-filter: none !important;
  }
  [data-testid="stPopoverButton"]:hover { background: rgba(255, 255, 255, .5) !important; }
  [data-testid="stPopoverButton"]:focus,
  [data-testid="stPopoverButton"]:active { box-shadow: none !important; border: none !important; }
  [data-testid="stPopoverBody"] { padding: .45rem !important; min-width: 190px; border-radius: var(--r-sm) !important; }
  [data-testid="stPopoverBody"] .stButton > button,
  [data-testid="stPopoverBody"] button[data-testid^="stBaseButton"] {
    background: transparent !important; border: none !important;
    box-shadow: none !important; border-radius: 9px !important;
    backdrop-filter: none !important; -webkit-backdrop-filter: none !important;
    justify-content: flex-start !important; text-align: left !important;
    padding: .42rem .6rem !important; margin: 0 !important;
    font-size: .93rem !important; font-weight: 500 !important;
    color: var(--ink) !important; min-height: 0 !important;
  }
  [data-testid="stPopoverBody"] .stButton > button:hover { background: rgba(255, 255, 255, .55) !important; }
  [data-testid="stPopoverBody"] .stButton > button p {
    font-size: .93rem !important; font-weight: 500 !important;
    white-space: pre !important; color: var(--ink) !important;
  }
  /* Streamlit centres the label in a nested flex wrapper inside the button,
     which overrides the button's own alignment - so unset it there too. */
  [data-testid="stPopoverBody"] .stButton > button > div,
  [data-testid="stPopoverBody"] .stButton > button > div > span {
    justify-content: flex-start !important; width: 100% !important;
  }
  [data-testid="stPopoverBody"] [data-testid="stVerticalBlock"] { gap: .1rem !important; }
  .flux-ver-note { display: inline-block; font-size: .735rem; color: var(--ink-3); margin-top: .1rem; }
  .flux-ver-pill {
    display: inline-block; font-size: .68rem; font-weight: 600;
    padding: .14rem .48rem; border-radius: 999px; margin-left: .3rem;
    background: var(--green-tint); color: var(--green);
  }

  /* ---------- sign-in ---------- */
  .signin-wrap {
    display: flex; align-items: center; justify-content: center;
    min-height: 62vh; padding: 1rem 0;
  }
  .signin-card {
    width: 100%; max-width: 430px; text-align: center;
    border-radius: var(--r-lg); padding: 2.4rem 2rem 1.9rem;
    box-shadow: var(--shadow-hi), var(--rim);
    animation: liftIn .55s var(--ease) both;
  }
  .signin-mark {
    width: 62px; height: 62px; margin: 0 auto 1.15rem; border-radius: 19px;
    background: linear-gradient(140deg, var(--blue), var(--violet) 55%, var(--magenta));
    display: flex; align-items: center; justify-content: center;
    color: #FFFFFF; font-size: 1.45rem; font-weight: 700; letter-spacing: -.035em;
    box-shadow: 0 8px 22px rgba(47, 107, 255, .32);
  }
  .signin-title { font-size: 1.45rem; font-weight: 600; color: var(--ink);
                  letter-spacing: -.03em; margin-bottom: .45rem; }
  .signin-sub { font-size: .9rem; color: var(--ink-2); line-height: 1.6;
                margin: 0 auto 1.4rem; max-width: 330px; }
  .signin-foot { font-size: .775rem; color: var(--ink-3); margin-top: 1.15rem;
                 padding-top: 1rem; border-top: 1px solid var(--edge-soft); }

  /* ---------- phones ---------- */
  @media (max-width: 640px) {
    [data-testid="stMain"] .block-container {
      padding-left: .75rem; padding-right: .75rem; padding-top: 1.6rem;
    }
    .kpi-grid { grid-template-columns: repeat(auto-fit, minmax(146px, 1fr)); gap: .55rem; }
    .kpi-card { padding: .8rem .85rem; border-radius: 16px; }
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
    /* Lighter blur on phones - the article flags it as a mobile cost. */
    :root { --blur: saturate(150%) blur(12px); --blur-dense: saturate(130%) blur(9px); }
  }

  @media (prefers-reduced-motion: reduce) {
    *, [data-testid="stMain"] [data-testid="stElementContainer"],
    .kpi-card, .callout, .g-hero, .g-alert, .alert-mini, .toast,
    .signin-card, [data-baseweb="tab-panel"] {
      animation: none !important; transition: none !important; filter: none !important;
    }
  }
</style>
"""
