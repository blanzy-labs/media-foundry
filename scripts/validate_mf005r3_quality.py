#!/usr/bin/env python3
"""Validate measured R3 fade envelopes, audio limits, timing, and release safeguards."""

import argparse,json,math,struct,wave
from pathlib import Path


def pcm(path):
    with wave.open(str(path),"rb") as source:
        if source.getframerate()!=48000 or source.getnchannels()!=1 or source.getsampwidth()!=2: raise ValueError("QUALITY_AUDIO_FAILED: expected 48 kHz mono PCM16")
        return [item[0]/32768 for item in struct.iter_unpack("<h",source.readframes(source.getnframes()))],source.getframerate()


def envelope_check(stem,reference,fade_in,fade_out,rate):
    if len(stem)!=len(reference) or fade_in<=0 or fade_out<=0: return {"result":"FAIL","error":"required stem fades are missing or inputs differ"}
    duration=len(stem)/rate; errors=[]; sampled=0
    for index,(actual,control) in enumerate(zip(stem,reference)):
        t=index/rate
        if t>=fade_in and t<=duration-fade_out: continue
        if abs(control)<0.004: continue
        expected=min(1.0,t/fade_in,max(0.0,(duration-t)/fade_out)); ratio=abs(actual/control); errors.append(abs(ratio-expected)); sampled+=1
    mae=sum(errors)/len(errors) if errors else 999
    start_ratio=sum(abs(stem[i]) for i in range(round(.1*rate)))/max(1e-9,sum(abs(reference[i]) for i in range(round(.1*rate))))
    end_start=round((duration-.1)*rate); end_ratio=sum(abs(stem[i]) for i in range(end_start,len(stem)))/max(1e-9,sum(abs(reference[i]) for i in range(end_start,len(stem))))
    return {"fade_in_seconds":fade_in,"fade_out_seconds":fade_out,"sampled_non_silent_points":sampled,"envelope_mean_absolute_error":round(mae,6),"first_100ms_gain_ratio":round(start_ratio,6),"last_100ms_gain_ratio":round(end_ratio,6),"result":"PASS" if sampled>100 and mae<0.035 and start_ratio<0.35 and end_ratio<0.2 else "FAIL"}


def main():
    parser=argparse.ArgumentParser()
    for name in ("fixture","music_stem","music_reference","narration","mix","mix_validation","layout","contract","output"): parser.add_argument(f"--{name.replace('_','-')}",required=True)
    args=parser.parse_args(); errors=[]
    try:
        fixture=json.loads(Path(args.fixture).read_text()); narration=json.loads(Path(args.narration).read_text()); mix=json.loads(Path(args.mix).read_text()); final=json.loads(Path(args.mix_validation).read_text()); layout=json.loads(Path(args.layout).read_text()); contract=json.loads(Path(args.contract).read_text())
        stem,rate=pcm(Path(args.music_stem)); reference,_=pcm(Path(args.music_reference)); music=fixture.get("music",{}); fade=envelope_check(stem,reference,float(music.get("fade_in",0)),float(music.get("fade_out",0)),rate)
        if fade["result"]!="PASS": errors.append("MUSIC_FADE_ENVELOPE_FAILED: measured stem envelope does not match required fades")
        loudness=final.get("loudness",{}); integrated=float(loudness.get("integrated_lufs",999)); peak=float(loudness.get("true_peak_db",999))
        if not -17<=integrated<=-15 or peak>-1.0 or mix.get("clipped_samples")!=0: errors.append("FINAL_LOUDNESS_FAILED: loudness, true peak, or clipping is outside v1 limits")
        duck=float(music.get("narration_duck_db",0)); attack=float(music.get("attack_ms",0)); release=float(music.get("release_ms",0)); gain=float(music.get("gain_db",0))
        if not -12<=duck<=-5 or not 50<=attack<=180 or not 120<=release<=400 or gain>-2: errors.append("MUSIC_MASKING_FAILED: bed/ducking configuration exceeds production guardrails")
        duration=float(fixture["format"]["duration_seconds"]); segments=narration.get("segments",[])
        if not segments or any(float(item["end"])>float(item["speech_window_end"])+.001 or float(item["end"])>=duration-.5 for item in segments): errors.append("NARRATION_TAIL_FAILED: narration escapes its beat or approaches final boundary")
        beats={beat["id"]:beat for beat in fixture["beats"]}; dung=next((item for item in segments if item["beat"]=="dung_beetle"),None); punch=beats.get("punchline")
        pause=float(punch["start"] if "start" in punch else next(item["start"] for item in json.loads(Path(args.narration).read_text()).get("segments",[]) if item["beat"]=="punchline"))-float(dung["end"]) if dung else 0
        if pause<.3: errors.append("COMEDIC_PAUSE_FAILED: pause before punchline is not deliberate")
        outro_layout=layout.get("layout",{}).get("beat_6",{})
        if layout.get("result")!="PASS" or outro_layout.get("status")!="PASS" or int(outro_layout.get("font_size",0))<30 or len(fixture.get("outro",{}).get("tagline",""))>24: errors.append("OUTRO_READABILITY_FAILED: simplified outro is outside readable range")
        if contract.get("result")!="PASS": errors.append("PRODUCTION_CONTRACT_FAILED: creative/asset contract did not pass")
        checks={"music_fade_in":"PASS" if fade["result"]=="PASS" else "FAIL","music_fade_out":"PASS" if fade["result"]=="PASS" else "FAIL","narration_sync":"PASS" if not any("NARRATION" in item for item in errors) else "FAIL","comedic_pause":"PASS" if not any("COMEDIC" in item for item in errors) else "FAIL","loudness_peak":"PASS" if not any("LOUDNESS" in item for item in errors) else "FAIL","music_voice_priority":"PASS" if not any("MASKING" in item for item in errors) else "FAIL","outro_readability":"PASS" if not any("OUTRO" in item for item in errors) else "FAIL","full_decode":final.get("checks",{}).get("full_decode","FAIL")}
        technical="PASS" if not errors and all(value=="PASS" for value in checks.values()) else "FAIL"; voice_release=contract.get("voice",{}).get("release_eligible") is True
        result={"slice":"MF-005R3","fixture":fixture.get("id"),"candidate":fixture.get("candidate"),"checks":checks,"fade_measurement":fade,"comedic_pause_seconds":round(pause,6),"audio":{"integrated_lufs":integrated,"true_peak_db":peak,"music_gain_db":gain,"duck_db":duck,"attack_ms":attack,"release_ms":release},"gates":{"technical":technical,"editorial":"PENDING_HUMAN","release":"PENDING_HUMAN" if voice_release else "BLOCKED_VOICE_ASSET"},"errors":errors,"result":technical}
    except (OSError,json.JSONDecodeError,KeyError,TypeError,ValueError,wave.Error,ZeroDivisionError) as error: result={"slice":"MF-005R3","errors":[str(error)],"gates":{"technical":"FAIL","editorial":"PENDING_HUMAN","release":"BLOCKED"},"result":"FAIL"}
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps(result,indent=2)); return 0 if result["result"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
