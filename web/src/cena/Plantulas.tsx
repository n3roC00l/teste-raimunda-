import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { type InstancedMesh, Object3D } from "three";
import { topoCarreira } from "../geometria";
import { useEstado } from "../store";
import type { Snapshot } from "../tipos";
import { roverAnim } from "./ambiente";
import { DISTANCIA_LADRILHOS, useLonge } from "./lod";
import { ESCALA_PLANTULA, plotsAnimados, recursosPlantula, sentidoCarreira, tempoPlantulas, vagas } from "./plantula";

// Plântulas que BROTAM: as do plot atual, do anterior e do selecionado, em
// qualquer modo de cor. Na carreira em captura, só aparecem atrás do rover
// (o que a câmera já viu), uma a uma, com um leve "pulo". O resto da lavoura
// (modo Lavoura) fica em Lavoura.tsx, nas MESMAS posições: quando o rover
// segue adiante, nada pula de lugar.

const BROTO_S = 0.35;

export default function Plantulas({ snap }: { snap: Snapshot }) {
  const selecao = useEstado((e) => e.selecao);
  const modo = useEstado((e) => e.modoCor);
  const longe = useLonge(DISTANCIA_LADRILHOS);
  const ref = useRef<InstancedMesh>(null);
  const { geometria, material } = recursosPlantula();
  const auxiliar = useMemo(() => new Object3D(), []);
  const nascimentos = useRef(new Map<string, number>()); // vaga -> quando apareceu

  const capturando = snap.rover.capturando;
  const lista = useMemo(
    () =>
      [...plotsAnimados(snap, selecao)].flatMap((p) =>
        p.carreiras.flatMap((k) => {
          const y = topoCarreira(k, modo);
          return vagas(p, k, snap.campo, sentidoCarreira(snap, k)).map((v) => ({ ...v, y }));
        }),
      ),
    [snap, selecao, modo],
  );
  const capacidade = Math.max(64, Math.ceil(lista.length / 256) * 256);

  // esquece as vagas que saíram de cena (outro plot), para não crescer sem fim
  useEffect(() => {
    const validas = new Set(lista.map((v) => v.chave));
    for (const k of nascimentos.current.keys()) if (!validas.has(k)) nascimentos.current.delete(k);
  }, [lista]);

  useFrame(({ clock }) => {
    const m = ref.current;
    tempoPlantulas.value = clock.elapsedTime;
    if (!m) return;
    const t = clock.elapsedTime;
    const nasc = nascimentos.current;
    let i = 0;
    for (const v of lista) {
      const passou = !(capturando && v.carreira === roverAnim.carreira) || v.frac <= roverAnim.progresso;
      if (!passou) nasc.delete(v.chave);
      else if (!nasc.has(v.chave)) nasc.set(v.chave, t);
      const nasceu = nasc.get(v.chave);
      const k = nasceu === undefined ? 0 : Math.min(1, (t - nasceu) / BROTO_S);
      const escala = ESCALA_PLANTULA * (k < 1 ? 1 + 1.7 * (k - 1) ** 3 + 0.7 * (k - 1) ** 2 : 1); // cresce com um leve "pulo"
      auxiliar.position.set(v.x, v.y, v.z);
      auxiliar.rotation.set(0, v.giro, 0);
      auxiliar.scale.setScalar(Math.max(0, k === 0 ? 0 : escala));
      auxiliar.updateMatrix();
      m.setMatrixAt(i++, auxiliar.matrix);
    }
    m.count = i;
    m.instanceMatrix.needsUpdate = true;
  });

  if (longe) return null; // de longe, uma planta tem menos de um pixel
  return <instancedMesh key={capacidade} ref={ref} args={[geometria, material, capacidade]} frustumCulled={false} raycast={() => null} />;
}
