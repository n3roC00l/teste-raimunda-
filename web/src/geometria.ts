import type { Campo, Carreira, Plot } from "./tipos";

// Plano do campo (core/campo.py) -> cena 3D. v (ao longo das carreiras) vira
// o eixo X e u (transversal) vira o eixo Z: o lado comprido do ensaio fica
// na horizontal da tela. Os componentes da cena trabalham em coordenadas do
// campo dentro de um grupo deslocado; a câmera precisa do mundo (+ deslocamento).

/** [cx, cy, cz, sx, sy, sz]: centro e tamanho de uma caixa. */
export type Caixa = [number, number, number, number, number, number];

export const deslocamento = (c: Campo): [number, number] => [-c.comprimento_m / 2, -c.largura_m / 2];

export const centroPlot = (c: Campo, p: Plot): [number, number] => [
  p.origem_m[1] + c.comprimento_plot_m / 2,
  p.origem_m[0] + c.largura_plot_m / 2,
];

export const centroCarreira = (c: Campo, p: Plot, k: Carreira): [number, number] => [
  p.origem_m[1] + c.comprimento_plot_m / 2,
  k.centro_u_m,
];

/** Carreira com dado fica mais alta; com alerta, mais ainda (canal além da cor). */
export function alturaCarreira(k: Carreira): number {
  if (k.estado === "pendente") return 0.02;
  if (k.alerta) return 0.16;
  return 0.09;
}

export function caixaPlot(c: Campo, p: Plot): Caixa {
  const [x, z] = centroPlot(c, p);
  return [x, 0.15, z, c.comprimento_plot_m + 0.3, 0.3, c.largura_plot_m + 0.15];
}

export function caixaCarreira(c: Campo, p: Plot, k: Carreira): Caixa {
  const [x, z] = centroCarreira(c, p, k);
  return [x, 0.15, z, c.comprimento_plot_m + 0.1, 0.3, c.espacamento_m * 0.7];
}

export const caixaCampo = (c: Campo): Caixa => [c.comprimento_m / 2, 0, c.largura_m / 2, c.comprimento_m, 0.5, c.largura_m];

export function noMundo(c: Campo, [cx, cy, cz, sx, sy, sz]: Caixa): Caixa {
  const [dx, dz] = deslocamento(c);
  return [cx + dx, cy, cz + dz, sx, sy, sz];
}
