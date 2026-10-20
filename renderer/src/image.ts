// Zoom lento do fundo de imagem: de 1 no início a 1,08 no fim do vídeo. Só o frame, para o render ser determinístico.
export const zoomAt = (frame: number, durationInFrames: number): number => {
  const progress = Math.min(1, Math.max(0, frame / Math.max(1, durationInFrames)));
  return 1 + 0.08 * progress;
};
