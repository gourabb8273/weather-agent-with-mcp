"""MCP server: exposes get_weather as a tool over stdio."""
from mcp.server.fastmcp import FastMCP
from mcp_server import weather as weather_mod

mcp = FastMCP("Weather Information Tool", json_response=True)

@mcp.tool()
def get_weather(city: str) -> str:
    """Get current weather and short-term forecast for a city (e.g. Seattle or Seattle, WA)."""
    return weather_mod.get_weather(city)

def run():
    import sys
    print("Weather MCP server starting...", file=sys.stderr)
    print("  Tool: get_weather(city)", file=sys.stderr)
    sys.stderr.flush()
    mcp.run(transport="stdio")

if __name__ == "__main__":
    run()
