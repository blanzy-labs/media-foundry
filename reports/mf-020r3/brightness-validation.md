# MF-020R3 brightness validation

The repository's existing composition validator measures full-frame mean, hero mean, hero pixels above luma 80, console mean, and title yellow pixels.

| State | Frame mean | Hero mean | Hero bright pixels | Console mean |
| --- | ---: | ---: | ---: | ---: |
| R2 dormant | 10.786 | 8.450 | 0 | 8.521 |
| R3 dormant | 20.823 | 20.642 | 488 | 17.943 |
| R3 startup | 20.965 | 21.029 | 524 | 17.752 |
| R3 mid-active | 30.335 | 49.556 | 44,469 | 17.379 |
| R3 peak | 43.740 | 77.196 | 97,507 | 18.062 |

The dormant readability threshold requires frame mean above 3, hero mean above 2, and more than 30 hero pixels above luma 80. R3 passes with 488 bright hero pixels.

Frame and hero means progress monotonically from dormant through peak. Peak/dormant ratios are approximately `2.10x` for the full frame and `3.74x` for the hero, preserving meaningful dynamic range. The dormant hero remains brighter than the secondary console.
