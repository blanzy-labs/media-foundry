#!/usr/bin/env python3
"""Fail-closed backend selection and capability checks for Media Foundry."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

VALID_BACKENDS = {"GODOT", "BLENDER", "COMPARE"}


class BackendContractError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def portable(path: str) -> bool:
    candidate = PurePosixPath(path)
    return bool(path) and not candidate.is_absolute() and ".." not in candidate.parts


def load_contract(path: Path) -> dict:
    data = json.loads(path.read_text())
    if data.get("contract") != "media_foundry_render_backend_v1":
        raise BackendContractError("INVALID_BACKEND_CONTRACT")
    if data.get("default_backend") != "GODOT":
        raise BackendContractError("GODOT_DEFAULT_REQUIRED")
    if set(data.get("backends", {})) != VALID_BACKENDS:
        raise BackendContractError("BACKEND_VOCABULARY_INVALID")
    return data


def select_backend(job: dict, contract: dict) -> str:
    render = job.get("render", {})
    backend = render.get("backend", contract["default_backend"])
    if backend not in VALID_BACKENDS:
        raise BackendContractError("UNKNOWN_RENDER_BACKEND", str(backend))
    if not contract["backends"][backend].get("enabled"):
        raise BackendContractError("BACKEND_DISABLED", backend)
    requested = set(render.get("required_capabilities", []))
    available = set(contract["backends"][backend].get("capabilities", []))
    missing = sorted(requested - available)
    if missing:
        raise BackendContractError("BACKEND_CAPABILITY_UNSUPPORTED", ",".join(missing))
    return backend


def validate_portable_paths(job: dict) -> None:
    blender = job.get("render", {}).get("blender", {})
    for key in ("template", "builder_script"):
        value = blender.get(key)
        if value is not None and not portable(value):
            raise BackendContractError("ABSOLUTE_BACKEND_ASSET_PATH", f"{key}={value}")


def resolve_blender_failure(job: dict, blender_available: bool) -> str:
    backend = job.get("render", {}).get("backend", "GODOT")
    if backend not in {"BLENDER", "COMPARE"} or blender_available:
        return backend
    fallback = job.get("render", {}).get("fallback", {})
    allowed = fallback.get("allowed") is True and "GODOT" in fallback.get("backends", [])
    if allowed:
        return "GODOT"
    raise BackendContractError("BLENDER_NOT_AVAILABLE")
