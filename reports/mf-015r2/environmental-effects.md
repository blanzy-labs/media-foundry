# MF-015R2 environmental effects

## Composition and narrative role

The human renderer is disabled and its draw method is a no-op. No person, humanoid shadow, robot, alien, creature, or mannequin was introduced. An angled, visibly mechanical foreground instrument bank now anchors the lower foreground. It includes a pressure gauge, transformer hardware, an automatic lever, and a pressure line while preserving dark negative space.

The system now implies self-operation: lamps and gauges escalate, the heavy lever moves automatically, and containment behavior grows more unstable without an operator.

## Bounded effects

- Reactor light spill increases onto pipes, panel edges, and nearby machinery.
- Two small steam sources activate after the configured pressure threshold and dissipate without covering the room.
- Three rare electrical-arc events occur at `16.75`, `21.85`, and `23.10` seconds, each limited to `0.16` seconds.
- A large pipe shadow shifts with the reactor pulse.
- One suspended cable sways by at most `5` pixels.
- Containment-ring vibration is capped at `2` pixels.
- Eighteen sparse atmospheric particles become most visible in reactor light.
- Gauge needles, incandescent warning lamps, pressure response, internal plasma turbulence, and the automatic lever communicate escalation.
- Existing R1 exposure, registration, grain, ink wear, scratches, and frame weave remain tied to system stress.

The configured shot budget remains one dominant event plus no more than three supporting effects. The reactor stays first in the hierarchy; independent dominance ratios range from `1.963` to `2.438` before the maximum exposure state.

## Execution evidence

- Steam helper state: active, opacity `230`, `15,572` nonzero alpha pixels in its isolated mask.
- Electrical-arc helper state at `16.75` s: active, `694` nonzero alpha pixels.
- Close-frame environmental comparison: `11.76%` of the sampled region changed, with mean pixel delta `10.837`.
- Reactor mean progression: `72.809` -> `84.858` -> `90.175` -> `98.019` -> `152.117`.

All effects derive from the single recorded seed `1501957` and the checked configuration.
