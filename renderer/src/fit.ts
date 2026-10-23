// Tamanho da legenda para a palavra mais longa caber na área segura. Sem Remotion, para ser testável.
// 0,8 em por letra é a estimativa conservadora do OneWord; a margem lateral é a do SafeArea.
const SIDE_MARGIN = 80;

export const fitSize = (words: string[], base: number, frameWidth: number, emPerChar = 0.8): number => {
  const longest = Math.max(1, ...words.map((word) => word.length));
  const maxWidth = frameWidth - 2 * SIDE_MARGIN;
  return Math.min(base, Math.floor(maxWidth / (longest * emPerChar)));
};
