#!/usr/bin/env python3
"""csv-preflight: a local, report-only CSV validator.

Reads a CSV file and an explicit JSON rules file, then emits a JSON report
of findings to stdout (or a file). Never modifies the input file. Never
makes network calls. Never claims email deliverability or import
compatibility with any downstream system -- it only checks the rules you
give it.

Rules file format (JSON):
{
  "headers": ["id", "email", "status"],
  "field_count": 3,
  "required": ["id", "email"],
  "unique": ["id"],
  "allowed_values": {"status": ["active", "inactive"]}
}

Record numbering: the header row is record 1. Data rows are numbered
starting at 2. A quoted field containing a newline does not create a new
logical record -- the csv module handles that for us because we read with
newline='' and let csv.reader do the parsing.

Exit codes:
  0  ran successfully, no findings (clean)
  1  ran successfully, findings reported
  2  operational error (bad args, bad rules, unreadable/malformed input)

Usage:
  python3 csv_preflight.py --input FILE.csv --rules RULES.json [--output OUT.json] [--max-bytes N]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

DEFAULT_MAX_BYTES = 50 * 1024 * 1024  # 50 MB, documented safety limit


class OperationalError(Exception):
    """Raised for errors that are not CSV content findings (bad input/rules)."""


def load_rules(rules_path: Path) -> dict:
    try:
        raw = rules_path.read_text(encoding="utf-8-sig")
    except OSError as error:
        raise OperationalError(f"cannot read rules file: {error}") from error
    try:
        rules = json.loads(raw)
    except json.JSONDecodeError as error:
        raise OperationalError(f"rules file is not valid JSON: {error}") from error

    if not isinstance(rules, dict):
        raise OperationalError("rules file must contain a JSON object")

    required_keys = {"headers", "field_count", "required", "unique", "allowed_values"}
    missing = required_keys - rules.keys()
    if missing:
        raise OperationalError(f"rules file missing required keys: {sorted(missing)}")

    if not isinstance(rules["headers"], list) or not all(isinstance(h, str) for h in rules["headers"]):
        raise OperationalError("rules.headers must be a list of strings")
    if len(set(rules["headers"])) != len(rules["headers"]):
        raise OperationalError("rules.headers contains duplicate column names")
    if not isinstance(rules["field_count"], int) or rules["field_count"] < 0:
        raise OperationalError("rules.field_count must be a non-negative integer")
    if not isinstance(rules["required"], list):
        raise OperationalError("rules.required must be a list")
    if not isinstance(rules["unique"], list):
        raise OperationalError("rules.unique must be a list")
    if not isinstance(rules["allowed_values"], dict):
        raise OperationalError("rules.allowed_values must be an object")

    headers_set = set(rules["headers"])
    for column in list(rules["required"]) + list(rules["unique"]) + list(rules["allowed_values"].keys()):
        if column not in headers_set:
            raise OperationalError(f"rules reference unknown column: {column!r}")

    return rules


def read_rows(input_path: Path, max_bytes: int) -> list[list[str]]:
    try:
        size = input_path.stat().st_size
    except OSError as error:
        raise OperationalError(f"cannot stat input file: {error}") from error
    if size > max_bytes:
        raise OperationalError(
            f"input file is {size} bytes, exceeds --max-bytes limit of {max_bytes}"
        )

    try:
        with input_path.open(newline="", encoding="utf-8-sig") as source:
            rows = list(csv.reader(source, strict=True))
    except UnicodeDecodeError as error:
        raise OperationalError(f"input file is not valid UTF-8: {error}") from error
    except csv.Error as error:
        raise OperationalError(f"malformed CSV (quoting error): {error}") from error
    except OSError as error:
        raise OperationalError(f"cannot read input file: {error}") from error

    if not rows:
        raise OperationalError("input file is empty")

    return rows


def validate(rows: list[list[str]], rules: dict) -> list[dict]:
    header_row = rows[0]
    if header_row != rules["headers"]:
        raise OperationalError(
            f"header mismatch: expected {rules['headers']}, got {header_row}"
        )

    findings: list[dict] = []
    seen: dict[str, dict[str, int]] = {column: {} for column in rules["unique"]}

    for record_number, row in enumerate(rows[1:], start=2):
        if len(row) != rules["field_count"]:
            findings.append({
                "record": record_number,
                "column": None,
                "rule": "ROW_WIDTH",
                "expected": rules["field_count"],
                "actual": len(row),
            })
            continue  # skip field-level checks for malformed-width rows

        values = dict(zip(header_row, row))

        for column in rules["required"]:
            if values[column] == "":
                findings.append({
                    "record": record_number,
                    "column": column,
                    "rule": "REQUIRED",
                })

        for column, previous in seen.items():
            value = values[column]
            if value in previous:
                findings.append({
                    "record": record_number,
                    "column": column,
                    "rule": "UNIQUE",
                    "duplicates_record": previous[value],
                })
            else:
                previous[value] = record_number

        for column, allowed in rules["allowed_values"].items():
            if values[column] not in allowed:
                findings.append({
                    "record": record_number,
                    "column": column,
                    "rule": "ALLOWED_VALUE",
                })

    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="csv_preflight.py",
        description="Local, report-only CSV validator. Checks a CSV against explicit rules "
                    "and emits a JSON findings report. Never modifies input. Never uploads data.",
    )
    parser.add_argument("--input", required=True, type=Path, help="Path to the CSV file to check.")
    parser.add_argument("--rules", required=True, type=Path, help="Path to the JSON rules file.")
    parser.add_argument("--output", type=Path, default=None,
                         help="Path to write the JSON report (default: stdout).")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                         help=f"Reject input larger than this many bytes (default: {DEFAULT_MAX_BYTES}).")
    args = parser.parse_args(argv)

    try:
        rules = load_rules(args.rules)
        rows = read_rows(args.input, args.max_bytes)
        findings = validate(rows, rules)
    except OperationalError as error:
        report = {"status": "error", "error": str(error)}
        text = json.dumps(report, indent=2)
        print(text, file=sys.stderr)
        return 2

    report = {
        "status": "clean" if not findings else "findings",
        "input": str(args.input),
        "rules": str(args.rules),
        "records_checked": len(rows) - 1,
        "findings": findings,
    }
    text = json.dumps(report, indent=2)

    if args.output:
        try:
            args.output.write_text(text + "\n", encoding="utf-8")
        except OSError as error:
            print(json.dumps({"status": "error", "error": f"cannot write output: {error}"}), file=sys.stderr)
            return 2
    else:
        print(text)

    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
