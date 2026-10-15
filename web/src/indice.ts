import { useMemo } from "react";
import type { Carreira, Plot, Snapshot } from "./tipos";

// Índices de busca sobre o snapshot (só organizam; não calculam nada).

export interface Indice {
  plots: Map<string, Plot>;
  carreiras: Map<string, { plot: Plot; carreira: Carreira }>;
  /** Plots em alerta: críticos primeiro, depois na ordem da planilha. */
  emAlerta: Plot[];
}

const GRAVIDADE = { critico: 2, atencao: 1 } as const;

export function montarIndice(snap: Snapshot | null): Indice {
  const plots = new Map<string, Plot>();
  const carreiras = new Map<string, { plot: Plot; carreira: Carreira }>();
  for (const plot of snap?.campo.plots ?? []) {
    plots.set(plot.id, plot);
    for (const carreira of plot.carreiras) carreiras.set(carreira.id, { plot, carreira });
  }
  const emAlerta = [...plots.values()]
    .filter((p) => p.alerta)
    .sort((a, b) => GRAVIDADE[b.alerta!] - GRAVIDADE[a.alerta!] || a.ordem - b.ordem);
  return { plots, carreiras, emAlerta };
}

export const useIndice = (snap: Snapshot | null) => useMemo(() => montarIndice(snap), [snap]);
