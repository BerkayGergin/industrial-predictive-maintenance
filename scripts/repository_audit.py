\
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    "htmlcov", "dist", "build",
}
EXCLUDED_FILES = {".env"}

PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "email address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "Windows user path": re.compile(r"\b[A-Za-z]:\\Users\\[^\\\s]+", re.I),
    "Unix home path": re.compile(r"/home/[^/\s]+"),
}


def repository_files() -> list[Path]:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(ROOT), "ls-files"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if out.strip():
            return [ROOT / line for line in out.splitlines()]
    except Exception:
        pass

    result: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.name in EXCLUDED_FILES:
            continue
        result.append(path)
    return result


def main() -> None:
    findings: list[str] = []

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    if ".env" not in gitignore:
        findings.append(".gitignore does not exclude .env")
    if ".env" not in dockerignore:
        findings.append(".dockerignore does not exclude .env")

    for path in repository_files():
        if path.resolve() == Path(__file__).resolve():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        rel = path.relative_to(ROOT)
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                findings.append(f"{rel}: possible {label}: {match.group(0)!r}")

    if findings:
        print("Repository audit FAILED:")
        for item in findings:
            print(f" - {item}")
        raise SystemExit(1)

    print("Repository audit passed: no obvious committed secrets or personal paths found.")


if __name__ == "__main__":
    main()
