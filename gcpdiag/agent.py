from gcpdiag.runbook import command
import inspect
import os

from gcpdiag import runbook
from fastmcp import FastMCP, Context
from typing import Dict
from google.adk.agents import LlmAgent
import json
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool import StdioConnectionParams, StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
import subprocess

from mcp.client.stdio import StdioServerParameters

RUNBOOKS: Dict[str, runbook.DiagnosticTree] = {}

# This creates a tool compatible with agent tool functions - directly usable in agent without
# the MCP layer.
def create_tool_func(rid, description, parameters):
  def tool_func(**kwargs):
    print(f"Calling {rid} with {kwargs}")
    return command.execute_runbook(rid, kwargs)

  # Create a new signature for the tool_func
  sig_params = [
      inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, annotation=str)
      for name in parameters.keys()
  ]
  tool_func.__signature__ = inspect.Signature(sig_params)
  tool_func.__doc__ = description
  tool_func.__name__ = rid.replace("/", "_")

  return tool_func

def truncate_output(output: str, max_chars: int = 20000) -> str:
    """Truncates a string to a maximum number of characters."""
    if len(output) > max_chars:
        return output[:max_chars] + f"\n------- OUTPUT TRUNCATED AT {max_chars} CHARACTERS -------"
    return output

def get_runbooks():
  """
  Get all runbooks.
  """
  repo = runbook.DiagnosticEngine()
  command._load_runbook_rules(repo.__module__)
  RUNBOOKS: Dict[str, runbook.DiagnosticTree] = {}
  for name in runbook.RunbookRegistry:
    RUNBOOKS[name] = runbook.RunbookRegistry[name]

  tools = []
  for runbook_id, runbook_class in RUNBOOKS.items():
    # Check if it has the method

    description = runbook_class.__doc__

    parameters = runbook_class.parameters

    tool_function = create_tool_func(runbook_id, description, parameters)

    tools.append(tool_function)
  return tools


# gcpdiag = McpToolset(connection_params=StdioConnectionParams(
#             server_params = StdioServerParameters(command='uvx', args=["--from", "../gcpdiag", 'gcpdiagmcp'])))

gcloudmcp = McpToolset(connection_params=StdioConnectionParams(
            server_params = StdioServerParameters(command='npx', args=["-y", "@google-cloud/gcloud-mcp"])))
observabilitymcp = McpToolset(connection_params=StdioConnectionParams(
            server_params = StdioServerParameters(command='npx', args=["-y", "@google-cloud/observability-mcp"])))

#gkemcp = McpToolset(connection_params=StdioConnectionParams(
#            server_params = StdioServerParameters(command='gke-mcp')))
def kubectl(command: str) -> str:
    """
    Executes a kubectl CLI command and returns the output.
    Use this for executing various read-only kubernetes queries such as kubectl describe, list, logs, cluster-info, etc

    Guidance:
    - ALWAYS specify the full kubectl command within the kubctl tool, as in "kubectl(command=\"kubectl get pods ...\")
    - ALWAYS specify a namespace in your commands using `-n`
    - ALWAYS specify a cluster context in your commands using `--context`
    - DO NOT update, create, or edit resources using kubectl. ONLY use kubectl for read-only commands.
    - ALWAYS detect that the cluster context is first set correctl by detecting that it is the default context
    - Start with simple kubectl commands (like get pods, get services) to identify relevant components and then expand from there with more detailed ones once you have found some valid and relevant information.

    parameter command: The full kubectl command to execute (e.g., 'kubectl get pods').
    returns: The stdout from the command, or stderr if an error occurs.
    example: kubectl(command="kubectl get pods -n my-namespace --context cluster-context")
    example: kubectl(command="kubectl get services -n my-namespace --context cluster-context")
    example: kubectl(command="kubectl describe pod my-pod -n my-namespace --context cluster-context")
    """
    if not command.strip().startswith("kubectl"):
        return "Error: This tool only accepts commands that start with 'kubectl'. For gcloud commands, use the 'gcloud' tool."
    try:
        full_command = command.split()
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )
        return truncate_output(result.stdout)
    except FileNotFoundError:
        return "Error: 'kubectl' command not found. Please ensure kubectl is installed and in your PATH."
    except subprocess.CalledProcessError as e:
        return truncate_output(f"Error executing command: {' '.join(full_command)}\nStderr: {e.stderr}")
    except Exception as e:
        return truncate_output(f"An unexpected error occurred: {str(e)}")

def agent_setup(model: str):
  """Standard agent setup - each runbook is a separate tool"""
  tools = get_runbooks()
  llm_agent = LlmAgent(
      model=model,
      name="llm_agent",
      description="test llm planning agent",
      instruction="""You are an agent troubleshooting GCP problems.When asked:
                     1. Select the top 5 most relevant tools.
                     2. Use the information provided by user or other tools to determine the required parameters, and call the runbooks in parallel as soon as the parameters are known.
                     3. Return each of the runbook output.
                     """,
      tools=tools,
  )
  return llm_agent


def agent_setup_search(model: str):
  """Agent using a function to search for the best runbook, and separate function to run the runbooks with id and params"""
  tools = []
  tools.append(list_runbooks)
  tools.append(run_runbook)
  tools.append(gcloudmcp)
  tools.append(observabilitymcp)
  tools.append(kubectl)
  #tools.append(gkemcp)
  llm_agent = LlmAgent(
      model=model,
      name="llm_agent",
      description="test llm planning agent",
      instruction="""You are an agent troubleshooting GCP problems.When asked:
                     1. Use the search tool to find the top 5 most relevant runbook IDs. The search tool returns structured data with the id and schema of the runbook.
                     2. Use the information provided by user or other tools to determine the required parameters, and call the runbooks in parallel as soon as the parameters are known.
                     3. Return each of the runbook output.
                     """,
      tools=tools,
  )
  return llm_agent

async def list_runbooks():
  """List all available runbooks."""

  repo = runbook.DiagnosticEngine()
  command._load_runbook_rules(repo.__module__)
  for name in runbook.RunbookRegistry:
    RUNBOOKS[name] = runbook.RunbookRegistry[name]

  tools = []
  for runbook_id, runbook_class in RUNBOOKS.items():
    # Check if it has the method
    tools.append({
        "name": runbook_id,
        "description": runbook_class.__doc__,
        #"parameters": runbook_class.parameters
    })
  return json.dumps(tools)


async def run_runbook(runbook_id: str, params: dict):
  """Execute a specific runbook and return the report."""
  if runbook_id not in RUNBOOKS:
    return {"error": "Runbook not found"}

  try:
    report = command.execute_runbook(runbook_id, params or {})
    return report
  except Exception as e:
    print(runbook_id, e)
    return ""

for name in runbook.RunbookRegistry:
    RUNBOOKS[name.replace("/", "_")] = runbook.RunbookRegistry[name]

root_agent = agent_setup_search(os.environ.get("MODEL", "gemini-2.5-flash"))
