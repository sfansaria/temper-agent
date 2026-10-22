import sys
import ollama

MODEL = "qwen3:8b"

question = sys.argv[1] if len(sys.argv) > 1 else "In three sentences, what is an agentic AI?"

try:
    response = ollama.chat(model=MODEL, messages=[{"role": "user", "content": question}],)
except Exception as exc: 
    sys.exit(f"Could not reach the model ({exc}).\n"
             f"Check that Ollama is running (open the app or `ollama serve`)"
             f"and that you ran `ollama pull {MODEL}`."
    )

print(response.message.content)
