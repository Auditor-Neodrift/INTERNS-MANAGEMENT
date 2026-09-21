"""The reflection rate worklist, its note store, and the stipend incentive.

Everything here runs on synthetic frames - no network, no Google Sheet - so
the rules are pinned by their definition rather than by whatever the live
workbook happens to contain today.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import metrics  # noqa: E402
import reflection  # noqa: E402


def make_main(rows: list[dict]) -> pd.DataFrame:
    """A MAIN-shaped frame with only the columns the report touches."""
    base = {
        "order_id": "", "asin": "", "intern": "", "product": "",
        "order_date": pd.NaT, "age_days": 0, "status": "", "review_link": "",
        "payment_state": "PAID", "order_price": 0.0, "sheet_row": 0,
        "review_submitted": True, "reflected": False, "delivered": True,
    }
    return pd.DataFrame([{**base, **row} for row in rows])


# ---------------------------------------------------------------------------
# Which orders land on the worklist
# ---------------------------------------------------------------------------
def test_report_keeps_only_submitted_unreflected_and_aged() -> None:
    main = make_main([
        {"order_id": "keep", "age_days": 20},
        {"order_id": "reflected", "age_days": 20, "reflected": True},
        {"order_id": "no-review", "age_days": 20, "review_submitted": False},
        {"order_id": "too-new", "age_days": 14},
        {"order_id": "exactly-sla", "age_days": 15},
    ])
    got = set(reflection.report(main, sla_days=15)["order_id"])
    assert got == {"keep", "exactly-sla"}, got


def test_report_sorts_oldest_first() -> None:
    main = make_main([
        {"order_id": "young", "age_days": 16},
        {"order_id": "ancient", "age_days": 300},
        {"order_id": "middle", "age_days": 90},
    ])
    assert list(reflection.report(main)["order_id"]) == [
        "ancient", "middle", "young"]


def test_undated_orders_never_age_in() -> None:
    """A blank order date must not be treated as infinitely old."""
    main = make_main([{"order_id": "undated", "age_days": None}])
    assert reflection.report(main, sla_days=15).empty


def test_delivered_only_narrows_the_list() -> None:
    main = make_main([
        {"order_id": "delivered", "age_days": 20, "delivered": True},
        {"order_id": "in-transit", "age_days": 20, "delivered": False},
    ])
    assert len(reflection.report(main, 15, delivered_only=False)) == 2
    narrowed = reflection.report(main, 15, delivered_only=True)
    assert list(narrowed["order_id"]) == ["delivered"]


def test_empty_main_returns_the_empty_shape() -> None:
    out = reflection.report(pd.DataFrame())
    assert out.empty
    for col in ("order_id", "asin", "intern", "product"):
        assert col in out.columns


# ---------------------------------------------------------------------------
# Notes merged onto the worklist
# ---------------------------------------------------------------------------
def test_merge_notes_with_no_store_leaves_every_row_open() -> None:
    rows = reflection.report(make_main([
        {"order_id": "a", "age_days": 20}, {"order_id": "b", "age_days": 20},
    ]))
    merged = reflection.merge_notes(rows, reflection._empty_notes())
    assert list(merged["checked"]) == [False, False]
    assert list(merged["remark"]) == ["", ""]
    assert reflection.summarise(merged)["unchecked"] == 2


def test_merge_notes_attaches_remark_and_signoff() -> None:
    rows = reflection.report(make_main([
        {"order_id": "a", "age_days": 20}, {"order_id": "b", "age_days": 20},
    ]))
    notes = pd.DataFrame([
        {"order_id": "a", "remark": "removed by Amazon", "checked": True,
         "checked_by": "checker@x", "updated_at": pd.Timestamp("2026-09-01"),
         "updated_by": "checker@x"},
    ])
    merged = reflection.merge_notes(rows, notes).set_index("order_id")
    assert merged.loc["a", "remark"] == "removed by Amazon"
    assert bool(merged.loc["a", "checked"]) is True
    assert bool(merged.loc["b", "checked"]) is False
    assert merged.loc["b", "remark"] == ""


def test_a_note_for_an_unlisted_order_does_not_add_a_row() -> None:
    """Notes are keyed by order ID but the worklist is still the source."""
    rows = reflection.report(make_main([{"order_id": "a", "age_days": 20}]))
    notes = pd.DataFrame([{"order_id": "gone", "remark": "x", "checked": True,
                           "checked_by": "", "updated_at": pd.NaT,
                           "updated_by": ""}])
    assert list(reflection.merge_notes(rows, notes)["order_id"]) == ["a"]


def test_open_errors_is_the_unchecked_rows() -> None:
    rows = reflection.report(make_main([
        {"order_id": "a", "age_days": 20}, {"order_id": "b", "age_days": 20},
    ]))
    notes = pd.DataFrame([{"order_id": "a", "remark": "", "checked": True,
                           "checked_by": "c", "updated_at": pd.NaT,
                           "updated_by": "c"}])
    merged = reflection.merge_notes(rows, notes)
    assert list(reflection.open_errors(merged)["order_id"]) == ["b"]
    assert reflection.summarise(merged)["unchecked"] == 1


def test_summarise_of_an_empty_worklist_is_all_zero() -> None:
    stats = reflection.summarise(reflection.merge_notes(
        reflection.report(pd.DataFrame()), reflection._empty_notes()))
    assert stats["total"] == 0 and stats["unchecked"] == 0


# ---------------------------------------------------------------------------
# Detecting what the editor changed
# ---------------------------------------------------------------------------
def test_diff_edits_reports_only_real_changes() -> None:
    before = pd.DataFrame([
        {"order_id": "a", "remark": "old", "checked": False},
        {"order_id": "b", "remark": "", "checked": True},
    ])
    after = pd.DataFrame([
        {"order_id": "a", "remark": "new", "checked": False},
        {"order_id": "b", "remark": "", "checked": True},
    ])
    assert reflection.diff_edits(before, after) == {"a": {"remark": "new"}}


def test_diff_edits_ignores_whitespace_only_edits() -> None:
    before = pd.DataFrame([{"order_id": "a", "remark": "why", "checked": False}])
    after = pd.DataFrame([{"order_id": "a", "remark": "  why  ", "checked": False}])
    assert reflection.diff_edits(before, after) == {}


def test_diff_edits_catches_a_ticked_checkbox() -> None:
    before = pd.DataFrame([{"order_id": "a", "remark": "", "checked": False}])
    after = pd.DataFrame([{"order_id": "a", "remark": "", "checked": True}])
    assert reflection.diff_edits(before, after) == {"a": {"checked": True}}


# ---------------------------------------------------------------------------
# The local note store
# ---------------------------------------------------------------------------
@pytest.fixture()
def local_store(tmp_path, monkeypatch):
    monkeypatch.setattr(reflection, "LOCAL_PATH", tmp_path / "notes.json")
    monkeypatch.setattr(reflection, "is_shared", lambda: False)
    return tmp_path


def test_save_then_load_round_trips(local_store) -> None:
    written, _ = reflection.save_notes(
        {"402-1": {"remark": "removed", "checked": True}}, "me@x.com")
    assert written == 1
    notes = reflection.load_notes().set_index("order_id")
    assert notes.loc["402-1", "remark"] == "removed"
    assert bool(notes.loc["402-1", "checked"]) is True
    assert notes.loc["402-1", "checked_by"] == "me@x.com"


def test_remark_only_edit_leaves_checked_by_blank(local_store) -> None:
    """NaN is truthy, so an unset checked_by once stringified to 'nan'."""
    reflection.save_notes({"402-1": {"remark": "waiting"}}, "me@x.com")
    notes = reflection.load_notes().set_index("order_id")
    assert notes.loc["402-1", "checked_by"] == ""
    assert notes.loc["402-1", "remark"] == "waiting"


def test_unticking_clears_who_signed_it_off(local_store) -> None:
    reflection.save_notes({"402-1": {"checked": True}}, "checker@x.com")
    reflection.save_notes({"402-1": {"checked": False}}, "other@x.com")
    notes = reflection.load_notes().set_index("order_id")
    assert bool(notes.loc["402-1", "checked"]) is False
    assert notes.loc["402-1", "checked_by"] == ""


def test_saving_nothing_writes_nothing(local_store) -> None:
    written, message = reflection.save_notes({}, "me@x.com")
    assert written == 0 and "Nothing" in message


def test_store_state_admits_the_local_store_is_not_durable(local_store) -> None:
    state = reflection.store_state()
    assert state["backend"] == "local"
    assert state["durable"] is False


# ---------------------------------------------------------------------------
# Review incentive from the promised stipend
# ---------------------------------------------------------------------------
def make_interns(rows: list[dict]) -> pd.DataFrame:
    base = {"name": "", "status": "Completed", "is_active": False,
            "stipend": None, "orders": 0, "reviews_submitted": 0,
            "reviews_reflected": 0}
    return pd.DataFrame([{**base, **row} for row in rows])


def test_per_review_is_the_stipend_over_the_target() -> None:
    table = metrics.review_incentive(
        make_interns([{"name": "A", "stipend": 5000, "reviews_submitted": 25}]),
        target_reviews=25,
    )
    row = table.iloc[0]
    assert row["per_review"] == 200.0
    assert row["incentive"] == 5000.0


def test_incentive_follows_actual_reviews_not_the_target() -> None:
    table = metrics.review_incentive(
        make_interns([
            {"name": "under", "stipend": 5000, "reviews_submitted": 10},
            {"name": "over", "stipend": 5000, "reviews_submitted": 30},
        ]),
        target_reviews=25,
    ).set_index("name")
    assert table.loc["under", "incentive"] == 2000.0
    assert table.loc["over", "incentive"] == 6000.0


def test_a_missing_stipend_is_not_a_zero_incentive() -> None:
    """'Not recorded' has to stay visibly different from 'worth nothing'."""
    table = metrics.review_incentive(
        make_interns([{"name": "A", "stipend": None, "reviews_submitted": 20}])
    )
    row = table.iloc[0]
    assert pd.isna(row["per_review"]) and pd.isna(row["incentive"])
    assert bool(row["stipend_recorded"]) is False


def test_a_zero_stipend_is_treated_as_not_recorded() -> None:
    table = metrics.review_incentive(
        make_interns([{"name": "A", "stipend": 0, "reviews_submitted": 20}])
    )
    assert bool(table.iloc[0]["stipend_recorded"]) is False


def test_the_reflected_basis_pays_only_for_reviews_that_went_live() -> None:
    interns = make_interns([{"name": "A", "stipend": 5000,
                             "reviews_submitted": 25, "reviews_reflected": 10}])
    submitted = metrics.review_incentive(interns, 25, "submitted").iloc[0]
    reflected = metrics.review_incentive(interns, 25, "reflected").iloc[0]
    assert submitted["incentive"] == 5000.0
    assert reflected["incentive"] == 2000.0


def test_an_unknown_basis_falls_back_to_submitted() -> None:
    interns = make_interns([{"name": "A", "stipend": 5000,
                             "reviews_submitted": 25, "reviews_reflected": 1}])
    assert metrics.review_incentive(interns, 25, "nonsense").iloc[0][
        "incentive"] == 5000.0


def test_totals_exclude_interns_with_no_stipend_but_still_count_them() -> None:
    table = metrics.review_incentive(make_interns([
        {"name": "paid", "stipend": 5000, "reviews_submitted": 25},
        {"name": "unknown", "stipend": None, "reviews_submitted": 25},
        {"name": "active", "stipend": None, "reviews_submitted": 5,
         "is_active": True, "status": "Active"},
    ]), target_reviews=25)
    totals = metrics.incentive_totals(table)
    assert totals["interns"] == 3
    assert totals["with_stipend"] == 1
    assert totals["without_stipend"] == 2
    assert totals["total"] == 5000.0
    assert totals["reviews"] == 25          # only the stipend-bearing intern
    assert totals["avg_per_review"] == 200.0
    assert totals["active"] == 1 and totals["active_with_stipend"] == 0
    assert round(totals["coverage"], 2) == round(100 / 3, 2)


def test_empty_roster_is_handled() -> None:
    table = metrics.review_incentive(pd.DataFrame())
    assert table.empty
    assert metrics.incentive_totals(table)["interns"] == 0


def test_a_zero_target_falls_back_rather_than_dividing_by_zero() -> None:
    table = metrics.review_incentive(
        make_interns([{"name": "A", "stipend": 5000, "reviews_submitted": 25}]),
        target_reviews=0,
    )
    assert table.iloc[0]["per_review"] == 5000.0 / metrics.REVIEW_TARGET
