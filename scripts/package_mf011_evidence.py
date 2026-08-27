#!/usr/bin/env python3
"""Create the compact MF-011 repository evidence and human-review package."""

import argparse
import collections
import json
import shutil
import subprocess
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n")


def copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def table(headers, rows) -> str:
    return "\n".join([
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(str(value) for value in row) + " |" for row in rows),
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--archive", required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    archive = Path(args.archive).resolve()
    artifacts = root / "artifacts/mf-011"
    reports = root / "reports/mf-011"
    artifacts.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    campaign = load(archive / "campaign-result.json")
    manifest = load(archive / "campaign-manifest.json")
    independent = load(archive / "independent-validation.json")
    jobs = campaign["jobs"]
    job_specs = {job["id"]: job for job in manifest["jobs"]}

    for name in ["campaign-result.json", "campaign-state.json", "campaign-manifest.json", "shared-preflight.json",
                 "final-shared-preflight.json", "independent-validation.json", "campaign-contact-sheet.png",
                 "openclaw-health.log", "shared-preflight.log", "final-catalog-integrity.log"]:
        copy(archive / name, artifacts / name)
    prior_run = archive.parent / "campaign-run-001"
    if prior_run.is_dir():
        for name in ["campaign-result.json", "campaign-state.json", "campaign-manifest.json"]:
            copy(prior_run / name, artifacts / "prior-run-001" / name)
        for job_id in ["05-simon-biometric-anomaly", "07-digital-empire", "08-for-what-he-is", "10-direct-book-cta"]:
            for name in ["creative-preflight.log", "timeline-preflight.log", "render.log"]:
                source = prior_run / job_id / "logs" / name
                if source.is_file():
                    copy(source, artifacts / "prior-run-001" / "logs" / job_id / name)
    for item in jobs:
        job_id = item["job_id"]
        job_dir = archive / job_id
        for name in ["job-brief.json", "resolved-config.json", "resolved-creative-profile.json", "result.json", "contact-sheet.png"]:
            copy(job_dir / name, artifacts / "jobs" / job_id / name)
        for name in ["phase-1.png", "phase-2.png", "phase-3.png", "cta.png"]:
            copy(job_dir / "representative-frames" / name, artifacts / "representative-frames" / job_id / name)
        copy(job_dir / "motion-evidence/sequence.png", artifacts / "motion-evidence" / job_id / "sequence.png")
        for name in ["creative-preflight.json", "timeline-preflight.json", "execution.json", "music-selection.json",
                     "music.json", "sfx.json", "narration.json", "mix.json", "media.json", "output.json", "ffprobe.json"]:
            copy(job_dir / "validation" / name, artifacts / "validation" / job_id / name)
        for log in (job_dir / "logs").glob("*.log"):
            copy(log, artifacts / "logs" / job_id / log.name)
    motion_inputs = [artifacts / "motion-evidence" / item["job_id"] / "sequence.png" for item in jobs]
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for path in motion_inputs:
        command += ["-i", str(path)]
    filters = [f"[{index}:v]scale=360:240[v{index}]" for index in range(len(motion_inputs))]
    layout = "|".join(f"{(index % 5) * 360}_{(index // 5) * 240}" for index in range(len(motion_inputs)))
    filters.append("".join(f"[v{index}]" for index in range(len(motion_inputs)))
                   + f"xstack=inputs={len(motion_inputs)}:layout={layout}:fill=0x070b0f")
    subprocess.run(command + ["-filter_complex", ";".join(filters), "-frames:v", "1",
                              str(artifacts / "motion-evidence-overview.png")], check=True)

    job_rows = []
    for item in jobs:
        job_rows.append([item["job_id"], item["state"], item["runtime_seconds"], item["mechanism"],
                         item["music"]["track_id"], item["music"]["region_id"], item["audio_policy"]["sfx_count"],
                         item["artifact"]["sha256"][:12]])
    evidence_summary = f"""# MF-011 Evidence Summary

Technical result: **{independent['result']}**

- Campaign: `{campaign['campaign_id']}`
- Archive: `{archive}`
- Manifest SHA-256: `{campaign['manifest_sha256']}`
- Frozen grammar: `{campaign['grammar_id']}` (`{campaign['grammar_sha256']}`)
- Start/end state: `{campaign['start_state']} -> {campaign['state']}`
- Jobs attempted / ready for review: `{campaign['jobs_attempted']} / {campaign['ready_for_review']}`
- Renderer changes: `{campaign['renderer_changes']}`
- Catalog changes: `{campaign['catalog_changes']}`
- Published outputs: `{campaign['published']}`
- Human editorial review: **PENDING**

{table(['Video', 'State', 'Runtime', 'Mechanism', 'Track', 'Cue', 'SFX', 'MP4 SHA-256'], job_rows)}

The technical result does not imply human editorial acceptance. No useful-candidate percentage or 20-video recommendation is calculated until a human reviews all ten candidates.
"""
    write(reports / "evidence-summary.md", evidence_summary)
    copy(archive / "campaign-result.json", reports / "campaign-result.json")
    copy(archive / "campaign-manifest.json", reports / "campaign-manifest.json")

    review_rows = [[item["job_id"], "PENDING", "PENDING", "PENDING", "PENDING", "PENDING_HUMAN"] for item in jobs]
    write(reports / "per-video-review.md", f"""# MF-011 Per-Video Human Review

Review the archived MP4 named in each job result. Technical validation has passed independently; these editorial fields intentionally remain unfilled.

{table(['Video', 'Story', 'Visual', 'Music', 'Release potential', 'Status'], review_rows)}

Allowed release-potential values: `PASS`, `MINOR_REFINEMENT`, `MAJOR_REFINEMENT`, `REJECT`.
""")

    track_counts = collections.Counter(item["music"]["track_id"] for item in jobs)
    cue_counts = collections.Counter((item["music"]["track_id"], item["music"]["region_id"]) for item in jobs)
    music_rows = [[item["job_id"], item["music"]["track_title"], item["music"]["region_id"],
                   f"{item['music']['actual_start']:.1f}-{item['music']['actual_end']:.1f}s",
                   item["runtime_seconds"], item["music"]["fade_in"], item["music"]["fade_out"],
                   item["music"]["selection_reason"]] for item in jobs]
    overlaps = []
    for index, left in enumerate(jobs):
        for right in jobs[index + 1:]:
            lm, rm = left["music"], right["music"]
            if lm["track_id"] == rm["track_id"] and max(lm["actual_start"], rm["actual_start"]) < min(lm["actual_end"], rm["actual_end"]):
                overlaps.append(f"- `{left['job_id']}` and `{right['job_id']}` overlap on `{lm['track_id']}`.")
    distribution = "\n".join(f"- `{key}`: {value}" for key, value in sorted(track_counts.items()))
    cue_distribution = "\n".join(f"- `{track}/{cue}`: {count}" for (track, cue), count in sorted(cue_counts.items()))
    write(reports / "music-usage.md", f"""# MF-011 Music Usage

{table(['Video', 'Track', 'Cue', 'Actual offset', 'Runtime', 'Fade in', 'Fade out', 'Rationale'], music_rows)}

## Track usage

{distribution}

## Cue usage

{cue_distribution}

## Repeated or overlapping regions

{chr(10).join(overlaps) if overlaps else '- No same-track source intervals overlap.'}

Reuse is permitted and is reported as campaign identity, not as a technical failure.
""")

    creative_rows = []
    for item in jobs:
        profiles = item["profiles"]
        creative_rows.append([item["job_id"], item["mechanism"], profiles["palette_profile"], profiles["camera_profile"],
                              profiles["node_profile"], profiles["projection_profile"], profiles["cta_profile"],
                              item["music"]["track_id"] + "/" + item["music"]["region_id"]])
    write(reports / "creative-diversity.md", f"""# MF-011 Creative Diversity

{table(['Video', 'Mechanism', 'Palette', 'Camera', 'Node', 'Projection', 'CTA', 'Music'], creative_rows)}

Independent concrete pairwise comparison: **{independent['checks']['campaign_diversity']}** across `{len(independent['pairwise_diversity'])}` pairs. This is bounded control-surface evidence, not an artistic-similarity model.
""")
    write(reports / "campaign-comparison.md", f"""# MF-011 Campaign Comparison

- Shared recovered-record identity: technically preserved by the frozen grammar and single-window checks.
- Mechanisms used: `{', '.join(sorted(set(item['mechanism'] for item in jobs)))}`.
- Distinct cosmetic combinations: `{len(set(tuple(item['profiles'].values()) for item in jobs))}`.
- Distinct runtimes: `{len(set(item['runtime_seconds'] for item in jobs))}`.
- Tracks used: `{len(track_counts)}` of 4 approved tracks.
- Track/cue combinations used: `{len(cue_counts)}`.
- Human judgment of cohesion, engagement, similarity, and filler: **PENDING**.
""")
    write(reports / "renderer-integrity.md", f"""# MF-011 Renderer Integrity

- Initial aggregate hash: `{campaign['renderer_source_hash_before']}`
- Final aggregate hash: `{campaign['renderer_source_hash_after']}`
- Renderer changes: `{campaign['renderer_changes']}`
- Independent result: **{independent['checks']['renderer_integrity']}**
""")
    write(reports / "catalog-integrity.md", f"""# MF-011 Catalog Integrity

- Initial catalog SHA-256: `{campaign['catalog_sha256_before']}`
- Final catalog SHA-256: `{campaign['catalog_sha256_after']}`
- Catalog changes: `{campaign['catalog_changes']}`
- Approved tracks: `4`
- Approved cue regions: `20`
- Independent result: **{independent['checks']['catalog_integrity']}**
""")
    write(reports / "scaling-recommendation.md", """# MF-011 Scaling Recommendation

Campaign orchestration: **TECHNICALLY VALIDATED**

Editorial campaign automation: **PENDING HUMAN REVIEW**

Useful-candidate percentage: **NOT YET CALCULABLE**

Do not expand to twenty videos yet. Technical campaign automation is validated, but the required useful-candidate threshold (at least 8/10 rated PASS or MINOR_REFINEMENT) can only be calculated after human review.
""")
    write(reports / "runtime-boundary-correction.md", f"""# MF-011 Runtime Boundary Correction

The preserved first campaign attempt ended `PARTIAL`: 10 jobs were attempted, 6 reached `READY_FOR_REVIEW`, and 4 exhausted their one permitted technical retry.

The cause was a preflight contract mismatch. Frozen grammar metadata and the inherited creative validator advertised 24–32 seconds, while the unchanged Godot production stage accepts 26–30 seconds. Jobs configured at 24, 25, 31, and 32 seconds therefore failed deterministically.

MF-011's new shared preflight was tightened to the existing 26–30-second renderer boundary, the four manifest timings and approved music subsections were shortened or extended within their approved cue bounds, and all ten timeline preflights were rerun before canonical Run 002.

- Run 001 archive: `{prior_run}`
- Run 001 state: `PARTIAL` (6/10 ready)
- Run 002 state: `{campaign['state']}` ({campaign['ready_for_review']}/10 ready)
- Renderer changes: `0`
- Visual grammar changes: `0`
- Music source/catalog changes: `0`

The failed attempt is retained as evidence rather than hidden or overwritten.
""")
    write(reports / "artifacts.md", f"""# MF-011 Artifacts

- Full candidate archive: `{archive}`
- Campaign contact sheet: `{archive / 'campaign-contact-sheet.png'}`
- Motion-evidence overview: `{artifacts / 'motion-evidence-overview.png'}`
- Compact evidence: `{artifacts}`
- Independent validation: `{artifacts / 'independent-validation.json'}`

Final MP4s remain in the external campaign archive and are not duplicated into Git.
""")
    write(reports / "changed-files.md", """# MF-011 Changed Files

Expected repository changes are limited to:

- `config/campaigns/unknown-process-mf-011-v1.json`
- `content/fixtures/mf011/*.json`
- `scripts/build_mf011_fixtures.py`
- `scripts/run_mf011_campaign.py`
- `scripts/validate_mf011.py`
- `scripts/validate_mf011_campaign.py`
- `scripts/package_mf011_evidence.py`
- `artifacts/mf-011/**`
- `reports/mf-011/**`

Renderer, timeline interpreter, visual grammar, music sources, prior archives, and publication state are unchanged.
""")
    print(json.dumps({"artifacts": str(artifacts), "reports": str(reports), "jobs": len(jobs), "result": "PASS"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
