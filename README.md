# Media Foundry

An AI-operated, human-directed system for producing deterministic media from structured content.

MF-001 proves one complete path; MF-002 evolves it into a shared scrappy visual grammar that renders three distinct fixtures:

```text
JSON content -> Godot template -> deterministic frames/audio -> FFmpeg -> FFprobe -> evidence
```

Run the workstation check:

```bash
./scripts/doctor.sh
./scripts/doctor.sh --json
```

Run end-to-end acceptance and controlled negative tests:

```bash
./scripts/mf-001-acceptance.sh
./scripts/mf-001-failure-tests.sh
./scripts/mf-002-acceptance.sh
./scripts/mf-002-failure-tests.sh
```

Validated candidate media lives under `artifacts/mf-001/` and `artifacts/mf-002/`. MF-002 technical PASS is not aesthetic approval: review its three videos and contact sheet before proceeding. Publication always requires human approval.
