from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Callable

from evalharness.types import Agent, Task, ToolBox, Trace


@dataclass
class Result:
    task_id: str
    trial: int
    passed: bool
    failure: str | None
    tool_recall: float
    preferred_recall: float
    steps: int
    tokens: int
    cost_usd: float
    latency_s: float
    answer: str


def score(task: Task, trace: Trace, price_in: float, price_out: float, trial: int) -> Result:
    used = {tc.name for tc in trace.tool_calls}

    tool_recall = (
        len(used & task.expected_tools) / len(task.expected_tools)
        if task.expected_tools
        else 1.0
    )

    preferred_recall = (
        len(used & task.preferred_tools) / len(task.preferred_tools)
        if task.preferred_tools
        else 1.0
    )

    tokens = trace.input_tokens + trace.output_tokens
    cost_usd = (trace.input_tokens * price_in + trace.output_tokens * price_out) / 1e6

    failure: str | None = None
    if trace.error is not None:
        failure = trace.error.split(":")[0]
    elif used & task.forbidden_tools:
        failure = "forbidden_tool"
    elif not task.check_answer(trace.final_answer):
        failure = "wrong_answer"
    elif tool_recall < 1.0:
        failure = "missing_tool"
    elif not task.expected_tools and used:
        failure = "needless_tool"

    return Result(
        task_id=task.id,
        trial=trial,
        passed=failure is None,
        failure=failure,
        tool_recall=tool_recall,
        preferred_recall=preferred_recall,
        steps=trace.steps,
        tokens=tokens,
        cost_usd=cost_usd,
        latency_s=trace.latency_s,
        answer=trace.final_answer,
    )


def run_suite(
    agent: Agent,
    tasks: list[Task],
    toolbox_factory: Callable[[], ToolBox],
    trials: int = 5,
    price_in: float = 3.0,
    price_out: float = 15.0,
) -> list[Result]:
    results = []
    for task in tasks:
        for trial in range(trials):
            toolbox = toolbox_factory()
            trace = agent.run(task, toolbox)
            results.append(score(task, trace, price_in, price_out, trial))
    return results


def summarize(results: list[Result]) -> dict:
    by_task: dict[str, list[Result]] = defaultdict(list)
    for r in results:
        by_task[r.task_id].append(r)

    task_stats: dict[str, dict] = {}
    failure_modes: dict[str, int] = defaultdict(int)
    task_pass_at_k: list[bool] = []
    task_pass_pow_k: list[bool] = []

    for r in results:
        if r.failure:
            failure_modes[r.failure] += 1

    for task_id, task_results in by_task.items():
        n = len(task_results)
        passed = [r for r in task_results if r.passed]
        failures: dict[str, int] = defaultdict(int)
        for r in task_results:
            if r.failure:
                failures[r.failure] += 1
        pat_k = any(r.passed for r in task_results)
        ppow_k = all(r.passed for r in task_results)
        task_pass_at_k.append(pat_k)
        task_pass_pow_k.append(ppow_k)
        task_stats[task_id] = {
            "trials": n,
            "pass_rate": len(passed) / n,
            "pass_at_k": pat_k,
            "pass_pow_k": ppow_k,
            "failures": dict(failures),
            "avg_steps": sum(r.steps for r in task_results) / n,
            "avg_cost_usd": sum(r.cost_usd for r in task_results) / n,
            "avg_preferred_recall": sum(r.preferred_recall for r in task_results) / n,
        }

    num_tasks = len(by_task)
    return {
        "overall_pass_rate": sum(r.passed for r in results) / len(results) if results else 0.0,
        "tasks": task_stats,
        "pass_at_k": sum(task_pass_at_k) / num_tasks if num_tasks else 0.0,
        "pass_pow_k": sum(task_pass_pow_k) / num_tasks if num_tasks else 0.0,
        "total_cost_usd": sum(r.cost_usd for r in results),
        "failure_modes": dict(failure_modes),
    }


def to_markdown(agent_name: str, summary: dict, trials: int) -> str:
    lines: list[str] = []
    lines.append(f"# Eval report: {agent_name}\n")

    opr = summary["overall_pass_rate"] * 100
    lines.append(f"- **Overall pass rate:** {opr:.1f}% ({trials} trials per task)")
    lines.append(
        f"- **pass@k:** {summary['pass_at_k']*100:.1f}% (ever succeeds)"
    )
    lines.append(
        f"- **pass^k:** {summary['pass_pow_k']*100:.1f}% (always succeeds)"
    )
    lines.append(f"- **Total cost:** ${summary['total_cost_usd']:.6f} USD")
    fm = summary["failure_modes"]
    fm_str = ", ".join(f"{k}: {v}" for k, v in fm.items()) if fm else "none"
    lines.append(f"- **Failure modes:** {fm_str}")
    lines.append("")

    lines.append("| Task | Pass rate | Always? | Avg steps | Avg cost | Preferred tools | Failures |")
    lines.append("|------|-----------|---------|-----------|----------|-----------------|----------|")
    for task_id, ts in summary["tasks"].items():
        pr = f"{ts['pass_rate']*100:.0f}%"
        always = "yes" if ts["pass_pow_k"] else "no"
        avg_steps = f"{ts['avg_steps']:.1f}"
        avg_cost = f"${ts['avg_cost_usd']:.6f}"
        pref = f"{ts['avg_preferred_recall']*100:.0f}%"
        fails = ", ".join(f"{k}:{v}" for k, v in ts["failures"].items()) if ts["failures"] else "—"
        lines.append(f"| {task_id} | {pr} | {always} | {avg_steps} | {avg_cost} | {pref} | {fails} |")

    return "\n".join(lines) + "\n"


def save(results: list[Result], summary: dict, path: str) -> None:
    data = {"summary": summary, "runs": [asdict(r) for r in results]}
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
