#!/usr/bin/env python3
"""Deterministic, reusable 2D circuit-branding compositor for distressed metal."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


Point = tuple[float, float]


@dataclass(frozen=True)
class BurnPath:
    """A normalized path and the portion of the active-burn window it occupies."""

    points: tuple[Point, ...]
    start: float
    end: float


@dataclass(frozen=True)
class BurnConfig:
    width: int = 768
    duration_seconds: float = 9.0
    fps: int = 30
    idle_seconds: float = 1.0
    burn_end_seconds: float = 6.7
    title_pulse_start: float = 6.15
    title_pulse_end: float = 7.35
    scorch_intensity: float = 1.0
    glow_intensity: float = 1.0


DEFAULT_PATHS = (
    BurnPath(((0.02, 0.20), (0.12, 0.20), (0.12, 0.31), (0.25, 0.31), (0.25, 0.38)), 0.00, 0.74),
    BurnPath(((0.97, 0.17), (0.83, 0.17), (0.83, 0.27), (0.64, 0.27), (0.64, 0.40), (0.56, 0.40)), 0.08, 0.92),
    BurnPath(((0.04, 0.72), (0.18, 0.72), (0.18, 0.58), (0.32, 0.58), (0.32, 0.49)), 0.18, 0.86),
    BurnPath(((0.92, 0.78), (0.77, 0.78), (0.77, 0.61), (0.62, 0.61), (0.62, 0.51), (0.55, 0.51)), 0.28, 1.00),
)


def _scaled_points(path: BurnPath, size: tuple[int, int]) -> list[tuple[float, float]]:
    width, height = size
    return [(x * (width - 1), y * (height - 1)) for x, y in path.points]


def _polyline_lengths(points: Sequence[tuple[float, float]]) -> tuple[list[float], float]:
    lengths = [0.0]
    for first, second in zip(points, points[1:]):
        lengths.append(lengths[-1] + math.dist(first, second))
    return lengths, lengths[-1]


def _point_at(points: Sequence[tuple[float, float]], progress: float) -> tuple[float, float]:
    lengths, total = _polyline_lengths(points)
    target = max(0.0, min(1.0, progress)) * total
    for index in range(1, len(points)):
        if target <= lengths[index]:
            span = max(lengths[index] - lengths[index - 1], 1e-6)
            amount = (target - lengths[index - 1]) / span
            return (
                points[index - 1][0] + (points[index][0] - points[index - 1][0]) * amount,
                points[index - 1][1] + (points[index][1] - points[index - 1][1]) * amount,
            )
    return points[-1]


def _partial_polyline(points: Sequence[tuple[float, float]], progress: float) -> list[tuple[float, float]]:
    progress = max(0.0, min(1.0, progress))
    if progress <= 0.0:
        return []
    lengths, total = _polyline_lengths(points)
    target = progress * total
    result = [points[0]]
    for index in range(1, len(points)):
        if lengths[index] <= target:
            result.append(points[index])
            continue
        result.append(_point_at(points, progress))
        break
    return result


def _segment_between(points: Sequence[tuple[float, float]], start: float, end: float, samples: int = 18) -> list[tuple[float, float]]:
    if end <= 0.0 or end <= start:
        return []
    lo, hi = max(0.0, start), min(1.0, end)
    return [_point_at(points, lo + (hi - lo) * index / (samples - 1)) for index in range(samples)]


def _line_mask(size: tuple[int, int], points: Iterable[tuple[float, float]], width: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    vertices = list(points)
    if len(vertices) >= 2:
        ImageDraw.Draw(mask).line(vertices, fill=255, width=width, joint="curve")
    return mask


def _color_layer(size: tuple[int, int], color: tuple[int, int, int], mask: Image.Image, opacity: float = 1.0) -> Image.Image:
    if opacity != 1.0:
        mask = mask.point(lambda value: round(value * opacity))
    layer = Image.new("RGBA", size, color + (0,))
    layer.putalpha(mask)
    return layer


class MetalCircuitBurnStage:
    """Render a bounded heated traversal while preserving a source plate."""

    def __init__(self, source: Path, config: BurnConfig = BurnConfig(), paths: Sequence[BurnPath] = DEFAULT_PATHS):
        self.source_path = Path(source)
        original = Image.open(self.source_path).convert("RGB")
        target_height = round(original.height * config.width / original.width)
        if target_height % 2:
            target_height += 1
        self.base = original.resize((config.width, target_height), Image.Resampling.LANCZOS)
        self.size = self.base.size
        self.config = config
        self.paths = tuple(paths)
        self.scaled_paths = tuple(_scaled_points(path, self.size) for path in self.paths)
        self.texture = self._texture_map()

    @property
    def frame_count(self) -> int:
        return round(self.config.duration_seconds * self.config.fps)

    def _texture_map(self) -> np.ndarray:
        luma = np.asarray(self.base.convert("L"), dtype=np.float32) / 255.0
        yy, xx = np.indices(luma.shape)
        deterministic_grain = 0.88 + 0.12 * np.sin(xx * 0.173 + yy * 0.119) * np.sin(xx * 0.037 - yy * 0.091)
        return np.clip((0.78 + 0.22 * (1.0 - luma)) * deterministic_grain, 0.56, 1.0)

    def _material_mask(self, mask: Image.Image, opacity: float = 1.0) -> Image.Image:
        values = np.asarray(mask, dtype=np.float32) * self.texture * opacity
        return Image.fromarray(np.clip(values, 0, 255).astype(np.uint8), "L")

    def _path_progress(self, timestamp: float, path: BurnPath) -> float:
        global_progress = (timestamp - self.config.idle_seconds) / (self.config.burn_end_seconds - self.config.idle_seconds)
        return max(0.0, min(1.0, (global_progress - path.start) / (path.end - path.start)))

    def _apply_aftermath(self, frame: Image.Image, points: Sequence[tuple[float, float]], progress: float) -> Image.Image:
        traveled = _partial_polyline(points, progress)
        if len(traveled) < 2:
            return frame
        intensity = self.config.scorch_intensity
        temper = _line_mask(self.size, traveled, 17).filter(ImageFilter.GaussianBlur(5.2))
        frame = Image.alpha_composite(frame, _color_layer(self.size, (104, 42, 13), self._material_mask(temper), 0.31 * intensity))
        char = _line_mask(self.size, traveled, 9).filter(ImageFilter.GaussianBlur(1.3))
        frame = Image.alpha_composite(frame, _color_layer(self.size, (8, 5, 3), self._material_mask(char), 0.72 * intensity))
        shadow = ImageChops.offset(_line_mask(self.size, traveled, 4), 1, 2)
        frame = Image.alpha_composite(frame, _color_layer(self.size, (0, 0, 0), self._material_mask(shadow), 0.82 * intensity))
        rim = ImageChops.offset(_line_mask(self.size, traveled, 2), -1, -1)
        frame = Image.alpha_composite(frame, _color_layer(self.size, (137, 68, 27), self._material_mask(rim), 0.66 * intensity))
        core = _line_mask(self.size, traveled, 1)
        return Image.alpha_composite(frame, _color_layer(self.size, (42, 22, 12), self._material_mask(core), 0.88 * intensity))

    def _apply_active_front(self, frame: Image.Image, points: Sequence[tuple[float, float]], progress: float, frame_index: int) -> Image.Image:
        if not 0.0 < progress < 1.0:
            return frame
        active = _segment_between(points, progress - 0.075, progress)
        if len(active) < 2:
            return frame
        pulse = 0.90 + 0.10 * math.sin(frame_index * 0.71)
        glow = _line_mask(self.size, active, 20).filter(ImageFilter.GaussianBlur(8.0))
        frame = Image.alpha_composite(frame, _color_layer(self.size, (229, 71, 8), glow, 0.50 * self.config.glow_intensity * pulse))
        amber = _line_mask(self.size, active, 8).filter(ImageFilter.GaussianBlur(2.6))
        frame = Image.alpha_composite(frame, _color_layer(self.size, (255, 126, 20), amber, 0.82 * self.config.glow_intensity * pulse))
        hot = _line_mask(self.size, active, 3)
        frame = Image.alpha_composite(frame, _color_layer(self.size, (255, 225, 144), hot, 0.94 * self.config.glow_intensity))
        front = _point_at(points, progress)
        flare = Image.new("L", self.size, 0)
        radius = 9 + 2 * math.sin(frame_index * 0.53)
        ImageDraw.Draw(flare).ellipse((front[0] - radius, front[1] - radius, front[0] + radius, front[1] + radius), fill=220)
        flare = flare.filter(ImageFilter.GaussianBlur(5.0))
        frame = Image.alpha_composite(frame, _color_layer(self.size, (255, 113, 20), flare, 0.74))
        return self._apply_sparks(frame, front, frame_index)

    def _apply_sparks(self, frame: Image.Image, front: tuple[float, float], frame_index: int) -> Image.Image:
        sparks = Image.new("RGBA", self.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(sparks)
        for index in range(3):
            cycle = (frame_index * (7 + index * 2) + index * 13) % 47
            if cycle > 14:
                continue
            life = cycle / 14.0
            angle = -1.9 + index * 0.67 + 0.16 * math.sin(frame_index * 0.31 + index)
            distance = 5 + life * (13 + index * 4)
            x = front[0] + math.cos(angle) * distance
            y = front[1] + math.sin(angle) * distance + life * life * 8
            alpha = round(150 * (1.0 - life))
            draw.line((x, y, x - math.cos(angle) * 4, y - math.sin(angle) * 4), fill=(255, 159, 45, alpha), width=1)
        return Image.alpha_composite(frame, sparks)

    def _apply_title_pulse(self, frame: Image.Image, timestamp: float) -> Image.Image:
        start, end = self.config.title_pulse_start, self.config.title_pulse_end
        if not start < timestamp < end:
            return frame
        phase = (timestamp - start) / (end - start)
        envelope = math.sin(math.pi * phase) ** 1.35
        width, height = self.size
        mask = Image.new("L", self.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0.045 * width, 0.235 * height, 0.605 * width, 0.535 * height), radius=34, fill=round(112 * envelope))
        mask = mask.filter(ImageFilter.GaussianBlur(38))
        return Image.alpha_composite(frame, _color_layer(self.size, (202, 73, 14), mask, 0.44))

    def render_frame(self, frame_index: int) -> Image.Image:
        timestamp = frame_index / self.config.fps
        frame = self.base.convert("RGBA")
        progresses = [self._path_progress(timestamp, path) for path in self.paths]
        for points, progress in zip(self.scaled_paths, progresses):
            frame = self._apply_aftermath(frame, points, progress)
        for points, progress in zip(self.scaled_paths, progresses):
            frame = self._apply_active_front(frame, points, progress, frame_index)
        frame = self._apply_title_pulse(frame, timestamp)
        return frame.convert("RGB")
