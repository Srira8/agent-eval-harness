import json

from evalharness.agents import MockAgent
from evalharness.runner import run_suite, save, summarize, to_markdown
from evalharness.tasks import TASKS
from evalharness.tools import DefaultToolBox


def _perfect_summary():
    results = run_suite(MockAgent(skill=1.0, seed=0), TASKS, DefaultToolBox, trials=3)
    return summarize(results), results


def test_to_markdown_contains_agent_name():
    summary, _ = _perfect_summary()
    md = to_markdown("mock(skill=1.0)", summary, trials=3)
    assert "mock(skill=1.0)" in md


def test_to_markdown_shows_100_percent():
    summary, _ = _perfect_summary()
    md = to_markdown("mock(skill=1.0)", summary, trials=3)
    assert "100%" in md or "100.0%" in md


def test_to_markdown_contains_all_task_ids():
    summary, _ = _perfect_summary()
    md = to_markdown("mock(skill=1.0)", summary, trials=3)
    for task in TASKS:
        assert task.id in md


def test_save_roundtrip(tmp_path):
    summary, results = _perfect_summary()
    path = str(tmp_path / "out.json")
    save(results, summary, path)
    with open(path) as f:
        data = json.load(f)
    assert "summary" in data
    assert "runs" in data
    assert len(data["runs"]) == len(TASKS) * 3


def test_main_creates_files(tmp_path):
    from evalharness.__main__ import main
    out = str(tmp_path / "r")
    main(["--agent", "mock", "--trials", "2", "--seed", "1", "--out", out])
    assert (tmp_path / "r.json").exists()
    assert (tmp_path / "r.md").exists()


def test_import_does_not_create_files(tmp_path):
    import importlib
    import evalharness.__main__  # noqa: F401 — just importing
    importlib.import_module("evalharness.__main__")
    assert list(tmp_path.iterdir()) == []
