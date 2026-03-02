# Weather Agent

Agentic AI: natural language → weather (MCP tool + agent).

## Project structure

```
weather-agent/
  app.py                 # Web UI (Flask), keep at root
  run.py                 # CLI: python run.py "What's the weather in Seattle?"
  run_mcp_server.py      # Run MCP server (stdio)
  test_weather_tool.py   # Test get_weather(city)
  .env / .env.example
  requirements.txt
  web/
    index.html            # Web UI (single page)
  mcp_server/            # Weather API + MCP
    __init__.py
    weather.py           # get_weather(city): geocode → NWS → JSON
    server.py            # FastMCP, exposes get_weather tool
  agent/                 # Natural-language agent (2 files)
    __init__.py          # load_dotenv, export run_agent
    prompts.py           # All prompts (INTENT, FORMAT_WEATHER, AGENT_SYSTEM, GET_WEATHER_TOOL)
    agent.py             # Intent fallback, format (bullet/LLM), LLM client, run_agent()
```

## Quick start

```bash
pip install -r requirements.txt
# Web UI
python3 app.py
# CLI
python3 run.py "What's the weather in Seattle?"
# MCP server 
python3 run_mcp_server.py
# Test weather API only
python3 test_weather_tool.py Seattle
```

## Config (.env)

- **OpenAI:** `OPENAI_API_KEY=sk-...`
- **Ollama:** `USE_OLLAMA=1`, optional `OLLAMA_BASE_URL`, `OLLAMA_MODEL`
- **Mode:** `AGENT_MODE=agentic` (LLM tool calling) or `two_step` (we fetch weather, LLM formats)

