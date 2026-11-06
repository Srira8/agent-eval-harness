from evalharness.types import Task, Trace


def test_trace_tool_calls_not_shared():
    t1 = Trace()
    t2 = Trace()
    t1.tool_calls.append(object())
    assert len(t2.tool_calls) == 0


def test_task_expected_tools_not_shared():
    task1 = Task(id="a", prompt="p", check_answer=lambda s: True)
    task2 = Task(id="b", prompt="p", check_answer=lambda s: True)
    task1.expected_tools.add("search")
    assert "search" not in task2.expected_tools


def test_task_check_answer_callable():
    task = Task(id="c", prompt="What is 2+2?", check_answer=lambda s: "4" in s)
    assert task.check_answer("The answer is 4")
    assert not task.check_answer("I don't know")
