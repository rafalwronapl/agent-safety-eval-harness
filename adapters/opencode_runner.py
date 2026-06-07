from __future__ import annotations

from pathlib import Path

try:
    from .local_cli_runner_common import base_prompt, final_output, log_tool_event, read_safe_task, resolve_command, run_cli
except ImportError:
    from local_cli_runner_common import base_prompt, final_output, log_tool_event, read_safe_task, resolve_command, run_cli


def build_command(opencode_command: str, sandbox_path: Path, prompt: str) -> list[str]:
    return [
        opencode_command,
        "run",
        "--format",
        "json",
        "--dir",
        str(sandbox_path),
        prompt,
    ]


def main() -> int:
    _, sandbox_path, _, tool_log_path, task_text = read_safe_task()
    opencode_command = resolve_command("opencode", "HDF_OPENCODE_COMMAND")
    prompt = base_prompt(task_text)
    command = build_command(opencode_command, sandbox_path, prompt)
    log_tool_event(
        tool_log_path,
        "run_agent_cli",
        {"command": "opencode run", "cwd": str(sandbox_path)},
        True,
        "Launched opencode in non-interactive run mode.",
    )
    completed = run_cli(command, "", sandbox_path)
    print(final_output(completed))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
