"""Serial supervision tests with synthetic projects and an offline fake agent."""

import csv
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from ops import run_articles as runner

CHECKER = """import argparse, csv, json
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('--article', type=int, required=True)
p.add_argument('--analysis', choices=['draft'], required=True)
a = p.parse_args()
with open('trace.jsonl', 'a') as f:
    f.write(json.dumps({'kind': 'check', 'article': a.article}) + '\\n')
import os
b = os.environ.get('FAKE_BEHAVIOR', '')
if (b == 'existing_bad' and a.article == 3) or (b == 'checker_fail' and a.article == 1):
    raise SystemExit(7)
statuses = {int(r['article_id']): r['status'] for r in csv.DictReader(open('results/extraction_status.csv'))}
base = Path(f'results/articles/{a.article}')
if statuses.get(a.article) != 'complete' or not all((base / n).is_file() for n in
        ['summary.json', 'matching_candidates.json', 'matching_audit.csv', 'comparison.csv']):
    raise SystemExit(1)
print('synthetic checkpoint passes')
"""

AGENT = """import csv, hashlib, json, os, re, subprocess, sys, time
from pathlib import Path
root = Path.cwd()
prompt = sys.argv[-1]
aid = int(re.search(r'Process only article (\\d+)', prompt).group(1))
def trace(kind):
    with open('trace.jsonl', 'a') as f:
        f.write(json.dumps({'kind': kind, 'article': aid, 'pid': os.getpid(),
            'args': sys.argv[1:], 'web': os.environ.get('AI4SCIENCE_WEB_DISABLED'),
            'lean': os.environ.get('AI4SCIENCE_LEAN_DISABLED')}) + '\\n')
trace('start')
print('fake agent stdout', flush=True)
print('fake agent stderr', file=sys.stderr, flush=True)
b = os.environ.get('FAKE_BEHAVIOR', '')
if b in {'sleep', 'exit_child', 'success_child'}:
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
    Path('.child-pid').write_text(str(child.pid))
    if b == 'sleep':
        time.sleep(60)
    if b == 'exit_child':
        raise SystemExit(4)
if b == 'exit':
    raise SystemExit(4)
if b == 'noop':
    trace('end')
    raise SystemExit(0)
ledger = Path('results/extraction_status.csv')
rows = list(csv.DictReader(ledger.open()))
rows = [r for r in rows if int(r['article_id']) != aid]
rows.append({'article_id': aid, 'status': 'pending' if b == 'pending' else 'complete'})
with ledger.open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['article_id', 'status'])
    w.writeheader()
    w.writerows(rows)
base = Path(f'results/articles/{aid}')
base.mkdir(parents=True, exist_ok=True)
for name in ['summary.json', 'matching_candidates.json', 'matching_audit.csv', 'comparison.csv']:
    (base / name).write_text('{}')
paths = ['METHOD.md', 'requirements.txt', 'tools/series.py', 'tools/ablation_db.py',
    'tools/snapshot_scope.py', 'data/ablation_snapshot.schema.json', 'data/snapshot_manifest.json']
paths += [str(p) for p in sorted(Path('checks/verifier').glob('*.py'))]
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
report = {'step': 'dry', 'status': 'pass', 'scope': {'article_id': aid}, 'violations': [],
    'snapshot_sha256': sha('data/ablation_snapshot.json'),
    'schema_sha256': sha('data/ablation_snapshot.schema.json'),
    'provenance': {'source_sha256': {p: sha(p) for p in paths}}}
if b == 'bad_dry':
    report['scope']['article_id'] = 999
if b != 'missing_dry':
    path = Path(f'results/verifier/articles/{aid}/dry.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report))
if b == 'mutate_source':
    Path('METHOD.md').write_text('changed after dry')
if b != 'dirty':
    subprocess.run(['git', 'add', '.'], check=True)
    subprocess.run(['git', 'commit', '-qm', f'Synthetic article {aid}'], check=True)
trace('end')
"""


def git(root, *args):
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def write_ledger(root, entries):
    with (root / "results/extraction_status.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["article_id", "status"])
        writer.writerows(entries)


def dry_report(root, aid):
    sources = (*runner.PREFLIGHT_SOURCES, "checks/verifier/run.py")

    def sha(p):
        return hashlib.sha256((root / p).read_bytes()).hexdigest()

    return {
        "step": "dry",
        "status": "pass",
        "scope": {"article_id": aid},
        "violations": [],
        "snapshot_sha256": sha("data/ablation_snapshot.json"),
        "schema_sha256": sha("data/ablation_snapshot.schema.json"),
        "provenance": {"source_sha256": {p: sha(p) for p in sources}},
    }


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    for relative in (
        *runner.PREFLIGHT_SOURCES,
        "data/corpus.csv",
        "data/ablation_snapshot.json",
        "checks/verifier/run.py",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic source\n")
    (root / "data/corpus.csv").write_text("article_id,title\n1,One\n2,Two\n3,Three\n")
    (root / "results").mkdir()
    write_ledger(root, [(3, "complete")])
    base = root / "results/articles/3"
    base.mkdir(parents=True)
    for name in (
        "summary.json",
        "matching_candidates.json",
        "matching_audit.csv",
        "comparison.csv",
    ):
        (base / name).write_text("{}")
    path = root / "results/verifier/articles/3/dry.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(dry_report(root, 3)))
    (root / "checks/check.py").write_text(CHECKER)
    (root / ".venv/bin").mkdir(parents=True)
    (root / ".venv/bin/python").symlink_to(sys.executable)
    (root / ".gitignore").write_text(".venv/\ntrace.jsonl\n.child-pid\n")
    git(root, "init", "-q")
    git(root, "config", "user.name", "Synthetic test")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "add", ".")
    git(root, "commit", "-qm", "Synthetic inputs")
    agent = tmp_path / "fake-ai4science"
    agent.write_text(f"#!{sys.executable}\n" + AGENT)
    agent.chmod(0o700)
    monkeypatch.delenv("FAKE_BEHAVIOR", raising=False)
    return SimpleNamespace(
        root=root,
        agent=agent,
        logs=tmp_path / "logs",
        args=[
            "--project",
            str(root),
            "--agent",
            str(agent),
            "--log-dir",
            str(tmp_path / "logs"),
        ],
    )


def events(project):
    path = project.root / "trace.jsonl"
    return (
        [json.loads(line) for line in path.read_text().splitlines()]
        if path.exists()
        else []
    )


def test_serial_fresh_processes_default_mode_and_exact_prompt(project):
    assert runner.main(project.args) == 0
    trace = events(project)
    assert [(e["kind"], e["article"]) for e in trace] == [
        ("check", 3),
        ("start", 1),
        ("end", 1),
        ("check", 1),
        ("start", 2),
        ("end", 2),
        ("check", 2),
    ]
    starts = [e for e in trace if e["kind"] == "start"]
    assert len({e["pid"] for e in starts}) == 2
    for entry in starts:
        assert entry["args"] == [
            "run",
            "--no-lean",
            "--mode",
            "smart_approve",
            "--",
            runner.PROMPT.format(article=entry["article"]),
        ]
        assert entry["web"] == entry["lean"] == "1"
    assert git(project.root, "status", "--porcelain") == ""
    assert not (project.root / "results/comparison.csv").exists()
    (run_dir,) = project.logs.iterdir()
    assert json.loads((run_dir / "queue.json").read_text())["queue"] == [1, 2]
    for aid in (1, 2):
        log = (run_dir / f"{aid}.log").read_text()
        assert "fake agent stdout" in log and "fake agent stderr" in log
        assert "[runner] exit=0" in log
    assert run_dir.stat().st_mode & 0o777 == 0o700
    assert (run_dir / "1.log").stat().st_mode & 0o777 == 0o600


def test_limit_mode_override_and_restart_skip_only_validated_articles(project):
    assert runner.main([*project.args, "--mode", "auto", "--limit", "1"]) == 0
    (start,) = [e for e in events(project) if e["kind"] == "start"]
    assert start["args"][3] == "auto"
    assert runner.main(project.args) == 0
    starts = [e["article"] for e in events(project) if e["kind"] == "start"]
    assert starts == [1, 2]
    before = len(events(project))
    assert runner.main(project.args) == 0
    assert all(e["kind"] == "check" for e in events(project)[before:])


def test_dry_run_is_read_only_even_when_checkout_is_dirty(project, capsys):
    (project.root / "METHOD.md").write_text("curator edit")
    assert runner.main([*project.args, "--dry-run"]) == 0
    assert "Queue (corpus order): [1, 2]" in capsys.readouterr().out
    assert not project.logs.exists()
    assert not (project.root / ".git/ai4science-batch.lock").exists()
    assert events(project) == []


@pytest.mark.parametrize(
    "behavior",
    [
        "exit",
        "noop",
        "pending",
        "checker_fail",
        "bad_dry",
        "missing_dry",
        "dirty",
        "mutate_source",
    ],
)
def test_failed_or_unfinished_article_never_advances(project, monkeypatch, behavior):
    monkeypatch.setenv("FAKE_BEHAVIOR", behavior)
    assert runner.main(project.args) == 1
    assert [e["article"] for e in events(project) if e["kind"] == "start"] == [1]
    if behavior == "exit":
        (log,) = project.logs.glob("*/1.log")
        assert "[runner] exit=4" in log.read_text()


def test_invalid_existing_checkpoint_stops_before_any_agent(project, monkeypatch):
    monkeypatch.setenv("FAKE_BEHAVIOR", "existing_bad")
    assert runner.main(project.args) == 1
    assert events(project) == [{"kind": "check", "article": 3}]


@pytest.mark.parametrize(
    "change",
    [
        "snapshot",
        "schema",
        "source",
        "new_source",
        "missing_source_hash",
        "failed",
        "violations",
        "wrong_step",
        "wrong_scope",
        "malformed",
    ],
)
def test_preflight_fails_closed_on_changed_or_invalid_evidence(project, change):
    root = project.root
    path = root / "results/verifier/articles/3/dry.json"
    report = json.loads(path.read_text())
    if change in {"snapshot", "schema", "source"}:
        relative = {
            "snapshot": "data/ablation_snapshot.json",
            "schema": "data/ablation_snapshot.schema.json",
            "source": "METHOD.md",
        }[change]
        (root / relative).write_text("changed")
    elif change == "new_source":
        (root / "checks/verifier/new_test.py").write_text("new source")
    elif change == "missing_source_hash":
        report["provenance"]["source_sha256"].pop("METHOD.md")
    elif change == "failed":
        report["status"] = "fail"
    elif change == "violations":
        report["violations"] = ["synthetic violation"]
    elif change == "wrong_step":
        report["step"] = "smoke"
    elif change == "wrong_scope":
        report["scope"] = {"article_id": 1}
    elif change == "malformed":
        path.write_text("{")
    if change != "malformed":
        path.write_text(json.dumps(report))
    with pytest.raises((runner.BatchError, ValueError)):
        runner.validate_preflight(root, 3)


def test_stale_existing_preflight_is_not_silently_skipped(project):
    (project.root / "METHOD.md").write_text("curator change")
    git(project.root, "add", "METHOD.md")
    git(project.root, "commit", "-qm", "Synthetic rule change")
    assert runner.main(project.args) == 1
    assert not any(e["kind"] == "start" for e in events(project))


def test_dirty_checkout_never_launches_or_commits(project):
    before = git(project.root, "rev-parse", "HEAD")
    (project.root / "METHOD.md").write_text("uncommitted curator change")
    assert runner.main(project.args) == 1
    assert events(project) == []
    assert git(project.root, "rev-parse", "HEAD") == before


def test_second_runner_cannot_bypass_lock_with_different_log_directory(project):
    with (project.root / ".git/ai4science-batch.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert (
            runner.main(
                [*project.args, "--log-dir", str(project.logs.parent / "other")]
            )
            == 1
        )
    assert events(project) == []


def test_project_logs_are_rejected(project):
    assert (
        runner.main([*project.args, "--log-dir", str(project.root / "results/logs")])
        == 1
    )
    assert events(project) == []
    assert not (project.root / "results/logs").exists()


@pytest.mark.parametrize(
    "corpus,ledger",
    [
        ("article_id\n1\n1\n", "article_id,status\n"),
        ("article_id\n../1\n", "article_id,status\n"),
        ("article_id\n0\n", "article_id,status\n"),
        ("article_id\n1\n", "article_id,status\n2,complete\n"),
        ("article_id\n1\n", "article_id,status\n1,complete\n1,pending\n"),
        ("article_id\n1\n", "article_id,status\n1,invented\n"),
    ],
)
def test_malformed_queue_never_launches(project, corpus, ledger):
    (project.root / "data/corpus.csv").write_text(corpus)
    (project.root / "results/extraction_status.csv").write_text(ledger)
    assert runner.main([*project.args, "--dry-run"]) == 1
    assert events(project) == []


@pytest.mark.parametrize(
    "args",
    [
        ["--limit", "0"],
        ["--timeout", "0"],
        ["--timeout", "nan"],
        ["--timeout", "inf"],
        ["--mode", "chat"],
    ],
)
def test_invalid_arguments_are_rejected(args):
    with pytest.raises(SystemExit) as error:
        runner.main(args)
    assert error.value.code == 2


def test_missing_agent_is_reported_without_model_call(project):
    assert runner.main([*project.args, "--agent", "/nonexistent/ai4science"]) == 1
    assert events(project) == []


def assert_stopped(pid):
    """Allow kernel signal delivery; adopted zombies cannot execute any work."""
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            if Path(f"/proc/{pid}/stat").read_text().split()[2] == "Z":
                return
        except FileNotFoundError:
            return
        time.sleep(0.01)
    pytest.fail(f"Process {pid} survived process-group termination")


def test_timeout_stops_launcher_and_its_child(project, monkeypatch):
    monkeypatch.setenv("FAKE_BEHAVIOR", "sleep")
    assert runner.main([*project.args, "--timeout", "0.3"]) == 1
    trace = events(project)
    (start,) = [e for e in trace if e["kind"] == "start"]
    child = int((project.root / ".child-pid").read_text())
    for pid in (start["pid"], child):
        assert_stopped(pid)
    assert not any(e["article"] == 2 for e in trace)


@pytest.mark.parametrize("signum", [signal.SIGTERM, signal.SIGINT])
def test_interrupt_uses_child_cleanup_and_returns_nonzero(project, signum):
    env = {**os.environ, "FAKE_BEHAVIOR": "sleep"}
    process = subprocess.Popen(
        [sys.executable, str(Path(runner.__file__)), *project.args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        deadline = time.monotonic() + 10
        while (
            not (project.root / ".child-pid").exists() and time.monotonic() < deadline
        ):
            time.sleep(0.02)
        assert (project.root / ".child-pid").exists()
        process.send_signal(signum)
        out, err = process.communicate(timeout=10)
        assert process.returncode == 130, (out, err)
        assert "interrupted" in err
        for event in events(project):
            if event["kind"] == "start":
                assert not Path(f"/proc/{event['pid']}").exists()
        child = int((project.root / ".child-pid").read_text())
        assert_stopped(child)
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()


def test_relative_agent_executable_is_resolved_before_changing_directory(
    project, monkeypatch
):
    monkeypatch.chdir(project.agent.parent)
    assert (
        runner.main([*project.args, "--agent", "./fake-ai4science", "--limit", "1"])
        == 0
    )
    assert [e["article"] for e in events(project) if e["kind"] == "start"] == [1]


@pytest.mark.parametrize("behavior,code", [("exit_child", 1), ("success_child", 0)])
def test_launcher_exit_also_cleans_up_remaining_children(
    project, monkeypatch, behavior, code
):
    monkeypatch.setenv("FAKE_BEHAVIOR", behavior)
    assert runner.main([*project.args, "--limit", "1"]) == code
    child = int((project.root / ".child-pid").read_text())
    assert_stopped(child)


def test_complete_extraction_without_checkpoint_is_queued_for_resume(project):
    write_ledger(project.root, [(1, "complete"), (3, "complete")])
    assert runner.plan(project.root) == ([1, 2], [3])


def test_no_ledger_means_all_articles_are_unassessed(project):
    (project.root / "results/extraction_status.csv").unlink()
    assert runner.plan(project.root) == ([1, 2, 3], [])
