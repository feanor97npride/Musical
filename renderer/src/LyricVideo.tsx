// Composição LyricVideo: fundo sólido ou gradiente com partículas, e a legenda no estilo escolhido.
import { AbsoluteFill, Audio, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Background } from "./backgrounds/Background";
import { fontFor } from "./fonts";
import { Highlight } from "./subtitles/Highlight";
import { Karaoke } from "./subtitles/Karaoke";
import { Motion } from "./subtitles/Motion";
import { OneWord } from "./subtitles/OneWord";
import { activeLine, activeWordIndex, beatPulse, chorusWeight } from "./timing";
import type { LyricProps } from "./types";

const SUBTITLES = { highlight: Highlight, oneword: OneWord, karaoke: Karaoke };
const DEFAULT_PALETTE = ["#111111", "#1B1B3A", "#3A1F4A"];

export const LyricVideo: React.FC<LyricProps> = ({ song, audioFile, style, backgroundFile, clip }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = (clip ? clip.start : 0) + frame / fps; // tempo da música, não do vídeo
  const progress = frame / durationInFrames; // do início ao fim do vídeo: o sol nasce no próprio vídeo, mesmo em corte
  const line = activeLine(song.lines, t);
  const current = line ? activeWordIndex(line, t) : -1;
  const intensity = chorusWeight(song.lines, t);
  const pulse = beatPulse(t, song.audio.bpm, song.audio.beats);
  const palette = song.theme?.palette ?? DEFAULT_PALETTE;
  const Subtitle = SUBTITLES[style.subtitle];

  return (
    <AbsoluteFill>
      <Background kind={style.background} palette={palette} intensity={intensity} pulse={pulse} progress={progress} file={backgroundFile} />
      {audioFile && (
        <Audio
          src={staticFile(audioFile)}
          trimBefore={clip ? Math.round(clip.start * fps) : undefined}
          durationInFrames={clip ? Math.round((clip.end - clip.start) * fps) : undefined}
        />
      )}
      <Motion line={line} t={t} intensity={intensity}>
        <Subtitle line={line} current={current} t={t} font={fontFor(song.theme?.font)} />
      </Motion>
    </AbsoluteFill>
  );
};
