# MCP server exposing gcpdiag runbooks as tools.
# This is a uvicorn app - using fast_api_app.get(), etc.
#
# Run as:
# uv run --with fastmcp fastmcp run gcpdiag/mcp_server.py
# uv run --with fastmcp fastmcp run --server-spec gcpdiag/mcp_server.py
# fastmcp dev gcpdiag/mcp_server.py --ui-port 9001 --server-port 9002

from gcpdiag.runbook import command
import inspect
import os

from gcpdiag import runbook
from fastmcp import FastMCP, Context
from typing import Dict
from google.adk.agents import LlmAgent
import json


def create_mcp_func(rid, description, parameters):
  """
  Return a function with the signature and doc based on the GCPDiag runbook,
  which invokes the runbook. A more direct approach would be to find the
  actual functions and expose them directly - for new runbooks it may be better
  to just expose directly as MCP.
  """

  def tool_func(**kwargs):
    print(f"Calling {rid} with {kwargs}")
    return command.execute_runbook(rid, kwargs)

  # Create a new signature for the tool_func
  sig_params = [
      inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, annotation=str)
      for name in parameters.keys()
  ]
  annotations = {}
  for name in parameters.keys():
    annotations[name] = str
  tool_func.__signature__ = inspect.Signature(sig_params)
  tool_func.__doc__ = description
  tool_func.__name__ = rid.replace("/", "_")
  tool_func.__annotations__ = annotations

  return tool_func


def add_tools(mcp):
  """
  Add all runbooks to the MCP server.
  """
  repo = runbook.DiagnosticEngine()
  command._load_runbook_rules(repo.__module__)
  RUNBOOKS: Dict[str, runbook.DiagnosticTree] = {}
  for name in runbook.RunbookRegistry:
    RUNBOOKS[name] = runbook.RunbookRegistry[name]

  for runbook_id, runbook_class in RUNBOOKS.items():
    # Check if it has the method

    description = runbook_class.__doc__
    try:
      parameters = runbook_class.parameters

      tool_function = create_mcp_func(runbook_id, description, parameters)
      mcp.tool(tool_function, name=runbook_id.replace("/", "_"))
    except Exception as e:
      print("Skipping ", runbook_id, e)


# This is a holder for the '@mcp' functions.
mcp: FastMCP = FastMCP(
    name="gcpdiag Runbooks",
    instructions="Exposes gcpdiag runbooks as MCP tools.",
)

@mcp.tool
async def hello(name: str, ctx: Context) -> str:
  """
  Hello is a test function to validate the server functionality.
  """
  await ctx.info("Example log")

  return f"Hello, {name} {ctx.request_id} {ctx.client_id} !"


@mcp.tool
async def elicit(ctx: Context) -> str:
  result = await ctx.elicit("Enter some text", response_type=str)

  if result.action == "accept":
    return f"Hello, {result.data}!"
  return "No input"


@mcp.resource("data://test")
def get_test() -> dict:
  """Provides a test resource"""
  return {"example": "resource"}


@mcp.resource("data://{param}/test")
def get_test_templ(param: str) -> dict:
  """Provides a test resource template """
  return {"example": f"resource {param}"}


@mcp.prompt
def prompt_run(user: str) -> str:
  """Creates a prompt asking for running a runbook."""
  return f"""You are an expert in GCP, insing GCPDiag too to diagnose problems.
     The user input is:
     {user}

     Use all available tools to identify the problem.
     """


@mcp.custom_route("/healthz", methods=["GET"])
async def health_check(request):

  tools = await mcp._tool_manager.list_tools(
  )  # type: ignore[reportPrivateUsage]
  print(tools)
  return JSONResponse({"status": "ok"})


@mcp.custom_route("/runbooks/{runbook_id}", methods=["POST"])
async def run_runbook(runbook_id: str, params: Dict):
  """Execute a specific runbook and return the report."""

  try:
    report = command.execute_runbook(runbook_id, params or {})
    return report
  except Exception as e:
    print(runbook_id, e)
    return ""

add_tools(mcp)


def main():
  # Using uvicorn
  if "PORT" in os.environ:
    mcp.run(transport="http", log_level="debug", port=int(os.environ["PORT"]))
  else:
    print("Starting stdio gcpidag MCP")
    mcp.run()

if __name__ == "__main__":
  main()
