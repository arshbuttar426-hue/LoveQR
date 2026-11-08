"""Registry of all experiments, in execution order."""

from __future__ import annotations

from .e01_capacity import SPEC as E01
from .e02_patterns import SPEC as E02
from .e03_frame_robustness import SPEC as E03
from .e04_geometry import SPEC as E04
from .e05_erasures import SPEC as E05
from .e06_errors import SPEC as E06
from .e07_compression import SPEC as E07
from .e08_rolling import SPEC as E08
from .e09_end_to_end import SPEC as E09
from .e10_determinism import SPEC as E10
from .e11_physical import SPEC as E11
from .e12_channel_efficiency import SPEC as E12
from .e13_packet_utilisation import SPEC as E13

EXPERIMENTS = (E01, E02, E03, E04, E05, E06, E07, E08, E09, E10, E11, E12, E13)
BY_ID = {spec.id: spec for spec in EXPERIMENTS}
