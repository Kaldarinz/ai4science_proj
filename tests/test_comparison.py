"""Hand-counted rules and integration with the independent acceptance checker."""

import ast
import csv
import hashlib
import json
from pathlib import Path

import pytest

from checks import analysis
from src.comparison import build, prepare
from src.comparison.comparison import agrees
from src.comparison.inputs import COMPARISON, SUMMARY, WORKSPACE
from src.comparison.summary import claim_outcome


class Report:
    def __init__(self):
        self.failures = 0
        self.messages = []

    def fail(self, rule, message):
        self.failures += 1
        self.messages.append(f"{rule}: {message}")

    def ok(self, message):
        self.messages.append(message)


def check_generated(f, stage):
    report = Report()
    statuses = analysis.check_coverage(f.root, report, set(range(1, 8)), f.claims)
    analysis.check_analysis(
        f.root, report, set(range(1, 8)), f.claims, statuses, f.tools, stage
    )
    assert report.failures == 0, report.messages


def test_prepare_produces_only_unscored_context(f):
    document = prepare(f.root, tools=f.tools)
    assert len(document["candidates"]) == 7
    pairs = [
        (row["claim"]["claim_id"], row["series"]["series_id"] if row["series"] else "")
        for row in document["candidates"]
    ]
    assert pairs == [
        ("1-c1", "1-s1"),
        ("1-c1", "1-s2"),
        ("1-c3", "1-s1"),
        ("1-c3", "1-s2"),
        ("1-c3", "1-s3"),
        ("3-c1", "3-s1"),
        ("7-c1", ""),
    ]
    # Energy series remain candidates for a fluence claim; no extra physical filters.
    assert document["candidates"][0]["series"]["x_quantity"] == "pulse_energy"
    assert not (f.root / "results/matching_audit.csv").exists()
    assert not (f.root / COMPARISON).exists()
    assert not (f.root / SUMMARY).exists()
    assert not (f.root / "checks/matching_review.json").exists()
    for row in document["candidates"]:
        assert "decision" not in row and "assessment" not in row
        if row["series"]:
            assert (
                not {"shape_primary", "shape_lenient", "spearman_rho"}
                & row["series"].keys()
            )
    before = (f.root / WORKSPACE).read_bytes()
    assert prepare(f.root, tools=f.tools) == document
    assert (f.root / WORKSPACE).read_bytes() == before


def test_hand_counted_draft(prepared):
    f = prepared
    summary = build(f.root, stage="draft", tools=f.tools)
    assert summary["contract_version"] == 1
    assert summary["articles"] == {
        "n_corpus": 7,
        "n_complete": 5,
        "n_pending": 1,
        "n_unreadable": 1,
        "prevalence": {"numerator": 4, "denominator": 5, "fraction": 0.8},
        "n_with_unspecified_claim": 1,
        "by_basis": {"own_data": 3, "cited": 1, "general": 1},
        "by_direction": {
            "increase": 1,
            "decrease": 2,
            "no_effect": 1,
            "non_monotonic": 1,
            "affects": 0,
        },
        "by_basis_and_direction": {
            "own_data": {
                "increase": 1,
                "decrease": 1,
                "no_effect": 0,
                "non_monotonic": 1,
                "affects": 0,
            },
            "cited": {
                "increase": 0,
                "decrease": 1,
                "no_effect": 0,
                "non_monotonic": 0,
                "affects": 0,
            },
            "general": {
                "increase": 0,
                "decrease": 0,
                "no_effect": 1,
                "non_monotonic": 0,
                "affects": 0,
            },
        },
    }
    comparison = summary["comparison"]
    assert {
        key: value
        for key, value in comparison.items()
        if key not in ("claim_outcomes", "by_model")
    } == {
        "n_own_data_claims": 4,
        "n_with_candidates": 3,
        "n_without_candidates": 1,
        "n_with_included_series": 2,
        "n_all_candidates_excluded": 1,
        "n_candidate_pairs": 6,
        "n_included_pairs": 5,
        "n_excluded_pairs": 1,
    }
    assert comparison["claim_outcomes"] == {
        "1-c1": {
            "primary": "mixed",
            "lenient": "all_agree",
            "n_included": 2,
            "n_qualified": 1,
            "n_unassessable": 0,
        },
        "1-c3": {
            "primary": "mixed",
            "lenient": "mixed",
            "n_included": 3,
            "n_qualified": 0,
            "n_unassessable": 1,
        },
        "3-c1": {
            "primary": "unassessable",
            "lenient": "unassessable",
            "n_included": 0,
            "n_qualified": 0,
            "n_unassessable": 0,
        },
        "7-c1": {
            "primary": "unassessable",
            "lenient": "unassessable",
            "n_included": 0,
            "n_qualified": 0,
            "n_unassessable": 0,
        },
    }
    primary, lenient = (
        comparison["by_model"]["primary"],
        comparison["by_model"]["lenient"],
    )
    assert primary["pairs"] == {
        "n_included": 5,
        "n_assessable": 4,
        "agree": 2,
        "disagree": 2,
        "unassessable": 1,
    }
    assert lenient["pairs"] == {
        "n_included": 5,
        "n_assessable": 4,
        "agree": 3,
        "disagree": 1,
        "unassessable": 1,
    }
    assert primary["claims"] == {
        "denominator": 4,
        "all_agree": 0,
        "all_disagree": 0,
        "mixed": 2,
        "unassessable": 2,
    }
    assert lenient["claims"] == {
        "denominator": 4,
        "all_agree": 1,
        "all_disagree": 0,
        "mixed": 1,
        "unassessable": 2,
    }
    assert primary["pairs_by_assessment"]["qualified"] == {
        "n_included": 1,
        "n_assessable": 1,
        "agree": 0,
        "disagree": 1,
        "unassessable": 0,
    }
    assert lenient["pairs_by_assessment"]["qualified"] == {
        "n_included": 1,
        "n_assessable": 1,
        "agree": 1,
        "disagree": 0,
        "unassessable": 0,
    }
    assert summary["series"] == {
        "primary": {
            "counts": {
                "flat": 2,
                "increasing": 2,
                "decreasing": 1,
                "peak": 0,
                "valley": 0,
                "irregular": 0,
            },
            "n_test": 3,
            "p_value": 0.5,
        },
        "lenient": {
            "counts": {
                "flat": 3,
                "increasing": 2,
                "decreasing": 0,
                "peak": 0,
                "valley": 0,
                "irregular": 0,
            },
            "n_test": 2,
            "p_value": 0.25,
        },
    }
    with (f.root / COMPARISON).open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[2]["agree_primary"] == rows[2]["agree_lenient"] == ""
    assert rows[2]["shape_primary"] == "increasing"
    assert set(summary["inputs"]) == set(analysis.INPUT_PATHS)
    for path, sha in summary["inputs"].items():
        assert hashlib.sha256((f.root / path).read_bytes()).hexdigest() == sha
    check_generated(f, "draft")


def test_rebuild_is_byte_identical_and_does_not_touch_audit(prepared):
    f = prepared
    audit_path = f.root / "results/matching_audit.csv"
    audit_before = audit_path.read_bytes()
    build(f.root, stage="draft", tools=f.tools)
    before = {path: (f.root / path).read_bytes() for path in (COMPARISON, SUMMARY)}
    mtimes = {path: (f.root / path).stat().st_mtime_ns for path in before}
    build(f.root, stage="draft", tools=f.tools)
    assert before == {path: (f.root / path).read_bytes() for path in before}
    assert mtimes == {path: (f.root / path).stat().st_mtime_ns for path in before}
    assert audit_path.read_bytes() == audit_before
    assert not (f.root / "checks/matching_review.json").exists()
    assert json.loads((f.root / SUMMARY).read_text())["stage"] == "draft"


@pytest.mark.parametrize(
    "direction, accepted",
    [
        ("increase", {"increasing"}),
        ("decrease", {"decreasing"}),
        ("no_effect", {"flat"}),
        ("non_monotonic", {"peak", "valley", "irregular"}),
        ("affects", {"increasing", "decreasing", "peak", "valley", "irregular"}),
    ],
)
@pytest.mark.parametrize(
    "shape", ["flat", "increasing", "decreasing", "peak", "valley", "irregular"]
)
def test_agreement_table(direction, accepted, shape):
    assert agrees(direction, shape) == (shape in accepted)


@pytest.mark.parametrize(
    "values, expected",
    [
        ([], "unassessable"),
        ([""], "unassessable"),
        (["true"], "all_agree"),
        (["false", "false"], "all_disagree"),
        (["true", "true", "false"], "mixed"),
        (["true", "false", ""], "mixed"),
        (["true", ""], "unassessable"),
        (["false", ""], "unassessable"),
        (["", ""], "unassessable"),
    ],
)
def test_no_majority_or_unknown_as_true(values, expected):
    assert (
        claim_outcome([{"agree_primary": value} for value in values], "primary")
        == expected
    )


def test_production_never_imports_checker():
    root = Path(__file__).resolve().parents[1] / "src/comparison"
    for path in root.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                assert all(not name.name.startswith("checks") for name in node.names)
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("checks")
