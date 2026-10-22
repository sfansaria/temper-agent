# temper-agent

A small agent built from scratch with a local model (Ollama + qwen3:8b), one step per day.

## Setup
```
ollama pull qwen3:8b
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Progress

### Day 1: 
- Talk to a model
`hello.py` sends one message to the local model and prints the reply. It confirms that Ollama and the model are set up correctly.
- Give the model a tool
`one_tool.py` describes a simple `add(a, b)` function to the model as a JSON schema. The model replies with a request to call `add` and the arguments it chose (for example `a=2890, b=1009`). 
