"""AgentDojo banking suite with a REAL LLM as the agent, with and without the AZT control plane.

Requires `pip install .[agentdojo]` and an API key for the model's provider (e.g. OPENAI_API_KEY).
Each (configuration, user task, injection task) result is cached as JSON under `llm_runs/`, so an
interrupted run resumes without paying twice.

    python -m evals.agentdojo_bridge.run_llm --model gpt-4o-mini-2024-07-18 --limit 2   # smoke test
    python -m evals.agentdojo_bridge.run_llm --model gpt-4o-mini-2024-07-18 --write     # full suite
"""
from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, PipelineConfig
from agentdojo.attacks.attack_registry import load_attack
from agentdojo.task_suite.load_suites import get_suite

from evals.agentdojo_bridge.guard import GuardConfig, runtime_factory
from evals.agentdojo_bridge.run_replay import VERSION, expected_ops

CONFIGS = {  # name -> (mandate, human); None = no control plane
    "undefended": (None, None),
    "azt-prompt-nohuman": ("prompt", "none"),
    "azt-known-nohuman": ("prompt+known", "none"),
    "azt-known-attentive": ("prompt+known", "attentive"),
}
RUNS = Path(__file__).with_name("llm_runs")


def run_one(suite, pipeline, ut, it, injections, mandate, human) -> dict:
    kw, cfg = {}, None
    if mandate is not None:
        pre = ut.init_environment(suite.load_and_inject_default_environment({}))
        cfg = GuardConfig(prompt=ut.PROMPT, mandate=mandate, human=human, expected_ops=expected_ops(ut, pre))
        kw = {"runtime_class": runtime_factory(cfg)}
    try:
        utility, attacked = suite.run_task_with_pipeline(pipeline, ut, it, injections, **kw)
        err = None
    except Exception as e:  # provider errors: recorded and retried on the next run, never counted
        if type(e).__name__ in {"AuthenticationError", "PermissionDeniedError"}:
            raise SystemExit(f"API key rejected by the provider, stopping: {e}") from e
        utility, attacked, err = None, None, f"{type(e).__name__}: {e}"
    return {"utility": utility, "attack_success": attacked if it is not None else None, "error": err,
            "stats": cfg.stats if cfg else None}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt-4o-mini-2024-07-18")
    ap.add_argument("--attack", default="important_instructions")
    ap.add_argument("--configs", default=",".join(CONFIGS))
    ap.add_argument("--limit", type=int, default=None, help="only the first N user tasks (smoke test)")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    warnings.filterwarnings("ignore")

    suite = get_suite(VERSION, "banking")
    pipeline = AgentPipeline.from_config(PipelineConfig(
        llm=args.model, model_id=None, defense=None, system_message_name=None, system_message=None))
    attack = load_attack(args.attack, suite, pipeline)
    user_tasks = list(suite.user_tasks.values())[: args.limit]

    for name in args.configs.split(","):
        mandate, human = CONFIGS[name]
        out = RUNS / args.model / args.attack / name
        out.mkdir(parents=True, exist_ok=True)
        for ut in user_tasks:
            for it in [None, *suite.injection_tasks.values()]:
                f = out / f"{ut.ID}__{it.ID if it else 'none'}.json"
                if f.exists() and json.loads(f.read_text())["error"] is None:
                    continue
                injections = attack.attack(ut, it) if it else {}
                r = run_one(suite, pipeline, ut, it, injections, mandate, human)
                f.write_text(json.dumps(r, indent=1))
                print(f"{name:22} {ut.ID:14} {it.ID if it else '-':18} utility={r['utility']} "
                      f"attack={r['attack_success']} {r['error'] or ''}")
    text = report(args.model, args.attack, args.configs.split(","))
    print(text)
    if args.write:
        Path(__file__).with_name(f"results_llm_{args.model}.md").write_text(text, encoding="utf-8")


def report(model: str, attack: str, configs: list[str]) -> str:
    lines = [f"# AgentDojo banking with a real LLM: `{model}`, attack `{attack}`", "",
             "| Configuration | Utility (no attack) | Utility under attack | Attack success rate | Errors |",
             "|---|---|---|---|---|"]
    for name in configs:
        rs = [json.loads(p.read_text()) | {"file": p.name} for p in (RUNS / model / attack / name).glob("*.json")]
        ok = [r for r in rs if r["error"] is None]
        clean = [r for r in ok if r["file"].endswith("__none.json")]
        att = [r for r in ok if not r["file"].endswith("__none.json")]

        def pct(n, d):
            return f"{n}/{d} ({100 * n / d:.1f}%)" if d else "-"
        lines.append(f"| {name} | {pct(sum(r['utility'] for r in clean), len(clean))} "
                     f"| {pct(sum(r['utility'] for r in att), len(att))} "
                     f"| **{pct(sum(r['attack_success'] for r in att), len(att))}** | {len(rs) - len(ok)} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
