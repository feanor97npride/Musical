// Fundo: duas camadas de degradê que giram devagar em sentidos opostos, halo que acende na batida e vinheta nas bordas.
// Só usa o frame do Remotion, então o mesmo tempo sempre gera o mesmo quadro.
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { lightFactor } from "../timing";

const stops = (colors: string[], shift: number) =>
  colors.map((color, i) => `${color} ${Math.round((i / Math.max(colors.length - 1, 1)) * 100 + shift)}%`).join(", ");

export const Gradient: React.FC<{ palette: string[]; intensity: number; pulse: number }> = ({ palette, intensity, pulse }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const seconds = frame / fps;
  const angle = (seconds * 5) % 360; // velocidade constante: mudar no refrão causaria salto
  const shift = Math.sin(seconds * 0.4) * 12; // desloca as cores para dar movimento
  const back = (-seconds * 3) % 360; // segunda camada: mais devagar e no sentido contrário
  const glow = Math.min(0.85, 0.3 + 6 * pulse + 0.3 * intensity); // o halo acende na batida e no refrão
  return (
    <AbsoluteFill style={{ filter: `brightness(${lightFactor(pulse, intensity)})` }}>
      <AbsoluteFill style={{ background: `linear-gradient(${angle}deg, ${stops(palette, shift)})` }} />
      <AbsoluteFill
        style={{
          background: `linear-gradient(${back}deg, ${stops([...palette].reverse(), -shift)})`,
          opacity: 0.4 + 0.2 * intensity,
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 50% 45%, ${palette[palette.length - 1]} 0%, transparent 60%)`,
          opacity: glow,
        }}
      />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, transparent 55%, rgba(0, 0, 0, 0.45) 100%)" }} />
    </AbsoluteFill>
  );
};
