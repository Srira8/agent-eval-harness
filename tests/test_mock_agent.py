from evalharness.agents import MockAgent
from evalharness.tasks import TASKS
from evalharness.tools import DefaultToolBox


def _run(task, skill, seed=42):
    return MockAgent(skill=skill, seed=seed).run(task, DefaultToolBox())


def _tool_names(trace):
    return {tc.name for tc in trace.tool_calls}


# --- skill=1.0: every task passes its checker and uses expected tools ---

def test_perfect_agent_passes_all_tasks():
    for task in TASKS:
        trace = _run(task, skill=1.0)
        assert task.check_answer(trace.final_answer), (
            f"task={task.id} answer={trace.final_answer!r}"
        )


def test_perfect_agent_uses_expected_tools():
    for task in TASKS:
        trace = _run(task, skill=1.0)
        used = _tool_names(trace)
        assert task.expected_tools.issubset(used), (
            f"task={task.id} expected={task.expected_tools} used={used}"
        )


def test_perfect_agent_avoids_forbidden_tools():
    for task in TASKS:
        trace = _run(task, skill=1.0)
        used = _tool_names(trace)
        assert used.isdisjoint(task.forbidden_tools), (
            f"task={task.id} forbidden={task.forbidden_tools} used={used}"
        )


# --- skill=0.0 failure modes ---

def _task(tid):
    return next(t for t in TASKS if t.id == tid)


def test_zero_skill_destructive_uses_delete_files():
    trace = _run(_task("destructive_request"), skill=0.0)
    assert "delete_files" in _tool_names(trace)


def test_zero_skill_arith_fails_check():
    trace = _run(_task("arith"), skill=0.0)
    assert not _task("arith").check_answer(trace.final_answer)


def test_zero_skill_weather_convert_fails_check():
    trace = _run(_task("weather_convert"), skill=0.0)
    assert not _task("weather_convert").check_answer(trace.final_answer)


def test_zero_skill_kb_lookup_fails_check():
    trace = _run(_task("kb_lookup"), skill=0.0)
    assert not _task("kb_lookup").check_answer(trace.final_answer)


def test_zero_skill_unknown_city_fails_check():
    trace = _run(_task("unknown_city"), skill=0.0)
    assert not _task("unknown_city").check_answer(trace.final_answer)


def test_zero_skill_no_tool_needed_makes_needless_call():
    trace = _run(_task("no_tool_needed"), skill=0.0)
    assert len(trace.tool_calls) > 0


# --- reproducibility ---

def test_same_seed_gives_identical_results():
    task = _task("arith")
    t1 = _run(task, skill=0.5, seed=7)
    t2 = _run(task, skill=0.5, seed=7)
    assert t1.final_answer == t2.final_answer
    assert [tc.name for tc in t1.tool_calls] == [tc.name for tc in t2.tool_calls]


def test_different_seeds_eventually_differ():
    task = _task("arith")
    answers = {_run(task, skill=0.5, seed=s).final_answer for s in range(50)}
    assert len(answers) > 1
