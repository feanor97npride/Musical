// Partículas que sobem devagar. As posições vêm de uma semente fixa, então o render é sempre igual.
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";

const WIDTH = 1080;
const HEIGHT = 1920;
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
const PARTICLES = Array.from({ length: MAX }, () => ({
  x: random() * WIDTH,
  y: random() * HEIGHT,
  size: 4 + random() * 8,
  speed: 40 + random() * 60,
}));

export const Particles: React.FC<{ intensity: number }> = ({ intensity }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const seconds = frame / fps;
  return (
    <AbsoluteFill>
      {PARTICLES.map((p, i) => {
        const y = (((p.y - seconds * p.speed) % HEIGHT) + HEIGHT) % HEIGHT;
        // no refrão, as partículas extras entram por opacidade, sem aparecer de repente
        const opacity = i < BASE ? 0.35 + 0.35 * intensity : 0.7 * intensity;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: p.x,
              top: y,
              width: p.size,
              height: p.size,
              borderRadius: "50%",
              background: "#FFFFFF",
              opacity,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
