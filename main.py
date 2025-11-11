import os

import uvicorn
from fastapi import FastAPI
from gcpdiag.mcp_server import mcp
from fastmcp import FastMCP

from google.adk.cli.fast_api import get_fast_api_app


AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Use a local/transient session service - fine with local use or with sticky sessions
ALLOWED_ORIGINS = ["http://localhost", "http://localhost:8080", "*"]
SERVE_WEB_INTERFACE = True

# Cloudrun starts by calling uvicorn main:app
mcpapp=mcp.http_app()

app = get_fast_api_app(
    agents_dir=AGENT_DIR,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
    lifespan=mcpapp.lifespan, # This is not well documented in either ADK or MCP
)


@app.get("/api/status")
def status():
    return {"status": "ok"}

@mcp.tool
def test1(query: str) -> dict:
    """Verify the MCP server works"""
    return {"result": "data"}

# Mount MCP at /mcp - the actual mcp endpoint will be /mcp/mcp/
# We may be able to adjust the path in the mcpapp.
app.mount("/mcp", mcpapp)

def main():
  # Using uvicorn
  if "PORT" in os.environ:
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT")))
  else:
    mcp.run()

if __name__ == "__main__":
  main()
