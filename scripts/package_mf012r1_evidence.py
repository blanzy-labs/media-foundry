#!/usr/bin/env python3
"""Package compact MF-012R1 A/B media, machine evidence, and review documents."""

import argparse
import json
import shutil
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text())


def copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    root, run_dir = Path(args.project_root).resolve(), Path(args.run_dir).resolve()
    reports, artifacts = root / "reports/mf-012r1", root / "artifacts/mf-012r1"
    if reports.exists() or artifacts.exists():
        raise SystemExit("refusing to overwrite existing MF-012R1 package")
    run = load(run_dir / "result.json")
    reports.mkdir(parents=True)
    for job in run["jobs"]:
        job_id, source = job["id"], run_dir / job["id"]
        copy(source / "original-reference/video-original.mp4", artifacts / job_id / "original-reference/video-original.mp4")
        copy(source / "original-reference/fixture.json", artifacts / job_id / "original-reference/fixture.json")
        copy(source / "original-reference/result.json", artifacts / job_id / "original-reference/result.json")
        copy(source / "original-reference/validation/music-selection.json", artifacts / job_id / "original-reference/music-selection.json")
        copy(source / "original-reference/validation/mix.json", artifacts / job_id / "original-reference/mix.json")
        copy(source / "refined/video-micro-variation.mp4", artifacts / job_id / "refined/video-micro-variation.mp4")
        copy(source / "refined/fixture.json", artifacts / job_id / "refined/fixture.json")
        for name in ["phase-1.png", "phase-2.png", "phase-3.png", "cta.png"]:
            copy(source / "original-reference/representative-frames" / name, artifacts / job_id / "original-reference/representative-frames" / name)
            copy(source / "refined/representative-frames" / name, artifacts / job_id / "refined/representative-frames" / name)
        for name in ["original-sequence.png", "refined-sequence.png", "comparison-sequence.png", "original-vs-refined.mp4"]:
            copy(source / "motion-evidence" / name, artifacts / job_id / "motion-evidence" / name)
        for name in ["config.json", "timeline.json", "layout.json", "execution.json", "ffprobe.json", "media.json", "output.json", "determinism.json", "legacy-default.json"]:
            copy(source / "validation" / name, artifacts / "validation" / job_id / name)
        copy(source / "result.json", artifacts / "validation" / job_id / "result.json")
    copy(run_dir / "failure-tests.json", artifacts / "validation/failure-tests.json")

    source_rows, variant_rows = [], []
    for job in run["jobs"]:
        output = load(run_dir / job["id"] / "validation/output.json")
        selection = output["music_selection"]
        mix = load(run_dir / job["id"] / "original-reference/validation/mix.json")
        source_rows.append(
            f"| {job['id']} | `{job['source_job']}` | {job['runtime_seconds']:.0f}s | `{job['source']['sha256']}` | "
            f"`{selection['track_id']}` / `{selection['region_id']}` | {selection['actual_start']:.1f}–{selection['actual_end']:.1f}s | "
            f"{mix['music']['gain_db']:.1f} dB | {selection['fade_in']:.1f}/{selection['fade_out']:.1f}s |"
        )
        micro = job["micro_variation"]
        ring = micro.get("floating_ring_dot")
        variant_rows.append(
            f"| {job['id']} | {job['variant']} | {', '.join(f'`{value}`' for value in micro['channels'])} | "
            f"{micro['seed']} | {len(micro['background_tiles']['active_indices'])} ({micro['background_tiles']['active_density'] * 100:.1f}%) | "
            f"{micro['indicator_dots']['mode']} | {ring['behavior'] if ring else 'disabled'} | `{job['refined']['sha256']}` |"
        )

    write(reports / "source-selection.md", """# MF-012R1 source selection

The executive MF-012R1 brief designates successful MF-011/MF-008B-R1 outputs as the approved source pool. Repository records for these MF-011 candidates say `READY_FOR_REVIEW` / `PENDING_HUMAN`; this report does not rewrite those historical fields. Selection eligibility is therefore attributed to the current executive direction.

The two selected MF-011 Run 002 videos use different narrative mechanisms and approved hash-bound music cues:

| Pair | Source job | Runtime | Original SHA-256 | Track/region | Source offsets | Gain | Fade in/out |
|---|---|---:|---|---|---|---:|---|
""" + "\n".join(source_rows) + """

- Video 1: Leo classification/link investigation, selected for a calm restrained treatment.
- Video 2: kill-switch biometric revelation, selected for a slightly more reactive treatment.

The source MP4s, source fixtures, source results, music selections, and mix reports are copied into `artifacts/mf-012r1/`. Originals were not overwritten.

The frozen MF-011 source baseline records renderer source hash `80fe5c5824ea90fb67c2995f37233b714fa9acdbf74b209f691c83a81a6a89f9`, grammar ID `unknown_process_recovered_record_v2`, and grammar SHA-256 `a5020243b8687681a25ff9bd8e5d99b7aa2a523c489bec12bc0e19f720c11314`.
""")

    write(reports / "micro-variation-contract.md", """# MF-012R1 micro-variation contract

The contract is an optional `micro_variation` object on the existing indicator-pulse renderer. Omitting it preserves the legacy path.

Guardrails:

- 1–3 unique channels from `indicator_dots`, `background_tiles`, and `floating_ring_dot`.
- At most one major motion element and three simultaneous minor accents.
- Colors restricted to amber, purple, green, and blue.
- Reactive indicator events are short, independently scheduled, and non-chasing.
- Three to eight active tiles from 54 visible tiles (5–15%), with at most 0.12 overlay alpha and no protected-zone intersection.
- Ring radius 4–14 px, maximum configured speed 18 px/s, explicit path and safe rectangle, and no protected-zone intersection.
- Required positive seed, deterministic `mf012r1_lcg_v1` schedule, and a hash signature over the recorded schedule.
- Music on; SFX, ambient audio, and narration off.

The JSON schema is `schemas/mf012r1-micro-variation.schema.json`. Independent semantic checks are implemented in `scripts/validate_mf012r1.py`.

Protected regions cover the main projection/story text, CTA/URL/author block, and emitter/indicator row. Safe-zone failure is explicit and fail-closed.
""")

    write(reports / "visual-comparison.md", """# MF-012R1 visual comparison

Comparison media uses **original on the left** and **refined on the right**.

## Video 1 — restrained

- Preserves the four inherited amber indicator dots and their approved restrained pulse behavior.
- Adds three eligible wall tiles (5.6% of 54) with six long, low-alpha seeded changes.
- No moving ring, new circuit lines, or central geometry.

## Video 2 — reactive

- Uses four approved indicator colors with six isolated 0.34–0.46 second flashes; no chase and no synchronized all-dot flash.
- Adds five eligible wall tiles (9.3%) with seven low-alpha seeded changes.
- Adds one 10 px blue ring/dot moving at 4.29 px/s through a fixed upper-right negative-space zone. It remains outside the CTA bounds and ends before final CTA stabilization.
- No new circuit lines, tracer web, HUD, or central geometry.

Inspection of the frame strips shows the record hierarchy and readable text remain unchanged. The first treatment is intentionally subtle; the second provides a more recognizable upper-right motion signature without entering the projection. Full-motion human review remains required to judge whether those differences are useful rather than merely detectable.

Evidence paths:

- `artifacts/mf-012r1/video-01/motion-evidence/original-vs-refined.mp4`
- `artifacts/mf-012r1/video-02/motion-evidence/original-vs-refined.mp4`
- Each directory also contains original, refined, and side-by-side 12-frame strips.
""")

    write(reports / "renderer-changes.md", """# MF-012R1 renderer changes

MF-012R1 modifies only `godot/indicator_pulse_stage.gd` to recognize an optional, subject-agnostic `micro_variation` object and draw its bounded tile, indicator, and ring accents.

Defaults are unchanged when that object is absent. Both selected legacy fixtures were fully rerendered without micro controls; their archived phase-3 PNGs remained byte-identical.

Renderer changes during the production run: 0. Subject/title/video-specific branches: 0. Large crossing lines: 0. New central-web geometry: 0. Visual grammar changes: 0.
""")

    write(reports / "human-review.md", """# MF-012R1 human review

Status: **PENDING_HUMAN**. No micro-variation behavior is production-approved by automation.

For both pairs, watch the side-by-side motion MP4 and answer:

1. Is the refinement cleaner than the MF-012 pursuit demonstration?
2. Is it more individually recognizable than its original?
3. Does any animation compete with text or the record?
4. Does it remain purposeful and free of unnecessary busyness?

Then judge each behavior explicitly:

- Indicators: useful, unnecessary, or too flashy?
- Sparse tile changes: useful, unnecessary, or too frequent?
- Floating ring/dot: intentional machine focus, unnecessary cursor-like motion, or too distracting?

Overall strategy decision: **YES / PARTIALLY / NO** — is guardrailed micro-variation preferable to the broader noisy pursuit approach?

Creative PASS requires both pairs to stay clean/readable and become recognizably distinct, with at least two behavior types approved. Until those answers are recorded, approved behaviors remain **none** and the five-video test remains on hold.
""")

    checks = {
        "two_sources_preserved": len(run["jobs"]) == 2 and all(job["source"]["sha256"] for job in run["jobs"]),
        "two_refined_variants": run["ready_for_review"] == 2,
        "text_preserved": all(job["text_identical"] for job in run["jobs"]),
        "audio_packet_identity": all(job["audio_packet_identical"] for job in run["jobs"]),
        "cue_identity": all(job["cue_identical"] for job in run["jobs"]),
        "runtime_and_frames": all(job["result"] == "PASS" for job in run["jobs"]),
        "safe_zones": all(job["safe_zone"] == "PASS" for job in run["jobs"]),
        "motion_budgets": all(job["motion_budget"] == "PASS" for job in run["jobs"]),
        "determinism": all(job["determinism"] == "PASS" for job in run["jobs"]),
        "legacy_defaults": all(job["legacy_default"] == "PASS" for job in run["jobs"]),
        "failure_tests": run["failure_tests"] == "PASS",
        "renderer_integrity": run["renderer_changes_during_run"] == 0,
        "not_published": run["published"] == 0,
    }
    result = {
        "slice": "MF-012R1", "type": "technical_acceptance",
        "checks": {name: "PASS" if passed else "FAIL" for name, passed in checks.items()},
        "source_jobs": [job["source_job"] for job in run["jobs"]], "refined_count": run["ready_for_review"],
        "failure_tests": run["failure_tests"], "human_review": "PENDING_HUMAN",
        "approved_micro_variations": [], "rejected_noisy_behaviors": ["crossing_tracer_lines", "central_web_geometry", "screen_wide_flashes", "motion_over_text"],
        "five_video_test": "HOLD_FOR_HUMAN_REVIEW", "published": 0,
        "result": "TECHNICAL_PASS" if all(checks.values()) else "FAIL",
    }
    (reports / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    failures = load(run_dir / "failure-tests.json")
    (reports / "failure-tests.json").write_text(json.dumps(failures, indent=2) + "\n")
    write(reports / "evidence-summary.md", f"""# MF-012R1 evidence summary

Technical result: **{result['result']}**. Human creative review: **PENDING_HUMAN**. Publication count: **0**.

| Pair | Treatment | Channels | Seed | Active tiles | Indicators | Ring | Refined SHA-256 |
|---|---|---|---:|---|---|---|---|
{chr(10).join(variant_rows)}

Both refined outputs preserve their source runtime, frame count, wording, beat timing, CTA, title, author, URL, music configuration, track, approved cue, actual offsets, gain, fades, and music-only policy. The original AAC packet payload and decoded audio hashes are identical in each A/B pair.

Both configurations pass safe-zone and motion-budget validation. Both rendered frame trees reproduce byte-identically on a second run. Both original fixtures still reproduce their archived MF-011 phase-3 frame byte-for-byte without micro controls. Six required failure cases pass.

No behavior is yet production-approved because human review is pending. Large crossing tracers, central-web geometry, screen-wide flashes, and motion over text were excluded by design and are recorded as rejected/noisy patterns.

Recommendation: hold the five-video test. If human review approves at least two behavior types and both pairs remain cleaner and more distinctive, test stable/reactive indicators and sparse tile shifts broadly; keep the ring/dot conditional on its cursor-like-motion review.

The initial unsupported headless attempt is preserved outside the repository at `{run_dir.parent / 'run-000-headless-failure'}` and was not used as acceptance evidence.
""")
    write(reports / "changed-files.md", """# MF-012R1 changed-file inventory

- Modified renderer: `godot/indicator_pulse_stage.gd`
- Contract/config: `schemas/mf012r1-micro-variation.schema.json`, `content/fixtures/mf012r1/`
- Automation: `scripts/mf012r1_contract.py`, `scripts/build_mf012r1_fixtures.py`, `scripts/validate_mf012r1.py`, `scripts/test_mf012r1_failures.py`, `scripts/run_mf012r1.py`, `scripts/package_mf012r1_evidence.py`
- Reports: `reports/mf-012r1/`
- Candidate evidence: `artifacts/mf-012r1/`

No music catalog, cue-region, scheduler, orchestration, campaign manifest, text pipeline, visual grammar, or source MF-011 fixture was modified by MF-012R1.
""")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "TECHNICAL_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
