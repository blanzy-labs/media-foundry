"""Build and headlessly render the MF-019 Blender pulp-reactor interpretation."""
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


def args():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(); parser.add_argument("--manifest", required=True); parser.add_argument("--output-dir", required=True); parser.add_argument("--mode", choices=("static", "frames"), required=True); parser.add_argument("--performance", required=True); parser.add_argument("--resume", action="store_true"); return parser.parse_args(values)


A = args(); ROOT = Path(bpy.path.abspath("//")).resolve().parents[1]; CONFIG = json.loads((ROOT / A.manifest).read_text()); SHARED = CONFIG["shared"]; FPS = SHARED["fps"]
random.seed(CONFIG["seed"]); STARTED = time.monotonic(); BUILD_STARTED = time.monotonic()


def collection(name): return bpy.data.collections[name]
def move_to(obj, name):
    for owner in list(obj.users_collection): owner.objects.unlink(obj)
    collection(name).objects.link(obj)
def mat(name, color, metallic=0.0, roughness=.5, emission=None, strength=0.0, transmission=0.0, alpha=1.0):
    existing = bpy.data.materials.get(name)
    if existing: return existing
    value = bpy.data.materials.new(name); value.use_nodes = True; node = value.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = (*color, 1.0); node.inputs["Metallic"].default_value = metallic; node.inputs["Roughness"].default_value = roughness
    node.inputs["Transmission Weight"].default_value = transmission; node.inputs["Alpha"].default_value = alpha
    if emission is not None: node.inputs["Emission Color"].default_value = (*emission, 1.0); node.inputs["Emission Strength"].default_value = strength
    value.diffuse_color = (*color, alpha); return value
def emission_input(material): return material.node_tree.nodes.get("Principled BSDF").inputs["Emission Strength"]
def animate_input(socket, values):
    for frame, value in values: socket.default_value = value; socket.keyframe_insert("default_value", frame=frame)
def animate_color(socket, values):
    for frame, value in values: socket.default_value = (*value, 1.0); socket.keyframe_insert("default_value", frame=frame)
def cube(name, location, scale, material, owner="ENVIRONMENT", bevel=.06):
    bpy.ops.mesh.primitive_cube_add(location=location); obj = bpy.context.object; obj.name = name; obj.scale = scale; bpy.ops.object.transform_apply(location=False, rotation=False, scale=True); obj.data.materials.append(material); move_to(obj, owner)
    if bevel: mod = obj.modifiers.new("WornEdges", "BEVEL"); mod.width = bevel; mod.segments = 2
    return obj
def cylinder(name, location, radius, depth, material, owner="REACTOR", rotation=(0,0,0), vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation); obj=bpy.context.object; obj.name=name; obj.data.materials.append(material); move_to(obj,owner); mod=obj.modifiers.new("EdgeWear","BEVEL"); mod.width=.035; mod.segments=2; return obj
def sphere(name, location, radius, material, owner):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=radius, location=location); obj=bpy.context.object; obj.name=name; obj.data.materials.append(material); move_to(obj,owner); return obj
def curve_path(name, points, material, bevel, owner, cyclic=False):
    data=bpy.data.curves.new(name,"CURVE"); data.dimensions="3D"; data.bevel_depth=bevel; data.bevel_resolution=2; spline=data.splines.new("POLY"); spline.points.add(len(points)-1)
    for point,co in zip(spline.points,points): point.co=(*co,1.0)
    spline.use_cyclic_u=cyclic; obj=bpy.data.objects.new(name,data); collection(owner).objects.link(obj); obj.data.materials.append(material); return obj
def text_obj(name, body, location, size, material, start_seconds, owner="DISPLAY", spacing=1.0):
    data=bpy.data.curves.new(name,"FONT"); data.body=body; data.align_x="CENTER"; data.align_y="CENTER"; data.size=size; data.space_line=spacing; data.extrude=.008; data.bevel_depth=.004
    font_path=ROOT/"godot/fonts/Lato-Heavy.ttf"
    if font_path.is_file(): data.font=bpy.data.fonts.load(str(font_path))
    obj=bpy.data.objects.new(name,data); collection(owner).objects.link(obj); obj.location=location; obj.rotation_euler=(math.radians(90),0,0); obj.data.materials.append(material)
    start=round(start_seconds*FPS)+1; socket=emission_input(material); animate_input(socket,[(1,0.0),(start-1,0.0),(start+20,1.9)])
    return obj
def frame(seconds): return round(seconds*FPS)+1


# Clear generated objects while preserving template collections and palette materials.
for obj in list(bpy.data.objects): bpy.data.objects.remove(obj, do_unlink=True)
scene=bpy.context.scene; scene.render.engine="BLENDER_EEVEE"; scene.eevee.taa_render_samples=int(CONFIG["render"]["blender"]["samples"]); scene.render.resolution_x=SHARED["resolution"][0]; scene.render.resolution_y=SHARED["resolution"][1]; scene.render.resolution_percentage=100; scene.render.fps=FPS; scene.frame_start=1; scene.frame_end=round(SHARED["runtime_seconds"]*FPS); scene.render.image_settings.file_format="PNG"; scene.render.film_transparent=False
scene.render.image_settings.color_mode="RGB"; scene.render.image_settings.color_depth="8"; scene.render.filepath=str(Path(A.output_dir).resolve())
scene["mf019_seed"]=CONFIG["seed"]; scene["mf019_semantic_sequence"]=json.dumps(SHARED["semantic_sequence"]); scene["mf019_text"]=SHARED["title"]+"|"+SHARED["cta"]+"|"+SHARED["display_url"]
world=scene.world; world.use_nodes=True; world.node_tree.nodes["Background"].inputs["Color"].default_value=(.002,.012,.010,1); world.node_tree.nodes["Background"].inputs["Strength"].default_value=.16

dark=mat("MF019_DARK_METAL",(.012,.065,.057),.72,.46); brass=mat("MF019_AGED_BRASS",(.42,.22,.025),.86,.29); black=mat("MF019_BLACK",(.002,.006,.005),.35,.7); cream=mat("MF019_CREAM",(.73,.57,.24),.42,.34); glass=mat("MF019_GLASS",(.025,.11,.095),.1,.13,transmission=.72,alpha=.38)
red=mat("MF019_RED_EMISSION",(.22,.008,.003),.2,.32,emission=(1.0,.035,.005),strength=.05); energy=mat("MF019_ENERGY",(.32,.11,.004),.05,.22,emission=(1.0,.34,.012),strength=.08); core_shell=mat("MF019_CORE_SHELL",(.035,.075,.055),.35,.2,transmission=.35,alpha=.32)
title_mat=mat("MF019_SCREEN_TITLE",(.001,.001,.001),.05,.6,emission=(1.0,.58,.06),strength=0.0); cta_mat=mat("MF019_SCREEN_CTA",(.001,.001,.001),.05,.6,emission=(.68,1.0,.77),strength=0.0); url_mat=mat("MF019_SCREEN_URL",(.001,.001,.001),.05,.6,emission=(1.0,.58,.06),strength=0.0)

# Environment shell and limited industrial depth.
cube("BackWall",(0,1.2,6),(4.7,.25,6),dark,"ENVIRONMENT",.02); cube("Floor",(0,0,0),(4.7,4,.18),black,"ENVIRONMENT",.03)
for x in (-3.75,-.2,3.75): cylinder(f"RearCylinder{x}",(x,.55,5.2),.42,8.8,dark,"ENVIRONMENT")
for z in (1.0,3.0,5.0,7.0,9.0): cube(f"WallBeam{z}",(0,.85,z),(4.5,.18,.07),brass,"ENVIRONMENT",.02)
curve_path("LeftWallPipe",[(-4.0,-.05,.5),(-4.0,-.05,8.9),(-3.55,-.05,9.35)],brass,.11,"ENVIRONMENT")

# Reactor hero: attached structure, glass chamber, contained energy and physical lamps.
cylinder("GlassChamber",(1.25,-.05,5.25),1.18,4.75,glass,"REACTOR")
cylinder("CoreContainment",(1.25,.05,5.2),.47,4.05,core_shell,"REACTOR")
animate_input(emission_input(energy),[(1,.06),(frame(5.72),.12),(frame(6.05),.24),(frame(9.0),.65),(frame(11.5),1.25),(scene.frame_end,1.50)])
for strand in range(7):
    points=[]
    for step in range(44):
        z=3.25+step*.09; angle=step*.47+strand*math.tau/7; radius=.34+.08*math.sin(step*.31+strand); points.append((1.25+math.cos(angle)*radius,-.55+strand*.015,z))
    curve_path(f"EnergyStrand{strand}",points,energy,.025,"REACTOR")
for x in (.0,2.5): cube(f"ReactorSupport{x}",(x,.05,5.1),(.16,.22,3.45),brass,"REACTOR",.05)
for z,scale in ((2.45,(1.65,.65,.32)),(8.0,(1.75,.46,.20))):
    bpy.ops.mesh.primitive_torus_add(major_radius=1.45,minor_radius=.16,major_segments=64,minor_segments=12,location=(1.25,-.08,z),rotation=(math.radians(90),0,0)); ring=bpy.context.object; ring.name=f"MountedRing{z}"; ring.scale=(scale[0]/1.45,1,scale[2]/.16); ring.data.materials.append(brass); move_to(ring,"REACTOR")
cube("ContainmentBase",(1.25,-.02,1.62),(1.72,.66,.55),dark,"REACTOR",.09); cube("BaseInset",(1.25,-.70,1.66),(1.05,.08,.40),black,"REACTOR",.02)
for index in range(6):
    x=.55+index*.28; cube(f"BaseVent{index}",(x,-.80,1.66),(.085,.03,.28),brass,"REACTOR",.01)
ring_lamps=[]
for index in range(8):
    angle=math.pi*.12+index*(math.pi*.76/7); x=1.25+math.cos(angle)*1.50; z=8.0+math.sin(angle)*.62; lamp_mat=mat(f"MF019_RING_LAMP_{index}",(.10,.008,.002),.2,.32,emission=(1.0,.055,.006),strength=.03); lamp=sphere(f"MountedRingLamp{index}",(x,-.58,z),.14,lamp_mat,"REACTOR"); ring_lamps.append(lamp)
    start=frame(5.72)+index*5; animate_input(emission_input(lamp_mat),[(1,.03),(start-1,.03),(start+8,4.2)])

# Physically local lighting follows the reactor and ring hierarchy.
bpy.ops.object.light_add(type="POINT",location=(1.25,-1.0,5.2)); core_light=bpy.context.object; core_light.name="ReactorLocalLight"; core_light.data.color=(1.0,.42,.04); core_light.data.energy=35; core_light.data.shadow_soft_size=1.4; move_to(core_light,"LIGHTING")
for f,value in ((1,20),(frame(6.05),45),(frame(9.0),90),(frame(11.5),155),(scene.frame_end,180)): core_light.data.energy=value; core_light.data.keyframe_insert("energy",frame=f)
bpy.ops.object.light_add(type="AREA",location=(-2.4,-3.0,5.0)); fill=bpy.context.object; fill.name="ConsoleFill"; fill.rotation_euler=(math.radians(90),0,0); fill.data.color=(.18,.55,.44); fill.data.energy=180; fill.data.shape="RECTANGLE"; fill.data.size=4; move_to(fill,"LIGHTING")

# Analog console and one clean attached perimeter.
panel=cube("AnalogConsole",(-2.45,-.18,3.35),(1.30,.42,2.35),dark,"CONSOLE",.12); panel.rotation_euler[1]=math.radians(-4)
curve_path("ConsolePerimeter",[(-3.70,-.65,1.05),(-1.16,-.65,1.20),(-1.10,-.65,5.52),(-3.55,-.65,5.72)],brass,.055,"CONSOLE",True)
gauge_needles=[]
for index,x in enumerate((-3.25,-2.45,-1.65)):
    cylinder(f"GaugeHousing{index}",(x,-.68,4.72),.32,.10,black,"CONSOLE",rotation=(math.radians(90),0,0)); cylinder(f"GaugeFace{index}",(x,-.75,4.72),.25,.045,cream,"CONSOLE",rotation=(math.radians(90),0,0))
    pivot=bpy.data.objects.new(f"GaugeNeedlePivot{index}",None); collection("CONSOLE").objects.link(pivot); pivot.location=(x,-.82,4.72); needle=cube(f"GaugeNeedle{index}",(0,0,.13),(.025,.018,.16),red,"CONSOLE",.008); needle.parent=pivot
    pivot.rotation_euler[1]=math.radians(-45); pivot.keyframe_insert("rotation_euler",frame=1,index=1); pivot.keyframe_insert("rotation_euler",frame=frame(1.75),index=1); pivot.rotation_euler[1]=math.radians(38-index*12); pivot.keyframe_insert("rotation_euler",frame=frame(4.0),index=1); pivot.rotation_euler[1]=math.radians(58-index*8); pivot.keyframe_insert("rotation_euler",frame=scene.frame_end,index=1); gauge_needles.append(pivot)
for index,x in enumerate((-3.0,-1.9)):
    cylinder(f"RotaryDial{index}",(x,-.72,3.45),.25,.11,black,"CONSOLE",rotation=(math.radians(90),0,0)); cylinder(f"DialTrim{index}",(x,-.79,3.45),.20,.04,brass,"CONSOLE",rotation=(math.radians(90),0,0))
lever_pivot=bpy.data.objects.new("StartupLeverHinge",None); collection("CONSOLE").objects.link(lever_pivot); lever_pivot.location=(-1.85,-.78,2.72); cylinder("LeverHinge",lever_pivot.location,.22,.12,brass,"CONSOLE",rotation=(math.radians(90),0,0)); arm=cube("StartupLeverArm",(0,0,.38),(.055,.045,.38),brass,"CONSOLE",.015); arm.parent=lever_pivot; knob=sphere("StartupLeverKnob",(0,0,.78),.14,red,"CONSOLE"); knob.parent=lever_pivot
lever_pivot.rotation_euler[1]=0; lever_pivot.keyframe_insert("rotation_euler",frame=1,index=1); lever_pivot.keyframe_insert("rotation_euler",frame=frame(1.15),index=1); lever_pivot.rotation_euler[1]=math.radians(90); lever_pivot.keyframe_insert("rotation_euler",frame=frame(2.25),index=1)
indicator_mats=[]
for index,x in enumerate((-3.35,-2.75,-2.15,-1.55)):
    lamp_mat=mat(f"MF019_INDICATOR_{index}",(.01,.02,.04),.1,.35,emission=(.04,.15,1.0),strength=.02); cylinder(f"IndicatorHousing{index}",(x,-.70,1.92),.17,.10,brass,"CONSOLE",rotation=(math.radians(90),0,0)); sphere(f"IndicatorBulb{index}",(x,-.82,1.92),.11,lamp_mat,"CONSOLE"); indicator_mats.append(lamp_mat)
    bsdf=lamp_mat.node_tree.nodes.get("Principled BSDF"); color=bsdf.inputs["Emission Color"]; strength=bsdf.inputs["Emission Strength"]
    animate_color(color,[(1,(.02,.06,.2)),(frame(2.75),(0.02,.22,1.0)),(frame(4.15),(.03,.72,.18)),(frame(5.45),(1.0,.62,.01))]); animate_input(strength,[(1,.02),(frame(2.75)+index*4,2.2),(frame(4.15)+index*3,2.7),(frame(5.45)+index*2,3.2)])

# Existing dark upper-left area becomes a physically mounted information display.
cube("InformationPanel",(-2.55,.0,8.40),(1.48,.24,1.36),black,"DISPLAY",.08); curve_path("InformationPanelFrame",[(-3.92,-.38,7.13),(-1.18,-.38,7.13),(-1.18,-.38,9.67),(-3.92,-.38,9.67)],brass,.035,"DISPLAY",True)
text_obj("DisplayTitle","UNKNOWN\nPROCESS",(-2.55,-.52,8.95),.39,title_mat,SHARED["event_markers_seconds"]["title_start"],spacing=.84)
text_obj("DisplayCTA","TRY A WEB GAME",(-2.55,-.52,8.25),.20,cta_mat,SHARED["event_markers_seconds"]["cta_start"])
text_obj("DisplayURL","RCBLANZY.COM/BOOKS/\nUNKNOWN-PROCESS",(-2.55,-.52,7.72),.145,url_mat,SHARED["event_markers_seconds"]["url_start"],spacing=.85)

# Restrained orthographic camera: same hierarchy and portrait intent as Candidate A.
bpy.ops.object.camera_add(location=(0,-18,6.0),rotation=(math.radians(90),0,0)); camera=bpy.context.object; camera.name="PromoCamera"; camera.data.type="ORTHO"; camera.data.ortho_scale=12.15; scene.camera=camera; move_to(camera,"ENVIRONMENT")
camera.location.y=-18; camera.keyframe_insert("location",frame=1,index=1); camera.location.y=-17.5; camera.keyframe_insert("location",frame=scene.frame_end,index=1)

build_ms=round((time.monotonic()-BUILD_STARTED)*1000); output=Path(A.output_dir).resolve(); output.mkdir(parents=True,exist_ok=True)
contract={"seed":CONFIG["seed"],"engine":scene.render.engine,"samples":scene.eevee.taa_render_samples,"resolution":[scene.render.resolution_x,scene.render.resolution_y],"fps":scene.render.fps,"frames":scene.frame_end,"objects":{"reactor":"GlassChamber","energy":"CoreContainment","ring_lights":len(ring_lamps),"gauges":len(gauge_needles),"lever":"StartupLeverHinge","indicators":len(indicator_mats),"display":["DisplayTitle","DisplayCTA","DisplayURL"]},"events_seconds":SHARED["event_markers_seconds"],"text":{"title":SHARED["title"],"cta":SHARED["cta"],"url":SHARED["display_url"]},"attached_motion":{"ring_lights":True,"gauge_pivots":True,"lever_hinge":True,"indicators_in_console":True,"energy_in_chamber":True,"local_reactor_light":True}}
(output/"scene-contract.json").write_text(json.dumps(contract,indent=2)+"\n")
render_started=time.monotonic(); rendered=0; skipped=0
if A.mode=="static":
    labels=CONFIG["composition_gate"]["static_labels"]
    for seconds,label in zip(CONFIG["composition_gate"]["static_seconds"],labels):
        scene.frame_set(frame(seconds)); scene.render.filepath=str(output/f"{label}.png"); bpy.ops.render.render(write_still=True); rendered+=1
else:
    expected=scene.frame_end
    for index in range(expected):
        target=output/f"frame-{index:04d}.png"
        if A.resume and target.is_file() and target.stat().st_size>1024: skipped+=1; continue
        scene.frame_set(index+1); scene.render.filepath=str(target); bpy.ops.render.render(write_still=True); rendered+=1
performance={"mode":A.mode,"build_ms":build_ms,"render_ms":round((time.monotonic()-render_started)*1000),"total_ms":round((time.monotonic()-STARTED)*1000),"rendered":rendered,"resumed_frames":skipped,"engine":scene.render.engine,"device":"CPU_HEADLESS_DEFAULT"}
Path(A.performance).write_text(json.dumps(performance,indent=2)+"\n"); print("MF019_BLENDER_RENDER_OK "+json.dumps(performance,sort_keys=True))
