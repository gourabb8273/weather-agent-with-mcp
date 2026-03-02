"""Weather agent: natural language → weather reply."""
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from agent.agent import run_agent
__all__ = ["run_agent"]
