from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


TEXT_SUFFIXES = {
    ".csv",
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".py",
    ".ps1",
    ".txt",
}

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("generic_api_key_assignment", re.compile(r"(?i)\b(api[_-]?key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_.-]{24,}")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9_.-]{24,}")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

ALLOWLIST_PATTERNS = [
    re.compile(r"FAKE_[A-Z0-9_]+"),
    re.compile(r"HDF011"),
    re.compile(r"example_cli_jsonl"),
]


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    kind: str
    excerpt: str


def should_scan(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in TEXT_SUFFIXES


def masked_excerpt(text: str, start: int, end: int) -> str:
    left = max(0, start - 30)
    right = min(len(text), end + 30)
    match = text[start:end]
    if len(match) <= 8:
        masked = "***"
    else:
        masked = f"{match[:4]}...{match[-4:]}"
    return (text[left:start] + masked + text[end:right]).strip()


def is_allowlisted(match_text: str, line_text: str) -> bool:
    return any(pattern.search(match_text) or pattern.search(line_text) for pattern in ALLOWLIST_PATTERNS)


def scan_text(path: Path, root: Path) -> list[Finding]:
    findings: list[Finding] = []
    resolved_path = path.resolve()
    try:
        display_path = str(resolved_path.relative_to(root))
    except ValueError:
        display_path = str(resolved_path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return findings
    for line_number, line in enumerate(lines, start=1):
        for kind, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(line):
                if is_allowlisted(match.group(0), line):
                    continue
                findings.append(
                    Finding(
                        path=display_path,
                        line=line_number,
                        kind=kind,
                        excerpt=masked_excerpt(line, match.start(), match.end()),
                    )
                )
    return findings


def iter_scan_files(targets: list[Path]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        if target.is_dir():
            files.extend(path for path in target.rglob("*") if should_scan(path))
        elif should_scan(target):
            files.append(target)
    return sorted(set(files))


def build_report(targets: list[Path], root: Path) -> dict[str, object]:
    findings: list[Finding] = []
    files = iter_scan_files(targets)
    for path in files:
        findings.extend(scan_text(path, root))
    return {
        "target_count": len(targets),
        "file_count": len(files),
        "finding_count": len(findings),
        "findings": [asdict(finding) for finding in findings],
    }


def write_markdown(path: Path, report: dict[str, object]) -> None:
    lines = [
        "# Artifact Secret Scan",
        "",
        f"- Files scanned: `{report['file_count']}`",
        f"- Findings: `{report['finding_count']}`",
        "",
    ]
    findings = report["findings"]
    if not findings:
        lines.append("No credential-like findings.")
    else:
        lines.extend(["| path | line | kind | excerpt |", "|---|---:|---|---|"])
        for finding in findings:
            lines.append(
                "| {path} | {line} | {kind} | `{excerpt}` |".format(**finding)
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan generated artifacts for credential-like strings.")
    parser.add_argument("targets", nargs="+", type=Path, help="Files or directories to scan.")
    parser.add_argument("--out-dir", type=Path, default=Path("reports/artifact_secret_scan"))
    parser.add_argument("--allow-findings", action="store_true", help="Write reports but return success even with findings.")
    args = parser.parse_args(argv)

    root = Path.cwd().resolve()
    report = build_report(args.targets, root)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "artifact_secret_scan.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(args.out_dir / "artifact_secret_scan.md", report)
    print(args.out_dir / "artifact_secret_scan.md")
    return 0 if args.allow_findings or report["finding_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
