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
  chao: "#151515",
  plot: "#232323",
  pendente: "#2e2e2e",
  analisada: "#555555",
  capturandoNeutra: "#3d3d3d",
  roverCorpo: "#d4d4d4",
  roverRoda: "#1c1c1c",
} as const;

const RAMPA = ["#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"];

export interface Faixa {
  min: number;
  max: number;
  cor: string;
  rotulo: string;
}

const pct = (v: number) => `${Math.round(v * 100)}%`;

/** Faixas da emergência. Os cortes de alerta vêm do snapshot (config.py),
 * para a legenda e o alerta nunca discordarem. */
export function faixasEmergencia(l: Limiares): Faixa[] {
  const cortes = [...new Set([l.emergencia_critico, l.emergencia_atencao, 0.8, 0.9, 1.0])]
    .filter((c) => c > 0)
    .sort((a, b) => a - b)
    .slice(0, RAMPA.length - 1);
  const passo = (RAMPA.length - 1) / cortes.length;
  const bordas = [0, ...cortes, Infinity];
  return bordas.slice(0, -1).map((min, i) => {
    const max = bordas[i + 1];
    const rotulo = i === 0 ? `abaixo de ${pct(max)}` : max === Infinity ? `${pct(min)} ou mais` : `${pct(min)} a ${pct(max)}`;
    return { min, max, cor: RAMPA[Math.round(i * passo)], rotulo };
  });
}

export function corCarreira(c: Carreira, modo: ModoCor, faixas: Faixa[]): string {
  if (c.estado === "pendente") return COR.pendente;
  if (c.estado === "capturando") return modo === "estado" ? COR.acento : COR.capturandoNeutra;
  if (modo === "estado") {
    if (c.alerta === "critico") return COR.critico;
    if (c.alerta === "atencao") return COR.atencao;
    return COR.analisada;
  }
  if (c.emergencia === null) return COR.analisada; // sem grãos na planilha
  return (faixas.find((f) => c.emergencia! >= f.min && c.emergencia! < f.max) ?? faixas[faixas.length - 1]).cor;
}

export const corAlerta = (a: Carreira["alerta"]) => (a === "critico" ? COR.critico : a === "atencao" ? COR.atencao : COR.t2);
