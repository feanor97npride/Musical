// Fundo da composição: escolhe o desenho pelo valor de style.background.
import { AbsoluteFill } from "remotion";
import { lightFactor } from "../timing";
import type { LyricProps } from "../types";
import { Aurora } from "./Aurora";
import { AuroraGL } from "./AuroraGL";
import { Gradient } from "./Gradient";
import { ImageBackground } from "./ImageBackground";
import { Particles } from "./Particles";
import { Sunrise } from "./Sunrise";

type Props = {
  kind: LyricProps["style"]["background"];
  palette: string[];
  intensity: number;
  pulse: number;
  progress: number; // 0 no início do vídeo, 1 no fim; só o sol usa
  file?: string; // imagem enviada pelo usuário; só o fundo "image" usa
};

export const Background: React.FC<Props> = ({ kind, palette, intensity, pulse, progress, file }) => {
  switch (kind) {
    case "gradient":
      return (
        <>
          <Gradient palette={palette} intensity={intensity} pulse={pulse} />
          <Particles intensity={intensity} />
        </>
      );
    case "aurora":
      return <Aurora palette={palette} intensity={intensity} pulse={pulse} />;
    case "aurora-gl":
      return <AuroraGL palette={palette} intensity={intensity} pulse={pulse} />;
    case "sunrise":
      return <Sunrise palette={palette} intensity={intensity} pulse={pulse} progress={progress} />;
    case "image":
      if (!file) throw new Error("fundo de imagem sem backgroundFile");
      return <ImageBackground file={file} />;
    case "solid":
      return (
        <AbsoluteFill style={{ backgroundColor: palette[0], filter: `brightness(${lightFactor(pulse, intensity)})` }} />
      );
    default:
      // valor fora da lista falha o render, em vez de cair em sólido sem aviso
      throw new Error(`fundo desconhecido: ${String(kind)}`);
  }
};
