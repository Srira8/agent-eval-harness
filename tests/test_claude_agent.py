from types import SimpleNamespace

from evalharness.agents import ClaudeAgent
from evalharness.tools import DefaultToolBox
from evalharness.types import Task


# --- fake infrastructure ---

def _text_resp(text, in_tok=100, out_tok=50):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok),
    )


def _tool_resp(name, tool_id, input_dict, in_tok=100, out_tok=50):
    return SimpleNamespace(
        content=[SimpleNamespace(type="tool_use", id=tool_id, name=name, input=input_dict)],
        usage=SimpleNamespace(input_tokens=in_tok, output_tokens=out_tok),
    )


class FakeMessages:
    def __init__(self, responses):
        self._responses = iter(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return next(self._responses)


class FakeClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)


def _task(max_steps=6):
    return Task(id="t", prompt="test", check_answer=lambda s: True, max_steps=max_steps)


# --- tests ---

def test_direct_answer_no_tools():
    client = FakeClient([_text_resp("42")])
    trace = ClaudeAgent(model="m", client=client).run(_task(), DefaultToolBox())
    assert trace.final_answer == "42"
    assert trace.tool_calls == []
    assert trace.steps == 1
    assert trace.error is None


def test_tool_use_then_text():
    responses = [
        _tool_resp("calculator", "tc1", {"expression": "2+2"}, in_tok=100, out_tok=30),
        _text_resp("The answer is 4.", in_tok=120, out_tok=40),
    ]
    client = FakeClient(responses)
    trace = ClaudeAgent(model="m", client=client).run(_task(), DefaultToolBox())

    assert trace.steps == 2
    assert trace.input_tokens == 220
    assert trace.output_tokens == 70
    assert len(trace.tool_calls) == 1
    assert trace.tool_calls[0].name == "calculator"
    assert trace.tool_calls[0].result == "4"
    assert not trace.tool_calls[0].error
    assert trace.final_answer == "The answer is 4."
    assert trace.error is None

    # tool_result message was sent back in the second call
    second_messages = client.messages.calls[1]["messages"]
    user_msg = second_messages[-1]
    assert user_msg["role"] == "user"
    assert any(
        b.get("type") == "tool_result" and b.get("tool_use_id") == "tc1"
        for b in user_msg["content"]
    )


def test_always_tool_use_triggers_max_steps():
    responses = [_tool_resp("search_kb", f"id{i}", {"query": "x"}) for i in range(2)]
    client = FakeClient(responses)
    trace = ClaudeAgent(model="m", client=client).run(_task(max_steps=2), DefaultToolBox())
    assert trace.error == "max_steps"


def test_client_raises_produces_crash():
    class ErrorMessages:
        def create(self, **kwargs):
            raise RuntimeError("network error")

    class ErrorClient:
        messages = ErrorMessages()

    trace = ClaudeAgent(model="m", client=ErrorClient()).run(_task(), DefaultToolBox())
    assert trace.error is not None
    assert trace.error.startswith("crash")


def test_tool_error_recorded_not_crash():
    responses = [
        _tool_resp("get_weather", "gw1", {"city": "Atlantis"}),
        _text_resp("I couldn't get the weather for Atlantis."),
    ]
    client = FakeClient(responses)
    trace = ClaudeAgent(model="m", client=client).run(_task(), DefaultToolBox())

    assert len(trace.tool_calls) == 1
    assert trace.tool_calls[0].name == "get_weather"
    assert trace.tool_calls[0].error is True
    assert trace.error is None
