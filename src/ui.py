"""Shared UI: responsive KPI cards, chips, chart theming and exports.

KPI rows are rendered as a single HTML CSS-grid block rather than st.columns,
because st.columns squeezes on narrow screens instead of wrapping. The grid
reflows to one or two cards per row on a phone and four to six on a laptop.
"""
from __future__ import annotations

import html
import io
from datetime import datetime
from typing import Any, Iterable, Sequence

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from settings_store import grade

SEVERITY_ORDER = {"red": 0, "amber": 1, "ok": 2, "neutral": 3}

CHART_COLORWAY = [
    "#0F766E", "#2563EB", "#D97706", "#DC2626", "#7C3AED",
    "#0891B2", "#65A30D", "#DB2777", "#475569", "#B45309",
]

BASE_CSS = """
<style>
  /* ---- layout ---- */
  .block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1500px; }
  footer, #MainMenu { visibility: hidden; }
  h1, h2, h3 { letter-spacing: -0.01em; }

  /* ---- KPI grid: wraps on mobile, spreads on desktop ---- */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(168px, 1fr));
    gap: 0.65rem;
    margin: 0.35rem 0 1.1rem 0;
  }
  .kpi-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-left: 4px solid var(--accent, #64748B);
    border-radius: 10px;
    padding: 0.7rem 0.85rem;
    box-shadow: 0 1px 2px rgba(15,23,42,0.04);
    min-width: 0;
  }
  .kpi-label {
    font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.04em; color: #64748B; margin-bottom: 0.28rem;
    line-height: 1.25; overflow-wrap: break-word;
  }
  .kpi-value {
    font-size: 1.5rem; font-weight: 700; line-height: 1.15;
    color: var(--accent, #0F172A); overflow-wrap: break-word;
  }
  .kpi-sub { font-size: 0.74rem; color: #64748B; margin-top: 0.2rem; line-height: 1.3; }
  .kpi-delta { font-size: 0.76rem; font-weight: 600; margin-top: 0.22rem; }
  .kpi-delta.up { color: #059669; }
  .kpi-delta.down { color: #DC2626; }
  .kpi-delta.flat { color: #64748B; }

  /* ---- chips ---- */
  .chip {
    display: inline-block; padding: 0.16rem 0.55rem; border-radius: 999px;
    font-size: 0.73rem; font-weight: 600; margin: 0.12rem 0.25rem 0.12rem 0;
    border: 1px solid transparent; white-space: nowrap;
  }
  .chip-red   { background: #FEF2F2; color: #B91C1C; border-color: #FECACA; }
  .chip-amber { background: #FFFBEB; color: #B45309; border-color: #FDE68A; }
  .chip-green { background: #ECFDF5; color: #047857; border-color: #A7F3D0; }
  .chip-grey  { background: #F1F5F9; color: #475569; border-color: #E2E8F0; }

  /* ---- callout ---- */
  .callout {
    border-radius: 10px; padding: 0.7rem 0.9rem; margin: 0.3rem 0 0.9rem 0;
    font-size: 0.88rem; border: 1px solid #E2E8F0; background: #F8FAFC;
  }
  .callout.red   { background: #FEF2F2; border-color: #FECACA; }
  .callout.amber { background: #FFFBEB; border-color: #FDE68A; }
  .callout.green { background: #ECFDF5; border-color: #A7F3D0; }
  .callout ul { margin: 0.3rem 0 0 1.1rem; padding: 0; }
  .callout li { margin: 0.16rem 0; }

  .section-note { color: #64748B; font-size: 0.85rem; margin: -0.35rem 0 0.75rem 0; }
  .src-note { color: #94A3B8; font-size: 0.76rem; margin-top: 0.4rem; }

  /* ---- phones ---- */
  @media (max-width: 640px) {
    .block-container { padding-left: 0.75rem; padding-right: 0.75rem; padding-top: 0.9rem; }
    .kpi-grid { grid-template-columns: repeat(auto-fit, minmax(132px, 1fr)); gap: 0.5rem; }
    .kpi-card { padding: 0.55rem 0.6rem; border-radius: 8px; }
    .kpi-value { font-size: 1.18rem; }
    .kpi-label { font-size: 0.66rem; }
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.15rem !important; }
    h3 { font-size: 1rem !important; }
    div[data-testid="stMetricValue"] { font-size: 1.1rem; }
  }
</style>
"""


def inject_css() -> None:
    st.markdown(BASE_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------
def fmt_int(value: Any) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "-"
    return f"{int(round(float(value))):,}"


def fmt_money(value: Any, symbol: str = "Rs", compact: bool = False) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "-"
    num = float(value)
    if compact and abs(num) >= 100000:
        return f"{symbol} {num / 100000:.2f}L"
    if compact and abs(num) >= 1000:
        return f"{symbol} {num / 1000:.1f}k"
    return f"{symbol} {num:,.0f}"


def fmt_pct(value: Any, digits: int = 1) -> str:
    if value is None or (isinstance(value, float) and value != value):
        return "-"
    return f"{float(value):.{digits}f}%"


def fmt_value(value: Any, unit: str, symbol: str = "Rs", compact: bool = True) -> str:
    if unit == "%":
        return fmt_pct(value)
    if unit in ("Rs", "money"):
        return fmt_money(value, symbol, compact=compact)
    return fmt_int(value)


# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------
def kpi(
    label: str,
    value: Any,
    *,
    unit: str = "n",
    kpi_key: str | None = None,
    config: dict | None = None,
    sub: str | None = None,
    delta: float | None = None,
    delta_unit: str | None = None,
    higher_is_better: bool | None = None,
    tone: str | None = None,
    help_text: str | None = None,
) -> dict:
    """Build one KPI card spec. `kpi_key` pulls its colour band from config."""
    severity = tone or "neutral"
    spec: dict = {}
    if kpi_key and config:
        spec = config.get("kpis", {}).get(kpi_key, {}) or {}
        if spec:
            severity = grade(value, spec)
            unit = spec.get("unit", unit)
            label = label or spec.get("label", kpi_key)
            help_text = help_text or spec.get("help")
    return {
        "label": label,
        "value": value,
        "unit": unit,
        "sub": sub,
        "delta": delta,
        "delta_unit": delta_unit or unit,
        "higher_is_better": higher_is_better,
        "severity": severity,
        "help": help_text,
        "band": _band_text(spec),
    }


def _band_text(spec: dict) -> str:
    if not spec:
        return ""
    mode = spec.get("mode")
    unit = spec.get("unit", "")
    suffix = "%" if unit == "%" else ""
    if mode == "higher_better":
        return f"green >= {spec.get('green')}{suffix}, amber >= {spec.get('amber')}{suffix}"
    if mode == "lower_better":
        return f"green <= {spec.get('green')}{suffix}, amber <= {spec.get('amber')}{suffix}"
    if mode == "between":
        return f"green {spec.get('min')}{suffix} - {spec.get('max')}{suffix} (slack {spec.get('slack')})"
    return ""


def _colour(severity: str, display: dict) -> str:
    return {
        "red": display.get("red_hex", "#DC2626"),
        "amber": display.get("amber_hex", "#D97706"),
        "green": display.get("green_hex", "#059669"),
    }.get(severity, display.get("neutral_hex", "#64748B"))


def render_kpis(cards: Sequence[dict], config: dict | None = None) -> None:
    """Render a wrapping grid of KPI cards as one HTML block."""
    display = (config or {}).get("display", {})
    symbol = display.get("currency_symbol", "Rs")
    parts: list[str] = ['<div class="kpi-grid">']

    for card in cards:
        if card is None:
            continue
        accent = _colour(card.get("severity", "neutral"), display)
        value_txt = html.escape(
            fmt_value(card.get("value"), card.get("unit", "n"), symbol)
        )
        tip_bits = [t for t in (card.get("help"), card.get("band")) if t]
        tip = html.escape(" | ".join(tip_bits)) if tip_bits else ""

        block = [
            f'<div class="kpi-card" style="--accent:{accent}"'
            + (f' title="{tip}"' if tip else "")
            + ">",
            f'<div class="kpi-label">{html.escape(str(card.get("label", "")))}</div>',
            f'<div class="kpi-value">{value_txt}</div>',
        ]

        delta = card.get("delta")
        if delta is not None and delta == delta:
            better = card.get("higher_is_better")
            if better is None:
                trend = "flat"
            elif (delta > 0 and better) or (delta < 0 and not better):
                trend = "up"
            elif delta == 0:
                trend = "flat"
            else:
                trend = "down"
            arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "→")
            dtxt = fmt_value(abs(delta), card.get("delta_unit", "n"), symbol)
            block.append(
                f'<div class="kpi-delta {trend}">{arrow} {html.escape(dtxt)}</div>'
            )

        if card.get("sub"):
            block.append(
                f'<div class="kpi-sub">{html.escape(str(card["sub"]))}</div>'
            )
        block.append("</div>")
        parts.append("".join(block))

    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def chips(items: Iterable[tuple[str, str]]) -> None:
    """items: (text, tone) where tone is red / amber / green / grey."""
    spans = [
        f'<span class="chip chip-{tone}">{html.escape(str(text))}</span>'
        for text, tone in items
    ]
    if spans:
        st.markdown("".join(spans), unsafe_allow_html=True)


def callout(lines: Sequence[str], tone: str = "grey", title: str | None = None) -> None:
    if not lines:
        return
    body = "".join(f"<li>{line}</li>" for line in lines)
    head = f"<strong>{html.escape(title)}</strong>" if title else ""
    st.markdown(
        f'<div class="callout {tone}">{head}<ul>{body}</ul></div>',
        unsafe_allow_html=True,
    )


def note(text: str) -> None:
    st.markdown(f'<div class="section-note">{html.escape(text)}</div>',
                unsafe_allow_html=True)


def source_note(text: str) -> None:
    st.markdown(f'<div class="src-note">{html.escape(text)}</div>',
                unsafe_allow_html=True)


def section(title: str, description: str | None = None) -> None:
    st.markdown(f"### {title}")
    if description:
        note(description)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def style_chart(fig: go.Figure, height: int = 320, legend: bool = True) -> go.Figure:
    """A title and a top legend would overlap, so reserve room for both."""
    has_title = bool(getattr(fig.layout.title, "text", None))
    top_margin = 62 if (has_title and legend) else (40 if has_title else 28)

    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=top_margin, b=8),
        colorway=CHART_COLORWAY,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12, color="#0F172A"),
        showlegend=legend,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.0,
            xanchor="left", x=0, title_text="",
        ),
        hovermode="x unified",
        dragmode=False,
    )
    if has_title:
        fig.update_layout(
            title=dict(
                x=0, xanchor="left", y=1, yanchor="top",
                font=dict(size=13.5), pad=dict(t=2, b=10),
            )
        )
    fig.update_xaxes(showgrid=False, linecolor="#E2E8F0")
    fig.update_yaxes(gridcolor="#F1F5F9", zerolinecolor="#E2E8F0")
    return fig


def show_chart(fig: go.Figure, height: int = 320, legend: bool = True) -> None:
    st.plotly_chart(
        style_chart(fig, height, legend),
        width="stretch",
        config={"displayModeBar": False, "scrollZoom": False, "responsive": True},
    )


def threshold_bands(
    fig: go.Figure, spec: dict, display: dict, values: Any = None
) -> go.Figure:
    """Shade the green window of a KPI behind its trend line.

    A shape drawn to +/-1e6 would hijack the y-axis autorange, so the band is
    clamped to the plotted data's own range and the axis is pinned to match.
    """
    if not spec:
        return fig
    mode = spec.get("mode")
    green_hex = display.get("green_hex", "#059669")

    marks = [
        float(spec[k]) for k in ("green", "amber", "min", "max")
        if spec.get(k) is not None
    ]
    series = pd.to_numeric(pd.Series(values), errors="coerce").dropna() \
        if values is not None else pd.Series(dtype=float)
    points = list(series) + marks
    if not points:
        return fig

    low, high = min(points), max(points)
    pad = max((high - low) * 0.12, 2.0)
    axis_low = 0.0 if low >= 0 else low - pad
    axis_high = high + pad

    kwargs = dict(fillcolor=green_hex, opacity=0.07, line_width=0, layer="below")
    if mode == "higher_better":
        fig.add_hrect(y0=float(spec["green"]), y1=axis_high, **kwargs)
    elif mode == "lower_better":
        fig.add_hrect(y0=axis_low, y1=float(spec["green"]), **kwargs)
    elif mode == "between":
        fig.add_hrect(y0=float(spec["min"]), y1=float(spec["max"]), **kwargs)
    fig.update_yaxes(range=[axis_low, axis_high])
    return fig


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------
def severity_styler(df: pd.DataFrame, column: str = "severity"):
    """Tint whole rows by severity for the exceptions tables."""
    tints = {"red": "#FEF2F2", "amber": "#FFFBEB", "ok": "#F8FAFC", "green": "#ECFDF5"}

    def paint(row: pd.Series):
        colour = tints.get(str(row.get(column, "")).lower(), "")
        return [f"background-color: {colour}" if colour else ""] * len(row)

    return df.style.apply(paint, axis=1)


def grade_styler(df: pd.DataFrame, columns: dict[str, str], config: dict):
    """Colour named numeric columns by their KPI band. columns: {col: kpi_key}."""
    display = config.get("display", {})
    specs = config.get("kpis", {})

    def paint(series: pd.Series):
        spec = specs.get(columns.get(series.name, ""), {})
        if not spec:
            return [""] * len(series)
        out = []
        for val in series:
            sev = grade(val, spec)
            out.append(
                f"color: {_colour(sev, display)}; font-weight: 600"
                if sev != "neutral" else ""
            )
        return out

    present = [c for c in columns if c in df.columns]
    return df.style.apply(paint, subset=present) if present else df.style


def show_table(df: pd.DataFrame, height: int | None = None, **kwargs) -> None:
    """Streamlit rejects an explicit height=None, so only pass it when set."""
    if height is not None:
        kwargs["height"] = height
    st.dataframe(df, width="stretch", hide_index=True, **kwargs)


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes | None:
    """One workbook, one sheet per frame. Tries xlsxwriter, then openpyxl."""
    for engine in ("xlsxwriter", "openpyxl"):
        buffer = io.BytesIO()
        try:
            with pd.ExcelWriter(buffer, engine=engine) as writer:
                for name, frame in sheets.items():
                    if frame is None or frame.empty:
                        continue
                    safe = str(name)[:31].replace("/", "-").replace("\\", "-")
                    out = frame.copy()
                    for col in out.columns:
                        if pd.api.types.is_datetime64_any_dtype(out[col]):
                            out[col] = out[col].dt.strftime("%Y-%m-%d")
                    out.to_excel(writer, sheet_name=safe or "Sheet1", index=False)
            return buffer.getvalue()
        except (ImportError, ModuleNotFoundError):
            continue
        except Exception:
            return None
    return None


def download_row(
    csv_frames: dict[str, pd.DataFrame],
    excel_name: str | None = None,
    key_prefix: str = "dl",
) -> None:
    """A CSV button per frame plus one combined Excel workbook."""
    frames = {n: f for n, f in csv_frames.items() if f is not None and not f.empty}
    if not frames:
        return
    stamp = datetime.now().strftime("%Y%m%d")
    buttons = list(frames.items())
    workbook = excel_bytes(frames) if excel_name else None
    columns = st.columns(len(buttons) + (1 if workbook else 0))

    for col, (name, frame) in zip(columns, buttons):
        slug = name.lower().replace(" ", "-")
        col.download_button(
            f"CSV: {name}",
            data=csv_bytes(frame),
            file_name=f"neodrift-{slug}-{stamp}.csv",
            mime="text/csv",
            width="stretch",
            key=f"{key_prefix}-{slug}",
        )
    if workbook:
        columns[-1].download_button(
            "Excel workbook",
            data=workbook,
            file_name=f"neodrift-{excel_name}-{stamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
            key=f"{key_prefix}-xlsx",
        )


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------
def month_options(months: Sequence[str]) -> dict[str, str]:
    """{'September 2026': '2026-09'} newest first, for the month picker."""
    out: dict[str, str] = {}
    for ym in months:
        try:
            label = datetime.strptime(ym, "%Y-%m").strftime("%B %Y")
        except ValueError:
            label = ym
        out[label] = ym
    return out


def delta_of(current: Any, previous: Any) -> float | None:
    try:
        if current is None or previous is None:
            return None
        cur, prev = float(current), float(previous)
        if cur != cur or prev != prev:
            return None
        return round(cur - prev, 2)
    except (TypeError, ValueError):
        return None


def empty_state(message: str) -> None:
    st.info(message, icon=":material/info:")
