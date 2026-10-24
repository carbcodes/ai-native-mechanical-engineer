# Tennis-ball catching arm

## Goal
Build a small desktop robot arm that catches a tennis ball gently tossed to it
from about 1.8 m away, and holds it in a cup.

## Constraints
- 4 degrees of freedom: base yaw, shoulder, elbow, wrist pitch.
- Uses parts the user already owns: 4 NEMA 17 steppers, 4 A4988 drivers, an Arduino.
- Motors sit at the base and drive the joints with belts, so the moving links stay light.
- A camera watches the throw (60 fps assumed) and a host computer predicts where the ball goes.
- 3D-printed links and catcher cup; total parts budget under about $60 beyond what is owned.

## Success
- Catches at least 80% of gentle underhand tosses that land within its reach.
- Never drops a caught ball within half a second of catching it.
- Safe: slow enough at rest and weak enough not to hurt a hand.

## Out of scope (for now)
- Fast overhand throws, catching from the side or behind, mobile base.
