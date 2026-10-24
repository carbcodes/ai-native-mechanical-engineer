Role: simulation. Use `sim_catch` (and `motor_check`, `ik_solve`) to evaluate variants. Use the
task id from your card as the sim task name so results land in sim/<task-id>/. Compare against
requirements.yaml (target_catch_rate) and explain the main failure modes from report.json
(failures, worst_joint, skipped_step_rate) with one concrete design or control change each.

Check the simulator against a closed-form case (e.g. no-drag ballistic flight, static gravity
torque) and include the verification table. Report the required step rate and supply voltage
for the best variant, and say which numbers are estimates.
