#!/usr/bin/env python3
"""Semantic scene-layout validation and fail-closed composition gating."""

from __future__ import annotations

import math


SEMANTIC_ROLES = {
    "hero", "primary_subject", "support_subject", "foreground_frame",
    "background_structure", "depth_element", "light_source", "story_prop",
    "machine_support", "atmosphere", "text", "decorative",
}

VISUAL_PURPOSES = {
    "establish_scale", "establish_depth", "frame_hero", "support_story",
    "communicate_machine_state", "provide_light", "guide_eye",
    "establish_location", "create_foreground_depth", "support_perspective",
}

ZONE_KINDS = {
    "hero_zone", "support_zone", "foreground_zone", "background_zone",
    "negative_space_zone", "text_safe_zone", "no_occlusion_zone",
}

REPAIR_LAYERS = {
    "COMPOSITION_OBJECT", "COMPOSITION_OCCLUSION", "COMPOSITION_HIERARCHY",
    "COMPOSITION_DENSITY", "COMPOSITION_PERSPECTIVE", "COMPOSITION_TEXT_SAFETY",
}


def overlaps(left: dict, right: dict) -> bool:
    return (left["x"] < right["x"] + right["width"]
            and left["x"] + left["width"] > right["x"]
            and left["y"] < right["y"] + right["height"]
            and left["y"] + left["height"] > right["y"])


def contains(zone: dict, bounds: dict, tolerance: float = 1e-8) -> bool:
    return (bounds["x"] + tolerance >= zone["x"]
            and bounds["y"] + tolerance >= zone["y"]
            and bounds["x"] + bounds["width"] <= zone["x"] + zone["width"] + tolerance
            and bounds["y"] + bounds["height"] <= zone["y"] + zone["height"] + tolerance)


def line_bounds(points: list[list[float]]) -> dict:
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    return {"x": min(xs), "y": min(ys), "width": max(xs) - min(xs), "height": max(ys) - min(ys)}


def object_bounds(obj: dict) -> dict:
    geometry = obj.get("geometry", {})
    if geometry.get("kind") == "line":
        return line_bounds(geometry.get("points", []))
    return {key: geometry.get(key, 0) for key in ("x", "y", "width", "height")}


def requires_composition_gate(job: dict) -> bool:
    """Legacy/simple jobs remain compatible unless explicitly complex."""
    return job.get("complex_scene") is True or job.get("composition", {}).get("required") is True


def authorize_animation(manifest: dict) -> dict:
    """Fail closed: static checks and explicit human approval are both required."""
    validation = validate_manifest(manifest)
    approval = manifest.get("approval", {})
    human_ready = approval.get("human_status") == "APPROVED" and bool(approval.get("reviewer"))
    ready = validation["result"] == "PASS" and human_ready
    return {
        "state": "COMPOSITION_READY" if ready else "BLOCKED_COMPOSITION",
        "animation_authorized": ready,
        "machine_validation": validation["result"],
        "human_status": approval.get("human_status", "PENDING_HUMAN"),
        "reason": None if ready else ("HUMAN_COMPOSITION_APPROVAL_REQUIRED" if validation["result"] == "PASS"
                                      else "COMPOSITION_VALIDATION_FAILED"),
    }


def validate_manifest(manifest: dict) -> dict:
    errors, advisories, checks = [], [], {}

    def check(name: str, passed: bool, code: str, layer: str) -> None:
        checks[name] = "PASS" if passed else "FAIL"
        if not passed:
            errors.append({"code": code, "repair_layer": layer})

    zones = manifest.get("zones", [])
    zone_by_id = {zone.get("id"): zone for zone in zones if isinstance(zone, dict)}
    kinds = {zone.get("kind") for zone in zones}
    required_kinds = {"hero_zone", "support_zone", "foreground_zone", "background_zone",
                      "negative_space_zone", "text_safe_zone", "no_occlusion_zone"}
    zone_geometry_ok = all(set(("id", "kind", "x", "y", "width", "height")) <= set(zone)
                           and zone.get("kind") in ZONE_KINDS
                           and all(0 <= zone.get(key, -1) <= 1 for key in ("x", "y", "width", "height"))
                           and zone["x"] + zone["width"] <= 1.000001
                           and zone["y"] + zone["height"] <= 1.000001 for zone in zones)
    check("zone_vocabulary_and_geometry", bool(zones) and zone_geometry_ok, "INVALID_SCENE_ZONE", "COMPOSITION_PERSPECTIVE")
    check("required_zone_kinds", required_kinds <= kinds, "REQUIRED_SCENE_ZONE_MISSING", "COMPOSITION_OBJECT")

    objects = manifest.get("objects", [])
    ids = [obj.get("id") for obj in objects]
    check("unique_object_ids", bool(objects) and len(ids) == len(set(ids)) and all(ids), "DUPLICATE_OR_MISSING_OBJECT_ID", "COMPOSITION_OBJECT")
    invalid_roles = [obj.get("id") for obj in objects if obj.get("semantic_role") not in SEMANTIC_ROLES]
    check("semantic_role_required", not invalid_roles, "MISSING_OR_INVALID_SEMANTIC_ROLE", "COMPOSITION_OBJECT")
    invalid_purpose = [obj.get("id") for obj in objects
                       if not obj.get("purpose") or "fill_empty_space" in obj.get("purpose", [])
                       or not set(obj.get("purpose", [])) <= VISUAL_PURPOSES]
    check("valid_visual_purpose_required", not invalid_purpose, "INVALID_VISUAL_PURPOSE", "COMPOSITION_OBJECT")
    remove_policy = all(obj.get("remove_if_no_visual_purpose") is True for obj in objects)
    check("remove_if_unnecessary_policy", remove_policy, "REMOVE_IF_UNNECESSARY_POLICY_MISSING", "COMPOSITION_OBJECT")

    priorities = manifest.get("hierarchy", {})
    hierarchy_ok = (priorities.get("primary") in ids and priorities.get("secondary") in ids
                    and bool(priorities.get("tertiary")) and set(priorities.get("tertiary", [])) <= set(ids))
    check("visual_hierarchy", hierarchy_ok, "VISUAL_HIERARCHY_INVALID", "COMPOSITION_HIERARCHY")

    zone_failures, clipping, negative_intrusions, hero_intrusions, text_intrusions = [], [], [], [], []
    long_line_failures, large_shape_failures = [], []
    hero_id = priorities.get("primary")
    protected = [zone for zone in zones if zone.get("kind") in {"hero_zone", "no_occlusion_zone", "text_safe_zone"}]
    negative = [zone for zone in zones if zone.get("kind") == "negative_space_zone" and zone.get("preserve") is True]
    major_zones = [zone for zone in zones if zone.get("kind") in {"hero_zone", "support_zone", "foreground_zone"}]
    for obj in objects:
        bounds = object_bounds(obj)
        if not all(0 <= bounds[key] <= 1 for key in ("x", "y", "width", "height")) \
                or bounds["x"] + bounds["width"] > 1.000001 or bounds["y"] + bounds["height"] > 1.000001:
            clipping.append(obj.get("id"))
        allowed = zone_by_id.get(obj.get("allowed_zone"))
        if not allowed or not contains(allowed, bounds):
            zone_failures.append(obj.get("id"))
        if obj.get("id") != hero_id and obj.get("semantic_role") not in {"atmosphere", "background_structure"}:
            for zone in negative:
                if overlaps(bounds, zone):
                    negative_intrusions.append(obj.get("id"))
            for zone in protected:
                if overlaps(bounds, zone):
                    intentional = (obj.get("occlusion_role") == "intentional"
                                   and bool(obj.get("occlusion_reason"))
                                   and zone.get("id") in obj.get("may_occlude", []))
                    if not intentional:
                        if zone.get("kind") in {"hero_zone", "no_occlusion_zone"}:
                            hero_intrusions.append(obj.get("id"))
                        else:
                            text_intrusions.append(obj.get("id"))
        geometry = obj.get("geometry", {})
        if geometry.get("kind") == "line":
            points = geometry.get("points", [])
            length = sum(math.dist(a, b) for a, b in zip(points, points[1:])) if len(points) >= 2 else 0
            crossings = [zone["id"] for zone in major_zones if overlaps(bounds, zone)]
            if length > .35 and len(crossings) > 1 and not obj.get("long_line_justification"):
                long_line_failures.append(obj.get("id"))
        area = bounds["width"] * bounds["height"]
        if obj.get("id") != hero_id and obj.get("semantic_role") != "background_structure" \
                and area > .16 and obj.get("estimated_contrast", 0) >= .75:
            if not ({"frame_hero", "create_foreground_depth", "establish_location"} & set(obj.get("purpose", []))):
                large_shape_failures.append(obj.get("id"))

    check("objects_inside_allowed_zones", not zone_failures, "OBJECT_OUTSIDE_ALLOWED_ZONE", "COMPOSITION_PERSPECTIVE")
    check("no_unexpected_frame_clipping", not clipping, "OBJECT_CLIPS_FRAME", "COMPOSITION_PERSPECTIVE")
    check("preserved_negative_space", not negative_intrusions, "NEGATIVE_SPACE_INTRUSION", "COMPOSITION_OBJECT")
    check("hero_and_no_occlusion_protection", not hero_intrusions, "UNMOTIVATED_HERO_OCCLUSION", "COMPOSITION_OCCLUSION")
    check("text_safety", not text_intrusions, "COMPOSITION_TEXT_SAFETY_VIOLATION", "COMPOSITION_TEXT_SAFETY")
    check("long_line_guardrail", not long_line_failures, "UNMOTIVATED_CROSS_SCENE_OCCLUSION", "COMPOSITION_OCCLUSION")
    check("large_shape_guardrail", not large_shape_failures, "UNMOTIVATED_LARGE_HIGH_CONTRAST_SHAPE", "COMPOSITION_HIERARCHY")

    capacities = manifest.get("support_zone_capacity", {})
    for zone_id, policy in capacities.items():
        count = sum(obj.get("major", False) and obj.get("allowed_zone") == zone_id for obj in objects)
        if count > policy.get("recommended_major_objects", 2):
            advisories.append({"code": "SUPPORT_DENSITY_ADVISORY", "zone": zone_id, "count": count})
        if count > policy.get("hard_maximum_major_objects", 3):
            errors.append({"code": "EXCESSIVE_SUPPORT_DENSITY", "repair_layer": "COMPOSITION_DENSITY", "zone": zone_id})
            checks["support_zone_capacity"] = "FAIL"
    checks.setdefault("support_zone_capacity", "PASS")
    check("negative_space_not_occupancy_scored", manifest.get("policies", {}).get("empty_region_is_defect") is False,
          "NEGATIVE_SPACE_POLICY_INVALID", "COMPOSITION_OBJECT")
    check("animation_cannot_rescue_composition", manifest.get("policies", {}).get("animation_may_rescue_composition") is False,
          "ANIMATION_RESCUE_POLICY_INVALID", "COMPOSITION_HIERARCHY")
    return {"checks": checks, "errors": errors, "advisories": advisories,
            "result": "PASS" if not errors else "FAIL"}
