#!/usr/bin/env python3
"""Material, character, and atmosphere refinement for the pulp-trailer format."""

from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from pulp_trailer_stage import PulpTrailerStage, ease


class PulpTrailerRefinementStage(PulpTrailerStage):
    """Preserve editorial structure while enriching the illustrated world."""

    def __init__(self, definition: dict):
        super().__init__(definition)
        rng = np.random.default_rng(self.seed + 151)
        h, w = self.size[1], self.size[0]
        fibers = np.full((h, w), 236, dtype=np.float32)
        fibers += rng.normal(0, 8, fibers.shape)
        for _ in range(170):
            y = int(rng.integers(0, h)); length = int(rng.integers(22, 180)); x = int(rng.integers(0, max(1, w - length)))
            fibers[y:y + 1, x:x + length] -= rng.uniform(18, 48)
        self.fiber_plate = Image.fromarray(np.clip(fibers, 0, 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(.35))

    def _draw_figure(self, canvas: Image.Image, intensity: float, timestamp: float) -> None:
        draw = ImageDraw.Draw(canvas)
        reaction = ease((intensity - self.definition["machine"]["silhouette_reaction_start"]) / .35)
        recoil = round(reaction * 16)
        step = round(reaction * 13)
        ink = (8, 10, 8, 255)
        coat = (20, 24, 18, 255)
        coat_mid = (45, 43, 27, 255)
        rim = (222, 164, 43, round(135 + 90 * intensity))
        teal_rim = (34, 105, 91, 210)
        # Separated legs and planted feet make the lower body unmistakably human.
        draw.polygon(((244 - recoil, 958), (279 - recoil, 956), (275 - recoil + step, 1085),
                      (237 - recoil + step, 1085), (225 - recoil, 1010)), fill=ink, outline=rim)
        draw.polygon(((286 - recoil, 955), (318 - recoil, 946), (350 - recoil - step, 1077),
                      (309 - recoil - step, 1084), (279 - recoil, 1010)), fill=(11, 13, 10, 255), outline=rim)
        draw.polygon(((232 - recoil + step, 1070), (278 - recoil + step, 1070), (286 - recoil + step, 1090),
                      (223 - recoil + step, 1090)), fill=(5, 7, 6, 255))
        draw.polygon(((304 - recoil - step, 1070), (353 - recoil - step, 1068), (365 - recoil - step, 1087),
                      (302 - recoil - step, 1089)), fill=(5, 7, 6, 255))
        # Long laboratory coat with readable shoulders, waist, lapel, and folds.
        torso = ((233 - recoil, 820), (268 - recoil, 804), (310 - recoil, 814), (333 - recoil, 866),
                 (322 - recoil, 970), (282 - recoil, 997), (224 - recoil, 970), (210 - recoil, 884))
        draw.polygon(torso, fill=coat, outline=rim)
        draw.polygon(((265 - recoil, 816), (286 - recoil, 843), (276 - recoil, 955), (244 - recoil, 963),
                      (232 - recoil, 863)), fill=coat_mid)
        draw.line((274 - recoil, 825, 286 - recoil, 961), fill=teal_rim, width=3)
        draw.line((239 - recoil, 848, 256 - recoil, 955), fill=(101, 75, 29, 175), width=4)
        draw.polygon(((259 - recoil, 817), (278 - recoil, 846), (293 - recoil, 816)), fill=(6, 9, 8, 255), outline=rim)
        # Neck and profile head with brow, nose, chin, ear, and hair breakup.
        draw.polygon(((263 - recoil, 799), (287 - recoil, 796), (291 - recoil, 822), (264 - recoil, 827)), fill=(35, 29, 17, 255), outline=rim)
        profile = ((242 - recoil, 752), (250 - recoil, 730), (271 - recoil, 719), (295 - recoil, 726),
                   (308 - recoil, 744), (320 - recoil, 751), (311 - recoil, 759), (314 - recoil, 776),
                   (300 - recoil, 795), (270 - recoil, 802), (248 - recoil, 787), (238 - recoil, 770))
        draw.polygon(profile, fill=(24, 22, 15, 255), outline=rim)
        draw.polygon(((239 - recoil, 755), (246 - recoil, 732), (269 - recoil, 717), (292 - recoil, 724),
                      (278 - recoil, 744), (255 - recoil, 752)), fill=(6, 9, 8, 255))
        draw.ellipse((278 - recoil, 755, 289 - recoil, 768), outline=(174, 116, 31, 220), width=2)
        draw.line((298 - recoil, 748, 310 - recoil, 751), fill=(234, 180, 54, 215), width=2)
        # Rear arm hangs separately; reactor-side arm bends at a visible elbow.
        draw.line(((225 - recoil, 850), (196 - recoil, 925), (188 - recoil, 982)), fill=ink, width=25, joint="curve")
        draw.line(((225 - recoil, 850), (196 - recoil, 925), (188 - recoil, 982)), fill=teal_rim, width=3, joint="curve")
        elbow = (350 - recoil, 872 - round(25 * reaction))
        hand = (414 - recoil, 838 - round(50 * reaction))
        draw.line(((310 - recoil, 835), elbow, hand), fill=ink, width=25, joint="curve")
        draw.line(((310 - recoil, 835), elbow, hand), fill=rim, width=3, joint="curve")
        draw.ellipse((elbow[0] - 14, elbow[1] - 14, elbow[0] + 14, elbow[1] + 14), fill=ink, outline=rim)
        palm = ((hand[0] - 8, hand[1] - 12), (hand[0] + 15, hand[1] - 8), (hand[0] + 18, hand[1] + 9),
                (hand[0] - 5, hand[1] + 12))
        draw.polygon(palm, fill=(17, 15, 10, 255), outline=rim)
        for finger in range(3):
            y = hand[1] - 7 + finger * 6
            draw.line((hand[0] + 10, y, hand[0] + 27 + finger * 2, y - 4 + finger * 2), fill=rim, width=2)
        # Sparse painterly dry-brush breaks on the coat.
        for index in range(11):
            x = 225 - recoil + (index * 17) % 92
            y = 850 + (index * 43) % 116
            draw.line((x, y, x + 12 + index % 4 * 3, y - 7), fill=(91, 70, 29, 90), width=2)

    def _machine(self, scene: dict, timestamp: float, frame_index: int) -> Image.Image:
        base = super()._machine(scene, timestamp, frame_index).convert("RGBA")
        progress = ease((timestamp - scene["start"]) / (scene["end"] - scene["start"]))
        intensity = scene["intensity"][0] + (scene["intensity"][1] - scene["intensity"][0]) * progress
        overlay = Image.new("RGBA", self.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        # Distant industrial silhouettes and nested pipes add depth without motion.
        draw.ellipse((280, 80, 470, 430), fill=(3, 17, 16, 95), outline=(36, 89, 76, 135), width=4)
        draw.rectangle((319, 202, 431, 620), fill=(2, 13, 13, 55), outline=(31, 79, 70, 100), width=3)
        for x, offset in ((20, 0), (88, 27), (332, 10), (733, 45)):
            draw.line((x, 80 + offset, x, 1050), fill=(2, 9, 9, 125), width=20)
            draw.line((x + 4, 80 + offset, x + 4, 1050), fill=(43, 103, 88, 105), width=3)
        for y in (152, 416, 665):
            draw.arc((250, y - 90, 790, y + 150), 195, 350, fill=(5, 17, 15, 92), width=7)
        # Catwalk cross-bracing and cable sag.
        for x in range(285, 760, 42):
            y = 885 - (x - 270) * .16
            draw.line((x, y, x + 34, y - 45), fill=(146, 115, 47, 115), width=2)
        cable = [(290 + i * 35, 520 + 34 * math.sin(i * .52)) for i in range(14)]
        draw.line(cable, fill=(2, 7, 7, 145), width=4)
        # Irregular asymmetric atomic plasma, distinct from the clean base filaments.
        rng = np.random.default_rng(self.seed + frame_index * 29)
        for index in range(self.definition["machine"]["plasma_blobs"]):
            y = 390 + index * 61 + math.sin(timestamp * (2.2 + index * .13)) * 23
            x = 520 + math.sin(timestamp * 1.7 + index * 1.31) * (18 + intensity * 31)
            rx = 8 + intensity * rng.uniform(12, 34); ry = 15 + intensity * rng.uniform(18, 46)
            color = self.palette["yellow"] if index % 2 else self.palette["cream"]
            draw.ellipse((x - rx, y - ry, x + rx, y + ry), fill=color + (round(16 + intensity * 38),))
        for index in range(5):
            x = 493 + index * 18 + math.sin(timestamp * 3 + index) * 8
            draw.line((x, 390, x - 22 + intensity * 38, 780), fill=self.palette["amber"] + (round(45 + 80 * intensity),), width=2)
        # Grime, flaking paint, and imperfect ink coverage on machinery surfaces.
        grime_rng = np.random.default_rng(self.seed + 500)
        for _ in range(self.definition["machine"]["grime_marks"]):
            x = int(grime_rng.integers(20, 735)); y = int(grime_rng.integers(120, 1040))
            length = int(grime_rng.integers(3, 24)); alpha = int(grime_rng.integers(18, 72))
            draw.line((x, y, x + length, y + int(grime_rng.integers(-5, 6))), fill=(3, 7, 6, alpha), width=int(grime_rng.integers(1, 4)))
        # Controlled reactor light spill reveals the refined figure edges.
        spill = Image.new("RGBA", self.size, (0, 0, 0, 0))
        ImageDraw.Draw(spill).ellipse((150, 650, 570, 1110), fill=self.palette["yellow"] + (round(12 + 28 * intensity),))
        base = Image.alpha_composite(base, spill.filter(ImageFilter.GaussianBlur(52)))
        return Image.alpha_composite(base, overlay).convert("RGB")

    def _film(self, image: Image.Image, timestamp: float, frame_index: int, stress: float) -> Image.Image:
        image = super()._film(image, timestamp, frame_index, stress).convert("RGBA")
        # Fiber plate and ink dropout make the image feel printed on aged stock.
        fiber = Image.new("RGBA", self.size, (27, 21, 11, 0))
        fiber_alpha = self.fiber_plate.point(lambda p: max(0, round((244 - p) * self.definition["film"]["paper_fiber_strength"] * 5.2)))
        fiber.putalpha(fiber_alpha)
        image = Image.alpha_composite(image, fiber)
        rng = np.random.default_rng(self.seed + 200000 + frame_index // 2)
        marks = Image.new("RGBA", self.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(marks)
        for _ in range(28):
            x = int(rng.integers(15, self.size[0] - 15)); y = int(rng.integers(15, self.size[1] - 15))
            if rng.random() < .68:
                draw.ellipse((x, y, x + int(rng.integers(1, 5)), y + int(rng.integers(1, 5))), fill=(235, 209, 137, int(rng.integers(8, 30))))
            else:
                draw.line((x, y, x + int(rng.integers(-18, 19)), y + int(rng.integers(8, 42))), fill=(4, 7, 6, int(rng.integers(12, 38))), width=1)
        # Selected stress frames receive shaped yellow/teal print separation.
        if stress > .7 and frame_index % self.definition["film"]["selected_registration_interval"] == 0:
            separated = image.copy()
            alpha = Image.new("L", self.size, 0)
            ImageDraw.Draw(alpha).ellipse((360, 240, 710, 930), fill=34)
            teal = Image.new("RGBA", self.size, self.palette["teal"] + (0,)); teal.putalpha(ImageChops.offset(alpha, -2, 1))
            yellow = Image.new("RGBA", self.size, self.palette["yellow"] + (0,)); yellow.putalpha(ImageChops.offset(alpha, 3, -1))
            separated = Image.alpha_composite(separated, teal); separated = Image.alpha_composite(separated, yellow)
            image = separated
        return Image.alpha_composite(image, marks).convert("RGB")
