# mechy-core

C++17 math library for Mechy with Python bindings (`import mechy_core`). API contract:
`docs/architecture/contracts.md` section 7. No dependencies beyond pybind11 (build) and numpy.

## Build and test

```bash
uv venv core/.venv && source core/.venv/bin/activate   # or python -m venv
uv pip install ./core pytest                           # or: pip install ./core pytest
pytest core/tests
python core/bench.py
```

The build uses scikit-build-core + CMake (>= 3.18) and fetches pybind11 as a build requirement.
Sources: `include/mechy/*.hpp`, `src/{ball,arm,motion}.cpp` (plain C++, static lib
`mechy_core_lib`), `src/bindings.cpp` (module `mechy_core._mechy_core`), and
`python/mechy_core/__init__.py` (re-exports + defaults).

## API (all SI, radians, numpy float64)

| Call | Returns |
|---|---|
| `ball_fit(points (N,4), mass, diameter, cd=0.55, rho=1.2, g=9.81)` | `dict(p0, v0, t0, residual, iterations)`; state at `t0` = earliest sample, RMS error m |
| `ball_predict(p0, v0, dt=0.002, t_max=2.0, mass, diameter, cd, rho, g, t0=0.0)` | `(M,4)` `[t,x,y,z]`, first row at `t0`, last at `t0+t_max` |
| `ball_intercept(traj, center, radius)` | `dict(t, p, v)` where the path first enters the sphere, or `None` |
| `Arm(base_height, upper, fore, hand, limits=None)` | `limits` (4,2) rad, default = section 1.3 |
| `arm.ik(target, hand_pitch, seed=None)` | `(4,)` or `None` (out of reach or outside limits) |
| `arm.fk(q)` / `arm.reachable(t, pitch)` / `arm.within_limits(q)` | `(p, pitch)` / bool / bool |
| `Stepper(torque_curve (K,2), gear_ratio, rotor_inertia, max_speed_rps=-1)` | `.torque_at(rps)`, `.max_joint_speed` |
| `plan_move(q0, q1, motors, load_inertia, t_avail, safety=0.7, load_torque=None)` | `dict(feasible, t_needed, t_per_joint, peak_torque_frac, limiting_joint)` |
| `plan_batch(q0, Q1 (N,4), motors, load_inertia, T_avail, safety, load_torque, threads=0)` | same keys, arrays over N; `q0`/`load_*` may be (4,) or (N,4) |
| `min_move_time(motor, load_inertia, dist, safety, load_torque)` | seconds, one joint |
| `default_arm()`, `default_motors()`, `NEMA17_TORQUE_CURVE` | v1 arm and NEMA 17 setup from the contract |

`Arm` and `Stepper` pickle, so they work with multiprocessing.

## Physics and conventions

**Ball.** `a = (0,0,-g) - k|v|v`, `k = rho*Cd*A/(2m)` (~0.020 1/m for a tennis ball). No spin/Magnus,
no wind. RK4 integration. `ball_fit` is Levenberg-Marquardt on all 3N coordinates with a
numeric Jacobian, started from the closed-form drag-free fit. `ball_intercept` tests each straight
segment between samples, so a fast ball cannot jump over a small sphere.

**Arm.** z up. `q0` base yaw about +z (0 = +x). `q1` shoulder elevation above horizontal,
`q2` elbow and `q3` wrist relative to the previous link, positive = up. Hand pitch
`= q1+q2+q3` = hand elevation above horizontal, in the arm's vertical plane, pointing away from
the base axis. The tool point is the end of the hand link. The shoulder axis is on the base axis at
`base_height`. IK points the base at the target and solves elbow-up/elbow-down, returning the
valid one closest to `seed` (or to zero). Poses that lean back over the base (tool behind the
base axis) are never returned. Positive elevation is a rotation about the arm-plane **-y** axis,
so MJCF generators must flip signs for a +y hinge.

**Motors** (`include/mechy/motion.hpp` has the full derivation). Per joint, referred to the motor shaft:
`J_m = J_rotor + J_load/N^2` (same as `J_rotor*N^2 + J_load` at the joint),
`alpha(w) = (s*T(w) - |tau_load|/N) / J_m`, with `T(w)` the linearly interpolated pull-out curve
(0 above max speed) and `s = 0.7` the safety fraction against skipped steps. Each joint runs its
own time-optimal rest-to-rest profile: full available acceleration up to the cruise speed (max
speed, or 95% of the speed where `alpha` hits 0), cruise, mirrored braking (braking needs the same
torque). Load torque is assumed to oppose motion in both phases (conservative); gear losses and
friction are ignored. `t_per_joint` is the minimum time at `s = 0.7`; `feasible` means all of them
fit in `t_avail`. `peak_torque_frac` is the smallest fraction of pull-out torque that still
finishes within `t_avail` (`inf` if impossible), so `feasible == all(peak_torque_frac <= 0.7)`.
`load_inertia` is the inertia each joint drives about its own axis; the caller computes it for the
current pose (worst case). Joints are not coupled (no Coriolis or inertia cross terms) and are not
synchronised.
