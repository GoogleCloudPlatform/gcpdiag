# Run using:
#   `adk web --reload_agents`
#
# Make sure GEMINI_API_KEY is set - can be saved to agent/.env

import inspect

from gcpdiag import runbook
from gcpdiag.runbook import command

from google.adk.agents import LlmAgent
from typing import Dict
import dotenv
import json

dotenv.load_dotenv()

model = "gemini-2.5-flash"

RUNBOOKS: Dict[str, runbook.DiagnosticTree] = {}


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
      inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, annotation=str)
      for name in parameters.keys()
  ]
  tool_func.__signature__ = inspect.Signature(sig_params)
  tool_func.__doc__ = description
  tool_func.__name__ = rid.replace("/", "_")

  return tool_func


def get_runbooks():
  """
  Get all runbooks.
  """
  repo = runbook.DiagnosticEngine()
  command._load_runbook_rules(repo.__module__)
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

  #return {"runbooks": list(RUNBOOKS.keys())}


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


def agent_setup():
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


def agent_setup_search():
  """Agent using a function to search for the best runbook, and separate function to run the runbooks with id and params"""
  tools = []
  tools.append(list_runbooks)
  tools.append(run_runbook)
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


# This is the root_agent
root_agent = agent_setup()
