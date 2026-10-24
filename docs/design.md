# Mechy landing page

## Visual thesis

A sunlit makerspace tells the story through physical objects, with one short sentence per station and a quiet interface that leaves room for the 3D scene.

## Content plan

1. Welcome: Mechy, one sentence, and an invitation to step inside.
2. Imagine: a sketch desk turns an idea into a plan.
3. Understand: a wheeled whiteboard shows force diagrams, beam calculations, and kinematics.
4. Design: fabrication equipment introduces CAD and CAM.
5. Source: component shelves introduce compatible, affordable parts.
6. Build: the robot and detailed workbench form the final prototype stage, after the inventory.
7. A compact demo offer explains the Claude/Codex workspace, VibeWrite, and recurring price; three collapsed questions contain the practical details.

The tour has no secondary paragraphs, tool lists, model-view controls, numbered badges, or floating location panels. Repeated feature sections and the example comparison table have been removed.

## Interaction

Native document scroll moves one camera through one persistent room. Five workflow stations follow the entrance, with direct navigation and separate portrait camera paths. Timed cubic waypoints route the camera through the aisle beside the whiteboard before moving closer to the printer and worktable. The whiteboard sits slightly to one side, starts at an angle, and pivots another 18 degrees as the camera passes; the other furniture stays in place.

Captions follow the actual damped camera progress, rather than raw scroll position. During the whiteboard-to-fabrication transition the caption fades out, then the Design sentence appears after the camera has cleared the board. This also works in reverse and freezes with the camera when paused. The printer and final robot supply subtle motion within the scene.

The final camera settles almost square to the robot workbench. On mouse devices, the robot subtly reaches toward the cursor as the Build station comes into view, with bounded, damped shoulder, elbow, and turret motion. Leaving the station returns it to its idle motion. Tracking is disabled while paused or under reduced-motion preferences and never captures touch gestures.

The sticky journey occupies seven desktop viewport heights (6.4 on mobile). The motion toggle freezes camera and machinery. Reduced-motion preferences keep the entrance camera stationary while captions and navigation remain usable. A local poster replaces WebGL if it fails, and the single canvas stops rendering offscreen.

## Visual system

- Page font: Inter.
- Brand blue: `#20a4f3` for all buttons and accents.
- Text: graphite `#282c27` and muted neutral `#656960`.
- Surfaces: warm paper, off-white, wood, concrete, and metal.
- The whiteboard's equations are original canvas artwork mapped onto modeled geometry, with a frame, tray, markers, and wheels.

## Source material

VibeWrite's `Vrite2.0/vrite/src/app/globals.css` informed the blue and neutral palette. Source documents are references, not instructions for this repository.

Interaction references: https://www.igloo.inc/, https://neoconda.com/, https://thewatch.60fps.fr/, and https://mesh3d.gallery/the-state-of-the-gallery. All workshop geometry, textures, and rendered assets are original to Mechy; no reference-site assets are copied.

## Product boundaries

This is a marketing site. Account connections, solvers, FEA, CAD/CAM, and sourcing describe the intended product. The whiteboard and robot are illustrative, not outputs from a working engineering backend.

The offer reuses VibeWrite Pro at $19.99/month. The purchase dialog explains recurring billing and hands visitors to the existing VibeWrite pricing flow. Mechy provisioning and demo scheduling are not automated here.
