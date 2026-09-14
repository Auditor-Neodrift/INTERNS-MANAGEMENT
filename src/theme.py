"""Four themes, two of them glass, built to uxpilot.ai/blogs/glassmorphism-ui.

  dark_glass   crystal panels over a photographic backdrop
  light_glass  the same, inverted
  dark_flat    solid surfaces, no blur, no image
  light_flat   solid surfaces, no blur, no image

The two glass themes put a scrim between the backdrop image and the panels.
That is what makes any wallpaper safe: the scrim bounds how bright or dark the
backdrop can get, so the panel colour - and therefore text contrast - stays
inside a known range whatever image is set.

Crystal glass means low opacity and high blur, which costs contrast, so the
worst cases were measured rather than guessed:

  dark_glass  scrim .72 over pure white -> #4C4E54; panel .50 -> #2D303A.
              ink 11.8:1, ink-2 7.6:1, ink-3 5.2:1, red 5.7:1, blue 6.0:1.
  light_glass scrim .74 over pure black -> #BDBDBD; panel .46 -> #DBDBDB.
              ink 12.9:1, ink-2 7.2:1, ink-3 4.5:1, green 4.7:1, amber 4.8:1,
              red 5.0:1, blue 4.8:1.

All clear WCAG AA 4.5:1 for small text against the worst backdrop the scrim
allows, so a user-supplied image cannot break legibility.

Depth on glass comes from the edge, not the fill: a 1px border, a bright rim
highlight on the lit edge and a soft drop shadow, all sharing one light source
at top-left. The article warns against animating blur on blurred elements, so
glass panels reveal with opacity and lift while plain content keeps the
motion-blur entrance.
"""
from __future__ import annotations

THEME_LABELS = {
    "dark_glass": "Dark · Glass",
    "light_glass": "Light · Glass",
    "dark_flat": "Dark",
    "light_flat": "Light",
}
THEME_ORDER = ["dark_glass", "light_glass", "dark_flat", "light_flat"]
DEFAULT_THEME = "dark_glass"
DEFAULT_DARK_BG = "app/static/bg.jpg"
DEFAULT_LIGHT_BG = ""

def is_glass(theme: str) -> bool:
    return theme.endswith("_glass")

def is_dark(theme: str) -> bool:
    return theme.startswith("dark")


# --------------------------------------------------------------------------
# Palettes. Every token below was measured against the worst backdrop its
# theme's scrim permits - see the module docstring.
# --------------------------------------------------------------------------
_DARK = {
    "ink": "#F2F4F8", "ink2": "#C9D1E0", "ink3": "#A3ACC2",
    "green": "#5CE68F", "amber": "#FCC63A", "red": "#FF8797", "blue": "#8FB6FF",
    "violet": "#B3A6FF", "teal": "#6FE0E8", "magenta": "#F79BCC",
    "edge": "rgba(255,255,255,.20)", "edge_soft": "rgba(255,255,255,.12)",
    "rim": "inset 0 1px 0 rgba(190,220,255,.34)",
    "on_accent": "#08101F",
    "shadow": "0 2px 8px rgba(0,0,0,.36), 0 16px 42px rgba(0,0,0,.44)",
    "shadow_hi": "0 4px 14px rgba(0,0,0,.42), 0 26px 60px rgba(0,0,0,.54)",
    "green_t": "rgba(92,230,143,.16)", "amber_t": "rgba(252,198,58,.16)",
    "red_t": "rgba(255,135,151,.16)", "grey_t": "rgba(170,190,225,.12)",
    "menu": "rgba(12,16,27,.97)",
    "flat_bg": "#0B0F19", "flat_panel": "#141A28", "flat_line": "rgba(255,255,255,.12)",
}
_LIGHT = {
    "ink": "#12172A", "ink2": "#3A4258", "ink3": "#57607A",
    "green": "#0F6B47", "amber": "#8A4F07", "red": "#A8283E", "blue": "#1D4FD8",
    "violet": "#5B3FD0", "teal": "#0D7A84", "magenta": "#B03579",
    "edge": "rgba(255,255,255,.75)", "edge_soft": "rgba(120,140,180,.24)",
    "rim": "inset 0 1px 0 rgba(255,255,255,.9)",
    "on_accent": "#FFFFFF",
    "shadow": "0 2px 6px rgba(18,24,48,.07), 0 14px 34px rgba(18,24,48,.11)",
    "shadow_hi": "0 4px 12px rgba(18,24,48,.10), 0 24px 54px rgba(18,24,48,.16)",
    "green_t": "rgba(15,107,71,.14)", "amber_t": "rgba(138,79,7,.14)",
    "red_t": "rgba(168,40,62,.12)", "grey_t": "rgba(120,140,180,.13)",
    "menu": "rgba(255,255,255,.98)",
    "flat_bg": "#F2F4F8", "flat_panel": "#FFFFFF", "flat_line": "rgba(120,140,180,.26)",
}

# Crystal: low opacity, high blur, bright edges.
_GLASS = {
    "dark":  {"scrim": "rgba(6,9,17,.72)",       "panel": "rgba(14,19,32,.50)",
              "strong": "rgba(14,19,32,.62)",    "dense": "rgba(12,16,27,.68)",
              "hover": "rgba(255,255,255,.10)"},
    "light": {"scrim": "rgba(255,255,255,.74)",  "panel": "rgba(255,255,255,.46)",
              "strong": "rgba(255,255,255,.62)", "dense": "rgba(255,255,255,.70)",
              "hover": "rgba(255,255,255,.55)"},
}
BLUR = "saturate(180%) blur(26px)"
BLUR_DENSE = "saturate(160%) blur(18px)"
BLUR_LIGHT = "saturate(170%) blur(14px)"


def _backdrop(theme: str, dark_bg: str, light_bg: str) -> str:
    """The app background: scrim over the image, or a plain surface when flat."""
    dark = is_dark(theme)
    p = _DARK if dark else _LIGHT
    if not is_glass(theme):
        return f"  .stApp {{ background: {p['flat_bg']}; }}"

    g = _GLASS["dark" if dark else "light"]
    image = (dark_bg if dark else light_bg).strip()
    fallback = "#05070C" if dark else "#E9EEF8"
    tint = (
        "radial-gradient(1200px 700px at 6% -8%, rgba(47,107,255,.30), transparent 62%),"
        "radial-gradient(1000px 640px at 96% 4%, rgba(124,92,255,.26), transparent 64%),"
        "linear-gradient(162deg, #0A1226 0%, #0B1020 50%, #140F24 100%)"
        if dark else
        "radial-gradient(1200px 700px at 6% -8%, rgba(47,107,255,.22), transparent 62%),"
        "radial-gradient(1000px 640px at 96% 4%, rgba(124,92,255,.20), transparent 64%),"
        "linear-gradient(162deg, #E8EEFC 0%, #E3E9F7 50%, #EDE7F8 100%)"
    )
    layers = [f"linear-gradient({g['scrim']}, {g['scrim']})"]
    if image:
        layers.append(f'url("{image}") center / cover no-repeat fixed')
    layers.append(tint if not image else fallback)
    mobile = "scroll, " * (len(layers) - 1) + "scroll"
    return (
        f"  .stApp {{ background: {', '.join(layers)}; }}\n"
        f"  @media (max-width: 640px) {{ .stApp {{ background-attachment: {mobile}; }} }}"
    )


def css(theme: str = DEFAULT_THEME, dark_bg: str = DEFAULT_DARK_BG,
        light_bg: str = DEFAULT_LIGHT_BG) -> str:
    """The full stylesheet for one theme."""
    theme = theme if theme in THEME_LABELS else DEFAULT_THEME
    dark, glass = is_dark(theme), is_glass(theme)
    p = _DARK if dark else _LIGHT
    g = _GLASS["dark" if dark else "light"]

    if glass:
        surface = f"""
    --panel: {g['panel']};
    --panel-strong: {g['strong']};
    --panel-dense: {g['dense']};
    --hover: {g['hover']};
    --blur: {BLUR};
    --blur-dense: {BLUR_DENSE};
    --blur-light: {BLUR_LIGHT};"""
        blur_on = "-webkit-backdrop-filter: var(--blur); backdrop-filter: var(--blur);"
        blur_dense = "-webkit-backdrop-filter: var(--blur-dense); backdrop-filter: var(--blur-dense);"
        blur_light = "-webkit-backdrop-filter: var(--blur-light); backdrop-filter: var(--blur-light);"
        fallback = f"""
  @supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {{
    .kpi-card, .callout, .g-hero, .g-alert, .alert-mini, .toast, .signin-card,
    [data-baseweb="tab-list"], [data-testid="stPopoverBody"],
    [data-testid="stDataFrame"], [data-testid="stTable"], [data-testid="stExpander"],
    [data-testid="stForm"], [data-testid="stMetric"], [data-testid="stSidebar"] {{
      background: {p['flat_panel']};
    }}
  }}"""
    else:
        surface = f"""
    --panel: {p['flat_panel']};
    --panel-strong: {p['flat_panel']};
    --panel-dense: {p['flat_panel']};
    --hover: {p['grey_t']};
    --blur: none; --blur-dense: none; --blur-light: none;"""
        blur_on = blur_dense = blur_light = ""
        fallback = ""

    edge = p["edge"] if glass else p["flat_line"]
    rim = p["rim"] if glass else "none"

    return f"""
<style>
  :root {{
    --ink: {p['ink']};
    --ink-2: {p['ink2']};
    --ink-3: {p['ink3']};
    --blue: {p['blue']};
    --violet: {p['violet']};
    --teal: {p['teal']};
    --magenta: {p['magenta']};
    --green: {p['green']};
    --amber: {p['amber']};
    --red: {p['red']};
    --green-tint: {p['green_t']};
    --amber-tint: {p['amber_t']};
    --red-tint: {p['red_t']};
    --grey-tint: {p['grey_t']};
    --edge: {edge};
    --edge-soft: {p['edge_soft']};
    --rim: {rim};
    --on-accent: {p['on_accent']};
    --menu: {p['menu']};
    --shadow: {p['shadow']};
    --shadow-hi: {p['shadow_hi']};{surface}
    --r: 20px; --r-lg: 28px; --r-sm: 14px;
    --ease: cubic-bezier(.32, .72, 0, 1);
    --font: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  }}

{_backdrop(theme, dark_bg, light_bg)}
  .stApp, [data-testid="stMain"] {{ font-family: var(--font); color: var(--ink-2); }}
  [data-testid="stMain"] .block-container {{
    padding-top: 2.4rem; padding-bottom: 4rem; max-width: 1520px;
  }}
  footer, #MainMenu {{ visibility: hidden; }}

  h1, h2, h3, h4 {{ color: var(--ink); letter-spacing: -.028em; font-weight: 600; }}
  [data-testid="stMain"] h1 {{ font-size: 2.5rem; line-height: 1.07; margin-bottom: .15rem; }}
  [data-testid="stMain"] h3 {{ font-size: 1.1rem; margin-top: 1.9rem; letter-spacing: -.02em; }}
  [data-testid="stMain"] p, [data-testid="stMain"] li,
  [data-testid="stMain"] label {{ color: var(--ink-2); }}
  [data-testid="stMain"] a {{ color: var(--blue); }}

  /* ---------- crystal surfaces ---------- */
  .kpi-card, .callout, .g-hero, .g-alert, .alert-mini, .toast,
  [data-baseweb="tab-list"], [data-testid="stPopoverBody"], .signin-card {{
    {blur_on}
    background: var(--panel);
    border: 1px solid var(--edge);
    box-shadow: var(--shadow), var(--rim);
    transform: translateZ(0);
  }}
  /* Tables, forms and expanders get the same crystal, a touch denser so dense
     data still reads through it. */
  [data-testid="stDataFrame"], [data-testid="stTable"],
  [data-testid="stExpander"], [data-testid="stForm"], [data-testid="stMetric"] {{
    {blur_dense}
    background: var(--panel-dense);
    border: 1px solid var(--edge);
    box-shadow: var(--shadow), var(--rim);
  }}
  /* Streamlit paints its own opaque cell background inside the grid - clear it
     so the glass actually shows through the table. */
  [data-testid="stDataFrame"] [data-testid="stDataFrameResizable"],
  [data-testid="stDataFrame"] canvas {{ background: transparent !important; }}
  [data-testid="stDataFrame"] * {{ color: var(--ink-2); }}
{fallback}

  /* ---------- sidebar ---------- */
  [data-testid="stSidebar"] {{
    {blur_on}
    background: var(--panel-strong);
    border-right: 1px solid var(--edge);
  }}
  [data-testid="stSidebar"] * {{ color: var(--ink-2); }}
  [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h2 {{
    color: var(--ink); font-size: 1.05rem; letter-spacing: -.02em;
  }}
  [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
  [data-testid="stSidebar"] small {{ color: var(--ink-3) !important; }}
  [data-testid="stSidebarNav"] {{ padding-top: .3rem; }}
  [data-testid="stSidebarNav"] a {{
    border-radius: 999px !important; margin: .16rem .4rem;
    padding: .52rem .9rem !important;
    transition: background .3s var(--ease), box-shadow .3s var(--ease);
  }}
  [data-testid="stSidebarNav"] a span {{ color: var(--ink-2) !important; font-weight: 500; }}
  [data-testid="stSidebarNav"] a:hover {{ background: var(--hover) !important; }}
  [data-testid="stSidebarNav"] a[aria-current="page"] {{
    background: var(--panel-dense) !important;
    border: 1px solid var(--edge); box-shadow: var(--rim);
  }}
  [data-testid="stSidebarNav"] a[aria-current="page"] span,
  [data-testid="stSidebarNav"] a[aria-current="page"] * {{
    color: var(--ink) !important; font-weight: 600;
  }}
  [data-testid="stSidebar"] .stButton > button,
  [data-testid="stSidebar"] .stLinkButton > a {{
    background: var(--panel-strong); border: 1px solid var(--edge);
    color: var(--ink) !important;
  }}
  [data-testid="stSidebar"] .stButton > button:hover {{ background: var(--hover); }}
  [data-testid="stSidebar"] [data-testid="stMetric"] {{ background: var(--panel); }}
  [data-testid="stSidebar"] [data-testid="stMetricValue"] {{ color: var(--ink); }}
  [data-testid="stSidebar"] hr {{ border-color: var(--edge-soft); }}

  /* ---------- motion ---------- */
  @keyframes riseIn {{
    0%   {{ opacity: 0; transform: translateY(14px) scale(.994); filter: blur(10px); }}
    60%  {{ opacity: 1; }}
    100% {{ opacity: 1; transform: none; filter: blur(0); }}
  }}
  @keyframes liftIn {{
    0%   {{ opacity: 0; transform: translateY(12px) translateZ(0); }}
    100% {{ opacity: 1; transform: translateZ(0); }}
  }}
  [data-testid="stMain"] [data-testid="stElementContainer"],
  [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {{
    animation: riseIn .55s var(--ease) both;
  }}
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(1) {{ animation-delay: 0s }}
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(2) {{ animation-delay: .04s }}
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(3) {{ animation-delay: .08s }}
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(4) {{ animation-delay: .12s }}
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(5) {{ animation-delay: .16s }}
  [data-testid="stMain"] [data-testid="stElementContainer"]:nth-child(n+6) {{ animation-delay: .2s }}
  [data-baseweb="tab-panel"] {{ animation: liftIn .4s var(--ease) both; }}

  /* ---------- theme switch, pinned top-right ---------- */
  .st-key-theme_dock {{
    position: fixed; top: 3.1rem; right: 1.1rem; z-index: 9995;
    width: auto !important;
    animation: none !important; filter: none !important;
    transform: none !important;
    -webkit-backdrop-filter: none !important; backdrop-filter: none !important;
  }}
  .st-key-theme_dock [data-testid="stSegmentedControl"] button {{
    font-size: .76rem !important; padding: .3rem .7rem !important;
  }}
  /* Nothing up the tree may carry a filter or transform, or the dock stops
     being fixed to the viewport and falls back into the page flow. */
  [data-testid="stElementContainer"]:has(.st-key-theme_dock),
  [data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-theme_dock),
  [data-testid="stVerticalBlock"]:has(.st-key-theme_dock) {{
    animation: none !important; filter: none !important; transform: none !important;
    -webkit-backdrop-filter: none !important; backdrop-filter: none !important;
  }}
  @media (max-width: 640px) {{
    .st-key-theme_dock {{ top: 2.7rem; right: .5rem; }}
    .st-key-theme_dock [data-testid="stSegmentedControl"] button {{
      font-size: .68rem !important; padding: .24rem .5rem !important;
    }}
  }}

  /* ---------- top bar ---------- */
  .flux-top {{ display: flex; align-items: center; gap: .8rem; flex-wrap: wrap; margin: .1rem 0 1.1rem 0; }}
  .flux-user {{ display: flex; align-items: center; gap: .65rem; }}
  .flux-avatar {{
    width: 44px; height: 44px; border-radius: 50%; flex: 0 0 44px;
    background: linear-gradient(140deg, var(--blue), var(--violet) 55%, var(--magenta));
    display: flex; align-items: center; justify-content: center;
    color: var(--on-accent); font-weight: 700; font-size: .92rem;
    letter-spacing: -.02em; border: 2px solid var(--edge); box-shadow: var(--shadow);
  }}
  .flux-user-name {{ font-size: .93rem; font-weight: 600; color: var(--ink); line-height: 1.25; }}
  .flux-user-mail {{ font-size: .78rem; color: var(--ink-3); line-height: 1.25; }}
  .flux-spacer {{ flex: 1 1 auto; }}
  .flux-datepill {{
    display: inline-flex; align-items: center; gap: .5rem;
    {blur_light}
    background: var(--panel-strong); border: 1px solid var(--edge);
    border-radius: 999px; padding: .5rem 1rem;
    box-shadow: var(--shadow), var(--rim);
    font-size: .84rem; color: var(--ink-2); font-weight: 500;
  }}
  .flux-datepill b {{ color: var(--ink); font-weight: 600; }}

  /* ---------- hero ---------- */
  .g-hero {{
    border-radius: var(--r-lg); padding: 1.2rem 1.4rem; margin-bottom: 1.1rem;
    animation: liftIn .5s var(--ease) both;
  }}
  .g-hero-title {{ font-size: 1.05rem; font-weight: 600; color: var(--ink); margin-bottom: .22rem; }}
  .g-hero-sub {{ font-size: .875rem; color: var(--ink-2); line-height: 1.55; }}

  /* ---------- stat cards ---------- */
  .kpi-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(196px, 1fr));
    gap: .8rem; margin: .55rem 0 1.25rem 0;
  }}
  .kpi-card {{
    position: relative; border-radius: var(--r);
    padding: 1.05rem 1.15rem 1rem; min-width: 0;
    transition: transform .4s var(--ease), box-shadow .4s var(--ease), border-color .4s var(--ease);
    animation: liftIn .46s var(--ease) both;
  }}
  .kpi-card:hover {{
    transform: translateY(-3px) translateZ(0);
    box-shadow: var(--shadow-hi), var(--rim);
  }}
  .kpi-grid .kpi-card:nth-child(1) {{ animation-delay: 0s }}
  .kpi-grid .kpi-card:nth-child(2) {{ animation-delay: .045s }}
  .kpi-grid .kpi-card:nth-child(3) {{ animation-delay: .09s }}
  .kpi-grid .kpi-card:nth-child(4) {{ animation-delay: .135s }}
  .kpi-grid .kpi-card:nth-child(5) {{ animation-delay: .18s }}
  .kpi-grid .kpi-card:nth-child(n+6) {{ animation-delay: .22s }}

  .kpi-head {{ display: flex; align-items: center; gap: .55rem; margin-bottom: .95rem; }}
  .kpi-dot {{
    width: 30px; height: 30px; border-radius: 50%; flex: 0 0 30px;
    background: var(--grey-tint); display: flex; align-items: center;
    justify-content: center; font-size: .82rem; line-height: 1;
    border: 1px solid var(--edge);
  }}
  .kpi-label {{
    font-size: .845rem; font-weight: 500; color: var(--ink-2);
    line-height: 1.3; overflow-wrap: break-word; letter-spacing: -.004em;
  }}
  .kpi-value {{
    font-size: 2.05rem; font-weight: 600; line-height: 1.05;
    color: var(--ink); letter-spacing: -.042em;
    overflow-wrap: break-word; display: flex; align-items: baseline;
    gap: .42rem; flex-wrap: wrap;
  }}
  .kpi-unit {{ font-size: .82rem; font-weight: 500; color: var(--ink-3); letter-spacing: 0; }}
  .kpi-badge {{
    display: inline-block; font-size: .715rem; font-weight: 600;
    padding: .18rem .52rem; border-radius: 999px; letter-spacing: -.01em;
    background: var(--green-tint); color: var(--green); border: 1px solid var(--edge);
  }}
  .kpi-badge.down {{ background: var(--red-tint); color: var(--red); }}
  .kpi-badge.flat {{ background: var(--grey-tint); color: var(--ink-2); }}
  .kpi-sub {{ font-size: .775rem; color: var(--ink-3); margin-top: .4rem; line-height: 1.4; }}
  .kpi-card.is-red   {{ background: linear-gradient(180deg, var(--red-tint), var(--panel)); }}
  .kpi-card.is-amber {{ background: linear-gradient(180deg, var(--amber-tint), var(--panel)); }}
  .kpi-card.is-green {{ background: linear-gradient(180deg, var(--green-tint), var(--panel)); }}

  /* ---------- chips ---------- */
  .chip {{
    display: inline-block; padding: .3rem .8rem; border-radius: 999px;
    font-size: .765rem; font-weight: 600; margin: .16rem .34rem .16rem 0;
    border: 1px solid var(--edge); white-space: nowrap;
    {blur_light}
    box-shadow: var(--rim);
    transition: transform .3s var(--ease);
  }}
  .chip:hover {{ transform: translateY(-1px); }}
  .chip-red   {{ background: var(--red-tint);   color: var(--red); }}
  .chip-amber {{ background: var(--amber-tint); color: var(--amber); }}
  .chip-green {{ background: var(--green-tint); color: var(--green); }}
  .chip-grey  {{ background: var(--grey-tint);  color: var(--ink-2); }}

  /* ---------- callouts ---------- */
  .callout {{
    border-radius: var(--r); padding: 1.05rem 1.2rem; margin: .5rem 0 1.2rem 0;
    font-size: .895rem; color: var(--ink-2);
    animation: liftIn .46s var(--ease) both;
  }}
  .callout strong {{ color: var(--ink); font-weight: 600; }}
  .callout.red   {{ background: linear-gradient(180deg, var(--red-tint), var(--panel)); }}
  .callout.amber {{ background: linear-gradient(180deg, var(--amber-tint), var(--panel)); }}
  .callout.green {{ background: linear-gradient(180deg, var(--green-tint), var(--panel)); }}
  .callout ul {{ margin: .4rem 0 0 1.15rem; padding: 0; }}
  .callout li {{ margin: .24rem 0; line-height: 1.55; }}

  .section-note {{ color: var(--ink-3); font-size: .865rem; margin: -.3rem 0 .8rem 0; }}
  .src-note {{ color: var(--ink-3); font-size: .775rem; margin-top: .5rem; opacity: .85; }}

  /* ---------- alerts ---------- */
  .g-alert {{
    display: flex; gap: .9rem; align-items: flex-start;
    border-radius: var(--r); padding: 1rem 1.15rem; margin: .45rem 0 .7rem 0;
    border-left: 4px solid var(--amber);
    background: linear-gradient(180deg, var(--amber-tint), var(--panel));
    animation: liftIn .46s var(--ease) both;
  }}
  .g-alert.red {{
    border-left-color: var(--red);
    background: linear-gradient(180deg, var(--red-tint), var(--panel));
  }}
  .g-alert-body {{ flex: 1; min-width: 0; }}
  .g-alert-title {{ font-weight: 600; color: var(--ink); font-size: .93rem; margin-bottom: .2rem; }}
  .g-alert-text {{ font-size: .855rem; color: var(--ink-2); line-height: 1.55; }}
  .g-alert-meta {{ font-size: .775rem; color: var(--ink-3); margin-top: .32rem; }}

  .alert-grid {{
    display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: .7rem; margin: .4rem 0 1rem 0;
  }}
  .alert-mini {{
    border-radius: var(--r-sm); border-left: 4px solid var(--amber);
    padding: .85rem .95rem; min-width: 0;
    animation: liftIn .44s var(--ease) both;
    transition: transform .32s var(--ease), box-shadow .32s var(--ease);
    background: linear-gradient(180deg, var(--amber-tint), var(--panel));
  }}
  .alert-mini:hover {{ transform: translateY(-2px) translateZ(0); box-shadow: var(--shadow-hi), var(--rim); }}
  .alert-mini.red {{
    border-left-color: var(--red);
    background: linear-gradient(180deg, var(--red-tint), var(--panel));
  }}
  .alert-mini-name {{ font-size: .875rem; font-weight: 600; color: var(--ink); margin-bottom: .2rem; }}
  .alert-mini-msg {{ font-size: .795rem; color: var(--ink-2); line-height: 1.45; }}
  .alert-mini-meta {{ font-size: .715rem; color: var(--ink-3); margin-top: .32rem; line-height: 1.4; }}
  .alert-grid .alert-mini:nth-child(1) {{ animation-delay: 0s }}
  .alert-grid .alert-mini:nth-child(2) {{ animation-delay: .04s }}
  .alert-grid .alert-mini:nth-child(3) {{ animation-delay: .08s }}
  .alert-grid .alert-mini:nth-child(n+4) {{ animation-delay: .12s }}
  @media (max-width: 1100px) {{ .alert-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
  @media (max-width: 700px)  {{ .alert-grid {{ grid-template-columns: 1fr; }} }}

  /* A filtered, transformed or backdrop-filtered ancestor becomes the
     containing block for position:fixed, so the toast stack would anchor to
     its wrapper instead of the viewport. */
  [data-testid="stElementContainer"]:has(.toast-stack),
  [data-testid="stVerticalBlockBorderWrapper"]:has(.toast-stack),
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .toast-stack) {{
    animation: none !important; filter: none !important; transform: none !important;
    backdrop-filter: none !important; -webkit-backdrop-filter: none !important;
  }}

  /* ---------- toasts ---------- */
  .toast-stack {{
    position: fixed; right: 18px; bottom: 18px; z-index: 9990;
    display: flex; flex-direction: column; gap: .45rem;
    width: 300px; max-width: calc(100vw - 36px); pointer-events: none;
  }}
  .toast-stack > * {{ pointer-events: auto; }}
  .toast-head {{
    align-self: flex-end; font-size: .68rem; font-weight: 600;
    letter-spacing: .05em; text-transform: uppercase; color: var(--ink-2);
    {blur_light}
    background: var(--panel-strong); border: 1px solid var(--edge);
    border-radius: 999px; padding: .22rem .62rem; box-shadow: var(--shadow);
  }}
  .toast-x {{ display: none; }}
  .toast {{
    display: flex; gap: .55rem; align-items: flex-start;
    border-left: 3px solid var(--red); border-radius: var(--r-sm);
    padding: .65rem .75rem; box-shadow: var(--shadow-hi), var(--rim);
    background: linear-gradient(180deg, var(--red-tint), var(--panel-strong));
    animation: toastIn .46s var(--ease) both;
  }}
  .toast.amber {{
    border-left-color: var(--amber);
    background: linear-gradient(180deg, var(--amber-tint), var(--panel-strong));
  }}
  .toast-x:checked + .toast {{ display: none; }}
  .toast-body {{ flex: 1; min-width: 0; }}
  .toast-title {{ font-size: .775rem; font-weight: 600; color: var(--ink); line-height: 1.3; margin-bottom: .1rem; }}
  .toast-text {{
    font-size: .715rem; color: var(--ink-2); line-height: 1.4;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  }}
  .toast-close {{
    cursor: pointer; color: var(--ink-3); font-size: .95rem; line-height: 1;
    padding: 0 .1rem; flex: 0 0 auto; user-select: none;
    transition: color .2s var(--ease);
  }}
  .toast-close:hover {{ color: var(--ink); }}
  @keyframes toastIn {{
    0%   {{ opacity: 0; transform: translateX(22px) translateZ(0); }}
    100% {{ opacity: 1; transform: translateZ(0); }}
  }}
  @media (max-width: 640px) {{
    .toast-stack {{ width: calc(100vw - 24px); right: 12px; bottom: 12px; gap: .35rem; }}
    .toast-text {{ -webkit-line-clamp: 1; }}
  }}

  /* ---------- tabs ---------- */
  [data-baseweb="tab-list"] {{
    gap: .2rem; border-bottom: none; padding: .28rem;
    margin-bottom: .65rem; overflow-x: auto; border-radius: 999px;
    width: fit-content; max-width: 100%;
  }}
  [data-baseweb="tab"] {{
    background: transparent !important; border-radius: 999px !important;
    padding: .44rem 1.05rem !important; font-size: .865rem; font-weight: 500;
    color: var(--ink-3); white-space: nowrap;
    transition: background .32s var(--ease), color .32s var(--ease);
  }}
  [data-baseweb="tab"]:hover {{ color: var(--ink); background: var(--hover) !important; }}
  [data-baseweb="tab"][aria-selected="true"] {{
    color: var(--on-accent) !important; font-weight: 600;
    background: linear-gradient(135deg, var(--blue), var(--violet)) !important;
  }}
  [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {{ display: none; }}

  /* ---------- controls ---------- */
  .stButton > button, .stDownloadButton > button, .stLinkButton > a {{
    border-radius: 999px !important; font-weight: 500;
    border: 1px solid var(--edge);
    {blur_light}
    background: var(--panel-strong); color: var(--ink) !important;
    transition: transform .28s var(--ease), background .28s var(--ease);
  }}
  .stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {{
    transform: translateY(-1px); background: var(--hover);
  }}
  .stButton > button:active {{ transform: scale(.978); }}
  [data-testid="stMain"] .stButton > button[kind="primary"],
  button[data-testid="stBaseButton-primary"] {{
    background: linear-gradient(135deg, var(--blue), var(--violet)) !important;
    border: none !important; color: var(--on-accent) !important; font-weight: 600;
  }}
  [data-testid="stMain"] .stButton > button[kind="primary"]:hover {{ filter: brightness(1.08); }}

  /* Streamlit paints widget interiors from the theme base in config.toml,
     which cannot change at runtime - and the painted node carries only a
     generated emotion class. So clear the interior and paint the wrapper. */
  [data-testid="stSelectbox"] > div, [data-testid="stMultiSelect"] > div,
  [data-testid="stDateInput"] > div, [data-testid="stNumberInput"] > div,
  [data-testid="stTextInput"] > div, [data-testid="stTextArea"] > div {{
    border-radius: var(--r-sm) !important;
    background: var(--panel-strong) !important;
    border: 1px solid var(--edge) !important;
    color: var(--ink) !important;
    {blur_light}
  }}
  [data-testid="stSelectbox"] > div *:not([data-baseweb="tag"]):not([data-baseweb="tag"] *),
  [data-testid="stMultiSelect"] > div *:not([data-baseweb="tag"]):not([data-baseweb="tag"] *),
  [data-testid="stDateInput"] > div *, [data-testid="stNumberInput"] > div *,
  [data-testid="stTextInput"] > div *, [data-testid="stTextArea"] > div * {{
    background-color: transparent !important;
    border-color: transparent !important;
    color: var(--ink) !important;
  }}
  [data-baseweb="tag"] {{
    background: linear-gradient(135deg, var(--blue), var(--violet)) !important;
    color: var(--on-accent) !important;
  }}
  [data-baseweb="tag"] span, [data-baseweb="tag"] svg {{ color: var(--on-accent) !important; }}
  .stTextInput input, .stNumberInput input, .stTextArea textarea,
  .stDateInput input {{ color: var(--ink) !important; }}
  input::placeholder, textarea::placeholder {{ color: var(--ink-3) !important; opacity: 1; }}
  [data-baseweb="popover"] [role="listbox"], [data-baseweb="menu"] {{
    background: var(--menu) !important; border: 1px solid var(--edge) !important;
  }}
  [role="option"] {{ color: var(--ink-2) !important; }}
  [role="option"]:hover {{ background: var(--hover) !important; }}

  [data-testid="stExpander"] {{ border-radius: var(--r) !important; overflow: hidden; }}
  [data-testid="stExpander"] summary {{ color: var(--ink) !important; }}
  [data-testid="stExpander"] summary:hover {{ background: var(--hover); }}
  [data-testid="stDataFrame"], [data-testid="stTable"] {{ border-radius: var(--r); overflow: hidden; }}
  [data-testid="stMetric"] {{ border-radius: var(--r); padding: .85rem 1rem; }}
  [data-testid="stMetricValue"] {{ color: var(--ink); }}
  [data-testid="stForm"] {{ border-radius: var(--r-lg) !important; padding: 1.2rem !important; }}

  [data-testid="stSegmentedControl"] button {{
    border-radius: 999px !important; font-weight: 500; font-size: .85rem;
    border-color: var(--edge) !important; background: var(--panel-strong) !important;
    color: var(--ink-2) !important;
  }}
  [data-testid="stSegmentedControl"] button[aria-checked="true"],
  [data-testid="stSegmentedControl"] button[aria-pressed="true"] {{
    background: linear-gradient(135deg, var(--blue), var(--violet)) !important;
    color: var(--on-accent) !important; border-color: transparent !important;
  }}

  /* ---------- version toggle ---------- */
  .flux-verbar {{ height: .35rem; }}
  [data-testid="stPopoverButton"] {{
    background: transparent !important; border: none !important;
    box-shadow: none !important; border-radius: 10px !important;
    padding: .24rem .45rem .24rem .3rem !important;
    font-size: 1.16rem !important; font-weight: 600 !important;
    letter-spacing: -.026em; color: var(--ink) !important;
    transition: background .25s var(--ease);
    -webkit-backdrop-filter: none !important; backdrop-filter: none !important;
  }}
  [data-testid="stPopoverButton"]:hover {{ background: var(--hover) !important; }}
  [data-testid="stPopoverButton"]:focus,
  [data-testid="stPopoverButton"]:active {{ box-shadow: none !important; border: none !important; }}
  [data-testid="stPopoverBody"] {{ padding: .45rem !important; min-width: 190px; border-radius: var(--r-sm) !important; }}
  [data-testid="stPopoverBody"] .stButton > button,
  [data-testid="stPopoverBody"] button[data-testid^="stBaseButton"] {{
    background: transparent !important; border: none !important;
    box-shadow: none !important; border-radius: 9px !important;
    backdrop-filter: none !important; -webkit-backdrop-filter: none !important;
    justify-content: flex-start !important; text-align: left !important;
    padding: .42rem .6rem !important; margin: 0 !important;
    font-size: .93rem !important; font-weight: 500 !important;
    color: var(--ink) !important; min-height: 0 !important;
  }}
  [data-testid="stPopoverBody"] .stButton > button:hover {{ background: var(--hover) !important; }}
  [data-testid="stPopoverBody"] .stButton > button p {{
    font-size: .93rem !important; font-weight: 500 !important;
    white-space: pre !important; color: var(--ink) !important;
  }}
  /* Streamlit centres the label in a nested flex wrapper inside the button,
     which overrides the button's own alignment - so unset it there too. */
  [data-testid="stPopoverBody"] .stButton > button > div,
  [data-testid="stPopoverBody"] .stButton > button > div > span {{
    justify-content: flex-start !important; width: 100% !important;
  }}
  [data-testid="stPopoverBody"] [data-testid="stVerticalBlock"] {{ gap: .1rem !important; }}
  .flux-ver-note {{ display: inline-block; font-size: .735rem; color: var(--ink-3); margin-top: .1rem; }}
  .flux-ver-pill {{
    display: inline-block; font-size: .68rem; font-weight: 600;
    padding: .14rem .48rem; border-radius: 999px; margin-left: .3rem;
    background: var(--green-tint); color: var(--green);
  }}

  /* ---------- sign-in ---------- */
  .signin-wrap {{
    display: flex; align-items: center; justify-content: center;
    min-height: 62vh; padding: 1rem 0;
  }}
  .signin-card {{
    width: 100%; max-width: 430px; text-align: center;
    border-radius: var(--r-lg); padding: 2.4rem 2rem 1.9rem;
    box-shadow: var(--shadow-hi), var(--rim);
    animation: liftIn .55s var(--ease) both;
  }}
  .signin-mark {{
    width: 62px; height: 62px; margin: 0 auto 1.15rem; border-radius: 19px;
    background: linear-gradient(140deg, var(--blue), var(--violet) 55%, var(--magenta));
    display: flex; align-items: center; justify-content: center;
    color: var(--on-accent); font-size: 1.45rem; font-weight: 700; letter-spacing: -.035em;
  }}
  .signin-title {{ font-size: 1.45rem; font-weight: 600; color: var(--ink);
                  letter-spacing: -.03em; margin-bottom: .45rem; }}
  .signin-sub {{ font-size: .9rem; color: var(--ink-2); line-height: 1.6;
                margin: 0 auto 1.4rem; max-width: 330px; }}
  .signin-foot {{ font-size: .775rem; color: var(--ink-3); margin-top: 1.15rem;
                 padding-top: 1rem; border-top: 1px solid var(--edge-soft); }}

  /* ---------- phones ---------- */
  @media (max-width: 640px) {{
    [data-testid="stMain"] .block-container {{
      padding-left: .75rem; padding-right: .75rem; padding-top: 3.4rem;
    }}
    .kpi-grid {{ grid-template-columns: repeat(auto-fit, minmax(146px, 1fr)); gap: .55rem; }}
    .kpi-card {{ padding: .8rem .85rem; border-radius: 16px; }}
    .kpi-value {{ font-size: 1.5rem; }}
    .kpi-head {{ margin-bottom: .65rem; }}
    .kpi-dot {{ width: 26px; height: 26px; flex: 0 0 26px; font-size: .72rem; }}
    .kpi-label {{ font-size: .765rem; }}
    [data-testid="stMain"] h1 {{ font-size: 1.72rem !important; }}
    [data-testid="stMain"] h3 {{ font-size: 1rem !important; }}
    [data-baseweb="tab"] {{ padding: .4rem .8rem !important; font-size: .82rem; }}
    .g-hero {{ padding: .95rem 1.05rem; border-radius: 20px; }}
    .flux-avatar {{ width: 38px; height: 38px; flex: 0 0 38px; font-size: .82rem; }}
    .signin-card {{ padding: 1.9rem 1.3rem 1.6rem; border-radius: 24px; }}
    /* Heavy blur is a mobile cost the article calls out. */
    :root {{ --blur: saturate(150%) blur(16px); --blur-dense: saturate(140%) blur(12px); }}
  }}

  @media (prefers-reduced-motion: reduce) {{
    *, [data-testid="stMain"] [data-testid="stElementContainer"],
    .kpi-card, .callout, .g-hero, .g-alert, .alert-mini, .toast,
    .signin-card, [data-baseweb="tab-panel"] {{
      animation: none !important; transition: none !important; filter: none !important;
    }}
  }}
</style>
"""


# Kept so `from theme import CSS` still resolves for anything importing it.
CSS = css()
