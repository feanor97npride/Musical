// Partículas que sobem devagar e tremulam. As posições vêm de uma semente fixa, então o render é sempre igual.
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";

const BASE = 40; // partículas sempre visíveis; as outras 40 aparecem no refrão
const MAX = 80;

// mulberry32: gerador pseudoaleatório com semente fixa.
const seeded = (seed: number) => () => {
  seed = (seed + 0x6d2b79f5) | 0;
  let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};

const random = seeded(42);
// posição em fração (0 a 1): a mesma partícula serve ao 9:16 e ao 16:9
const PARTICLES = Array.from({ length: MAX }, () => ({
  fx: random(),
  fy: random(),
  size: 4 + random() * 8,
  speed: 40 + random() * 60,
  phase: random() * Math.PI * 2, // cada partícula pisca em seu próprio tempo
}));

export const Particles: React.FC<{ intensity: number }> = ({ intensity }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const seconds = frame / fps;
  return (
    <AbsoluteFill>
      {PARTICLES.map((p, i) => {
        const y = (((p.fy * height - seconds * p.speed) % height) + height) % height;
        // no refrão, as partículas extras entram por opacidade, sem aparecer de repente
        const base = i < BASE ? 0.35 + 0.35 * intensity : 0.7 * intensity;
        const twinkle = 0.6 + 0.4 * Math.sin(seconds * 2 + p.phase);
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: p.fx * width,
              top: y,
              width: p.size,
              height: p.size,
              borderRadius: "50%",
              background: "#FFFFFF",
              opacity: base * twinkle,
              transform: `scale(${1 + 0.3 * intensity})`, // cresce no refrão sem mudar a posição
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
