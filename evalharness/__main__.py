from __future__ import annotations

import argparse
import os
import sys

from evalharness.agents import MockAgent
from evalharness.runner import run_suite, save, summarize, to_markdown
from evalharness.tasks import TASKS
from evalharness.tools import DefaultToolBox


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the agent eval harness.")
    parser.add_argument("--agent", choices=["mock", "claude"], default="mock")
    parser.add_argument("--skill", type=float, default=0.8, help="Mock success probability")
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", default="report")
    parser.add_argument("--model", default="claude-sonnet-5-5")
    parser.add_argument("--price-in", type=float, default=3.0, dest="price_in",
                        help="USD per million input tokens")
    parser.add_argument("--price-out", type=float, default=15.0, dest="price_out",
                        help="USD per million output tokens")
    args = parser.parse_args(argv)

    if args.agent == "claude":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("Error: ANTHROPIC_API_KEY is not set. Export it before running with --agent claude.",
                  file=sys.stderr)
            sys.exit(1)
        from evalharness.agents import ClaudeAgent
        agent = ClaudeAgent(model=args.model)
        n_runs = len(TASKS) * args.trials
        print(f"Running {n_runs} evals ({args.trials} trials × {len(TASKS)} tasks) with {agent.name}...")
    else:
        agent = MockAgent(skill=args.skill, seed=args.seed)

    results = run_suite(
        agent, TASKS, DefaultToolBox,
        trials=args.trials,
        price_in=args.price_in,
        price_out=args.price_out,
    )
    summary = summarize(results)

    save(results, summary, f"{args.out}.json")

    md = to_markdown(agent.name, summary, args.trials)
    with open(f"{args.out}.md", "w") as f:
        f.write(md)

    print(md)


if __name__ == "__main__":
    main()
