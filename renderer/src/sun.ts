// Altura do sol conforme o progresso do vídeo: 0 no horizonte, 1 no alto. Sem Remotion, para ser testável.
const smoothstep = (x: number): number => x * x * (3 - 2 * x); // começa e termina devagar, sem salto

export const sunHeight = (progress: number): number => smoothstep(Math.min(1, Math.max(0, progress)));
