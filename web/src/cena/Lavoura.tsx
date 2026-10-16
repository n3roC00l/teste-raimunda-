import { useLayoutEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import type { InstancedMesh } from "three";
import { corLadrilho, faixasEmergencia, RAMPA_LAVOURA } from "../cores";
import { CAMALHAO_M, centroCarreira, topoCarreira } from "../geometria";
import { useEstado } from "../store";
import type { Carreira, Plot, Snapshot } from "../tipos";
import Instancias, { type Item } from "./Instancias";
import { DISTANCIA_LADRILHOS, useLonge } from "./lod";
import { ESCALA_PLANTULA, plotsAnimados, recursosPlantula, sentidoCarreira, tempoPlantulas, vagas } from "./plantula";

// Modo Lavoura: o ensaio vai "verdejando" conforme o rover analisa.
// - De perto: toda carreira analisada mostra as plântulas contadas (a
//   quantidade é exata; as falhas são as sementes que não emergiram). As do
//   plot do rover e do selecionado brotam em Plantulas.tsx; aqui fica o resto,
//   parado, numa malha só, refeita apenas quando alguma carreira muda.
// - De longe: cada carreira analisada vira um ladrilho na rampa oliva -> verde
//   (emergência), largo como a carreira, para não virar listra.

function aoPassar(id: string | null) {
  if (useEstado.getState().hover !== id) useEstado.getState().setHover(id);
}

type Alvo = { plot: Plot; carreira: Carreira };

/** Um bloco (uma coluna de plots): a câmera descarta o que está fora do quadro. */
function Bloco({ matrizes }: { matrizes: Float32Array }) {
  const ref = useRef<InstancedMesh>(null);
  const { geometria, material } = recursosPlantula();
  const quantas = matrizes.length / 16;
  const capacidade = Math.max(256, Math.ceil(quantas / 1024) * 1024);
  useLayoutEffect(() => {
    const m = ref.current;
    if (!m) return;
    m.instanceMatrix.array.set(matrizes);
    m.count = quantas;
    m.instanceMatrix.needsUpdate = true;
    m.computeBoundingSphere(); // sem isto, o descarte usaria a esfera de uma plântula só
  }, [matrizes, quantas, capacidade]);
  return <instancedMesh key={capacidade} ref={ref} args={[geometria, material, capacidade]} raycast={() => null} />;
}

function matrizesDe(snap: Snapshot, alvos: Alvo[]): Float32Array {
  // giro em Y + escala uniforme + posição, escritos direto (sem Object3D)
  const dados: number[] = [];
  const s = ESCALA_PLANTULA;
  for (const { plot, carreira } of alvos) {
    const y = topoCarreira(carreira, "lavoura");
    for (const v of vagas(plot, carreira, snap.campo, sentidoCarreira(snap, carreira))) {
      const c = Math.cos(v.giro) * s;
      const n = Math.sin(v.giro) * s;
      dados.push(c, 0, -n, 0, 0, s, 0, 0, n, 0, c, 0, v.x, y, v.z, 1);
    }
  }
  return new Float32Array(dados);
}

const chaveDe = (alvos: Alvo[]) => alvos.map((a) => `${a.carreira.id}:${a.carreira.plantulas}:${a.carreira.esperado}`).join(",");

function PlantasParadas({ snap, alvos, chave }: { snap: Snapshot; alvos: Alvo[]; chave: string }) {
  // um bloco por coluna de plots; quando o rover troca de plot, só a coluna
  // que mudou é refeita (as outras reaproveitam as matrizes já enviadas)
  const cache = useRef(new Map<number, { chave: string; matrizes: Float32Array }>());
  const blocos = useMemo(() => {
    const porColuna = new Map<number, Alvo[]>();
    for (const a of alvos) {
      const lista = porColuna.get(a.plot.origem_m[1]) ?? [];
      porColuna.set(a.plot.origem_m[1], lista);
      lista.push(a);
    }
    const trajeto = snap.rover.movimento?.trajeto ?? "";
    const novo = new Map<number, { chave: string; matrizes: Float32Array }>();
    for (const [coluna, lista] of porColuna) {
      const ch = `${trajeto}|${chaveDe(lista)}`;
      const antes = cache.current.get(coluna);
      novo.set(coluna, antes && antes.chave === ch ? antes : { chave: ch, matrizes: matrizesDe(snap, lista) });
    }
    cache.current = novo;
    return [...novo.entries()].map(([coluna, b]) => ({ coluna, matrizes: b.matrizes }));
  }, [chave]);

  useFrame(({ clock }) => {
    tempoPlantulas.value = clock.elapsedTime;
  });

  return (
    <>
      {blocos.map((b) => (
        <Bloco key={b.coluna} matrizes={b.matrizes} />
      ))}
    </>
  );
}

export default function Lavoura({ snap }: { snap: Snapshot }) {
  const modo = useEstado((e) => e.modoCor);
  const selecao = useEstado((e) => e.selecao);
  const selecionar = useEstado((e) => e.selecionar);
  const longe = useLonge(DISTANCIA_LADRILHOS);
  const faixas = useMemo(() => faixasEmergencia(snap.limiares, RAMPA_LAVOURA), [snap.limiares]);
  const campo = snap.campo;

  // carreiras analisadas fora dos plots animados; a chave muda só quando
  // alguma delas muda (o snapshot chega a cada 2 s, quase sempre igual)
  const animados = plotsAnimados(snap, selecao);
  const alvos: Alvo[] = [];
  for (const plot of campo.plots)
    if (!animados.has(plot))
      for (const carreira of plot.carreiras) if (carreira.estado === "analisada") alvos.push({ plot, carreira });
  const chave = `${snap.rover.movimento?.trajeto}|${chaveDe(alvos)}`;

  const ladrilhos = useMemo<Item[]>(
    () =>
      campo.plots.flatMap((p) =>
        p.carreiras.flatMap((k) => {
          const cor = corLadrilho(k, faixas);
          if (!cor) return [];
          const [x, z] = centroCarreira(campo, p, k);
          return [{ id: k.id, pos: [x, CAMALHAO_M + 0.04, z], escala: [campo.comprimento_plot_m * 0.98, 0.02, campo.espacamento_m * 0.98], cor }];
        }),
      ),
    [campo, faixas],
  );

  if (modo !== "lavoura") return null;
  if (longe)
    return (
      <Instancias itens={ladrilhos} aoClicar={(id) => selecionar({ tipo: "carreira", id })} aoPassar={aoPassar}>
        <boxGeometry />
        {/* cor exata da rampa validada: material sem luz */}
        <meshBasicMaterial />
      </Instancias>
    );
  return <PlantasParadas snap={snap} alvos={alvos} chave={chave} />;
}
