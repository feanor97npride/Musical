// Aurora: três manchas de luz que se movem devagar. Só o frame define a posição, então o mesmo tempo gera o mesmo quadro.
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { lightFactor } from "../timing";

type Props = {
  palette: string[];
  intensity: number;
  pulse: number;
};

export const Aurora: React.FC<Props> = ({ palette, intensity, pulse }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const seconds = frame / fps;
  const blobs = [0, 1, 2].map((i) => {
    const x = 50 + 35 * Math.sin(seconds * 0.15 + i * 2.1);
    const y = 45 + 30 * Math.cos(seconds * 0.11 + i * 1.7);
    return `radial-gradient(circle at ${x}% ${y}%, ${palette[(i + 1) % palette.length]} 0%, transparent 55%)`;
  });
  return (
    <AbsoluteFill
      style={{ background: `${blobs.join(", ")}, ${palette[0]}`, filter: `brightness(${lightFactor(pulse, intensity)})` }}
    />
  );
};
