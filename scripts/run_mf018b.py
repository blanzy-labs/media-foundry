#!/usr/bin/env python3
"""Build the refined MF-018B native promo and playable-scene evidence."""
from __future__ import annotations
import argparse,json,re,shutil,subprocess,sys,tempfile,time
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from composition_contract import validate_manifest
from playable_scene_contract import sha256,validate_package

FONT="/usr/share/fonts/opentype/urw-base35/NimbusSansNarrow-Bold.otf"

def write_json(path:Path,value:dict)->None:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+"\n")
def run_checked(command:list[str],log:Path,engine:bool=False)->str:
    p=subprocess.run(command,capture_output=True,text=True);rendered=p.stdout+p.stderr;log.parent.mkdir(parents=True,exist_ok=True);log.write_text(rendered)
    if p.returncode or (engine and ("ERROR:" in rendered or "SCRIPT ERROR:" in rendered)):raise RuntimeError(f"command failed ({p.returncode}); see {log}")
    return rendered
def approved_audio(root:Path,d:dict):
    catalog=json.loads((root/d["catalog"]).read_text());track=next((x for x in catalog["tracks"] if x["qualified_id"]==d["qualified_id"]),None)
    cue=next((x for x in track.get("cue_regions",[]) if x["id"]==d["cue_region"]),None) if track else None;source=root/d["source"];actual=sha256(source) if source.is_file() else None
    if not track or not cue or actual!=d["source_sha256"] or actual!=track["integrity"]["sha256"]:raise ValueError("audio source/catalog invalid")
    if track["approval"]["status"]!="APPROVED" or cue["approval"]["status"]!="APPROVED" or track["approval"]["approved_sha256"]!=actual or cue["approval"]["approved_sha256"]!=actual:raise ValueError("audio approval invalid")
    if not cue["usable_start"]<=d["start_seconds"]<d["end_seconds"]<=cue["usable_end"]:raise ValueError("audio excerpt outside approved cue")
    return source,track,cue
def measure_audio(path:Path)->dict:
    p=subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",str(path),"-vn","-af","loudnorm=I=-16:TP=-1.5:LRA=8:print_format=json","-f","null","-"],capture_output=True,text=True)
    blocks=re.findall(r'\{\s*"input_i".*?\}',p.stderr,re.DOTALL)
    if p.returncode or not blocks:raise RuntimeError("audio measurement failed")
    v=json.loads(blocks[-1]);return {"integrated_lufs":float(v["input_i"]),"true_peak_db":float(v["input_tp"]),"loudness_range_lu":float(v["input_lra"])}
def contact_sheet(paths:list[Path],labels:list[str],output:Path)->None:
    font=ImageFont.truetype(FONT,18);canvas=Image.new("RGB",(800,724),(4,10,9));draw=ImageDraw.Draw(canvas)
    for i,(path,label) in enumerate(zip(paths,labels)):
        im=Image.open(path).convert("RGB").resize((188,282),Image.Resampling.LANCZOS);x=8+i%4*198;y=66+i//4*340;canvas.paste(im,(x,y));seconds,name=label.split(" ",1)
        draw.text((x,y-47),seconds,font=font,fill=(230,185,5));draw.text((x,y-25),name.upper(),font=font,fill=(224,201,139))
    canvas.save(output,optimize=True)
def interaction_diagnostic(source:Path,output:Path)->None:
    im=Image.open(source).convert("RGB");d=ImageDraw.Draw(im);title=ImageFont.truetype(FONT,25);font=ImageFont.truetype(FONT,18);cyan=(78,230,255);dark=(3,15,14)
    d.rectangle((28,132,326,336),fill=dark,outline=cyan,width=3);d.text((44,146),"PLAYABLE SCENE HOOKS",font=title,fill=cyan)
    entries=[("coolant_dial",(93,803)),("field_dial",(165,803)),("containment_switch",(93,852)),("emergency_lever",(203,824)),("reactor_energy",(526,560)),("warning_ring",(526,200))]
    for i,(label,point) in enumerate(entries):
        y=188+i*23;d.text((45,y),label,font=font,fill=(232,255,255));d.line((326,y+10,point[0],point[1]),fill=cyan,width=2);d.ellipse((point[0]-12,point[1]-12,point[0]+12,point[1]+12),outline=cyan,width=3)
    d.text((44,313),"DEBUG ONLY — NOT IN PROMO",font=font,fill=(230,185,5));im.save(output,optimize=True)
def static_comparison(left:Path,right:Path,output:Path)->None:
    a=Image.open(left).convert("RGB").resize((384,576),Image.Resampling.LANCZOS);b=Image.open(right).convert("RGB").resize((384,576),Image.Resampling.LANCZOS);c=Image.new("RGB",(768,636),(4,10,9));c.paste(a,(0,60));c.paste(b,(384,60));d=ImageDraw.Draw(c);f=ImageFont.truetype(FONT,27);d.text((18,17),"MF-018A NATIVE V1",font=f,fill=(224,201,139));d.text((402,17),"MF-018B REFINED",font=f,fill=(230,185,5));c.save(output,optimize=True)

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--project-root",default=".");p.add_argument("--config",default="config/mf018b-native-pulp-scene.json");p.add_argument("--artifacts",default="artifacts/mf-018b");a=p.parse_args();root=Path(a.project_root).resolve();config_path=root/a.config;artifacts=root/a.artifacts
    if artifacts.exists():raise SystemExit(f"refusing to overwrite: {artifacts}")
    definition=json.loads(config_path.read_text());baseline=root/definition["baseline"]["artifact"]
    if not baseline.is_file() or sha256(baseline)!=definition["baseline"]["artifact_sha256"]:raise SystemExit("MF-018A baseline missing or changed")
    if sha256(root/definition["baseline"]["config"])!=definition["baseline"]["config_sha256"]:raise SystemExit("MF-018A config changed")
    composition_path=root/definition["composition_manifest"];composition=json.loads(composition_path.read_text());composition_result=validate_manifest(composition)
    if composition_result["result"]!="PASS":raise SystemExit("MF-018B composition failed")
    handoff_path=root/definition["handoff_manifest"];handoff=json.loads(handoff_path.read_text());handoff_result=validate_package(root,handoff)
    if handoff_result["result"]!="PASS":raise SystemExit(json.dumps(handoff_result,indent=2))
    music,track,cue=approved_audio(root,definition["audio"])
    for d in (artifacts,artifacts/"representative-frames",artifacts/"static-keyframes",artifacts/"interaction-diagnostic",artifacts/"comparison",artifacts/"validation",artifacts/"logs"):d.mkdir(parents=True,exist_ok=True)
    started=time.monotonic();duration=definition["video"]["duration_seconds"];fps=definition["video"]["fps"];frame_count=round(duration*fps)
    probe=run_checked(["godot","--headless","--path",str(root/"godot"),"--script","mf018b_contract_probe.gd","--","--manifest",str(handoff_path)],artifacts/"logs/base-scene-probe.log",True)
    if "MF018B_CONTRACT_PROBE_OK" not in probe:raise RuntimeError("base-scene probe marker missing")
    with tempfile.TemporaryDirectory(prefix="mf018b-") as name:
        temp=Path(name);frames=temp/"frames";video=temp/"video-only.mp4";godot=run_checked(["godot","--headless","--path",str(root/"godot"),"--script","mf018b_render.gd","--","--config",str(config_path),"--output",str(frames)],artifacts/"logs/godot-render.log",True)
        if "MF018B_NATIVE_SCENE_OK" not in godot or len(list(frames.glob("frame-*.png")))!=frame_count:raise RuntimeError("Godot render incomplete")
        run_checked(["ffmpeg","-y","-v","error","-framerate",str(fps),"-i",str(frames/"frame-%04d.png"),"-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart","-metadata","creation_time=1970-01-01T00:00:00Z","-t",str(duration),str(video)],artifacts/"logs/video-encode.log")
        audio=definition["audio"];fade=duration-audio["fade_out_seconds"];af=f"atrim=start={audio['start_seconds']}:end={audio['end_seconds']},asetpts=PTS-STARTPTS,afade=t=in:st=0:d={audio['fade_in_seconds']},afade=t=out:st={fade}:d={audio['fade_out_seconds']},loudnorm=I={audio['target_lufs']}:TP={audio['true_peak_db']}:LRA=8,volume={audio['post_normalization_gain_db']}dB";final=artifacts/"final-test.mp4"
        run_checked(["ffmpeg","-y","-v","error","-i",str(video),"-i",str(music),"-filter_complex",f"[1:a]{af}[a]","-map","0:v:0","-map","[a]","-t",str(duration),"-c:v","copy","-c:a","aac","-b:a","192k","-ar","48000","-movflags","+faststart","-metadata","creation_time=1970-01-01T00:00:00Z",str(final)],artifacts/"logs/audio-mux.log")
        reps=[];labels=[]
        for seconds,label in definition["representative_frames"]:
            target=artifacts/"representative-frames"/f"{label}.png";shutil.copy2(frames/f"frame-{min(frame_count-1,round(seconds*fps)):04d}.png",target);reps.append(target);labels.append(f"{seconds:.1f}s {label}")
        for item in definition["static_states"]:shutil.copy2(frames/f"frame-{round(item['seconds']*fps):04d}.png",artifacts/"static-keyframes"/f"{item['id']}.png")
        interaction_diagnostic(frames/"interaction-diagnostic.png",artifacts/"interaction-diagnostic/controls-and-state.png")
    contact_sheet(reps,labels,artifacts/"representative-frames/contact-sheet.png");static_comparison(root/"artifacts/mf-018a/static-keyframes/peak.png",artifacts/"static-keyframes/critical.png",artifacts/"comparison/mf018a-vs-mf018b.png")
    run_checked(["ffmpeg","-y","-v","error","-ss","8","-t","4","-i",str(baseline),"-ss","8","-t","4","-i",str(final),"-filter_complex",f"[0:v]setpts=PTS-STARTPTS,drawtext=fontfile={FONT}:text=MF-018A NATIVE V1:x=24:y=24:fontsize=32:fontcolor=0xE0C98B[v0];[1:v]setpts=PTS-STARTPTS,drawtext=fontfile={FONT}:text=MF-018B REFINED:x=24:y=24:fontsize=32:fontcolor=0xE6B905[v1];[v0][v1]hstack=inputs=2[v]","-map","[v]","-an","-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart","-t","4",str(artifacts/"comparison/mf018a-vs-mf018b.mp4")],artifacts/"logs/comparison-encode.log")
    selection={"track_id":track["id"],"qualified_id":track["qualified_id"],"track_path":track["source"],"track_sha256":sha256(music),"track_approval":track["approval"]["status"],"cue_id":cue["id"],"cue_approval":cue["approval"]["status"],"usable_start":cue["usable_start"],"usable_end":cue["usable_end"],"actual_start":audio["start_seconds"],"actual_end":audio["end_seconds"],"direction":audio["direction"],"loudness":measure_audio(final),"object_event_hooks":[x["id"] for x in handoff["audio_events"]],"dedicated_sfx_embedded":False,"result":"PASS"}
    write_json(artifacts/"validation/audio-selection.json",selection);write_json(artifacts/"validation/handoff-validation.json",handoff_result);write_json(artifacts/"validation/composition-validation.json",composition_result)
    files=[final,artifacts/"representative-frames/contact-sheet.png",artifacts/"interaction-diagnostic/controls-and-state.png",artifacts/"comparison/mf018a-vs-mf018b.png",artifacts/"comparison/mf018a-vs-mf018b.mp4"]+reps+sorted((artifacts/"static-keyframes").glob("*.png"));outputs={str(x.relative_to(artifacts)):{"sha256":sha256(x),"bytes":x.stat().st_size} for x in files}
    manifest={"slice":"MF-018B","mode":definition["mode"],"config":str(config_path),"config_sha256":sha256(config_path),"seed":definition["seed"],"baseline":definition["baseline"],"base_scene":{"path":definition["scene"],"sha256":sha256(root/definition["scene"]),"promo_driver_separate":True,"standalone_probe":"PASS"},"handoff":{"path":definition["handoff_manifest"],"sha256":sha256(handoff_path),"validation":"PASS","game_foundry_dependencies":0},"composition":{"path":definition["composition_manifest"],"machine_validation":"PASS","human_status":composition["approval"]["human_status"]},"video":{**definition["video"],"frame_count":frame_count},"audio":selection,"outputs":outputs,"raw_frames_retained":False,"elapsed_ms":round((time.monotonic()-started)*1000),"human_review":"PENDING_HUMAN","release_ready":False,"published":False};write_json(artifacts/"render-manifest.json",manifest);print(json.dumps(manifest,indent=2));return 0
if __name__=="__main__":sys.exit(main())
