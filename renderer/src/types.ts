// Tipos do song.json e do props.json, conforme docs/ARQUITETURA.md.
export type Section = "intro" | "verse" | "chorus" | "bridge" | "outro" | "other";

export type Word = { text: string; start: number; end: number };

export type Line = {
  id: number;
  text: string;
  section: Section;
  start: number;
  end: number;
  words: Word[];
};

export type Theme = {
  title: string;
  mood: string;
  keywords: string[];
  palette: string[];
  font: string;
  visual_concept: string;
};

export type Song = {
  version: number;
  language: string;
  audio: { file: string; duration: number; bpm: number; beats?: number[] };
  lines: Line[];
  theme: Theme | null;
};

export type Clip = { start: number; end: number };

export type LyricProps = {
  song: Song;
  audioFile: string;
  style: { subtitle: "highlight" | "oneword" | "karaoke"; background: "solid" | "gradient" | "aurora" | "aurora-gl" | "sunrise" | "image" };
  backgroundFile?: string; // caminho da imagem gerada por IA, dentro de public/ (só com background "image")
  clip: Clip | null;
};

// Fonte já carregada: família e peso que ela realmente tem.
export type FontSpec = { fontFamily: string; fontWeight: number };

// Dados que cada estilo de legenda recebe a cada frame.
export type SubtitleProps = { line: Line | null; current: number; t: number; font: FontSpec };
