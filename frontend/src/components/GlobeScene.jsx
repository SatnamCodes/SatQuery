import { useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import dayMapUrl from "../assets/earth/earth_atmos_2048.jpg";
import cloudsMapUrl from "../assets/earth/earth_clouds_1024.png";

const GLOW = new THREE.Color("#e3b48c");
const ROTATION_RANGE = Math.PI * 3.5;
const BASE_CAMERA_Z = 6.2;
const DOLLY_AMOUNT = 3.2;

const ATMOSPHERE_VERTEX = `
  varying vec3 vNormal;
  void main() {
    vNormal = normalize(normalMatrix * normal);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;
const ATMOSPHERE_FRAGMENT = `
  varying vec3 vNormal;
  uniform vec3 glowColor;
  void main() {
    float intensity = pow(0.58 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 4.0);
    gl_FragColor = vec4(glowColor, 1.0) * intensity;
  }
`;

// Unlit materials throughout — the source texture is already a fully-lit
// "daytime" map, so no virtual sun/shading is applied. A physically-shaded
// light was creating a dark night-side hemisphere that read as "the globe
// is broken," which isn't the effect wanted here.
function Earth({ progressRef }) {
  const groupRef = useRef(null);
  const cloudsRef = useRef(null);
  const idleSpin = useRef(0);

  const [dayMap, cloudsMap] = useMemo(
    () => [new THREE.TextureLoader().load(dayMapUrl), new THREE.TextureLoader().load(cloudsMapUrl)],
    [],
  );

  useMemo(() => {
    [dayMap, cloudsMap].forEach((t) => {
      t.colorSpace = THREE.SRGBColorSpace;
    });
  }, [dayMap, cloudsMap]);

  const atmosphereUniforms = useMemo(() => ({ glowColor: { value: GLOW } }), []);

  useFrame((_, delta) => {
    idleSpin.current += delta * 0.035;
    const scrollSpin = (progressRef.current ?? 0) * ROTATION_RANGE;
    if (groupRef.current) {
      groupRef.current.rotation.y = idleSpin.current + scrollSpin;
      groupRef.current.rotation.x = 0.12;
    }
    if (cloudsRef.current) {
      cloudsRef.current.rotation.y += delta * 0.018;
    }
  });

  return (
    <group ref={groupRef}>
      <mesh>
        <sphereGeometry args={[2, 64, 64]} />
        <meshBasicMaterial map={dayMap} />
      </mesh>

      <mesh ref={cloudsRef}>
        <sphereGeometry args={[2.02, 48, 48]} />
        <meshBasicMaterial map={cloudsMap} alphaMap={cloudsMap} transparent opacity={0.4} depthWrite={false} />
      </mesh>

      <mesh scale={1.1}>
        <sphereGeometry args={[2, 48, 48]} />
        <shaderMaterial
          vertexShader={ATMOSPHERE_VERTEX}
          fragmentShader={ATMOSPHERE_FRAGMENT}
          uniforms={atmosphereUniforms}
          transparent
          blending={THREE.AdditiveBlending}
          side={THREE.BackSide}
          depthWrite={false}
        />
      </mesh>
    </group>
  );
}

function CameraRig({ progressRef }) {
  const { camera } = useThree();
  useFrame(() => {
    camera.position.z = BASE_CAMERA_Z - (progressRef.current ?? 0) * DOLLY_AMOUNT;
  });
  return null;
}

function Scene({ progressRef }) {
  return (
    <>
      <CameraRig progressRef={progressRef} />
      <Earth progressRef={progressRef} />
    </>
  );
}

export default function GlobeScene({ progressRef, active }) {
  return (
    <Canvas
      dpr={[1, 1.5]}
      frameloop={active ? "always" : "never"}
      camera={{ position: [0, 0, BASE_CAMERA_Z], fov: 45 }}
      gl={{ antialias: true, alpha: true, powerPreference: "low-power" }}
      style={{ background: "transparent" }}
    >
      <Scene progressRef={progressRef} />
    </Canvas>
  );
}
