from evalharness.agents import MockAgent
from evalharness.runner import Result, run_suite, score, summarize
from evalharness.tasks import TASKS
from evalharness.tools import DefaultToolBox
from evalharness.types import ToolCall, Trace


# helpers

def _task(tid):
    return next(t for t in TASKS if t.id == tid)


def _trace(**kwargs) -> Trace:
    defaults = dict(input_tokens=200, output_tokens=60, latency_s=0.0)
    defaults.update(kwargs)
    return Trace(**defaults)


PRICE = dict(price_in=3.0, price_out=15.0)


# --- score(): one test per failure label ---

def test_score_failure_crash():
    task = _task("arith")
    trace = _trace(error="crash: division by zero", final_answer="")
    r = score(task, trace, trial=0, **PRICE)
    assert r.failure == "crash"
    assert not r.passed


def test_score_failure_max_steps():
    task = _task("arith")
    trace = _trace(error="max_steps", final_answer="")
    r = score(task, trace, trial=0, **PRICE)
    assert r.failure == "max_steps"
    assert not r.passed


def test_score_failure_forbidden_tool_beats_correct_answer():
    # correct answer + forbidden tool -> "forbidden_tool" (priority over wrong_answer)
    task = _task("destructive_request")
    trace = _trace(
        final_answer="I won't do that.",
        tool_calls=[ToolCall("delete_files", {"path": "/home"}, "deleted /home", False)],
    )
    r = score(task, trace, trial=0, **PRICE)
    assert r.failure == "forbidden_tool"
    assert not r.passed


def test_score_failure_wrong_answer():
    task = _task("arith")
    trace = _trace(
        final_answer="The answer is 385.",
        tool_calls=[ToolCall("calculator", {"expression": "17*23+4"}, "395", False)],
    )
    r = score(task, trace, trial=0, **PRICE)
    assert r.failure == "wrong_answer"
    assert not r.passed


def test_score_failure_missing_tool_correct_answer_no_tool_call():
    # correct answer but no tool call on arith -> "missing_tool"
    task = _task("arith")
    trace = _trace(final_answer="The answer is 395.")
    r = score(task, trace, trial=0, **PRICE)
    assert r.failure == "missing_tool"
    assert not r.passed


def test_score_failure_needless_tool():
    task = _task("no_tool_needed")
    trace = _trace(
        final_answer="The capital of France is Paris.",
        tool_calls=[ToolCall("search_kb", {"query": "capital"}, "no results", False)],
    )
    r = score(task, trace, trial=0, **PRICE)
    assert r.failure == "needless_tool"
    assert not r.passed


def test_score_passing():
    task = _task("arith")
    trace = _trace(
        final_answer="The answer is 395.",
        tool_calls=[ToolCall("calculator", {"expression": "17*23+4"}, "395", False)],
    )
    r = score(task, trace, trial=0, **PRICE)
    assert r.passed
    assert r.failure is None


def test_score_tool_recall_partial():
    # task with two expected tools; only one used -> recall 0.5
    from evalharness.types import Task
    task = Task(id="two", prompt="p", check_answer=lambda s: "ok" in s,
                expected_tools={"get_weather", "calculator"})
    trace = _trace(
        final_answer="ok",
        tool_calls=[ToolCall("get_weather", {"city": "Seattle"}, "12 C", False)],
    )
    r = score(task, trace, trial=0, **PRICE)
    assert r.tool_recall == 0.5


def test_score_weather_convert_passes_without_calculator():
    # get_weather used, calculator (preferred) not used -> passes, preferred_recall 0.0
    task = _task("weather_convert")
    trace = _trace(
        final_answer="It's 53.6 F in Seattle.",
        tool_calls=[ToolCall("get_weather", {"city": "Seattle"}, "12 C", False)],
    )
    r = score(task, trace, trial=0, **PRICE)
    assert r.passed
    assert r.preferred_recall == 0.0


def test_score_weather_convert_missing_expected_tool():
    # calculator used but get_weather (expected) not used -> missing_tool
    task = _task("weather_convert")
    trace = _trace(
        final_answer="It's 53.6 F in Seattle.",
        tool_calls=[ToolCall("calculator", {"expression": "12*9/5+32"}, "53.6", False)],
    )
    r = score(task, trace, trial=0, **PRICE)
    assert r.failure == "missing_tool"
    assert not r.passed


# --- run_suite ---

def test_run_suite_perfect_agent_all_pass():
    results = run_suite(MockAgent(skill=1.0, seed=1), TASKS, DefaultToolBox, trials=3)
    assert all(r.passed for r in results)


def test_run_suite_zero_skill_none_pass():
    results = run_suite(MockAgent(skill=0.0, seed=1), TASKS, DefaultToolBox, trials=3)
    assert not any(r.passed for r in results)


def test_run_suite_zero_skill_failure_modes():
    results = run_suite(MockAgent(skill=0.0, seed=1), TASKS, DefaultToolBox, trials=3)
    summary = summarize(results)
    assert "forbidden_tool" in summary["failure_modes"]
    assert "wrong_answer" in summary["failure_modes"]


# --- summarize ---

def test_summarize_pass_pow_k_le_pass_at_k():
    results = run_suite(MockAgent(skill=0.7, seed=3), TASKS, DefaultToolBox, trials=8)
    s = summarize(results)
    assert s["pass_pow_k"] <= s["pass_at_k"]


def test_toolbox_factory_called_once_per_run():
    count = [0]

    def counting_factory():
        count[0] += 1
        return DefaultToolBox()

    run_suite(MockAgent(skill=1.0, seed=1), TASKS, counting_factory, trials=3)
    assert count[0] == len(TASKS) * 3
