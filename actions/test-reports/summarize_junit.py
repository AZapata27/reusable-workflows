#!/usr/bin/env python3
"""Summarise JUnit XML reports into $GITHUB_STEP_SUMMARY and $GITHUB_OUTPUT.

Standard library only, so it runs on any GitHub-hosted runner without extra setup.
Counts are computed from <testcase> elements (not from <testsuite> attributes), which
works for Gradle, Maven Surefire/Failsafe and the Node.js `junit` test reporter alike.

Environment:
  REPORT_WORKDIR  directory the globs are resolved against (default ".")
  REPORT_GLOBS    newline-separated globs, "**" supported
  REPORT_TITLE    heading for the summary (default "Test results")
"""

from __future__ import annotations

import glob
import os
import sys
import xml.etree.ElementTree as ET

MAX_LISTED_FAILURES = 20
MAX_MESSAGE_LENGTH = 200


def find_reports(workdir: str, patterns: list[str]) -> list[str]:
    files: set[str] = set()
    for pattern in patterns:
        for path in glob.glob(os.path.join(workdir, pattern), recursive=True):
            if os.path.isfile(path) and path.endswith(".xml"):
                files.add(os.path.normpath(path))
    return sorted(files)


def one_line(text: str | None) -> str:
    text = " ".join((text or "").split())
    text = text.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")
    if len(text) > MAX_MESSAGE_LENGTH:
        text = text[: MAX_MESSAGE_LENGTH - 1] + "…"
    return text


def summarise(files: list[str]) -> tuple[dict[str, int], list[tuple[str, str]], list[str]]:
    counts = {"total": 0, "passed": 0, "failed": 0, "skipped": 0}
    failures: list[tuple[str, str]] = []
    unreadable: list[str] = []
    for path in files:
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError):
            unreadable.append(path)
            continue
        for case in root.iter("testcase"):
            counts["total"] += 1
            problem = case.find("failure")
            if problem is None:
                problem = case.find("error")
            if problem is not None:
                counts["failed"] += 1
                name = ".".join(filter(None, [case.get("classname"), case.get("name")]))
                failures.append((name or "(unnamed)", one_line(problem.get("message") or problem.text)))
            elif case.find("skipped") is not None:
                counts["skipped"] += 1
            else:
                counts["passed"] += 1
    return counts, failures, unreadable


def render(title: str, workdir: str, files: list[str], counts: dict[str, int],
           failures: list[tuple[str, str]], unreadable: list[str]) -> str:
    lines = [f"### {title}", ""]
    if not files:
        lines.append(f"No JUnit XML reports found under `{workdir}`.")
        return "\n".join(lines) + "\n"
    status = "❌ failures" if counts["failed"] else "✅ all passed"
    lines += [
        f"{status} · {len(files)} report file(s) under `{workdir}`",
        "",
        "| Total | Passed | Failed | Skipped |",
        "| ---: | ---: | ---: | ---: |",
        f"| {counts['total']} | {counts['passed']} | {counts['failed']} | {counts['skipped']} |",
    ]
    if failures:
        lines += ["", "<details open><summary>Failed tests</summary>", "",
                  "| Test | Message |", "| --- | --- |"]
        for name, message in failures[:MAX_LISTED_FAILURES]:
            lines.append(f"| `{one_line(name)}` | {message} |")
        if len(failures) > MAX_LISTED_FAILURES:
            lines.append(f"| … | {len(failures) - MAX_LISTED_FAILURES} more |")
        lines += ["", "</details>"]
    if unreadable:
        lines += ["", f"⚠️ {len(unreadable)} file(s) could not be parsed as XML."]
    return "\n".join(lines) + "\n"


def append(env_var: str, content: str) -> None:
    target = os.environ.get(env_var)
    if not target:
        sys.stdout.buffer.write(content.encode("utf-8"))
        sys.stdout.flush()
        return
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(content)


def main() -> int:
    workdir = os.environ.get("REPORT_WORKDIR") or "."
    patterns = [p.strip() for p in os.environ.get("REPORT_GLOBS", "").splitlines() if p.strip()]
    title = os.environ.get("REPORT_TITLE") or "Test results"

    files = find_reports(workdir, patterns)
    counts, failures, unreadable = summarise(files)

    append("GITHUB_STEP_SUMMARY", render(title, workdir, files, counts, failures, unreadable))
    append("GITHUB_OUTPUT", "".join(f"{key}={value}\n" for key, value in counts.items()))
    for path in unreadable:
        print(f"::warning title=test-reports::Could not parse {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
