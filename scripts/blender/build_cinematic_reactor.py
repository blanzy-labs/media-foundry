"""Build staged MF-020 Blender-native cinematic reactor evidence and final frames."""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--stage", choices=("blockout", "detail", "lighting", "fx", "final"), required=True)
    parser.add_argument("--mode", choices=("stills", "frames"), required=True)
    parser.add_argument("--performance", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--scene-output")
    return parser.parse_args(values)


A = parse_args()
ROOT = Path(bpy.path.abspath("//")).resolve().parents[1]
CONFIG = json.loads((ROOT / A.manifest).read_text())
SHOT = CONFIG["shot"]
FPS = SHOT["fps"]
random.seed(CONFIG["seed"])
STARTED = time.monotonic()
BUILD_STARTED = time.monotonic()
DETAILED = A.stage != "blockout"
DRAMATIC = A.stage in ("lighting", "fx", "final")
WITH_FX = A.stage in ("fx", "final")


def frame(seconds):
    return round(seconds * FPS) + 1


def coll(name):
    value = bpy.data.collections.get(name)
    if value is None:
        value = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(value)
    return value


def own(obj, name):
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    coll(name).objects.link(obj)
    return obj


def material(name, color, metallic=0.0, rough=.5, emission=None, strength=0.0, transmission=0.0):
    value = bpy.data.materials.new(name)
    value.use_nodes = True
    bsdf = value.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Transmission Weight"].default_value = transmission
    if transmission > 0:
        bsdf.inputs["Alpha"].default_value = .22
        bsdf.inputs["IOR"].default_value = 1.08
        value.surface_render_method = "DITHERED"
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = strength
    value.diffuse_color = (*color, 1)
    return value


def weathered(name, color, metallic, rough, scale=5.0, bump=.16):
    value = material(name, color, metallic, rough)
    nodes = value.node_tree.nodes
    links = value.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 4.0
    noise.inputs["Roughness"].default_value = .72
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = .24
    ramp.color_ramp.elements[0].color = (.12, .12, .12, 1)
    ramp.color_ramp.elements[1].position = .78
    ramp.color_ramp.elements[1].color = (.72, .72, .72, 1)
    bump_node = nodes.new("ShaderNodeBump")
    bump_node.inputs["Strength"].default_value = bump
    bump_node.inputs["Distance"].default_value = .08
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Roughness"])
    links.new(noise.outputs["Fac"], bump_node.inputs["Height"])
    links.new(bump_node.outputs["Normal"], bsdf.inputs["Normal"])
    return value


def emission_strength(value):
    return value.node_tree.nodes.get("Principled BSDF").inputs["Emission Strength"]


def animate(socket, values):
    for when, value in values:
        socket.default_value = value
        socket.keyframe_insert("default_value", frame=when)


def cube(name, location, scale, mat, owner="ARCHITECTURE", bevel=.05):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    own(obj, owner)
    if bevel:
        mod = obj.modifiers.new("ShotFacingEdgeWear", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return obj


def cyl(name, location, radius, depth, mat, owner="REACTOR", rotation=(0, 0, 0), vertices=48, bevel=.035):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    own(obj, owner)
    if bevel:
        mod = obj.modifiers.new("MachinedEdge", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return obj


def sphere(name, location, radius, mat, owner="FX", segments=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=12, radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    own(obj, owner)
    return obj


def torus(name, location, major, minor, mat, owner="REACTOR"):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=64, minor_segments=12, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    own(obj, owner)
    return obj


def path(name, points, mat, bevel, owner="ARCHITECTURE", cyclic=False):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.bevel_depth = bevel
    data.bevel_resolution = 2
    spline = data.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for point, value in zip(spline.points, points):
        point.co = (*value, 1)
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, data)
    coll(owner).objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def point_light(name, location, color, energy, size, owner="LIGHTING"):
    bpy.ops.object.light_add(type="POINT", location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.color = color
    obj.data.energy = energy
    obj.data.shadow_soft_size = size
    own(obj, owner)
    return obj


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def volume_material(name, color, density):
    value = bpy.data.materials.new(name)
    value.use_nodes = True
    nodes = value.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    volume = nodes.new("ShaderNodeVolumePrincipled")
    volume.inputs["Color"].default_value = (*color, 1)
    volume.inputs["Density"].default_value = density
    value.node_tree.links.new(volume.outputs["Volume"], output.inputs["Volume"])
    return value, volume.inputs["Density"]


for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for name in ("ARCHITECTURE", "REACTOR", "CONSOLE", "LIGHTING", "FX", "CAMERA"):
    coll(name)

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.eevee.taa_render_samples = int(CONFIG["render"]["blender"]["samples"])
scene.render.resolution_x, scene.render.resolution_y = SHOT["resolution"]
scene.render.resolution_percentage = 100
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = round(SHOT["runtime_seconds"] * FPS)
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.image_settings.color_depth = "8"
scene.render.film_transparent = False
scene.render.filepath = str(Path(A.output_dir).resolve())
scene.view_settings.look = "AgX - Medium High Contrast"
scene["mf020_seed"] = CONFIG["seed"]
scene["mf020_stage"] = A.stage
scene["mf020_shot_id"] = SHOT["id"]
scene["mf020_stage_order"] = json.dumps(CONFIG["stages"]["order"])

world = scene.world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (.002, .008, .010, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = .11 if DRAMATIC else .18

if DETAILED:
    steel = weathered("MF020_AGED_STEEL", (.018, .065, .068), .78, .52, 6.5, .18)
    dark = weathered("MF020_BLACKENED_METAL", (.006, .012, .014), .82, .64, 8.0, .13)
    brass = weathered("MF020_WORN_BRASS", (.34, .16, .025), .90, .34, 7.0, .12)
    floor_mat = weathered("MF020_DIRTY_FLOOR", (.009, .022, .023), .72, .72, 10.0, .22)
    glass = material("MF020_DIRTY_GLASS", (.018, .085, .085), .08, .12, transmission=.76)
else:
    steel = material("MF020_BLOCKOUT_STEEL", (.12, .20, .20), .1, .75)
    dark = material("MF020_BLOCKOUT_DARK", (.035, .055, .06), .0, .8)
    brass = material("MF020_BLOCKOUT_HERO", (.44, .27, .04), .1, .66)
    floor_mat = dark
    glass = material("MF020_BLOCKOUT_GLASS", (.04, .18, .17), .0, .3, transmission=.25)
red = material("MF020_WARNING_RED", (.18, .004, .001), .25, .28, emission=(1.0, .015, .002), strength=.02)
amber = material("MF020_WARNING_AMBER", (.18, .035, .001), .2, .3, emission=(1.0, .19, .005), strength=.02)
energy = material("MF020_CONTAINED_ENERGY", (.16, .025, .001), .05, .2, emission=(1.0, .20, .006), strength=.015)
cream = material("MF020_GAUGE_FACE", (.52, .42, .19), .2, .48)

# Purposeful room shell: foreground floor, mid-ground hero, receding background structure.
cube("Floor", (0, 1.2, -.18), (6.3, 7.2, .18), floor_mat, bevel=.02)
cube("BackWall", (0, 4.2, 4.8), (6.3, .20, 5.0), dark, bevel=.02)
for x in (-5.35, -2.4, 2.8, 5.35):
    cyl(f"SupportColumn_{x}", (x, 3.72, 4.7), .30 if DETAILED else .42, 9.1, steel, owner="ARCHITECTURE")
for z in (1.0, 3.2, 5.4, 7.6, 9.1):
    cube(f"RearBeam_{z}", (0, 3.75, z), (6.0, .24, .10 if DETAILED else .16), brass)
if DETAILED:
    path("LeftPressureRun", [(-5.5, 2.9, .5), (-5.5, 2.9, 7.8), (-4.4, 2.9, 8.9), (-2.6, 2.9, 8.9)], brass, .13)
    path("RightCoolantRun", [(5.3, 3.0, .4), (5.3, 3.0, 6.7), (4.3, 3.0, 7.7), (2.8, 3.0, 7.7)], steel, .16)
    for index in range(5):
        cube(f"FloorChannel_{index}", (-4.8 + index * 2.4, .7, .05), (.7, 3.6, .035), brass, bevel=.01)

# Central contained reactor, constructed for this perspective shot.
hero_x, hero_y = .35, 1.25
cube("LowerContainment", (hero_x, hero_y, 1.05), (1.65, 1.25, .72), steel, "REACTOR", .12)
cube("ContainmentPlinth", (hero_x, hero_y, .34), (2.05, 1.48, .25), dark, "REACTOR", .08)
cyl("GlassChamber", (hero_x, hero_y, 4.55), 1.38, 5.75, glass, "REACTOR", vertices=64)
for cage_z in (2.25, 3.75, 5.25, 6.75):
    torus(f"InnerFieldRing_{cage_z}", (hero_x, hero_y, cage_z), .54, .035, dark)
for cage_x in (hero_x - .48, hero_x + .48):
    cube(f"InnerFieldRail_{cage_x}", (cage_x, hero_y + .30, 4.55), (.035, .035, 2.5), dark, "REACTOR", .01)
for z in (1.72, 7.38):
    torus(f"ContainmentRing_{z}", (hero_x, hero_y, z), 1.62, .19, brass)
for x in (-1.28, 1.98):
    cube(f"ReactorRail_{x}", (x, hero_y, 4.55), (.14, .20, 3.25), brass, "REACTOR", .04)
if DETAILED:
    for index in range(8):
        angle = index * math.tau / 8
        x = hero_x + math.cos(angle) * 1.58
        y = hero_y + math.sin(angle) * 1.58
        cube(f"RingClamp_{index}", (x, y, 7.38), (.12, .12, .24), dark, "REACTOR", .025).rotation_euler[2] = angle
    for side in (-1, 1):
        path(f"ReactorFeed_{side}", [(hero_x + side * 1.2, hero_y + .25, 1.1), (hero_x + side * 2.0, hero_y + .5, 1.1), (hero_x + side * 2.0, 3.2, 2.2)], brass, .11, "REACTOR")

# Internal energy is spatially contained and escalates after the pressure event.
animate(emission_strength(energy), [(1, .015), (frame(4.8) - 1, .015), (frame(5.4), .55), (frame(7.3), 5.0), (scene.frame_end, 6.0)])
strand_count = 2 if not DETAILED else 7
for strand in range(strand_count):
    points = []
    for step in range(46):
        z = 2.05 + step * .11
        angle = step * .47 + strand * math.tau / strand_count
        radius = .23 + .11 * math.sin(step * .31 + strand)
        points.append((hero_x + math.cos(angle) * radius, hero_y - .78 + strand * .015, z))
    path(f"EnergyFilament_{strand}", points, energy, .042 if DETAILED else .06, "REACTOR")
energy_kernel = sphere("EnergyKernel", (hero_x, hero_y - .74, 4.55), .28, energy, "REACTOR", 24)
energy_kernel.scale = (.25, .25, .25)
energy_kernel.keyframe_insert("scale", frame=1)
energy_kernel.keyframe_insert("scale", frame=frame(4.8) - 1)
energy_kernel.scale = (1.0, .72, 1.8)
energy_kernel.keyframe_insert("scale", frame=frame(7.3))
energy_kernel.scale = (1.12, .82, 2.05)
energy_kernel.keyframe_insert("scale", frame=scene.frame_end)

# A physical collar with asymmetric bolts makes rotation legible.
collar = torus("MotorizedCollar", (hero_x, hero_y, 5.85), 1.54, .16, brass)
for index in range(6):
    angle = index * math.tau / 6
    bolt = sphere(f"CollarBolt_{index}", (hero_x + math.cos(angle) * 1.55, hero_y + math.sin(angle) * 1.55, 5.85), .10, red if index == 0 else dark, "REACTOR", 16)
    bolt.parent = collar
collar.rotation_euler[2] = 0
collar.keyframe_insert("rotation_euler", frame=1, index=2)
collar.keyframe_insert("rotation_euler", frame=frame(5.3), index=2)
collar.rotation_euler[2] = math.radians(155)
collar.keyframe_insert("rotation_euler", frame=frame(7.3), index=2)
collar.rotation_euler[2] = math.radians(205)
collar.keyframe_insert("rotation_euler", frame=scene.frame_end, index=2)

# Left foreground analog console: secondary in hierarchy but mechanically readable.
console = cube("AnalogConsole", (-3.55, -.10, 1.48), (1.55, .82, 1.35), steel, "CONSOLE", .13)
console.rotation_euler[2] = math.radians(-7)
face = cube("ConsoleFace", (-3.55, -.90, 1.75), (1.40, .10, 1.02), dark, "CONSOLE", .06)
face.rotation_euler[2] = math.radians(-7)
gauge_pivots = []
for index, x in enumerate((-4.35, -3.55, -2.75)):
    cyl(f"GaugeHousing_{index}", (x, -1.04, 2.17), .30, .11, brass, "CONSOLE", (math.radians(90), 0, 0), 36)
    cyl(f"GaugeFace_{index}", (x, -1.12, 2.17), .24, .035, cream, "CONSOLE", (math.radians(90), 0, 0), 36, 0)
    pivot = bpy.data.objects.new(f"GaugePivot_{index}", None)
    coll("CONSOLE").objects.link(pivot)
    pivot.location = (x, -1.17, 2.17)
    needle = cube(f"GaugeNeedle_{index}", (0, -.01, .13), (.025, .018, .15), red, "CONSOLE", .008)
    needle.parent = pivot
    pivot.rotation_euler[1] = math.radians(-48)
    pivot.keyframe_insert("rotation_euler", frame=1, index=1)
    pivot.keyframe_insert("rotation_euler", frame=frame(1.8), index=1)
    pivot.rotation_euler[1] = math.radians(35 - index * 10)
    pivot.keyframe_insert("rotation_euler", frame=frame(4.2), index=1)
    pivot.rotation_euler[1] = math.radians(55 - index * 7)
    pivot.keyframe_insert("rotation_euler", frame=frame(7.3), index=1)
    gauge_pivots.append(pivot)

lever_pivot = bpy.data.objects.new("StartupLeverHinge", None)
coll("CONSOLE").objects.link(lever_pivot)
lever_pivot.location = (-2.78, -1.14, 1.30)
cyl("LeverHinge", lever_pivot.location, .20, .12, brass, "CONSOLE", (math.radians(90), 0, 0), 32)
arm = cube("StartupLeverArm", (0, 0, .38), (.055, .05, .38), brass, "CONSOLE", .015)
arm.parent = lever_pivot
knob = sphere("StartupLeverKnob", (0, 0, .79), .15, red, "CONSOLE", 20)
knob.parent = lever_pivot
lever_pivot.rotation_euler[1] = math.radians(-24)
lever_pivot.keyframe_insert("rotation_euler", frame=1, index=1)
lever_pivot.keyframe_insert("rotation_euler", frame=frame(1.2), index=1)
lever_pivot.rotation_euler[1] = math.radians(72)
lever_pivot.keyframe_insert("rotation_euler", frame=frame(2.2), index=1)

lamp_materials = []
for index, x in enumerate((-4.28, -3.62, -2.96)):
    lamp_mat = material(f"MF020_PRACTICAL_{index}", (.08, .008, .001), .1, .25, emission=(1.0, .05, .002), strength=.02)
    cyl(f"LampHousing_{index}", (x, -1.13, 1.33), .18, .10, brass, "CONSOLE", (math.radians(90), 0, 0), 32)
    sphere(f"PracticalBulb_{index}", (x, -1.23, 1.33), .12, lamp_mat, "CONSOLE", 20)
    start = frame(2.8) + index * 10
    animate(emission_strength(lamp_mat), [(1, .02), (start - 1, .02), (start + 6, 2.2), (frame(3.6), 4.0), (scene.frame_end, 5.0)])
    lamp_materials.append(lamp_mat)

# Mounted upper warning lamps reinforce vertical scale.
ring_lamps = []
for index in range(7):
    angle = math.radians(18 + index * 24)
    x = hero_x + math.cos(angle) * 1.75
    y = hero_y - .58
    z = 7.38 + math.sin(angle) * .48
    lamp_mat = material(f"MF020_RING_WARNING_{index}", (.1, .003, .001), .15, .25, emission=(1.0, .015, .001), strength=.02)
    lamp = sphere(f"MountedWarning_{index}", (x, y, z), .135, lamp_mat, "REACTOR", 20)
    ring_lamps.append(lamp)
    start = frame(3.6) + index * 5
    animate(emission_strength(lamp_mat), [(1, .02), (start - 1, .02), (start + 7, 4.2), (scene.frame_end, 5.0)])

# Lighting pass: motivated practicals, reactor spill, rim, and restrained console fill.
if DRAMATIC:
    core_light = point_light("ReactorSpill", (hero_x, -.15, 4.7), (1.0, .24, .015), 30, 1.5)
    for when, value in ((1, 24), (frame(4.8), 55), (frame(5.6), 210), (frame(7.3), 720), (scene.frame_end, 790)):
        core_light.data.energy = value
        core_light.data.keyframe_insert("energy", frame=when)
    point_light("ConsolePracticalFill", (-3.5, -2.3, 3.2), (.06, .42, .38), 285, 2.2)
    point_light("RearSeparation", (3.7, 3.0, 6.7), (.06, .20, .28), 520, 2.7)
    point_light("LowAmberMotivation", (-.8, 2.2, 1.0), (1.0, .10, .006), 230, 2.0)
else:
    point_light("BlockoutWorkLight", (-3.0, -4.5, 7.5), (.7, .86, 1.0), 720 if DETAILED else 900, 5.0)
    point_light("BlockoutHeroFill", (3.5, -1.5, 5.0), (1.0, .55, .18), 380, 3.5)

# Restrained native FX: bounded steam volumes and a few causal electrical sparks.
if WITH_FX:
    for index in range(4):
        steam_mat, density = volume_material(f"MF020_STEAM_{index}", (.42, .52, .50), .001)
        puff = sphere(f"PressureSteam_{index}", (2.00 + index * .22, .48, 2.0 + index * .18), .45, steam_mat, "FX", 16)
        start = frame(4.4) + index * 8
        puff.scale = (.08, .08, .08)
        puff.keyframe_insert("scale", frame=start - 1)
        puff.scale = (1.0, .72, 1.3)
        puff.keyframe_insert("scale", frame=start + 18)
        puff.location.z += 1.15
        puff.location.x += .35
        puff.keyframe_insert("location", frame=start + 38)
        animate(density, [(1, .001), (start - 1, .001), (start + 4, .42), (start + 30, .10), (start + 48, .001)])
    point_light("SteamVentMotivation", (2.35, -.05, 2.8), (.10, .48, .44), 190, 1.4)
    spark_mat = material("MF020_SPARK", (.4, .08, .001), .0, .15, emission=(1.0, .20, .01), strength=7.0)
    for index in range(9):
        angle = index * 2.4
        start = frame(6.1) + index * 4
        spark = sphere(f"ContainedSpark_{index}", (hero_x, .42, 4.7), .035, spark_mat, "FX", 12)
        spark.scale = (0, 0, 0)
        spark.keyframe_insert("scale", frame=start - 1)
        spark.scale = (1, 1, 1)
        spark.keyframe_insert("scale", frame=start)
        spark.location = (hero_x + math.cos(angle) * .70, .42, 4.7 + math.sin(angle) * 1.45)
        spark.keyframe_insert("location", frame=start + 14)
        spark.scale = (0, 0, 0)
        spark.keyframe_insert("scale", frame=start + 17)
    scene.use_nodes = True
    compositor = bpy.data.node_groups.new("MF020_BoundedGlow", "CompositorNodeTree")
    scene.compositing_node_group = compositor
    nodes = compositor.nodes
    nodes.clear()
    layers = nodes.new("CompositorNodeRLayers")
    glare = nodes.new("CompositorNodeGlare")
    glare.inputs["Type"].default_value = "Bloom"
    glare.inputs["Quality"].default_value = "High"
    glare.inputs["Threshold"].default_value = 1.0
    glare.inputs["Strength"].default_value = .55
    glare.inputs["Size"].default_value = .64
    compositor.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    composite = nodes.new("NodeGroupOutput")
    compositor.links.new(layers.outputs["Image"], glare.inputs["Image"])
    compositor.links.new(glare.outputs["Image"], composite.inputs["Image"])

# One perspective hero camera move; lens and target remain restrained.
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(hero_x, hero_y, 4.45))
target = bpy.context.object
target.name = "CameraAim"
own(target, "CAMERA")
bpy.ops.object.camera_add(location=(-6.7, -12.5, 4.25))
camera = bpy.context.object
camera.name = "CinematicHeroCamera"
camera.data.lens = SHOT["lens_mm"]
camera.data.sensor_width = 36
camera.data.dof.use_dof = True
camera.data.dof.focus_object = target
camera.data.dof.aperture_fstop = 5.6
own(camera, "CAMERA")
scene.camera = camera
constraint = camera.constraints.new(type="TRACK_TO")
constraint.target = target
constraint.track_axis = "TRACK_NEGATIVE_Z"
constraint.up_axis = "UP_Y"
camera.keyframe_insert("location", frame=1)
camera.location = (-5.5, -10.6, 4.55)
camera.keyframe_insert("location", frame=frame(5.0))
camera.location = (-3.65, -8.9, 4.82)
camera.keyframe_insert("location", frame=scene.frame_end)
target.keyframe_insert("location", frame=1)
target.location.z = 4.75
target.keyframe_insert("location", frame=scene.frame_end)

build_ms = round((time.monotonic() - BUILD_STARTED) * 1000)
output = Path(A.output_dir).resolve()
output.mkdir(parents=True, exist_ok=True)
events = SHOT["events_seconds"]
contract = {
    "slice": "MF-020",
    "backend": "BLENDER",
    "stage": A.stage,
    "seed": CONFIG["seed"],
    "engine": scene.render.engine,
    "samples": scene.eevee.taa_render_samples,
    "resolution": [scene.render.resolution_x, scene.render.resolution_y],
    "fps": scene.render.fps,
    "frames": scene.frame_end,
    "shot_id": SHOT["id"],
    "camera": {"name": camera.name, "lens_mm": camera.data.lens, "move": SHOT["camera_move"], "single_shot": True},
    "production_stage_order": CONFIG["stages"]["order"],
    "events_seconds": events,
    "objects": {"reactor": "GlassChamber", "console": "AnalogConsole", "gauges": len(gauge_pivots), "lever": "StartupLeverHinge", "ring_lamps": len(ring_lamps), "collar": collar.name, "energy_filaments": strand_count},
    "mechanical_logic": {"lever_hinge": True, "gauge_pivots": True, "mounted_warning_lamps": True, "pressure_precedes_energy": events["pressure_release"] < events["energy_forms"], "energy_inside_chamber": True, "collar_response_after_energy": events["energy_forms"] < events["collar_response"]},
    "fx": {"steam_volumes": 4 if WITH_FX else 0, "contained_sparks": 9 if WITH_FX else 0, "bounded_compositor_glow": WITH_FX},
    "godot_dependency": False,
}
(output / "scene-contract.json").write_text(json.dumps(contract, indent=2) + "\n")

if A.scene_output:
    scene_path = Path(A.scene_output).resolve()
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(scene_path))

render_started = time.monotonic()
rendered = 0
resumed = 0
if A.mode == "stills":
    stage_config = CONFIG["stages"]["blockout" if A.stage == "blockout" else A.stage]
    for seconds, label in zip(stage_config["seconds"], stage_config["labels"]):
        scene.frame_set(frame(seconds))
        scene.render.filepath = str(output / f"{label}.png")
        bpy.ops.render.render(write_still=True)
        rendered += 1
else:
    for index in range(scene.frame_end):
        target_path = output / f"frame-{index:04d}.png"
        if A.resume and target_path.is_file() and target_path.stat().st_size > 1024:
            resumed += 1
            continue
        scene.frame_set(index + 1)
        scene.render.filepath = str(target_path)
        bpy.ops.render.render(write_still=True)
        rendered += 1

performance = {
    "stage": A.stage,
    "mode": A.mode,
    "build_ms": build_ms,
    "render_ms": round((time.monotonic() - render_started) * 1000),
    "total_ms": round((time.monotonic() - STARTED) * 1000),
    "rendered": rendered,
    "resumed_frames": resumed,
    "engine": scene.render.engine,
    "device": "CPU_HEADLESS_DEFAULT",
}
Path(A.performance).write_text(json.dumps(performance, indent=2) + "\n")
print("MF020_BLENDER_RENDER_OK " + json.dumps(performance, sort_keys=True))
