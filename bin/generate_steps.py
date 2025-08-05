#!/usr/bin/env python3
"""Generate a markdown table with all gcpdiag runbook steps."""

import importlib
import inspect
import os
import pathlib
import textwrap
from typing import List, Sequence

from absl import app, flags

from gcpdiag import runbook
from gcpdiag.runbook import constants

_URL_BASE_PREFIX = flags.DEFINE_string(
    "url_base_prefix",
    "https://github.com/GoogleCloudPlatform/gcpdiag/tree/main",
    "Base URL prefix for the files in the table.",
)


def fetch_and_list_steps(output_file_path: str, base_url_path: str):
  """Fetches all Step subclasses and generates a Markdown table."""
  table_rows = []
  modules_with_files: List[tuple[str, str]] = []
  for root, _, files in os.walk("gcpdiag/runbook"):
    for file in files:
      if file.endswith(".py") and not file.startswith("__"):
        module_path = os.path.join(root, file)
        # Prepare path for URL
        url_path = module_path.replace("\\", "/")
        file_url = f"{base_url_path}/{url_path}"
        module_path = module_path.replace("/", ".")[:-3]
        modules_with_files.append(
            (module_path, file_url))  # gcpdiag.runbook.nameofrunbook.nameoffile

  rows_data = []
  for module_path, file_url in modules_with_files:
    try:
      module = importlib.import_module(module_path)
      file_name = module_path.split(".")[-1]
    except ImportError:
      continue
    for _, obj in inspect.getmembers(module,
                                     inspect.isclass):  # returns Only class
      if issubclass(obj, runbook.Step) and obj is not runbook.Step:
        try:
          step_instance = obj()  # obj of the Class
          if hasattr(step_instance, "type") and isinstance(
              step_instance.type, constants.StepType):
            step_type = step_instance.type.value
          else:
            step_type = "ERROR: Invalid Step Type"
        except TypeError:
          step_type = "ERROR: Could not instantiate Step"
        step_id = f"google.cloud.{obj.id}"

        rows_data.append({
            "file_name": file_name,
            "file_url": file_url,
            "step_name": obj.__name__,
            "step_type": step_type,
            "step_id": step_id
        })

  # Sort the rows data
  rows_data.sort(key=lambda x: (x["file_name"], x["step_name"]))

  for row in rows_data:
    row_values = {
        "file_name": row["file_name"],
        "file_url": row["file_url"],
        "step_name": row["step_name"],
        "step_type": row["step_type"],
        "step_id": row["step_id"],
    }
    table_rows.append(
        "|[{file_name}]({file_url}) | **{step_name}** | {step_type} |"
        " `{step_id}` |".format(**row_values))

  markdown_table = textwrap.dedent("""
        |Runbook name| **Runbook Step** | stepType | `StepId` |
        |:------------|:----------- |:----------- |:----------- |
    """)
  markdown_table += "\n".join(table_rows)

  # Create the parent directory if it doesn't exist
  pathlib.Path(output_file_path).parent.mkdir(parents=True, exist_ok=True)

  with open(output_file_path, "w", encoding="utf-8") as f:
    f.write(markdown_table)


def main(argv: Sequence[str]) -> None:
  if len(argv) > 1:
    raise app.UsageError("Too many command-line arguments.")
  output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "steps_table.md")
  base_url = _URL_BASE_PREFIX.value
  fetch_and_list_steps(output_file_path=output_file, base_url_path=base_url)


if __name__ == "__main__":
  app.run(main)
