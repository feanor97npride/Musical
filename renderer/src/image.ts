// Animação da imagem de fundo: zoom de 1 a 1,08 com deslocamento suave em círculo. Só o frame, para o render ser determinístico.
export type ImageTransform = { scale: number; x: number; y: number }; // x e y em % da tela

export const transformAt = (frame: number, durationInFrames: number): ImageTransform => {
  const p = Math.min(1, Math.max(0, frame / Math.max(1, durationInFrames)));
  return { scale: 1 + 0.08 * p, x: 2.5 * Math.sin(2 * Math.PI * p), y: 1.5 * Math.cos(2 * Math.PI * p) };
};
