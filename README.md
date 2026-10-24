# Mechy

**Big ideas. Real things.** An AI engineering workbench for makers, hobbyists, and hardware startups.

This repository currently contains Mechy’s interactive landing page, built with React, TypeScript, Vite, React Three Fiber, Three.js, and Motion.

## Run locally

Requires Node.js 22.12 or newer.

```sh
npm ci
npm run dev -- --port 5173
```

Open http://127.0.0.1:5173.

```sh
npm run build     # Type-check and create dist/
npm run preview   # Serve the production build
npm run test:e2e  # Desktop + mobile browser checks (Google Chrome installed locally)
```

## The experience

- One original 3D makerspace with a sketch desk, a wheeled physics whiteboard, fabrication equipment, component shelves, and a working robot bench at the end of the room.
- Native scrolling moves through six stops: Welcome, Imagine, Understand, Design, Source, and Build. Each stage has one sentence; the room carries the story. Captions track the rendered camera, which passes beside the angled whiteboard before moving in toward fabrication. Mobile has its own camera framing.
- The whiteboard contains original force diagrams, beam deflection, kinematics, and finite element notation. The final camera faces the detailed robot workbench almost squarely, and the arm gently follows the mouse with bounded, eased joint motion.
- One page font, Inter, and one brand blue, `#20a4f3`, with warm neutral surfaces and graphite text.
- A compact demo offer and three collapsed questions replace the repeated marketing sections and illustrative comparison sheet.
- Responsive navigation, an accessible purchase dialog, and locally served fonts and visuals. The motion toggle freezes camera and machinery; reduced-motion preferences keep the camera fixed while story navigation remains usable. WebGL failure retains a rendered room poster, and the single canvas stops rendering offscreen.

## Paid demo / VibeWrite Pro

The offer reuses **VibeWrite Pro at $19.99 USD/month**. It is a recurring subscription, not a one-time demo charge.

Every demo CTA opens a disclosure dialog and links to VibeWrite’s existing live pricing page. The visitor chooses **Pro → Monthly**, then completes VibeWrite’s existing account and Stripe checkout flow. A separate email link lets the visitor contact the team with their Pro account email and project to arrange the Mechy demo.

No Stripe credentials or VibeWrite source files are copied. This site does not create subscriptions, verify payments, schedule appointments, or provision Mechy accounts. A direct authenticated checkout handoff and shared Mechy/VibeWrite entitlements are future integration work.

## Product status

The landing page is implemented. Claude/Codex account connections, equation solvers, FBD generation, FEA, CAD, CAM, and supplier agents describe the intended product; those backends are not implemented here. The workshop, whiteboard calculations, and robot illustrate the intended workflow; they are not solver outputs or a validated engineering design. Supplier names do not imply partnerships or verified compatibility.

## Files

- `src/App.tsx`: compact demo offer, FAQ, and purchase flow.
- `src/components/Journey.tsx`: sticky story, native scroll progress, station navigation, and motion controls.
- `src/components/Makerspace.tsx`: continuous room, station models, desktop/mobile camera paths, lighting, and WebGL fallback.
- `src/components/Whiteboard.tsx`: original equation texture, physics diagrams, and wheeled whiteboard model.
- `src/components/Workbench.tsx`: reusable geometry, robot assembly, tools, and procedural textures.
- `src/styles.css`: brand tokens, layout, responsive styles, and reduced-motion behavior.
- `docs/design.md`: art direction, source references, and product boundaries.
- `tests/landing.spec.ts`: desktop/mobile browser verification.
- `public/`: favicon and rendered fallback/social images. Fonts are bundled by Vite from the font packages.

Regenerate the original room poster and social preview with the dev server running:

```sh
node scripts/capture-posters.mjs
```

The production output is a static `dist/` directory. No hosting deployment is configured yet. Set the final public site URL and absolute social-preview URL when connecting a domain.
