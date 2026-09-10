import { useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import dayMapUrl from "../assets/earth/earth_atmos_2048.jpg";
import normalMapUrl from "../assets/earth/earth_normal_2048.jpg";
import cloudsMapUrl from "../assets/earth/earth_clouds_1024.png";
import nightMapUrl from "../assets/earth/earth_lights_2048.png";

const CYAN = new THREE.Color("#4fd8c9");
const ORANGE = "#ff7a2f";
const SUN_DIRECTION = new THREE.Vector3(5, 2, 4).normalize();
const ROTATION_RANGE = Math.PI * 3.5;
const BASE_CAMERA_Z = 6.2;
const DOLLY_AMOUNT = 1.4;

const NIGHT_LIGHTS_VERTEX = `
  varying vec3 vWorldNormal;
  varying vec2 vUv;
  void main() {
    vUv = uv;
    vWorldNormal = normalize(mat3(modelMatrix) * normal);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;
const NIGHT_LIGHTS_FRAGMENT = `
  uniform sampler2D nightTexture;
  uniform vec3 sunDirection;
  varying vec3 vWorldNormal;
  varying vec2 vUv;
  void main() {
    float night = clamp(-dot(normalize(vWorldNormal), normalize(sunDirection)), 0.0, 1.0);
    vec3 lights = texture2D(nightTexture, vUv).rgb;
    float luma = (lights.r + lights.g + lights.b) / 3.0;
    gl_FragColor = vec4(lights, night * luma);
  }
`;

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
    float intensity = pow(0.65 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 3.0);
    gl_FragColor = vec4(glowColor, 1.0) * intensity;
  }
`;

function makePanelTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 64;
  canvas.height = 64;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#0a2540";
  ctx.fillRect(0, 0, 64, 64);
  ctx.strokeStyle = "#4fd8c9";
  ctx.lineWidth = 2;
  for (let i = 0; i <= 64; i += 16) {
    ctx.beginPath();
    ctx.moveTo(i, 0);
    ctx.lineTo(i, 64);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(0, i);
    ctx.lineTo(64, i);
    ctx.stroke();
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  return texture;
}

function Satellite({ radius, speed, tilt, offset, scale = 1, showOrbitRing, progressRef, scrollInfluence }) {
  const orbitRef = useRef(null);
  const busRef = useRef(null);
  const panelTexture = useMemo(() => makePanelTexture(), []);
  const angleRef = useRef(offset);

  useFrame((_, delta) => {
    angleRef.current += speed * delta + (progressRef.current ?? 0) * scrollInfluence * delta * 10;
    if (orbitRef.current) orbitRef.current.rotation.y = angleRef.current;
    if (busRef.current) busRef.current.rotation.y += delta * 0.8;
  });

  return (
    <group rotation={[tilt, 0, 0]}>
      {showOrbitRing && (
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[radius, 0.004, 8, 128]} />
          <meshBasicMaterial color={CYAN} transparent opacity={0.25} />
        </mesh>
      )}
      <group ref={orbitRef}>
        <group position={[radius, 0, 0]} scale={scale}>
          <group ref={busRef}>
            <mesh>
              <boxGeometry args={[0.14, 0.14, 0.2]} />
              <meshStandardMaterial color="#c7cede" metalness={0.6} roughness={0.4} />
            </mesh>
            <mesh position={[0, 0, 0.16]}>
              <coneGeometry args={[0.06, 0.1, 12]} />
              <meshStandardMaterial color="#e9edf6" metalness={0.3} roughness={0.5} />
            </mesh>
            <mesh position={[0.24, 0, 0]}>
              <boxGeometry args={[0.34, 0.02, 0.14]} />
              <meshStandardMaterial map={panelTexture} emissive={CYAN} emissiveIntensity={0.35} metalness={0.2} roughness={0.6} />
            </mesh>
            <mesh position={[-0.24, 0, 0]}>
              <boxGeometry args={[0.34, 0.02, 0.14]} />
              <meshStandardMaterial map={panelTexture} emissive={CYAN} emissiveIntensity={0.35} metalness={0.2} roughness={0.6} />
            </mesh>
          </group>
        </group>
      </group>
    </group>
  );
}

function ScanRing() {
  const ref = useRef(null);
  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.z += delta * 0.12;
  });
  return (
    <mesh ref={ref} rotation={[Math.PI / 2.3, 0, 0]}>
      <torusGeometry args={[2.3, 0.006, 8, 128]} />
      <meshBasicMaterial color={CYAN} transparent opacity={0.3} />
    </mesh>
  );
}

function Earth({ progressRef }) {
  const groupRef = useRef(null);
  const cloudsRef = useRef(null);
  const idleSpin = useRef(0);

  const [dayMap, normalMap, cloudsMap, nightMap] = useMemo(
    () => [
      new THREE.TextureLoader().load(dayMapUrl),
      new THREE.TextureLoader().load(normalMapUrl),
      new THREE.TextureLoader().load(cloudsMapUrl),
      new THREE.TextureLoader().load(nightMapUrl),
    ],
    [],
  );

  useMemo(() => {
    [dayMap, normalMap, cloudsMap, nightMap].forEach((t) => {
      t.colorSpace = THREE.SRGBColorSpace;
    });
  }, [dayMap, normalMap, cloudsMap, nightMap]);

  const nightUniforms = useMemo(
    () => ({
      nightTexture: { value: nightMap },
      sunDirection: { value: SUN_DIRECTION },
    }),
    [nightMap],
  );

  const atmosphereUniforms = useMemo(
    () => ({
      glowColor: { value: CYAN },
    }),
    [],
  );

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
        <meshPhongMaterial
          map={dayMap}
          specularMap={dayMap}
          normalMap={normalMap}
          normalScale={new THREE.Vector2(0.6, 0.6)}
          shininess={12}
        />
      </mesh>

      <mesh>
        <sphereGeometry args={[2.003, 64, 64]} />
        <shaderMaterial
          vertexShader={NIGHT_LIGHTS_VERTEX}
          fragmentShader={NIGHT_LIGHTS_FRAGMENT}
          uniforms={nightUniforms}
          transparent
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      <mesh ref={cloudsRef}>
        <sphereGeometry args={[2.02, 48, 48]} />
        <meshStandardMaterial
          map={cloudsMap}
          alphaMap={cloudsMap}
          transparent
          opacity={0.4}
          depthWrite={false}
        />
      </mesh>

      <mesh scale={1.12}>
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
  const sunPos = useMemo(() => SUN_DIRECTION.clone().multiplyScalar(6), []);
  return (
    <>
      <ambientLight intensity={0.22} />
      <directionalLight position={sunPos} intensity={2.1} color="#fff6e8" />
      <CameraRig progressRef={progressRef} />
      <Earth progressRef={progressRef} />
      <ScanRing />
      <Satellite radius={2.75} speed={0.32} tilt={0.42} offset={0} progressRef={progressRef} scrollInfluence={0.08} showOrbitRing />
      <Satellite radius={3.15} speed={-0.2} tilt={-0.28} offset={2.1} progressRef={progressRef} scrollInfluence={-0.05} />
      <Satellite radius={2.5} speed={0.46} tilt={0.95} offset={4.2} progressRef={progressRef} scrollInfluence={0.12} />
    </>
  );
}

export default function GlobeScene({ progressRef, active }) {
  return (
    <Canvas
      dpr={[1, 1.5]}
      frameloop={active ? "always" : "never"}
      camera={{ position: [0, 0, BASE_CAMERA_Z], fov: 45 }}
      gl={{ antialias: true, powerPreference: "low-power" }}
    >
      <Scene progressRef={progressRef} />
    </Canvas>
  );
}
