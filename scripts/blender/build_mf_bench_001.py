#!/usr/bin/env python3
"""Build the new MF-BENCH-001 empty-lab scene and render stills or frames."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector


STARTED = time.monotonic()


def arguments() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--mode", choices=("stills", "frames", "lamp-proof", "lamp-debug"), required=True)
    parser.add_argument("--performance", required=True)
    parser.add_argument("--scene-output")
    return parser.parse_args(values)


A = arguments()
ROOT = Path.cwd().resolve()
CONFIG_PATH = (ROOT / A.manifest).resolve()
CONFIG_DEFINITION = json.loads(CONFIG_PATH.read_text())
BASE_CONFIG_PATH = None
if CONFIG_DEFINITION.get("base_manifest"):
    BASE_CONFIG_PATH = (ROOT / CONFIG_DEFINITION["base_manifest"]).resolve()
    CONFIG = json.loads(BASE_CONFIG_PATH.read_text())
    for config_key, config_value in CONFIG_DEFINITION.items():
        if config_key not in ("base_manifest", "frozen_invariants"):
            CONFIG[config_key] = config_value
else:
    CONFIG = CONFIG_DEFINITION
SHOT = CONFIG["shot"]
FPS = SHOT["fps"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frame(seconds: float) -> int:
    return max(1, round(seconds * FPS) + 1)


def key(value, data_path: str, seconds: float) -> None:
    value.keyframe_insert(data_path=data_path, frame=frame(seconds))


def material(name: str, color: tuple[float, float, float, float], metallic: float = 0.0,
             roughness: float = 0.6, emission: tuple[float, float, float, float] | None = None,
             emission_strength: float = 0.0, alpha: float = 1.0) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    result.diffuse_color = (*color[:3], alpha)
    result.use_nodes = True
    node = result.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = (*color[:3], 1.0)
    node.inputs["Metallic"].default_value = metallic
    node.inputs["Roughness"].default_value = roughness
    if "Coat Weight" in node.inputs:
        node.inputs["Coat Weight"].default_value = 0.12
    if emission:
        node.inputs["Emission Color"].default_value = emission
        node.inputs["Emission Strength"].default_value = emission_strength
    if alpha < 1.0:
        node.inputs["Alpha"].default_value = alpha
        result.surface_render_method = "DITHERED"
    return result


def worn_material(name: str, dark: tuple[float, float, float, float], light: tuple[float, float, float, float],
                  metallic: float, roughness: float) -> bpy.types.Material:
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    nodes = result.node_tree.nodes
    links = result.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 5.5
    noise.inputs["Detail"].default_value = 4.0
    noise.inputs["Roughness"].default_value = 0.72
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = dark
    ramp.color_ramp.elements[1].color = light
    ramp.color_ramp.elements[0].position = 0.28
    ramp.color_ramp.elements[1].position = 0.76
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.12
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return result


def assign(obj: bpy.types.Object, mat: bpy.types.Material) -> bpy.types.Object:
    obj.data.materials.append(mat)
    return obj


def cube(name: str, location, scale, mat, rotation=(0.0, 0.0, 0.0), bevel=0.08) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.scale = (scale[0] / 2, scale[1] / 2, scale[2] / 2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        modifier = obj.modifiers.new("worn_edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    return assign(obj, mat)


def cylinder(name: str, location, radius: float, depth: float, mat, vertices=48,
             rotation=(0.0, 0.0, 0.0)) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    bevel = obj.modifiers.new("machined_edge", "BEVEL")
    bevel.width = 0.05
    bevel.segments = 2
    return assign(obj, mat)


def torus(name: str, location, major: float, minor: float, mat) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=48, minor_segments=10, location=location)
    obj = bpy.context.object
    obj.name = name
    return assign(obj, mat)


def sphere(name: str, location, radius: float, mat, segments=32) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=16, radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    return assign(obj, mat)


def emission_input(mat: bpy.types.Material):
    return mat.node_tree.nodes.get("Principled BSDF").inputs["Emission Strength"]


def animate_emission(mat: bpy.types.Material, points: list[tuple[float, float]]) -> None:
    socket = emission_input(mat)
    for seconds, strength in points:
        socket.default_value = strength
        socket.keyframe_insert("default_value", frame=frame(seconds))


def text_object(name: str, body: str, location, size: float, mat) -> bpy.types.Object:
    bpy.ops.object.text_add(location=location, rotation=(math.radians(90), 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.data.body = body
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = 0.012
    obj.data.bevel_depth = 0.006
    return assign(obj, mat)


def look_at(camera: bpy.types.Object, target: bpy.types.Object) -> None:
    constraint = camera.constraints.new(type="TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"


for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
    for block in list(datablocks):
        if block.users == 0:
            datablocks.remove(block)

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = SHOT["resolution"]
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = round(SHOT["runtime_seconds"] * FPS)
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.color_depth = "8"
scene.render.image_settings.compression = 35
scene.render.use_file_extension = True
scene.world.use_nodes = True
lighting = CONFIG.get("dormant_lighting", {})
world_lighting = lighting.get("world", {"color": [0.055, 0.095, 0.080, 1], "strength": 0.38})
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = world_lighting["color"]
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = world_lighting["strength"]

# Palette and surface system are derived from the cover without embedding it.
iron = worn_material("sooted_iron", (0.009, 0.017, 0.016, 1), (0.055, 0.095, 0.085, 1), 0.72, 0.67)
steel = worn_material("worn_green_steel", (0.012, 0.035, 0.032, 1), (0.045, 0.16, 0.13, 1), 0.63, 0.61)
brass = worn_material("aged_brass", (0.09, 0.045, 0.008, 1), (0.42, 0.25, 0.045, 1), 0.82, 0.48)
cream = material("aged_gauge_face", (0.42, 0.35, 0.19, 1), metallic=0.08, roughness=0.76)
glass = material("dirty_containment_glass", (0.025, 0.10, 0.09, 1), metallic=0.0, roughness=0.19, alpha=0.27)
dark_glass = material("gauge_glass", (0.01, 0.025, 0.021, 1), roughness=0.22, alpha=0.34)
needle_red = material("needle_red", (0.43, 0.025, 0.008, 1), metallic=0.35, roughness=0.55)
pilot = material("unexplained_pilot_red", (0.12, 0.003, 0.001, 1), emission=(1.0, 0.018, 0.002, 1), emission_strength=0.03)
relay_amber = [material(f"relay_amber_{i}", (0.11, 0.025, 0.002, 1), emission=(1.0, 0.24, 0.012, 1), emission_strength=0.0) for i in range(5)]
ring_lights = [material(f"containment_lamp_{i}", (0.08, 0.02, 0.002, 1), emission=(1.0, 0.08, 0.006, 1), emission_strength=0.0) for i in range(9)]
energy = material("contained_unknown_energy", (0.12, 0.08, 0.003, 1), emission=(1.0, 0.62, 0.05, 1), emission_strength=0.0)
title_mat = material("pulp_title_ink", (0.002, 0.003, 0.002, 1), emission=(1.0, 0.52, 0.025, 1), emission_strength=0.0)
support_mat = material("warning_copy", (0.002, 0.003, 0.002, 1), emission=(0.82, 0.03, 0.006, 1), emission_strength=0.0)

# Empty room shell: floor, rear wall, purposeful service ribs and threshold.
cube("RoomFloor", (0, 1.8, -0.28), (11.8, 15.0, 0.55), iron, bevel=0.03)
cube("RearWall", (0, 5.6, 4.7), (11.8, 0.45, 9.8), steel, bevel=0.03)
cube("InspectionThreshold", (0, -4.6, 0.18), (11.8, 1.0, 0.36), iron, bevel=0.04)
for x in (-5.25, 5.25):
    cube(f"WallRib_{x}", (x, 5.28, 4.8), (0.38, 0.48, 9.6), brass, bevel=0.04)
for z in (2.0, 4.8, 7.6):
    cube(f"RearBrace_{z}", (0, 5.25, z), (10.2, 0.42, 0.24), iron, bevel=0.03)
for index, z in enumerate((8.62, 8.88, 9.12)):
    cylinder(f"OverheadService_{index}", (0.35, 5.02, z), 0.10 + index * 0.015, 9.0, brass, vertices=24, rotation=(0, math.radians(90), 0))

# Hero: a self-starting induction chamber with contained motion and mounted lamps.
hero_x, hero_y = 0.85, 1.25
lamp_definition = CONFIG["upper_ring_lamps"]
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(hero_x, hero_y, 0.0))
reactor_root = bpy.context.object
reactor_root.name = "ReactorRoot"
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(hero_x, hero_y, 6.82))
upper_ring = bpy.context.object
upper_ring.name = "UpperRingAssembly"
upper_ring.parent = reactor_root
upper_ring.location = (0.0, 0.0, 6.82)
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0.0, 0.0, 0.0))
lamp_arc_root = bpy.context.object
lamp_arc_root.name = "LampArcRoot"
lamp_arc_root.parent = upper_ring
lamp_arc_root.location = (0.0, 0.0, 0.0)
cylinder("ChamberFoundation", (hero_x, hero_y, 0.62), 2.0, 0.75, iron)
cylinder("ChamberLowerMachine", (hero_x, hero_y, 1.35), 1.62, 1.05, steel)
cylinder("ContainmentGlass", (hero_x, hero_y, 4.15), 1.38, 5.0, glass, vertices=64)
upper_cap = cylinder("UpperCap", (hero_x, hero_y, 6.82), lamp_definition["host_outer_radius"], 0.52, iron)
upper_cap.parent = upper_ring
upper_cap.matrix_parent_inverse = upper_ring.matrix_world.inverted()
for index, z in enumerate((1.75, 2.35, 5.95, 6.48)):
    torus(f"ContainmentBand_{index}", (hero_x, hero_y, z), 1.49, 0.105, brass)
protected_bolts = []
for index in range(12):
    angle = math.tau * index / 12
    x = hero_x + math.cos(angle) * 1.70
    y = hero_y + math.sin(angle) * 1.70
    bolt = cylinder(f"CapBolt_{index}", (x, y, 6.55), 0.075, 0.35, brass, vertices=16)
    bolt.parent = upper_ring
    bolt.matrix_parent_inverse = upper_ring.matrix_world.inverted()
    protected_bolts.append(bolt)

# MF-020R2: one ring-local arc and one shared geometry definition drive every lamp.
lamp_count = lamp_definition["count"]
lamp_radius = lamp_definition["radius"]
bulb_radius = lamp_definition["bulb_radius"]
start_angle = math.radians(lamp_definition["start_angle_degrees"])
end_angle = math.radians(lamp_definition["end_angle_degrees"])
elevation = lamp_definition["elevation_offset"]

bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=bulb_radius, location=(0, 0, 0))
master_bulb = bpy.context.object
master_bulb.name = "UpperRingLampMasterBulb"
bulb_mesh = master_bulb.data
bulb_mesh.name = "UpperRingLampSharedBulbMesh"
bulb_mesh.materials.append(ring_lights[0])
bpy.data.objects.remove(master_bulb, do_unlink=True)
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=lamp_definition["socket_radius"], depth=lamp_definition["socket_depth"], location=(0, 0, 0))
master_socket = bpy.context.object
master_socket.name = "UpperRingLampMasterSocket"
socket_mesh = master_socket.data
socket_mesh.name = "UpperRingLampSharedSocketMesh"
socket_mesh.materials.append(brass)
bpy.data.objects.remove(master_socket, do_unlink=True)

lamp_roots = []
lamp_bulbs = []
lamp_sockets = []
for index, mat in enumerate(ring_lights):
    t = index / (lamp_count - 1) if lamp_count > 1 else 0.5
    angle = start_angle + (end_angle - start_angle) * t
    root = bpy.data.objects.new(f"UpperRingLamp_{index:02d}", None)
    bpy.context.collection.objects.link(root)
    root.empty_display_type = "PLAIN_AXES"
    root.parent = lamp_arc_root
    root.location = (math.cos(angle) * lamp_radius, math.sin(angle) * lamp_radius, elevation)
    root.rotation_euler.z = angle
    socket = bpy.data.objects.new(f"UpperRingLamp_{index:02d}_Socket", socket_mesh)
    bpy.context.collection.objects.link(socket)
    socket.parent = root
    # The shared socket's axis points radially inward from the bulb into the cap.
    socket.rotation_euler.y = math.radians(90)
    socket.location = (-lamp_definition["socket_depth"] * 0.48, 0.0, 0.0)
    bulb = bpy.data.objects.new(f"UpperRingLamp_{index:02d}_BulbGlow", bulb_mesh)
    bpy.context.collection.objects.link(bulb)
    bulb.parent = root
    bulb.location = (0.0, 0.0, 0.0)
    bulb.material_slots[0].link = "OBJECT"
    bulb.material_slots[0].material = mat
    lamp_roots.append(root)
    lamp_bulbs.append(bulb)
    lamp_sockets.append(socket)
for index, z in enumerate((2.2, 2.8, 3.4, 4.0, 4.6, 5.2, 5.8)):
    torus(f"InductionCoil_{index}", (hero_x, hero_y, z), 0.92, 0.038, energy)
sphere("ContainedProcessCore", (hero_x, hero_y, 4.05), 0.62, energy, segments=40)

# Physical energy filaments remain inside the chamber.
for filament in range(7):
    curve = bpy.data.curves.new(f"EnergyFilament_{filament}", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.018 + (filament % 2) * 0.007
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(17)
    for step in range(18):
        z = 2.15 + step * 0.225
        radius = 0.23 + 0.06 * math.sin(step * 0.9 + filament)
        angle = filament * 0.91 + step * 0.54
        spline.points[step].co = (hero_x + math.cos(angle) * radius, hero_y + math.sin(angle) * radius, z, 1)
    curve.materials.append(energy)
    obj = bpy.data.objects.new(f"EnergyFilament_{filament}", curve)
    bpy.context.collection.objects.link(obj)

# Secondary witness console: no operator control moves; it merely records the event.
cube("WitnessConsoleBody", (-2.95, -0.25, 1.48), (2.45, 1.38, 2.65), steel, rotation=(math.radians(-6), 0, 0), bevel=0.13)
cube("WitnessConsoleFace", (-2.95, -1.02, 1.68), (2.15, 0.16, 1.85), iron, rotation=(math.radians(-6), 0, 0), bevel=0.07)
gauge_pivots = []
for index, x in enumerate((-3.45, -2.75)):
    cylinder(f"GaugeFace_{index}", (x, -1.15, 2.02), 0.42, 0.10, cream, vertices=48, rotation=(math.radians(90), 0, 0))
    cylinder(f"GaugeGlass_{index}", (x, -1.22, 2.02), 0.39, 0.035, dark_glass, vertices=48, rotation=(math.radians(90), 0, 0))
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(x, -1.29, 2.02))
    pivot = bpy.context.object
    pivot.name = f"GaugeNeedlePivot_{index}"
    needle = cube(f"GaugeNeedle_{index}", (x, -1.31, 2.25), (0.055, 0.045, 0.48), needle_red, bevel=0.012)
    needle.parent = pivot
    gauge_pivots.append(pivot)
pilot_lamp = sphere("ImpossiblePilotSignal", (-3.43, -1.20, 1.16), 0.16, pilot, segments=24)
for index in range(4):
    cylinder(f"ConsoleFastener_{index}", (-3.75 + index * 0.54, -1.16, 0.77), 0.055, 0.12, brass, vertices=12, rotation=(math.radians(90), 0, 0))

# Tertiary relay spine: each mounted relay responds to the previous event.
cube("RelaySpine", (4.25, 3.65, 4.15), (1.15, 0.72, 5.25), iron, bevel=0.08)
for index, mat in enumerate(relay_amber):
    z = 2.55 + index * 0.78
    cube(f"RelayBlock_{index}", (4.25, 3.18, z), (0.76, 0.22, 0.42), steel, bevel=0.04)
    sphere(f"RelayLamp_{index}", (4.25, 3.00, z), 0.11, mat, segments=20)

# A real pressure vent gives the later atmosphere a physical origin.
cylinder("PressureVent", (2.45, 1.28, 6.23), 0.19, 1.10, brass, vertices=24, rotation=(0, math.radians(90), 0))
for index in range(3):
    steam_mat = material(f"steam_{index}", (0.26, 0.32, 0.27, 1), emission=(0.16, 0.22, 0.17, 1), emission_strength=0.0, alpha=0.14)
    cloud = sphere(f"VentSteam_{index}", (2.9 + index * 0.42, 1.28, 6.22 + index * 0.18), 0.32 + index * 0.12, steam_mat, segments=20)
    cloud.scale = (0.15, 0.15, 0.15)
    key(cloud, "scale", 10.0 + index * 0.12)
    cloud.scale = (1.0 + index * 0.20, 0.62, 0.82 + index * 0.18)
    key(cloud, "scale", 10.8 + index * 0.16)
    cloud.location.x += 0.8 + index * 0.3
    cloud.location.z += 0.35 + index * 0.24
    key(cloud, "location", 11.8 + index * 0.18)
    cloud.scale = (0.04, 0.04, 0.04)
    key(cloud, "scale", 13.2 + index * 0.12)
    animate_emission(steam_mat, [(9.9, 0.0), (10.25 + index * 0.12, 0.5), (12.0, 0.08)])

# Lighting progression tells the story rather than exposing the room at once.
bpy.ops.object.light_add(type="AREA", location=(-3.4, -3.6, 5.9))
moon = bpy.context.object
moon.name = "ColdInspectionFill"
inspection_fill = lighting.get("inspection_fill", {"energy": 105, "color": [0.035, 0.15, 0.13]})
moon.data.energy = inspection_fill["energy"]
moon.data.color = inspection_fill["color"]
moon.data.shape = "DISK"
moon.data.size = 4.0
moon.rotation_euler = (math.radians(24), 0, math.radians(-12))
bpy.ops.object.light_add(type="POINT", location=(-2.4, -4.0, 5.2))
room_fill = bpy.context.object
room_fill.name = "DormantRoomReadability"
room_readability = lighting.get("room_readability", {"energy": 980, "color": [0.035, 0.16, 0.13]})
room_fill.data.color = room_readability["color"]
room_fill.data.energy = room_readability["energy"]
room_fill.data.shadow_soft_size = 3.2
service_practical = lighting.get("service_practical")
if service_practical:
    bpy.ops.object.light_add(type="POINT", location=service_practical["location"])
    service_light = bpy.context.object
    service_light.name = "DimAmberServicePractical"
    service_light.data.color = service_practical["color"]
    service_light.data.energy = service_practical["energy"]
    service_light.data.shadow_soft_size = service_practical["shadow_soft_size"]
bpy.ops.object.light_add(type="POINT", location=(hero_x, hero_y - 0.25, 4.2))
hero_light = bpy.context.object
hero_light.name = "ContainedProcessLight"
hero_light.data.color = (1.0, 0.42, 0.025)
hero_light.data.energy = 0.0
hero_light.data.shadow_soft_size = 1.1
for seconds, strength in ((0.0, 0.0), (7.8, 0.0), (8.5, 300.0), (12.4, 620.0), (15.2, 880.0), (20.0, 760.0)):
    hero_light.data.energy = strength
    hero_light.data.keyframe_insert("energy", frame=frame(seconds))

# Causal animation: signal -> real-pivot gauges -> relay chain -> lamps -> contained process.
animate_emission(pilot, [(0.0, 0.03), (0.72, 0.03), (0.82, 8.0), (1.04, 0.8), (1.32, 5.5), (20.0, 3.5)])
for index, pivot in enumerate(gauge_pivots):
    pivot.rotation_euler.y = math.radians(-48 + index * 6)
    key(pivot, "rotation_euler", 0.0)
    key(pivot, "rotation_euler", 2.18 + index * 0.18)
    pivot.rotation_euler.y = math.radians(18 + index * 12)
    key(pivot, "rotation_euler", 2.82 + index * 0.22)
    pivot.rotation_euler.y = math.radians(52 - index * 8)
    key(pivot, "rotation_euler", 12.8)
for index, mat in enumerate(relay_amber):
    on = 3.42 + index * 0.38
    animate_emission(mat, [(0.0, 0.0), (on - 0.04, 0.0), (on, 6.5), (on + 0.22, 2.2), (20.0, 1.5)])
for index, mat in enumerate(ring_lights):
    on = 5.95 + index * 0.16
    animate_emission(mat, [(0.0, 0.0), (on - 0.08, 0.0), (on, 8.0), (20.0, 4.3)])
animate_emission(energy, [(0.0, 0.0), (7.95, 0.0), (8.35, 0.9), (10.0, 1.8), (12.4, 3.2), (15.2, 4.8), (20.0, 4.1)])

# Final in-world identity occupies protected negative space and remains subordinate until earned.
title = text_object("UnknownProcessIdentity", "UNKNOWN PROCESS", (0.85, 5.02, 8.18), 0.54, title_mat)
support = text_object("NoOperatorPresent", "NO OPERATOR PRESENT", (0.85, 5.00, 7.72), 0.25, support_mat)
animate_emission(title_mat, [(0.0, 0.0), (15.35, 0.0), (15.55, 5.5), (20.0, 4.4)])
animate_emission(support_mat, [(0.0, 0.0), (16.05, 0.0), (16.35, 3.2), (20.0, 2.6)])

# Single restrained camera shot preserves spatial continuity and emptiness.
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0.22, 1.25, 4.10))
target = bpy.context.object
target.name = "HeroAim"
bpy.ops.object.camera_add(location=(-0.55, -14.8, 5.45))
camera = bpy.context.object
camera.name = "EmptyLabWitnessCamera"
camera.data.lens = SHOT["lens_mm"]
camera.data.sensor_width = 36
camera.data.dof.use_dof = True
camera.data.dof.focus_object = target
camera.data.dof.aperture_fstop = 6.3
scene.camera = camera
look_at(camera, target)
key(camera, "location", 0.0)
camera.location = (0.08, -13.15, 5.28)
key(camera, "location", 10.0)
camera.location = (0.48, -11.85, 5.10)
key(camera, "location", 20.0)

# Fixed close-up camera isolates alignment from activation and from the production dolly.
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(hero_x, hero_y, 6.82))
proof_target = bpy.context.object
proof_target.name = "UpperRingProofAim"
bpy.ops.object.camera_add(location=(hero_x, -5.65, 7.58))
proof_camera = bpy.context.object
proof_camera.name = "UpperRingFixedProofCamera"
proof_camera.data.lens = 35.0
proof_camera.data.sensor_width = 36
proof_camera.data.dof.use_dof = False
look_at(proof_camera, proof_target)

if A.mode == "lamp-debug":
    debug_mat = material("LampArcDebug", (0.01, 0.18, 0.20, 1), emission=(0.02, 0.9, 1.0, 1), emission_strength=5.0)
    arc_curve = bpy.data.curves.new("LampArcDebugPath", "CURVE")
    arc_curve.dimensions = "3D"
    arc_curve.bevel_depth = 0.012
    arc_curve.bevel_resolution = 2
    spline = arc_curve.splines.new("POLY")
    steps = 64
    spline.points.add(steps)
    for step in range(steps + 1):
        t = step / steps
        angle = start_angle + (end_angle - start_angle) * t
        spline.points[step].co = (math.cos(angle) * lamp_radius, math.sin(angle) * lamp_radius, elevation, 1)
    arc_curve.materials.append(debug_mat)
    arc_object = bpy.data.objects.new("LampArcDebugPath", arc_curve)
    bpy.context.collection.objects.link(arc_object)
    arc_object.parent = lamp_arc_root
    center_marker = sphere("LampArcCenterMarker", (0, 0, 0), 0.055, debug_mat, segments=16)
    center_marker.parent = lamp_arc_root
    center_marker.location = (0.0, 0.0, elevation)
    for index, root in enumerate(lamp_roots):
        marker = sphere(f"LampAnchorDebug_{index:02d}", (0, 0, 0), 0.028, debug_mat, segments=12)
        marker.parent = root
        marker.location = (0.0, 0.0, 0.0)

# Subtle bloom supports practical lamps without turning the scene into neon.
scene.use_nodes = True
compositor = bpy.data.node_groups.new("MF_BENCH_BoundedGlow", "CompositorNodeTree")
scene.compositing_node_group = compositor
nodes = compositor.nodes
links = compositor.links
nodes.clear()
layers = nodes.new("CompositorNodeRLayers")
glare = nodes.new("CompositorNodeGlare")
glare.inputs["Type"].default_value = "Bloom"
glare.inputs["Quality"].default_value = "High"
glare.inputs["Threshold"].default_value = 1.0
glare.inputs["Strength"].default_value = 0.48
glare.inputs["Size"].default_value = 0.58
compositor.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
composite = nodes.new("NodeGroupOutput")
links.new(layers.outputs["Image"], glare.inputs["Image"])
links.new(glare.outputs["Image"], composite.inputs["Image"])

build_ms = round((time.monotonic() - STARTED) * 1000)
output = Path(A.output_dir).resolve()
output.mkdir(parents=True, exist_ok=True)
builder_path = Path(__file__).resolve()
template_path = (ROOT / CONFIG["render"]["blender"]["template"]).resolve()
fingerprint = {
    "config_sha256": sha256(CONFIG_PATH),
    "base_config_sha256": sha256(BASE_CONFIG_PATH) if BASE_CONFIG_PATH else None,
    "builder_sha256": sha256(builder_path),
    "template_sha256": sha256(template_path),
    "seed": CONFIG["seed"],
    "blender_version": bpy.app.version_string,
    "engine": scene.render.engine,
    "resolution": SHOT["resolution"],
    "fps": FPS,
    "frames": scene.frame_end
}
bpy.context.view_layer.update()
lamp_records = []
for index, (root, bulb, socket) in enumerate(zip(lamp_roots, lamp_bulbs, lamp_sockets)):
    lamp_records.append({
        "index": index,
        "angle_degrees": round(math.degrees(start_angle + (end_angle - start_angle) * index / (lamp_count - 1)), 6),
        "local_position": [round(value, 9) for value in root.location],
        "world_position": [round(value, 9) for value in root.matrix_world.translation],
        "local_rotation_euler": [round(value, 9) for value in root.rotation_euler],
        "scale": [round(value, 9) for value in root.scale],
        "parent": root.parent.name if root.parent else None,
        "bulb_parent": bulb.parent.name if bulb.parent else None,
        "bulb_local_position": [round(value, 9) for value in bulb.location],
        "glow_anchor_delta": round(bulb.location.length, 12),
        "shared_bulb_mesh": bulb.data.name,
        "shared_socket_mesh": socket.data.name,
    })
positions = [Vector(item["local_position"]) for item in lamp_records]
spacing = [(positions[index + 1] - positions[index]).length for index in range(len(positions) - 1)]
minimum_allowed = 2 * bulb_radius + lamp_definition["minimum_spacing_margin"]
overlap_count = sum(distance <= minimum_allowed for distance in spacing)
radial_deviations = [abs(math.hypot(item["local_position"][0], item["local_position"][1]) - lamp_radius) for item in lamp_records]
bpy.context.view_layer.update()
protected_centers = [bolt.matrix_world.translation.copy() for bolt in protected_bolts]
protected_clearance = bulb_radius + lamp_definition["protected_detail_radius"] + 0.03
protected_intersections = 0
for root in lamp_roots:
    for bolt_center in protected_centers:
        if (root.matrix_world.translation - bolt_center).length <= protected_clearance:
            protected_intersections += 1
position_samples = {}
activation_samples = {}
for label, seconds in (("off", 5.70), ("half", 6.55), ("all", 7.50), ("camera_end", 20.0)):
    scene.frame_set(frame(seconds))
    bpy.context.view_layer.update()
    position_samples[label] = [[round(value, 9) for value in root.matrix_world.translation] for root in lamp_roots]
    strengths = [round(mat.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value, 9) for mat in ring_lights]
    activation_samples[label] = {
        "emission_strengths": strengths,
        "active_count": sum(value > 0.1 for value in strengths),
    }
position_drift = max((Vector(position_samples[state][index]) - Vector(position_samples["off"][index])).length for state in ("half", "all", "camera_end") for index in range(lamp_count))
contract = {
    "slice": "MF-BENCH-001",
    "scene_id": SHOT["id"],
    "backend": "BLENDER",
    "source_strategy": CONFIG["visual_source"]["configured_strategy"],
    "render_fingerprint": fingerprint,
    "camera": {"name": camera.name, "lens_mm": camera.data.lens, "move": SHOT["camera_move"], "single_shot": True},
    "proof_camera": {
        "name": proof_camera.name,
        "lens_mm": proof_camera.data.lens,
        "location": [round(value, 9) for value in proof_camera.location],
        "rotation_euler": [round(value, 9) for value in proof_camera.rotation_euler],
        "animated": bool(proof_camera.animation_data and proof_camera.animation_data.action),
    },
    "objects": {"hero": "self_starting_induction_chamber", "console": "unattended_witness_console", "gauges": 2, "relays": 5, "ring_lamps": 9, "operator_count": 0},
    "upper_ring_lamps": {
        "placement": lamp_definition,
        "placement_formula": "angle=lerp(start_angle,end_angle,index/(count-1)); local=(cos(angle)*radius,sin(angle)*radius,elevation)",
        "hierarchy": ["ReactorRoot", "UpperRingAssembly", "LampArcRoot", "UpperRingLamp_NN", "BulbGlow"],
        "master_geometry": {"bulb_mesh": bulb_mesh.name, "socket_mesh": socket_mesh.name},
        "records": lamp_records,
        "spacing": {
            "center_distances": [round(value, 9) for value in spacing],
            "minimum_allowed": round(minimum_allowed, 9),
            "minimum_observed": round(min(spacing), 9),
            "maximum_observed": round(max(spacing), 9),
            "maximum_variation": round(max(spacing) - min(spacing), 12)
        },
        "maximum_radial_deviation": round(max(radial_deviations), 12),
        "overlap_count": overlap_count,
        "protected_detail_intersection_count": protected_intersections,
        "maximum_glow_anchor_delta": round(max(item["glow_anchor_delta"] for item in lamp_records), 12),
        "position_samples": position_samples,
        "activation_samples": activation_samples,
        "maximum_position_drift": round(position_drift, 12),
        "placement_animation_channels": 0,
        "screen_space_offsets": 0,
        "per_lamp_manual_offsets": 0,
    },
    "causality": {"pilot_precedes_gauge": True, "gauge_precedes_relays": True, "relays_precede_containment": True, "containment_precedes_energy": True, "energy_precedes_title": True},
    "text": CONFIG["text"],
    "reference_embedded": False
}
(output / "scene-contract.json").write_text(json.dumps(contract, indent=2) + "\n")
if A.scene_output:
    scene_path = Path(A.scene_output).resolve()
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(scene_path))

render_started = time.monotonic()
rendered = 0
if A.mode == "stills":
    for seconds, label in zip(CONFIG["stages"]["blockout"]["seconds"], CONFIG["stages"]["blockout"]["labels"]):
        scene.frame_set(frame(seconds))
        scene.render.filepath = str(output / f"{label}.png")
        bpy.ops.render.render(write_still=True)
        rendered += 1
elif A.mode == "lamp-proof":
    scene.camera = proof_camera
    for seconds, label in ((5.70, "lamps-off"), (6.55, "lamps-half"), (7.50, "lamps-all")):
        scene.frame_set(frame(seconds))
        scene.render.filepath = str(output / f"{label}.png")
        bpy.ops.render.render(write_still=True)
        rendered += 1
elif A.mode == "lamp-debug":
    scene.camera = proof_camera
    scene.frame_set(frame(7.50))
    scene.render.filepath = str(output / "lamp-arc-overlay.png")
    bpy.ops.render.render(write_still=True)
    rendered += 1
else:
    # Resume is deliberately unsupported: a frame sequence is one immutable render fingerprint.
    if any(output.glob("frame-*.png")):
        raise SystemExit("MF_BENCH_FRAME_SEQUENCE_ALREADY_EXISTS")
    for index in range(scene.frame_end):
        scene.frame_set(index + 1)
        scene.render.filepath = str(output / f"frame-{index:04d}.png")
        bpy.ops.render.render(write_still=True)
        rendered += 1

performance = {
    "mode": A.mode,
    "build_ms": build_ms,
    "render_ms": round((time.monotonic() - render_started) * 1000),
    "total_ms": round((time.monotonic() - STARTED) * 1000),
    "rendered": rendered,
    "engine": scene.render.engine,
    "device": "CPU_HEADLESS_DEFAULT",
    "render_fingerprint": fingerprint
}
performance_path = Path(A.performance).resolve()
performance_path.parent.mkdir(parents=True, exist_ok=True)
performance_path.write_text(json.dumps(performance, indent=2) + "\n")
print("MF_BENCH_001_RENDER_OK " + json.dumps(performance, sort_keys=True))
