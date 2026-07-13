"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import {
  Float,
  Icosahedron,
  MeshDistortMaterial,
} from "@react-three/drei";
import { EffectComposer, Bloom, Vignette, ChromaticAberration, DepthOfField } from "@react-three/postprocessing";
import { BlendFunction } from "postprocessing";
import * as THREE from "three";
import { scrollStore } from "@/lib/scrollStore";

/* ----------------------------------------------------------------
   SHOT LIST  (the "story" the camera walks through)
   0.00  HERO     — far, slow spin, title.
   0.33  PUSH-IN  — dolly toward the core (profiling).
   0.66  ORBIT    — arc around the lattice (the "silent killers").
   1.00  REVEAL   — pull back, full frame, CTA.
   ---------------------------------------------------------------- */
interface Shot {
  at: number;
  pos: [number, number, number];
  look: [number, number, number];
  fov: number;
  lightIntensity: number;
  lightColor: string;
  fogDensity: number;
  dof: boolean;
}

const SHOTS: Shot[] = [
  { at: 0.0, pos: [0, 0.2, 9.5], look: [0, 0, 0], fov: 46, lightIntensity: 1.1, lightColor: "#bfffe9", fogDensity: 8, dof: true },
  { at: 0.34, pos: [0.6, 0.7, 4.6], look: [0, 0.1, 0], fov: 42, lightIntensity: 1.4, lightColor: "#a8d8ff", fogDensity: 6, dof: false },
  { at: 0.66, pos: [-4.4, 1.4, 4.0], look: [0, 0, 0], fov: 50, lightIntensity: 0.9, lightColor: "#ffb454", fogDensity: 10, dof: false },
  { at: 1.0, pos: [0, 0.3, 7.2], look: [0, 0, 0], fov: 46, lightIntensity: 1.3, lightColor: "#bfffe9", fogDensity: 7, dof: true },
];

function smoothstep(t: number) {
  return t * t * (3 - 2 * t);
}

function sampleShot<T>(p: number, extract: (s: Shot) => T, lerpFn: (a: T, b: T, t: number) => T): T {
  p = Math.max(0, Math.min(1, p));
  let a = SHOTS[0];
  let b = SHOTS[SHOTS.length - 1];
  for (let i = 0; i < SHOTS.length - 1; i++) {
    if (p >= SHOTS[i].at && p <= SHOTS[i + 1].at) {
      a = SHOTS[i];
      b = SHOTS[i + 1];
      break;
    }
  }
  const span = b.at - a.at || 1;
  const t = smoothstep((p - a.at) / span);
  return lerpFn(extract(a), extract(b), t);
}

function sampleVector(p: number, key: "pos" | "look") {
  return sampleShot(
    p,
    (s) => new THREE.Vector3(...s[key]),
    (a, b, t) => a.clone().lerp(b, t)
  );
}

function sampleFloat(p: number, key: keyof Shot) {
  return sampleShot(p, (s) => s[key] as number, (a, b, t) => THREE.MathUtils.lerp(a, b, t));
}

function sampleColor(p: number) {
  return sampleShot(
    p,
    (s) => new THREE.Color(s.lightColor),
    (a, b, t) => a.clone().lerp(b, t)
  );
}

/* ---------- The "Living Schema": a dataset rendered as a 3D lattice ---------- */
function Lattice({ quality }: { quality: number }) {
  const ref = useRef<THREE.InstancedMesh>(null);
  const group = useRef<THREE.Group>(null);

  const { count, size, gap } = useMemo(() => {
    const n = quality > 0.5 ? 9 : 6;
    return { count: n * n * n, size: n, gap: 0.42 };
  }, [quality]);

  const dummy = useMemo(() => new THREE.Object3D(), []);
  const color = useMemo(() => new THREE.Color(), []);

  const done = useRef(false);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    if (!done.current) {
      let i = 0;
      const half = (size - 1) / 2;
      for (let x = 0; x < size; x++) {
        for (let y = 0; y < size; y++) {
          for (let z = 0; z < size; z++) {
            dummy.position.set((x - half) * gap, (y - half) * gap, (z - half) * gap);
            const s = 0.16 + 0.05 * Math.sin((x + y + z) * 0.6);
            dummy.scale.setScalar(s);
            dummy.updateMatrix();
            ref.current.setMatrixAt(i, dummy.matrix);
            const t = z / (size - 1);
            color.set("#00e5a0").lerp(new THREE.Color("#ff5c7a"), t);
            ref.current.setColorAt(i, color);
            i++;
          }
        }
      }
      ref.current.instanceMatrix.needsUpdate = true;
      if (ref.current.instanceColor) ref.current.instanceColor.needsUpdate = true;
      done.current = true;
    }
    if (group.current) {
      group.current.rotation.y += 0.0016;
      group.current.rotation.x = Math.sin(clock.elapsedTime * 0.15) * 0.12 + scrollStore.pointer.y * 0.2;
      group.current.rotation.y += scrollStore.pointer.x * 0.0008;
    }
  });

  return (
    <group ref={group}>
      <instancedMesh ref={ref} args={[undefined as any, undefined as any, count]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial vertexColors roughness={0.35} metalness={0.1} emissive="#0a3d2c" emissiveIntensity={0.4} />
      </instancedMesh>
    </group>
  );
}

/* ---------- The "data core" ---------- */
function DataCore() {
  return (
    <Float speed={1.4} rotationIntensity={0.6} floatIntensity={0.8}>
      <Icosahedron args={[1.05, 6]}>
        <MeshDistortMaterial color="#00e5a0" emissive="#00e5a0" emissiveIntensity={0.55} roughness={0.2} metalness={0.3} distort={0.38} speed={1.8} />
      </Icosahedron>
    </Float>
  );
}

/* ---------- Camera rig with per-shot mood ---------- */
function Rig() {
  const { camera, scene } = useThree();
  const target = useRef(new THREE.Vector3());
  const dirLight = useRef<THREE.DirectionalLight>(null);

  useEffect(() => {
    scene.fog = new THREE.Fog("#0a0e14", 8, 18);
    return () => { scene.fog = null; };
  }, []);

  useFrame(() => {
    const p = scrollStore.current;
    const pos = sampleVector(p, "pos");
    const look = sampleVector(p, "look");
    camera.position.lerp(pos, 0.07);
    target.current.lerp(look, 0.07);
    (camera as THREE.PerspectiveCamera).lookAt(target.current);
    const cam = camera as THREE.PerspectiveCamera;
    cam.fov = THREE.MathUtils.lerp(cam.fov, sampleFloat(p, "fov"), 0.07);
    cam.updateProjectionMatrix();

    if (dirLight.current) {
      const c = sampleColor(p);
      dirLight.current.color.copy(c);
      dirLight.current.intensity = THREE.MathUtils.lerp(dirLight.current.intensity, sampleFloat(p, "lightIntensity"), 0.05);
    }
    if (scene.fog) {
      (scene.fog as THREE.Fog).far = THREE.MathUtils.lerp((scene.fog as THREE.Fog).far, sampleFloat(p, "fogDensity") + 10, 0.04);
    }
  });

  return (
    <group>
      <directionalLight ref={dirLight} position={[5, 6, 4]} intensity={1.1} color="#bfffe9" />
    </group>
  );
}

/* ---------- Atmosphere ---------- */
function Scene({ quality }: { quality: number }) {
  return (
    <>
      <color attach="background" args={["#0a0e14"]} />
      <ambientLight intensity={0.25} />
      <pointLight position={[-6, -2, -4]} intensity={2.2} color="#ff5c7a" distance={20} />
      <DataCore />
      <Lattice quality={quality} />
      <Rig />
    </>
  );
}

/* ---------- DOF controlled by current shot ---------- */
function Effects() {
  const [bokehScale, setBokehScale] = useState(0);
  const bokehRef = useRef(0);
  useFrame(() => {
    const wantsDof = sampleFloat(scrollStore.current, "dof");
    const target = wantsDof > 0.5 ? 0.12 : 0;
    bokehRef.current = THREE.MathUtils.lerp(bokehRef.current, target, 0.05);
    setBokehScale(bokehRef.current);
  });
  return (
    <EffectComposer>
      <Bloom mipmapBlur intensity={0.85} luminanceThreshold={0.55} luminanceSmoothing={0.3} />
      <ChromaticAberration blendFunction={BlendFunction.NORMAL} offset={new THREE.Vector2(0.0009, 0.0012)} radialModulation={false} modulationOffset={0} />
      <DepthOfField focalLength={0.02} bokehScale={bokehScale} height={700} />
      <Vignette eskil={false} offset={0.25} darkness={0.75} />
    </EffectComposer>
  );
}

export default function LivingSchema({ quality = 1 }: { quality?: number }) {
  return (
    <Canvas
      dpr={[1, quality > 0.5 ? 1.6 : 1.2]}
      gl={{ antialias: true, powerPreference: "high-performance" }}
      camera={{ position: [0, 0.2, 9.5], fov: 46 }}
      onPointerMove={(e) => {
        scrollStore.pointer.x = (e as any).clientX / window.innerWidth - 0.5;
        scrollStore.pointer.y = (e as any).clientY / window.innerHeight - 0.5;
      }}
    >
      <Scene quality={quality} />
      <Effects />
    </Canvas>
  );
}
