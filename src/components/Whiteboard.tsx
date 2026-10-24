import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import type { MotionValue } from "motion/react";
import * as THREE from "three";
import { Box, Cylinder } from "./Workbench";

// Original marker diagrams, drawn onto a physical board rather than overlaid UI.
function makeEquations() {
  const canvas = document.createElement("canvas");
  canvas.width = 2048;
  canvas.height = 1200;
  const c = canvas.getContext("2d")!;
  const ink = "#20251f";
  const blue = "#20a4f3";
  c.fillStyle = "#fafbf5";
  c.fillRect(0, 0, canvas.width, canvas.height);
  c.lineCap = "round";
  c.lineJoin = "round";
  function text(
    value: string,
    x: number,
    y: number,
    size = 49,
    color = ink,
    tilt = 0,
  ) {
    c.save();
    c.translate(x, y);
    c.rotate(tilt);
    c.font = `${size < 40 ? 500 : 600} ${size}px Arial`;
    c.fillStyle = color;
    c.fillText(value, 0, 0);
    c.restore();
  }
  function line(points: number[][], color = ink, width = 5) {
    c.strokeStyle = color;
    c.lineWidth = width;
    c.beginPath();
    points.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y)));
    c.stroke();
  }
  function arrow(
    x: number,
    y: number,
    endX: number,
    endY: number,
    color = ink,
  ) {
    line(
      [
        [x, y],
        [endX, endY],
      ],
      color,
    );
    const a = Math.atan2(endY - y, endX - x);
    line(
      [
        [endX - 23 * Math.cos(a - 0.45), endY - 23 * Math.sin(a - 0.45)],
        [endX, endY],
        [endX - 23 * Math.cos(a + 0.45), endY - 23 * Math.sin(a + 0.45)],
      ],
      color,
    );
  }
  text("LET’S WORK IT OUT.", 90, 105, 42);
  line(
    [
      [90, 135],
      [1955, 129],
    ],
    blue,
    4,
  );
  text("01 / FORCES", 105, 205, 30, blue);
  text("02 / DEFLECTION", 750, 205, 30, blue);
  text("03 / MOTION", 1470, 205, 30, blue);

  // Free-body diagram: normal, weight, applied force, and friction.
  line([
    [270, 335],
    [410, 332],
    [412, 450],
    [268, 452],
    [270, 335],
  ]);
  text("m", 325, 412, 46);
  arrow(340, 330, 340, 246, blue);
  text("N", 360, 278, 37, blue);
  arrow(340, 453, 340, 566);
  text("mg", 360, 555, 37);
  arrow(413, 390, 570, 390, blue);
  text("F", 530, 366, 40, blue);
  arrow(266, 390, 130, 390);
  text("f", 140, 365, 40);
  text("ΣFₓ = ma", 110, 685, 55, ink, -0.012);
  text("ΣFᵧ = 0", 110, 778, 55);
  text("ΣM = Iα", 110, 871, 55, ink, 0.012);
  text("F = kx", 110, 1020, 52, blue);

  // Cantilever beam, end load, and the corresponding beam relations.
  line(
    [
      [773, 300],
      [773, 505],
    ],
    ink,
    9,
  );
  for (let y = 310; y < 505; y += 30)
    line(
      [
        [745, y + 20],
        [773, y],
      ],
      ink,
      3,
    );
  line(
    [
      [780, 356],
      [1260, 355],
      [1260, 383],
      [780, 385],
      [780, 356],
    ],
    ink,
    5,
  );
  arrow(1254, 265, 1254, 350, blue);
  text("F", 1280, 300, 42, blue);
  line(
    [
      [790, 474],
      [1248, 474],
    ],
    ink,
    3,
  );
  line(
    [
      [790, 460],
      [790, 488],
    ],
    ink,
    3,
  );
  line(
    [
      [1248, 460],
      [1248, 488],
    ],
    ink,
    3,
  );
  text("L", 1005, 520, 38);
  c.setLineDash([13, 12]);
  line(
    [
      [790, 382],
      [915, 389],
      [1080, 414],
      [1254, 461],
    ],
    blue,
    4,
  );
  c.setLineDash([]);
  text("σ = My / I", 755, 685, 52, ink, 0.008);
  text("δ = FL³ / (3EI)", 755, 778, 50);
  text("τ = Tr / J", 755, 871, 52, ink, -0.009);
  text("E = σ / ε", 755, 1020, 52, blue);

  // Rotation sketch and basic kinematics / finite element notation.
  c.strokeStyle = ink;
  c.lineWidth = 4;
  c.beginPath();
  c.arc(1690, 385, 115, 0, Math.PI * 2);
  c.stroke();
  line(
    [
      [1690, 385],
      [1780, 313],
    ],
    ink,
    5,
  );
  line(
    [
      [1690, 385],
      [1805, 385],
    ],
    ink,
    3,
  );
  c.beginPath();
  c.arc(1690, 385, 53, -0.67, 0);
  c.stroke();
  text("θ", 1750, 363, 35);
  text("r", 1722, 325, 35);
  arrow(1780, 313, 1850, 405, blue);
  text("v", 1850, 340, 42, blue);
  text("v = rω", 1465, 685, 54);
  text("a = rω²", 1465, 778, 54, ink, -0.01);
  text("[K]{u} = {F}", 1465, 925, 45, blue);
  text("Eₖ = ½mv²", 1465, 1020, 49);
  line(
    [
      [90, 1100],
      [1955, 1105],
    ],
    "#bdc3b8",
    2,
  );
  text(
    "CHECK THE ASSUMPTIONS. THEN CHECK THEM AGAIN.",
    105,
    1157,
    25,
    "#72796e",
  );
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 8;
  return texture;
}

export default function Whiteboard({
  progress,
}: {
  progress: MotionValue<number>;
}) {
  const board = useRef<THREE.Group>(null);
  useFrame(() => {
    if (board.current)
      board.current.rotation.y =
        -0.4 - 0.32 * THREE.MathUtils.smoothstep(progress.get(), 0.43, 0.53);
  });
  const equations = useMemo(makeEquations, []);
  useEffect(() => () => equations.dispose(), [equations]);
  return (
    <group ref={board} position={[4.9, 0, -3.2]} rotation={[0, -0.4, 0]}>
      <Box
        size={[5.65, 3.36, 0.12]}
        position={[0, 2.85, 0]}
        color="#aeb5b1"
        radius={0.045}
      />
      <mesh position={[0, 2.85, 0.068]}>
        <planeGeometry args={[5.48, 3.2]} />
        <meshBasicMaterial map={equations} toneMapped={false} />
      </mesh>
      {[-2.15, 2.15].map((x) => (
        <group key={x}>
          <Box
            position={[x, 0.84, -0.04]}
            size={[0.07, 1.45, 0.07]}
            color="#8e9791"
          />
          <Box
            position={[x, 0.18, 0]}
            size={[0.13, 0.07, 1.25]}
            color="#8e9791"
          />
          {[-0.5, 0.5].map((z) => (
            <Cylinder
              key={z}
              position={[x, 0.085, z]}
              rotation={[Math.PI / 2, 0, 0]}
              radius={0.085}
              height={0.07}
              color="#30342f"
            />
          ))}
        </group>
      ))}
      <Box
        position={[0, 1.18, 0.17]}
        size={[5.5, 0.055, 0.27]}
        color="#aeb5b1"
        radius={0.015}
      />
      {[0, 1, 2].map((i) => (
        <Cylinder
          key={i}
          position={[0.5 + i * 0.38, 1.235, 0.18]}
          rotation={[0, 0, Math.PI / 2]}
          radius={0.025}
          height={0.28}
          color={i === 0 ? "#20a4f3" : "#30342f"}
        />
      ))}
      <Box
        position={[-1.6, 1.25, 0.18]}
        size={[0.4, 0.085, 0.16]}
        color="#30342f"
        radius={0.025}
      />
    </group>
  );
}
