import sys
import ollama


MODEL = "qwen3:8b"

def add(a: float, b: float) -> float:
    return a+b

TOOLS = [
         {
            "type": "function",
            "function": {
                "name": "add",
                "description": "Add two numbers and return the sum.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "The first number"},
                        "b": {"type": "number", "description": "The second number"},
                        },
                        "required": ["a", "b"],
                    },
                },
         }
]


task = sys.argv[1] if len(sys.argv) > 1 else "What is 17 plus 25?"

try: 
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content":task}],
        tools=TOOLS,
        )
except Exception as exc:
    sys.exit(f"Could not reach the model ({exec}). Is Ollama running?")


message = response.message
print("Task:", task)

if not message.tool_calls:
    print("\nThe model answered directly (no tool call):")
    print(message.content)
else:
    for call in message.tool_calls:
        print("\nThe model asked to call a tool:")
        print("name:", call.function.name)
        print("arguments:", dict(call.function.arguments))









