import { Component, useEffect, useMemo, useRef } from "react";
import type { ReactNode } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { RoundedBox } from "@react-three/drei";
import type { MotionValue } from "motion/react";
import * as THREE from "three";

export type ModelMode = "solid" | "wire" | "stress" | "exploded";
type Vec3 = [number, number, number];
const BLUE = "#20a4f3";
const STEEL = "#bfc3bd";
const INK = "#30342f";

function seeded(seed: number) {
  return () => {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return seed / 4294967296;
  };
}

function makeTexture(kind: "wood" | "mat" | "paper" | "screen" | "label") {
  const canvas = document.createElement("canvas");
  canvas.width = 1024;
  canvas.height = 768;
  const c = canvas.getContext("2d")!;
  const random = seeded(24);
  c.fillStyle = {
    wood: "#d5ba96",
    mat: "#6c7663",
    paper: "#faf9ee",
    screen: "#eaf1ed",
    label: "#fbfaf1",
  }[kind];
  c.fillRect(0, 0, 1024, 768);
  if (kind === "wood") {
    for (let i = 0; i < 1600; i++) {
      const y = random() * 768;
      c.beginPath();
      c.moveTo(0, y);
      c.bezierCurveTo(
        250,
        y + random() * 9,
        650,
        y - random() * 12,
        1024,
        y + random() * 5,
      );
      c.strokeStyle = `rgba(${random() > 0.5 ? "106,75,49" : "255,238,205"},${random() * 0.19})`;
      c.lineWidth = random() * 2;
      c.stroke();
    }
    for (let i = 0; i < 5; i++) {
      c.fillStyle = "rgba(107,76,41,.15)";
      c.fillRect(0, i * 160, 1024, 2);
    }
  }
  if (kind === "mat" || kind === "paper") {
    c.strokeStyle = kind === "mat" ? "#83afb5" : "#c5d9e2";
    c.lineWidth = 1;
    for (let i = 0; i < 1024; i += 32) {
      c.beginPath();
      c.moveTo(i, 0);
      c.lineTo(i, 768);
      c.stroke();
    }
    for (let i = 0; i < 768; i += 32) {
      c.beginPath();
      c.moveTo(0, i);
      c.lineTo(1024, i);
      c.stroke();
    }
    c.strokeStyle = kind === "mat" ? "#b4d2d0" : "#99bacf";
    c.lineWidth = 2;
    c.strokeRect(32, 32, 960, 704);
    if (kind === "mat") {
      c.font = "13px monospace";
      c.fillStyle = "#c0d8d7";
      for (let i = 1; i < 31; i++) c.fillText(String(i), 32 * i, 25);
      for (let i = 1; i < 23; i++) c.fillText(String(i), 8, 32 * i);
      [80, 120, 160].forEach((r) => {
        c.beginPath();
        c.arc(810, 570, r, 0, Math.PI * 2);
        c.stroke();
      });
      c.font = "bold 25px sans-serif";
      c.fillText("MECHY / MAKING SPACE", 60, 700);
      c.font = "16px monospace";
      c.fillText("CUTTING MAT     A2     1:1", 60, 732);
    } else {
      c.strokeStyle = "#52594f";
      c.fillStyle = "#52594f";
      c.lineWidth = 4;
      c.font = "500 42px Arial";
      c.fillText("What if it could…", 80, 110);
      c.beginPath();
      c.moveTo(220, 560);
      c.lineTo(370, 300);
      c.lineTo(680, 400);
      c.lineTo(720, 520);
      c.stroke();
      c.lineWidth = 2;
      [
        [220, 560, 65],
        [370, 300, 52],
        [680, 400, 36],
      ].forEach(([x, y, r]) => {
        c.beginPath();
        c.arc(x, y, r, 0, Math.PI * 2);
        c.stroke();
      });
      c.strokeRect(125, 600, 210, 50);
      c.strokeRect(686, 520, 74, 80);
      c.font = "28px Arial";
      c.fillText("F = ma", 680, 240);
      c.fillText("v0.3 — try a lighter arm?", 100, 720);
      c.setLineDash([10, 8]);
      c.beginPath();
      c.moveTo(370, 300);
      c.lineTo(370, 590);
      c.lineTo(650, 590);
      c.stroke();
    }
  }
  if (kind === "screen") {
    c.fillStyle = "#22333b";
    c.fillRect(0, 0, 1024, 78);
    c.fillStyle = "#fff";
    c.font = "bold 35px sans-serif";
    c.fillText("mechy", 45, 52);
    c.font = "20px monospace";
    c.fillStyle = "#d3e3e3";
    c.fillText("PROJECT_001 / ROBOT ARM", 450, 47);
    c.strokeStyle = "#9bbcc5";
    c.lineWidth = 1;
    for (let i = 100; i < 768; i += 40) {
      c.beginPath();
      c.moveTo(250, i);
      c.lineTo(1024, i);
      c.stroke();
    }
    for (let i = 260; i < 1024; i += 40) {
      c.beginPath();
      c.moveTo(i, 80);
      c.lineTo(i, 768);
      c.stroke();
    }
    c.fillStyle = "#d3deda";
    c.fillRect(0, 78, 220, 690);
    c.fillStyle = "#4a6068";
    c.font = "24px monospace";
    [
      "ASSEMBLY",
      "▸ Base",
      "▸ Shoulder",
      "▸ Link_01",
      "▸ Link_02",
      "▸ Gripper",
    ].forEach((t, i) => c.fillText(t, 24, 150 + i * 65));
    c.strokeStyle = "#20a4f3";
    c.lineWidth = 22;
    c.beginPath();
    c.moveTo(500, 600);
    c.lineTo(620, 300);
    c.lineTo(850, 430);
    c.lineTo(830, 530);
    c.stroke();
    c.lineWidth = 4;
    [
      [500, 600],
      [620, 300],
      [850, 430],
    ].forEach(([x, y]) => {
      c.beginPath();
      c.arc(x, y, 35, 0, Math.PI * 2);
      c.stroke();
    });
    c.fillStyle = "#20a4f3";
    c.fillRect(420, 650, 180, 35);
    c.fillStyle = "#41606c";
    c.font = "20px monospace";
    c.fillText("CONCEPT / REV 03", 650, 730);
  }
  if (kind === "label") {
    c.fillStyle = "#273740";
    c.font = "bold 140px sans-serif";
    c.fillText("mechy", 70, 270);
    c.font = "52px monospace";
    c.fillText("MAKE SOMETHING REAL.", 70, 400);
    c.fillStyle = "#20a4f3";
    c.fillRect(70, 490, 850, 30);
    c.font = "40px monospace";
    c.fillStyle = "#536571";
    c.fillText("PROTOTYPE 001 / REV.03", 70, 620);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  return texture;
}

export function useTexture(kind: Parameters<typeof makeTexture>[0]) {
  const texture = useMemo(() => makeTexture(kind), [kind]);
  useEffect(() => () => texture.dispose(), [texture]);
  return texture;
}

export function Box({
  position = [0, 0, 0],
  size,
  color = STEEL,
  rotation = [0, 0, 0],
  radius = 0.025,
  metalness = 0.15,
  roughness = 0.55,
}: {
  position?: Vec3;
  size: Vec3;
  color?: string;
  rotation?: Vec3;
  radius?: number;
  metalness?: number;
  roughness?: number;
}) {
  return (
    <RoundedBox
      args={size}
      radius={radius}
      smoothness={2}
      position={position}
      rotation={rotation}
      castShadow
      receiveShadow
    >
      <meshStandardMaterial
        color={color}
        metalness={metalness}
        roughness={roughness}
      />
    </RoundedBox>
  );
}

export function Cylinder({
  position = [0, 0, 0],
  radius = 0.2,
  height = 0.1,
  color = STEEL,
  rotation = [0, 0, 0],
  metalness = 0.75,
  segments = 48,
}: {
  position?: Vec3;
  radius?: number;
  height?: number;
  color?: string;
  rotation?: Vec3;
  metalness?: number;
  segments?: number;
}) {
  return (
    <mesh position={position} rotation={rotation} castShadow receiveShadow>
      <cylinderGeometry args={[radius, radius, height, segments]} />
      <meshStandardMaterial
        color={color}
        metalness={metalness}
        roughness={0.32}
      />
    </mesh>
  );
}

export function Bolt({
  position = [0, 0, 0],
  rotation = [0, 0, 0],
  scale = 1,
}: {
  position?: Vec3;
  rotation?: Vec3;
  scale?: number;
}) {
  return (
    <group position={position} rotation={rotation} scale={scale}>
      <Cylinder radius={0.064} height={0.045} segments={6} />
      <Cylinder radius={0.027} height={0.047} color="#233037" segments={6} />
      <Cylinder position={[0, -0.07, 0]} radius={0.03} height={0.12} />
    </group>
  );
}

export function Cable({
  points,
  color = INK,
  radius = 0.025,
}: {
  points: Vec3[];
  color?: string;
  radius?: number;
}) {
  const curve = useMemo(
    () =>
      new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(...p))),
    [points],
  );
  return (
    <mesh castShadow>
      <tubeGeometry args={[curve, 32, radius, 7, false]} />
      <meshStandardMaterial color={color} roughness={0.7} />
    </mesh>
  );
}

function LinkPlate({
  length,
  position,
  mode,
}: {
  length: number;
  position: Vec3;
  mode: ModelMode;
}) {
  const geo = useMemo(() => {
    const shape = new THREE.Shape();
    const r = 0.22;
    shape.moveTo(-r, 0);
    shape.absarc(0, 0, r, Math.PI, Math.PI * 2, false);
    shape.lineTo(r, length);
    shape.absarc(0, length, r, 0, Math.PI, false);
    shape.closePath();
    [0, length].forEach((y) => {
      const hole = new THREE.Path();
      hole.absarc(0, y, 0.104, 0, Math.PI * 2, true);
      shape.holes.push(hole);
    });
    const slot = new THREE.Path();
    slot.moveTo(-0.075, 0.38);
    slot.lineTo(-0.075, length - 0.38);
    slot.absarc(0, length - 0.38, 0.075, Math.PI, 0, true);
    slot.lineTo(0.075, 0.38);
    slot.absarc(0, 0.38, 0.075, 0, -Math.PI, true);
    shape.holes.push(slot);
    const g = new THREE.ExtrudeGeometry(shape, {
      depth: 0.095,
      bevelEnabled: true,
      bevelSegments: 2,
      steps: 1,
      bevelSize: 0.018,
      bevelThickness: 0.012,
      curveSegments: 24,
    });
    const pos = g.getAttribute("position");
    const colors = [];
    const color = new THREE.Color();
    for (let i = 0; i < pos.count; i++) {
      const y = pos.getY(i);
      const stress = Math.max(0, 1 - y / (length * 0.8));
      color.setHSL(0.62 - stress * 0.62, 0.85, 0.54);
      colors.push(color.r, color.g, color.b);
    }
    g.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    return g;
  }, [length]);
  useEffect(() => () => geo.dispose(), [geo]);
  return (
    <mesh geometry={geo} position={position} castShadow receiveShadow>
      {mode === "stress" ? (
        <meshBasicMaterial vertexColors toneMapped={false} />
      ) : (
        <meshStandardMaterial
          color={BLUE}
          metalness={0.65}
          roughness={0.34}
          wireframe={mode === "wire"}
        />
      )}
    </mesh>
  );
}

function Joint({
  radius = 0.24,
  exploded = false,
  reduced = false,
}: {
  radius?: number;
  exploded?: boolean;
  reduced?: boolean;
}) {
  const caps = useRef<THREE.Group>(null);
  useFrame((_, delta) => {
    caps.current?.children.forEach((cap, i) => {
      const target = exploded ? (i === 0 ? -0.35 : 0.35) : 0;
      cap.position.z = reduced
        ? target
        : THREE.MathUtils.damp(cap.position.z, target, 5, delta);
    });
  });
  return (
    <group>
      <Cylinder
        radius={radius}
        height={0.65}
        rotation={[Math.PI / 2, 0, 0]}
        color={INK}
      />
      <group ref={caps}>
        {[-1, 1].map((s) => (
          <group key={s}>
            <Cylinder
              radius={radius * 0.9}
              height={0.07}
              position={[0, 0, s * 0.36]}
              rotation={[Math.PI / 2, 0, 0]}
            />
            <Cylinder
              radius={radius * 0.58}
              height={0.08}
              position={[0, 0, s * 0.4]}
              rotation={[Math.PI / 2, 0, 0]}
              color={BLUE}
            />
            <Bolt
              position={[0, 0, s * 0.45]}
              rotation={[(s * Math.PI) / 2, 0, 0]}
              scale={1.25}
            />
          </group>
        ))}
      </group>
    </group>
  );
}

export function Robot({
  mode = "solid",
  play = false,
  reduced = false,
  scale = 1,
  followPointer,
}: {
  mode?: ModelMode;
  play?: boolean;
  reduced?: boolean;
  scale?: number;
  followPointer?: MotionValue<number>;
}) {
  const shoulder = useRef<THREE.Group>(null);
  const elbow = useRef<THREE.Group>(null);
  const left = useRef<THREE.Group>(null);
  const right = useRef<THREE.Group>(null);
  const platform = useRef<THREE.Group>(null);
  const separation = useRef(0);
  const plates = useRef<THREE.Group>(null);
  const pointer = useRef({ x: 0, y: 0, present: false });
  const tracking = useRef(0);
  const { gl } = useThree();
  useEffect(() => {
    const surface = gl.domElement.closest<HTMLElement>(".journey-sticky");
    if (!followPointer || !play || reduced || !surface) return;
    const hover = window.matchMedia("(any-hover: hover) and (any-pointer: fine)");
    const reset = () => {
      pointer.current.present = false;
    };
    const move = (event: PointerEvent) => {
      if (event.pointerType !== "mouse" || !hover.matches) return;
      const bounds = surface.getBoundingClientRect();
      pointer.current = {
        x: THREE.MathUtils.clamp(
          ((event.clientX - bounds.left) / bounds.width) * 2 - 1,
          -1,
          1,
        ),
        y: THREE.MathUtils.clamp(
          1 - ((event.clientY - bounds.top) / bounds.height) * 2,
          -1,
          1,
        ),
        present: true,
      };
    };
    // Listen over the whole station, including its caption and navigation.
    // Passive mouse-only tracking leaves native touch scrolling untouched.
    surface.addEventListener("pointermove", move, { passive: true });
    surface.addEventListener("pointerleave", reset);
    window.addEventListener("blur", reset);
    return () => {
      surface.removeEventListener("pointermove", move);
      surface.removeEventListener("pointerleave", reset);
      window.removeEventListener("blur", reset);
      reset();
    };
  }, [followPointer, gl, play, reduced]);
  useFrame(({ clock }, frameDelta) => {
    const delta = Math.min(frameDelta, 0.05);
    const t = clock.elapsedTime;
    const active = play && !reduced;
    if (active) {
      tracking.current = THREE.MathUtils.damp(
        tracking.current,
        pointer.current.present && followPointer
          ? THREE.MathUtils.smoothstep(followPointer.get(), 0.9, 0.98)
          : 0,
        5,
        delta,
      );
      const x = pointer.current.x * tracking.current;
      const y = pointer.current.y * tracking.current;
      const idle = 1 - tracking.current;
      // Small opposing joint offsets move the gripper toward the cursor;
      // the fixed base stays planted, and every joint eases into its pose.
      if (platform.current)
        platform.current.rotation.y = THREE.MathUtils.damp(
          platform.current.rotation.y,
          x * 0.1,
          5,
          delta,
        );
      if (shoulder.current)
        shoulder.current.rotation.z = THREE.MathUtils.damp(
          shoulder.current.rotation.z,
          -0.38 - x * 0.2 + y * 0.14 + Math.sin(t * 0.8) * 0.17 * idle,
          5,
          delta,
        );
      if (elbow.current)
        elbow.current.rotation.z = THREE.MathUtils.damp(
          elbow.current.rotation.z,
          -1.18 + x * 0.25 + y * 0.18 + Math.sin(t * 0.8 + 1) * 0.23 * idle,
          5,
          delta,
        );
      if (left.current)
        left.current.rotation.z = THREE.MathUtils.damp(
          left.current.rotation.z,
          0.15 + Math.sin(t * 1.7) * 0.15,
          6,
          delta,
        );
      if (right.current)
        right.current.rotation.z = -(left.current?.rotation.z ?? 0.15);
    }
    separation.current = reduced
      ? mode === "exploded"
        ? 0.9
        : 0
      : THREE.MathUtils.damp(
          separation.current,
          mode === "exploded" ? 0.9 : 0,
          4,
          delta,
        );
    if (platform.current)
      platform.current.position.y = 0.35 + separation.current * 0.5;
    if (plates.current) {
      plates.current.children.forEach((child, i) => {
        child.position.z = (i === 0 ? -1 : 1) * separation.current * 0.7;
      });
    }
    if (followPointer && platform.current && shoulder.current && elbow.current) {
      gl.domElement.dataset.robotPose = [
        platform.current.rotation.y,
        shoulder.current.rotation.z,
        elbow.current.rotation.z,
      ]
        .map((angle) => angle.toFixed(4))
        .join(",");
    }
  });
  return (
    <group scale={scale}>
      <Cylinder
        radius={0.73}
        height={0.13}
        position={[0, 0.065, 0]}
        color={INK}
      />
      <Cylinder
        radius={0.65}
        height={0.18}
        position={[0, 0.2, 0]}
        color={BLUE}
      />
      {[0, 1, 2, 3].map((i) => (
        <Bolt
          key={i}
          position={[
            Math.cos((i * Math.PI) / 2 + 0.7) * 0.54,
            0.31,
            Math.sin((i * Math.PI) / 2 + 0.7) * 0.54,
          ]}
        />
      ))}
      <group ref={platform} position={[0, 0.35, 0]}>
        <Cylinder radius={0.42} height={0.16} color={STEEL} />
        <Cylinder
          radius={0.35}
          height={0.2}
          position={[0, 0.11, 0]}
          color={INK}
        />
        <Box
          position={[0, 0.28, 0]}
          size={[0.56, 0.32, 0.58]}
          color={BLUE}
          radius={0.07}
        />
        <group position={[0, 0.46, 0]} ref={shoulder} rotation={[0, 0, -0.38]}>
          <Joint exploded={mode === "exploded"} reduced={reduced} />
          <group ref={plates}>
            <group>
              <LinkPlate length={1.65} position={[0, 0, -0.29]} mode={mode} />
            </group>
            <group>
              <LinkPlate length={1.65} position={[0, 0, 0.19]} mode={mode} />
            </group>
          </group>
          {[0.38, 1.3].map((y) => (
            <Cylinder
              key={y}
              radius={0.065}
              height={0.5}
              rotation={[Math.PI / 2, 0, 0]}
              position={[0, y, 0]}
            />
          ))}
          <Box
            size={[0.27, 0.7, 0.32]}
            position={[0, 0.82, 0]}
            color={INK}
            radius={0.035}
          />
          <Cable
            points={[
              [-0.2, 0.1, 0],
              [-0.34, 0.65, 0],
              [-0.32, 1.3, 0],
              [-0.1, 1.7, 0],
            ]}
            radius={0.035}
          />
          <Cable
            points={[
              [-0.25, 0.1, 0.06],
              [-0.4, 0.65, 0.06],
              [-0.38, 1.3, 0.06],
              [-0.14, 1.7, 0.06],
            ]}
            color={BLUE}
            radius={0.018}
          />
          <group position={[0, 1.65, 0]} ref={elbow} rotation={[0, 0, -1.18]}>
            <Joint
              radius={0.21}
              exploded={mode === "exploded"}
              reduced={reduced}
            />
            <LinkPlate length={1.25} position={[0, 0, -0.22]} mode={mode} />
            <LinkPlate length={1.25} position={[0, 0, 0.13]} mode={mode} />
            <Box size={[0.2, 0.6, 0.22]} position={[0, 0.64, 0]} color={INK} />
            <Cylinder
              radius={0.055}
              height={0.4}
              position={[0, 0.36, 0]}
              rotation={[Math.PI / 2, 0, 0]}
            />
            <Cable
              points={[
                [-0.2, 0, 0],
                [-0.3, 0.45, 0],
                [-0.28, 0.95, 0],
                [0, 1.25, 0],
              ]}
              radius={0.025}
            />
            <group position={[0, 1.25, 0]} rotation={[0, 0, -0.95]}>
              <Joint
                radius={0.16}
                exploded={mode === "exploded"}
                reduced={reduced}
              />
              <Box
                size={[0.4, 0.4, 0.38]}
                position={[0, 0.24, 0]}
                color={BLUE}
                radius={0.04}
              />
              <Box
                size={[0.49, 0.1, 0.4]}
                position={[0, 0.49, 0]}
                color={STEEL}
              />
              {[-1, 1].map((s) => (
                <group
                  ref={s === -1 ? left : right}
                  key={s}
                  position={[s * 0.19, 0.5, 0]}
                  rotation={[0, 0, -s * 0.15]}
                >
                  <Box
                    size={[0.1, 0.36, 0.21]}
                    position={[0, 0.16, 0]}
                    color={STEEL}
                  />
                  <Box
                    size={[0.18, 0.22, 0.22]}
                    position={[-s * 0.035, 0.43, 0]}
                    color={INK}
                  />
                  <Bolt
                    position={[0, 0.09, 0.12]}
                    rotation={[Math.PI / 2, 0, 0]}
                    scale={0.65}
                  />
                </group>
              ))}
            </group>
          </group>
        </group>
      </group>
    </group>
  );
}

export function Lamp() {
  return (
    <group position={[-2.9, 0, -1.3]} rotation={[0, 0.4, 0]}>
      <Cylinder radius={0.4} height={0.09} color={INK} />
      <Cylinder
        radius={0.3}
        height={0.05}
        position={[0, 0.07, 0]}
        color={BLUE}
      />
      <group position={[0, 0.1, 0]} rotation={[0, 0, -0.18]}>
        {[-0.08, 0.08].map((z) => (
          <Box
            key={z}
            size={[0.055, 1.6, 0.055]}
            position={[0, 0.8, z]}
            color={INK}
          />
        ))}
        <Cylinder
          radius={0.1}
          height={0.25}
          position={[0, 1.6, 0]}
          rotation={[Math.PI / 2, 0, 0]}
          color={STEEL}
        />
        <group position={[0, 1.6, 0]} rotation={[0, 0, -1.15]}>
          {[-0.08, 0.08].map((z) => (
            <Box
              key={z}
              size={[0.05, 1.2, 0.05]}
              position={[0, 0.6, z]}
              color={INK}
            />
          ))}
          <Cylinder
            radius={0.1}
            height={0.25}
            position={[0, 1.2, 0]}
            rotation={[Math.PI / 2, 0, 0]}
          />
          <group position={[0, 1.25, 0]} rotation={[0, 0, 1.1]}>
            <mesh castShadow>
              <cylinderGeometry args={[0.12, 0.43, 0.4, 48, 1, true]} />
              <meshStandardMaterial
                color={BLUE}
                metalness={0.5}
                roughness={0.3}
                side={THREE.DoubleSide}
              />
            </mesh>
            <mesh position={[0, -0.2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
              <circleGeometry args={[0.39, 48]} />
              <meshStandardMaterial
                color="#fff4cf"
                emissive="#fff1c9"
                emissiveIntensity={1}
              />
            </mesh>
          </group>
        </group>
      </group>
      <Cable
        points={[
          [0, 0.07, -0.13],
          [-0.1, 0.7, -0.13],
          [0, 1.7, -0.13],
          [0.65, 2.1, -0.13],
          [1.1, 2.2, -0.13],
        ]}
        radius={0.015}
      />
    </group>
  );
}

export function Laptop() {
  const texture = useTexture("screen");
  return (
    <group position={[-1.85, 0.03, -0.8]} rotation={[0, 0.32, 0]}>
      <Box size={[1.65, 0.06, 1.15]} color="#8a9599" radius={0.04} />
      <Box
        position={[0, 0.037, -0.1]}
        size={[1.45, 0.016, 0.64]}
        color={INK}
        radius={0.02}
      />
      {Array.from({ length: 5 }, (_, row) =>
        Array.from({ length: 12 }, (_, col) => (
          <Box
            key={`${row}-${col}`}
            size={[0.088, 0.01, 0.08]}
            position={[-0.65 + col * 0.118, 0.05, -0.35 + row * 0.12]}
            color="#4b575d"
            radius={0.006}
          />
        )),
      )}
      <Box
        position={[0, 0.04, 0.37]}
        size={[0.55, 0.01, 0.27]}
        color="#a8b2b5"
        radius={0.015}
      />
      <group position={[0, 0.04, -0.53]} rotation={[-0.17, 0, 0]}>
        <Box
          position={[0, 0.55, 0]}
          size={[1.65, 1.1, 0.055]}
          color={INK}
          radius={0.05}
        />
        <mesh position={[0, 0.56, 0.031]}>
          <planeGeometry args={[1.54, 0.95]} />
          <meshStandardMaterial
            map={texture}
            roughness={0.75}
            emissive="#ffffff"
            emissiveMap={texture}
            emissiveIntensity={0.18}
          />
        </mesh>
      </group>
    </group>
  );
}

export function Notebook() {
  const texture = useTexture("paper");
  return (
    <group position={[-1.8, 0.04, 1.35]} rotation={[0, -0.24, 0]}>
      <Box size={[1.55, 0.06, 1.1]} color="#d8d6c7" radius={0.01} />
      <mesh position={[0, 0.034, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[1.52, 1.08]} />
        <meshStandardMaterial map={texture} roughness={0.95} />
      </mesh>
      {Array.from({ length: 12 }, (_, i) => (
        <mesh
          key={i}
          position={[-0.73, 0.055, -0.47 + i * 0.085]}
          rotation={[0, Math.PI / 2, 0]}
        >
          <torusGeometry args={[0.04, 0.008, 5, 12]} />
          <meshStandardMaterial color={INK} metalness={0.7} />
        </mesh>
      ))}
      <group position={[0.25, 0.09, 0.05]} rotation={[0, 0.44, Math.PI / 2]}>
        <Cylinder radius={0.035} height={1.2} color={BLUE} segments={6} />
        <mesh position={[0, 0.69, 0]}>
          <coneGeometry args={[0.035, 0.18, 6]} />
          <meshStandardMaterial color="#c89e74" />
        </mesh>
        <mesh position={[0, 0.79, 0]}>
          <coneGeometry args={[0.012, 0.06, 6]} />
          <meshStandardMaterial color={INK} />
        </mesh>
        <Cylinder
          position={[0, -0.64, 0]}
          radius={0.037}
          height={0.08}
          color={STEEL}
        />
      </group>
    </group>
  );
}

export function Caliper() {
  return (
    <group position={[2.25, 0.07, 1.4]} rotation={[0, -0.45, 0]}>
      <Box size={[1.55, 0.035, 0.13]} color={STEEL} metalness={0.9} />
      <Box
        size={[0.08, 0.1, 0.56]}
        position={[-0.68, 0.01, 0.15]}
        color={STEEL}
        metalness={0.9}
      />
      <Box
        size={[0.08, 0.1, 0.56]}
        position={[-0.15, 0.01, 0.15]}
        color={STEEL}
        metalness={0.9}
      />
      <Box size={[0.35, 0.13, 0.26]} position={[-0.14, 0.06, 0]} color={INK} />
      <Box
        size={[0.24, 0.01, 0.14]}
        position={[-0.14, 0.13, 0]}
        color="#a4beb0"
        radius={0.003}
      />
      {Array.from({ length: 25 }, (_, i) => (
        <Box
          key={i}
          size={[0.008, 0.004, i % 5 === 0 ? 0.07 : 0.035]}
          position={[-0.6 + i * 0.05, 0.02, -0.025]}
          color={INK}
          radius={0.001}
        />
      ))}
    </group>
  );
}

function Mug() {
  return (
    <group position={[2.7, 0.02, -1.5]}>
      <mesh position={[0, 0.22, 0]} castShadow>
        <cylinderGeometry args={[0.24, 0.22, 0.44, 48, 1, true]} />
        <meshStandardMaterial
          color="#eeeae0"
          side={THREE.DoubleSide}
          roughness={0.2}
        />
      </mesh>
      <Cylinder
        radius={0.215}
        height={0.015}
        position={[0, 0.39, 0]}
        color="#46362a"
        metalness={0}
      />
      <mesh position={[0.24, 0.25, 0]}>
        <torusGeometry args={[0.14, 0.04, 12, 32]} />
        <meshStandardMaterial color="#eeeae0" roughness={0.2} />
      </mesh>
      <mesh position={[0, 0.442, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.23, 0.015, 8, 48]} />
        <meshStandardMaterial color="#eeeae0" roughness={0.2} />
      </mesh>
    </group>
  );
}

function Pegboard() {
  const holes = useRef<THREE.InstancedMesh>(null);
  const note = useTexture("paper");
  useEffect(() => {
    if (!holes.current) return;
    const matrix = new THREE.Matrix4();
    for (let i = 0; i < 126; i++) {
      matrix.makeTranslation(
        -2.85 + (i % 21) * 0.285,
        0.35 + Math.floor(i / 21) * 0.235,
        -2.196,
      );
      holes.current.setMatrixAt(i, matrix);
    }
    holes.current.instanceMatrix.needsUpdate = true;
  }, []);
  return (
    <group>
      <Box
        size={[6.45, 1.7, 0.09]}
        position={[0, 0.94, -2.25]}
        color="#b2bdb6"
        radius={0.03}
      />
      <Box
        size={[6.5, 0.055, 0.14]}
        position={[0, 1.79, -2.25]}
        color="#859d9f"
        radius={0.01}
      />
      <instancedMesh ref={holes} args={[undefined, undefined, 126]}>
        <circleGeometry args={[0.017, 8]} />
        <meshStandardMaterial color="#6b8285" roughness={0.8} />
      </instancedMesh>
      {[-2.55, -2.25, -1.96].map((x, i) => (
        <group key={x} position={[x, 1.06, -2.12]}>
          <Cylinder
            radius={0.05}
            height={0.32}
            color={i === 1 ? "#d1a96c" : BLUE}
          />
          <Cylinder radius={0.017} height={0.4} position={[0, 0.34, 0]} />
          <Cylinder
            radius={0.057}
            height={0.025}
            color={INK}
            position={[0, 0.13, 0]}
          />
        </group>
      ))}
      <group position={[-1.46, 1.2, -2.1]} rotation={[0, 0, -0.1]}>
        <Box size={[0.1, 0.58, 0.04]} color={STEEL} />
        <mesh position={[0, 0.34, 0]}>
          <torusGeometry args={[0.12, 0.035, 8, 24, Math.PI * 1.6]} />
          <meshStandardMaterial
            color={STEEL}
            metalness={0.85}
            roughness={0.3}
          />
        </mesh>
        <mesh position={[0, -0.35, 0]}>
          <torusGeometry args={[0.09, 0.032, 8, 24]} />
          <meshStandardMaterial
            color={STEEL}
            metalness={0.85}
            roughness={0.3}
          />
        </mesh>
      </group>
      <Box
        size={[1.8, 0.07, 0.43]}
        position={[0.3, 0.7, -2.04]}
        color="#7d969a"
        radius={0.01}
      />
      {[-0.25, 0.3, 0.85].map((x, i) => (
        <group key={x}>
          <Box
            size={[0.44, 0.24, 0.3]}
            position={[x, 0.86, -2.03]}
            color={["#e8e6d4", "#83989a", "#5e8ba0"][i]}
            radius={0.02}
          />
          <Box
            size={[0.2, 0.09, 0.005]}
            position={[x, 0.87, -1.875]}
            color="#e9eadc"
            radius={0.001}
          />
        </group>
      ))}
      <group position={[2.1, 1.14, -2.18]} rotation={[0, 0, -0.08]}>
        <mesh>
          <planeGeometry args={[0.8, 0.62]} />
          <meshStandardMaterial map={note} />
        </mesh>
        <Box
          size={[0.28, 0.07, 0.009]}
          position={[0, 0.31, 0.01]}
          color="#d8d3b5"
          radius={0.002}
        />
      </group>
    </group>
  );
}

export function Worktop({
  play,
  reduced,
  mode = "solid",
  followPointer,
}: {
  play: boolean;
  reduced: boolean;
  mode?: ModelMode;
  followPointer?: MotionValue<number>;
}) {
  const wood = useTexture("wood");
  const mat = useTexture("mat");
  const label = useTexture("label");
  return (
    <group>
      <RoundedBox
        args={[7.6, 0.24, 4.6]}
        radius={0.04}
        smoothness={3}
        position={[0, -0.14, 0]}
        castShadow
        receiveShadow
      >
        <meshStandardMaterial map={wood} roughness={0.8} />
      </RoundedBox>
      {[0.08, 0.12, 0.16, 0.2].map((y) => (
        <Box
          key={y}
          size={[7.57, 0.009, 4.57]}
          position={[0, -y - 0.04, 0]}
          color="#a88c67"
          radius={0.008}
        />
      ))}
      {[-3.3, 3.3].map((x) =>
        [-1.75, 1.75].map((z) => (
          <group key={`${x}${z}`}>
            <Box
              position={[x, -0.98, z]}
              size={[0.13, 1.5, 0.13]}
              color="#536167"
            />
            <Box
              position={[x, -1.72, z]}
              size={[0.18, 0.07, 0.18]}
              color={INK}
            />
          </group>
        )),
      )}
      <Box
        position={[0, -1.55, -1.75]}
        size={[6.7, 0.09, 0.09]}
        color="#536167"
      />
      <Box
        position={[-3.3, -1.3, 0]}
        size={[0.09, 0.09, 3.5]}
        color="#536167"
      />
      <Box position={[3.3, -1.3, 0]} size={[0.09, 0.09, 3.5]} color="#536167" />
      <mesh
        position={[0.35, 0.006, 0.15]}
        rotation={[-Math.PI / 2, 0, 0]}
        receiveShadow
      >
        <boxGeometry args={[3.8, 2.8, 0.015]} />
        <meshStandardMaterial map={mat} roughness={0.95} />
      </mesh>
      <mesh position={[-2.6, -0.15, 2.309]}>
        <planeGeometry args={[0.7, 0.19]} />
        <meshStandardMaterial map={label} />
      </mesh>
      <Pegboard />
      <Lamp />
      <Laptop />
      <Notebook />
      <Mug />
      <Caliper />
      <group position={[-0.1, 0.03, -0.2]} rotation={[0, -0.24, 0]}>
        <Robot
          play={play}
          reduced={reduced}
          mode={mode}
          followPointer={followPointer}
        />
      </group>
      <group position={[2.4, 0.14, -0.1]} rotation={[0, 0.3, 0]}>
        <Box size={[0.7, 0.22, 0.7]} color="#dce1dd" radius={0.07} />
        <Cylinder
          position={[0, 0.14, 0]}
          radius={0.22}
          height={0.06}
          color={INK}
        />
        <Cylinder position={[0, 0.22, 0]} radius={0.055} height={0.15} />
        {[0, 1, 2, 3].map((i) => (
          <Bolt
            key={i}
            position={[
              Math.cos((i * Math.PI) / 2 + 0.78) * 0.35,
              0.12,
              Math.sin((i * Math.PI) / 2 + 0.78) * 0.35,
            ]}
            scale={0.7}
          />
        ))}
        <Cable
          points={[
            [0.3, 0, 0],
            [0.6, -0.1, 0.1],
            [0.7, -0.1, 0.6],
            [0.4, -0.1, 0.8],
          ]}
          color={BLUE}
          radius={0.025}
        />
      </group>
      <group position={[-0.1, 0.04, 1.48]} rotation={[Math.PI / 2, 0, 0.2]}>
        <Cylinder radius={0.23} height={0.13} color={INK} />
        <Cylinder radius={0.14} height={0.14} color={STEEL} />
        <Cylinder radius={0.08} height={0.15} color="#3a4d54" />
        {Array.from({ length: 16 }, (_, i) => (
          <Box
            key={i}
            size={[0.06, 0.12, 0.07]}
            position={[
              Math.cos((i * Math.PI) / 8) * 0.25,
              0,
              Math.sin((i * Math.PI) / 8) * 0.25,
            ]}
            rotation={[0, (-i * Math.PI) / 8, 0]}
            color={STEEL}
            radius={0.007}
          />
        ))}
      </group>
      <group position={[2.85, 0.08, 0.65]} rotation={[0, 0.3, Math.PI / 2]}>
        <Cylinder radius={0.065} height={0.52} color={BLUE} />
        <Cylinder radius={0.021} height={0.65} position={[0, 0.55, 0]} />
        {[-0.17, 0, 0.17].map((y) => (
          <Cylinder
            key={y}
            radius={0.072}
            height={0.04}
            position={[0, y, 0]}
            color={INK}
          />
        ))}
      </group>
      {Array.from({ length: 9 }, (_, i) => (
        <Bolt
          key={i}
          position={[
            1.5 + (i % 3) * 0.18,
            0.08,
            0.75 + Math.floor(i / 3) * 0.16,
          ]}
          scale={0.7}
          rotation={[0, i * 0.8, i % 3 === 0 ? 1.5 : 0]}
        />
      ))}
      <group position={[-2.8, 0.03, 0.2]}>
        <mesh rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.21, 0.34, 48]} />
          <meshStandardMaterial color="#d8caa6" side={THREE.DoubleSide} />
        </mesh>
        <mesh position={[0, 0.08, 0]}>
          <cylinderGeometry args={[0.34, 0.34, 0.16, 48, 1, true]} />
          <meshStandardMaterial color="#d8caa6" side={THREE.DoubleSide} />
        </mesh>
        <mesh position={[0, 0.16, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.21, 0.34, 48]} />
          <meshStandardMaterial color="#e6d7ad" side={THREE.DoubleSide} />
        </mesh>
      </group>
      <Box
        position={[3.0, 0.008, 1.8]}
        size={[0.6, 0.015, 0.42]}
        color="#f0e3a8"
        radius={0.001}
        rotation={[0, 0.1, 0]}
      />
    </group>
  );
}

export class SceneBoundary extends Component<
  { children: ReactNode; onError: () => void },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    this.props.onError();
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}
