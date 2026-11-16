"""Synthetic contract tests: no corpus PDFs, numerical snapshot or src/ import."""

import csv
import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from checks import analysis as a
from checks import check


class Report:
    def __init__(self):
        self.failures = 0
        self.messages = []

    def fail(self, rule, message):
        self.failures += 1
        self.messages.append(f"{rule}: {message}")

    def ok(self, message):
        self.messages.append(message)


class Tools:
    def __init__(self, series):
        self.series = series

    def list_series(self, aid):
        return [s for s in self.series if s["article_id"] == aid]


def write_csv(root, path, columns, records):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)


def write_json(root, path, data):
    (root / path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def fixture_digest(files, aid):
    # Test-side implementation, not the checker helper.
    triples = [[f["file"], f["role"], f["sha256"]] for f in files if f["article_id"] == str(aid)]
    return hashlib.sha256(json.dumps(sorted(triples), separators=(",", ":")).encode()).hexdigest()


def rebind(f):
    f["summary"]["inputs"] = {p: hashlib.sha256((f["root"] / p).read_bytes()).hexdigest() for p in a.INPUT_PATHS}
    write_json(f["root"], "results/summary.json", f["summary"])


def make_fixture(root):
    # Complete articles 1,2,3,6,7; article 3 is genuinely negative.
    # Pending article 4 has a partial claim; it must not affect any tally.
    claims = []
    for aid, k, variable, direction, basis, medium in [
        (1, 1, "energy", "increase", "own_data", "water"),
        (1, 2, "power", "no_effect", "general", "water"),
        (1, 3, "intensity", "increase", "cited", "water"),
        (2, 1, "unspecified", "affects", "own_data", "organic"),
        (4, 1, "fluence", "increase", "own_data", "water"),
        (6, 1, "fluence", "decrease", "own_data", "water"),
        (7, 1, "energy", "increase", "own_data", "water"),
        (7, 2, "unspecified", "no_effect", "own_data", "other"),
        (7, 3, "energy", "increase", "own_data", "organic"),
    ]:
        row = dict.fromkeys(check.CLAIMS_COLUMNS, "synthetic")
        row.update(claim_id=f"{aid}-c{k}", article_id=str(aid), variable=variable,
                   direction=direction, basis=basis, medium_class=medium)
        claims.append(row)
    series = []
    for aid, k, medium, primary, lenient in [
        (1, 1, "water", "increasing", "increasing"),
        (1, 2, "water", "increasing", "decreasing"),
        (1, 3, "water", "decreasing", "decreasing"),
        (6, 1, "water", "increasing", "increasing"),
        (7, 1, "water", "increasing", "increasing"),
        (7, 2, "other", "flat", "flat"),
        (7, 3, "organic", "increasing", "increasing"),
        (7, 4, "organic", "flat", "flat"),
    ]:
        series.append(dict(article_id=aid, series_id=f"{aid}-s{k}", medium_class=medium,
                           shape_primary=primary, shape_lenient=lenient))
    audit = []
    comparison = []
    # Explicit pair inventory, independent of a.candidates().
    for cid, sid, decision, assessment in [
        ("1-c1", "1-s1", "include", "direct"),
        ("1-c1", "1-s2", "include", "direct"),
        ("1-c1", "1-s3", "include", "direct"),
        ("2-c1", "", "no_candidates", ""),
        ("6-c1", "6-s1", "exclude", ""),
        ("7-c1", "7-s1", "include", "qualified"),
        ("7-c2", "7-s2", "include", "unassessable"),
        ("7-c3", "7-s3", "include", "direct"),
        ("7-c3", "7-s4", "include", "unassessable"),
    ]:
        audit.append(dict(claim_id=cid, series_id=sid, decision=decision,
                          assessment=assessment, reason="synthetic evidence, p. 1",
                          caveats="explicit synthetic limitation"))
        if decision != "include":
            continue
        s = next(s for s in series if s["series_id"] == sid)
        direction = next(c["direction"] for c in claims if c["claim_id"] == cid)
        comparison.append(dict(
            claim_id=cid, series_id=sid, direction=direction,
            shape_primary=s["shape_primary"], shape_lenient=s["shape_lenient"],
            agree_primary="" if assessment == "unassessable" else str(s["shape_primary"] == "increasing").lower(),
            agree_lenient="" if assessment == "unassessable" else str(s["shape_lenient"] == "increasing").lower(),
            assessment=assessment, note="see audit caveats"))
    statuses = {str(i): "pending" if i == 4 else "unreadable" if i == 5 else "complete" for i in range(1, 8)}
    files = [dict(article_id=str(i), file="main.pdf", role="main", sha256="a" * 64) for i in range(1, 8)]
    files.append(dict(article_id="1", file="si.pdf", role="supplement", sha256="b" * 64))
    ledger = [dict(article_id=aid, status=status, files_sha256=fixture_digest(files, aid),
                   reason="synthetic coverage attestation") for aid, status in statuses.items()]
    for path in a.INPUT_PATHS:
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text("synthetic input\n", encoding="utf-8")
    write_csv(root, "data/files.csv", check.FILES_COLUMNS, files)
    write_csv(root, "results/claims.csv", check.CLAIMS_COLUMNS, claims)
    write_csv(root, "results/no_claims.csv", check.NO_CLAIMS_COLUMNS,
              [dict(article_id="3", file="main.pdf", page="1", quote="synthetic sentence", reason="no dependence")])
    write_csv(root, "results/extraction_status.csv", a.STATUS_COLUMNS, ledger)
    write_csv(root, "results/matching_audit.csv", a.AUDIT_COLUMNS, audit)
    write_csv(root, "results/comparison.csv", a.COMPARISON_COLUMNS, comparison)
    zeros = {d: 0 for d in a.DIRECTIONS}
    outcomes = {
        "1-c1": dict(primary="mixed", lenient="mixed", n_included=3, n_qualified=0, n_unassessable=0),
        "2-c1": dict(primary="unassessable", lenient="unassessable", n_included=0, n_qualified=0, n_unassessable=0),
        "6-c1": dict(primary="unassessable", lenient="unassessable", n_included=0, n_qualified=0, n_unassessable=0),
        "7-c1": dict(primary="all_agree", lenient="all_agree", n_included=1, n_qualified=1, n_unassessable=0),
        "7-c2": dict(primary="unassessable", lenient="unassessable", n_included=1, n_qualified=0, n_unassessable=1),
        "7-c3": dict(primary="unassessable", lenient="unassessable", n_included=2, n_qualified=0, n_unassessable=1),
    }

    def pair_counts(n, yes, no, unknown=0):
        return dict(n_included=n, n_assessable=yes + no, agree=yes, disagree=no, unassessable=unknown)

    models = {}
    shapes = {}
    for model, yes, no, increasing, decreasing, p in [
        ("primary", 4, 1, 5, 1, 7 / 64), ("lenient", 3, 2, 4, 2, 22 / 64),
    ]:
        models[model] = dict(
            claims=dict(denominator=6, all_agree=1, all_disagree=0, mixed=1, unassessable=4),
            pairs=pair_counts(7, yes, no, 2),
            pairs_by_assessment=dict(direct=pair_counts(4, yes - 1, no),
                                     qualified=pair_counts(1, 1, 0),
                                     unassessable=pair_counts(2, 0, 0, 2)))
        shapes[model] = dict(counts=dict(flat=2, increasing=increasing, decreasing=decreasing,
                                        peak=0, valley=0, irregular=0), n_test=6, p_value=p)
    summary = dict(
        contract_version=1, stage="draft", inputs={},
        articles=dict(n_corpus=7, n_complete=5, n_pending=1, n_unreadable=1,
                      prevalence=dict(numerator=3, denominator=5, fraction=0.6),
                      n_with_unspecified_claim=2,
                      by_basis=dict(own_data=3, cited=1, general=1),
                      by_direction=dict(increase=2, decrease=1, no_effect=1, non_monotonic=0, affects=0),
                      by_basis_and_direction=dict(own_data={**zeros, "increase": 2, "decrease": 1},
                                                 cited={**zeros, "increase": 1}, general={**zeros, "no_effect": 1})),
        comparison=dict(n_own_data_claims=6, n_with_candidates=5, n_without_candidates=1,
                        n_with_included_series=4, n_all_candidates_excluded=1,
                        n_candidate_pairs=8, n_included_pairs=7, n_excluded_pairs=1,
                        claim_outcomes=outcomes, by_model=models), series=shapes)
    f = dict(root=root, ids=set(range(1, 8)), claims=claims, series=series,
             statuses=statuses, ledger=ledger, files=files, audit=audit,
             comparison=comparison, summary=summary)
    rebind(f)
    return f


@pytest.fixture
def f(tmp_path):
    return make_fixture(tmp_path)


def run(f, stage="draft"):
    report = Report()
    a.check_analysis(f["root"], report, f["ids"], f["claims"], f["statuses"], Tools(f["series"]), stage)
    return report


def test_hand_counted_draft(f):
    report = run(f)
    assert report.failures == 0, report.messages
    coverage = Report()
    assert a.check_coverage(f["root"], coverage, f["ids"], f["claims"]) == f["statuses"]
    assert coverage.failures == 0, coverage.messages


@pytest.mark.parametrize("values, expected", [
    ([], "unassessable"), ([""], "unassessable"),
    (["true", "true", "false"], "mixed"), (["false", "true", ""], "mixed"),
    (["true", "true"], "all_agree"), (["false", "false"], "all_disagree"),
    (["true", ""], "unassessable"), (["false", ""], "unassessable"),
])
def test_outcomes_no_majority(values, expected):
    assert a.outcome(values) == expected


@pytest.mark.parametrize("table, mutation, message", [
    ("audit", lambda r: r.pop(0), "missing pair"),
    ("audit", lambda r: r.append(deepcopy(r[0])), "duplicate pair"),
    ("audit", lambda r: r[0].update(decision="exclude", assessment=""), "unexpected or duplicate pair"),
    ("audit", lambda r: r[0].update(reason=" "), "reason and caveats"),
    ("audit", lambda r: r[5].update(caveats="none"), "substantive caveats"),
    ("audit", lambda r: r[4].update(assessment="direct"), "must be empty"),
    ("audit", lambda r: r[3].update(decision="include", assessment="direct"), "no_candidates requires"),
    ("audit", lambda r: r[0].update(decision="silent_skip"), "invalid decision"),
    ("audit", lambda r: r[0].update(assessment="maybe"), "needs an assessment"),
    ("comparison", lambda r: r.pop(), "missing pair"),
    ("comparison", lambda r: r.append(deepcopy(r[0])), "duplicate pair"),
    ("comparison", lambda r: r[0].update(claim_id="1-c3"), "unexpected or duplicate pair"),
    ("comparison", lambda r: r[0].update(series_id="7-s3"), "unexpected or duplicate pair"),
    ("comparison", lambda r: r[0].update(shape_primary="flat"), "shape_primary differs"),
    ("comparison", lambda r: r[0].update(agree_primary="false"), "agree_primary must"),
    ("comparison", lambda r: r[0].update(agree_lenient="TRUE"), "agree_lenient must"),
    ("comparison", lambda r: r[4].update(agree_primary="true"), "agree_primary must be ''"),
    ("comparison", lambda r: r[3].update(assessment="direct"), "direction/assessment differs"),
    ("comparison", lambda r: r[0].update(direction="decrease"), "direction/assessment differs"),
    ("comparison", lambda r: r[0].update(note=""), "note required"),
])
def test_pair_corruption(f, table, mutation, message):
    mutation(f[table])
    path, columns = ("matching_audit", a.AUDIT_COLUMNS) if table == "audit" else ("comparison", a.COMPARISON_COLUMNS)
    write_csv(f["root"], f"results/{path}.csv", columns, f[table])
    rebind(f)
    report = run(f)
    assert report.failures and any(message in s for s in report.messages), report.messages


@pytest.mark.parametrize("mutation", [
    lambda s: s["articles"]["prevalence"].update(denominator=7),
    lambda s: s["articles"]["prevalence"].update(numerator=4),
    lambda s: s["articles"]["by_basis"].update(own_data=4),
    lambda s: s["articles"]["by_direction"].update(no_effect=0),
    lambda s: s["articles"].update(n_with_unspecified_claim=0),
    lambda s: s["comparison"]["claim_outcomes"]["1-c1"].update(primary="all_agree"),
    lambda s: s["comparison"]["claim_outcomes"].pop("2-c1"),
    lambda s: s["comparison"]["by_model"]["primary"]["claims"].update(denominator=4),
    lambda s: s["comparison"]["by_model"]["primary"]["pairs_by_assessment"]["qualified"].update(agree=0),
    lambda s: s["comparison"].update(n_all_candidates_excluded=0),
    lambda s: s["series"]["primary"].update(p_value=0.5),
    lambda s: s.update(contract_version=True),
    lambda s: s["articles"].update(n_complete=5.0),
    lambda s: s.update(extra="hidden denominator"),
])
def test_summary_corruption(f, mutation):
    mutation(f["summary"])
    write_json(f["root"], "results/summary.json", f["summary"])
    report = run(f)
    assert report.failures and any("summary" in s for s in report.messages), report.messages


def test_unknown_medium_all_article_series_and_no_physical_filter():
    claim = dict(claim_id="1-c1", article_id="1", medium_class="unspecified", variable="power")
    series = {f"{aid}-s{k}": dict(article_id=aid, medium_class=medium)
              for aid, k, medium in [(1, 1, "water"), (1, 2, "organic"), (2, 1, "water")]}
    assert a.candidates([claim], series) == {("1-c1", "1-s1"), ("1-c1", "1-s2")}
    claim["medium_class"] = "other"
    assert a.candidates([claim], series) == {("1-c1", "")}


@pytest.mark.parametrize("mutation, message", [
    (lambda f: f["ledger"].pop(), "missing extraction status"),
    (lambda f: f["ledger"].append(deepcopy(f["ledger"][0])), "duplicate article"),
    (lambda f: f["ledger"][0].update(files_sha256="0" * 64), "stale PDF"),
    (lambda f: f["ledger"][0].update(status="done"), "invalid status"),
    (lambda f: f["ledger"][0].update(reason=""), "needs a reason"),
    (lambda f: f["ledger"][2].update(status="unreadable"), "cannot be no_claims"),
    (lambda f: f["ledger"][4].update(status="complete"), "claims XOR"),
])
def test_coverage_corruption(f, mutation, message):
    mutation(f)
    write_csv(f["root"], "results/extraction_status.csv", a.STATUS_COLUMNS, f["ledger"])
    report = Report()
    a.check_coverage(f["root"], report, f["ids"], f["claims"])
    assert report.failures and any(message in s for s in report.messages), report.messages


def test_new_si_invalidates_attestation(f):
    f["files"].append(dict(article_id="3", file="new-si.pdf", role="supplement", sha256="c" * 64))
    write_csv(f["root"], "data/files.csv", check.FILES_COLUMNS, f["files"])
    report = Report()
    a.check_coverage(f["root"], report, f["ids"], f["claims"])
    assert any("article 3: stale PDF" in s for s in report.messages)


def test_coverage_scoped_to_article(f):
    report = Report()
    statuses = a.check_coverage(f["root"], report, {1}, [c for c in f["claims"] if c["article_id"] == "1"], 1)
    assert statuses == {"1": "complete"}
    assert report.failures == 0, report.messages


def approve(f):
    write_json(f["root"], "checks/matching_review.json", dict(
        decision="accepted", reviewer="synthetic curator", date="2026-11-15", inputs=f["summary"]["inputs"]))


def make_final(f):
    f["statuses"]["4"] = "unreadable"
    f["ledger"][3]["status"] = "unreadable"
    write_csv(f["root"], "results/extraction_status.csv", a.STATUS_COLUMNS, f["ledger"])
    f["summary"]["stage"] = "final"
    f["summary"]["articles"].update(n_pending=0, n_unreadable=2)
    rebind(f)


def test_final_requires_review_and_no_pending(f):
    report = run(f, "final")
    assert any("pending" in s for s in report.messages)
    assert any("matching_review" in s for s in report.messages)
    make_final(f)
    assert run(f, "final").failures
    approve(f)
    report = run(f, "final")
    assert report.failures == 0, report.messages


@pytest.mark.parametrize("path", a.INPUT_PATHS)
def test_any_changed_review_input_invalidates_acceptance(f, path):
    make_final(f)
    approve(f)
    # Keep schemas intact: a byte-only newline change is still a new input.
    with (f["root"] / path).open("a") as stream:
        stream.write("\n")
    rebind(f)
    report = run(f, "final")
    assert report.failures and any("matching_review.inputs" in s for s in report.messages), report.messages


@pytest.mark.parametrize("field, value", [("decision", "draft"), ("reviewer", " "), ("date", "2026-02-30"), ("date", 1)])
def test_bad_review(f, field, value):
    make_final(f)
    approve(f)
    path = f["root"] / "checks/matching_review.json"
    review = json.loads(path.read_text())
    review[field] = value
    write_json(f["root"], "checks/matching_review.json", review)
    assert run(f, "final").failures


@pytest.mark.parametrize("payload", ["{", "null", "[]", "true", '{"stage":"draft","stage":"final"}', '{"x":NaN}', '{"x":Infinity}'])
def test_bad_json(f, payload):
    (f["root"] / "results/summary.json").write_text(payload)
    report = run(f)
    assert report.failures and any("analysis input" in s for s in report.messages)


@pytest.mark.parametrize("payload", ["wrong,header\n", ",".join(a.AUDIT_COLUMNS), ",".join(a.AUDIT_COLUMNS) + "\n1-c1\n"])
def test_bad_csv(f, payload):
    (f["root"] / "results/matching_audit.csv").write_text(payload)
    assert run(f).failures


def test_missing_outputs_fail_closed(f):
    (f["root"] / "results/comparison.csv").unlink()
    assert run(f).failures


def test_tool_failure_is_not_empty_success(f):
    class Broken:
        def list_series(self, aid):
            raise ValueError("broken snapshot")
    report = Report()
    a.check_analysis(f["root"], report, f["ids"], f["claims"], f["statuses"], Broken(), "draft")
    assert any("series tools failed" in s for s in report.messages)


def test_zero_denominators():
    s = a.expected_summary([], {"1": "unreadable"}, [], [], {}, {}, "draft")
    assert s["articles"]["prevalence"] == dict(numerator=0, denominator=0, fraction=None)
    assert s["comparison"]["by_model"]["primary"]["claims"]["denominator"] == 0
    assert s["series"]["primary"]["p_value"] is None


@pytest.mark.parametrize("values, expected", [
    ([("true", "true"), ("true", "true"), ("false", "false")], "mixed"),
    ([("true", "true"), ("true", "false")], "mixed"),
    ([("true", "false")], "model_dependent"),
    ([("true", "true")], "agrees"),
    ([("false", "false")], "disagrees"),
    ([("", "")], "unassessable"),
    ([("true", "true"), ("", "")], "unassessable"),
    ([], "unmatched"),
])
def test_graph_does_not_mislabel_mixed_as_model_dependent(values, expected):
    from tools import graph
    records = [dict(claim_id="1-c1", series_id=f"1-s{i}", agree_primary=p, agree_lenient=l)
               for i, (p, l) in enumerate(values, 1)]
    assert graph.verdict("1-c1", {"basis": "own_data"}, records) == expected
    assert graph.verdict("1-c1", {"basis": "cited"}, records) is None
    assert graph.verdict("1-c1", {"basis": "own_data"}, None) is None


def test_graph_retains_conditional_qualification(f, monkeypatch):
    from tools import graph
    monkeypatch.setattr(graph, "ROOT", f["root"])
    notes = graph.build_objects({p: None for p in (graph.QUERIES, graph.SOURCES, graph.CITATIONS, graph.SOURCE_CHECKS)})
    note = next(n for n in notes if n.name == "Claim 7-c1")
    assert note.attrs["verdict"] == "agrees"
    assert "primary outcome: all_agree" in note.body
    assert any("qualified pairs: 1" in line and "not unqualified verification" in line for line in note.body)


def test_vocabulary_matches_actual_specs():
    report = Report()
    check.check_vocabulary(report)
    assert report.failures == 0, report.messages


def test_claim_only_cli_does_not_load_analysis_tools_or_outputs(monkeypatch, tmp_path):
    monkeypatch.setattr(check.sys, "argv", ["check.py", "--article", "1"])
    monkeypatch.setattr(check, "RESULTS", tmp_path)
    monkeypatch.setattr(check, "check_data", lambda *args: ({1}, {}))
    monkeypatch.setattr(check, "check_claims", lambda *args: [])
    monkeypatch.setattr(check, "check_no_claims", lambda *args: None)
    monkeypatch.setattr(check, "check_committed", lambda *args: None)
    def forbidden(*args):
        pytest.fail("claim-only mode touched analysis tools/results")
    monkeypatch.setattr(check, "load_tools", forbidden)
    monkeypatch.setattr(a, "check_analysis", forbidden)
    monkeypatch.setattr(a, "read_json", forbidden)
    assert check.main() == 0


@pytest.mark.parametrize("stage", ["draft", "final"])
def test_analysis_cli_uses_ledger_and_review(f, monkeypatch, stage):
    if stage == "final":
        make_final(f)
        approve(f)
    monkeypatch.setattr(check.sys, "argv", ["check.py", "--analysis", stage])
    monkeypatch.setattr(check, "ROOT", f["root"])
    monkeypatch.setattr(check, "RESULTS", f["root"] / "results")
    monkeypatch.setattr(check, "check_vocabulary", lambda *args: None)
    monkeypatch.setattr(check, "check_data", lambda *args: (f["ids"], {}))
    monkeypatch.setattr(check, "check_claims", lambda *args: f["claims"])
    monkeypatch.setattr(check, "check_no_claims", lambda *args: None)
    monkeypatch.setattr(check, "check_committed", lambda *args: None)
    monkeypatch.setattr(check, "load_tools", lambda *args: Tools(f["series"]))
    assert check.main() == 0
    (f["root"] / "results/extraction_status.csv").unlink()
    def forbidden(*args):
        pytest.fail("analysis loaded numbers before valid reading coverage")
    monkeypatch.setattr(check, "load_tools", forbidden)
    assert check.main() == 1


def test_full_claim_readiness_rejects_pending_ledger(f, monkeypatch):
    monkeypatch.setattr(check.sys, "argv", ["check.py"])
    monkeypatch.setattr(check, "ROOT", f["root"])
    monkeypatch.setattr(check, "RESULTS", f["root"] / "results")
    monkeypatch.setattr(check, "check_vocabulary", lambda *args: None)
    monkeypatch.setattr(check, "check_data", lambda *args: (f["ids"], {}))
    monkeypatch.setattr(check, "check_claims", lambda *args: f["claims"])
    monkeypatch.setattr(check, "check_no_claims", lambda *args: None)
    monkeypatch.setattr(check, "check_committed", lambda *args: None)
    def forbidden(*args):
        pytest.fail("claim readiness touched numerical tools")
    monkeypatch.setattr(check, "load_tools", forbidden)
    assert check.main() == 1


def test_huge_number_cannot_crash_or_match_fraction():
    assert a.differences(0.5, 10**400)


def test_final_analysis_and_article_are_mutually_exclusive(monkeypatch):
    monkeypatch.setattr(check.sys, "argv", ["check.py", "--article", "1", "--analysis", "final"])
    with pytest.raises(SystemExit) as error:
        check.main()
    assert error.value.code == 2
