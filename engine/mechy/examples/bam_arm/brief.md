# BAM desktop pick-and-place arm

## Goal
A 3D-printed desktop robot arm that picks small parts from a tray and places them
in a bin, over and over, with 4 NEMA 17 steppers and an Arduino Mega.

## Constraints
- Based on the 20sffactory Community Robot Arm (CC BY 4.0), stretched to 140 mm shanks.
- Parallel linkage keeps the gripper level; the wrist has no motor.
- Motors sit at the base, driving the joints through 20T to 90T GT2 belts.
- Servo gripper (MG90S, 9 g). The 4th motor drives a 400 mm linear rail.
- Parts budget under about $120 beyond what is owned.

## Success
- Carries at least 200 g in the whole pick-and-place zone.
- Cycle under 3 s for a 150 mm move.
- Every motor under 50% of its holding torque at rest.

## Out of scope (for now)
- Machining-grade accuracy, vision-guided picking, payloads above 0.5 kg.
