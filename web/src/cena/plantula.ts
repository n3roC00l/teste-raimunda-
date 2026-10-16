import { BufferGeometry, Color, DoubleSide, Float32BufferAttribute, MeshLambertMaterial } from "three";
import type { Selecao } from "../store";
import type { Campo, Carreira, Plot, Snapshot } from "../tipos";
import { hashTexto, sorteador } from "./ambiente";

// A plântula da cena, compartilhada pela lavoura inteira (Lavoura.tsx) e pelas
// que brotam atrás do rover (Plantulas.tsx). Leve de propósito: o ensaio
// completo passa de 60 mil plantas, então são 6 triângulos cada, uma malha
// instanciada por coluna de plots e vento no shader (custo zero de CPU). QUANTIDADE = contagem corrigida de cada carreira;
// POSIÇÃO e tamanho são ilustrativos (não guardamos as caixas do YOLO).

export const ESCALA_PLANTULA = 2.4; // plântula real tem ~7 cm: aumentada para ser vista

function geometriaPlantula(): BufferGeometry {
  // indexada: 12 vértices e 6 triângulos (caule + duas folhas dobradas na
  // nervura). Com 60 mil plantas, vértice é o que pesa numa GPU integrada.
  const c = (hex: string) => new Color(hex);
  const [caule, base, lado, ponta] = [c("#6f8f4a"), c("#7aa652"), c("#86b35c"), c("#a3cf6d")];
  const h = 0.05;
  const w = 0.005;
  const vertices: [number[], Color][] = [
    [[-w, 0, 0], caule],
    [[w, 0, 0], caule],
    [[w, h, 0], caule],
    [[-w, h, 0], caule],
  ];
  const indices = [0, 1, 2, 0, 2, 3];
  for (const s of [-1, 1]) {
    const i = vertices.length;
    vertices.push([[s * 0.003, h, 0], base], [[s * 0.025, 0.065, 0.013], lado], [[s * 0.048, 0.074, 0], ponta], [[s * 0.025, 0.065, -0.013], lado]);
    indices.push(i, i + 1, i + 2, i, i + 2, i + 3);
  }
  const g = new BufferGeometry();
  g.setAttribute("position", new Float32BufferAttribute(vertices.flatMap(([v]) => v), 3));
  g.setAttribute("color", new Float32BufferAttribute(vertices.flatMap(([, k]) => [k.r, k.g, k.b]), 3));
  g.setIndex(indices);
  g.computeVertexNormals();
  return g;
}

/** Relógio do vento: quem desenha plântulas atualiza a cada quadro. */
export const tempoPlantulas = { value: 0 };

function materialPlantula(): MeshLambertMaterial {
  const m = new MeshLambertMaterial({ vertexColors: true, side: DoubleSide });
  m.onBeforeCompile = (shader) => {
    shader.uniforms.uTempo = tempoPlantulas;
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nuniform float uTempo;")
      .replace(
        "#include <begin_vertex>",
        `#include <begin_vertex>
        #ifdef USE_INSTANCING
          vec3 origemP = vec3(instanceMatrix[3][0], instanceMatrix[3][1], instanceMatrix[3][2]);
        #else
          vec3 origemP = vec3(0.0);
        #endif
        // rajadas que atravessam o ensaio no sentido das carreiras + tremor de cada planta
        float altP = clamp(position.y / 0.075, 0.0, 1.0);
        float rajada = 0.55 + 0.45 * sin(uTempo * 1.3 - origemP.x * 0.22 - origemP.z * 0.08);
        float faseP = origemP.x * 7.1 + origemP.z * 13.3;
        transformed.x += (sin(uTempo * 2.2 + faseP) * 0.5 + 0.8) * 0.006 * rajada * altP;
        transformed.z += cos(uTempo * 1.7 + faseP) * 0.003 * rajada * altP;`,
      );
  };
  return m;
}

let compartilhado: { geometria: BufferGeometry; material: MeshLambertMaterial } | null = null;
/** Geometria e material únicos para todas as plântulas (um shader compilado só). */
export function recursosPlantula() {
  compartilhado ??= { geometria: geometriaPlantula(), material: materialPlantula() };
  return compartilhado;
}

export interface Vaga {
  chave: string;
  carreira: string;
  frac: number; // posição ao longo da carreira, no sentido do rover (0 a 1)
  x: number;
  z: number;
  giro: number;
}

/** Sentido do rover na carreira (serpentina: carreiras pares voltam). */
export const sentidoCarreira = (snap: Snapshot, k: Carreira) =>
  snap.rover.movimento?.trajeto === "serpentina" && k.linha % 2 === 0 ? -1 : 1;

/**
 * Onde ficam as plantas de uma carreira: uma vaga por semente esperada
 * (sem planilha, uma por planta contada) e emergiram EXATAMENTE `plantulas`
 * delas, as de menor sorteio, para as falhas ficarem espalhadas. O sorteio é
 * fixo por carreira: a mesma planta fica no mesmo lugar em qualquer
 * componente, e quando a contagem cresce só aparecem plantas novas.
 */
export function vagas(plot: Plot, k: Carreira, campo: Campo, sentido: number): Vaga[] {
  const n = k.plantulas ?? 0;
  if (n <= 0) return [];
  const total = Math.max(n, Math.round(k.esperado ?? n));
  const sorte = sorteador(hashTexto(k.id));
  const a = plot.origem_m[1] + 0.15;
  const L = campo.comprimento_plot_m - 0.3;
  const lista = Array.from({ length: total }, (_, j) => {
    const frac = (j + 0.5 + (sorte() - 0.5) * 0.6) / total;
    return {
      chave: `${k.id}:${j}`,
      carreira: k.id,
      frac,
      x: a + (sentido > 0 ? frac : 1 - frac) * L,
      z: k.centro_u_m + (sorte() - 0.5) * 0.05,
      giro: sorte() * 6.28,
      sorteio: sorte(),
    };
  });
  const ordem = [...lista].sort((p, q) => p.sorteio - q.sorteio);
  const emergiu = new Set(ordem.slice(0, n));
  return lista.filter((v) => emergiu.has(v)).map(({ sorteio: _s, ...v }) => v);
}

/**
 * Plots cujas plântulas são animadas (brotam): o do rover, o anterior a ele
 * e o selecionado. O resto da lavoura é desenhado parado, de uma vez.
 */
export function plotsAnimados(snap: Snapshot, selecao: Selecao): Set<Plot> {
  const campo = snap.campo;
  const pos = snap.rover.posicao;
  const plots = new Set<Plot>();
  const atual = pos && campo.plots.find((p) => p.x === pos.x && p.y === pos.y);
  if (atual) {
    plots.add(atual);
    const anterior = campo.plots.find((p) => p.ordem === atual.ordem - 1);
    if (anterior) plots.add(anterior);
  }
  if (selecao?.tipo === "plot") {
    const p = campo.plots.find((q) => q.id === selecao.id);
    if (p) plots.add(p);
  }
  return plots;
}
