#!/usr/bin/env python3
"""CLI: run the weather agent. Usage: python run.py "What's the weather in Seattle?" """
import sys
from agent import run_agent

if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read()
    print(run_agent(text))
