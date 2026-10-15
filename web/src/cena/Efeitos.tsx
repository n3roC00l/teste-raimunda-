import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import { type InstancedMesh, Object3D } from "three";
import { pct } from "../formato";
import type { Snapshot } from "../tipos";
import { roverAnim } from "./ambiente";

// Efeitos disparados por DADO NOVO (nada inventado):
// - "+N plantas" subindo do rover quando a contagem da carreira atual cresce;
// - resumo flutuante quando uma carreira fecha (plantas e emergência dela);
// - partículas subindo quando acontece um backup na nuvem (sync_ok).

interface Flutuante {
  id: number;
  x: number;
  z: number;
  texto: string;
  classe: string;
}

const DURACAO_MS = 2200;
let proximoId = 1;

function Particulas({ disparo }: { disparo: { x: number; z: number; t: number } | null }) {
  const ref = useRef<InstancedMesh>(null);
  const aux = useRef(new Object3D());
  const inicio = useRef<number | null>(null);
  useLayoutEffect(() => {
    // começa escondido (escala zero); cada disparo reinicia a animação
    const m = ref.current;
    if (!m) return;
    aux.current.scale.setScalar(0);
    aux.current.updateMatrix();
    for (let i = 0; i < m.count; i++) m.setMatrixAt(i, aux.current.matrix);
    m.instanceMatrix.needsUpdate = true;
  }, []);
  useEffect(() => {
    if (disparo) inicio.current = null; // começa no próximo quadro
  }, [disparo]);
  useFrame(({ clock }) => {
    const m = ref.current;
    if (!m || !disparo) return;
    inicio.current ??= clock.elapsedTime;
    const k = (clock.elapsedTime - inicio.current) / 2.6;
    const o = aux.current;
    for (let i = 0; i < m.count; i++) {
      const fase = (i / m.count) * Math.PI * 2;
      const subida = k * 38 + (i % 5) * 0.8;
      const raio = 0.6 + k * 4;
      o.position.set(disparo.x + Math.cos(fase + k * 6) * raio, 1.5 + subida, disparo.z + Math.sin(fase + k * 6) * raio);
      o.scale.setScalar(k < 1 ? 0.16 * (1 - k * 0.6) : 0);
      o.updateMatrix();
      m.setMatrixAt(i, o.matrix);
    }
    m.instanceMatrix.needsUpdate = true;
  });
  return (
    <instancedMesh ref={ref} args={[undefined, undefined, 28]} frustumCulled={false} raycast={() => null}>
      <icosahedronGeometry args={[1, 0]} />
      <meshBasicMaterial color="#cfe3ff" transparent opacity={0.85} />
    </instancedMesh>
  );
}

export default function Efeitos({ snap }: { snap: Snapshot }) {
  const [flutuantes, setFlutuantes] = useState<Flutuante[]>([]);
  const [backup, setBackup] = useState<{ x: number; z: number; t: number } | null>(null);
  const antes = useRef<Snapshot | null>(null);

  useEffect(() => {
    const anterior = antes.current;
    antes.current = snap;
    if (!anterior) return; // primeira resposta: nada é "novo"
    const novos: Flutuante[] = [];
    const mesmoLugar = anterior.rover.posicao?.parcela === snap.rover.posicao?.parcela;
    const ganho = (snap.kpis.plantulas_em_captura ?? 0) - (anterior.kpis.plantulas_em_captura ?? 0);
    if (mesmoLugar && ganho > 0 && roverAnim.visivel) {
      novos.push({ id: proximoId++, x: roverAnim.x, z: roverAnim.z, texto: `+${ganho} plantas`, classe: "efeito-ganho" });
    }
    // carreira fechou: resumo onde ela fica
    const fechou = anterior.rover.posicao?.parcela;
    if (fechou && !mesmoLugar) {
      for (const p of snap.campo.plots)
        for (const k of p.carreiras)
          if (k.id === fechou && k.estado === "analisada") {
            novos.push({
              id: proximoId++,
              x: p.origem_m[1] + snap.campo.comprimento_plot_m / 2,
              z: k.centro_u_m,
              texto: `${k.id} ✓ ${k.plantulas} plantas${k.emergencia !== null ? ` · ${pct(k.emergencia)}` : ""}`,
              classe: k.alerta ? `efeito-resumo ${k.alerta}` : "efeito-resumo",
            });
          }
    }
    if (snap.kpis.ultima_sync && snap.kpis.ultima_sync !== anterior.kpis.ultima_sync && roverAnim.visivel) {
      setBackup({ x: roverAnim.x, z: roverAnim.z, t: performance.now() });
      novos.push({ id: proximoId++, x: roverAnim.x, z: roverAnim.z, texto: "backup na nuvem", classe: "efeito-backup" });
    }
    if (novos.length) {
      setFlutuantes((f) => [...f.slice(-6), ...novos]);
      const ids = new Set(novos.map((n) => n.id));
      window.setTimeout(() => setFlutuantes((f) => f.filter((n) => !ids.has(n.id))), DURACAO_MS);
    }
  }, [snap]);

  return (
    <>
      {flutuantes.map((f) => (
        <Html key={f.id} position={[f.x, 2.4, f.z]} center zIndexRange={[25, 15]}>
          <div className={`efeito ${f.classe}`}>{f.texto}</div>
        </Html>
      ))}
      <Particulas disparo={backup} />
    </>
  );
}
