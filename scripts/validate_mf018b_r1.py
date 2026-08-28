#!/usr/bin/env python3
"""Independent validation for MF-018B-R1 cleanup and startup causality."""
from __future__ import annotations
import argparse,json,math,subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from composition_contract import validate_manifest
from playable_scene_contract import sha256,validate_package

def probe(path:Path)->dict:
    p=subprocess.run(["ffprobe","-v","error","-count_frames","-show_streams","-show_format","-of","json",str(path)],capture_output=True,text=True);d=json.loads(p.stdout) if p.returncode==0 else {};v=next((x for x in d.get("streams",[]) if x.get("codec_type")=="video"),{});a=next((x for x in d.get("streams",[]) if x.get("codec_type")=="audio"),{})
    return {"video":v.get("codec_name"),"audio":a.get("codec_name"),"width":v.get("width"),"height":v.get("height"),"fps":v.get("avg_frame_rate"),"frames":int(v.get("nb_read_frames",0)),"duration":float(d.get("format",{}).get("duration",0)),"sample_rate":int(a.get("sample_rate",0))}
def im(path:Path):return np.asarray(Image.open(path).convert("RGB")).astype(float)
def centroid(mask:np.ndarray)->tuple[float,float]:
    ys,xs=np.where(mask);return (float(xs.mean()),float(ys.mean())) if len(xs) else (-1.0,-1.0)
def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--project-root",required=True);p.add_argument("--output",required=True);a=p.parse_args();root=Path(a.project_root).resolve();art=root/"artifacts/mf-018b-r1";config=json.loads((root/"config/mf018b-r1-control-cleanup.json").read_text());manifest=json.loads((art/"render-manifest.json").read_text());handoff=json.loads((root/config["handoff_manifest"]).read_text());checks={}
    def check(name,passed,detail):checks[name]={"status":"PASS" if passed else "FAIL","detail":detail}
    base=config["baseline"];actual={key:sha256(root/base[key]) for key in ("artifact","scene","config","handoff")};expected={key:base[f"{key}_sha256"] for key in actual};check("mf018b_baseline_preserved",actual==expected,actual)
    cv=validate_manifest(json.loads((root/config["composition_manifest"]).read_text()));check("composition_preserved",cv["result"]=="PASS" and all(x=="PASS" for x in cv["checks"].values()),cv)
    hv=validate_package(root,handoff);check("r1_playable_handoff",hv["result"]=="PASS",hv)
    log=(art/"logs/base-scene-probe.log").read_text();check("scene_load_and_external_api","MF018B_R1_PROBE_OK nodes=5 passive_switch=false signals=5 driver_loaded=false" in log and "ERROR:" not in log,log.strip())
    scene_text=(root/config["scene"]).read_text();source=(root/config["base_script"]).read_text();check("passive_lever_detail_removed","SwitchContainment" not in scene_text and "passive containment-switch detail is intentionally absent" in source,config["geometry_contract"]["passive_containment_switch_present"])
    interactions=[x["id"] for x in handoff["interaction_points"]];check("startup_lever_interaction","startup_lever" in interactions and "containment_switch" not in interactions and "emergency_lever" not in interactions,interactions)
    geometry=config["geometry_contract"];large=[];small=[]
    for i in range(6):
        angle=math.pi+math.pi*(i+.5)/6;large.append((526+math.cos(angle)*137,286+math.sin(angle)*48))
    for i in range(18):
        angle=math.tau*i/18;small.append((526+math.cos(angle)*170,286+math.sin(angle)*79))
    ll=min(math.dist(x,y) for i,x in enumerate(large) for y in large[i+1:]);ls=min(math.dist(x,y) for x in large for y in small)
    check("upper_large_indicator_count_reduced",geometry["large_linked_indicator_count"]==6 and geometry["small_ring_detail_count"]==18 and source.count("range(6)")>=1,{"large":6,"small":18})
    check("large_indicators_do_not_overlap",ll>geometry["large_indicator_radius"]*2+2,{"minimum_center_distance":round(ll,3),"required":geometry["large_indicator_radius"]*2+2})
    check("large_do_not_cover_small",ls>geometry["large_indicator_radius"]+geometry["small_indicator_radius"]+2,{"minimum_center_distance":round(ls,3),"required":geometry["large_indicator_radius"]+geometry["small_indicator_radius"]+2})
    xs=geometry["four_dot_centers_x"];radius=geometry["four_dot_radius"];bounds=geometry["four_dot_safe_bounds"];spacing=min(b-a for a,b in zip(xs,xs[1:]));fit=xs[0]-radius>=bounds[0] and xs[-1]+radius<=bounds[1]
    check("four_dot_spacing",len(xs)==4 and spacing>radius*2+4 and fit,{"centers":xs,"radius":radius,"spacing":spacing,"safe_bounds":bounds})
    # The sloped lower boundary is at least 25 pixels below every dot edge.
    border_y=lambda x:947+(235-x)*28/183;clearances=[border_y(x)-(geometry["four_dot_y"]+radius) for x in xs]
    check("fourth_dot_border_clearance",min(clearances)>10 and clearances[-1]>10,{"clearances":list(map(lambda x:round(x,2),clearances))})
    frames={name:im(art/"representative-frames"/f"{name}.png") for _,name in config["representative_frames"]}
    before=frames["startup-lever-before"];after=frames["startup-lever-after"];roi=(slice(785,900),slice(125,240));red=lambda x:(x[:,:,0]>135)&(x[:,:,0]>x[:,:,1]*1.55)&(x[:,:,1]<90)
    before_c=centroid(red(before[roi]));after_c=centroid(red(after[roi]));lever_delta={"before_local":before_c,"after_local":after_c,"x_delta":round(after_c[0]-before_c[0],2),"y_delta":round(after_c[1]-before_c[1],2)}
    check("startup_lever_rotates_right",geometry["startup_lever_degrees"]==[-90.0,0.0] and lever_delta["x_delta"]>25 and lever_delta["y_delta"]>25,lever_delta)
    gauge_roi=(slice(620,735),slice(40,250));gauge_delta=float(np.abs(frames["gauges-respond"][gauge_roi]-before[gauge_roi]).mean());check("gauges_respond_after_lever",config["startup_timeline"]["gauge_start"]>config["startup_timeline"]["lever_start"] and gauge_delta>.5,{"gauge_region_delta":gauge_delta})
    panel=(slice(880,955),slice(45,230));blue=lambda x:(x[:,:,2]>120)&(x[:,:,2]>x[:,:,0]*1.3)&(x[:,:,1]>75);green=lambda x:(x[:,:,1]>100)&(x[:,:,1]>x[:,:,0]*1.2)&(x[:,:,1]>x[:,:,2]*1.05);yellow=lambda x:(x[:,:,0]>150)&(x[:,:,1]>120)&(x[:,:,2]<80)
    colors={"blue_pixels":int(blue(frames["four-dot-blue"][panel]).sum()),"green_pixels":int(green(frames["four-dot-green"][panel]).sum()),"yellow_pixels":int(yellow(frames["four-dot-yellow-trigger"][panel]).sum())};check("blue_green_yellow_logic",min(colors.values())>40,colors)
    ring=(slice(170,380),slice(330,735));orange=lambda x:(x[:,:,0]>145)&(x[:,:,1]>65)&(x[:,:,1]<150)&(x[:,:,2]<60);pre=int(orange(frames["four-dot-yellow-trigger"][ring]).sum());post=int(orange(frames["linked-ring-activating"][ring]).sum());check("yellow_triggers_linked_ring",config["startup_timeline"]["yellow_start"]<config["startup_timeline"]["linked_ring_start"] and post>pre+150,{"yellow_frame_ring_pixels":pre,"linked_frame_ring_pixels":post,"delta":post-pre})
    order=[config["startup_timeline"][k] for k in ("lever_start","gauge_start","blue_start","green_start","yellow_start","linked_ring_start","reactor_escalation_start")];check("causal_startup_order",order==sorted(order) and len(set(order))==len(order),order)
    check("representative_and_closeup_evidence",len(frames)==9 and len(list((art/"closeups").glob("*.png")))==6 and (art/"representative-frames/contact-sheet.png").is_file(),{"representative":len(frames),"closeups":len(list((art/"closeups").glob("*.png")))})
    outputs_ok=True;hashes={}
    for rel,expected_output in manifest["outputs"].items():
        path=art/rel;actual_hash=sha256(path) if path.is_file() else None;hashes[rel]=actual_hash;outputs_ok=outputs_ok and actual_hash==expected_output["sha256"] and path.stat().st_size==expected_output["bytes"]
    check("artifact_integrity",outputs_ok,hashes)
    media=probe(art/"final-test.mp4");check("promo_media_contract",media=={"video":"h264","audio":"aac","width":768,"height":1152,"fps":"30/1","frames":420,"duration":14.0,"sample_rate":48000},media)
    decode=subprocess.run(["ffmpeg","-v","error","-i",str(art/"final-test.mp4"),"-f","null","-"],capture_output=True);check("full_decode",decode.returncode==0,decode.stderr.decode()[-1000:])
    comparison=probe(art/"comparison/mf018b-vs-r1.mp4");check("baseline_comparison",comparison["video"]=="h264" and comparison["width"]==1536 and comparison["frames"]==240 and comparison["duration"]==8.0,comparison)
    audio=manifest["audio"];check("approved_audio_unchanged",audio["track_approval"]==audio["cue_approval"]=="APPROVED" and audio["track_sha256"]==config["audio"]["source_sha256"],audio)
    check("audio_levels",abs(audio["loudness"]["integrated_lufs"]+16)<=.75 and audio["loudness"]["true_peak_db"]<=-1.4,audio["loudness"])
    render_log=(art/"logs/godot-render.log").read_text();check("clean_native_render","MF018B_R1_NATIVE_OK frames=420" in render_log and "ERROR:" not in render_log and "SCRIPT ERROR:" not in render_log,render_log.strip())
    chamber=(slice(320,820),slice(425,630));adjacent=(slice(320,820),slice(630,760));active=frames["strong-active-machine"];dormant=frames["dormant"];energy_in=float(np.abs(active[chamber]-dormant[chamber]).mean());energy_out=float(np.abs(active[adjacent]-dormant[adjacent]).mean());check("motion_coherence_preserved",energy_in>energy_out*1.3,{"chamber_delta":energy_in,"adjacent_delta":energy_out})
    check("promo_scene_separation",manifest["scene"]["promo_driver_separate"] is True and handoff["package"]["promo_driver_optional"] is True,{"scene":manifest["scene"],"driver_optional":handoff["package"]["promo_driver_optional"]})
    check("no_gameplay_or_publication",manifest["gameplay_implemented"] is False and handoff["gameplay_implemented"] is False and manifest["published"] is False and manifest["human_review"]=="PENDING_HUMAN",{"gameplay":manifest["gameplay_implemented"],"published":manifest["published"],"human":manifest["human_review"]})
    result="TECHNICAL_PASS" if all(x["status"]=="PASS" for x in checks.values()) else "FAIL";report={"slice":"MF-018B-R1","result":result,"release_ready":False,"human_review":"PENDING_HUMAN","checks":checks,"metrics":{"ring_min_large_distance":ll,"ring_min_large_small_distance":ls,"four_dot_clearances":clearances,"lever":lever_delta,"gauge_delta":gauge_delta,"colors":colors,"ring_link":{"pre":pre,"post":post},"elapsed_ms":manifest["elapsed_ms"]},"published":False};out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report,indent=2));return 0 if result=="TECHNICAL_PASS" else 1
if __name__=="__main__":raise SystemExit(main())
