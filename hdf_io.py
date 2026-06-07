from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def is_relative_to_path(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def assert_safe_clean_target(out_dir: Path) -> None:
    target = out_dir.resolve()
    repo_root = Path(__file__).resolve().parent
    reports_root = (repo_root / "reports").resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    forbidden = {
        repo_root,
        repo_root.parent.resolve(),
        Path.home().resolve(),
        Path(target.anchor).resolve(),
        reports_root,
        temp_root,
    }

    if target in forbidden:
        raise ValueError(f"refusing to clean unsafe output directory: {target}")
    if is_relative_to_path(target, reports_root) or is_relative_to_path(target, temp_root):
        return
    raise ValueError(
        "refusing to clean output directory outside reports/ or the system temp directory: "
        f"{target}"
    )
