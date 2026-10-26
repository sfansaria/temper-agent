import json
import sys
import time
from datetime import datetime
from pathlib import Path

import ollama

from agent_tools import MODEL, TOOLS, run_tool, seed_workspace

MAX_STEPS = 10
TRACE_DIR = Path(__file__).parent / "traces"


def run_agent(task: str) -> dict:
    """Run the agent and return a full trace of what happened."""
    trace = {
        "task": task,
        "model": MODEL,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "steps": [],
        "final_answer": None,
        "status": "running",
        "error": None,
    }
    messages = [{"role": "user", "content": task}]
    t_start = time.perf_counter()

    try:
        for step_no in range(1, MAX_STEPS + 1):
            t0 = time.perf_counter()
            reply = ollama.chat(model=MODEL, messages=messages, tools=TOOLS)
            model_seconds = round(time.perf_counter() - t0, 2)

            message = reply.message
            messages.append(message)
            step = {
                "step": step_no,
                "model_seconds": model_seconds,
                "prompt_tokens": getattr(reply, "prompt_eval_count", None),
                "output_tokens": getattr(reply, "eval_count", None),
                # qwen3 can return its reasoning separately; keep it if present
                "thinking": getattr(message, "thinking", None),
                "said": message.content or "",
                "tool_calls": [],
            }
            trace["steps"].append(step)

            if not message.tool_calls:
                trace["final_answer"] = message.content
                trace["status"] = "finished"
                break

            for call in message.tool_calls:
                name, args = call.function.name, dict(call.function.arguments)
                t1 = time.perf_counter()
                result = run_tool(name, args)
                step["tool_calls"].append({
                    "name": name,
                    "arguments": args,
                    "result": result,
                    "is_error": result.startswith("Error:"),
                    "tool_seconds": round(time.perf_counter() - t1, 3),
                })
                messages.append({"role": "tool", "tool_name": name, "content": result})
        else:
            trace["status"] = "step_limit"
    except Exception as exc:  # record the failure instead of losing the run
        trace["status"] = "error"
        trace["error"] = f"{type(exc).__name__}: {exc}"

    trace["total_seconds"] = round(time.perf_counter() - t_start, 2)
    return trace


def summarize(trace: dict) -> dict:
    calls = [c for s in trace["steps"] for c in s["tool_calls"]]
    return {
        "steps": len(trace["steps"]),
        "tool_calls": len(calls),
        "tool_errors": sum(c["is_error"] for c in calls),
        "prompt_tokens": sum(s["prompt_tokens"] or 0 for s in trace["steps"]),
        "output_tokens": sum(s["output_tokens"] or 0 for s in trace["steps"]),
    }


def clip(text: str, n: int = 150) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 3] + "..."


def print_trace(trace: dict) -> None:
    print(f"\nTask:   {trace['task']}")
    print(f"Model:  {trace['model']}   Started: {trace['started_at']}\n")
    for s in trace["steps"]:
        print(f"-- step {s['step']}  ({s['model_seconds']}s model time)")
        if s.get("thinking"):
            print(f"   thinking: {clip(s['thinking'])}")
        if s["said"]:
            print(f"   said:     {clip(s['said'])}")
        for c in s["tool_calls"]:
            flag = "  !! ERROR" if c["is_error"] else ""
            print(f"   tool:     {c['name']}({c['arguments']}){flag}")
            print(f"   result:   {clip(c['result'])}")
    print()
    if trace["status"] == "finished":
        print(f"Final answer: {trace['final_answer']}")
    elif trace["status"] == "step_limit":
        print(f"STOPPED: hit the {MAX_STEPS}-step limit with no final answer.")
    else:
        print(f"FAILED: {trace['error']}")
    t = summarize(trace)
    print(f"\nSummary: status={trace['status']} | {t['steps']} steps | "
          f"{t['tool_calls']} tool calls ({t['tool_errors']} errors) | "
          f"{trace['total_seconds']}s | tokens in/out {t['prompt_tokens']}/{t['output_tokens']}")


def save_trace(trace: dict) -> Path:
    TRACE_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = TRACE_DIR / f"run_{stamp}.json"
    n = 1
    while path.exists():  # two runs in the same second
        n += 1
        path = TRACE_DIR / f"run_{stamp}_{n}.json"
    path.write_text(json.dumps(trace, indent=2, default=str), encoding="utf-8")
    return path


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--show":
        print_trace(json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")))
        sys.exit(0)

    seed_workspace()
    task = sys.argv[1] if len(sys.argv) > 1 else (
        "Find which file in the workspace mentions Ollama, summarize it in one "
        "sentence, and save the summary as a note called ollama_summary.md."
    )
    trace = run_agent(task)
    print_trace(trace)
    print(f"Trace saved: {save_trace(trace)}")
