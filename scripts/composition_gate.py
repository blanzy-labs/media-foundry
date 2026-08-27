#!/usr/bin/env python3
"""Campaign-facing composition authorization hook for complex scene jobs."""

import argparse
import json
from pathlib import Path

from composition_contract import authorize_animation, requires_composition_gate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text())
    if not requires_composition_gate(manifest):
        result = {"state": "COMPOSITION_NOT_REQUIRED", "animation_authorized": True}
    else:
        result = authorize_animation(manifest)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(rendered)
    print(rendered, end="")
    return 0 if result["animation_authorized"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
