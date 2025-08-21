"""
Tests for the MCP server and the tools.
This is a local e2e test, using the MCP client.
"""
import mcp_server as srv
import pytest
import fastmcp


@pytest.fixture
def mcp_server():
  mcp = srv.mcp
  srv.create_mcp_server(mcp)

  @mcp.tool
  def greet(name: str) -> str:
    return f"Hello, {name}!"

  return mcp


# Need to install pytest-asyncio for this to work


@pytest.mark.asyncio
async def test_tool_functionality(mcp_server: fastmcp.FastMCP):
  # Pass the server directly to the Client constructor
  async with fastmcp.Client(mcp_server) as client:
    result = await client.call_tool("greet", {"name": "World"})
    assert result.data == "Hello, World!"


@pytest.mark.asyncio
async def test_tool_hello(mcp_server):
  # Pass the server directly to the Client constructor
  async with fastmcp.Client(mcp_server) as client:
    result = await client.call_tool("hello", {"name": "World"})
    assert result.data == "Hello, World!"


@pytest.mark.asyncio
async def test_tool_gke1(mcp_server):
  # Pass the server directly to the Client constructor
  async with fastmcp.Client(mcp_server) as client:
    result = await client.call_tool(
        "gke/image-pull", {
            "project_id": "costin-asm1",
            "gke_cluster_name": "big1",
            "name": "big1",
            "location": "us-central1",
            "start_time": "0",
            "end_time": "0"
        })
    print(result.data)
    #assert result.data == "Hello, World!"
