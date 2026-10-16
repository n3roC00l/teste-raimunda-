import type { Carreira, Limiares } from "./tipos";
import type { ModoCor } from "./store";

// Mesmos tokens do painel Tkinter (ui/tema.py): neutro por padrão, roxo só
// para o que está acontecendo agora, âmbar/vermelho só para alerta
// (frente #6, ISA-101). Validado com o validate_palette do skill de dataviz
// contra o fundo #1a1a1a:
// - analisada #555 vs crítico/atenção: CVD ΔE >= 10,8 (protan/deutan);
// - rampa da emergência (6 passos): monotônica, ΔL >= 0,06, ponta escura 2,15:1;
// - o roxo da captura NÃO convive com a rampa (ΔE 2,2 deutan): no modo
//   emergência a carreira em captura fica neutra, com contorno pulsante.
// Alerta nunca é só cor: tem pino 3D na cena e texto no painel.
//
// Modo Lavoura (padrão): o ensaio é desenhado como lavoura. Solo preparado
// com camalhão; de perto, cada plântula contada aparece na carreira; de longe,
// cada carreira analisada vira um ladrilho na RAMPA_LAVOURA (oliva -> verde,
// como um mapa de vigor). Validada (--ordinal, contra o solo #45372a): um tom
// só (35°), L monotônica com passos >= 0,06, ponta escura 2,28:1 vs solo.
// Âmbar e vermelho se confundem com o meio da rampa para daltônicos (ΔE 2 a 5),
// por isso, neste modo, o alerta é FORMA: moldura em volta do plot (no
// carreador, sobre o solo, nunca encostada no ladrilho), bandeirinha na
// cabeceira da carreira e pino de longe.

export const COR = {
  fundo: "#1a1a1a",
  fundo2: "#212121",
  linha: "#2e2e2e",
  t1: "#e7e7e7",
  t2: "#9a9a9a",
  t3: "#626262",
  acento: "#a68cf5",
  ok: "#57c08a",
  atencao: "#d9a441",
  critico: "#d96a5b",
  // cena
  chao: "#29231d", // solo da área do ensaio
  plot: "#332b24",
  pendente: "#3d352d",
  analisada: "#555555",
  capturandoNeutra: "#3d3d3d",
  // lavoura: solo preparado (carreador mais claro que o plot, camalhão aceso pelo sol)
  soloCarreador: "#5b4b3b",
  soloPlot: "#45372a",
  camalhao: "#6a5541",
  semEsperado: "#8a8a80", // analisada, mas sem grãos na planilha: sem emergência
  estaca: "#e9e4d6",
  cerca: "#d8d2c4",
  roverCorpo: "#d4d4d4",
  roverRoda: "#1c1c1c",
} as const;

const RAMPA = ["#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"];
export const RAMPA_LAVOURA = ["#797035", "#89883a", "#95a143", "#9abb4f", "#9ed468", "#aae98b"];

export interface Faixa {
  min: number;
  max: number;
  cor: string;
  rotulo: string;
}

const pct = (v: number) => `${Math.round(v * 100)}%`;

/** Faixas da emergência. Os cortes de alerta vêm do snapshot (config.py),
 * para a legenda e o alerta nunca discordarem. */
export function faixasEmergencia(l: Limiares, rampa: string[] = RAMPA): Faixa[] {
  const cortes = [...new Set([l.emergencia_critico, l.emergencia_atencao, 0.8, 0.9, 1.0])]
    .filter((c) => c > 0)
    .sort((a, b) => a - b)
    .slice(0, rampa.length - 1);
  const passo = (rampa.length - 1) / cortes.length;
  const bordas = [0, ...cortes, Infinity];
  return bordas.slice(0, -1).map((min, i) => {
    const max = bordas[i + 1];
    const rotulo = i === 0 ? `abaixo de ${pct(max)}` : max === Infinity ? `${pct(min)} ou mais` : `${pct(min)} a ${pct(max)}`;
    return { min, max, cor: rampa[Math.round(i * passo)], rotulo };
  });
}

const faixaDe = (e: number, faixas: Faixa[]) => (faixas.find((f) => e >= f.min && e < f.max) ?? faixas[faixas.length - 1]).cor;

/** Cor da carreira nos modos Estado e Emergência (no Lavoura o camalhão é solo). */
export function corCarreira(c: Carreira, modo: ModoCor, faixas: Faixa[]): string {
  if (c.estado === "pendente") return COR.pendente;
  if (c.estado === "capturando") return modo === "estado" ? COR.acento : COR.capturandoNeutra;
  if (modo === "estado") {
    if (c.alerta === "critico") return COR.critico;
    if (c.alerta === "atencao") return COR.atencao;
    return COR.analisada;
  }
  if (c.emergencia === null) return COR.analisada; // sem grãos na planilha
  return faixaDe(c.emergencia, faixas);
}

/** Ladrilho de longe no modo Lavoura: só carreira analisada tem (o resto é solo). */
export function corLadrilho(c: Carreira, faixas: Faixa[]): string | null {
  if (c.estado !== "analisada") return null;
  if (c.emergencia === null) return COR.semEsperado;
  return faixaDe(c.emergencia, faixas);
}

export const corAlerta = (a: Carreira["alerta"]) => (a === "critico" ? COR.critico : a === "atencao" ? COR.atencao : COR.t2);
