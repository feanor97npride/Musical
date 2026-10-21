// Tamanho do vídeo por formato: 9:16 para Shorts e TikTok, 16:9 para o YouTube. Sem Remotion, para ser testável.
export const sizeFor = (format?: "vertical" | "horizontal"): { width: number; height: number } =>
  format === "horizontal" ? { width: 1920, height: 1080 } : { width: 1080, height: 1920 };
