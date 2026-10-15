// Estilo base da legenda: cor de destaque, fonte do tema e sombra para ler sobre qualquer fundo.
import type { FontSpec } from "./types";

export const HIGHLIGHT = "#FFD60A";
export const SHADOW = "drop-shadow(0 4px 14px rgba(0, 0, 0, 0.7))";

export const textStyle = (font: FontSpec, size: number): React.CSSProperties => ({
  fontFamily: font.fontFamily,
  fontSize: size,
  fontWeight: font.fontWeight,
  lineHeight: 1.25,
  color: "#FFFFFF",
  textAlign: "center",
  width: "100%", // ocupa a área segura para a frase quebrar em linhas
  textShadow: "0 4px 14px rgba(0, 0, 0, 0.7)",
});
