#!/usr/bin/env python3
"""Independent, fail-closed validation for MF-002R1 text geometry."""

import argparse
import json
import sys
from pathlib import Path


REQUIRED_ROLES = {"INTRO", "HEADLINE", "BODY", "EMPHASIS", "LABEL", "OUTRO"}
REQUIRED_AREAS = {
    "INTRO_SAFE_AREA", "INTRO_LABEL_SAFE_AREA", "HEADLINE_SAFE_AREA",
    "BODY_SAFE_AREA", "EMPHASIS_SAFE_AREA", "LABEL_SAFE_AREA",
    "OUTRO_SAFE_AREA", "OUTRO_LABEL_SAFE_AREA",
}
REQUIRED_INSTANCES = {"intro", "intro_label", "headline", "body", "emphasis", "visual_label", "outro", "outro_label"}
CONSTRAINT_FIELDS = {
    "preferred_font_size", "min_font_size", "max_lines", "line_spacing",
    "min_line_spacing", "wrap", "fit_mode", "horizontal_alignment", "vertical_alignment",
}
EPSILON = 0.05


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rect(value):
    return tuple(float(value[key]) for key in ("x", "y", "width", "height"))


def contains(outer, inner):
    ox, oy, ow, oh = outer
    ix, iy, iw, ih = inner
    return (
        iw >= 0 and ih >= 0
        and ix >= ox - EPSILON and iy >= oy - EPSILON
        and ix + iw <= ox + ow + EPSILON
        and iy + ih <= oy + oh + EPSILON
    )


def intersects(first, second):
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def stage_rect(area):
    x, y, width, height = rect(area)
    origin = area.get("stage_origin", [0, 0])
    return x + float(origin[0]), y + float(origin[1]), width, height


def validate_grammar(grammar, errors):
    typography = grammar.get("typography")
    if not isinstance(typography, dict):
        errors.append("CONFIG_LAYOUT_FAILED: missing typography object")
        return
    roles = typography.get("roles", {})
    missing_roles = sorted(REQUIRED_ROLES - set(roles))
    if missing_roles:
        errors.append(f"CONFIG_LAYOUT_FAILED: missing roles {missing_roles}")
    for name in sorted(REQUIRED_ROLES & set(roles)):
        role = roles[name]
        missing = sorted(CONSTRAINT_FIELDS - set(role))
        if missing:
            errors.append(f"{name}_LAYOUT_FAILED: missing constraints {missing}")
            continue
        preferred = role["preferred_font_size"]
        minimum = role["min_font_size"]
        if not (isinstance(preferred, int) and isinstance(minimum, int) and 0 < minimum <= preferred):
            errors.append(f"{name}_LAYOUT_FAILED: invalid font-size bounds")
        if role["wrap"] is not True or role["fit_mode"] != "shrink_to_fit":
            errors.append(f"{name}_LAYOUT_FAILED: unsupported fitting policy")
        if role["horizontal_alignment"] != "center" or role["vertical_alignment"] != "center":
            errors.append(f"{name}_LAYOUT_FAILED: unsupported alignment")
    areas = typography.get("safe_areas", {})
    missing_areas = sorted(REQUIRED_AREAS - set(areas))
    if missing_areas:
        errors.append(f"CONFIG_LAYOUT_FAILED: missing safe-area definitions {missing_areas}")
    panels = typography.get("panels", {})
    for name, area in areas.items():
        try:
            area_rect = rect(area)
        except (KeyError, TypeError, ValueError):
            errors.append(f"CONFIG_LAYOUT_FAILED: malformed safe area {name}")
            continue
        panel_name = area.get("panel")
        if panel_name not in panels:
            errors.append(f"CONFIG_LAYOUT_FAILED: {name} references missing panel {panel_name!r}")
            continue
        try:
            panel_rect = rect(panels[panel_name])
        except (KeyError, TypeError, ValueError):
            errors.append(f"CONFIG_LAYOUT_FAILED: malformed panel {panel_name}")
            continue
        if not contains(panel_rect, area_rect):
            errors.append(f"CONFIG_LAYOUT_FAILED: {name} escapes panel {panel_name}")
        if area.get("role") not in roles:
            errors.append(f"CONFIG_LAYOUT_FAILED: {name} references missing role")
    for pair in typography.get("collision_checks", []):
        if not isinstance(pair, list) or len(pair) != 2 or any(name not in areas for name in pair):
            errors.append(f"CONFIG_LAYOUT_FAILED: malformed collision pair {pair!r}")
        elif intersects(stage_rect(areas[pair[0]]), stage_rect(areas[pair[1]])):
            errors.append(f"COLLISION_LAYOUT_FAILED: {pair[0]} overlaps {pair[1]}")
    derived = typography.get("derived_safe_areas", {})
    required_derived = {"PROP_NOTE_LABEL_SAFE_AREA", "PROP_COUNTER_LABEL_SAFE_AREA", "PROP_COUNTER_VALUE_SAFE_AREA"}
    if not required_derived <= set(derived):
        errors.append(f"CONFIG_LAYOUT_FAILED: missing derived safe areas {sorted(required_derived - set(derived))}")
    for name, rule in derived.items():
        if rule.get("role") not in roles or rule.get("container") not in {"note", "counter"}:
            errors.append(f"CONFIG_LAYOUT_FAILED: malformed derived safe area {name}")
    iterations = typography.get("max_fit_iterations")
    if not isinstance(iterations, int) or not 1 <= iterations <= 64:
        errors.append("CONFIG_LAYOUT_FAILED: max_fit_iterations must be between 1 and 64")
    if roles.get("HEADLINE", {}).get("min_font_size", 0) <= roles.get("BODY", {}).get("preferred_font_size", 999):
        errors.append("HIERARCHY_LAYOUT_FAILED: headline minimum must exceed body preferred size")


def validate_report(path, report, grammar, errors):
    fixture = report.get("fixture", Path(path).stem)
    if report.get("slice") != "MF-002R1" or report.get("result") != "PASS":
        failure = report.get("failure", {})
        errors.append(f"{failure.get('code', 'LAYOUT_FAILED')}: fixture={fixture} reason={failure.get('reason', report.get('reason', 'renderer rejected layout'))}")
        return
    layouts = report.get("layout", {})
    missing = sorted(REQUIRED_INSTANCES - set(layouts))
    if missing:
        errors.append(f"CONFIG_LAYOUT_FAILED: fixture={fixture} missing layout results {missing}")
        return
    safe_areas = grammar["typography"]["safe_areas"]
    derived_areas = grammar["typography"].get("derived_safe_areas", {})
    roles = grammar["typography"]["roles"]
    for key, item in layouts.items():
        role = item.get("role")
        area_name = item.get("safe_area")
        if item.get("status") != "PASS" or role not in roles or area_name not in safe_areas | derived_areas:
            errors.append(f"LAYOUT_FAILED: fixture={fixture} element={key} has invalid role, area, or status")
            continue
        try:
            reported_safe = rect(item["safe_rect"])
            rendered = rect(item["rendered_rect"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{role}_LAYOUT_FAILED: fixture={fixture} element={key} malformed geometry")
            continue
        if area_name in safe_areas:
            configured_safe = rect(safe_areas[area_name])
            if any(abs(a - b) > EPSILON for a, b in zip(configured_safe, reported_safe)):
                errors.append(f"{role}_LAYOUT_FAILED: fixture={fixture} element={key} safe area differs from template")
        else:
            try:
                container = rect(item["container_rect"])
            except (KeyError, TypeError, ValueError):
                errors.append(f"{role}_LAYOUT_FAILED: fixture={fixture} element={key} missing derived container geometry")
                continue
            if not contains(container, reported_safe):
                errors.append(f"{role}_LAYOUT_FAILED: fixture={fixture} element={key} derived safe area escapes its container")
        if not contains(reported_safe, rendered):
            errors.append(f"{role}_LAYOUT_FAILED: fixture={fixture} element={key} rendered_rect={rendered} safe_rect={reported_safe}")
        size = item.get("font_size")
        if not isinstance(size, int) or not roles[role]["min_font_size"] <= size <= roles[role]["preferred_font_size"]:
            errors.append(f"{role}_LAYOUT_FAILED: fixture={fixture} element={key} font size {size} violates constraints")
        if not 1 <= item.get("line_count", 0) <= roles[role]["max_lines"]:
            errors.append(f"{role}_LAYOUT_FAILED: fixture={fixture} element={key} line count violates constraints")
    if layouts["headline"].get("font_size", 0) <= layouts["body"].get("font_size", 999):
        errors.append(f"HIERARCHY_LAYOUT_FAILED: fixture={fixture} headline no longer dominates body")
    if report.get("overlap_checks") != "PASS":
        errors.append(f"COLLISION_LAYOUT_FAILED: fixture={fixture} overlap checks did not pass")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grammar", required=True)
    parser.add_argument("--reports", nargs="*", default=[])
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    errors = []
    try:
        grammar = load_json(args.grammar)
    except (OSError, json.JSONDecodeError) as error:
        grammar = {}
        errors.append(f"CONFIG_LAYOUT_FAILED: cannot read grammar: {error}")
    validate_grammar(grammar, errors)
    reports = []
    if not errors:
        for path in args.reports:
            try:
                report = load_json(path)
            except (OSError, json.JSONDecodeError) as error:
                errors.append(f"LAYOUT_FAILED: cannot read report {path}: {error}")
                continue
            reports.append(report)
            validate_report(path, report, grammar, errors)
    result = {
        "slice": "MF-002R1", "type": "independent_layout_validation",
        "grammar": "PASS" if not any("CONFIG_" in error for error in errors) else "FAIL",
        "fixtures": {report.get("fixture", "unknown"): report.get("result", "FAIL") for report in reports},
        "layout": {
            "intro": "PASS" if not errors else "FAIL", "headline": "PASS" if not errors else "FAIL",
            "body": "PASS" if not errors else "FAIL", "emphasis": "PASS" if not errors else "FAIL",
            "labels": "PASS" if not errors else "FAIL", "outro": "PASS" if not errors else "FAIL",
            "overlap_checks": "PASS" if not errors else "FAIL",
        },
        "errors": errors, "result": "PASS" if not errors else "FAIL",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
