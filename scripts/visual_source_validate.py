#!/usr/bin/env python3
"""CLI for machine-readable visual-source assessment and validation."""

import argparse
import json
from pathlib import Path

from visual_source_contract import validate_visual_source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    definition = json.loads((root / args.config).read_text())
    result = validate_visual_source(root, definition)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        output = root / args.output; output.parent.mkdir(parents=True, exist_ok=True); output.write_text(rendered)
    print(rendered, end="")
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
