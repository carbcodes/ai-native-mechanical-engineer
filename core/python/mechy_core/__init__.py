"""mechy_core: fast math for Mechy (see docs/architecture/contracts.md, section 7).

All units SI, angles in radians, arrays numpy float64.
The compiled functions live in ``mechy_core._mechy_core``; this package
re-exports them and adds a few defaults taken from the contract's example
hardware (NEMA 17 on A4988, arm v1).
"""
from __future__ import annotations

import numpy as np

from ._mechy_core import (  # noqa: F401
    Arm,
    Stepper,
    ball_drag_k,
    ball_fit,
    ball_intercept,
    ball_predict,
    min_move_time,
    plan_batch,
    plan_move,
)

__version__ = "0.1.0"

#: Approximate NEMA 17 pull-out torque on an A4988 at 12 V: [rev/s, N*m]
#: (contracts.md section 1.2).
NEMA17_TORQUE_CURVE = np.array([[0.0, 0.45], [2.0, 0.40], [5.0, 0.28], [10.0, 0.12]])
NEMA17_ROTOR_INERTIA = 5.4e-6  # kg*m^2

#: Gear ratios of base, shoulder, elbow, wrist in design v1 (section 1.3).
V1_GEAR_RATIOS = (3.0, 4.0, 3.0, 2.0)


def default_motors(gear_ratios=V1_GEAR_RATIOS) -> list:
    """Four NEMA 17 steppers with the given reductions (base..wrist)."""
    return [Stepper(NEMA17_TORQUE_CURVE, float(n), NEMA17_ROTOR_INERTIA) for n in gear_ratios]


def default_arm() -> Arm:
    """Arm v1 from contracts.md section 1.3 with its joint limits."""
    return Arm(0.12, 0.22, 0.20, 0.06)


__all__ = [
    "Arm",
    "Stepper",
    "ball_drag_k",
    "ball_fit",
    "ball_intercept",
    "ball_predict",
    "min_move_time",
    "plan_batch",
    "plan_move",
    "NEMA17_TORQUE_CURVE",
    "NEMA17_ROTOR_INERTIA",
    "V1_GEAR_RATIOS",
    "default_motors",
    "default_arm",
]
