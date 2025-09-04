"""Mocked tests"""

import unittest
from unittest.mock import Mock, patch
from starlette.responses import JSONResponse

import pytest
from fastmcp import FastMCP, Client


class TestMCPServer(unittest.TestCase):

  def setUp(self):
    self.mcp = FastMCP(name="gcpdiag Runbooks",
                       instructions="Exposes gcpdiag runbooks as MCP tools.")
    # Clear RUNBOOKS for isolated testing
    RUNBOOKS.clear()

  def test_create_mcp_server(self):
    # Mock a runbook class
    mock_runbook_class = Mock()
    mock_runbook_class.__doc__ = "Test runbook description."
    mock_runbook_class.parameters = {"param1": "type1", "param2": "type2"}
    RUNBOOKS["test_runbook"] = mock_runbook_class

    with patch(
        'gcpdiag.runbook.command.execute_runbook') as mock_execute_runbook:
      # create_mcp_server(self.mcp)
      add_tools(self.mcp)

      # Check if the tool was registered
      self.assertIn("test_runbook", self.mcp._tool_manager._tools)

  async def test_hello_tool(self):
    response = await hello("World")
    self.assertEqual(response, "Hello, World!")

  async def test_health_check_route(self):
    request = Mock()
    response = await health_check(request)
    self.assertIsInstance(response, JSONResponse)
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.body.decode(), '{"status":"ok"}')
