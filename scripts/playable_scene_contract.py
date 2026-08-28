#!/usr/bin/env python3
"""Fail-closed validation for portable playable-scene handoff packages."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath


VALID_INTERACTIONS = {"rotary", "toggle", "lever", "button"}
VALID_STATES = {"DORMANT", "STABLE", "UNSTABLE", "CRITICAL"}
FORBIDDEN_GAME_KEYS = {"score", "difficulty", "level_progression", "win_condition", "fail_condition", "player_controller", "save_game", "achievements"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""): digest.update(block)
    return digest.hexdigest()


def portable(value: str) -> bool:
    path = PurePosixPath(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts and not re.match(r"^[A-Za-z]:", value)


def validate_package(root: Path, manifest: dict) -> dict:
    errors, checks = [], {}
    def check(name: str, passed: bool, code: str, detail=None) -> None:
        checks[name] = {"status": "PASS" if passed else "FAIL", "detail": detail}
        if not passed: errors.append({"code": code, "check": name})

    package = manifest.get("package", {}); interactions = manifest.get("interaction_points", [])
    variables = manifest.get("state_variables", []); signals = manifest.get("signals", [])
    events = manifest.get("audio_events", []); assets = manifest.get("assets", [])
    check("contract_version", manifest.get("contract") == "playable_scene_package_v1", "INVALID_CONTRACT_VERSION")
    check("package_identity", all(package.get(key) for key in ("id", "version", "source_commit", "scene_path", "scene_hash", "base_script", "promo_driver")), "PACKAGE_IDENTITY_INCOMPLETE")
    ids = [item.get("id") for item in interactions]
    check("unique_interaction_ids", bool(ids) and len(ids) == len(set(ids)) and all(ids), "DUPLICATE_INTERACTION_ID", ids)
    interaction_shape = all(item.get("type") in VALID_INTERACTIONS and portable(item.get("node", ""))
                            and item.get("animation_hook") and item.get("audio_hook") and item.get("affects") for item in interactions)
    check("interaction_metadata", interaction_shape, "INVALID_INTERACTION_METADATA")
    declared_nodes = {"Machines/Console/Controls/DialCoolant", "Machines/Console/Controls/DialField",
                      "Machines/Console/Controls/SwitchContainment", "Machines/Console/Controls/LeverEmergency",
                      "Machines/Console/Controls/StartupLever", "PromoCamera"}
    paths = [item.get("node") for item in interactions] + [item.get("node") for item in manifest.get("cameras", [])]
    check("declared_node_paths", all(path in declared_nodes for path in paths), "MISSING_INTERACTION_NODE", paths)
    variable_ids = [item.get("id") for item in variables]; allowed_setters = {
        "reactor_energy": "set_reactor_energy", "temperature": "set_temperature", "containment": "set_containment",
        "field_strength": "set_field_strength", "pressure": "set_pressure", "warning_level": "set_warning_level",
        "startup_progress": "set_startup_progress", "indicator_stage": "set_indicator_stage",
        "linked_ring_activation": "set_linked_ring_activation"}
    variables_ok = len(variable_ids) == len(set(variable_ids)) and all(item.get("setter") == allowed_setters.get(item.get("id"))
        and item.get("signal") in signals and item.get("range") == [0.0, 1.0] for item in variables)
    check("valid_state_variables", variables_ok, "INVALID_STATE_VARIABLE", variable_ids)
    check("visual_state_vocabulary", set(manifest.get("visual_states", [])) == VALID_STATES, "INVALID_VISUAL_STATE")
    valid_signal_names = all(isinstance(name, str) and re.fullmatch(r"[a-z][a-z0-9_]*", name) for name in signals)
    check("semantic_signal_names", len(signals) == len(set(signals)) and valid_signal_names, "INVALID_SIGNAL_NAME", signals)
    event_ids = [item.get("id") for item in events]; asset_ids = {item.get("id") for item in assets}
    hooks = [item.get("audio_hook") for item in interactions]
    check("audio_hooks_resolve", all(hook in event_ids for hook in hooks) and len(event_ids) == len(set(event_ids))
          and all(item.get("source_asset_id") in asset_ids for item in events), "MISSING_AUDIO_HOOK", hooks)
    all_paths = [package.get("scene_path", ""), package.get("base_script", ""), package.get("promo_driver", "")]
    all_paths += [item.get("path", "") for item in assets]
    check("portable_project_paths", manifest.get("portable_paths") is True and all(portable(path) for path in all_paths), "ABSOLUTE_OR_UNSAFE_PATH", all_paths)
    asset_results, assets_ok = {}, True
    for item in assets:
        path = root / item.get("path", ""); actual = sha256(path) if path.is_file() else None
        item_ok = actual == item.get("sha256") and (not path.is_file() or path.stat().st_size == item.get("bytes"))
        assets_ok = assets_ok and item_ok; asset_results[item.get("id")] = {"exists": path.is_file(), "sha256": actual}
    check("asset_integrity", assets_ok, "UNRESOLVED_OR_CHANGED_ASSET", asset_results)
    base_source_path = root / package.get("base_script", ""); base_source = base_source_path.read_text() if base_source_path.is_file() else ""
    api_source = base_source
    if 'extends "res://mf018b_pulp_scene.gd"' in base_source:
        parent_source = root / "godot/mf018b_pulp_scene.gd"
        if parent_source.is_file(): api_source += "\n" + parent_source.read_text()
    driver_name = Path(package.get("promo_driver", "missing")).name
    check("promo_driver_separation", package.get("promo_driver_optional") is True and driver_name not in base_source
          and "PromoDriver" not in base_source, "PROMO_DEPENDENCY_IN_BASE_SCENE")
    deps = manifest.get("dependencies", {})
    check("zero_game_foundry_dependency", deps.get("game_foundry") == [] and not any("game_foundry" in str(item).lower() for item in assets), "GAME_FOUNDRY_DEPENDENCY")
    serialized = json.dumps({key: value for key, value in manifest.items() if key != "ownership"})
    check("ownership_boundary", manifest.get("gameplay_implemented") is False and not any(f'"{key}"' in serialized for key in FORBIDDEN_GAME_KEYS), "GAMEPLAY_SCOPE_LEAK")
    declared_setters = {item.get("setter") for item in variables}
    check("base_scene_api_declared", all(setter in api_source for setter in declared_setters)
          and "activate_control" in api_source and "state_snapshot" in api_source, "BASE_SCENE_API_MISSING")
    return {"result": "PASS" if not errors else "FAIL", "checks": checks, "errors": errors}
