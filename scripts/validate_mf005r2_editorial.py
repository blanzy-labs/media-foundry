#!/usr/bin/env python3
"""Structurally validate MF-005R2's explicit editorial communication contract."""

import argparse
import json
from pathlib import Path


REQUIRED = {"game_type", "protagonist", "premise", "product_name"}


def validate(fixture):
    errors = []
    editorial = fixture.get("editorial", {})
    beats = {beat.get("id"): beat for beat in fixture.get("beats", [])}
    required = set(editorial.get("required_messages", []))
    owners = editorial.get("message_beats", {})
    spoken = editorial.get("required_spoken", {}).get("product_name", "")
    visual = editorial.get("required_visual", {}).get("product_name", "")
    if editorial.get("objective") != "promote_game" or required != REQUIRED:
        errors.append("EDITORIAL_REQUIREMENT_FAILED: required communication outcomes are incomplete")
    for message in REQUIRED:
        if owners.get(message) not in beats:
            errors.append(f"EDITORIAL_REQUIREMENT_FAILED: {message} has no valid owning beat")
    reveal = beats.get(owners.get("product_name"), {})
    narration = reveal.get("narration") or {}
    if not spoken or spoken.casefold() not in str(narration.get("text", "")).casefold():
        errors.append("EDITORIAL_REQUIREMENT_FAILED: required_spoken: product_name")
    if not visual or str(reveal.get("text", "")).casefold() != str(visual).casefold():
        errors.append("EDITORIAL_REQUIREMENT_FAILED: required_visual: product_name")
    media = fixture.get("media", {})
    if editorial.get("required_visual", {}).get("authentic_game_media") is not True or media.get("required") is not True or media.get("provenance", {}).get("type") != "project_asset":
        errors.append("EDITORIAL_REQUIREMENT_FAILED: authentic_game_media")
    checks = {
        "game_identified": "PASS" if "product_name" not in " ".join(errors) else "FAIL",
        "stealth_game_communicated": "PASS" if owners.get("game_type") in beats else "FAIL",
        "dung_beetle_communicated": "PASS" if owners.get("protagonist") in beats else "FAIL",
        "turd_stealing_premise_communicated": "PASS" if owners.get("premise") in beats else "FAIL",
        "product_name_visual": "PASS" if visual and str(reveal.get("text", "")).casefold() == str(visual).casefold() else "FAIL",
        "product_name_spoken": "PASS" if spoken and spoken.casefold() in str(narration.get("text", "")).casefold() else "FAIL",
        "authentic_game_media": "PASS" if not any("authentic_game_media" in item for item in errors) else "FAIL",
    }
    return {"slice": "MF-005R2", "fixture": fixture.get("id"), "checks": checks, "errors": errors, "result": "PASS" if not errors else "FAIL"}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--fixture", required=True); parser.add_argument("--output", required=True); args = parser.parse_args()
    try:
        result = validate(json.loads(Path(args.fixture).read_text()))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        result = {"slice": "MF-005R2", "errors": [str(error)], "result": "FAIL"}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2)); return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
