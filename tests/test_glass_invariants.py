"""Guards for the one CSS trap that keeps breaking the glass.

An element with any `filter` value - `blur(0px)` included - becomes a
*backdrop root*. Every descendant's `backdrop-filter` then samples inside that
ancestor rather than the page behind it, so the frost silently turns into a
flat tint. The same rule also makes the element a containing block, which
un-fixes `position: fixed` descendants.

This has broken the toast stack, the theme dock, and then every card on the
page. These tests fail the build rather than let it happen a fourth time.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import theme as theme_mod  # noqa: E402

# Streamlit's own layout wrappers. Glass panels always live inside these, so a
# filter on any of them is a backdrop root sitting between the glass and the
# page it is meant to be sampling.
LAYOUT_WRAPPERS = (
    'data-testid="stApp"',
    'data-testid="stMain"',
    'data-testid="stElementContainer"',
    'data-testid="stVerticalBlock"',
    'data-testid="stVerticalBlockBorderWrapper"',
    'data-testid="stHorizontalBlock"',
    ".block-container",
)

RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")
COMMENT = re.compile(r"/\*.*?\*/", re.S)
COMBINATOR = re.compile(r"\s+|\s*>\s*")


def rules(css: str) -> list[tuple[str, str]]:
    """(selector, body) for every flat rule, skipping @-block headers."""
    out = []
    for selector, body in RULE.findall(COMMENT.sub(" ", css)):
        selector = " ".join(selector.split())
        if not selector or selector.startswith("@") or selector.endswith("%"):
            continue
        out.append((selector, body))
    return out


def subjects(selector: str) -> list[str]:
    """The element each comma-separated selector actually styles.

    `[data-testid="stMain"] h1` styles the heading, not the wrapper, so only
    the last compound counts - anything before it is an ancestor filter, and
    putting a blur on a heading inside stMain is perfectly safe. Combinators
    inside a functional pseudo-class such as `:has(> .x)` are not breaks, so
    those brackets are blanked out before splitting.
    """
    out = []
    for part in selector.split(","):
        part = part.strip()
        if not part:
            continue
        masked, depth = [], 0
        for char in part:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                masked.append(char)
                continue
            masked.append("_" if depth and char in " >" else char)
        out.append(COMBINATOR.split("".join(masked))[-1].strip())
    return out


def declared(body: str, prop: str) -> list[str]:
    """Values declared for `prop`, ignoring the backdrop-filter longhand."""
    body = re.sub(r"(-webkit-)?backdrop-filter\s*:[^;]*;?", "", body)
    pattern = re.compile(r"(?:^|;|\s)" + prop + r"\s*:([^;]+)")
    return [m.group(1).strip() for m in pattern.finditer(body)]


def blurring_keyframes(css: str) -> set[str]:
    """Names of @keyframes that animate `filter`."""
    names = set()
    for match in re.finditer(r"@keyframes\s+([A-Za-z0-9_-]+)\s*\{", css):
        name = match.group(1)
        depth, i = 0, match.end() - 1
        while i < len(css):
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = re.sub(r"(-webkit-)?backdrop-filter\s*:", "", css[match.end():i])
        if re.search(r"(?:^|;|\s)filter\s*:\s*(?!none)", body):
            names.add(name)
    return names


def is_none(value: str) -> bool:
    return value.split()[0] == "none" if value.split() else True


@pytest.mark.parametrize("theme", theme_mod.THEME_ORDER)
def test_no_filter_on_layout_wrappers(theme: str) -> None:
    """No Streamlit layout wrapper may carry a filter, static or animated."""
    css = theme_mod.css(theme)
    blurring = blurring_keyframes(css)
    offenders = []
    for selector, body in rules(css):
        targeted = [s for s in subjects(selector)
                    if any(w in s for w in LAYOUT_WRAPPERS)]
        if not targeted:
            continue
        for value in declared(body, "filter"):
            if not is_none(value):
                offenders.append(f"{targeted} -> filter: {value}")
        for value in declared(body, "animation"):
            if any(k in value for k in blurring):
                offenders.append(f"{targeted} -> animation: {value}")
    assert not offenders, (
        "These rules put a filter on a layout wrapper, which makes it a "
        "backdrop root and switches off the glass inside it:\n  "
        + "\n  ".join(offenders)
    )


@pytest.mark.parametrize("theme", theme_mod.THEME_ORDER)
def test_frosted_elements_do_not_animate_filter(theme: str) -> None:
    """A frosted element must not also animate its own blur.

    Cheap to get wrong, expensive to look at: the browser re-samples the
    backdrop every frame, and the uxpilot guidance calls it out explicitly.
    """
    css = theme_mod.css(theme)
    blurring = blurring_keyframes(css)
    frosted = set()
    for selector, body in rules(css):
        values = re.findall(r"backdrop-filter\s*:([^;]+)", body)
        if any(not is_none(v.strip()) for v in values):
            frosted.update(subjects(selector))
    offenders = []
    for selector, body in rules(css):
        if not any(s in frosted for s in subjects(selector)):
            continue
        for value in declared(body, "animation"):
            if any(k in value for k in blurring):
                offenders.append(f"{selector} -> {value}")
    assert not offenders, (
        "Frosted elements animating their own filter:\n  " + "\n  ".join(offenders)
    )


@pytest.mark.parametrize("theme", theme_mod.THEME_ORDER)
def test_theme_dock_stays_pinned(theme: str) -> None:
    """The dock is position: fixed, so its ancestors must stay filter-free."""
    css = theme_mod.css(theme)
    dock = [b for s, b in rules(css) if s == ".st-key-theme_dock"]
    assert dock, "the theme dock rule is missing"
    assert "position: fixed" in dock[0]
    # It has to outrank Streamlit's own header (z-index 999990) or its top
    # edge is painted over by it.
    z = re.search(r"z-index:\s*(\d+)", dock[0])
    assert z and int(z.group(1)) > 999990, "dock would sit under the header"

    ancestors = [b for s, b in rules(css) if ":has(.st-key-theme_dock)" in s]
    assert ancestors, "the dock's ancestors are not exempted from filters"
    for body in ancestors:
        assert "filter: none !important" in body
        assert "transform: none !important" in body


@pytest.mark.parametrize("theme", theme_mod.THEME_ORDER)
def test_glass_themes_frost_the_expected_surfaces(theme: str) -> None:
    """Cards, sidebar, tables and charts all frost on the glass themes."""
    css = theme_mod.css(theme)
    for surface in (".kpi-card", '[data-testid="stSidebar"]',
                    '[data-testid="stDataFrame"]',
                    '[data-testid="stPlotlyChart"]'):
        assert surface in css, f"{surface} is not styled at all"
    if theme.endswith("_glass"):
        assert re.search(r"--blur:\s*saturate", css), "glass theme has no blur"
    else:
        assert re.search(r"--blur:\s*none", css), "flat theme should not blur"


@pytest.mark.parametrize("theme", theme_mod.THEME_ORDER)
def test_content_clears_the_pinned_dock(theme: str) -> None:
    """The dock is fixed, so content must start below it, not under it."""
    css = theme_mod.css(theme)
    dock = [b for s, b in rules(css) if s == ".st-key-theme_dock"][0]
    top = float(re.search(r"top:\s*([\d.]+)rem", dock).group(1))
    container = [b for s, b in rules(css)
                 if s == '[data-testid="stMain"] .block-container'][0]
    pad = float(re.search(r"padding-top:\s*([\d.]+)rem", container).group(1))
    assert pad > top, (
        f"content starts at {pad}rem but the dock is pinned at {top}rem, "
        "so the dock would sit on top of the first heading"
    )
