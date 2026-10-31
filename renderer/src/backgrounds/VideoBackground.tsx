// Fundo com o vídeo enviado pelo usuário: já cortado no formato, sem som (a música vem do áudio), repetido até o fim da música.
import { AbsoluteFill, Loop, OffthreadVideo, staticFile, useVideoConfig } from "remotion";

export const VideoBackground: React.FC<{ file: string }> = ({ file }) => {
  const { durationInFrames } = useVideoConfig();
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Loop durationInFrames={durationInFrames}>
        <OffthreadVideo src={staticFile(file)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      </Loop>
    </AbsoluteFill>
  );
};
