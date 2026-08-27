#!/usr/bin/env python3
"""Build the MF-016 static composition approval package; never renders a trailer."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from composition_contract import authorize_animation, validate_manifest
from pulp_trailer_stage_r2 import CharacterlessPulpTrailerStage


PALETTE = {
    "black": (8, 12, 11), "paper": (224, 201, 139), "cream": (244, 218, 151),
    "yellow": (230, 185, 5), "teal": (24, 87, 85), "deep_teal": (10, 45, 45),
    "red": (177, 35, 18), "amber": (239, 128, 12),
}

STATE_INTENSITY = {"dormant": .08, "wake": .34, "escalation": .68, "peak": 1.0}
FONT_PATH = "/usr/share/fonts/opentype/urw-base35/NimbusSansNarrow-Bold.otf"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


class StaticCompositionRenderer:
    def __init__(self, manifest: dict):
        self.manifest = manifest
        self.size = (manifest["canvas"]["width"], manifest["canvas"]["height"])
        self.seed = manifest["seed"]
        self.font = ImageFont.truetype(FONT_PATH, 28)

    def _printed_material(self, image: Image.Image, state_index: int) -> Image.Image:
        rng = np.random.default_rng(self.seed + state_index * 101)
        values = np.asarray(image).astype(np.float32)
        grain = rng.normal(0, 5.2, values.shape[:2])[:, :, None]
        values = np.clip(values + grain, 0, 255).astype(np.uint8)
        result = Image.fromarray(values, "RGB").convert("RGBA")
        marks = Image.new("RGBA", self.size, (0, 0, 0, 0)); draw = ImageDraw.Draw(marks)
        for _ in range(72):
            x = int(rng.integers(8, self.size[0] - 8)); y = int(rng.integers(8, self.size[1] - 8))
            if rng.random() < .82:
                draw.ellipse((x, y, x + int(rng.integers(1, 4)), y + int(rng.integers(1, 4))),
                             fill=PALETTE["paper"] + (int(rng.integers(7, 26)),))
            else:
                draw.line((x, y, x + int(rng.integers(-8, 9)), y + int(rng.integers(12, 48))),
                          fill=(3, 6, 5, int(rng.integers(11, 31))), width=1)
        result = Image.alpha_composite(result, marks)
        vignette = Image.new("L", self.size, 0); vd = ImageDraw.Draw(vignette)
        vd.rectangle((18, 18, self.size[0] - 19, self.size[1] - 19), outline=115, width=24)
        edge = Image.new("RGBA", self.size, PALETTE["black"] + (0,)); edge.putalpha(vignette.filter(ImageFilter.GaussianBlur(8)))
        return Image.alpha_composite(result, edge).convert("RGB")

    def render(self, state: str) -> Image.Image:
        intensity = STATE_INTENSITY[state]
        w, h = self.size
        canvas = Image.new("RGBA", self.size, PALETTE["deep_teal"] + (255,)); draw = ImageDraw.Draw(canvas)
        # Quiet room shell: vertical architecture only; no cross-scene rails or diagonal pipes.
        draw.rectangle((0, 0, w, h), fill=(7, 27, 26, 255))
        draw.rectangle((18, 72, 257, 954), fill=(8, 25, 23, 255), outline=(28, 75, 69, 255), width=5)
        for x, width in ((16, 17), (268, 12), (705, 18), (744, 12)):
            draw.rectangle((x, 80, x + width, 1034), fill=(4, 15, 14, 255), outline=(35, 83, 75, 190), width=2)
        # Deliberate negative space remains in the upper left.
        draw.rectangle((42, 130, 255, 430), fill=(5, 19, 18, 255))
        draw.arc((66, 162, 218, 358), 215, 325, fill=(25, 60, 55, 115), width=3)
        # A narrow rear tower establishes depth without entering the protected hero zone.
        draw.rounded_rectangle((267, 230, 321, 936), radius=17, fill=(4, 20, 19, 255), outline=(33, 77, 67, 180), width=3)
        for y in range(282, 900, 92):
            draw.line((274, y, 313, y), fill=(88, 78, 37, 105), width=2)
        # One intentionally placed control bank, with breathing room around the hero.
        draw.rounded_rectangle((42, 553, 246, 944), radius=10, fill=(12, 26, 23, 255), outline=(137, 116, 54, 235), width=5)
        draw.rectangle((57, 574, 230, 904), fill=(15, 34, 29, 255), outline=(35, 89, 77, 215), width=3)
        for index, level in enumerate((intensity * .73, min(1, intensity * 1.06), intensity ** .8)):
            cx, cy = 88 + index * 57, 648 + (index % 2) * 20
            draw.ellipse((cx - 23, cy - 23, cx + 23, cy + 23), fill=(194, 177, 122, 255), outline=(5, 11, 10, 255), width=4)
            angle = math.radians(215 + level * 220)
            draw.line((cx, cy, cx + math.cos(angle) * 17, cy + math.sin(angle) * 17), fill=(112, 14, 8, 255), width=3)
        for index in range(6):
            x, y = 76 + index % 3 * 58, 795 + index // 3 * 62
            active = intensity >= (.16 + index * .13)
            color = PALETTE["red"] if index % 3 != 2 else PALETTE["amber"]
            draw.ellipse((x - 9, y - 9, x + 9, y + 9), fill=color + (255,) if active else (35, 20, 12, 255), outline=PALETTE["paper"] + (130,), width=2)
        # Reactor is an unobstructed, high-contrast center-right hero.
        draw.rounded_rectangle((354, 260, 680, 1010), radius=38, fill=(6, 18, 16, 255), outline=(150, 126, 42, 255), width=8)
        draw.ellipse((340, 190, 696, 374), fill=(13, 31, 26, 255), outline=PALETTE["yellow"] + (245,), width=11)
        draw.ellipse((378, 230, 659, 338), fill=(18, 50, 41, 255), outline=PALETTE["paper"] + (205,), width=5)
        for index in range(14):
            angle = math.tau * index / 14
            x, y = 518 + math.cos(angle) * 158, 282 + math.sin(angle) * 66
            active = intensity > .28 + index * .035
            draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(212, 44, 15, 255) if active else (43, 20, 12, 255))
        draw.rounded_rectangle((405, 320, 632, 842), radius=49, fill=(17, 53, 44, 255), outline=(218, 194, 111, 255), width=6)
        glow = Image.new("RGBA", self.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
        gd.ellipse((330 - 28 * intensity, 190 - 20 * intensity, 706 + 28 * intensity, 932 + 25 * intensity),
                   fill=PALETTE["yellow"] + (round(10 + 58 * intensity),))
        gd.rounded_rectangle((417, 330, 620, 830), radius=43, fill=PALETTE["yellow"] + (round(20 + 93 * intensity),))
        canvas = Image.alpha_composite(canvas, glow.filter(ImageFilter.GaussianBlur(28 + 14 * intensity)))
        draw = ImageDraw.Draw(canvas)
        rng = np.random.default_rng(self.seed + list(STATE_INTENSITY).index(state) * 503)
        for filament in range(8):
            points = []
            for step in range(19):
                y = 350 + step * 24
                x = 518 + math.sin(filament * .78 + step * .66) * (11 + 47 * intensity) + rng.uniform(-4, 4) * intensity
                points.append((x, y))
            draw.line(points, fill=(PALETTE["cream"] if filament % 3 else PALETTE["yellow"]) + (round(70 + 170 * intensity),), width=2 + filament % 2)
        draw.rectangle((463, 750, 575, 1016), fill=(8, 17, 15, 255), outline=PALETTE["paper"] + (190,), width=5)
        for y in range(780, 990, 43):
            draw.line((468, y, 570, y), fill=(148, 110, 28, 255), width=3)
        # A shallow floor plinth frames the bottom without crossing the hero silhouette.
        draw.rectangle((0, 1048, w, h), fill=(4, 12, 11, 255))
        draw.line((0, 1051, w, 1051), fill=(77, 88, 54, 150), width=4)
        # Static state label is evidence-only and stays in the dedicated top safe zone.
        label = state.upper()
        draw.text((w // 2, 54), label, font=self.font, anchor="mm", fill=PALETTE["paper"] + (155,))
        exposure = .83 + intensity * .17
        return self._printed_material(ImageEnhance.Brightness(canvas.convert("RGB")).enhance(exposure), list(STATE_INTENSITY).index(state))


def contact_sheet(paths: list[Path], output: Path) -> None:
    thumbs = []
    for path in paths:
        image = Image.open(path).convert("RGB"); image.thumbnail((360, 540), Image.Resampling.LANCZOS)
        thumbs.append(image.copy())
    sheet = Image.new("RGB", (768, 1152), (12, 16, 14)); draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(FONT_PATH, 24)
    for index, (name, image) in enumerate(zip(STATE_INTENSITY, thumbs)):
        x = 20 + index % 2 * 374; y = 30 + index // 2 * 558
        sheet.paste(image, (x, y + 34)); draw.text((x, y), name.upper(), font=font, fill=PALETTE["cream"])
    sheet.save(output, optimize=True)


def comparison(before: Image.Image, after: Image.Image, output: Path) -> None:
    before = before.convert("RGB"); after = after.convert("RGB")
    before.thumbnail((360, 540), Image.Resampling.LANCZOS); after.thumbnail((360, 540), Image.Resampling.LANCZOS)
    result = Image.new("RGB", (768, 620), (10, 14, 12)); draw = ImageDraw.Draw(result)
    font = ImageFont.truetype(FONT_PATH, 24)
    result.paste(before, (20, 58)); result.paste(after, (388, 58))
    draw.text((20, 18), "MF-015R2 PROBLEM", font=font, fill=PALETTE["paper"])
    draw.text((388, 18), "MF-016 STATIC", font=font, fill=PALETTE["yellow"])
    result.save(output, optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--config", default="config/mf016-pulp-composition.json")
    parser.add_argument("--artifacts", default="artifacts/mf-016")
    args = parser.parse_args()
    root = Path(args.project_root).resolve(); config_path = root / args.config; artifacts = root / args.artifacts
    if artifacts.exists():
        raise SystemExit(f"refusing to overwrite: {artifacts}")
    manifest = json.loads(config_path.read_text())
    prior = root / manifest["source_regression"]["path"]
    if not prior.is_file() or sha256(prior) != manifest["source_regression"]["sha256"]:
        raise SystemExit("frozen MF-015R2 regression artifact missing or changed")
    machine = validate_manifest(manifest)
    if machine["result"] != "PASS":
        raise SystemExit("composition manifest failed machine validation")
    for directory in (artifacts / "pulp-keyframes", artifacts / "before-after", artifacts / "validation"):
        directory.mkdir(parents=True, exist_ok=True)
    renderer = StaticCompositionRenderer(manifest); paths = []
    for state in manifest["composition"]["static_states"]:
        path = artifacts / "pulp-keyframes" / f"{state}.png"
        renderer.render(state).save(path, optimize=True); paths.append(path)
    contact_sheet(paths, artifacts / "composition-contact-sheet.png")
    r2_definition = json.loads((root / "config/mf015r2-characterless-atmosphere.json").read_text())
    prior_stage = CharacterlessPulpTrailerStage(r2_definition)
    before = prior_stage.render_frame(round(manifest["source_regression"]["sample_seconds"] * prior_stage.fps))
    before.save(artifacts / "before-after/mf015r2-problem-frame.png", optimize=True)
    comparison(before, Image.open(paths[2]), artifacts / "before-after/problem-vs-corrected.png")
    gate = authorize_animation(manifest)
    write_json(artifacts / "validation/machine-validation.json", machine)
    write_json(artifacts / "validation/gate-decision.json", gate)
    package = {
        "slice": "MF-016", "config": str(config_path), "config_sha256": sha256(config_path),
        "seed": manifest["seed"], "source_regression": manifest["source_regression"],
        "static_keyframes": [{"state": state, "path": str(path), "sha256": sha256(path)}
                             for state, path in zip(manifest["composition"]["static_states"], paths)],
        "contact_sheet": str(artifacts / "composition-contact-sheet.png"),
        "before_after": str(artifacts / "before-after/problem-vs-corrected.png"),
        "machine_validation": machine["result"], "gate_decision": gate,
        "full_video_rendered": False, "published": False,
    }
    write_json(artifacts / "composition-approval-package.json", package)
    print(json.dumps(package, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
