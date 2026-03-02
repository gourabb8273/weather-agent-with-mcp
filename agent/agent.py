"""Weather agent: intent, format, LLM, run_agent. Prompts in prompts.py."""
import json
import os
import re
import sys

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from agent.prompts import AGENT_SYSTEM, FORMAT_WEATHER, GET_WEATHER_TOOL, INTENT

WEATHER_WORDS = ("weather", "forecast", "temp", "rain", "snow", "sunny", "hot", "cold", "warm", "what's the weather")
CITY_PATTERNS = [
    r"(?:weather|forecast|temp)\s+(?:in|for|at)\s+([^.?!]+?)(?:\?|$)",
    r"(?:in|for|at)\s+([^.?!]+?)(?:\?|$)",
]

def _intent_fallback(message: str) -> tuple[str, str | None]:
    msg = message.strip().lower()
    if not any(w in msg for w in WEATHER_WORDS):
        return ("other", None)
    for pattern in CITY_PATTERNS:
        m = re.search(pattern, message.strip(), re.IGNORECASE)
        if m:
            city = m.group(1).strip()
            if len(city) > 1 and city.lower() not in ("it", "me", "us", "there", "here"):
                return ("weather", city)
    parts = message.strip().split()
    return ("weather", parts[-1].rstrip("?.") if parts else "Seattle")

def _temp_str(t_f, t_c) -> str:
    if t_f is None:
        return ""
    c = t_c if t_c is not None else round((t_f - 32) * 5 / 9)
    return f"{t_f}°F ({c}°C)"

def _simple_format(data: dict) -> str:
    loc = data.get("location", "Unknown")
    cur = data.get("current") or {}
    periods = data.get("periods", []) or []
    t = _temp_str(cur.get("temperature"), cur.get("temperatureCelsius"))
    short = (cur.get("shortForecast") or "").strip()
    main = f"{loc}: {t}, {short}".strip(", ") if (loc or t or short) else ""
    wind = (cur.get("windSpeed") or "").strip()
    next_bits = [f"{p.get('name') or ''} {_temp_str(p.get('temperature'), p.get('temperatureCelsius'))}".strip() for p in periods[:3]]
    next_bits = [x for x in next_bits if x]
    parts = [p for p in [main, f"Wind {wind}" if wind else "", "Next: " + ", ".join(next_bits) if next_bits else ""] if p]
    return ". ".join(parts)

def _format_response(tool_output: str, llm_formatter=None) -> str:
    try:
        data = json.loads(tool_output)
    except json.JSONDecodeError:
        return f"I got data but couldn't read it.\n{tool_output[:200]}"
    if "error" in data:
        return f"Sorry, I couldn't get the weather: {data['error']}"
    if llm_formatter:
        text = llm_formatter(tool_output)
        if text and not re.search(r"\[[\w\s]+\]", text):
            return text
    return _simple_format(data)

def _get_client():
    if not HAS_OPENAI:
        return None, None, None
    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if key:
        return OpenAI(api_key=key), "gpt-4o-mini", "OpenAI"
    base = (os.environ.get("OLLAMA_BASE_URL") or os.environ.get("OLLAMA_HOST") or "").strip()
    if not base and (os.environ.get("USE_OLLAMA", "").strip().lower() in ("1", "true", "yes")):
        base = "http://localhost:11434/v1"
    if not base:
        return None, None, None
    base = base.rstrip("/") + "/v1" if not base.endswith("/v1") else base
    model = (os.environ.get("OLLAMA_MODEL") or "llama3.2").strip()
    return OpenAI(base_url=base, api_key="ollama"), model, "Ollama"

def _run_tool_calling(msg: str, client: OpenAI, model: str, get_weather_fn) -> str | None:
    try:
        messages = [{"role": "system", "content": AGENT_SYSTEM}, {"role": "user", "content": msg.strip()}]
        while True:
            resp = client.chat.completions.create(model=model, messages=messages, tools=[GET_WEATHER_TOOL], tool_choice="auto", max_tokens=500)
            m = resp.choices[0].message
            if m.tool_calls:
                messages.append({"role": "assistant", "content": m.content or None, "tool_calls": [{"id": t.id, "type": "function", "function": {"name": t.function.name, "arguments": t.function.arguments}} for t in m.tool_calls]})
                for tc in m.tool_calls:
                    if tc.function.name == "get_weather":
                        city = (json.loads(tc.function.arguments or "{}").get("city") or "").strip()
                        result = get_weather_fn(city) if city else json.dumps({"error": "City name is required."})
                    else:
                        result = json.dumps({"error": "Unknown tool."})
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
                continue
            text = (m.content or "").strip()
            return text or None
    except Exception as e:
        print(f"[Weather agent] LLM tool-call failed: {e}", file=sys.stderr)
        return None

def _extract_intent(msg: str, client: OpenAI, model: str) -> tuple[str, str | None]:
    try:
        resp = client.chat.completions.create(model=model, messages=[{"role": "system", "content": INTENT}, {"role": "user", "content": msg.strip()}], max_tokens=150)
        text = (resp.choices[0].message.content or "").strip()
        m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if m:
            d = json.loads(m.group())
            city = d.get("city")
            return (d.get("intent", "other"), city.strip() if isinstance(city, str) and city.strip() else None)
    except Exception:
        pass
    return _intent_fallback(msg)

def _format_with_llm(weather_json: str, client: OpenAI, model: str) -> str | None:
    try:
        resp = client.chat.completions.create(model=model, messages=[{"role": "system", "content": FORMAT_WEATHER}, {"role": "user", "content": "Weather data:\n" + weather_json}], max_tokens=350)
        return (resp.choices[0].message.content or "").strip() or None
    except Exception:
        return None

def run_agent(user_message: str) -> str:
    from mcp_server.weather import get_weather

    msg = (user_message or "").strip()
    if not msg:
        return 'Please ask something. For example: "What\'s the weather in Seattle?"'

    client, model, provider = _get_client()
    mode = (os.environ.get("AGENT_MODE", "two_step") or "two_step").strip().lower()

    if client and model and mode == "agentic":
        reply = _run_tool_calling(msg, client, model, get_weather)
        if reply:
            print(f"[Weather agent] {provider}, {model}, strategy=1 (agentic)", file=sys.stderr)
            return reply

    if client and model:
        print(f"[Weather agent] {provider}, {model}, strategy=2 (two-step)", file=sys.stderr)
        intent, city = _extract_intent(msg, client, model)
        if intent != "weather":
            return 'I can only help with weather. Try: "What\'s the weather in [city]?"'
        if not city:
            return 'I didn\'t catch which city. Try: "What\'s the weather in Seattle?"'
        out = get_weather(city)
        try:
            if "error" in json.loads(out):
                return f"Sorry, I couldn't get the weather: {json.loads(out)['error']}"
        except json.JSONDecodeError:
            pass
        formatted = _format_response(out, lambda s: _format_with_llm(s, client, model))
        if formatted:
            return formatted

    print(f"[Weather agent] {provider or 'none'}, {model or 'n/a'}, strategy=3 (fallback)", file=sys.stderr)
    return "Weather is currently unavailable. Set OPENAI_API_KEY or USE_OLLAMA=1 in .env to get weather."
