# core/ summary

**Built.** `mechy-core`, a C++17 library with pybind11 bindings (`import mechy_core`), installed with
`pip install ./core` (scikit-build-core, no deps except numpy). It implements contracts.md section 7:
- Ball flight with quadratic drag (Cd 0.55, rho 1.2): RK4 `ball_predict`, Levenberg-Marquardt
  `ball_fit` of (p0, v0), and `ball_intercept` with exact segment-sphere crossing.
- `Arm`: analytic 4-DOF IK (base yaw, then planar 3-link at a given hand pitch), FK, joint limits,
  elbow-branch choice by seed.
- `Stepper` + `plan_move` / `plan_batch`: time-optimal, torque-limited rest-to-rest moves using the
  speed-dependent pull-out curve, reflected inertia `J_rotor + J_load/N^2`, optional gravity load,
  70% safety fraction. `plan_batch` runs on all cores with `std::thread`, GIL released.

**Tests.** 20 pytest tests pass (IK/FK round trip on ~1,400 random poses, unreachable targets ->
None, no-drag prediction = analytic to 1e-10, fit recovers state under 3 mm noise, closed-form
check of the motion planner, monotonic in t_avail, batch == loop == single thread).

**Benchmark** (Linux x86-64, 4 cores, `python core/bench.py`):
IK 1.2 M solves/s (Python loop); ball_predict 17.7 k one-second trajectories/s; ball_fit 3.3 k fits/s
(15 samples); plan_move 53 k/s from Python; plan_batch 66 k/s on 1 thread, 238 k/s on 4.

**Open issues.**
- Not built on macOS yet (compiles cleanly with clang++ -Wall -Wextra -Wpedantic on Linux).
- Hand pitch is defined in the arm plane; IK never leans back over the base.
- Joints are planned independently: no coupled dynamics, no synchronised arrival.
- `load_inertia` and `load_torque` must be supplied by the caller for each pose.
- Step rate is not checked: 10 rev/s at 16 microsteps is 32 k steps/s per motor, far beyond what an
  Arduino Uno can generate for 4 motors. A step-rate cap (`max_speed_rps`) is available on `Stepper`.
- No spin/Magnus in the ball model.
