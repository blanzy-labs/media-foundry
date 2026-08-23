#!/usr/bin/env python3
"""Validate Production Batch 001 fixtures without judging aesthetics."""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grammar", required=True)
    parser.add_argument("--fixtures", nargs=3, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    checks = {}

    def record(name, passed, detail):
        checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}

    try:
        grammar = json.loads(Path(args.grammar).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        grammar = {}
        record("grammar", False, str(error))
    else:
        record("grammar", grammar.get("id") == "scrappy-diorama-v1", grammar.get("id", ""))

    fixtures = []
    errors = []
    allowed_props = {"glow", "book", "note", "line", "droplet", "planet", "star", "counter", "telescope"}
    for fixture_path in args.fixtures:
        try:
            fixture = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
            assert fixture["template"] == "scrappy_diorama"
            assert fixture["format"] == {"width":1080, "height":1920, "fps":30, "duration_seconds":15}
            assert fixture["intro"]["text"] == "WHAT YOU DIDN'T KNOW..."
            assert fixture["outro"]["text"] == "(s)Crap²y Games"
            assert fixture["outro"].get("tagline", "").strip()
            assert fixture["audio"]["enabled"] is True
            assert fixture["visual"]["kind"] == "prop_board"
            assert 4 <= len(fixture["visual"]["props"]) <= 12
            assert all(prop.get("type") in allowed_props for prop in fixture["visual"]["props"])
            assert all(-170 <= float(prop.get("x", 0)) <= 170 and -115 <= float(prop.get("y", 0)) <= 115 for prop in fixture["visual"]["props"])
            assert len(fixture["content"]["headline"]) <= 48
            assert len(fixture["content"]["body"]) <= 90
            assert len(fixture["content"]["emphasis"]) <= 32
            assert not any(key in fixture for key in ("renderer", "scene", "script"))
            fixtures.append(fixture)
        except (OSError, json.JSONDecodeError, AssertionError, KeyError, TypeError, ValueError) as error:
            errors.append(f"{fixture_path}: {type(error).__name__}")
    record("fixture_contracts", len(fixtures) == 3 and not errors, "; ".join(errors) or ",".join(f["id"] for f in fixtures))
    record("subject_set", {f["id"] for f in fixtures} == {"books", "mythadis", "venus"}, "books,mythadis,venus")
    record("shared_renderer_contract", all(f["visual"]["kind"] == "prop_board" for f in fixtures), "scrappy_diorama/prop_board")
    record("explicit_seeds", len({f["seed"] for f in fixtures}) == 3 if len(fixtures) == 3 else False, "unique deterministic fixture seeds")
    venus = next((f for f in fixtures if f.get("id") == "venus"), {})
    source_urls = [source.get("url", "") for source in venus.get("sources", [])]
    record("venus_source", "https://science.nasa.gov/venus/venus-facts/" in source_urls, "NASA Science")
    record("no_bespoke_renderers", all(not any(key in f for key in ("renderer", "scene", "script")) for f in fixtures), "one existing scene and renderer")
    passed = all(check["status"] == "PASS" for check in checks.values())
    result = {"batch":"production-batch-001", "type":"content_contract", "checks":checks, "result":"PASS" if passed else "FAIL"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
