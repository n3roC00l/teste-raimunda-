import { useEffect, useMemo, useState } from "react";
import { criarProjecao } from "../geo";
import type { Entorno, GeoCampo } from "../tipos";

// O entorno (public/entorno/fapa.json) é baixado uma vez e compartilhado
// entre quem desenha o cenário e quem anima o trânsito.

let promessa: Promise<Entorno | null> | null = null;

export function useEntorno(): Entorno | null {
  const [dados, setDados] = useState<Entorno | null>(null);
  useEffect(() => {
    promessa ??= fetch("entorno/fapa.json")
      .then((r) => (r.ok ? (r.json() as Promise<Entorno>) : null))
      .catch(() => null);
    let vivo = true;
    void promessa.then((d) => vivo && setDados(d));
    return () => {
      vivo = false;
    };
  }, []);
  return dados;
}

/** Projeção memorizada pelos VALORES do geo (o snapshot chega a cada 2 s com
 * objetos novos; memorizar pelo objeto refaria tudo a cada resposta). */
export function useProjecao(g: GeoCampo) {
  return useMemo(() => criarProjecao(g), [g.lat, g.lon, g.rumo_graus, g.espelhar]);
}
