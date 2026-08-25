# MF-008 Orchestration Report

OpenClaw schedule `55968f6f-1314-41a6-9e7e-ab9875aa0c63` invoked one command batch at `2026-08-25T09:24:42.284Z` after a persisted wait of 119.604 seconds. The command used the same runner and manifest as the supervised dry run. It ran jobs sequentially, called Codex in a read-only schema-constrained role, rendered with the frozen Godot stack, validated with independent Media Foundry checks, and persisted all state under `/home/blanzy/media-foundry-output/unknown-process-batch-001/scheduled-run-001`.

Batch start delta from declared time: 0.003 seconds. OpenClaw command duration: 178562 ms. Delivery was `none`; run delivery status was `not-requested`.

## up-video-001

State: **READY_FOR_REVIEW**

Output: `/home/blanzy/media-foundry-output/unknown-process-batch-001/scheduled-run-001/up-video-001/final.mp4`

SHA-256: `552948ee3b0a2cc804e4ca24cc17ff2be28ea78da4fb8220db8e50c646a06ae1`

Size: 5,171,941 bytes

Codex/render/finalization/validation: 7268 / 21920 / 27318 / 1650 ms

Peak render memory: 214,164 KiB

## up-video-002

State: **READY_FOR_REVIEW**

Output: `/home/blanzy/media-foundry-output/unknown-process-batch-001/scheduled-run-001/up-video-002/final.mp4`

SHA-256: `44b783be2ece1d20dfee7fd15c1d8a3d84d3bb9c65b04695d3560104a3d75ef4`

Size: 5,200,582 bytes

Codex/render/finalization/validation: 5958 / 21819 / 27083 / 1651 ms

Peak render memory: 212,288 KiB

## up-video-003

State: **READY_FOR_REVIEW**

Output: `/home/blanzy/media-foundry-output/unknown-process-batch-001/scheduled-run-001/up-video-003/final.mp4`

SHA-256: `58602d8fbb1c0eaa0faf660e09190a670bfca85360ec4570147495dd02a17c3d`

Size: 5,158,744 bytes

Codex/render/finalization/validation: 6058 / 21721 / 27027 / 1648 ms

Peak render memory: 213,724 KiB

Batch archive retained size: 43,242,722 bytes. Batch wall time: 178,491 ms. Job idle and retry time: 0 ms.
