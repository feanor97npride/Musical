// Raiz do Remotion: registra a composição LyricVideo, com duração vinda do clip ou do áudio.
import { CalculateMetadataFunction, Composition } from "remotion";
import { LyricVideo } from "./LyricVideo";
import { sizeFor } from "./size";
import type { LyricProps } from "./types";

const FPS = 30;

const calculateMetadata: CalculateMetadataFunction<LyricProps> = ({ props }) => ({
  ...sizeFor(props.format),
  durationInFrames: Math.ceil((props.clip ? props.clip.end - props.clip.start : props.song.audio.duration) * FPS),
});

// Props vazias para o Studio abrir sem arquivo; o render real recebe o props.json.
const placeholder: LyricProps = {
  song: { version: 1, language: "pt", audio: { file: "", duration: 1, bpm: 0 }, lines: [], theme: null },
  audioFile: "",
  style: { subtitle: "highlight", background: "solid" },
  clip: null,
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="LyricVideo"
    component={LyricVideo}
    durationInFrames={FPS}
    fps={FPS}
    width={1080}
    height={1920}
    defaultProps={placeholder}
    calculateMetadata={calculateMetadata}
  />
);
