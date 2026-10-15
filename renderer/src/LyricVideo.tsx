// Composição LyricVideo: fundo sólido, linha ativa no centro da área segura e palavra atual destacada.
import { AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { activeLine, activeWordIndex } from "./timing";
import type { LyricProps } from "./types";

const HIGHLIGHT = "#FFD60A";

export const LyricVideo: React.FC<LyricProps> = ({ song, audioFile, clip }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = (clip ? clip.start : 0) + frame / fps; // tempo da música, não do vídeo
  const line = activeLine(song.lines, t);
  const current = line ? activeWordIndex(line, t) : -1;
  const background = song.theme?.palette[0] ?? "#111111";

  return (
    <AbsoluteFill style={{ backgroundColor: background }}>
      {audioFile && (
        <Audio
          src={staticFile(audioFile)}
          trimBefore={clip ? Math.round(clip.start * fps) : undefined}
          durationInFrames={clip ? Math.round((clip.end - clip.start) * fps) : undefined}
        />
      )}
      {line && (
        <div
          style={{
            position: "absolute",
            top: "12%",
            bottom: "22%",
            left: 80,
            right: 80,
            display: "flex",
            flexWrap: "wrap",
            alignContent: "center",
            justifyContent: "center",
            textAlign: "center",
            fontFamily: "sans-serif",
            fontSize: 88,
            fontWeight: 700,
            lineHeight: 1.25,
          }}
        >
          {line.words.map((word, index) => (
            <span key={index} style={{ color: index === current ? HIGHLIGHT : "#FFFFFF", marginRight: 18 }}>
              {word.text}
            </span>
          ))}
        </div>
      )}
    </AbsoluteFill>
  );
};
