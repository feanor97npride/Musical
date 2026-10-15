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
  audio: { file: string; duration: number; bpm: number };
  lines: Line[];
  theme: Theme | null;
};

export type Clip = { start: number; end: number };

export type LyricProps = {
  song: Song;
  audioFile: string;
  style: { subtitle: "highlight" | "oneword" | "karaoke"; background: "solid" | "gradient" };
  clip: Clip | null;
};
