#!/usr/bin/env python3
"""Characterless environmental-storytelling variant of the pulp trailer."""

from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from pulp_trailer_stage import ease
from pulp_trailer_stage_r1 import PulpTrailerRefinementStage


class CharacterlessPulpTrailerStage(PulpTrailerRefinementStage):
    """Let the laboratory carry tension with a bounded deterministic effect set."""

    def _draw_figure(self, canvas: Image.Image, intensity: float, timestamp: float) -> None:
        return

    def _instrument_bank(self, layer: Image.Image, intensity: float, timestamp: float) -> None:
        draw = ImageDraw.Draw(layer)
        paper, yellow, teal = self.palette["paper"], self.palette["yellow"], self.palette["teal"]
        # Angled foreground cabinet occupies the old figure zone without imitating a body.
        draw.polygon(((170, 820), (354, 782), (392, 1036), (145, 1090)), fill=(7, 15, 14, 246),
                     outline=(131, 109, 47, 240))
        draw.polygon(((190, 845), (334, 814), (355, 968), (171, 1008)), fill=(17, 31, 27, 255),
                     outline=teal + (220,))
        # Transformer coils and relay housings.
        for index in range(4):
            x = 206 + index * 37
            draw.rectangle((x, 870, x + 23, 963), fill=(7, 12, 11, 255), outline=(170, 128, 34, 215), width=2)
            for y in range(878, 960, 10):
                draw.line((x + 3, y, x + 20, y - 2), fill=(96, 76, 34, 170), width=2)
        # One pressure dial and one automatically moving lever.
        draw.ellipse((186, 1015, 247, 1076), fill=(199, 181, 125, 255), outline=(4, 9, 8, 255), width=5)
        angle = math.radians(215 + min(1.0, intensity * 1.12) * 220)
        draw.line((216, 1045, 216 + math.cos(angle) * 23, 1045 + math.sin(angle) * 23), fill=(115, 18, 10, 255), width=4)
        lever_angle = math.radians(-78 + 62 * ease((intensity - .28) / .58))
        pivot = (328, 1018)
        tip = (pivot[0] + math.cos(lever_angle) * 58, pivot[1] + math.sin(lever_angle) * 58)
        draw.line((pivot, tip), fill=paper + (255,), width=7)
        draw.ellipse((pivot[0] - 10, pivot[1] - 10, pivot[0] + 10, pivot[1] + 10), fill=(8, 13, 11, 255), outline=yellow + (235,), width=3)
        draw.ellipse((tip[0] - 9, tip[1] - 9, tip[0] + 9, tip[1] + 9), fill=self.palette["red"] + (255,))
        # Foreground pressure line leads the eye back to the reactor base.
        draw.line(((0, 1100), (154, 1040), (292, 1025), (474, 961)), fill=(3, 9, 8, 255), width=24, joint="curve")
        draw.line(((0, 1092), (154, 1032), (292, 1017), (474, 953)), fill=(67, 105, 80, 180), width=3, joint="curve")

    def _steam(self, layer: Image.Image, intensity: float, timestamp: float, frame_index: int) -> dict:
        effects = self.definition["environmental_effects"]
        if intensity < effects["steam_activation"]:
            return {"active": False, "opacity": 0}
        draw = ImageDraw.Draw(layer)
        activation = ease((intensity - effects["steam_activation"]) / .42)
        opacity_total = 0
        for source_index, (nx, ny) in enumerate(effects["steam_sources"]):
            sx, sy = nx * self.size[0], ny * self.size[1]
            cycle = (timestamp * (.37 + source_index * .08) + source_index * .41) % 1
            for puff in range(5):
                life = (cycle + puff / 5) % 1
                x = sx + math.sin(life * 7 + source_index) * (7 + 13 * activation)
                y = sy - life * (75 + 55 * activation)
                radius = 8 + life * 24
                alpha = round((1 - life) * (18 + 39 * activation))
                opacity_total += alpha
                draw.ellipse((x - radius * 1.25, y - radius, x + radius * 1.25, y + radius),
                             fill=self.palette["paper"] + (alpha,))
        return {"active": True, "opacity": opacity_total}

    def _arcs(self, layer: Image.Image, intensity: float, timestamp: float, frame_index: int) -> dict:
        effects = self.definition["environmental_effects"]
        event_level = 0.0
        nearest = None
        for event in effects["arc_events_seconds"]:
            distance = abs(timestamp - event)
            level = max(0.0, 1.0 - distance / effects["arc_duration_seconds"])
            if level > event_level:
                event_level, nearest = level, event
        if event_level <= 0 or intensity < .58:
            return {"active": False, "event": nearest, "level": 0}
        draw = ImageDraw.Draw(layer)
        rng = np.random.default_rng(self.seed + round((nearest or 0) * 1000))
        starts = ((352, 832, 438, 784), (390, 424, 455, 465))
        for arc_index, (x1, y1, x2, y2) in enumerate(starts[:1 if intensity < .88 else 2]):
            points = []
            for step in range(9):
                fraction = step / 8
                x = x1 + (x2 - x1) * fraction + rng.uniform(-6, 6) * math.sin(fraction * math.pi)
                y = y1 + (y2 - y1) * fraction + rng.uniform(-10, 10) * math.sin(fraction * math.pi)
                points.append((x, y))
            draw.line(points, fill=self.palette["yellow"] + (round(125 * event_level),), width=7)
            draw.line(points, fill=self.palette["cream"] + (round(235 * event_level),), width=3)
        return {"active": True, "event": nearest, "level": round(event_level, 3)}

    def _machine(self, scene: dict, timestamp: float, frame_index: int) -> Image.Image:
        base = super()._machine(scene, timestamp, frame_index).convert("RGBA")
        progress = ease((timestamp - scene["start"]) / (scene["end"] - scene["start"]))
        intensity = scene["intensity"][0] + (scene["intensity"][1] - scene["intensity"][0]) * progress
        effects = self.definition["environmental_effects"]
        pulse = .5 + .5 * math.sin(timestamp * math.tau * self.definition["machine"]["reactor_pulse_hz"])
        # Reactor-driven illumination reveals surrounding hardware, not the whole room.
        spill = Image.new("RGBA", self.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(spill)
        sd.ellipse((245, 185, 760, 1080), fill=self.palette["yellow"] + (round(11 + 34 * intensity * effects["light_spill_gain"]),))
        sd.polygon(((420, 260), (648, 290), (740, 1040), (318, 1040)), fill=self.palette["amber"] + (round(5 + 14 * intensity),))
        base = Image.alpha_composite(base, spill.filter(ImageFilter.GaussianBlur(58)))
        # A large pulse-driven pipe shadow shifts across the room.
        shadow = Image.new("RGBA", self.size, (0, 0, 0, 0))
        shift = round((pulse - .5) * 18 * intensity)
        ImageDraw.Draw(shadow).polygon(((250 + shift, 280), (310 + shift, 260), (540 + shift, 1120), (430 + shift, 1120)),
                                       fill=(2, 5, 5, round(18 + 55 * intensity * effects["moving_shadow_strength"])))
        base = Image.alpha_composite(base, shadow.filter(ImageFilter.GaussianBlur(18)))
        hardware = Image.new("RGBA", self.size, (0, 0, 0, 0))
        self._instrument_bank(hardware, intensity, timestamp)
        draw = ImageDraw.Draw(hardware)
        # One suspended cable sways; the containment ring only vibrates near danger.
        sway = math.sin(timestamp * 1.37) * effects["cable_sway_pixels"] * intensity
        cable = [(330 + index * 34, 535 + sway * math.sin(index * .48) + 23 * math.sin(index * .51)) for index in range(13)]
        draw.line(cable, fill=(4, 10, 9, 215), width=5)
        vibration = round(effects["ring_vibration_max_pixels"] * max(0, (intensity - .68) / .32) * math.sin(timestamp * 28))
        draw.ellipse((349 + vibration, 225, 704 + vibration, 400), outline=self.palette["yellow"] + (round(30 + 90 * intensity),), width=3)
        # Sparse dust only appears strongly inside the reactor light.
        dust_rng = np.random.default_rng(self.seed + 310000 + frame_index // 2)
        for _ in range(effects["dust_particles"]):
            x = int(dust_rng.integers(210, 735)); y = int(dust_rng.integers(170, 1080))
            alpha = round(dust_rng.uniform(12, 47) * intensity)
            radius = 1 if dust_rng.random() < .8 else 2
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=self.palette["paper"] + (alpha,))
        steam_layer = Image.new("RGBA", self.size, (0, 0, 0, 0))
        self._steam(steam_layer, intensity, timestamp, frame_index)
        steam_layer = steam_layer.filter(ImageFilter.GaussianBlur(8))
        arc_layer = Image.new("RGBA", self.size, (0, 0, 0, 0))
        self._arcs(arc_layer, intensity, timestamp, frame_index)
        base = Image.alpha_composite(base, hardware)
        base = Image.alpha_composite(base, steam_layer)
        return Image.alpha_composite(base, arc_layer).convert("RGB")
