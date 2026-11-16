"""CLI integration with the real numerical adapter on a synthetic snapshot."""

import hashlib
import json
from pathlib import Path

from conftest import write_csv, write_json
from test_comparison import Report

from checks import analysis
from src.comparison.__main__ import main
from src.comparison.inputs import (
    AUDIT_COLUMNS,
    BASE_INPUT_PATHS,
    CLAIM_COLUMNS,
    CORPUS_COLUMNS,
    FILES_COLUMNS,
    NEGATIVE_COLUMNS,
    STATUS_COLUMNS,
)
from tools.ablation_db import SnapshotTools
from tools.tests.series_fixtures import snapshot


def test_real_snapshot_adapter_cli_roundtrip(tmp_path, capsys):
    root = tmp_path
    project = Path(__file__).resolve().parents[1]
    for relative in BASE_INPUT_PATHS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        # Copy infrastructure text, never the real snapshot, extraction or decisions.
        path.write_bytes(
            (project / relative).read_bytes()
            if relative.startswith(("checks/", "tools/")) or relative == "ontology.yaml"
            else b"synthetic\n"
        )
    write_json(root, "data/ablation_snapshot.json", snapshot())
    write_csv(
        root,
        "data/corpus.csv",
        CORPUS_COLUMNS,
        [
            {
                "article_id": "77",
                "doi": "",
                "title": "Synthetic adapter example",
                "year": "2026",
            }
        ],
    )
    files = [
        {"article_id": "77", "file": "main.pdf", "role": "main", "sha256": "a" * 64}
    ]
    write_csv(root, "data/files.csv", FILES_COLUMNS, files)
    triples = [["main.pdf", "main", "a" * 64]]
    sha = hashlib.sha256(
        json.dumps(triples, separators=(",", ":")).encode()
    ).hexdigest()
    write_csv(
        root,
        "results/extraction_status.csv",
        STATUS_COLUMNS,
        [
            {
                "article_id": "77",
                "status": "complete",
                "files_sha256": sha,
                "reason": "Synthetic fixture",
            }
        ],
    )
    claim = dict.fromkeys(CLAIM_COLUMNS, "synthetic")
    claim.update(
        claim_id="77-c1",
        article_id="77",
        file="main.pdf",
        page="1",
        variable="energy",
        direction="increase",
        basis="own_data",
        medium_class="water",
        material="Au",
    )
    write_csv(root, "results/claims.csv", CLAIM_COLUMNS, [claim])
    write_csv(root, "results/no_claims.csv", NEGATIVE_COLUMNS, [])
    assert main(["prepare"], root=root) == 0
    context = json.loads((root / "results/matching_candidates.json").read_text())
    assert context["candidates"][0]["series"]["series_id"] == "77-s1"
    write_csv(
        root,
        "results/matching_audit.csv",
        AUDIT_COLUMNS,
        [
            {
                "claim_id": "77-c1",
                "series_id": "77-s1",
                "decision": "include",
                "assessment": "direct",
                "reason": "Synthetic matching decision",
                "caveats": "none",
            }
        ],
    )
    assert main(["build", "--stage", "draft"], root=root) == 0
    summary = json.loads((root / "results/summary.json").read_text())
    assert summary["articles"]["prevalence"] == {
        "numerator": 1,
        "denominator": 1,
        "fraction": 1.0,
    }
    assert summary["comparison"]["claim_outcomes"]["77-c1"] == {
        "primary": "all_agree",
        "lenient": "all_agree",
        "n_included": 1,
        "n_qualified": 0,
        "n_unassessable": 0,
    }
    write_json(
        root,
        "checks/matching_review.json",
        {
            "decision": "accepted",
            "reviewer": "Synthetic fixture curator",
            "date": "2026-11-16",
            "inputs": summary["inputs"],
        },
    )
    assert main(["build", "--stage", "final"], root=root) == 0
    report = Report()
    analysis.check_analysis(
        root,
        report,
        {77},
        [claim],
        {"77": "complete"},
        SnapshotTools(root / "data/ablation_snapshot.json"),
        "final",
    )
    assert report.failures == 0, report.messages
    assert "Built final: 1 included pairs" in capsys.readouterr().out
