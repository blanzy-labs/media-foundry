#!/usr/bin/env python3
"""Cold recessed steel inscription with a material-driven thermal reveal."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from metal_circuit_burn_stage import BurnPath, _color_layer, _scaled_points
from metal_circuit_burn_stage_r1 import RefinedBurnConfig, RefinedMetalCircuitBurnStage


class ThermalRecessedTaglineStage(RefinedMetalCircuitBurnStage):
    """Keep the R1 bumper intact and reveal a pre-existing stamped inscription with heat."""

    def __init__(self, source: Path, config: RefinedBurnConfig, paths: list[BurnPath], tagline: dict, thermal_route: dict):
        super().__init__(source, config, paths)
        self.tagline = tagline
        self.thermal_route = thermal_route
        self.route_points = _scaled_points(BurnPath(tuple(tuple(point) for point in thermal_route["points"]), 0.0, 1.0), self.size)
        self.font = ImageFont.truetype(tagline["font"], tagline["font_size"])
        self.raw_tagline_mask, self.tagline_mask = self._build_tagline_masks()
        dilated = self.tagline_mask.filter(ImageFilter.MaxFilter(5))
        eroded = self.tagline_mask.filter(ImageFilter.MinFilter(3))
        self.tagline_edge = ImageChops.subtract(dilated, eroded)

    def _build_tagline_masks(self) -> tuple[Image.Image, Image.Image]:
        width, height = self.size
        raw = Image.new("L", self.size, 0)
        display_text = "\n".join(self.tagline.get("layout_lines", [self.tagline["text"]]))
        ImageDraw.Draw(raw).multiline_text((self.tagline["position"][0] * width, self.tagline["position"][1] * height),
                                           display_text, font=self.font, fill=255, anchor="mm", align="center", spacing=-2)
        values = np.asarray(raw, dtype=np.float32)
        yy, xx = np.indices(values.shape)
        wear = 0.68 + 0.20 * self.texture + 0.12 * np.sin(xx * 0.41 + yy * 0.17) * np.sin(xx * 0.09 - yy * 0.29)
        distressed = Image.fromarray(np.clip(values * wear, 0, 255).astype(np.uint8), "L")
        return raw, distressed

    @staticmethod
    def _ease(value: float) -> float:
        value = max(0.0, min(1.0, value))
        return value * value * (3.0 - 2.0 * value)

    def _route_progress(self, timestamp: float) -> float:
        return max(0.0, min(1.0, (timestamp - self.thermal_route["start"]) / self.thermal_route["duration"]))

    def _spatial_mask(self, progress: float, feather_fraction: float = 0.08) -> Image.Image:
        values = np.asarray(self.tagline_mask, dtype=np.float32)
        columns = np.where(values.max(axis=0) > 0)[0]
        if not len(columns):
            return self.tagline_mask
        left, right = float(columns[0]), float(columns[-1])
        span = right - left
        front = right - progress * span
        feather = max(12.0, span * feather_fraction)
        x = np.arange(values.shape[1], dtype=np.float32)
        activated = np.clip((x - front) / feather + 1.0, 0.0, 1.0)
        return Image.fromarray(np.clip(values * activated[None, :], 0, 255).astype(np.uint8), "L")

    def _front_mask(self, progress: float) -> Image.Image:
        values = np.asarray(self.tagline_edge, dtype=np.float32)
        columns = np.where(values.max(axis=0) > 0)[0]
        if not len(columns):
            return self.tagline_edge
        front = columns[-1] - progress * (columns[-1] - columns[0])
        x = np.arange(values.shape[1], dtype=np.float32)
        band = np.exp(-0.5 * ((x - front) / 7.0) ** 2)
        return Image.fromarray(np.clip(values * band[None, :], 0, 255).astype(np.uint8), "L")

    def _apply_cold_recess(self, frame: Image.Image) -> Image.Image:
        intensity = self.tagline["recessed_intensity"]
        visibility = self.tagline["cold_visibility"]
        # Preserve local plate texture inside the stamp, shifted slightly as if the steel were pressed inward.
        displaced = ImageChops.offset(frame, 1, 2)
        displaced.putalpha(self._material_mask(self.tagline_mask, 0.34 * intensity))
        frame = Image.alpha_composite(frame, displaced)
        upper_edge = ImageChops.subtract(self.tagline_edge, ImageChops.offset(self.tagline_edge, -1, -1))
        lower_edge = ImageChops.subtract(self.tagline_edge, ImageChops.offset(self.tagline_edge, 1, 1))
        frame = Image.alpha_composite(frame, _color_layer(self.size, (3, 3, 3), self._material_mask(upper_edge), 0.72 * intensity))
        frame = Image.alpha_composite(frame, _color_layer(self.size, (116, 107, 92), self._material_mask(lower_edge), visibility * intensity))
        frame = Image.alpha_composite(frame, _color_layer(self.size, (18, 16, 14), self._material_mask(self.tagline_mask), 0.10 * intensity))
        return frame

    def _apply_thermal_state(self, frame: Image.Image, timestamp: float) -> Image.Image:
        start = self.tagline["heat_reveal_start"]
        duration = self.tagline["heat_propagation_duration"]
        settle_duration = self.tagline["heat_settle_duration"]
        if timestamp < start:
            return frame
        progress = max(0.0, min(1.0, (timestamp - start) / duration))
        activated = self._spatial_mask(progress)
        if timestamp < start + duration:
            heat_level = self.tagline["active_heat_level"]
        else:
            settle = self._ease((timestamp - start - duration) / settle_duration)
            heat_level = self.tagline["active_heat_level"] + (
                self.tagline["final_settle_brightness"] - self.tagline["active_heat_level"]
            ) * settle
        # Activated steel chars permanently; heat lives primarily on the irregular recessed edges.
        frame = Image.alpha_composite(frame, _color_layer(self.size, (12, 6, 3), self._material_mask(activated), 0.42))
        activated_edge = ImageChops.multiply(self.tagline_edge, activated)
        frame = Image.alpha_composite(frame, _color_layer(self.size, (126, 61, 26), self._material_mask(activated_edge), 0.42))
        edge_glow = activated_edge.filter(ImageFilter.GaussianBlur(2.4))
        frame = Image.alpha_composite(frame, _color_layer(self.size, (196, 61, 9), edge_glow, 0.34 * heat_level))
        frame = Image.alpha_composite(frame, _color_layer(self.size, (193, 91, 31), self._material_mask(activated_edge), 0.70 * heat_level))
        if progress < 1.0:
            front = self._front_mask(progress)
            frame = Image.alpha_composite(frame, _color_layer(self.size, (255, 173, 74), front.filter(ImageFilter.GaussianBlur(1.2)), 0.72))
        return frame

    def render_frame(self, frame_index: int) -> Image.Image:
        timestamp = frame_index / self.config.fps
        frame = super().render_frame(frame_index).convert("RGBA")
        frame = self._apply_cold_recess(frame)
        route_progress = self._route_progress(timestamp)
        if 0.0 < route_progress < 1.0:
            frame = self._apply_active_front(frame, self.route_points, route_progress, frame_index)
        frame = self._apply_thermal_state(frame, timestamp)
        return frame.convert("RGB")
