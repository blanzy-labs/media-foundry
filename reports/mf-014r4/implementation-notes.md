# MF-014R4 implementation notes

## Preserved baseline

R4 imports the MF-014R1 renderer and its frozen source/configuration directly. It does not build on R2 or R3. The R1 video, configuration, source plate, six circuit routes, hero title behavior, and approved music identity are hash-checked before rendering.

## Incandescent engraving

The support text is constructed as plate-local material masks:

- cold displaced cavities with dark upper edges and muted lower highlights;
- distressed heated bodies derived from the existing plate texture;
- char immediately around the cavities;
- warm local-light and edge-glow fields;
- a narrow pale incandescent core that survives 360 px downsampling;
- a traveling white-hot front during the right-to-left reveal;
- deterministic glyph-rooted flame polygons and restrained embers.

The pale core is intentionally narrow. The surrounding distressed fill, cavity displacement, char, and local lighting keep it within the physical heated-metal treatment rather than a clean neon treatment.

## Thermal sequence

- Existing-route branch begins at 10.4 s.
- Tagline heating begins at 10.9 s and settles by 13.9 s.
- URL heating begins at 12.1 s and settles by 14.5 s.
- The final composition holds from 14.5 through 17.0 s.

## Readability correction during production

The first complete R4 candidate technically rendered but the two-line 24 px URL collapsed into an orange bar at 360 px. It was rejected before validation and archived outside the repository at `/home/blanzy/media-foundry-output/mf-014r4-first-readability-candidate`.

The accepted candidate uses a 28 px, three-line slash-boundary layout, reduced bloom, and a clearer incandescent core. No frozen baseline asset was modified.

An earlier pre-encode diagnostic failure caused by `/tmp` capacity was also archived outside the repository at `/home/blanzy/media-foundry-output/mf014r4-pre-encode-failure`; the canonical run used an artifact-local temporary directory.

## Reproduction

```bash
python3 scripts/run_mf014r4.py --project-root .
python3 scripts/validate_mf014r4.py --project-root . --output reports/mf-014r4/result.json
```

The renderer refuses to overwrite an existing artifact directory. Move an existing candidate to an explicit archive location before reproducing.
