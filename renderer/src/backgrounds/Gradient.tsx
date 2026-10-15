// Gradiente que gira devagar, com brilho que sobe no refrão. Só usa o frame do Remotion.
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { lightFactor } from "../timing";

export const Gradient: React.FC<{ palette: string[]; intensity: number; pulse: number }> = ({ palette, intensity, pulse }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const seconds = frame / fps;
  const angle = (seconds * 5) % 360; // velocidade constante: mudar no refrão causaria salto
  const shift = Math.sin(seconds * 0.4) * 12; // desloca as cores para dar movimento
  const stops = palette
    .map((color, i) => `${color} ${Math.round((i / Math.max(palette.length - 1, 1)) * 100 + shift)}%`)
    .join(", ");
  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(${angle}deg, ${stops})`,
        filter: `brightness(${lightFactor(pulse, intensity)})`,
      }}
    />
  );
};
