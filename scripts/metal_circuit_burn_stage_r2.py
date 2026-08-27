#!/usr/bin/env python3
"""Etched supporting-text refinement layered over the frozen MF-014R1 stage."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from metal_circuit_burn_stage import BurnPath, _color_layer
from metal_circuit_burn_stage_r1 import RefinedBurnConfig, RefinedMetalCircuitBurnStage


class EtchedSupportingTextStage(RefinedMetalCircuitBurnStage):
    """Add material-integrated secondary inscriptions after the R1 hero event."""

    def __init__(self, source: Path, config: RefinedBurnConfig, paths: list[BurnPath], supporting: dict, fonts: dict):
        super().__init__(source, config, paths)
        self.supporting = supporting
        self.fonts = {
            "tagline": ImageFont.truetype(fonts["tagline"], supporting["tagline"]["font_size"]),
            "website": ImageFont.truetype(fonts["website"], supporting["website"]["font_size"]),
        }

    def _text_mask(self, key: str) -> Image.Image:
        spec = self.supporting[key]
        width, height = self.size
        mask = Image.new("L", self.size, 0)
        ImageDraw.Draw(mask).text(
            (spec["position"][0] * width, spec["position"][1] * height),
            spec["text"], font=self.fonts[key], fill=255, anchor="mm", stroke_width=0,
        )
        return mask

    def _reveal_mask(self, mask: Image.Image, progress: float) -> Image.Image:
        if progress >= 1.0:
            return mask
        values = np.asarray(mask, dtype=np.float32)
        columns = np.where(values.max(axis=0) > 0)[0]
        if not len(columns):
            return mask
        left, right = int(columns[0]), int(columns[-1])
        feather = max(16, round((right - left) * 0.09))
        front = left - feather + progress * ((right - left) + 2 * feather)
        x = np.arange(values.shape[1], dtype=np.float32)
        reveal = np.clip((front - x) / feather + 1.0, 0.0, 1.0)
        return Image.fromarray(np.clip(values * reveal[None, :], 0, 255).astype(np.uint8), "L")

    def _apply_etched_text(self, frame: Image.Image, key: str, timestamp: float) -> Image.Image:
        spec = self.supporting[key]
        progress = (timestamp - spec["reveal_start"]) / spec["reveal_duration"]
        if progress <= 0.0:
            return frame
        progress = max(0.0, min(1.0, progress))
        mask = self._reveal_mask(self._text_mask(key), progress)
        intensity = spec["etched_intensity"]
        brightness = spec["supporting_brightness"]
        # A glyph-local undercut increases contrast without introducing a plaque or panel.
        undercut = mask.filter(ImageFilter.GaussianBlur(2.2))
        frame = Image.alpha_composite(frame, _color_layer(self.size, (7, 5, 4), undercut, 0.24 * intensity))
        shadow = ImageChops.offset(mask, 1, 2)
        frame = Image.alpha_composite(frame, _color_layer(self.size, (4, 3, 2), self._material_mask(shadow), 0.90 * intensity))
        groove_color = (72, 46, 29) if key == "tagline" else (78, 71, 60)
        frame = Image.alpha_composite(frame, _color_layer(self.size, groove_color, self._material_mask(mask), 0.78 * intensity))
        rim = ImageChops.offset(mask, -1, -1)
        rim_color = (188, 111, 55) if key == "tagline" else (172, 151, 117)
        frame = Image.alpha_composite(frame, _color_layer(self.size, rim_color, self._material_mask(rim), brightness))
        if progress < 1.0:
            values = np.asarray(mask, dtype=np.uint8)
            columns = np.where(values.max(axis=0) > 0)[0]
            if len(columns):
                front_x = int(columns[0] + progress * (columns[-1] - columns[0]))
                sheen = Image.new("L", self.size, 0)
                ImageDraw.Draw(sheen).rectangle((front_x - 3, 0, front_x + 3, self.size[1]), fill=110)
                sheen = ImageChops.multiply(sheen.filter(ImageFilter.GaussianBlur(3.0)), mask)
                frame = Image.alpha_composite(frame, _color_layer(self.size, (216, 149, 79), sheen, 0.36 * brightness))
        return frame

    def render_frame(self, frame_index: int) -> Image.Image:
        timestamp = frame_index / self.config.fps
        frame = super().render_frame(frame_index).convert("RGBA")
        frame = self._apply_etched_text(frame, "tagline", timestamp)
        frame = self._apply_etched_text(frame, "website", timestamp)
        return frame.convert("RGB")
