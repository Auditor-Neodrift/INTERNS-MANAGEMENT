"""Settings: edit the green/amber/red bands, the audit rules and their limits.

Changes apply immediately across every page. Save writes
config/thresholds.json; on Streamlit Cloud that file is wiped when the app
restarts, so the download/commit route is the way to make settings permanent.
"""
from __future__ import annotations

import json
import pathlib

import pandas as pd
import streamlit as st

import audit
import data as data_mod
import theme as theme_mod
import settings_store
import ui
from settings_store import grade

MODE_LABELS = {
    "higher_better": "Higher is better",
    "lower_better": "Lower is better",
    "between": "Must stay between",
}
MODE_KEYS = {v: k for k, v in MODE_LABELS.items()}

# Widget keys this page owns. Replacing the whole config has to clear these
# too, or a still-mounted widget would write its old value straight back.
WIDGET_PREFIXES = (
    "mode_", "min_", "max_", "slack_", "green_", "amber_",
    "on_", "sev_", "param_", "c_", "d_", "set_", "bg_up_",
)


def _clear_widget_state() -> None:
    for key in [
        k for k in list(st.session_state.keys())
        if isinstance(k, str) and k.startswith(WIDGET_PREFIXES)
    ]:
        del st.session_state[key]


def _flash(message: str, kind: str = "success") -> None:
    """Survive the st.rerun that follows a config swap."""
    st.session_state["_settings_flash"] = (kind, message)


def _show_flash() -> None:
    flash = st.session_state.pop("_settings_flash", None)
    if not flash:
        return
    kind, message = flash
    {"success": st.success, "error": st.error, "info": st.info}.get(
        kind, st.info
    )(message)


def render(bundle, config: dict) -> None:
    st.title("Settings")
    ui.note(
        "Everything here drives the colours and the audit rules on every other "
        "page. Edits apply as soon as you change them."
    )
    _show_flash()

    tabs = st.tabs([
        "KPI limits (green / amber / red)",
        "Audit rules",
        "Display & data",
        "Save, load, reset",
    ])

    with tabs[0]:
        _kpi_tab(config)
    with tabs[1]:
        _rules_tab(bundle, config)
    with tabs[2]:
        _display_tab(config)
    with tabs[3]:
        _persistence_tab(config)


# ---------------------------------------------------------------------------
# KPI bands
# ---------------------------------------------------------------------------
def _kpi_tab(config: dict) -> None:
    ui.section(
        "How each KPI is coloured",
        "Pick the direction, then set the limits. 'Must stay between' also takes "
        "a slack value: inside the window is green, within slack of it is amber, "
        "beyond that is red.",
    )
    kpis = config["kpis"]
    symbol = config.get("display", {}).get("currency_symbol", "Rs")

    percent_keys = [k for k, s in kpis.items() if s.get("unit") == "%"]
    money_keys = [k for k, s in kpis.items() if s.get("unit") in ("Rs", "money")]
    other_keys = [k for k in kpis if k not in percent_keys and k not in money_keys]

    for title, keys in (
        ("Percentage KPIs", percent_keys),
        (f"Money KPIs ({symbol})", money_keys),
        ("Other KPIs", other_keys),
    ):
        if not keys:
            continue
        st.markdown(f"#### {title}")
        for key in keys:
            _kpi_editor(key, kpis[key], config)

    ui.section("Preview", "How the current limits colour a sample of values.")
    _preview(config)


def _kpi_editor(key: str, spec: dict, config: dict) -> None:
    unit = spec.get("unit", "n")
    step = 1.0 if unit == "%" else (500.0 if unit in ("Rs", "money") else 1.0)
    fmt = "%.1f" if unit == "%" else "%.0f"

    with st.expander(f"{spec.get('label', key)}  ({unit})"):
        if spec.get("help"):
            st.caption(spec["help"])

        mode_label = st.selectbox(
            "Direction", list(MODE_LABELS.values()),
            index=list(MODE_LABELS.keys()).index(spec.get("mode", "higher_better")),
            key=f"mode_{key}",
        )
        spec["mode"] = MODE_KEYS[mode_label]

        if spec["mode"] == "between":
            col_a, col_b, col_c = st.columns(3)
            spec["min"] = col_a.number_input(
                "Minimum (green from)", value=float(spec.get("min", 0.0)),
                step=step, format=fmt, key=f"min_{key}",
            )
            spec["max"] = col_b.number_input(
                "Maximum (green to)", value=float(spec.get("max", 100.0)),
                step=step, format=fmt, key=f"max_{key}",
            )
            spec["slack"] = col_c.number_input(
                "Amber slack either side", value=float(spec.get("slack", 0.0)),
                min_value=0.0, step=step, format=fmt, key=f"slack_{key}",
            )
            if spec["min"] > spec["max"]:
                st.warning("Minimum is above maximum, so nothing can be green.",
                           icon=":material/warning:")
        else:
            higher = spec["mode"] == "higher_better"
            col_a, col_b = st.columns(2)
            spec["green"] = col_a.number_input(
                "Green at or above" if higher else "Green at or below",
                value=float(spec.get("green", 0.0)), step=step, format=fmt,
                key=f"green_{key}",
            )
            spec["amber"] = col_b.number_input(
                "Amber at or above" if higher else "Amber at or below",
                value=float(spec.get("amber", 0.0)), step=step, format=fmt,
                key=f"amber_{key}",
            )
            if higher and spec["amber"] > spec["green"]:
                st.warning(
                    "For a higher-is-better KPI the amber limit should sit below "
                    "the green one.", icon=":material/warning:",
                )
            if not higher and spec["amber"] < spec["green"]:
                st.warning(
                    "For a lower-is-better KPI the amber limit should sit above "
                    "the green one.", icon=":material/warning:",
                )

        sample = _sample_values(spec)
        ui.chips([
            (ui.fmt_value(v, unit, config.get("display", {}).get("currency_symbol", "Rs")),
             _tone(grade(v, spec)))
            for v in sample
        ])


def _sample_values(spec: dict) -> list[float]:
    if spec.get("mode") == "between":
        lo, hi = float(spec.get("min", 0)), float(spec.get("max", 100))
        slack = float(spec.get("slack", 0))
        span = max(hi - lo, 1)
        return [lo - slack - span * 0.2, lo - slack * 0.5, (lo + hi) / 2,
                hi + slack * 0.5, hi + slack + span * 0.2]
    green, amber = float(spec.get("green", 0)), float(spec.get("amber", 0))
    spread = max(abs(green - amber), max(abs(green), 1) * 0.25)
    if spec.get("mode") == "higher_better":
        return [amber - spread, amber, (amber + green) / 2, green, green + spread]
    return [green - spread, green, (green + amber) / 2, amber, amber + spread]


def _tone(severity: str) -> str:
    return {"green": "green", "amber": "amber", "red": "red"}.get(severity, "grey")


def _preview(config: dict) -> None:
    rows = []
    for key, spec in config["kpis"].items():
        unit = spec.get("unit", "n")
        symbol = config.get("display", {}).get("currency_symbol", "Rs")
        cells = {
            "KPI": spec.get("label", key),
            "Direction": MODE_LABELS.get(spec.get("mode", ""), ""),
            "Limits": ui._band_text(spec),
        }
        for idx, value in enumerate(_sample_values(spec)):
            cells[f"Sample {idx + 1}"] = (
                f"{ui.fmt_value(value, unit, symbol)} "
                f"({grade(value, spec).upper()})"
            )
        rows.append(cells)
    ui.show_table(pd.DataFrame(rows), height=420)


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------
PARAM_LABELS = {
    "days": "Days allowed before it is flagged",
    "min": "Minimum allowed",
    "max": "Maximum allowed",
    "tolerance": "Allowed difference",
    "grace_days": "Grace period in days",
}


def _rules_tab(bundle, config: dict) -> None:
    ui.section(
        "Row-level validation rules",
        "Switch a rule off, change red to amber, or move its limit. The counts "
        "below refresh as you edit.",
    )
    rules = config["rules"]
    findings, _ = common_audit(bundle, config)
    counts = (
        findings["rule_id"].value_counts() if not findings.empty else pd.Series(dtype=int)
    )

    groups: dict[str, list[str]] = {}
    for key, spec in rules.items():
        groups.setdefault(spec.get("group", "Other"), []).append(key)

    for group in sorted(groups):
        st.markdown(f"#### {group}")
        for key in groups[group]:
            _rule_editor(key, rules[key], int(counts.get(key, 0)))

    ui.section("Current rule set")
    summary = audit.rule_summary(findings, config)
    if not summary.empty:
        view = summary.copy()
        view["On"] = view["enabled"].map({True: "yes", False: "no"})
        ui.show_table(
            view.rename(columns={
                "rule": "Rule", "group": "Area", "severity": "Severity",
                "rows_flagged": "Rows flagged", "limit": "Limit",
            })[["Rule", "Area", "Severity", "On", "Rows flagged", "Limit"]]
        )


def common_audit(bundle, config: dict):
    """Local import to avoid a circular import at module load."""
    import common
    return common.audit_results(bundle, config)


def _rule_editor(key: str, spec: dict, hits: int) -> None:
    severity = str(spec.get("severity", "amber")).lower()
    badge = "RED" if severity == "red" else "WARN"
    state = "" if spec.get("enabled", True) else "  [off]"
    with st.expander(f"[{badge}] {spec.get('label', key)} — {hits} rows{state}"):
        if spec.get("help"):
            st.caption(spec["help"])
        col_a, col_b = st.columns([1, 1])
        spec["enabled"] = col_a.toggle(
            "Rule is on", value=bool(spec.get("enabled", True)), key=f"on_{key}"
        )
        spec["severity"] = col_b.radio(
            "Severity", ["red", "amber"],
            index=0 if severity == "red" else 1,
            horizontal=True, key=f"sev_{key}",
        )
        params = spec.get("params", {}) or {}
        if params:
            columns = st.columns(len(params))
            for column, (name, value) in zip(columns, list(params.items())):
                params[name] = column.number_input(
                    PARAM_LABELS.get(name, name),
                    value=float(value), min_value=0.0,
                    step=1.0 if "days" in name else 25.0,
                    format="%.0f", key=f"param_{key}_{name}",
                )
            spec["params"] = params


# ---------------------------------------------------------------------------
# Display & data
# ---------------------------------------------------------------------------
def _display_tab(config: dict) -> None:
    display = config["display"]

    ui.section(
        "Theme and background",
        "The same switch sits in the top-right corner of every page. Glass "
        "themes blur whatever is behind them; the flat themes are solid.",
    )
    current = display.get("theme", theme_mod.DEFAULT_THEME)
    picked = st.segmented_control(
        "Theme", theme_mod.THEME_ORDER,
        format_func=lambda k: theme_mod.THEME_LABELS[k],
        default=current, key="set_theme",
    )
    if picked:
        display["theme"] = picked

    col_dark, col_light = st.columns(2)
    with col_dark:
        _bg_controls("dark", display, "Dark theme background",
                     "app/static/bg.jpg or https://...",
                     "Used by Dark - Glass. Leave empty for a plain gradient.",
                     theme_mod.DEFAULT_DARK_BG)
    with col_light:
        _bg_controls("light", display, "Light theme background",
                     "app/static/bg-light.jpg or https://...",
                     "Used by Light - Glass. Leave empty for a plain gradient.",
                     theme_mod.DEFAULT_LIGHT_BG)

    ui.callout(
        [
            "Whatever image you set, a scrim sits between it and the panels, so "
            "text contrast stays inside a tested range - a very bright or very "
            "dark photo cannot make the interface unreadable.",
            "Uploads are written to <code>static/</code>. That folder survives a "
            "local restart but is wiped when Streamlit Cloud redeploys, so for a "
            "permanent background commit the file to the repo or paste a URL.",
            "<strong>Known limit:</strong> data tables are drawn on a canvas by "
            "Streamlit using the base theme in <code>config.toml</code>, which "
            "cannot change at runtime. It is set to dark, so tables look right "
            "in both dark themes and stay dark under the light ones.",
        ],
        "grey",
    )

    ui.section("Colours")
    col_a, col_b, col_c, col_d = st.columns(4)
    display["green_hex"] = col_a.color_picker(
        "Green", value=display.get("green_hex", "#059669"), key="c_green")
    display["amber_hex"] = col_b.color_picker(
        "Amber", value=display.get("amber_hex", "#FBBF24"), key="c_amber")
    display["red_hex"] = col_c.color_picker(
        "Red", value=display.get("red_hex", "#FB7185"), key="c_red")
    display["neutral_hex"] = col_d.color_picker(
        "Neutral", value=display.get("neutral_hex", "#64748B"), key="c_neutral")
    ui.chips([("Green sample", "green"), ("Amber sample", "amber"),
              ("Red sample", "red"), ("Neutral sample", "grey")])

    ui.section("Data behaviour")
    col_a, col_b, col_c = st.columns(3)
    display["cache_ttl_minutes"] = col_a.number_input(
        "Re-read the sheet after (minutes)",
        value=int(display.get("cache_ttl_minutes", 10)),
        min_value=1, max_value=240, step=1, key="d_ttl",
        help="How long a pull is reused before the app fetches the sheet again.",
    )
    display["week_days"] = col_b.number_input(
        "Days in the 'last week' window",
        value=int(display.get("week_days", 7)),
        min_value=1, max_value=60, step=1, key="d_week",
    )
    display["intern_min_orders_for_grading"] = col_c.number_input(
        "Minimum orders before an intern is graded",
        value=int(display.get("intern_min_orders_for_grading", 5)),
        min_value=1, max_value=100, step=1, key="d_minorders",
    )
    col_d, col_e, col_f = st.columns(3)
    display["tenure_days"] = col_d.number_input(
        "Intern tenure window (days)",
        value=int(display.get("tenure_days", 30)),
        min_value=1, max_value=365, step=1, key="d_tenure",
        help="An active intern past this many days since joining raises a tenure review reminder.",
    )
    display["intern_idle_days"] = col_e.number_input(
        "Alert if active with no orders after (days)",
        value=int(display.get("intern_idle_days", 3)),
        min_value=1, max_value=90, step=1, key="d_idle",
        help="An active intern who has been on the roster longer than this with zero orders is flagged.",
    )
    display["intern_cancel_alert_pct"] = col_f.number_input(
        "Alert if not-delivered rate exceeds (%)",
        value=float(display.get("intern_cancel_alert_pct", 30.0)),
        min_value=1.0, max_value=100.0, step=5.0, format="%.0f", key="d_cancelpct",
        help="Cancelled plus undelivered, over total orders, for an active intern.",
    )
    display["currency_symbol"] = st.text_input(
        "Currency label", value=display.get("currency_symbol", "Rs"),
        max_chars=4, key="d_symbol",
    )

    ui.section("Source workbook")
    st.code(data_mod.sheet_id(), language=None)
    st.caption(
        "To point the app at a different workbook, set `SHEET_ID` in "
        "`.streamlit/secrets.toml` (or the `INTERNS_SHEET_ID` environment "
        "variable) and restart. The workbook must be shared as "
        "'Anyone with the link - Viewer'."
    )
    st.link_button("Open the workbook", data_mod.sheet_url())
    if st.button("Clear the cache and re-read now", icon=":material/refresh:"):
        st.cache_data.clear()
        st.rerun()


def _bg_controls(mode: str, display: dict, label: str, placeholder: str,
                 help_text: str, default: str) -> None:
    """Path field plus an optional upload, for one theme mode.

    The uploader is rendered *before* the text field on purpose. Writing to a
    widget's session_state key after that widget has been instantiated in the
    same run raises StreamlitWidgetAlreadyInstantiatedError, so the upload has
    to seed the field's state before the field exists.
    """
    key, done_key = f"set_bg_{mode}", f"_bg_saved_{mode}"
    if key not in st.session_state:
        st.session_state[key] = display.get(f"bg_{mode}", default)

    upload = st.file_uploader(
        f"Upload a {mode} background", type=["jpg", "jpeg", "png", "webp"],
        key=f"bg_up_{mode}", label_visibility="collapsed",
    )
    if upload is not None:
        # The uploader keeps returning the same file on every rerun, so the
        # write is keyed on its identity to avoid a rerun loop.
        signature = f"{upload.name}:{upload.size}"
        if st.session_state.get(done_key) != signature:
            saved = _save_background(upload, mode)
            if saved:
                display[f"bg_{mode}"] = saved
                st.session_state[key] = saved
                st.session_state[done_key] = signature
                _flash(f"Background saved as {saved.rsplit('/', 1)[-1]}.")
                st.rerun()

    value = st.text_input(label, key=key, placeholder=placeholder, help=help_text)
    display[f"bg_{mode}"] = value


def _save_background(upload, mode: str) -> str | None:
    """Write an uploaded image into static/ and return its app-relative path."""
    static = pathlib.Path(__file__).resolve().parent.parent / "static"
    suffix = pathlib.Path(upload.name).suffix.lower() or ".jpg"
    if suffix not in (".jpg", ".jpeg", ".png", ".webp"):
        st.error("Use a JPG, PNG or WebP image.")
        return None
    target = static / f"bg-{mode}{suffix}"
    try:
        static.mkdir(parents=True, exist_ok=True)
        target.write_bytes(upload.getvalue())
    except OSError as exc:
        st.error(f"Could not save the image: {exc}")
        return None
    # Bust the browser cache so a replaced file is actually re-fetched.
    return f"app/static/{target.name}?v={target.stat().st_mtime_ns}"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _persistence_tab(config: dict) -> None:
    ui.section("Save your configuration")
    st.markdown(
        "Edits are live for this session already. Saving writes "
        f"`{settings_store.CONFIG_PATH.name}` so they survive a restart."
    )
    ui.callout(
        [
            "On Streamlit Community Cloud the filesystem resets whenever the app "
            "restarts, so a save there is temporary.",
            "To make settings permanent, use <strong>Download</strong> below and commit "
            "the file to your repository at <code>config/thresholds.json</code>.",
        ],
        "amber",
        title="Deploying on Streamlit Cloud",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Save to config/thresholds.json", type="primary",
                     width="stretch", icon=":material/save:"):
            ok, detail = settings_store.save_config(config)
            if ok:
                st.success(f"Saved to {detail}")
            else:
                st.error(f"Could not save: {detail}")
    with col_b:
        st.download_button(
            "Download thresholds.json",
            data=json.dumps(config, indent=2).encode("utf-8"),
            file_name="thresholds.json",
            mime="application/json",
            width="stretch",
            icon=":material/download:",
        )

    ui.section("Load a configuration")
    uploaded = st.file_uploader("Upload a thresholds.json", type=["json"],
                                key="cfg_upload")
    if uploaded is not None and st.button("Apply the uploaded file",
                                         width="stretch"):
        try:
            new_config = settings_store.config_from_json(
                uploaded.getvalue().decode("utf-8")
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            st.error(f"That file could not be read: {exc}")
        else:
            _clear_widget_state()
            st.session_state["config"] = new_config
            _flash("Configuration applied from the uploaded file.")
            st.rerun()

    ui.section("Reset")
    st.caption("Puts every limit and rule back to the shipped defaults.")
    if st.button("Reset to defaults", width="stretch",
                 icon=":material/restart_alt:"):
        _clear_widget_state()
        st.session_state["config"] = settings_store.default_config()
        _flash("Every limit and rule is back to the shipped defaults.")
        st.rerun()

    with st.expander("Show the current configuration as JSON"):
        st.json(config, expanded=False)
