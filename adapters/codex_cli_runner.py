from __future__ import annotations

from pathlib import Path

try:
    from .local_cli_runner_common import base_prompt, final_output, log_tool_event, read_safe_task, resolve_command, run_cli
except ImportError:
    from local_cli_runner_common import base_prompt, final_output, log_tool_event, read_safe_task, resolve_command, run_cli


def build_command(codex_command: str, sandbox_path: Path) -> list[str]:
    return [
        codex_command,
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--ask-for-approval",
        "never",
        "--cd",
        str(sandbox_path),
        "-",
    ]


def main() -> int:
    _, sandbox_path, _, tool_log_path, task_text = read_safe_task()
    codex_command = resolve_command("codex", "HDF_CODEX_COMMAND")
    command = build_command(codex_command, sandbox_path)
    log_tool_event(
        tool_log_path,
        "run_agent_cli",
        {"command": "codex exec", "cwd": str(sandbox_path)},
        True,
        "Launched Codex CLI in non-interactive read-only mode.",
    )
    completed = run_cli(command, base_prompt(task_text), sandbox_path)
    print(final_output(completed))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
