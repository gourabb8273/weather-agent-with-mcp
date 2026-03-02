#!/usr/bin/env python3
"""
Run this script to call the weather MCP tool with a city and print the response.
Usage: python3 test_weather_tool.py [city]
Example: python3 test_weather_tool.py Seattle
"""

import json
import logging
import sys


logging.getLogger("httpx").setLevel(logging.WARNING)

from mcp_server.weather import get_weather

def main():
    city = sys.argv[1] if len(sys.argv) > 1 else "Seattle"
    print(f"Calling get_weather(city={city!r})...\n")
    response = get_weather(city)
    print(response)
    # Pretty-validate it's JSON
    try:
        data = json.loads(response)
        if "error" in data:
            sys.exit(1)
    except json.JSONDecodeError:
        sys.exit(1)
    return 0

if __name__ == "__main__":
    sys.exit(main() or 0)
