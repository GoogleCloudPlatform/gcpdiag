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

RUNBOOKS: Dict[str, runbook.DiagnosticTree] = {}

# Using uvicorn
mcp: FastMCP = FastMCP(
    name="gcpdiag Runbooks",
    instructions="Exposes gcpdiag runbooks as MCP tools.",
)


def create_tool_func(rid, description, parameters):
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
      inspect.Parameter(name,
                        inspect.Parameter.KEYWORD_ONLY)  # , annotation="str")
      for name in parameters.keys()
  ]
  tool_func.__signature__ = inspect.Signature(sig_params)
  tool_func.__doc__ = description
  tool_func.__name__ = rid

  return tool_func


def add_tools(mcp):
  """
  Add all runbooks to the MCP server.
  """
  repo = runbook.DiagnosticEngine()
  command._load_runbook_rules(repo.__module__)
  for name in runbook.RunbookRegistry:
    RUNBOOKS[name] = runbook.RunbookRegistry[name]

  for runbook_id, runbook_class in RUNBOOKS.items():
    # Check if it has the method

    description = runbook_class.__doc__
    try:
      parameters = runbook_class.parameters

      tool_function = create_tool_func(runbook_id, description, parameters)
      mcp.tool(tool_function, name=runbook_id)

      print(runbook_id, tool_function)
    except:
      print("Skipping ", runbook_id)
    #agent_setup(mcp)


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


@mcp.custom_route("/runbooks", methods=["GET"])
async def list_runbooks(request):
  """List all available runbooks."""
  return JSONResponse({"runbooks": list(RUNBOOKS.keys())})


@mcp.custom_route("/runbooks/{runbook_id}", methods=["POST"])
async def run_runbook(runbook_id: str, params: Dict):
  """Execute a specific runbook and return the report."""
  if runbook_id not in RUNBOOKS:
    return {"error": "Runbook not found"}

  report = command.execute_runbook(runbook_id, params or {})
  return report


# FastMCP also wraps OpenAPI and proxes other MCP servers.
add_tools(mcp)

if __name__ == "__main__":
  print("starting app")

  if "PORT" in os.environ:
    mcp.run(transport="http", log_level="debug", port=int(os.environ["PORT"]))
  else:
    mcp.run()
