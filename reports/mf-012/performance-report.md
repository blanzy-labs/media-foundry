# MF-012 performance report

Deterministic render runs use 540×960 source frames at 30 fps and retain the established encode path.

- Four canonical demo renders were 28.573–33.377 ms/frame.
- The canonical override render recorded a one-time outlier of 98.600 ms/frame during concurrent system load.
- An isolated repeat of the same 330-frame override fixture completed in 9.81 seconds (29.727 ms/frame, 100% CPU, 203156 KiB maximum RSS).
- Representative legacy renders completed in 22.01–22.68 seconds for 810–840 frames.
- The pursuit demo encoded byte-identically on a second full render: `71376bc91f727d5f8732c5076f2f62d2247ba13701f7576929863c1f5e2984da`.

Conclusion: the repeat measurement places override in the same range as the other new activities; no sustained material slowdown was observed. The original outlier remains recorded rather than discarded.
