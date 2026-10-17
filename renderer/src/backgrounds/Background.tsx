// Fundo da composição: escolhe o desenho pelo valor de style.background.
import { AbsoluteFill } from "remotion";
import { lightFactor } from "../timing";
import type { LyricProps } from "../types";
import { Gradient } from "./Gradient";
import { Particles } from "./Particles";

type Props = {
  kind: LyricProps["style"]["background"];
  palette: string[];
  intensity: number;
  pulse: number;
};

export const Background: React.FC<Props> = ({ kind, palette, intensity, pulse }) => {
  switch (kind) {
    case "gradient":
      return (
        <>
          <Gradient palette={palette} intensity={intensity} pulse={pulse} />
          <Particles intensity={intensity} />
        </>
      );
    case "solid":
      return (
        <AbsoluteFill style={{ backgroundColor: palette[0], filter: `brightness(${lightFactor(pulse, intensity)})` }} />
      );
    default:
      // valor fora da lista falha o render, em vez de cair em sólido sem aviso
      throw new Error(`fundo desconhecido: ${String(kind)}`);
  }
};
