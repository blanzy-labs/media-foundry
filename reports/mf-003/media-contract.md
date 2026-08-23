# MF-003 Media Contract

## Fixture schema

Existing fixtures may omit `media` or set it to `null`; the deterministic MF-002 primitive visual remains the fallback. A media fixture uses one compact object:

```json
{
  "media": {
    "type": "image | screenshot | video",
    "source": "media/images/example.png",
    "fit": "contain | cover",
    "anchor": "center | top | bottom | left | right",
    "motion": "none | slow_push | gentle_pan",
    "caption": "OPTIONAL FRAME LABEL",
    "required": true,
    "provenance": {
      "type": "supplied | generated | project_asset | captured | public_domain | licensed",
      "description": "short traceability note"
    }
  }
}
```

Video additionally requires:

```json
{
  "start_seconds": 2.0,
  "duration_seconds": 5.0,
  "muted": true
}
```

Video motion is `none` in v1 because movement comes from the clip itself.

## Supported formats

- Image and screenshot: PNG, JPEG (`.jpg`/`.jpeg`), and WebP.
- Video: MP4 containing a readable video stream. Source audio is ignored and `muted: true` is required.

The independent input stage verifies the actual image format, dimensions, readability, source containment, video stream, dimensions, frame rate, duration, start offset, and requested clip extent. A matching extension alone is insufficient.

## Fit and anchor behavior

- `contain`: scales the whole source into the 360×252 internal-pixel slot. Padding uses the workshop-dark inset. The source is never cropped.
- `cover`: fills the complete slot at the source aspect ratio. Cropping occurs in source coordinates.
- Anchors select placement in contain padding or the retained edge during cover cropping. `center` is the symmetric default; top, bottom, left, and right are explicit.

Geometry is sampled at start, midpoint, and end and independently checked against `media_slot.safe_rect`. The slot remains inside the existing physical panel and is separate from headline/body regions.

## Image motion

- `none`: stable image.
- `slow_push`: restrained 2.5% deterministic enlargement. For contain, it approaches full contained size without escaping the slot; for cover, it narrows the source crop.
- `gentle_pan`: deterministic horizontal movement bounded by available padding/crop space.

Motion uses the existing content-stage enter/display/exit timing. There is no separate timeline engine.

## Video normalization and timing

FFprobe validates the source. FFmpeg selects exactly `duration_seconds × 30` frames beginning at `start_seconds`. The shared renderer preloads that bounded normalized sequence, starts it when the content stage enters, advances at 30fps, and holds the selected segment's final frame after it ends. The source MP4 is never manually edited or mutated.

Normalized frame sequences are disposable work products. Acceptance preserves only a manifest and representative start/middle/end frames in `artifacts/mf-003/normalized/`.

## Caption and safe layout

`caption` replaces the existing visual label text and uses MF-002R1's `LABEL` role, `LABEL_SAFE_AREA`, responsive fitting, minimum size, and fail-closed behavior. If caption is absent, `visual.label` remains in use.

## Missing-media behavior

- `required: true`: a missing or unreadable source fails with `MEDIA_ASSET_FAILED`; no blank slot is rendered.
- `required: false`: a missing source deterministically falls back to the fixture's existing primitive `visual` and logs `MF003_MEDIA_OPTIONAL_FALLBACK`.
- An invalid present asset always fails; optional does not excuse corrupt or malformed input.

No replacement media is generated, downloaded, or inferred.

## Asset locations

- Source: `media/images/`, `media/screenshots/`, `media/video/`, `media/audio/`, and deliberate `media/generated/` assets.
- Disposable normalized clips: acceptance work directory.
- Accepted evidence only: `artifacts/mf-003/normalized/`.

Provenance travels with the fixture rather than a separate rights-management database.
