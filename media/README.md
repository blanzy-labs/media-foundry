# Media source assets

- `images/`: supplied or project still artwork (`.png`, `.jpg`, `.jpeg`, `.webp`).
- `screenshots/`: image assets whose semantic role is a screenshot.
- `video/`: source MP4 clips. Fixtures select offsets; source files remain unchanged.
- `audio/`: existing source audio conventions.
- `generated/`: deliberate generated source assets only, not disposable render intermediates.

Every fixture media object records provenance. FFmpeg-normalized video frames and other disposable derivatives belong under `artifacts/<slice>/normalized/` or an acceptance work directory, never beside source assets.
