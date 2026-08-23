# Media Foundry

An AI-operated, human-directed system for producing deterministic media from structured content.

MF-001 proves one complete path:

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
```

The final candidate is `artifacts/mf-001/mf001-demo.mp4`. Publication is outside this slice and always requires human approval.
