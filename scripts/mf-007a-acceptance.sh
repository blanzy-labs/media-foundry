#!/usr/bin/env bash
set -Eeuo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
fixture=$root/content/fixtures/mf007a-unknown-process-audio.json
source_media=$root/artifacts/mf-006r9/candidate-a.mp4
source_narration=$root/artifacts/mf-006r9/timelines/narration.json
art=${MF_ARTIFACT_DIR:-$root/artifacts/mf-007a}
rep=${MF_REPORT_DIR:-$root/reports/mf-007a}
mkdir -p "$art"/{audio/ambient,audio/narration,audio/sfx,audio/mixes,logs,timelines,validation,waveforms} "$rep"

fail() {
  code=$?
  python3 - "$rep/result.json" "$code" <<'PY'
import json,pathlib,sys
pathlib.Path(sys.argv[1]).write_text(json.dumps({"slice":"MF-007A","result":"FAIL","exit_code":int(sys.argv[2])},indent=2)+"\n")
PY
  exit "$code"
}
trap fail ERR

cp "$source_media" "$art/candidate-a-music.mp4"
cp "$source_narration" "$art/audio/narration/source-manifest.json"

python3 "$root/scripts/generate_mf007a_ambient.py" \
  --fixture "$fixture" \
  --ambient-output "$art/audio/ambient/machine-room.wav" \
  --sfx-output "$art/audio/sfx/event-sfx.wav" \
  --report "$art/timelines/ambient-events.json" >"$art/logs/generate.log"

processing_target=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["candidate_b"]["normalization_processing_target_lufs"])' "$fixture")
ffmpeg -hide_banner -loglevel error -y \
  -i "$art/audio/ambient/machine-room.wav" -i "$art/audio/sfx/event-sfx.wav" \
  -filter_complex "[0:a][1:a]amix=inputs=2:normalize=0,loudnorm=I=${processing_target}:TP=-2.0:LRA=7" \
  -ar 48000 -ac 2 -c:a pcm_s16le "$art/audio/mixes/candidate-b.wav" 2>"$art/logs/mix.log"

ffmpeg -hide_banner -loglevel error -y -i "$source_media" -vn -ar 48000 -ac 1 -c:a pcm_s16le "$art/audio/mixes/candidate-a.wav" 2>"$art/logs/extract-control-audio.log"
ffmpeg -hide_banner -loglevel error -y -i "$source_media" -i "$art/audio/mixes/candidate-b.wav" \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 160k -ar 48000 -t 28 \
  -movflags +faststart -metadata creation_time='1970-01-01T00:00:00Z' "$art/candidate-b-ambient.mp4" 2>"$art/logs/remux.log"

python3 "$root/scripts/validate_media.py" "$art/candidate-a-music.mp4" --slice MF-007A-A --duration-min 27.95 --duration-max 28.05 --ffprobe-json "$art/validation/candidate-a-ffprobe.json" --result-json "$art/validation/candidate-a-media.json" >/dev/null
python3 "$root/scripts/validate_media.py" "$art/candidate-b-ambient.mp4" --slice MF-007A-B --duration-min 27.95 --duration-max 28.05 --ffprobe-json "$art/validation/candidate-b-ffprobe.json" --result-json "$art/validation/candidate-b-media.json" >/dev/null

python3 "$root/scripts/validate_mf007a_production.py" \
  --project-root "$root" --fixture "$fixture" \
  --candidate-a "$art/candidate-a-music.mp4" --candidate-b "$art/candidate-b-ambient.mp4" \
  --ambient "$art/audio/ambient/machine-room.wav" --sfx "$art/audio/sfx/event-sfx.wav" \
  --final-mix "$art/audio/mixes/candidate-b.wav" --ambient-report "$art/timelines/ambient-events.json" \
  --narration "$source_narration" --output "$art/validation/production.json" \
  --audio-timeline "$art/timelines/audio-ab.json" >"$art/logs/production.log"

python3 "$root/scripts/mf-007a-failure-tests.py" \
  --repo-root "$root" --fixture "$fixture" \
  --candidate-a "$art/candidate-a-music.mp4" --candidate-b "$art/candidate-b-ambient.mp4" \
  --ambient "$art/audio/ambient/machine-room.wav" --sfx "$art/audio/sfx/event-sfx.wav" \
  --final-mix "$art/audio/mixes/candidate-b.wav" --ambient-report "$art/timelines/ambient-events.json" \
  --narration "$source_narration" --output "$rep/failure-tests.json" >"$art/logs/failure-tests.log"

ffmpeg -hide_banner -loglevel error -y -i "$art/audio/mixes/candidate-a.wav" -filter_complex 'showwavespic=s=1000x220:colors=0xd4b863' -frames:v 1 "$art/waveforms/candidate-a-music.png"
ffmpeg -hide_banner -loglevel error -y -i "$art/audio/mixes/candidate-b.wav" -filter_complex 'showwavespic=s=1000x220:colors=0x39b8c9' -frames:v 1 "$art/waveforms/candidate-b-ambient.png"
ffmpeg -hide_banner -loglevel error -y -i "$art/waveforms/candidate-a-music.png" -i "$art/waveforms/candidate-b-ambient.png" -filter_complex '[0:v][1:v]vstack=inputs=2' -frames:v 1 "$art/waveforms/ab-comparison.png"

python3 - "$fixture" "$art" "$rep" <<'PY'
import hashlib,json,pathlib,sys
fixture=json.loads(pathlib.Path(sys.argv[1]).read_text());a=pathlib.Path(sys.argv[2]);r=pathlib.Path(sys.argv[3])
production=json.loads((a/'validation/production.json').read_text());failures=json.loads((r/'failure-tests.json').read_text())
assert production['result']=='PASS_WITH_BLOCKER' and failures['result']=='PASS'
base=production['baseline'];ca=production['candidate_a'];cb=production['candidate_b']
(a/'validation/baseline.json').write_text(json.dumps({'slice':'MF-007A','source':base['path'],'sha256':base['sha256'],'video_stream_sha256':base['video_stream_sha256'],'runtime_seconds':28.0,'frame_rate':30.0,'visual_validation':'PASS','visual_changes':0,'timeline_changes':0},indent=2)+'\n')
(a/'validation/mix.json').write_text(json.dumps({'slice':'MF-007A','candidate':'B','music_enabled':False,'music_sources':[],'inputs':['deterministic_machine_ambience','deterministic_event_sfx','preserved_narration_manifest'],'narration':{'status':'BLOCKED_PRODUCTION_VOICE','segments':0,'preserved_identically_in_a_and_b':True},'ducking':{'ambient_duck_db':-4.5,'attack_ms':120,'release_ms':320,'applied_windows':[],'reason':'no approved production narration segments'},'normalization':{'processing_target_lufs':fixture['candidate_b']['normalization_processing_target_lufs'],'measured_output':cb['loudness']},'clipping':'PASS','result':'PASS_WITH_BLOCKER'},indent=2)+'\n')
human={'slice':'MF-007A','review_status':'PENDING_HUMAN','devices':{'phone_speakers':'PENDING','headphones_or_earbuds':'PENDING','desktop_or_laptop_speakers':'PENDING'},'decision':'NO_WINNER_PENDING_HUMAN','allowed_decisions':fixture['human_decision'],'release_eligible':False}
(a/'validation/human-review.json').write_text(json.dumps(human,indent=2)+'\n')
result={'slice':'MF-007A','visual_changes':0,'timeline_changes':0,'renderer_changes':0,'candidate_a_preserved':'PASS','candidate_b_no_music':'PASS','identical_video_stream':'PASS','event_sound_design':'PASS','loudness_match_delta_lu':production['loudness_delta_lu'],'full_decode':'PASS','failure_tests':'PASS','production_voice':'BLOCKED_PRODUCTION_VOICE','human_ab_review':'PENDING_HUMAN','preferred_audio_direction':'NO_WINNER_PENDING_HUMAN','release_eligible':False,'technical_result':'PASS','result':'PASS_WITH_BLOCKER'}
(r/'result.json').write_text(json.dumps(result,indent=2)+'\n')
(r/'ambient-sound-contract.md').write_text('''# MF-007A Ambient Sound Contract

Candidate B uses four deterministic non-musical layers: a low 47.3 Hz equipment hum, filtered electrical interference, sparse aperiodic mechanical resonance, and a very low projection field while the recovered-record screen is active. It wakes over 1.55 seconds, briefly recedes at overload, evolves without a beat or chord progression, and powers down from 26.3–28.0 seconds. Orange indicator pulses and background powered cells remain acoustically silent.

Narration priority is configured above event SFX, ambience, and detail SFX. The ambient duck is −4.5 dB with 120 ms attack and 320 ms release. It has no applied windows because the frozen R9 production narration manifest is blocked and contains zero approved segments.
''')
event_rows=['| Event | Visible trigger | Time | Sound family |','|---|---|---:|---|']
event_rows += [f"| `{item['id']}` | `{item['visual_event']}` | {item['time']:.2f}s | `{item['family']}` |" for item in fixture['events']]
(r/'event-sfx-mapping.md').write_text('# MF-007A Event-SFX Mapping\n\n'+'\n'.join(event_rows)+'\n\nThe four orange indicators and powered wall cells have no dedicated sound event.\n')
(r/'candidate-comparison.md').write_text(f'''# MF-007A Candidate Comparison

No winner is selected automatically. Both candidates preserve the exact video stream `{base['video_stream_sha256']}` and the same blocked, zero-segment narration state.

| Candidate | Direction | Integrated | True peak | LRA | SHA-256 |
|---|---|---:|---:|---:|---|
| A | existing music + existing SFX | {ca['loudness']['integrated_lufs']:.2f} LUFS | {ca['loudness']['true_peak_db']:.2f} dBTP | {ca['loudness']['loudness_range']:.2f} LU | `{ca['sha256']}` |
| B | machine ambience + expanded event SFX; no music | {cb['loudness']['integrated_lufs']:.2f} LUFS | {cb['loudness']['true_peak_db']:.2f} dBTP | {cb['loudness']['loudness_range']:.2f} LU | `{cb['sha256']}` |

The loudness difference is {production['loudness_delta_lu']:.2f} LU. This is a controlled audio-direction comparison, not a publication decision.
''')
(r/'audio-ab-review.md').write_text('''# MF-007A Human A/B Review

Status: **PENDING HUMAN**. Preferred direction: **NO WINNER — PENDING HUMAN REVIEW**.

Listen back-to-back on phone speakers, headphones/earbuds, and ordinary desktop/laptop speakers. Record one result: `A — MUSIC`, `B — AMBIENT TECH`, or `NO WINNER — REFINE`.

Assess attention, atmosphere, originality, tension/curiosity, professionalism, fit with the scrappy low-fi machine language, rewatchability, and publishability. For B, also judge whether it feels full and physical without becoming empty, tiring, music-like, or a pile of generic sci-fi effects. This report does not impersonate a human listening decision.
''')
(r/'evidence-summary.md').write_text(f'''# MF-007A Evidence Summary

Audio/visual technical gate: **PASS**. Candidate A is byte-identical to R9. Candidate B copies the same encoded video stream and changes audio only. No-music structure, continuous ambience, 18 synchronized sound events, wake/power-down arc, loudness, peak, both full decodes, and eight negative mutation cases pass.

Production voice remains **BLOCKED** because the frozen R9 narration source contains no approved segments. Human device listening and winner selection remain **PENDING**. Release eligibility is **NO**.

- Frozen video stream: `{base['video_stream_sha256']}`
- Candidate A: `{ca['sha256']}`
- Candidate B: `{cb['sha256']}`
''')
(r/'changed-files.md').write_text('''# MF-007A Changed Files

## Source/configuration

- `.gitignore`
- `content/fixtures/mf007a-unknown-process-audio.json`
- `scripts/generate_mf007a_ambient.py`
- `scripts/validate_mf007a_production.py`
- `scripts/mf-007a-failure-tests.py`
- `scripts/mf-007a-acceptance.sh`

## Preserved/generated evidence

- `artifacts/mf-007a/candidate-a-music.mp4`
- `artifacts/mf-007a/candidate-b-ambient.mp4`
- `artifacts/mf-007a/timelines/ambient-events.json`
- `artifacts/mf-007a/timelines/audio-ab.json`
- `artifacts/mf-007a/validation/baseline.json`
- `artifacts/mf-007a/validation/candidate-a-ffprobe.json`
- `artifacts/mf-007a/validation/candidate-a-media.json`
- `artifacts/mf-007a/validation/candidate-b-ffprobe.json`
- `artifacts/mf-007a/validation/candidate-b-media.json`
- `artifacts/mf-007a/validation/human-review.json`
- `artifacts/mf-007a/validation/mix.json`
- `artifacts/mf-007a/validation/production.json`
- `artifacts/mf-007a/waveforms/ab-comparison.png`
- `artifacts/mf-007a/waveforms/candidate-a-music.png`
- `artifacts/mf-007a/waveforms/candidate-b-ambient.png`
- `reports/mf-007a/ambient-sound-contract.md`
- `reports/mf-007a/audio-ab-review.md`
- `reports/mf-007a/candidate-comparison.md`
- `reports/mf-007a/changed-files.md`
- `reports/mf-007a/evidence-summary.md`
- `reports/mf-007a/event-sfx-mapping.md`
- `reports/mf-007a/failure-tests.json`
- `reports/mf-007a/result.json`

Deterministic WAV stems and command logs under `artifacts/mf-007a/audio/` and `artifacts/mf-007a/logs/` are reproducible and ignored. Existing MF-006R8/R9 worktree changes were preserved. Godot, renderer, visual grammar, visual fixture, camera, and timeline-interpreter files changed by MF-007A: **none**.
''')
print(json.dumps(result,indent=2))
PY

trap - ERR
printf '\nMF-007A AUDIO/VISUAL TECHNICAL: PASS\nPRODUCTION VOICE: BLOCKED\nHUMAN A/B REVIEW: PENDING\n'
exit 3
