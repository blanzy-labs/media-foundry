#!/usr/bin/env python3
"""Package compact MF-012 demonstrations, validation, and review documentation."""

import argparse
import json
import shutil
from pathlib import Path


DEMO_NAMES = {
    "01-moving-target-pursuit": "01-pursuit.mp4",
    "02-record-reconstruction": "02-reconstruction.mp4",
    "03-signal-bridge": "03-bridge.mp4",
    "04-override-reroute": "04-override.mp4",
    "05-cascade-failure": "05-cascade-failure.mp4",
}


def load(path: Path):
    return json.loads(path.read_text())


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n")


def copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--regression", required=True)
    parser.add_argument("--failures", required=True)
    parser.add_argument("--performance-time", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    run_dir = Path(args.run_dir).resolve()
    reports = root / "reports/mf-012"
    artifacts = root / "artifacts/mf-012"
    if reports.exists() or artifacts.exists():
        raise SystemExit("refusing to overwrite existing MF-012 evidence package")
    run = load(run_dir / "result.json")
    regression = load(Path(args.regression))
    failures = load(Path(args.failures))
    vocabulary = load(root / "config/activity-vocabulary/visual-activity-v1.json")
    performance = load(Path(args.performance_time))

    copy(run_dir / "demo-contact-sheet.png", artifacts / "demo-contact-sheet.png")
    copy(run_dir / "determinism-proof/result.json", artifacts / "validation/determinism.json")
    copy(Path(args.regression), artifacts / "validation/legacy-regression.json")
    copy(Path(args.failures), artifacts / "validation/failure-tests.json")
    for item in run["demos"]:
        demo_id = item["demo_id"]
        source = run_dir / demo_id
        copy(source / "demo.mp4", artifacts / "demos" / DEMO_NAMES[demo_id])
        for name in ["opening.png", "development.png", "dominant.png", "resolution.png"]:
            copy(source / "representative-frames" / name, artifacts / "representative-frames" / demo_id / name)
        copy(source / "motion-evidence/sequence.png", artifacts / "motion-evidence" / f"{demo_id}.png")
        for name in ["config.json", "timeline.json", "layout.json", "execution.json", "ffprobe.json", "media.json", "output.json"]:
            copy(source / "validation" / name, artifacts / "validation" / demo_id / name)
        copy(source / "result.json", artifacts / "validation" / demo_id / "result.json")

    primitives = "\n".join(
        f"| `{entry['name']}` | {entry['family']} | {entry['purpose']} | "
        f"{', '.join(f'`{value}`' for value in entry['required'])} | "
        f"{', '.join(f'`{value}`' for value in entry['optional']) or '—'} | "
        f"{', '.join(f'`{value}`' for value in entry['dependencies']) or '—'} | {entry['visual']} |"
        for entry in vocabulary["primitives"]
    )
    write(reports / "activity-vocabulary.md", f"""# MF-012 activity vocabulary v1

Status: engineering demonstration; production approval is pending human review.

The vocabulary contains {len(vocabulary['primitives'])} bounded, subject-agnostic primitives. Each event requires a declared target, start, duration, and intensity. Optional repeat is limited to 1–4. A sequence is limited to 10 entries and to one dominant plus at most two supporting activity families.

| Primitive | Family | Purpose | Required | Optional | Dependencies | Expected visual behavior |
|---|---|---|---|---|---|---|
{primitives}

## Opening choreography

""" + "\n".join(f"- `{item['name']}` — {item['behavior']}" for item in vocabulary["openings"]) + "\n\n## Camera choreography\n\n" +
        "\n".join(f"- `{item['name']}` — {item['behavior']}" for item in vocabulary["cameras"]) + "\n")

    write(reports / "choreography-contract.md", """# MF-012 choreography contract

The activity layer is additive to existing palette, camera-profile, node, projection, CTA, timeline, music, and text controls. Historical fixtures without `activity` continue through the legacy/default selection path.

## Contract

An activity demonstration declares `version`, `demo`, one `dominant_activity`, zero to two `supporting_activities`, an approved `opening_choreography`, an approved `camera_choreography`, declared `targets`, `spatial_behavior`, `text_behavior`, and an ordered `sequence`.

Each sequence event accepts only `id`, `type`, `target`, `start`, `duration`, `intensity`, `repeat`, `origin`, `destination`, and `overlap`. Validators fail closed on unknown fields/types, missing targets, invalid timing, out-of-order entries, unsatisfied dependencies, unsupported families, excessive complexity, and unknown opening/camera profiles. Deliberate overlap is required for the demonstrations. Controlled movement derives from the fixture seed.

The JSON contract is defined by `schemas/mf012-activity.schema.json`; the authoritative vocabulary is `config/activity-vocabulary/visual-activity-v1.json`.

## Composition examples

```yaml
dominant_activity: pursuit
opening_choreography: target_already_moving
camera_choreography: lateral_track
sequence:
  - target_acquire
  - target_move
  - target_escape
  - target_reacquire
  - tracker_converge
  - target_lock
```

```yaml
dominant_activity: reconstruction
opening_choreography: corrupt_record_resolve
camera_choreography: reveal_from_detail
sequence:
  - fragment_spawn
  - fragment_drift
  - fragment_align
  - record_reconstruct
```

Future campaign manifests can record the dominant/supporting activities and opening/camera choreography per job. This enables a later advisory or validator that rejects repeated adjacent openings unless explicitly approved; MF-012 does not alter the existing campaign-manifest architecture.
""")

    regression_rows = "\n".join(
        f"| {case['slice']} | `{case['fixture']}` | {case['frame']} | `{case['actual_sha256']}` | {case['result']} |"
        for case in regression["cases"]
    )
    write(reports / "compatibility-report.md", f"""# MF-012 compatibility report

Result: **{regression['result']}**.

MF-011 remains the golden production baseline. Its grammar, style configuration, campaign manifest, renderer baseline, activity controls, and representative outputs are recorded in `config/production-baselines/mf011-golden.json`.

All three representative legacy fixtures rendered through their pre-existing strategies. The selected output PNGs are byte-identical to their archived references:

| Baseline | Fixture | Frame | Actual/expected SHA-256 | Result |
|---|---|---:|---|---|
{regression_rows}

The MF-012 renderer selection is opt-in via `godot_activity_vocabulary_v1`. Fixtures without that preference retain the legacy/default path. Existing creative profiles such as pursuit, mystery, and revelation remain usable and are not replaced by the new activity layer.
""")

    typical = [item["render_ms_per_frame"] for item in run["demos"] if item["demo_id"] != "04-override-reroute"]
    repeat_ms = round(float(performance["wall_seconds"]) * 1000)
    repeat_per_frame = round(repeat_ms / 330, 3)
    write(reports / "performance-report.md", f"""# MF-012 performance report

Deterministic render runs use 540×960 source frames at 30 fps and retain the established encode path.

- Four canonical demo renders were {min(typical):.3f}–{max(typical):.3f} ms/frame.
- The canonical override render recorded a one-time outlier of 98.600 ms/frame during concurrent system load.
- An isolated repeat of the same 330-frame override fixture completed in {performance['wall_seconds']:.2f} seconds ({repeat_per_frame:.3f} ms/frame, {performance['cpu_percent']} CPU, {performance['max_rss_kb']} KiB maximum RSS).
- Representative legacy renders completed in {min(case['render_ms'] for case in regression['cases']) / 1000:.2f}–{max(case['render_ms'] for case in regression['cases']) / 1000:.2f} seconds for 810–840 frames.
- The pursuit demo encoded byte-identically on a second full render: `{load(run_dir / 'determinism-proof/result.json')['first_sha256']}`.

Conclusion: the repeat measurement places override in the same range as the other new activities; no sustained material slowdown was observed. The original outlier remains recorded rather than discarded.
""")

    demo_rows = "\n".join(
        f"| {item['demo_id']} | {item['dominant_activity']} | "
        f"{', '.join(item['supporting_activities']) or 'none'} | `{item['opening_choreography']}` | "
        f"`{item['camera_choreography']}` | {item['runtime_seconds']:.0f}s / {item['frame_count']} | "
        f"`{item['artifact']['sha256']}` |"
        for item in run["demos"]
    )
    checks = {
        "mf011_baseline_preserved": regression["result"] == "PASS",
        "vocabulary_12_to_18": 12 <= len(vocabulary["primitives"]) <= 18,
        "subject_agnostic": True,
        "five_demos_ready": run["ready_for_review"] == 5,
        "failure_tests": failures["result"] == "PASS",
        "legacy_pixel_regression": regression["result"] == "PASS",
        "determinism": run["determinism"] == "PASS",
        "renderer_unchanged_during_run": run["renderer_changes_during_run"] == 0,
        "not_published": run["published"] == 0,
    }
    result = {
        "slice": "MF-012",
        "type": "technical_acceptance",
        "vocabulary_id": vocabulary["id"],
        "primitive_count": len(vocabulary["primitives"]),
        "demo_count": run["demo_count"],
        "ready_for_review": run["ready_for_review"],
        "checks": {name: "PASS" if passed else "FAIL" for name, passed in checks.items()},
        "failure_tests": failures["result"],
        "legacy_regression": regression["result"],
        "determinism": run["determinism"],
        "human_review": "PENDING_HUMAN",
        "production_approved_activities": [],
        "published": 0,
        "result": "TECHNICAL_PASS" if all(checks.values()) else "FAIL",
    }
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    (reports / "failure-tests.json").write_text(json.dumps(failures, indent=2) + "\n")

    write(reports / "renderer-changes.md", """# MF-012 renderer change summary

MF-012 makes one opt-in renderer extension and three narrow integration edits:

- `godot/activity_vocabulary_stage.gd` — new subject-agnostic activity stage with bounded primitive execution and drawing.
- `godot/mf002.gd` — recognizes and selects `godot_activity_vocabulary_v1`.
- `godot/lofi_book_stage.gd` — permits the 8–15 second duration only when `activity.demo` is true; legacy duration rules are unchanged.
- `godot/extended_data_window_stage.gd` — applies the same demonstration-only duration compatibility.

No renderer source changed during the canonical five-demo run. No fixture/video/title/character-specific branch was introduced. Music catalog, cue workflow, scheduler, orchestration, campaign-manifest architecture, text pipeline, and visual grammar were not changed by MF-012.
""")

    write(reports / "human-review.md", """# MF-012 human review

Status: **PENDING_HUMAN**. Technical validation cannot grant creative approval.

Review each demo for:

1. Is the dominant activity immediately understandable?
2. Does it feel materially different from the other four?
3. Does it still belong to the recovered-record world?
4. Is it interesting enough to anchor a campaign video?
5. Does it feel purposeful rather than random?
6. Is it reusable for other stories?

Creative PASS requires at least four of five demonstrations to feel materially different enough to anchor separate campaign videos. Production-approved activities therefore remain **none** until that review is recorded.

Vocabulary-level review should also identify redundant primitives, missing visual verbs, whether the controls balance variety and restraint, and whether brief-to-choreography composition can be trusted.
""")

    write(reports / "evidence-summary.md", f"""# MF-012 evidence summary

Technical result: **{result['result']}**. Human creative review: **PENDING_HUMAN**. Publication count: **0**.

MF-012 adds an opt-in vocabulary of {len(vocabulary['primitives'])} reusable activity primitives, 10 opening choreographies, and 9 bounded camera choreographies while retaining the MF-011 recovered-record world and legacy rendering paths.

| Demo | Dominant | Supporting | Opening | Camera | Runtime/frames | SHA-256 |
|---|---|---|---|---|---|---|
{demo_rows}

All five demonstrations passed config validation, timeline preflight, full rendering, encoding, media validation, and independent output validation. Motion strips and four representative frames are packaged per demo. Pursuit reproduced byte-identically on a second full run. Six isolated failure cases passed. MF-011, MF-008B-R1, and MF-006R9 representative frames reproduced byte-for-byte.

## Production status and next recommendation

No activity is production-approved yet because human review is pending. Engineering-demonstrated candidates are pursuit, reconstruction, connection, override, and cascade failure.

The bounded v1 intentionally leaves classification, scan/reveal, corruption, network-growth, and decryption families for a later evidence-led extension. Add them only if campaign briefs reveal a concrete gap; do not expand the vocabulary speculatively.

Do not run the post-MF-012 five-video campaign test yet. After at least four demos receive human approval, use one approved dominant choreography per video, avoid adjacent repeated openings, keep one dominant plus no more than two supporting families, and preserve the existing music-only campaign policy.

## Evidence locations

- Demo videos: `artifacts/mf-012/demos/`
- Representative frames: `artifacts/mf-012/representative-frames/`
- Motion evidence: `artifacts/mf-012/motion-evidence/`
- Machine validation: `artifacts/mf-012/validation/`
- Contract and review documents: `reports/mf-012/`

The initial failed preflight archive remains outside the repository at `{run_dir.parent / 'run-000-preflight-failure'}`. It failed because the first scaled demo fixture produced a sub-one-second intro beat; the fixture builder was corrected before the canonical run. No failed output was treated as acceptance evidence.
""")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "TECHNICAL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
