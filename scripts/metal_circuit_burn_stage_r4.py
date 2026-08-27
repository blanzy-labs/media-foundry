#!/usr/bin/env python3
"""Engraved incandescent information with controlled groove-rooted fire."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from metal_circuit_burn_stage import BurnPath, _color_layer, _scaled_points
from metal_circuit_burn_stage_r1 import RefinedBurnConfig, RefinedMetalCircuitBurnStage


class IncandescentInformationStage(RefinedMetalCircuitBurnStage):
    """Keep R1 intact while thermally activating two engraved information fields."""

    def __init__(self, source: Path, config: RefinedBurnConfig, paths: list[BurnPath], elements: dict, font_path: str,
                 thermal_route: dict, seed: int):
        super().__init__(source, config, paths)
        self.elements = elements
        self.font_path = font_path
        self.thermal_route = thermal_route
        self.seed = seed
        self.route_points = _scaled_points(BurnPath(tuple(tuple(point) for point in thermal_route["points"]), 0.0, 1.0), self.size)
        self.masks = {key: self._build_masks(spec) for key, spec in elements.items()}

    def _build_masks(self, spec: dict) -> dict:
        width, height = self.size
        font = ImageFont.truetype(self.font_path, spec["font_size"])
        raw = Image.new("L", self.size, 0)
        display = "\n".join(spec["layout_lines"])
        ImageDraw.Draw(raw).multiline_text((spec["position"][0] * width, spec["position"][1] * height), display,
                                           font=font, fill=255, anchor="mm", align="center",
                                           spacing=spec.get("line_spacing", -2))
        values = np.asarray(raw, dtype=np.float32)
        yy, xx = np.indices(values.shape)
        wear = 0.72 + 0.18 * self.texture + 0.10 * np.sin(xx * 0.37 + yy * 0.23) * np.sin(xx * 0.11 - yy * 0.31)
        distressed = Image.fromarray(np.clip(values * wear, 0, 255).astype(np.uint8), "L")
        edge = ImageChops.subtract(distressed.filter(ImageFilter.MaxFilter(5)), distressed.filter(ImageFilter.MinFilter(3)))
        columns = np.where(np.asarray(raw).max(axis=0) > 0)[0]
        rows = np.where(np.asarray(raw).max(axis=1) > 0)[0]
        return {"raw": raw, "body": distressed, "edge": edge,
                "bounds": (int(columns[0]), int(rows[0]), int(columns[-1]), int(rows[-1]))}

    @staticmethod
    def _ease(value: float) -> float:
        value = max(0.0, min(1.0, value))
        return value * value * (3.0 - 2.0 * value)

    def _thermal_state(self, timestamp: float, spec: dict) -> tuple[float, float, float]:
        start = spec["heat_start"]
        travel_end = start + spec["heat_travel_duration"]
        peak_end = travel_end + spec["peak_hold_duration"]
        settle_end = peak_end + spec["settle_duration"]
        if timestamp < start:
            return 0.0, 0.0, 0.0
        if timestamp < travel_end:
            progress = self._ease((timestamp - start) / spec["heat_travel_duration"])
            return progress, spec["peak_level"] * (0.42 + 0.58 * progress), 0.72 + 0.28 * progress
        if timestamp < peak_end:
            return 1.0, spec["peak_level"], 1.0
        if timestamp < settle_end:
            amount = self._ease((timestamp - peak_end) / spec["settle_duration"])
            level = spec["peak_level"] + (spec["final_level"] - spec["peak_level"]) * amount
            return 1.0, level, 1.0 - amount
        return 1.0, spec["final_level"], 0.0

    def _activated_mask(self, mask: Image.Image, progress: float, bounds: tuple[int, int, int, int]) -> Image.Image:
        values = np.asarray(mask, dtype=np.float32)
        left, _, right, _ = bounds
        feather = max(10.0, (right - left) * 0.07)
        front = right - progress * (right - left)
        x = np.arange(values.shape[1], dtype=np.float32)
        activation = np.clip((x - front) / feather + 1.0, 0.0, 1.0)
        return Image.fromarray(np.clip(values * activation[None, :], 0, 255).astype(np.uint8), "L")

    def _front_mask(self, edge: Image.Image, progress: float, bounds: tuple[int, int, int, int]) -> Image.Image:
        values = np.asarray(edge, dtype=np.float32)
        left, _, right, _ = bounds
        front = right - progress * (right - left)
        x = np.arange(values.shape[1], dtype=np.float32)
        band = np.exp(-0.5 * ((x - front) / 6.0) ** 2)
        return Image.fromarray(np.clip(values * band[None, :], 0, 255).astype(np.uint8), "L")

    def _apply_cold_engraving(self, frame: Image.Image, key: str) -> Image.Image:
        spec, masks = self.elements[key], self.masks[key]
        displaced = ImageChops.offset(frame, 1, 2)
        displaced.putalpha(self._material_mask(masks["body"], 0.30))
        frame = Image.alpha_composite(frame, displaced)
        upper = ImageChops.subtract(masks["edge"], ImageChops.offset(masks["edge"], -1, -1))
        lower = ImageChops.subtract(masks["edge"], ImageChops.offset(masks["edge"], 1, 1))
        frame = Image.alpha_composite(frame, _color_layer(self.size, (2, 2, 2), self._material_mask(upper), 0.72))
        frame = Image.alpha_composite(frame, _color_layer(self.size, (104, 94, 79), self._material_mask(lower), spec["cold_recess_visibility"]))
        return Image.alpha_composite(frame, _color_layer(self.size, (13, 10, 8), self._material_mask(masks["body"]), 0.13))

    def _apply_flames(self, frame: Image.Image, key: str, progress: float, flame_level: float, frame_index: int) -> Image.Image:
        spec, masks = self.elements[key], self.masks[key]
        intensity = spec["flame_intensity"] * flame_level
        if intensity <= 0.02:
            return frame
        left, top, right, _ = masks["bounds"]
        active_front = right - progress * (right - left)
        flames = Image.new("RGBA", self.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(flames)
        count = 5 if key == "tagline" else 3
        for index in range(count):
            x = left + (right - left) * (index + 0.55) / count
            if x < active_front - 8:
                continue
            flicker = 0.72 + 0.28 * math.sin(frame_index * (0.31 + index * 0.027) + index * 1.7 + self.seed)
            height = (8 + (index % 3) * 4) * flicker * intensity
            width = 3.0 + 1.5 * flicker
            base_y = top + 3 + (index % 2) * 2
            alpha = round(150 * intensity)
            draw.polygon(((x - width, base_y), (x + width, base_y), (x + 1.2, base_y - height * 0.55),
                          (x - 0.8, base_y - height)), fill=(255, 95, 13, alpha))
            draw.ellipse((x - 1.8, base_y - height * 0.72, x + 1.8, base_y - height * 0.24), fill=(255, 190, 66, round(alpha * 0.72)))
        flames = flames.filter(ImageFilter.GaussianBlur(0.65))
        return Image.alpha_composite(frame, flames)

    def _apply_embers(self, frame: Image.Image, key: str, progress: float, flame_level: float, frame_index: int) -> Image.Image:
        spec, masks = self.elements[key], self.masks[key]
        if flame_level <= 0.05:
            return frame
        left, top, right, _ = masks["bounds"]
        active_front = right - progress * (right - left)
        layer = Image.new("RGBA", self.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        for index in range(spec["ember_count"]):
            cycle = (frame_index * (5 + index * 2) + index * 17 + self.seed) % 53
            if cycle > 15:
                continue
            life = cycle / 15.0
            x = right - ((index + 1) / (spec["ember_count"] + 1)) * (right - left)
            if x < active_front - 5:
                continue
            y = top - 2 - life * (8 + index * 2)
            alpha = round(135 * flame_level * (1.0 - life))
            draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill=(255, 137, 33, alpha))
        return Image.alpha_composite(frame, layer)

    def _apply_incandescent_state(self, frame: Image.Image, key: str, timestamp: float, frame_index: int) -> Image.Image:
        spec, masks = self.elements[key], self.masks[key]
        progress, level, flame_level = self._thermal_state(timestamp, spec)
        if progress <= 0.0:
            return frame
        body = self._activated_mask(masks["body"], progress, masks["bounds"])
        core = self._activated_mask(masks["raw"], progress, masks["bounds"])
        edge = self._activated_mask(masks["edge"], progress, masks["bounds"])
        # Burnt steel immediately around the cavity prevents the glow reading as clean neon.
        char = body.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(2.2))
        frame = Image.alpha_composite(frame, _color_layer(self.size, (8, 3, 1), char, 0.38))
        local_light = body.filter(ImageFilter.GaussianBlur(13.0))
        frame = Image.alpha_composite(frame, _color_layer(self.size, (171, 48, 5), local_light, 0.22 * level))
        glow = edge.filter(ImageFilter.GaussianBlur(spec.get("glow_radius", 5.5)))
        frame = Image.alpha_composite(frame, _color_layer(
            self.size, (241, 73, 7), glow, spec.get("glow_opacity", 0.52) * level))
        frame = Image.alpha_composite(frame, _color_layer(self.size, (218, 64, 7), self._material_mask(body), 0.62 * level))
        frame = Image.alpha_composite(frame, _color_layer(self.size, (255, 153, 41), self._material_mask(edge), 0.76 * level))
        # A narrow pale core survives mobile downsampling while the distressed body
        # and charred cavity preserve the physically heated, non-neon treatment.
        frame = Image.alpha_composite(frame, _color_layer(
            self.size, (255, 203, 104), core, spec.get("core_opacity", 0.30) * level))
        if progress < 1.0:
            front = self._front_mask(masks["edge"], progress, masks["bounds"])
            frame = Image.alpha_composite(frame, _color_layer(self.size, (255, 239, 169), front.filter(ImageFilter.GaussianBlur(1.0)), 0.94))
        frame = self._apply_flames(frame, key, progress, flame_level, frame_index)
        return self._apply_embers(frame, key, progress, flame_level, frame_index)

    def render_frame(self, frame_index: int) -> Image.Image:
        timestamp = frame_index / self.config.fps
        frame = super().render_frame(frame_index).convert("RGBA")
        for key in ("tagline", "website"):
            frame = self._apply_cold_engraving(frame, key)
        route_progress = max(0.0, min(1.0, (timestamp - self.thermal_route["start"]) / self.thermal_route["duration"]))
        if 0.0 < route_progress < 1.0:
            frame = self._apply_active_front(frame, self.route_points, route_progress, frame_index)
        for key in ("tagline", "website"):
            frame = self._apply_incandescent_state(frame, key, timestamp, frame_index)
        return frame.convert("RGB")
