import sys
from pathlib import Path

import ollama

MODEL = "qwen3:8b"
MAX_STEPS = 10
WORKSPACE = Path(__file__).parent / "workspace"
MAX_READ_CHARS = 4000  # keep huge files from flooding the model's context


# --- sample data so there is something to search -------------------------
def seed_workspace() -> None:
    WORKSPACE.mkdir(exist_ok=True)
    samples = {
        "ollama_notes.txt": (
            "Ollama runs language models locally. Install it, then run "
            "`ollama pull qwen3:8b`. The model needs about 5 GB of disk space "
            "and runs well on a 24 GB Mac."
        ),
        "agent_ideas.txt": (
            "Ideas: a tool contract fuzzer, a voice agent for farmers, "
            "and an agent that tests other agents."
        ),
        "shopping.txt": "Milk, eggs, bread, coffee, bananas.",
    }

    for name, text in samples.items():
        path = WORKSPACE / name
        if not path.exists():
            path.write_text(text, encoding="utf-8")


# --- safety: keep every path inside the workspace ------------------------
def safe_path(relative: str) -> Path:
    
    path = (WORKSPACE / relative).resolve()

    if WORKSPACE.resolve() != path and WORKSPACE.resolve() not in path.parents:
        raise ValueError("path is outside the workspace")
    return path


# --- the tools -----------------------------------------------------------
def list_files(folder: str = ".") -> str:
    path = safe_path(folder)
    if not path.is_dir():
        return f"Error: {folder!r} is not a folder."
    names = sorted(p.name + ("/" if p.is_dir() else "") for p in path.iterdir())
    return "\n".join(names) if names else "(empty folder)"


def read_file(path: str) -> str:
    target = safe_path(path)
    if not target.is_file():
        return f"Error: {path!r} is not a file. Use list_files to see what exists."
    text = target.read_text(encoding="utf-8", errors="replace")
    if len(text) > MAX_READ_CHARS:
        return text[:MAX_READ_CHARS] + f"\n...[truncated, file is {len(text)} characters]"
    return text


def write_note(filename: str, content: str) -> str:
    if not filename.endswith((".txt", ".md")):
        return "Error: filename must end in .txt or .md."
    target = safe_path("notes/" + Path(filename).name)  # .name drops any folders
    target.parent.mkdir(exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Saved {len(content)} characters to notes/{target.name}"


def search_web(query: str) -> str:
    # FAKE on purpose: canned results, no network. Swap in a real API later.
    return (
        f"[fake search results for {query!r}]\n"
        "1. Ollama - run LLMs locally (ollama.com)\n"
        "2. Building agents: a tool-calling loop (example.com/agents)\n"
        "3. Qwen3 model card (example.com/qwen3)"
    )


TOOL_FUNCTIONS = {
    "list_files": list_files,
    "read_file": read_file,
    "write_note": write_note,
    "search_web": search_web,
}


def tool(name: str, description: str, props: dict, required: list) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


TOOLS = [
    tool("list_files", "List the files and folders inside a folder of the workspace.",
         {"folder": {"type": "string", "description": "Folder path, '.' for the top level"}}, []),
    tool("read_file", "Read the text of one file in the workspace.",
         {"path": {"type": "string", "description": "File path, e.g. 'ollama_notes.txt'"}}, ["path"]),
    tool("write_note", "Save a short note as a .txt or .md file in the notes folder.",
         {"filename": {"type": "string", "description": "e.g. 'summary.md'"},
          "content": {"type": "string", "description": "The text to save"}},
         ["filename", "content"]),
    tool("search_web", "Search the web and return a few result titles.",
         {"query": {"type": "string", "description": "The search query"}}, ["query"]),
]


def run_tool(name: str, arguments: dict) -> str:
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return f"Error: there is no tool called {name!r}."
    try:
        return str(func(**arguments))
    except Exception as exc:
        return f"Error: {name} failed with {exc}"


def run_agent(task: str) -> None:
    messages = [{"role": "user", "content": task}]
    for step in range(1, MAX_STEPS + 1):
        try:
            reply = ollama.chat(model=MODEL, messages=messages, tools=TOOLS)
        except Exception as exc:
            sys.exit(f"Could not reach the model ({exc}). Is Ollama running?")
        message = reply.message
        messages.append(message)
        if not message.tool_calls:
            print(f"\n[step {step}] Final answer:\n{message.content}")
            return
        for call in message.tool_calls:
            name, args = call.function.name, dict(call.function.arguments)
            result = run_tool(name, args)
            shown = result if len(result) < 120 else result[:117] + "..."
            print(f"[step {step}] {name}({args}) -> {shown!r}")
            messages.append({"role": "tool", "tool_name": name, "content": result})
    print(f"\nStopped: reached the {MAX_STEPS}-step limit without a final answer.")


if __name__ == "__main__":
    seed_workspace()
    task = sys.argv[1] if len(sys.argv) > 1 else (
        "Find which file in the workspace mentions Ollama, summarize it in one "
        "sentence, and save the summary as a note called ollama_summary.md."
    )
    print("Task:", task)
    run_agent(task)
