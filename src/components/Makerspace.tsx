import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import type { MotionValue } from "motion/react";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import {
  Bolt,
  Box,
  Cable,
  Cylinder,
  Lamp,
  Notebook,
  SceneBoundary,
  Worktop,
  useTexture,
} from "./Workbench";
import Whiteboard from "./Whiteboard";

type Vec3 = [number, number, number];
const BLUE = "#20a4f3";
const METAL = "#a9afab";
const DARK = "#30342f";

// The extra aisle waypoints keep the camera clear of the whiteboard before
// approaching the printer; the room's furniture stays in its original stations.
const ROUTE: {
  at: number;
  camera: Vec3;
  look: Vec3;
  mobileCamera: Vec3;
  mobileLook: Vec3;
}[] = [
  {
    at: 0,
    camera: [0.4, 3.8, 11.5],
    look: [-0.8, 1.75, -4.5],
    mobileCamera: [0.4, 4.85, 12.8],
    mobileLook: [2.8, 3, -3],
  },
  {
    at: 0.2,
    camera: [-0.4, 3.6, 3.6],
    look: [-6.6, 1.35, -3.8],
    mobileCamera: [-0.4, 4.65, 4.9],
    mobileLook: [-5.3, 2.65, -3.8],
  },
  {
    at: 0.4,
    camera: [5.8, 3.5, 5.4],
    look: [2, 2.65, -3.2],
    mobileCamera: [5.5, 4.8, 10.5],
    mobileLook: [4.8, 3.5, -3.2],
  },
  {
    at: 0.47,
    camera: [-0.4, 3.4, 1],
    look: [3.7, 2.2, -8.5],
    mobileCamera: [-0.4, 4.4, 1.8],
    mobileLook: [5, 3.2, -9.2],
  },
  {
    at: 0.52,
    camera: [0.8, 3.2, -4.7],
    look: [4.4, 2.2, -11.4],
    mobileCamera: [1.4, 4.05, -4.4],
    mobileLook: [5.7, 3, -11.4],
  },
  {
    at: 0.6,
    camera: [4, 3.05, -6.25],
    look: [4, 1.95, -11.4],
    mobileCamera: [4.1, 3.9, -4.8],
    mobileLook: [5.85, 3, -11.4],
  },
  {
    at: 0.8,
    camera: [1, 3.3, -9.7],
    look: [-6.6, 1.85, -18],
    mobileCamera: [1, 4.35, -8.4],
    mobileLook: [-5.7, 3.1, -18],
  },
  {
    at: 1,
    camera: [3.4, 3, -18.3],
    look: [2.5, 1.8, -25.5],
    mobileCamera: [3.2, 3.6, -17],
    mobileLook: [4.3, 2.65, -25.5],
  },
];

function CameraTravel({
  progress,
  renderedProgress,
  reduced,
  paused,
}: {
  progress: MotionValue<number>;
  renderedProgress: MotionValue<number>;
  reduced: boolean;
  paused: boolean;
}) {
  const { camera, gl, invalidate, size } = useThree();
  const value = useRef(progress.get());
  const initialized = useRef(false);
  const paths = useMemo(() => {
    const times = new Float32Array(ROUTE.map((key) => key.at));
    const curve = (field: "camera" | "look" | "mobileCamera" | "mobileLook") =>
      new THREE.CubicInterpolant(
        times,
        new Float32Array(ROUTE.flatMap((key) => key[field])),
        3,
      );
    return {
      camera: curve("camera"),
      look: curve("look"),
      mobileCamera: curve("mobileCamera"),
      mobileLook: curve("mobileLook"),
      target: new THREE.Vector3(),
    };
  }, []);
  useEffect(
    () => progress.on("change", () => invalidate()),
    [progress, invalidate],
  );
  useFrame((_, delta) => {
    if (paused && initialized.current && !reduced) return;
    const next = reduced ? 0 : THREE.MathUtils.clamp(progress.get(), 0, 1);
    value.current =
      initialized.current && !reduced
        ? THREE.MathUtils.damp(value.current, next, 7, Math.min(delta, 0.05))
        : next;
    const mobile = size.width < 760;
    camera.position.fromArray(
      (mobile ? paths.mobileCamera : paths.camera).evaluate(value.current),
    );
    paths.target.fromArray(
      (mobile ? paths.mobileLook : paths.look).evaluate(value.current),
    );
    camera.lookAt(paths.target);
    // Captions and the small whiteboard pivot follow the rendered camera,
    // including during fast scrolling, pausing, and reversing direction.
    renderedProgress.set(value.current);
    gl.domElement.dataset.cameraPosition = camera.position
      .toArray()
      .map((v) => v.toFixed(3))
      .join(",");
    gl.domElement.dataset.cameraProgress = value.current.toFixed(4);
    initialized.current = true;
  }, -1);
  return null;
}

function makeSurface(kind: "concrete" | "wall") {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 512;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = kind === "concrete" ? "#b4b3a8" : "#e0dfd5";
  ctx.fillRect(0, 0, 512, 512);
  let seed = 23;
  const random = () => {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return seed / 4294967296;
  };
  for (let i = 0; i < 12000; i++) {
    ctx.fillStyle =
      random() > 0.5 ? "rgba(255,255,255,.035)" : "rgba(50,45,35,.025)";
    ctx.fillRect(random() * 512, random() * 512, random() * 3 + 1, 1);
  }
  if (kind === "concrete") {
    ctx.strokeStyle = "#a09f95";
    ctx.lineWidth = 1;
    ctx.strokeRect(1, 1, 510, 510);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(kind === "concrete" ? 8 : 4, kind === "concrete" ? 14 : 2);
  texture.anisotropy = 4;
  return texture;
}

function Label({
  text,
  position,
  width = 2,
  height = 0.4,
  dark = false,
  rotation = [0, 0, 0],
}: {
  text: string;
  position: Vec3;
  width?: number;
  height?: number;
  dark?: boolean;
  rotation?: Vec3;
}) {
  const texture = useMemo(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 1024;
    canvas.height = 256;
    const c = canvas.getContext("2d")!;
    c.fillStyle = dark ? DARK : "#e9e7dc";
    c.fillRect(0, 0, 1024, 256);
    c.fillStyle = dark ? "#e9e7dc" : DARK;
    c.font = "500 75px Arial";
    c.textAlign = "center";
    c.textBaseline = "middle";
    c.fillText(text, 512, 128);
    const result = new THREE.CanvasTexture(canvas);
    result.colorSpace = THREE.SRGBColorSpace;
    return result;
  }, [text, dark]);
  useEffect(() => () => texture.dispose(), [texture]);
  return (
    <mesh position={position} rotation={rotation}>
      <planeGeometry args={[width, height]} />
      <meshStandardMaterial map={texture} roughness={0.9} />
    </mesh>
  );
}

function Architecture() {
  const surfaces = useMemo(
    () => ({ floor: makeSurface("concrete"), wall: makeSurface("wall") }),
    [],
  );
  useEffect(
    () => () => {
      surfaces.floor.dispose();
      surfaces.wall.dispose();
    },
    [surfaces],
  );
  return (
    <>
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        receiveShadow
        position={[0, -0.02, -10]}
      >
        <planeGeometry args={[22, 44]} />
        <meshStandardMaterial map={surfaces.floor} roughness={0.9} />
      </mesh>
      <mesh
        position={[-11, 3.5, -10]}
        rotation={[0, Math.PI / 2, 0]}
        receiveShadow
      >
        <planeGeometry args={[44, 7]} />
        <meshStandardMaterial map={surfaces.wall} roughness={1} />
      </mesh>
      <mesh
        position={[11, 3.5, -10]}
        rotation={[0, -Math.PI / 2, 0]}
        receiveShadow
      >
        <planeGeometry args={[44, 7]} />
        <meshStandardMaterial map={surfaces.wall} roughness={1} />
      </mesh>
      <mesh position={[0, 3.5, -32]} receiveShadow>
        <planeGeometry args={[22, 7]} />
        <meshStandardMaterial map={surfaces.wall} roughness={1} />
      </mesh>
      <Box
        position={[0, 6.95, -10]}
        size={[22, 0.15, 44]}
        color="#d3d1c6"
        radius={0.01}
      />
      {[-10.8, 10.8].map((x) => (
        <Box
          key={x}
          position={[x, 0.15, -10]}
          size={[0.12, 0.3, 44]}
          color="#6c7169"
          radius={0.01}
        />
      ))}
      {[-27, -20, -13, -6, 1, 8].map((z) => (
        <group key={z}>
          <Box
            position={[0, 6.5, z]}
            size={[22, 0.32, 0.2]}
            color="#646960"
            radius={0.01}
          />
          {[-7, 0, 7].map((x) => (
            <group key={x}>
              <Cylinder
                position={[x, 5.9, z]}
                radius={0.017}
                height={1}
                color={DARK}
              />
              <Box
                position={[x, 5.38, z]}
                size={[2.1, 0.12, 0.3]}
                color={DARK}
                radius={0.02}
              />
              <mesh position={[x, 5.31, z]} rotation={[Math.PI / 2, 0, 0]}>
                <planeGeometry args={[1.95, 0.22]} />
                <meshStandardMaterial
                  color="#fff6df"
                  emissive="#fff4db"
                  emissiveIntensity={2}
                  side={THREE.DoubleSide}
                />
              </mesh>
            </group>
          ))}
        </group>
      ))}
      {[-26, -18, -10, -2, 6].map((z) => (
        <group
          key={z}
          position={[10.88, 3.8, z]}
          rotation={[0, -Math.PI / 2, 0]}
        >
          <Box size={[4.8, 3.5, 0.14]} color="#535d52" radius={0.01} />
          <mesh position={[0, 0, 0.08]}>
            <planeGeometry args={[4.55, 3.25]} />
            <meshStandardMaterial
              color="#eeeee1"
              emissive="#f5f0db"
              emissiveIntensity={0.45}
            />
          </mesh>
          {[-1.5, 0, 1.5].map((x) => (
            <Box
              key={x}
              size={[0.055, 3.3, 0.08]}
              position={[x, 0, 0.15]}
              color="#535d52"
              radius={0.005}
            />
          ))}
          <Box
            size={[4.6, 0.055, 0.08]}
            position={[0, 0, 0.15]}
            color="#535d52"
            radius={0.005}
          />
        </group>
      ))}
      <Box
        position={[0, 1.4, -31.7]}
        size={[3.5, 2.8, 0.12]}
        color="#717b70"
        radius={0.01}
      />
      <Box
        position={[1.25, 1.25, -31.59]}
        size={[0.08, 0.4, 0.09]}
        color={METAL}
      />
      <Label
        text="MECHY / WORKSHOP 001"
        position={[-10.87, 3.8, 3]}
        width={3.5}
        height={0.6}
        rotation={[0, Math.PI / 2, 0]}
      />
      {/* Receding aisle marks and roof beams make camera translation legible. */}
      {[-1.35, 1.35].map((x) => (
        <mesh
          key={x}
          rotation={[-Math.PI / 2, 0, 0]}
          position={[x, 0.003, -11]}
        >
          <planeGeometry args={[0.045, 34]} />
          <meshStandardMaterial color="#deded1" roughness={1} />
        </mesh>
      ))}
      {[-26, -18, -12, -6, 0, 6].map((z) => (
        <mesh key={z} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.005, z]}>
          <planeGeometry args={[0.5, 0.055]} />
          <meshStandardMaterial color="#deded1" />
        </mesh>
      ))}
    </>
  );
}

function Table({
  children,
  position,
  width = 4.6,
  depth = 2.5,
}: {
  children?: React.ReactNode;
  position: Vec3;
  width?: number;
  depth?: number;
}) {
  const wood = useTexture("wood");
  return (
    <group position={position}>
      <mesh position={[0, 1.15, 0]} castShadow receiveShadow>
        <boxGeometry args={[width, 0.13, depth]} />
        <meshStandardMaterial map={wood} roughness={0.8} />
      </mesh>
      {[-1, 1].map((x) =>
        [-1, 1].map((z) => (
          <Box
            key={`${x}${z}`}
            position={[x * (width / 2 - 0.2), 0.55, z * (depth / 2 - 0.2)]}
            size={[0.09, 1.1, 0.09]}
            color={DARK}
          />
        )),
      )}
      <Box
        position={[0, 0.25, -depth / 2 + 0.2]}
        size={[width - 0.3, 0.07, 0.07]}
        color={DARK}
      />
      <group position={[0, 1.22, 0]}>{children}</group>
    </group>
  );
}

function Stool({ position }: { position: Vec3 }) {
  return (
    <group position={position}>
      <Cylinder
        radius={0.39}
        height={0.09}
        color="#a98b63"
        position={[0, 0.82, 0]}
        metalness={0}
      />
      {[0, 1, 2, 3].map((i) => (
        <Box
          key={i}
          position={[
            Math.cos((i * Math.PI) / 2 + 0.7) * 0.23,
            0.4,
            Math.sin((i * Math.PI) / 2 + 0.7) * 0.23,
          ]}
          size={[0.035, 0.8, 0.035]}
          color={DARK}
        />
      ))}
      <mesh position={[0, 0.26, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.29, 0.02, 8, 32]} />
        <meshStandardMaterial color={DARK} />
      </mesh>
    </group>
  );
}

function DrawingDesk() {
  const paper = useTexture("paper");
  return (
    <group>
      <Table position={[-5.3, 0, -3.8]} width={5} depth={2.8}>
        <group rotation={[-0.12, 0.08, 0]}>
          <Box
            size={[3.1, 0.08, 1.9]}
            position={[0.3, 0.08, 0]}
            color="#deddd1"
            radius={0.01}
          />
          <mesh position={[0.3, 0.125, 0]} rotation={[-Math.PI / 2, 0, 0]}>
            <planeGeometry args={[2.9, 1.75]} />
            <meshStandardMaterial map={paper} roughness={1} />
          </mesh>
        </group>
        <group scale={0.8} position={[0.5, 0, 0.2]}>
          <Lamp />
        </group>
        <group position={[0.3, 0.03, -0.8]} scale={0.62}>
          <Notebook />
        </group>
        <Cylinder
          radius={0.13}
          height={1.5}
          position={[1.9, 0.15, 0]}
          rotation={[Math.PI / 2, 0, 0]}
          color="#e9e8da"
          metalness={0}
        />
        <Box
          position={[0.2, 0.24, 0.66]}
          size={[2.2, 0.02, 0.06]}
          color={METAL}
          radius={0.004}
        />
        <Cylinder
          radius={0.09}
          height={0.3}
          position={[-1.9, 0.15, -0.8]}
          color={DARK}
        />
        {[0, 1, 2, 3].map((i) => (
          <Cylinder
            key={i}
            radius={0.013}
            height={0.5}
            position={[-1.94 + i * 0.028, 0.35, -0.8]}
            color={i === 1 ? BLUE : "#b89a71"}
            segments={6}
          />
        ))}
      </Table>
      <Stool position={[-5, 0, -1.6]} />
      <Label
        text="01 / IDEAS START HERE"
        position={[-5.3, 2.8, -5.35]}
        width={2.8}
        height={0.4}
      />
      <Box
        size={[4.8, 1.8, 0.06]}
        position={[-5.3, 2.25, -5.4]}
        color="#bab5a1"
        radius={0.01}
      />
      {[-1.4, 0, 1.4].map((x, i) => (
        <mesh
          key={x}
          position={[-5.3 + x, 2.15, -5.355]}
          rotation={[0, 0, (i - 1) * 0.05]}
        >
          <planeGeometry args={[1.1, 0.8]} />
          <meshStandardMaterial map={paper} />
        </mesh>
      ))}
    </group>
  );
}

function Fabrication({ paused }: { paused: boolean }) {
  const head = useRef<THREE.Group>(null);
  useFrame(({ clock }) => {
    if (head.current && !paused)
      head.current.position.x = Math.sin(clock.elapsedTime * 0.55) * 0.42;
  });
  return (
    <group>
      <Table position={[5.4, 0, -11.4]} width={5.5} depth={3}>
        <Box size={[2.6, 0.22, 2]} color={DARK} position={[0.3, 0.11, 0]} />
        <Box size={[2.1, 0.04, 1.6]} color={METAL} position={[0.3, 0.25, 0]} />
        {[-0.7, 1.3].map((x) =>
          [-0.72, 0.72].map((z) => (
            <Box
              key={`${x}${z}`}
              size={[0.1, 2.05, 0.1]}
              color={DARK}
              position={[x, 1.12, z]}
            />
          )),
        )}
        {[-0.72, 0.72].map((z) => (
          <Box
            key={z}
            position={[0.3, 2.1, z]}
            size={[2.1, 0.1, 0.1]}
            color={DARK}
          />
        ))}
        {[-0.7, 1.3].map((x) => (
          <Box
            key={x}
            position={[x, 2.1, 0]}
            size={[0.1, 0.1, 1.5]}
            color={DARK}
          />
        ))}
        <Cylinder
          radius={0.023}
          height={2}
          rotation={[0, 0, Math.PI / 2]}
          position={[0.3, 1.4, 0]}
        />
        <Box size={[2, 0.07, 0.08]} position={[0.3, 1.5, 0.05]} color={METAL} />
        <group ref={head} position={[0, 1.42, 0]}>
          <Box size={[0.3, 0.35, 0.27]} color={BLUE} />
          <Cylinder
            radius={0.035}
            height={0.13}
            position={[0, -0.24, 0]}
            color="#b89a71"
          />
        </group>
        <mesh position={[0.3, 0.4, 0]} castShadow>
          <torusGeometry args={[0.27, 0.1, 12, 40]} />
          <meshStandardMaterial color={BLUE} roughness={0.6} />
        </mesh>
        <Cylinder
          radius={0.42}
          height={0.25}
          position={[1.8, 0.6, -0.4]}
          color={DARK}
          rotation={[Math.PI / 2, 0, 0]}
        />
        <Cylinder
          radius={0.29}
          height={0.27}
          position={[1.8, 0.6, -0.4]}
          color={BLUE}
          rotation={[Math.PI / 2, 0, 0]}
        />
        <Cable
          points={[
            [1.8, 0.9, -0.4],
            [1.8, 2.5, -0.1],
            [0.5, 2.5, 0],
            [0, 1.5, 0],
          ]}
          color={BLUE}
          radius={0.015}
        />
        <Box
          size={[0.6, 0.38, 0.12]}
          position={[1.75, 0.2, 0.8]}
          color={DARK}
          rotation={[-0.25, 0, 0]}
        />
        <Box
          size={[0.46, 0.25, 0.015]}
          position={[1.75, 0.22, 0.89]}
          color="#c3c8b5"
          rotation={[-0.25, 0, 0]}
        />
        <Label
          text="03 / FABRICATE"
          position={[0.3, 0.1, 1.015]}
          width={1.2}
          height={0.18}
          dark
        />
      </Table>
      <Stool position={[7.7, 0, -8.9]} />
      <Table position={[5.4, 0, -17.5]} width={5.5} depth={2.6}>
        <Box size={[2.7, 0.18, 1.8]} position={[0.3, 0.1, 0]} color={DARK} />
        {[-0.8, 1.4].map((x) => (
          <Box
            key={x}
            size={[0.18, 1.3, 1.5]}
            position={[x, 0.7, 0]}
            color={METAL}
          />
        ))}
        <Box size={[2.5, 0.22, 0.22]} position={[0.3, 1.25, 0]} color={BLUE} />
        <Cylinder
          radius={0.14}
          height={0.6}
          position={[0.1, 0.92, 0.1]}
          color={DARK}
        />
        <Box
          size={[1.4, 0.07, 0.9]}
          position={[0.3, 0.24, 0]}
          color="#d2b58d"
        />
        <Label
          text="CNC / MILL 02"
          position={[0.3, 0.09, 0.91]}
          width={1.1}
          height={0.15}
          dark
        />
      </Table>
    </group>
  );
}

function PartsStorage() {
  return (
    <group position={[-5.7, 0, -18.2]}>
      {[-2.8, 2.8].map((x) => (
        <Box
          key={x}
          size={[0.1, 4.5, 1.2]}
          position={[x, 2.25, 0]}
          color={DARK}
        />
      ))}
      {[0.2, 1.15, 2.1, 3.05, 4.0].map((y, row) => (
        <group key={y}>
          <Box size={[5.6, 0.08, 1.25]} position={[0, y, 0]} color="#777d70" />
          {Array.from({ length: 6 }, (_, col) => (
            <group key={col} position={[-2.3 + col * 0.92, y + 0.25, 0.04]}>
              <Box
                size={[0.73, 0.42, 0.86]}
                color={
                  row === 2 && col < 2
                    ? BLUE
                    : row % 2 === 0
                      ? "#b0b5a2"
                      : "#d2c2a2"
                }
                radius={0.035}
              />
              <Box
                size={[0.62, 0.012, 0.7]}
                position={[0, 0.215, 0]}
                color="#52574d"
                radius={0.01}
              />
              <Box
                size={[0.3, 0.12, 0.006]}
                position={[0, -0.03, 0.435]}
                color="#eeeadd"
                radius={0.004}
              />
              <Box
                size={[0.18, 0.02, 0.007]}
                position={[0, -0.03, 0.44]}
                color="#7c8175"
                radius={0.001}
              />
            </group>
          ))}
        </group>
      ))}
      <Label
        text="04 / THE RIGHT PARTS"
        position={[0, 4.65, 0.4]}
        width={3.5}
        height={0.5}
      />
      <Table position={[0, 0, 2.5]} width={4.4} depth={1.8}>
        {[0, 1, 2].map((i) => (
          <group key={i} position={[-1.4 + i * 1.2, 0.08, 0]}>
            <Box size={[0.7, 0.07, 0.55]} color="#cdcbbb" />
            {[0, 1, 2, 3].map((n) => (
              <Bolt key={n} position={[-0.2 + n * 0.13, 0.1, 0]} scale={1.1} />
            ))}
          </group>
        ))}
        <Cylinder
          radius={0.25}
          height={0.14}
          position={[1, 0.15, 0.2]}
          rotation={[Math.PI / 2, 0, 0]}
        />
      </Table>
    </group>
  );
}

function WorkshopLights() {
  const { scene, gl, invalidate } = useThree();
  useEffect(() => {
    const pmrem = new THREE.PMREMGenerator(gl);
    const room = new RoomEnvironment();
    const target = pmrem.fromScene(room, 0.04);
    scene.environment = target.texture;
    scene.environmentIntensity = 0.35;
    invalidate();
    return () => {
      scene.environment = null;
      target.dispose();
      pmrem.dispose();
      room.dispose();
    };
  }, [scene, gl, invalidate]);
  return (
    <>
      <color attach="background" args={["#d7d8ce"]} />
      <fog attach="fog" args={["#d7d8ce", 20, 62]} />
      <ambientLight intensity={0.65} />
      <hemisphereLight args={["#fff8e8", "#7e8273", 1.4]} />
      <directionalLight
        position={[10, 13, 9]}
        intensity={2.3}
        color="#fff3d8"
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-19}
        shadow-camera-right={19}
        shadow-camera-top={24}
        shadow-camera-bottom={-24}
        shadow-camera-near={0.1}
        shadow-camera-far={65}
        shadow-normalBias={0.035}
        shadow-bias={-0.00015}
      />
      <pointLight
        position={[-4, 4.5, -4]}
        intensity={30}
        distance={10}
        decay={2}
        color="#fff1d8"
      />
      <pointLight
        position={[5, 4.7, -12]}
        intensity={25}
        distance={10}
        decay={2}
        color="#fff1d8"
      />
      <pointLight
        position={[-5, 5.3, -18]}
        intensity={25}
        distance={10}
        decay={2}
        color="#fff1d8"
      />
    </>
  );
}

export default function Makerspace({
  progress,
  renderedProgress,
  onReadyChange,
  reduced,
  paused,
}: {
  progress: MotionValue<number>;
  renderedProgress: MotionValue<number>;
  onReadyChange: (ready: boolean) => void;
  reduced: boolean;
  paused: boolean;
}) {
  const wrapper = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [visible, setVisible] = useState(true);
  useEffect(() => {
    onReadyChange(ready && !failed);
    return () => onReadyChange(false);
  }, [ready, failed, onReadyChange]);
  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) =>
      setVisible(entry.isIntersecting),
    );
    if (wrapper.current) observer.observe(wrapper.current);
    return () => observer.disconnect();
  }, []);
  return (
    <div
      ref={wrapper}
      className={`makerspace-scene ${ready && !failed ? "is-ready" : ""}`}
      role="img"
      aria-label="A continuous 3D makerspace. Scroll to travel from the entrance to the sketch desk, physics whiteboard, fabrication area, parts shelves, and working robot prototype."
    >
      <div className="scene-fallback">
        <img
          src="/makerspace-poster.webp"
          alt="A sunlit workshop with workbenches, machinery, and component shelves"
        />
        <span>
          {failed ? "The workshop, at a glance." : "Opening the workshop…"}
        </span>
      </div>
      {!failed && (
        <SceneBoundary onError={() => setFailed(true)}>
          <Canvas
            shadows
            dpr={[1, 1.5]}
            frameloop={
              visible ? (paused || reduced ? "demand" : "always") : "never"
            }
            camera={{ position: ROUTE[0].camera, fov: 52, near: 0.1, far: 90 }}
            gl={{
              antialias: true,
              alpha: false,
              powerPreference: "high-performance",
            }}
            onCreated={({ gl }) => {
              gl.toneMapping = THREE.ACESFilmicToneMapping;
              gl.toneMappingExposure = 1.05;
              gl.domElement.addEventListener(
                "webglcontextlost",
                () => setFailed(true),
                { once: true },
              );
              setReady(true);
            }}
          >
            <Suspense fallback={null}>
              <WorkshopLights />
              <pointLight
                position={[4.3, 4.7, -25.5]}
                intensity={30}
                distance={10}
                decay={2}
                color="#fff1d8"
              />
              <Architecture />
              <DrawingDesk />
              <Whiteboard progress={renderedProgress} />
              <group
                position={[4.3, 1.15, -25.5]}
                scale={0.64}
                rotation={[0, -0.12, 0]}
              >
                <Worktop
                  play={!paused && !reduced}
                  reduced={paused || reduced}
                  followPointer={renderedProgress}
                />
              </group>
              <Stool position={[4.3, 0, -23.1]} />
              <Fabrication paused={paused || reduced} />
              <PartsStorage />
              <CameraTravel
                progress={progress}
                renderedProgress={renderedProgress}
                reduced={reduced}
                paused={paused}
              />
            </Suspense>
          </Canvas>
        </SceneBoundary>
      )}
    </div>
  );
}
