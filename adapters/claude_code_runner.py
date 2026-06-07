from __future__ import annotations

from pathlib import Path

try:
    from .local_cli_runner_common import base_prompt, final_output, log_tool_event, read_safe_task, resolve_command, run_cli
except ImportError:
    from local_cli_runner_common import base_prompt, final_output, log_tool_event, read_safe_task, resolve_command, run_cli


def build_command(claude_command: str, sandbox_path: Path) -> list[str]:
    return [
        claude_command,
        "--print",
        "--output-format",
        "text",
        "--permission-mode",
        "dontAsk",
        "--allowedTools",
        "Read,Grep,Glob",
        "--add-dir",
        str(sandbox_path),
    ]


def main() -> int:
    _, sandbox_path, _, tool_log_path, task_text = read_safe_task()
    claude_command = resolve_command("claude", "HDF_CLAUDE_COMMAND")
    command = build_command(claude_command, sandbox_path)
    log_tool_event(
        tool_log_path,
        "run_agent_cli",
        {"command": "claude --print", "cwd": str(sandbox_path)},
        True,
        "Launched Claude Code in non-interactive print mode.",
    )
    completed = run_cli(command, base_prompt(task_text), sandbox_path)
    print(final_output(completed))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
