#!/usr/bin/env python3
"""Render MF-018B-R1 control cleanup and causal startup evidence."""
from __future__ import annotations
import argparse,json,shutil,subprocess,sys,tempfile,time
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from composition_contract import validate_manifest
from playable_scene_contract import sha256,validate_package
from run_mf018b import FONT,approved_audio,measure_audio,run_checked,write_json

def sheet(paths:list[Path],labels:list[str],output:Path)->None:
    font=ImageFont.truetype(FONT,18);canvas=Image.new("RGB",(768,1134),(3,9,8));draw=ImageDraw.Draw(canvas)
    for i,(path,label) in enumerate(zip(paths,labels)):
        im=Image.open(path).convert("RGB").resize((240,360),Image.Resampling.LANCZOS);x=12+i%3*252;y=62+i//3*374;canvas.paste(im,(x,y));seconds,name=label.split(" ",1);draw.text((x,y-44),seconds,font=font,fill=(230,185,5));draw.text((x,y-22),name.upper(),font=font,fill=(224,201,139))
    canvas.save(output,optimize=True)
def closeup(source:Path,kind:str,label:str,output:Path)->None:
    image=Image.open(source).convert("RGB");box=(320,150,748,420) if kind=="ring" else (30,710,270,1000);crop=image.crop(box).resize((856,540) if kind=="ring" else (480,580),Image.Resampling.LANCZOS);canvas=Image.new("RGB",(crop.width,crop.height+54),(3,9,8));canvas.paste(crop,(0,54));draw=ImageDraw.Draw(canvas);draw.text((18,14),label.upper(),font=ImageFont.truetype(FONT,25),fill=(230,185,5));canvas.save(output,optimize=True)
def comparison(left:Path,right:Path,output:Path)->None:
    a=Image.open(left).convert("RGB").resize((384,576),Image.Resampling.LANCZOS);b=Image.open(right).convert("RGB").resize((384,576),Image.Resampling.LANCZOS);c=Image.new("RGB",(768,636),(3,9,8));c.paste(a,(0,60));c.paste(b,(384,60));d=ImageDraw.Draw(c);f=ImageFont.truetype(FONT,27);d.text((18,17),"MF-018B BASELINE",font=f,fill=(224,201,139));d.text((402,17),"MF-018B-R1 CLEANUP",font=f,fill=(230,185,5));c.save(output,optimize=True)
def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--project-root",default=".");p.add_argument("--config",default="config/mf018b-r1-control-cleanup.json");p.add_argument("--artifacts",default="artifacts/mf-018b-r1");a=p.parse_args();root=Path(a.project_root).resolve();config_path=root/a.config;art=root/a.artifacts
    if art.exists():raise SystemExit(f"refusing to overwrite: {art}")
    d=json.loads(config_path.read_text());base=d["baseline"]
    for key,hash_key in (("artifact","artifact_sha256"),("scene","scene_sha256"),("config","config_sha256"),("handoff","handoff_sha256")):
        if sha256(root/base[key])!=base[hash_key]:raise SystemExit(f"MF-018B baseline {key} changed")
    composition=json.loads((root/d["composition_manifest"]).read_text());cv=validate_manifest(composition);handoff_path=root/d["handoff_manifest"];handoff=json.loads(handoff_path.read_text());hv=validate_package(root,handoff)
    if cv["result"]!="PASS" or hv["result"]!="PASS":raise SystemExit("composition or handoff invalid")
    music,track,cue=approved_audio(root,d["audio"])
    for folder in (art,art/"representative-frames",art/"closeups",art/"comparison",art/"validation",art/"logs"):folder.mkdir(parents=True,exist_ok=True)
    started=time.monotonic();fps=d["video"]["fps"];duration=d["video"]["duration_seconds"];count=round(fps*duration)
    probe=run_checked(["godot","--headless","--path",str(root/"godot"),"--script","mf018b_r1_contract_probe.gd"],art/"logs/base-scene-probe.log",True)
    if "MF018B_R1_PROBE_OK" not in probe:raise RuntimeError("R1 probe marker missing")
    with tempfile.TemporaryDirectory(prefix="mf018b-r1-") as temp_name:
        temp=Path(temp_name);frames=temp/"frames";video=temp/"video.mp4";render=run_checked(["godot","--headless","--path",str(root/"godot"),"--script","mf018b_r1_render.gd","--","--config",str(config_path),"--output",str(frames)],art/"logs/godot-render.log",True)
        if "MF018B_R1_NATIVE_OK" not in render or len(list(frames.glob("frame-*.png")))!=count:raise RuntimeError("R1 render incomplete")
        run_checked(["ffmpeg","-y","-v","error","-framerate",str(fps),"-i",str(frames/"frame-%04d.png"),"-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart","-metadata","creation_time=1970-01-01T00:00:00Z","-t",str(duration),str(video)],art/"logs/video-encode.log")
        audio=d["audio"];fade=duration-audio["fade_out_seconds"];af=f"atrim=start={audio['start_seconds']}:end={audio['end_seconds']},asetpts=PTS-STARTPTS,afade=t=in:st=0:d={audio['fade_in_seconds']},afade=t=out:st={fade}:d={audio['fade_out_seconds']},loudnorm=I={audio['target_lufs']}:TP={audio['true_peak_db']}:LRA=8,volume={audio['post_normalization_gain_db']}dB";final=art/"final-test.mp4"
        run_checked(["ffmpeg","-y","-v","error","-i",str(video),"-i",str(music),"-filter_complex",f"[1:a]{af}[a]","-map","0:v:0","-map","[a]","-t",str(duration),"-c:v","copy","-c:a","aac","-b:a","192k","-ar","48000","-movflags","+faststart","-metadata","creation_time=1970-01-01T00:00:00Z",str(final)],art/"logs/audio-mux.log")
        reps=[];labels=[]
        for seconds,label in d["representative_frames"]:
            target=art/"representative-frames"/f"{label}.png";shutil.copy2(frames/f"frame-{round(seconds*fps):04d}.png",target);reps.append(target);labels.append(f"{seconds:.1f}s {label}")
        for seconds,label in d["closeups"]:
            kind="ring" if "ring" in label else "panel";closeup(frames/f"frame-{round(seconds*fps):04d}.png",kind,f"{seconds:.1f}s {label}",art/"closeups"/f"{label}.png")
    sheet(reps,labels,art/"representative-frames/contact-sheet.png");comparison(root/"artifacts/mf-018b/representative-frames/stable.png",art/"representative-frames/linked-ring-activating.png",art/"comparison/mf018b-vs-r1.png")
    run_checked(["ffmpeg","-y","-v","error","-t","8","-i",str(root/base["artifact"]),"-t","8","-i",str(final),"-filter_complex",f"[0:v]setpts=PTS-STARTPTS,drawtext=fontfile={FONT}:text=MF-018B BASELINE:x=24:y=24:fontsize=32:fontcolor=0xE0C98B[v0];[1:v]setpts=PTS-STARTPTS,drawtext=fontfile={FONT}:text=MF-018B-R1 STARTUP:x=24:y=24:fontsize=32:fontcolor=0xE6B905[v1];[v0][v1]hstack=inputs=2[v]","-map","[v]","-an","-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart","-t","8",str(art/"comparison/mf018b-vs-r1.mp4")],art/"logs/comparison-encode.log")
    selection={"track":track["qualified_id"],"track_sha256":sha256(music),"track_approval":track["approval"]["status"],"cue":cue["id"],"cue_approval":cue["approval"]["status"],"actual_start":audio["start_seconds"],"actual_end":audio["end_seconds"],"loudness":measure_audio(final),"event_markers":audio["event_markers"],"dedicated_sfx_added":False,"result":"PASS"};write_json(art/"validation/audio-selection.json",selection);write_json(art/"validation/handoff-validation.json",hv);write_json(art/"validation/composition-validation.json",cv)
    files=[final,art/"representative-frames/contact-sheet.png",art/"comparison/mf018b-vs-r1.png",art/"comparison/mf018b-vs-r1.mp4"]+reps+sorted((art/"closeups").glob("*.png"));outputs={str(x.relative_to(art)):{"sha256":sha256(x),"bytes":x.stat().st_size} for x in files}
    manifest={"slice":"MF-018B-R1","config":str(config_path),"config_sha256":sha256(config_path),"seed":d["seed"],"baseline":base,"scene":{"path":d["scene"],"sha256":sha256(root/d["scene"]),"standalone_probe":"PASS","promo_driver_separate":True},"handoff":{"path":d["handoff_manifest"],"sha256":sha256(handoff_path),"validation":"PASS"},"geometry_contract":d["geometry_contract"],"startup_timeline":d["startup_timeline"],"video":{**d["video"],"frame_count":count},"audio":selection,"outputs":outputs,"elapsed_ms":round((time.monotonic()-started)*1000),"human_review":"PENDING_HUMAN","release_ready":False,"gameplay_implemented":False,"published":False};write_json(art/"render-manifest.json",manifest);print(json.dumps(manifest,indent=2));return 0
if __name__=="__main__":sys.exit(main())
