import json
from collections import Counter


PY_TYPES = {
    "string": (str, ),
    "number": (int, float),
    "integer": (int,),
    "boolean": (bool,),
}



def check_args(schema: dict, arguments) -> str:
    #return a description of the problem, or '' if the arguments are fine.

    if not isinstance(arguments, dict):
        return "arguments must be an object of name/value pairs"

    props = schema.get("properties", {})

    for name in schema.get("required", []):
        if name not in arguments:
            return f"missing required argument {name!r}"
    
    for name, value in arguments.items():
        if name not in props:
            return f"unexpected arguments {name!r} (allowed: {', '.join(props) or 'none'})"

        want = props[name].get("type")
        allowed = PY_TYPES.get(want)

        if allowed:
            if isinstance(value, bool) and want != "boolean":
                return f"argument {name!r} should be {want}, got a boolean"
            
            if not isinstance(value, allowed):
                return f"argument {name!r} should be {want}, got {type(value).__name__}"
    return ""


def make_guarded_run_tool(raw_run_tool, tools, max_repeats: int = 3, max_chars: int = 4000):
    #Wrap a run_tool(name, arguments) function with the guards above.
    #Create a NEW guarded function for every run: it remembers repeated calls.

    schemas = {t["function"]["name"]: t["function"]["parameters"] for t in tools}
    seen = Counter()


    def guarded(name: str, arguments: dict)-> str:

        if name not in schemas:
            return (f"Error: there is no tool called {name!r}."
                    f"Available tools: {', '.join(schemas)}.")

        problem = check_args(schemas[name], arguments)
        if problem:
            return (f"Errror: bad arguments for {name}: {problem}."
                    f"Expected: {json.dumps(schemas[name]['properties'])}")
        
        key = (name, json.dumps(arguments, sort_keys=True, default=str))
        seen[key] += 1

        if seen[key] > max_repeats:
            return (f"Error: you have already called {name} with these exact arguments {max_repeats} times."
                    f"Do not call it again."
                    f"Try a different approach, or give your final answer and explain what is blocking you.")
        
        result = raw_run_tool(name, arguments)

        if not str(result).strip():
            return (f"(The {name} tool returned an empty result. Do not guess what it should contain."
                    f"If you cannot continue, tell the user it was empty.)")

        if len(result) > max_chars:
            return result[:max_chars] + f"\n...[truncated, {len(result)} characters in total]"
        return result

    return guarded
