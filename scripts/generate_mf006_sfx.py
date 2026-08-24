#!/usr/bin/env python3
"""Generate deterministic physical/electronic MF-006 foreground SFX."""

import argparse,json,math,random,struct,wave
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--fixture",required=True); parser.add_argument("--output",required=True); parser.add_argument("--report",required=True); args=parser.parse_args()
    fixture=json.loads(Path(args.fixture).read_text()); rate=48000; duration=float(fixture["format"]["duration_seconds"]); events=fixture.get("sfx",[]); samples=[0.0]*round(duration*rate); evidence=[]
    for ordinal,event in enumerate(events):
        start=float(event["time"]); kind=event["type"]; gain=float(event["gain"]); rng=random.Random(int(fixture["seed"])+ordinal*7919)
        lengths={"electronic_motion":1.45,"circuit_draw":.55,"energy_flow":1.1,"central_overload":.3,"overload_rise":.72,"spark_burst":.48,"book_formation":.55,"book_open":.42,"page_flip":.28,"book_close":.48,"data_dissolve":1.15,"cta_energy":.8,"projection_emission":.8,"projection_shift":.42,"projection_refresh":.38,"projection_collapse":1.0,"target_lock":.3,"bridge_lock":.46,"hidden_reveal":.42,"cta_resolve":.52}; span=lengths[kind]
        for offset in range(round(span*rate)):
            t=offset/rate; envelope=(1-t/span)**2; value=0.0
            if kind=="electronic_motion": value=math.sin(2*math.pi*(92+35*t)*t)*(0.45+0.55*math.sin(2*math.pi*7*t)**2)
            elif kind=="circuit_draw": value=math.sin(2*math.pi*(118+310*t)*t)*(0.4+0.6*math.sin(2*math.pi*13*t)**2)
            elif kind=="energy_flow": value=math.sin(2*math.pi*(155+95*t)*t)*(0.3+0.7*math.sin(2*math.pi*8*t)**4)
            elif kind=="central_overload": value=math.sin(2*math.pi*(180+1450*t*t)*t)+(rng.random()*2-1)*0.18
            elif kind=="overload_rise": value=.58*math.sin(2*math.pi*(120+780*t*t)*t)+.22*math.sin(2*math.pi*(38+95*t)*t)+(rng.random()*2-1)*.08
            elif kind=="spark_burst": value=(rng.random()*2-1)*envelope+0.5*math.sin(2*math.pi*(900+1600*t)*t)
            elif kind=="book_formation": value=math.sin(2*math.pi*(72-18*t)*t)+0.3*math.sin(2*math.pi*181*t)
            elif kind in {"book_open","book_close"}: value=0.65*math.sin(2*math.pi*(135+95*t)*t)+(rng.random()*2-1)*0.28
            elif kind=="page_flip": value=(rng.random()*2-1)*math.sin(math.pi*min(1,t/span)) + 0.25*math.sin(2*math.pi*220*t)
            elif kind=="data_dissolve": value=0.5*math.sin(2*math.pi*(610+1800*t)*t)+(rng.random()*2-1)*0.2
            elif kind=="cta_energy": value=math.sin(2*math.pi*(105+225*t)*t)*(0.55+0.45*math.sin(2*math.pi*6*t)**2)
            elif kind=="projection_emission": value=math.sin(2*math.pi*(165+520*t)*t)+.28*math.sin(2*math.pi*670*t)
            elif kind=="projection_shift": value=.65*math.sin(2*math.pi*(330+290*t)*t)+(rng.random()*2-1)*.15
            elif kind=="projection_refresh": value=.5*math.sin(2*math.pi*(480-130*t)*t)+(rng.random()*2-1)*.11
            elif kind=="projection_collapse": value=math.sin(2*math.pi*(760-610*t)*t)+.2*(rng.random()*2-1)
            elif kind=="target_lock": value=.5*math.sin(2*math.pi*410*t)+.32*math.sin(2*math.pi*615*t)
            elif kind=="bridge_lock": value=.4*math.sin(2*math.pi*330*t)+.4*math.sin(2*math.pi*(495+55*t)*t)
            elif kind=="hidden_reveal": value=.5*math.sin(2*math.pi*(270+440*t)*t)+.18*(rng.random()*2-1)
            elif kind=="cta_resolve": value=.55*math.sin(2*math.pi*(180-45*t)*t)+.3*math.sin(2*math.pi*360*t)
            index=round(start*rate)+offset
            if index<len(samples): samples[index]+=gain*envelope*value
        evidence.append({"id":event["id"],"event":event["event"],"time":start,"type":kind,"duration":span,"gain":gain})
    peak=max(abs(value) for value in samples); samples=[max(-1,min(1,value)) for value in samples]; output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(output),"wb") as target:
        target.setnchannels(1); target.setsampwidth(2); target.setframerate(rate); target.writeframes(b"".join(struct.pack("<h",round(value*32767)) for value in samples))
    report={"slice":"MF-006","duration":duration,"sample_rate":rate,"channels":1,"event_count":len(events),"events":evidence,"pre_clamp_peak":round(peak,6),"clipped_samples":sum(abs(value)>1 for value in samples),"result":"PASS" if events and peak<1 else "FAIL"}; Path(args.report).write_text(json.dumps(report,indent=2)+"\n"); print(json.dumps(report,indent=2)); return 0 if report["result"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
