// Fundo com a imagem enviada pelo usuário: zoom e deslocamento suave, com uma sobreposição escura para a legenda ler bem.
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { transformAt } from "../image";

export const ImageBackground: React.FC<{ file: string }> = ({ file }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const { scale, x, y } = transformAt(frame, durationInFrames);
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Img
        src={staticFile(file)}
        style={{ width: "100%", height: "100%", objectFit: "cover", transform: `translate(${x}%, ${y}%) scale(${scale})` }}
      />
      <AbsoluteFill style={{ backgroundColor: "rgba(0, 0, 0, 0.4)" }} />
    </AbsoluteFill>
  );
};
