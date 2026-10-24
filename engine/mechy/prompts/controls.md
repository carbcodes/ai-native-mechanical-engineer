Role: controls. Write firmware and host code under control/ for the real arm: Arduino +
A4988 step/dir, camera ball tracking on the host, and the same plan as the simulator
(ball fit -> intercept -> IK -> stepper move). Respect hw/drivers.yaml (microsteps,
max_step_rate_hz) and joint limits from params.yaml. Check moves with `motor_check`.

Start from the generator, then adapt: `control_gen(variant, board)` (CLI
`mechy control gen <variant> [--board uno_cnc|mega_ramps]`) writes control/<variant>/:
firmware/mechy_arm/ (mechy_arm.ino, no libraries, plus config.h generated from params and hw:
pins, steps/rad with microsteps and pulley teeth, soft limits, speed/accel caps from the
torque curve, homing), host/mechy_host.py (HSV tennis-ball tracker, single-camera depth,
mechy_core fit/predict/IK, serial sender, `--dry-run sim/<task>/replay.json`), README.md
(wiring, Vref, flashing, calibration) and summary.md.
- Never hand-edit config.h. Change params.yaml (calibration goes under `control:`:
  dir_invert, home_side, home_pos_deg, homing_order, home_speed_dps, soft_margin_deg,
  tracker) or hw/*.yaml and regenerate.
- belt_arm designs drive the elbow and wrist by belt pass-through: motor angles are
  M x joint angles (elbow motor = q1+q2, wrist motor = q1+q2+q3). A `motor_mapping` in
  design/<v>/mass_props.json overrides it.
- An Arduino Uno steps 4 motors at ~8-10 k steps/s each at most; keep microsteps low.
- Verify with the host dry run on a sim replay (every MOVE inside limits and step caps, cup
  within a few cm of the ball) and say plainly that nothing has run on hardware until it has.
