// Valores que mudam a cada quadro, sem passar pelo React (re-render a 60 fps
// seria caro). Quem escreve: Ceu (noite) e Rover (onde ele está). Quem lê:
// os outros componentes, dentro de useFrame.

export const ambiente = {
  /** 0 = dia pleno, 1 = noite fechada */
  noite: 0,
};

export const roverAnim = {
  /** posição na cena (coordenadas do campo) */
  x: 0,
  z: 0,
  /** fração já percorrida da carreira atual (0 a 1) */
  progresso: 0,
  /** id da carreira em que está (ex.: X3Y7L2), ou "" sem posição */
  carreira: "",
  visivel: false,
};

/** Número pseudoaleatório determinístico (mesma cena a cada recarga). */
export function sorteador(semente: number): () => number {
  let a = semente >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Hash de texto -> semente (para jitter estável por carreira). */
export function hashTexto(texto: string): number {
  let h = 2166136261;
  for (let i = 0; i < texto.length; i++) h = Math.imul(h ^ texto.charCodeAt(i), 16777619);
  return h >>> 0;
}

export const suave = (a: number, b: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};
