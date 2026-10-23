import sys
import ollama


MODEL = "qwen3:8b"
MAX_STEPS = 10 

#the real tools
def add(a:float, b: float)->float:
    return a + b

def multiply(a: float, b: float) -> float:
    return a * b

#name the model uses -> the function actually run
TOOL_FUNCTIONS = {"add": add, "multiply": multiply}

def number_tool(name: str, description: str) -> dict:
    #Build the JSON description of a two-number tool.

    return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "parameters": {
                        "type": "object",
                        "properties":{ 
                             "a": {"type": "number", "description": "The first number"},
                             "b": {"type": "number", "description": "The second number"},
                        },
                        "required": ["a", "b"],
                },
            },
    }
}



TOOLS = [
    number_tool("add", "Add two numbers and return the sum."),
    number_tool("multiply", "Multiply two numbers and return the product."),
]


def run_tool(name: str, arguments: dict) -> str:
    #Run a tool the model asked for. 
    #Always return text, even on failure so the model can see what went wrong instead of the program crashing

    func = TOOL_FUNCTIONS.get(name)
    
    if func is None:
        return f"Error: there is no tool called {name!r}."

    try:
        return str(func(**arguments))
    except Exception as exc:
        return f"Error: {name} failed with {exc}"


def run_agent(task: str)-> None:
    messages = [{"role": "user", "content": task}]

    for step in range(1, MAX_STEPS+1):
        try:
           reply = ollama.chat(model=MODEL, messages=messages, tools=TOOLS)
        except Exception as exc:
            sys.exit(f"Could not reach the model ({exc}). Is Ollama running?")



        message = reply.message
        messages.append(message) #keep the model's turn in the history
        
        #No tool requested: the model is giving its final anaswer
        if not message.tool_calls:
            print(f"\n[step {step}] Final answer: \n{message.content}")
            return

        
        #Run every tool the model asked for and send the results back
        for call in message.tool_calls:
            name = call.function.name
            args = dict(call.function.arguments)
            result = run_tool(name, args)
            print(f"[step {step}] {name}({args}) -> {result}")
            messages.append({"role": "tool", "tool_name": name, "content": result})

    print(f"\n Stopped: reached the {MAX_STEPS}-step limit without a final answer.")


if __name__=="__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "What is 17 plus 25, then multiplied by 3?"

    print("Task:", task)
    run_agent(task)
              

