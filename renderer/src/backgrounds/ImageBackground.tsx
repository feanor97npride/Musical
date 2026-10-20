// Fundo com a imagem gerada por IA: zoom lento e uma sobreposição escura para a legenda ler bem.
import { AbsoluteFill, Img, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { zoomAt } from "../image";

export const ImageBackground: React.FC<{ file: string }> = ({ file }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Img
        src={staticFile(file)}
        style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoomAt(frame, durationInFrames)})` }}
      />
      <AbsoluteFill style={{ backgroundColor: "rgba(0, 0, 0, 0.4)" }} />
    </AbsoluteFill>
  );
};
