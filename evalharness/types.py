from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from typing import Protocol, runtime_checkable


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]
    result: str = ""
    error: bool = False


@dataclass
class Trace:
    final_answer: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    steps: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    error: str | None = None  # either "crash: ..." or "max_steps"


@dataclass
class Task:
    id: str
    prompt: str
    check_answer: Callable[[str], bool]
    expected_tools: set[str] = field(default_factory=set)
    preferred_tools: set[str] = field(default_factory=set)
    forbidden_tools: set[str] = field(default_factory=set)
    max_steps: int = 6


@runtime_checkable
class ToolBox(Protocol):
    schemas: list[dict]

    def call(self, name: str, args: dict) -> tuple[str, bool]: ...


@runtime_checkable
class Agent(Protocol):
    name: str

    def run(self, task: Task, tools: ToolBox) -> Trace: ...
