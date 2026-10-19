// Aurora em WebGL: as mesmas três manchas da Aurora em DOM, desenhadas por um shader de tela cheia.
// shortcut: o raio das manchas imita o radial-gradient do CSS (canto mais distante, 55%); conferir com PSNR se mudar a conta.
import { useLayoutEffect, useMemo, useRef } from "react";
import { ThreeCanvas } from "@remotion/three";
import * as THREE from "three";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { lightFactor } from "../timing";

const VERTEX = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position.xy, 0.0, 1.0);
  }
`;

// mesma ordem de empilhamento do CSS: a mancha 0 fica por cima, a 2 por baixo
const FRAGMENT = `
  uniform vec2 uResolution;
  uniform float uTime;
  uniform float uLight;
  uniform vec3 uBase;
  uniform vec3 uBlob[3];
  varying vec2 vUv;
  void main() {
    // pixels com a origem em cima, como no CSS (o UV do WebGL começa embaixo)
    vec2 p = vec2(vUv.x, 1.0 - vUv.y) * uResolution;
    vec3 color = uBase;
    for (int j = 0; j < 3; j++) {
      int i = 2 - j;
      float fi = float(i);
      vec2 c = vec2(0.5 + 0.35 * sin(uTime * 0.15 + fi * 2.1), 0.45 + 0.30 * cos(uTime * 0.11 + fi * 1.7)) * uResolution;
      // circle com farthest-corner: o transparente começa em 55% da distância até o canto mais longe
      float reach = 0.55 * length(max(c, uResolution - c));
      float a = clamp(1.0 - length(p - c) / reach, 0.0, 1.0);
      color = mix(color, uBlob[i], a);
    }
    gl_FragColor = vec4(color * uLight, 1.0);
  }
`;

// o validador aceita #RGB, #RGBA, #RRGGBB e #RRGGBBAA; o alfa fica de fora (a aurora usa cor opaca)
const hexToVec3 = (hex: string): THREE.Vector3 => {
  const digits = hex.slice(1);
  const full = digits.length <= 4 ? digits.split("").map((c) => c + c).join("") : digits;
  const channel = (offset: number) => parseInt(full.slice(offset, offset + 2), 16) / 255;
  return new THREE.Vector3(channel(0), channel(2), channel(4));
};

const Plane: React.FC<{ palette: string[]; light: number }> = ({ palette, light }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const material = useRef<THREE.ShaderMaterial>(null);
  const uniforms = useMemo(
    () => ({
      uResolution: { value: new THREE.Vector2(width, height) },
      uTime: { value: 0 },
      uLight: { value: 1 },
      uBase: { value: hexToVec3(palette[0]) },
      uBlob: { value: [1, 2, 3].map((i) => hexToVec3(palette[i % palette.length])) },
    }),
    [palette, width, height],
  );

  // o uniforme muda no commit do frame, antes de o ThreeCanvas avançar a cena; lê do material, não do objeto de criação
  useLayoutEffect(() => {
    const current = material.current?.uniforms;
    if (!current) return;
    current.uTime.value = frame / fps;
    current.uLight.value = light;
  }, [uniforms, frame, fps, light]);

  return (
    <mesh>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial ref={material} uniforms={uniforms} vertexShader={VERTEX} fragmentShader={FRAGMENT} />
    </mesh>
  );
};

export const AuroraGL: React.FC<{ palette: string[]; intensity: number; pulse: number }> = ({
  palette,
  intensity,
  pulse,
}) => {
  const { width, height } = useVideoConfig();
  return (
    <AbsoluteFill>
      <ThreeCanvas width={width} height={height}>
        <Plane palette={palette} light={lightFactor(pulse, intensity)} />
      </ThreeCanvas>
    </AbsoluteFill>
  );
};
