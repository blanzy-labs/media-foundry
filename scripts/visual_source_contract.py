#!/usr/bin/env python3
"""Visual-source strategy assessment, asset resolution, and integrity rules."""

from __future__ import annotations

import hashlib
from pathlib import Path


STRATEGIES = {"PROCEDURAL", "PLATE", "HYBRID", "AUTHENTIC_MEDIA"}
RATINGS = {"LOW", "MEDIUM", "HIGH"}
QUALITY_INTENTS = {"FAST", "STANDARD", "CINEMATIC"}
PLATE_APPROVAL_STATES = {"UNREVIEWED", "APPROVED", "REJECTED", "REVIEW_REQUIRED"}
PROVENANCE = {"user_supplied", "generated", "derived", "authentic_capture", "internal_procedural_render"}
ASSESSMENT_FIELDS = {
    "surface_complexity", "illustration_complexity", "character_complexity", "geometric_precision",
    "motion_requirement", "lighting_requirement", "depth_requirement", "authenticity_requirement",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recommend_strategy(requirements: dict) -> tuple[str, list[str]]:
    """Bounded guidance; no fictitious precision score."""
    if requirements.get("authenticity_requirement") == "HIGH":
        return "AUTHENTIC_MEDIA", ["source authenticity is a primary requirement"]
    illustration_high = requirements.get("illustration_complexity") == "HIGH" or requirements.get("surface_complexity") == "HIGH"
    motion_active = requirements.get("motion_requirement") in {"MEDIUM", "HIGH"} or requirements.get("lighting_requirement") in {"MEDIUM", "HIGH"}
    if illustration_high and motion_active:
        return "HYBRID", ["high illustration or surface richness is required", "meaningful local motion or lighting remains required"]
    if illustration_high:
        return "PLATE", ["illustration richness dominates", "motion requirement is low"]
    if requirements.get("geometric_precision") == "HIGH" and motion_active:
        return "PROCEDURAL", ["geometric precision is high", "animation-first construction is appropriate"]
    if requirements.get("illustration_complexity") == "LOW":
        return "PROCEDURAL", ["illustration complexity is low", "procedural construction is proportionate"]
    return "HYBRID", ["mixed material and motion needs favor a layered source"]


def validate_visual_source(root: Path, definition: dict) -> dict:
    errors, warnings, checks = [], [], {}

    def check(name: str, passed: bool, code: str, state: str = "BLOCKED_VISUAL_SOURCE") -> None:
        checks[name] = "PASS" if passed else "FAIL"
        if not passed:
            errors.append({"code": code, "state": state})

    complex_scene = definition.get("complex_scene") is True
    source = definition.get("visual_source", {})
    configured = source.get("configured_strategy")
    resolved = source.get("resolved_strategy", configured)
    check("source_strategy_required", not complex_scene or configured in STRATEGIES, "MISSING_SOURCE_STRATEGY")
    check("known_source_strategy", configured in STRATEGIES if configured is not None else not complex_scene, "UNKNOWN_SOURCE_STRATEGY")
    check("quality_intent", source.get("quality_intent") in QUALITY_INTENTS, "INVALID_QUALITY_INTENT")
    requirements = source.get("requirements", {})
    bounded = set(requirements) == ASSESSMENT_FIELDS and all(value in RATINGS for value in requirements.values())
    check("bounded_assessment", bounded, "INVALID_SOURCE_ASSESSMENT")
    recommended, reasons = recommend_strategy(requirements) if bounded else (None, [])
    override = source.get("human_override")
    override_ok = override is None or (override.get("strategy") in STRATEGIES and bool(override.get("reason")))
    check("human_override", override_ok, "INVALID_HUMAN_OVERRIDE")
    expected = override.get("strategy") if isinstance(override, dict) else recommended
    if configured in STRATEGIES and expected and configured != expected:
        warnings.append({"code": "VISUAL_SOURCE_STRATEGY_WARNING", "recommended": expected, "configured": configured})
    fallback = source.get("fallback", {})
    fallback_ok = isinstance(fallback.get("allowed"), bool) and isinstance(fallback.get("strategies"), list) \
        and set(fallback.get("strategies", [])) <= STRATEGIES
    check("fallback_policy", fallback_ok, "INVALID_FALLBACK_POLICY")
    if resolved != configured:
        permitted = fallback.get("allowed") is True and resolved in fallback.get("strategies", [])
        check("no_silent_fallback", permitted, "SILENT_STRATEGY_FALLBACK_PROHIBITED")
    else:
        checks["no_silent_fallback"] = "PASS"

    plate = source.get("plate")
    plate_required = configured in {"PLATE", "HYBRID"}
    asset_detail = None
    if plate_required:
        plate_fields = {"id", "source_path", "source_type", "dimensions", "aspect_ratio", "provenance", "source_sha256",
                        "crop_policy", "safe_zones", "animated_regions", "protected_regions", "layer_plan", "approval"}
        check("plate_contract", isinstance(plate, dict) and plate_fields <= set(plate), "INVALID_PLATE_CONTRACT")
        if isinstance(plate, dict):
            path = root / plate.get("source_path", "")
            exists = path.is_file()
            check("required_plate_exists", exists, "MISSING_APPROVED_PLATE")
            approval = plate.get("approval", {})
            declared_status = approval.get("status")
            check("plate_approval_vocabulary", declared_status in PLATE_APPROVAL_STATES, "INVALID_PLATE_APPROVAL")
            check("plate_provenance", plate.get("provenance") in PROVENANCE, "INVALID_PLATE_PROVENANCE")
            actual_hash = sha256(path) if exists else None
            hash_matches = exists and actual_hash == plate.get("source_sha256")
            check("plate_hash_integrity", hash_matches, "PLATE_HASH_CHANGED", "REVIEW_REQUIRED")
            effective_status = "REVIEW_REQUIRED" if exists and not hash_matches else declared_status
            production = source.get("mode") == "production"
            if production:
                check("production_plate_approved", effective_status == "APPROVED", "UNREVIEWED_PLATE_FOR_PRODUCTION", "BLOCKED_APPROVAL")
            else:
                checks["production_plate_approved"] = "NOT_REQUIRED"
                if effective_status != "APPROVED":
                    warnings.append({"code": "PRODUCTION_PLATE_PENDING", "approval": effective_status})
            plan_ok = bool(plate.get("animated_regions")) and bool(plate.get("layer_plan")) \
                and all(region.get("id") and region.get("owner") in {"plate", "compositor", "godot"} for region in plate.get("animated_regions", []))
            check("plate_layer_and_region_plan", plan_ok, "INVALID_PLATE_LAYER_PLAN")
            asset_detail = {"path": str(path), "exists": exists, "declared_sha256": plate.get("source_sha256"),
                            "actual_sha256": actual_hash, "declared_approval": declared_status, "effective_approval": effective_status}
    else:
        checks.update({"plate_contract": "NOT_REQUIRED", "required_plate_exists": "NOT_REQUIRED",
                       "plate_approval_vocabulary": "NOT_REQUIRED", "plate_provenance": "NOT_REQUIRED",
                       "plate_hash_integrity": "NOT_REQUIRED", "production_plate_approved": "NOT_REQUIRED",
                       "plate_layer_and_region_plan": "NOT_REQUIRED"})

    authentic = source.get("authentic_media")
    if configured == "AUTHENTIC_MEDIA":
        path = root / authentic.get("source_path", "") if isinstance(authentic, dict) else root / "__missing__"
        exists = isinstance(authentic, dict) and path.is_file()
        check("authentic_media_exists", exists, "MISSING_AUTHENTIC_MEDIA")
    else:
        checks["authentic_media_exists"] = "NOT_REQUIRED"
    composition = source.get("composition_gate", {})
    composition_path = root / composition.get("manifest_path", "")
    composition_bound = composition.get("required") is True and composition_path.is_file() and bool(composition.get("manifest_sha256")) \
        and sha256(composition_path) == composition.get("manifest_sha256")
    check("composition_gate_bound", not complex_scene or composition_bound, "MF016_COMPOSITION_GATE_MISSING")
    status = "PASS" if not errors else errors[0]["state"]
    return {"result": "PASS" if not errors else "FAIL", "state": status, "configured_strategy": configured,
            "resolved_strategy": resolved, "recommended_strategy": recommended, "recommendation_reasons": reasons,
            "checks": checks, "warnings": warnings, "errors": errors, "asset": asset_detail,
            "release_ready": not errors and not any(warning["code"] == "PRODUCTION_PLATE_PENDING" for warning in warnings)}
