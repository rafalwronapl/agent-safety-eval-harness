from __future__ import annotations

import json
import os
from pathlib import Path


def log_tool_call(tool: str, args: dict[str, object], allowed: bool, note: str) -> None:
    tool_log_path = Path(os.environ["HDF_TOOL_LOG_PATH"])
    tool_log_path.parent.mkdir(parents=True, exist_ok=True)
    with tool_log_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "tool": tool,
                    "args": args,
                    "allowed": allowed,
                    "note": note,
                },
                sort_keys=True,
            )
            + "\n"
        )


def run_agent_placeholder(task_text: str, sandbox_path: Path) -> str:
    """Replace this function with a real agent call.

    Keep credentials in environment variables. Do not write prompts, raw model
    responses, or tool outputs containing real secrets into this repository.
    """
    return (
        "Example CLI runner read the synthetic safe task and returned a placeholder answer. "
        f"Sandbox: {sandbox_path.name}. Task length: {len(task_text)}."
    )


def main() -> int:
    scenario_id = os.environ["HDF_SCENARIO_ID"]
    sandbox_path = Path(os.environ["HDF_SANDBOX_PATH"])
    safe_task_path = Path(os.environ["HDF_SAFE_TASK_PATH"])
    task_text = safe_task_path.read_text(encoding="utf-8")
    log_tool_call(
        "read_file",
        {"path": safe_task_path.name},
        True,
        f"Read safe task for {scenario_id}.",
    )
    print(run_agent_placeholder(task_text, sandbox_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
