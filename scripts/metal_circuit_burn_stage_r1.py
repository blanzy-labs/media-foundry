#!/usr/bin/env python3
"""MF-014R1 presentation refinement built on the unchanged MF-014 burn stage."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFilter

from metal_circuit_burn_stage import BurnConfig, BurnPath, MetalCircuitBurnStage, _color_layer


@dataclass(frozen=True)
class RefinedBurnConfig(BurnConfig):
    title_heat_start: float = 5.2
    title_heat_rise_duration: float = 3.0
    title_peak_level: float = 1.0
    title_peak_hold_duration: float = 1.0
    title_settle_level: float = 0.5
    title_settle_duration: float = 1.2


class RefinedMetalCircuitBurnStage(MetalCircuitBurnStage):
    """Keep MF-014 material rendering while refining title thermal staging."""

    config: RefinedBurnConfig

    def __init__(self, source: Path, config: RefinedBurnConfig, paths: Sequence[BurnPath]):
        super().__init__(source, config, paths)

    @staticmethod
    def _smoothstep(value: float) -> float:
        value = max(0.0, min(1.0, value))
        return value * value * (3.0 - 2.0 * value)

    def title_heat_level(self, timestamp: float) -> float:
        start = self.config.title_heat_start
        peak_at = start + self.config.title_heat_rise_duration
        peak_end = peak_at + self.config.title_peak_hold_duration
        settle_end = peak_end + self.config.title_settle_duration
        if timestamp <= start:
            return 0.0
        if timestamp < peak_at:
            rise = self._smoothstep((timestamp - start) / self.config.title_heat_rise_duration)
            return self.config.title_peak_level * rise
        if timestamp < peak_end:
            return self.config.title_peak_level
        if timestamp < settle_end:
            transition = self._smoothstep((timestamp - peak_end) / self.config.title_settle_duration)
            return self.config.title_peak_level + (self.config.title_settle_level - self.config.title_peak_level) * transition
        return self.config.title_settle_level

    def _apply_title_pulse(self, frame: Image.Image, timestamp: float) -> Image.Image:
        heat = self.title_heat_level(timestamp)
        if heat <= 0.0:
            return frame
        width, height = self.size
        mask = Image.new("L", self.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0.045 * width, 0.235 * height, 0.605 * width, 0.535 * height),
            radius=34,
            fill=round(112 * heat),
        )
        mask = mask.filter(ImageFilter.GaussianBlur(38))
        # A small thermal flutter avoids a sterile opacity ramp without changing the configured envelope.
        flutter = 0.985 + 0.015 * math.sin(timestamp * 11.3)
        return Image.alpha_composite(frame, _color_layer(self.size, (202, 73, 14), mask, 0.44 * flutter))
