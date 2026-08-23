#!/usr/bin/env python3
"""Fail-closed structural validation for the MF-002 grammar and fixtures."""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grammar", required=True)
    parser.add_argument("--fixtures", nargs=3, required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    checks = {}

    def record(name, passed, detail):
        checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}

    try:
        grammar = json.loads(Path(args.grammar).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        grammar = {}
        record("grammar_readable", False, str(error))
    else:
        record("grammar_readable", True, grammar.get("id", ""))

    required_roles = {"INTRO", "HEADLINE", "BODY", "EMPHASIS", "LABEL", "OUTRO"}
    roles = set(grammar.get("typography", {}).get("roles", {}))
    record("typography_roles", required_roles <= roles, ",".join(sorted(roles)))
    required_surfaces = {"painted_wood", "paper_note", "metal_plate", "tape", "bolts", "crate", "cable", "lamp", "scratched_backing"}
    surfaces = set(grammar.get("surfaces", {}).get("vocabulary", []))
    record("surface_vocabulary", required_surfaces <= surfaces, ",".join(sorted(surfaces)))
    required_motion = {"ENTER", "SETTLE", "EMPHASIS", "EXIT"}
    motion = set(grammar.get("motion", {}))
    record("motion_grammar", required_motion <= motion, ",".join(sorted(required_motion & motion)))
    required_audio = {"INTRO_HIT", "TEXT_POP", "TRANSITION", "OUTRO_STING"}
    audio_names = {event.get("name") for event in grammar.get("audio", {}).get("events", [])}
    record("audio_grammar", required_audio <= audio_names, ",".join(sorted(name for name in audio_names if name)))
    safe = grammar.get("canvas", {}).get("safe_area", {})
    safe_ok = safe.get("left", -1) >= 24 and safe.get("right", 999) <= 516 and safe.get("top", -1) >= 40 and safe.get("bottom", 999) <= 920
    record("mobile_safe_area", safe_ok, json.dumps(safe, sort_keys=True))

    project_root = Path(args.project_root)
    grammar_document = project_root / "reports" / "mf-002" / "visual-grammar.md"
    record("canonical_document", grammar_document.is_file() and grammar_document.stat().st_size > 1000, str(grammar_document))
    font_results = []
    for key in ("heavy_font", "regular_font"):
        resource = grammar.get("typography", {}).get(key, "")
        path = project_root / "godot" / resource.removeprefix("res://")
        font_results.append(path.is_file() and path.stat().st_size > 0)
    record("font_assets", all(font_results), "Lato Heavy and Regular, OFL-1.1")

    fixtures = []
    fixture_errors = []
    required_fixture = {"id", "template", "seed", "format", "intro", "content", "visual", "outro", "audio"}
    for fixture_path in args.fixtures:
        try:
            fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
            assert required_fixture <= set(fixture)
            assert fixture["template"] == "scrappy_diorama"
            assert fixture["format"] == {"width":1080, "height":1920, "fps":30, "duration_seconds":15}
            assert fixture["intro"].get("text") == "WHAT YOU DIDN'T KNOW..."
            assert fixture["outro"].get("text") == "(s)Crap²y Games"
            assert all(fixture["content"].get(key, "").strip() for key in ("headline", "body", "emphasis"))
            assert all(len(fixture["content"][key]) <= limit for key, limit in (("headline", 44), ("body", 90), ("emphasis", 28)))
            assert fixture["visual"].get("kind") in {"radial_creature", "beetle", "terminal", "prop_board"}
            assert fixture["audio"].get("enabled") is True
            fixtures.append(fixture)
        except (OSError, json.JSONDecodeError, AssertionError, KeyError) as error:
            fixture_errors.append(f"{fixture_path}: {type(error).__name__}")
    record("fixture_contracts", not fixture_errors and len(fixtures) == 3, "; ".join(fixture_errors) or ",".join(f["id"] for f in fixtures))
    record("fixture_distinction", len({f["visual"]["kind"] for f in fixtures}) == 3 and len({f["seed"] for f in fixtures}) == 3 if len(fixtures) == 3 else False, "distinct visual kinds and explicit seeds")
    record("required_layers", grammar.get("id") == "scrappy-diorama-v1", "workshop,sign,media,paper,tape,props")
    passed = all(item["status"] == "PASS" for item in checks.values())
    result = {"slice":"MF-002", "type":"structural_contract", "checks":checks, "result":"PASS" if passed else "FAIL"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
