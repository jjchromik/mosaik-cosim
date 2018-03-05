"""
Database of operating resources.

"""
from collections import namedtuple


Transformer = namedtuple('Transformer', 'sr, i_max_p, i_max_s, pl, r, x, taps')
"""Transformer with

- *S_r* [MVA] as *sr*,
- *I_max_primary* [A] as *I_max_p*,
- *I_max_secondary* [A], as *I_max_s*,
- *P_loss* [kW] as *pl*,
- *R* [Ω] as *r*,
- *X* [Ω] as *x*,
- *taps*.

"""

Line = namedtuple('Line', 'r, x, c, i')
"""Line with *R'* [Ω/km] as *r*, *X'* [Ω/km] as *x*, *C'* [nF/km] as *b* and
*I_max* [A] as *i*."""


taps_9_002 = {
    -4: 0.92,
    -3: 0.94,
    -2: 0.96,
    -1: 0.98,
     0: 1.0,
     1: 1.02,
     2: 1.04,
     3: 1.06,
     4: 1.08,
}  # NOQA


transformers = {
    # High to medium voltage
    'TRAFO_31':  Transformer(31.5, 165.0,  827.0, 120, 0.0443, 1.7143, taps_9_002),  # NOQA
    'TRAFO_40':  Transformer(40,   209.9, 1050.0, 160, 0.0350, 1.3500, taps_9_002),  # NOQA

    # Medium to low voltage
    'TRAFO_200': Transformer(0.20,  5.5, 288.6, 3.6, 0.00960, 0.02432, {0: 1.0}),  # NOQA
    'TRAFO_250': Transformer(0.25,  6.9, 360.8, 3.6, 0.00960, 0.02432, {0: 1.0}),  # NOQA
    'TRAFO_400': Transformer(0.40, 11.5, 577.4, 3.6, 0.00520, 0.01800, {0: 1.0}),  # NOQA
    'TRAFO_630': Transformer(0.63, 18.2, 909.3, 3.6, 0.00305, 0.01194, {0: 1.0}),  # NOQA
}
lines = {
    # Medium voltage
    'NA2XS2Y_120':    Line(0.253, 0.126, 235, 287),
    'NA2XS2Y_185':    Line(0.162, 0.119, 247, 362),
    'AL/ST_70/12/20': Line(0.430, 0.357, 9.8, 275),

    # Low voltage
    'NAYY_35':  Line(0.8690, 0.0851, 0, 120),
    'NAYY_50':  Line(0.6417, 0.0848, 0, 141),
    'NAYY_70':  Line(0.4442, 0.0823, 0, 180),
    'NAYY_95':  Line(0.3200, 0.0820, 0, 215),
    'NAYY_120': Line(0.2542, 0.0804, 0, 240),
    'NAYY_150': Line(0.2067, 0.0804, 0, 270),
    'NAYY_185': Line(0.1650, 0.0804, 0, 307),
    'NAYY_240': Line(0.1267, 0.0798, 0, 360),
}

# base MVA to use with a certain RefBus voltage level
base_mva = {
    20: 1,
    110: 10,
}
