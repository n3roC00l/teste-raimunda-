import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { type BufferGeometry, Color, CylinderGeometry, Float32BufferAttribute, type InstancedMesh, Object3D, SphereGeometry } from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { useEstado } from "../store";
import type { Carreira, Plot, Snapshot } from "../tipos";
import { hashTexto, roverAnim, sorteador } from "./ambiente";

// Plântulas brotando nas carreiras perto do rover (plot atual, anterior e o
// selecionado). QUANTIDADE = a contagem corrigida de cada carreira; POSIÇÃO e
// tamanho são ilustrativos (não guardamos as caixas do YOLO). Os "buracos"
// (sementes que não emergiram) ficam espalhados ao longo da carreira.
// Na carreira em captura, só aparecem atrás do rover, e vão surgindo.

const ESCALA = 2.4; // plântula real tem ~7 cm: aumentada para ser vista
const BROTO_S = 0.35;

function geometriaPlantula(): BufferGeometry {
  const pintar = (g: BufferGeometry, cor: string) => {
    const c = new Color(cor);
    const n = g.getAttribute("position").count;
    g.setAttribute("color", new Float32BufferAttribute(Array.from({ length: n }, () => [c.r, c.g, c.b]).flat(), 3));
    g.deleteAttribute("uv");
    return g;
  };
  const caule = pintar(new CylinderGeometry(0.004, 0.006, 0.07, 4).translate(0, 0.035, 0).toNonIndexed(), "#6f8f4a");
  const folhaE = pintar(new SphereGeometry(0.02, 6, 4).scale(1.5, 0.35, 0.9).translate(-0.022, 0.072, 0).toNonIndexed(), "#86b35c");
  const folhaD = pintar(new SphereGeometry(0.02, 6, 4).scale(1.5, 0.35, 0.9).translate(0.022, 0.072, 0).toNonIndexed(), "#7aa652");
  return mergeGeometries([caule, folhaE, folhaD])!;
}

interface Vaga {
  chave: string;
  carreira: string;
  frac: number; // posição ao longo da carreira, no sentido do rover (0 a 1)
  x: number;
  z: number;
  giro: number;
}

function vagas(plot: Plot, k: Carreira, campo: Snapshot["campo"], sentido: number): Vaga[] {
  const n = k.plantulas ?? 0;
  if (n <= 0) return [];
  // vagas = sementes esperadas; sem planilha, uma por planta contada
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
  // emergiram exatamente n: as n vagas de menor sorteio (falhas espalhadas)
  const ordem = [...lista].sort((p, q) => p.sorteio - q.sorteio);
  const emergiu = new Set(ordem.slice(0, n));
  return lista.filter((v) => emergiu.has(v)).map(({ sorteio: _s, ...v }) => v);
}

export default function Plantulas({ snap }: { snap: Snapshot }) {
  const selecao = useEstado((e) => e.selecao);
  const ref = useRef<InstancedMesh>(null);
  const geometria = useMemo(geometriaPlantula, []);
  const auxiliar = useMemo(() => new Object3D(), []);
  const nascimentos = useRef(new Map<string, number>()); // vaga -> quando apareceu

  const pos = snap.rover.posicao;
  const capturando = snap.rover.capturando;
  const lista = useMemo(() => {
    const campo = snap.campo;
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
    const serpentina = snap.rover.movimento?.trajeto === "serpentina";
    return [...plots].flatMap((p) =>
      p.carreiras.flatMap((k) => vagas(p, k, campo, serpentina && k.linha % 2 === 0 ? -1 : 1)),
    );
  }, [snap, pos, selecao]);
  const capacidade = Math.max(64, Math.ceil(lista.length / 256) * 256);

  // esquece as vagas que saíram de cena (outro plot), para não crescer sem fim
  useEffect(() => {
    const validas = new Set(lista.map((v) => v.chave));
    for (const k of nascimentos.current.keys()) if (!validas.has(k)) nascimentos.current.delete(k);
  }, [lista]);

  useFrame(({ clock }) => {
    const m = ref.current;
    if (!m) return;
    const t = clock.elapsedTime;
    const nasc = nascimentos.current;
    let i = 0;
    for (const v of lista) {
      // na carreira em captura, só atrás do rover (o que a câmera já viu)
      const passou = !(capturando && v.carreira === roverAnim.carreira) || v.frac <= roverAnim.progresso;
      if (!passou) nasc.delete(v.chave);
      else if (!nasc.has(v.chave)) nasc.set(v.chave, t);
      const nasceu = nasc.get(v.chave);
      const k = nasceu === undefined ? 0 : Math.min(1, (t - nasceu) / BROTO_S);
      const escala = ESCALA * (k < 1 ? 1 + 1.7 * (k - 1) ** 3 + 0.7 * (k - 1) ** 2 : 1); // cresce com um leve "pulo"
      auxiliar.position.set(v.x, 0.09, v.z);
      auxiliar.rotation.set(0, v.giro, 0);
      auxiliar.scale.setScalar(Math.max(0, k === 0 ? 0 : escala));
      auxiliar.updateMatrix();
      m.setMatrixAt(i++, auxiliar.matrix);
    }
    for (; i < m.count; i++) {
      auxiliar.scale.setScalar(0);
      auxiliar.updateMatrix();
      m.setMatrixAt(i, auxiliar.matrix);
    }
    m.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh key={capacidade} ref={ref} args={[geometria, undefined, capacidade]} frustumCulled={false} raycast={() => null}>
      <meshLambertMaterial vertexColors />
    </instancedMesh>
  );
}
