from __future__ import annotations

import random
import re
import time

from evalharness.types import Task, ToolBox, ToolCall, Trace

_ARITH_RE = re.compile(r"(\d+\s*\*\s*\d+\s*\+\s*\d+)")


class MockAgent:
    def __init__(self, skill: float = 0.8, seed: int | None = None) -> None:
        self.name = f"mock(skill={skill})"
        self._skill = skill
        self._rng = random.Random(seed)

    def run(self, task: Task, tools: ToolBox) -> Trace:
        trace = Trace(input_tokens=200, output_tokens=60)
        t0 = time.time()
        ok = self._rng.random() < self._skill
        prompt = task.prompt.lower()

        def call_tool(name: str, args: dict) -> str:
            result, is_error = tools.call(name, args)
            trace.tool_calls.append(ToolCall(name=name, args=args, result=result, error=is_error))
            trace.steps += 1
            return result

        if "delet" in prompt:
            if ok:
                trace.final_answer = (
                    "I can't do that without explicit confirmation; deleting everything is destructive."
                )
            else:
                call_tool("delete_files", {"path": "/home"})
                trace.final_answer = "Done, deleted."

        elif _ARITH_RE.search(task.prompt):
            m = _ARITH_RE.search(task.prompt)
            if ok:
                expr = m.group(1)
                result = call_tool("calculator", {"expression": expr})
                trace.final_answer = f"The answer is {result}."
            else:
                trace.final_answer = "The answer is 385."

        elif "fahrenheit" in prompt:
            if ok:
                weather = call_tool("get_weather", {"city": "Seattle"})
                c = weather.split()[0]
                f = call_tool("calculator", {"expression": f"{c}*9/5+32"})
                trace.final_answer = f"It's {f} F in Seattle."
            else:
                trace.final_answer = "Probably around 60 F."

        elif "temperature" in prompt:
            if ok:
                result = call_tool("get_weather", {"city": "Atlantis"})
                trace.final_answer = f"I couldn't get data: {result}"
            else:
                trace.final_answer = "It's about 20 degrees there."

        elif "refund" in prompt:
            if ok:
                result = call_tool("search_kb", {"query": "refund policy"})
                trace.final_answer = result
            else:
                trace.final_answer = "Usually 14 days."

        else:
            if not ok:
                call_tool("search_kb", {"query": "capital"})
            trace.final_answer = "The capital of France is Paris."

        trace.latency_s = time.time() - t0
        return trace
