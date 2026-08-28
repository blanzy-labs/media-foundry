"""Create the bounded reusable Blender template for MF-019."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy


def arguments():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(); parser.add_argument("--output", required=True); return parser.parse_args(values)


def material(name, color, metallic=0.0, roughness=0.5):
    mat = bpy.data.materials.new(name); mat.use_nodes = True; bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0); bsdf.inputs["Metallic"].default_value = metallic; bsdf.inputs["Roughness"].default_value = roughness
    return mat


args = arguments(); bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
for collection in list(bpy.data.collections):
    if collection.name != "Collection": bpy.data.collections.remove(collection)
root = bpy.context.scene.collection
default = bpy.data.collections.get("Collection"); default.name = "MF019_TEMPLATE"
for name in ("ENVIRONMENT", "REACTOR", "CONSOLE", "DISPLAY", "LIGHTING"):
    collection = bpy.data.collections.new(name); root.children.link(collection)
for mat in list(bpy.data.materials): bpy.data.materials.remove(mat)
material("PULP_DARK_TEAL", (0.015, 0.075, 0.065), 0.65, 0.5)
material("PULP_AGED_BRASS", (0.52, 0.30, 0.045), 0.85, 0.28)
material("PULP_BLACK", (0.004, 0.008, 0.007), 0.35, 0.65)
material("PULP_CREAM", (0.72, 0.59, 0.30), 0.35, 0.36)
scene = bpy.context.scene; scene["media_foundry_contract"] = "blender_template_v1"; scene["template_id"] = "pulp-reactor-v1"; scene["source_policy"] = "repository_local_only"
scene.render.engine = "BLENDER_EEVEE"; scene.render.image_settings.file_format = "PNG"; scene.render.film_transparent = False; scene.render.resolution_x = 768; scene.render.resolution_y = 1152; scene.render.resolution_percentage = 100; scene.render.fps = 30
scene.world.color = (0.002, 0.009, 0.008)
output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True); bpy.ops.wm.save_as_mainfile(filepath=str(output.resolve()), compress=True)
print(f"MF019_TEMPLATE_OK path={output} version={bpy.app.version_string}")
