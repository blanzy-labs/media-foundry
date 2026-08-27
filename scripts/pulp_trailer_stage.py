#!/usr/bin/env python3
"""Reusable deterministic pulp-trailer cards, machinery, and film treatment."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont


def ease(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


class PulpTrailerStage:
    def __init__(self, definition: dict):
        self.definition = definition
        self.seed = definition["seed"]
        video = definition["video"]
        self.size = (video["width"], video["height"])
        self.fps = video["fps"]
        self.duration = video["duration_seconds"]
        self.frame_count = round(self.duration * self.fps)
        self.palette = {key: tuple(value) for key, value in definition["palette"].items()}
        self.display_font = definition["fonts"]["display"]
        self.support_font = definition["fonts"]["support"]
        self.reference = Image.open(Path(definition["source_reference"]["path"])).convert("RGB")
        rng = np.random.default_rng(self.seed)
        height, width = self.size[1], self.size[0]
        low = rng.normal(0, 1, (height // 4, width // 4)).astype(np.float32)
        low_image = Image.fromarray(np.uint8(np.clip(128 + low * 28, 0, 255)), "L")
        self.paper_texture = np.asarray(low_image.resize(self.size, Image.Resampling.BILINEAR), dtype=np.float32) - 128
        self.wear = rng.random((height, width))
        self.edge_mask = self._edge_mask(definition["film"]["edge_wear"])

    def _edge_mask(self, width: int) -> Image.Image:
        w, h = self.size
        y, x = np.indices((h, w))
        distance = np.minimum.reduce((x, y, w - 1 - x, h - 1 - y)).astype(np.float32)
        rng = np.random.default_rng(self.seed + 91)
        rough = rng.normal(0, 3.2, (h // 8, w // 8)).astype(np.float32)
        rough = np.asarray(Image.fromarray(rough, mode="F").resize(self.size, Image.Resampling.BILINEAR))
        mask = np.clip((width + rough - distance) / max(width, 1), 0, 1) * 205
        return Image.fromarray(mask.astype(np.uint8), "L")

    def _scene(self, timestamp: float) -> dict:
        for scene in self.definition["timeline"]:
            if scene["start"] <= timestamp < scene["end"]:
                return scene
        return self.definition["timeline"][-1]

    @staticmethod
    def _fit_font(path: str, text: str, maximum: int, start: int) -> ImageFont.FreeTypeFont:
        size = start
        while size > 16:
            font = ImageFont.truetype(path, size)
            if font.getbbox(text)[2] <= maximum:
                return font
            size -= 2
        return ImageFont.truetype(path, size)

    def _printed_text(self, canvas: Image.Image, position: tuple[int, int], text: str, size: int,
                      color: tuple[int, int, int], anchor: str = "mm", maximum: int | None = None,
                      registration: bool = False) -> None:
        font = self._fit_font(self.display_font, text, maximum or self.size[0] - 90, size)
        raw = Image.new("L", self.size, 0)
        ImageDraw.Draw(raw).text(position, text, font=font, fill=255, anchor=anchor, stroke_width=1)
        values = np.asarray(raw, dtype=np.uint8)
        distress = ((self.wear > 0.982) | ((self.paper_texture > 27) & (self.wear > .86))) & (values > 0)
        values = values.copy()
        values[distress] = 0
        mask = Image.fromarray(values, "L")
        if registration:
            teal = Image.new("RGBA", self.size, self.palette["teal"] + (0,))
            teal.putalpha(ImageChops.offset(mask, -2, 1).point(lambda p: round(p * .48)))
            canvas.alpha_composite(teal)
            yellow = Image.new("RGBA", self.size, self.palette["yellow"] + (0,))
            yellow.putalpha(ImageChops.offset(mask, 2, 0).point(lambda p: round(p * .35)))
            canvas.alpha_composite(yellow)
        layer = Image.new("RGBA", self.size, color + (0,))
        layer.putalpha(mask)
        canvas.alpha_composite(layer)

    def _card(self, scene: dict, timestamp: float) -> Image.Image:
        w, h = self.size
        canvas = Image.new("RGBA", self.size, self.palette["black"] + (255,))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((28, 25, w - 29, h - 26), outline=self.palette["paper"] + (120,), width=2)
        lines = scene["lines"]
        if len(lines) == 1:
            self._printed_text(canvas, (w // 2, h // 2), lines[0], 180,
                               self.palette[scene["color"]], maximum=w - 72, registration=True)
            draw.line((90, h // 2 + 122, w - 90, h // 2 + 122), fill=self.palette["yellow"] + (210,), width=5)
        else:
            sizes = (106, 85, 105)
            positions = (h * .34, h * .50, h * .66)
            for line, size, y in zip(lines, sizes, positions):
                self._printed_text(canvas, (w // 2, round(y)), line, size,
                                   self.palette[scene["color"]], maximum=w - 92, registration=False)
        progress = (timestamp - scene["start"]) / (scene["end"] - scene["start"])
        exposure = 0.78 + min(1.0, progress * 7) * .22
        return ImageEnhance.Brightness(canvas.convert("RGB")).enhance(exposure)

    def _draw_figure(self, canvas: Image.Image, intensity: float, timestamp: float) -> None:
        """Draw the intentionally simple first-pass scale silhouette."""
        draw = ImageDraw.Draw(canvas)
        reaction = ease((intensity - self.definition["machine"]["silhouette_reaction_start"]) / .35)
        lean = round(reaction * 18)
        draw.ellipse((244 - lean, 735, 322 - lean, 817), fill=(4, 7, 6, 255), outline=(185, 139, 37, 220), width=3)
        draw.polygon(((258 - lean, 800), (326 - lean, 806), (355 - lean, 1000), (207 - lean, 1055), (211 - lean, 879)),
                     fill=(4, 7, 6, 255), outline=(174, 130, 37, 220))
        arm_y = 870 - round(42 * reaction)
        draw.line((318 - lean, 846, 398 - lean, arm_y), fill=(5, 8, 7, 255), width=28)
        draw.ellipse((388 - lean, arm_y - 10, 412 - lean, arm_y + 12), fill=(5, 8, 7, 255))

    def _machine(self, scene: dict, timestamp: float, frame_index: int) -> Image.Image:
        w, h = self.size
        progress = ease((timestamp - scene["start"]) / (scene["end"] - scene["start"]))
        intensity = scene["intensity"][0] + (scene["intensity"][1] - scene["intensity"][0]) * progress
        pulse = .5 + .5 * math.sin(timestamp * math.tau * self.definition["machine"]["reactor_pulse_hz"])
        instability = intensity * (.88 + .12 * pulse)
        canvas = Image.new("RGBA", self.size, self.palette["black"] + (255,))
        draw = ImageDraw.Draw(canvas)
        # Teal ink architecture and deep industrial shadows.
        draw.rectangle((0, 0, w, h), fill=self.palette["deep_teal"] + (255,))
        draw.rectangle((22, 70, 250, 925), fill=(12, 30, 28, 255), outline=self.palette["teal"] + (255,), width=7)
        for x in (48, 112, 177, 238, 650, 706):
            draw.rectangle((x, 0, x + 14, h), fill=(5, 18, 17, 255), outline=(42, 103, 94, 190), width=3)
        for y in (250, 466, 725):
            draw.line((0, y, w, y - 45), fill=(6, 17, 16, 255), width=18)
            draw.line((0, y - 4, w, y - 49), fill=(45, 103, 91, 255), width=3)
        # Left analog control panel.
        draw.polygon(((30, 525), (277, 490), (277, 930), (30, 1000)), fill=(15, 25, 22, 255),
                     outline=self.palette["paper"] + (180,))
        gauge_levels = (intensity * .78, min(1.0, intensity * 1.08 + .05 * math.sin(timestamp * 11)), intensity ** .72)
        for index, level in enumerate(gauge_levels):
            cx, cy, radius = 78 + index * 75, 622 + (index % 2) * 21, 31
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(199, 181, 125, 255),
                         outline=(5, 12, 10, 255), width=5)
            angle = math.radians(215 + 220 * min(1, level))
            draw.line((cx, cy, cx + math.cos(angle) * 24, cy + math.sin(angle) * 24), fill=(112, 14, 8, 255), width=4)
            draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=(5, 8, 7, 255))
        thresholds = self.definition["machine"]["indicator_thresholds"]
        for index, threshold in enumerate(thresholds):
            x, y = 55 + (index % 3) * 72, 760 + (index // 3) * 70
            active = intensity >= threshold
            flicker = active and ((frame_index + index * 7) % (17 + index) > 1)
            color = self.palette["red"] if index % 3 != 2 else self.palette["amber"]
            draw.ellipse((x - 11, y - 11, x + 11, y + 11), fill=(26, 18, 9, 255), outline=self.palette["paper"] + (170,), width=2)
            if flicker:
                halo = Image.new("RGBA", self.size, (0, 0, 0, 0))
                ImageDraw.Draw(halo).ellipse((x - 25, y - 25, x + 25, y + 25), fill=color + (120,))
                canvas.alpha_composite(halo.filter(ImageFilter.GaussianBlur(9)))
                draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=color + (255,))
        # Reactor body, chamber, and suspended ring.
        draw.rounded_rectangle((386, 285, 667, 1025), radius=35, fill=(8, 19, 17, 255), outline=(151, 126, 40, 255), width=8)
        draw.ellipse((349, 225, 704, 400), fill=(16, 29, 24, 255), outline=self.palette["yellow"] + (230,), width=11)
        draw.ellipse((389, 265, 665, 360), fill=(22, 54, 43, 255), outline=self.palette["paper"] + (200,), width=5)
        for index in range(14):
            angle = math.tau * index / 14
            x = 527 + math.cos(angle) * 157
            y = 312 + math.sin(angle) * 63
            active = intensity > .35 + index * .025
            draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(216, 45, 16, 255) if active else (45, 20, 12, 255))
        draw.rounded_rectangle((430, 340, 622, 845), radius=44, fill=(20, 57, 48, 255), outline=(219, 193, 108, 255), width=6)
        # Energy illumination is layered, illustrative, and intensity-driven.
        glow = Image.new("RGBA", self.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        energy_alpha = round(55 + 180 * instability)
        gd.rounded_rectangle((443, 348, 609, 836), radius=42, fill=self.palette["yellow"] + (round(28 + 85 * intensity),))
        gd.ellipse((396 - 60 * intensity, 260 - 30 * intensity, 656 + 60 * intensity, 900 + 30 * intensity),
                   fill=self.palette["yellow"] + (round(18 + 48 * intensity),))
        canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(24 + 18 * intensity)))
        draw = ImageDraw.Draw(canvas)
        rng = np.random.default_rng(self.seed + frame_index * 13)
        for filament in range(self.definition["machine"]["energy_filaments"]):
            phase = filament * .73 + timestamp * (2.3 + filament * .07)
            points = []
            for step in range(18):
                y = 380 + step * 25
                spread = 15 + intensity * 54
                x = 526 + math.sin(phase + step * .72) * spread + rng.uniform(-6, 6) * intensity
                points.append((x, y))
            color = self.palette["cream"] if filament % 3 else self.palette["yellow"]
            draw.line(points, fill=color + (energy_alpha,), width=2 + (filament % 2))
        draw.rectangle((474, 748, 580, 1032), fill=(10, 18, 16, 255), outline=self.palette["paper"] + (200,), width=5)
        for y in range(780, 1000, 45):
            draw.line((478, y, 576, y), fill=(151, 111, 26, 255), width=3)
        # Catwalk and sparse scale figures.
        draw.line((270, 890, 768, 810), fill=(202, 176, 91, 255), width=6)
        for x in range(290, 760, 48):
            draw.line((x, 886 - (x - 270) * .16, x, 840 - (x - 270) * .16), fill=(178, 151, 78, 255), width=3)
        # Foreground human reacts only after the machine is dangerous.
        self._draw_figure(canvas, intensity, timestamp)
        # Peak overload is brief, not a sustained whiteout.
        if scene["phase"] == "peak":
            flash = math.exp(-((timestamp - 23.72) / .16) ** 2)
            if flash > .01:
                veil = Image.new("RGBA", self.size, self.palette["cream"] + (round(175 * flash),))
                canvas.alpha_composite(veil)
        return canvas.convert("RGB")

    def _final(self, scene: dict, timestamp: float) -> Image.Image:
        w, h = self.size
        canvas = Image.new("RGBA", self.size, self.palette["black"] + (255,))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((24, 24, w - 25, h - 25), outline=self.palette["paper"] + (170,), width=3)
        draw.rectangle((41, 42, w - 42, h - 43), outline=self.palette["teal"] + (180,), width=2)
        self._printed_text(canvas, (w // 2, 370), scene["title"][0], 184, self.palette["cream"], maximum=w - 76, registration=True)
        self._printed_text(canvas, (w // 2, 550), scene["title"][1], 184, self.palette["yellow"], maximum=w - 76, registration=True)
        self._printed_text(canvas, (w // 2, 700), scene["book"], 64, self.palette["paper"], maximum=w - 180)
        draw.line((145, 745, w - 145, 745), fill=self.palette["yellow"] + (230,), width=5)
        self._printed_text(canvas, (w // 2, 875), scene["author"], 72, self.palette["yellow"], maximum=w - 100)
        if timestamp >= scene["cta_start"]:
            self._printed_text(canvas, (w // 2, 1015), scene["cta"], 36, self.palette["cream"], maximum=w - 80)
        return canvas.convert("RGB")

    def _film(self, image: Image.Image, timestamp: float, frame_index: int, stress: float) -> Image.Image:
        w, h = self.size
        jitter = self.definition["film"]["jitter_pixels"]
        dx = round(math.sin(frame_index * 1.71 + self.seed) * jitter)
        dy = round(math.sin(frame_index * 1.13 + self.seed * .3) * jitter)
        image = image.transform(self.size, Image.Transform.AFFINE, (1, 0, -dx, 0, 1, -dy), fillcolor=self.palette["black"])
        if stress > .72 and frame_index % 11 in (0, 1):
            values = np.asarray(image).copy()
            drift = self.definition["film"]["registration_peak_pixels"]
            red = np.roll(values[:, :, 0], drift, axis=1)
            teal = np.roll(values[:, :, 2], -1, axis=1)
            values[:, :, 0] = red
            values[:, :, 2] = teal
            image = Image.fromarray(values, "RGB")
        exposure = 0.975 + .025 * math.sin(frame_index * 2.39) + .012 * math.sin(frame_index * .37)
        image = ImageEnhance.Brightness(image).enhance(exposure)
        rng = np.random.default_rng(self.seed + 100000 + frame_index)
        small = rng.normal(128, 23, (h // 6, w // 6)).clip(0, 255).astype(np.uint8)
        grain = Image.fromarray(small, "L").resize(self.size, Image.Resampling.BILINEAR).convert("RGB")
        image = Image.blend(image, grain, self.definition["film"]["grain_strength"])
        overlay = Image.new("RGBA", self.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for index in range(self.definition["film"]["dust_count"]):
            x = int(rng.integers(8, w - 8)); y = int(rng.integers(8, h - 8)); radius = int(rng.integers(1, 4))
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=self.palette["paper"] + (int(rng.integers(18, 75)),))
        if frame_index % 127 in (0, 1):
            x = int(rng.integers(40, w - 40)); draw.line((x, 18, x + int(rng.integers(-5, 6)), h - 18), fill=(238, 218, 160, 65), width=1)
        result = Image.alpha_composite(image.convert("RGBA"), overlay)
        wear = Image.new("RGBA", self.size, self.palette["black"] + (0,)); wear.putalpha(self.edge_mask)
        result = Image.alpha_composite(result, wear)
        return result.convert("RGB")

    def render_frame(self, frame_index: int) -> Image.Image:
        timestamp = frame_index / self.fps
        scene = self._scene(timestamp)
        if scene["kind"] == "black":
            frame = Image.new("RGB", self.size, self.palette["black"])
            stress = 0.0
        elif scene["kind"] == "card":
            frame = self._card(scene, timestamp)
            stress = .35
        elif scene["kind"] == "machine":
            frame = self._machine(scene, timestamp, frame_index)
            progress = ease((timestamp - scene["start"]) / (scene["end"] - scene["start"]))
            stress = scene["intensity"][0] + (scene["intensity"][1] - scene["intensity"][0]) * progress
        else:
            frame = self._final(scene, timestamp)
            stress = .42
        return self._film(frame, timestamp, frame_index, stress)
