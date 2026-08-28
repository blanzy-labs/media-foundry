#!/usr/bin/env python3
"""Independent technical validation for MF-018B."""
from __future__ import annotations
import argparse,io,json,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from composition_contract import validate_manifest
from playable_scene_contract import sha256,validate_package

def probe(path:Path)->dict:
    p=subprocess.run(["ffprobe","-v","error","-count_frames","-show_streams","-show_format","-of","json",str(path)],capture_output=True,text=True);d=json.loads(p.stdout) if p.returncode==0 else {};v=next((x for x in d.get("streams",[]) if x.get("codec_type")=="video"),{});a=next((x for x in d.get("streams",[]) if x.get("codec_type")=="audio"),{})
    return {"video_codec":v.get("codec_name"),"audio_codec":a.get("codec_name"),"width":v.get("width"),"height":v.get("height"),"fps":v.get("avg_frame_rate"),"frames":int(v.get("nb_read_frames",0)),"duration":float(d.get("format",{}).get("duration",0)),"sample_rate":int(a.get("sample_rate",0))}
def image(path:Path)->np.ndarray:return np.asarray(Image.open(path).convert("RGB")).astype(float)
def luma(x):return .2126*x[:,:,0]+.7152*x[:,:,1]+.0722*x[:,:,2]
def material(x):
    g=luma(x);return {"edge_mean":float((np.abs(np.diff(g,axis=0)).mean()+np.abs(np.diff(g,axis=1)).mean())/2),"quantized_colors":len(np.unique((x.astype(np.uint8)//8).reshape(-1,3),axis=0)),"bright_ratio":float(np.mean(g>120))}
def video_frame(path:Path,seconds:float)->np.ndarray:
    p=subprocess.run(["ffmpeg","-v","error","-ss",str(seconds),"-i",str(path),"-frames:v","1","-f","image2pipe","-vcodec","png","-"],capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr.decode());return np.asarray(Image.open(io.BytesIO(p.stdout)).convert("RGB")).astype(float)

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--project-root",required=True);p.add_argument("--output",required=True);a=p.parse_args();root=Path(a.project_root).resolve();art=root/"artifacts/mf-018b";config_path=root/"config/mf018b-native-pulp-scene.json";config=json.loads(config_path.read_text());manifest=json.loads((art/"render-manifest.json").read_text());handoff_path=root/config["handoff_manifest"];handoff=json.loads(handoff_path.read_text());failures=json.loads((root/"reports/mf-018b/failure-tests.json").read_text());checks={}
    def check(name,passed,detail):checks[name]={"status":"PASS" if passed else "FAIL","detail":detail}
    baseline=root/config["baseline"]["artifact"];baseline_config=root/config["baseline"]["config"]
    check("mf018a_preserved",sha256(baseline)==config["baseline"]["artifact_sha256"] and sha256(baseline_config)==config["baseline"]["config_sha256"],{"artifact":sha256(baseline),"config":sha256(baseline_config)})
    composition=json.loads((root/config["composition_manifest"]).read_text());composition_result=validate_manifest(composition)
    check("static_composition_contract",composition_result["result"]=="PASS" and len(composition_result["checks"])==17 and all(x=="PASS" for x in composition_result["checks"].values()),composition_result)
    handoff_result=validate_package(root,handoff);check("playable_scene_contract",handoff_result["result"]=="PASS" and len(handoff_result["checks"])>=14,handoff_result)
    check("required_failure_tests",failures["result"]=="PASS" and failures["passed"]==failures["total"]==7,failures)
    check("portable_handoff_manifest",manifest["handoff"]["sha256"]==sha256(handoff_path) and handoff["portable_paths"] is True,{"path":config["handoff_manifest"],"sha256":sha256(handoff_path)})
    check("zero_game_foundry_dependency",handoff["dependencies"]["game_foundry"]==[] and manifest["handoff"]["game_foundry_dependencies"]==0,handoff["dependencies"])
    check("ownership_boundary",handoff["gameplay_implemented"] is False and set(handoff["ownership"]["game_foundry"])>={"input","objectives","rules","score","win_fail"},handoff["ownership"])
    source=(root/handoff["package"]["base_script"]).read_text();driver=(root/handoff["package"]["promo_driver"]).read_text()
    check("base_scene_driver_separation",handoff["package"]["promo_driver_optional"] is True and "PromoDriver" not in source and "MF018BPromoDriver" in driver and manifest["base_scene"]["standalone_probe"]=="PASS",manifest["base_scene"])
    log=(art/"logs/base-scene-probe.log").read_text();check("scene_load_nodes_setters_signals","MF018B_CONTRACT_PROBE_OK nodes=4 signals=7 driver_loaded=false" in log and "ERROR:" not in log,log.strip())
    interaction_ids=[x["id"] for x in handoff["interaction_points"]];state_ids=[x["id"] for x in handoff["state_variables"]]
    check("interaction_inventory",interaction_ids==["coolant_dial","field_dial","containment_switch","emergency_lever"],interaction_ids)
    check("state_variable_inventory",state_ids==["reactor_energy","temperature","containment","field_strength","pressure","warning_level"],state_ids)
    check("signal_inventory",len(handoff["signals"])==11 and all(name in source for name in handoff["signals"]),handoff["signals"])
    check("audio_event_inventory",len(handoff["audio_events"])==7 and all(x["source_asset_id"]=="approved_music" for x in handoff["audio_events"]),handoff["audio_events"])
    audio=manifest["audio"];check("approved_audio",audio["track_approval"]==audio["cue_approval"]=="APPROVED" and audio["track_sha256"]==config["audio"]["source_sha256"] and audio["usable_start"]<=audio["actual_start"]<audio["actual_end"]<=audio["usable_end"],audio)
    check("audio_levels",abs(audio["loudness"]["integrated_lufs"]-config["audio"]["target_lufs"])<=.75 and audio["loudness"]["true_peak_db"]<=config["audio"]["true_peak_db"]+.1,audio["loudness"])
    outputs_ok=True;actual={}
    for rel,expected in manifest["outputs"].items():
        path=art/rel;value=sha256(path) if path.is_file() else None;actual[rel]=value;outputs_ok=outputs_ok and value==expected["sha256"] and path.stat().st_size==expected["bytes"]
    check("artifact_integrity",outputs_ok,actual)
    final=art/"final-test.mp4";media=probe(final);check("promo_media_contract",media=={"video_codec":"h264","audio_codec":"aac","width":768,"height":1152,"fps":"30/1","frames":420,"duration":14.0,"sample_rate":48000},media)
    decode=subprocess.run(["ffmpeg","-v","error","-i",str(final),"-f","null","-"],capture_output=True);check("full_audio_video_decode",decode.returncode==0,decode.stderr.decode()[-1000:])
    comp=probe(art/"comparison/mf018a-vs-mf018b.mp4");check("native_v1_refined_comparison",comp["video_codec"]=="h264" and comp["width"]==1536 and comp["height"]==1152 and comp["frames"]==120 and comp["duration"]==4.0,comp)
    stills={name:image(art/"static-keyframes"/f"{name}.png") for name in ("dormant","stable","unstable","critical")};check("four_static_states",all(x.shape==(1152,768,3) for x in stills.values()),list(stills))
    state_motion={"dormant_stable":float(np.abs(stills["stable"]-stills["dormant"]).mean()),"stable_unstable":float(np.abs(stills["unstable"]-stills["stable"]).mean()),"unstable_critical":float(np.abs(stills["critical"]-stills["unstable"]).mean())};check("state_progression_visible",min(state_motion.values())>.5,state_motion)
    hierarchy={};reactor=(slice(180,1040),slice(330,755));support=(slice(520,1020),slice(15,285))
    for name,x in stills.items():hierarchy[name]=float(luma(x[reactor]).mean()/max(luma(x[support]).mean(),1))
    check("reactor_remains_hero",min(hierarchy.values())>1.08,hierarchy)
    chamber=(slice(330,820),slice(425,630));adj=(slice(330,820),slice(630,768));yellow=lambda x:(x[:,:,0]>120)&(x[:,:,1]>85)&(x[:,:,2]<125)&((x[:,:,0]+x[:,:,1])>x[:,:,2]*2.5)
    inside=int(yellow(stills["critical"][chamber]).sum()-yellow(stills["dormant"][chamber]).sum());outside=int(yellow(stills["critical"][adj]).sum()-yellow(stills["dormant"][adj]).sum());binding={"inside":inside,"adjacent":outside,"ratio":round(inside/max(outside,1),3)};check("reactor_energy_contained",inside>2500 and inside>max(outside,1)*5,binding)
    critical=stills["critical"];red=(critical[:,:,0]>110)&(critical[:,:,0]>critical[:,:,1]*1.45)&(critical[:,:,1]<95);lamp={"ring":int(red[170:380,330:750].sum()),"console":int(red[850:990,20:270].sum()),"total":int(red.sum())};check("lamps_attached_to_machine_regions",lamp["ring"]>1000 and lamp["console"]>200 and (lamp["ring"]+lamp["console"])/max(lamp["total"],1)>.75,lamp)
    cyan=(critical[:,:,0]<100)&(critical[:,:,1]>180)&(critical[:,:,2]>190);check("diagnostic_excluded_from_promo",cyan.sum()<10 and (art/"interaction-diagnostic/controls-and-state.png").is_file(),{"promo_cyan_pixels":int(cyan.sum())})
    old=image(root/"artifacts/mf-018a/static-keyframes/peak.png");new=critical;old_m=material(old);new_m=material(new);ratios={k:round(new_m[k]/old_m[k],3) for k in old_m};check("measured_visual_refinement",ratios["edge_mean"]>1.25 and ratios["quantized_colors"]>1.15 and ratios["bright_ratio"]>1.25,{"mf018a":old_m,"mf018b":new_m,"ratios":ratios})
    render_log=(art/"logs/godot-render.log").read_text();check("native_render_clean","MF018B_NATIVE_SCENE_OK frames=420" in render_log and "ERROR:" not in render_log and "SCRIPT ERROR:" not in render_log,render_log.strip())
    check("deterministic_state_control",manifest["seed"]==config["seed"]==composition["seed"]==1801958 and manifest["raw_frames_retained"] is False,{"seed":manifest["seed"],"raw_frames_retained":manifest["raw_frames_retained"]})
    assets=handoff["assets"];core=sum(x["bytes"] for x in assets if x["required"]);total=sum(x["bytes"] for x in assets);web=handoff["web_advisory"];check("performance_web_advisory",manifest["elapsed_ms"]<120000 and core<100000 and web["custom_shaders"]==0 and web["external_plugins"]==0 and web["export_tested"] is False,{"elapsed_ms":manifest["elapsed_ms"],"required_core_bytes":core,"declared_asset_bytes":total,"web":web})
    check("no_publication",manifest["published"] is False and manifest["human_review"]=="PENDING_HUMAN" and manifest["release_ready"] is False,{"published":manifest["published"],"human":manifest["human_review"]})
    result="TECHNICAL_PASS" if all(x["status"]=="PASS" for x in checks.values()) else "FAIL";report={"slice":"MF-018B","result":result,"release_ready":False,"human_review":"PENDING_HUMAN","checks":checks,"metrics":{"state_motion":state_motion,"hierarchy":hierarchy,"energy_binding":binding,"visual_refinement":ratios,"elapsed_ms":manifest["elapsed_ms"]},"published":False};out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report,indent=2));return 0 if result=="TECHNICAL_PASS" else 1
if __name__=="__main__":raise SystemExit(main())
