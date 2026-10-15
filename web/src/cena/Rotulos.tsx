import { useMemo, useState } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { EdgesGeometry, BoxGeometry } from "three";
import { Html } from "@react-three/drei";
import { COR } from "../cores";
import { pct, numero } from "../formato";
import { caixaCarreira, caixaPlot, type Caixa } from "../geometria";
import { useIndice } from "../indice";
import { useEstado } from "../store";
import type { Snapshot } from "../tipos";

// Rótulos dos eixos (X/Y da planilha), contorno da seleção e a dica do
// ponteiro. Tudo em DOM (Html): nada de fonte baixada da internet, que no
// campo não tem.

const arestas = new EdgesGeometry(new BoxGeometry(1, 1, 1));

function Contorno({ caixa, cor }: { caixa: Caixa; cor: string }) {
  const [cx, cy, cz, sx, sy, sz] = caixa;
  return (
    <lineSegments geometry={arestas} position={[cx, cy, cz]} scale={[sx, sy, sz]}>
      <lineBasicMaterial color={cor} />
    </lineSegments>
  );
}

// Rótulos ao longo do comprimento ficam a ~7 m um do outro: sempre visíveis.
// Os da largura ficam a ~1,5 m: só aparecem de perto, para não se embolarem.
const DISTANCIA_ROTULOS_LARGURA = 45;
const DISTANCIA_ROTULOS_COMPRIMENTO = 240;

function Eixos({ snap }: { snap: Snapshot }) {
  const campo = snap.campo;
  const controles = useThree((s) => s.controls) as unknown as { distance?: number } | null;
  const [perto, setPerto] = useState(false);
  const [medio, setMedio] = useState(true);
  useFrame(() => {
    const d = controles?.distance;
    if (d === undefined) return;
    const p = d < DISTANCIA_ROTULOS_LARGURA;
    const m = d < DISTANCIA_ROTULOS_COMPRIMENTO;
    if (p !== perto) setPerto(p);
    if (m !== medio) setMedio(m);
  });

  const [comprimento, largura] = useMemo(() => {
    // qual índice da planilha anda no comprimento (eixo X da cena) e na largura (eixo Z)
    const noComp = campo.eixos_trocados ? "x" : "y";
    const noLarg = campo.eixos_trocados ? "y" : "x";
    const comp = new Map<string, [number, number]>();
    const larg = new Map<string, [number, number]>();
    for (const p of campo.plots) {
      comp.set(`${noComp.toUpperCase()}${p[noComp]}`, [p.origem_m[1] + campo.comprimento_plot_m / 2, -1.6]);
      // os da largura se repetem nas passagens, a cada 3 plots, para estarem
      // à vista em qualquer trecho do campo
      if ((p[noComp] - 1) % 3 === 0) {
        const chave = `${noLarg.toUpperCase()}${p[noLarg]}@${p[noComp]}`;
        larg.set(chave, [p.origem_m[1] - campo.passagem_m / 2, p.origem_m[0] + campo.largura_plot_m / 2]);
      }
    }
    return [[...comp.entries()], [...larg.entries()]];
  }, [campo]);

  return (
    <>
      {[...(medio ? comprimento : []), ...(perto ? largura : [])].map(([chave, [x, z]]) => (
        <Html key={chave} position={[x, 0.05, z]} center className="rotulo-eixo" zIndexRange={[10, 0]}>
          {chave.split("@")[0]}
        </Html>
      ))}
    </>
  );
}

function Dica({ snap }: { snap: Snapshot }) {
  const hover = useEstado((e) => e.hover);
  const idx = useIndice(snap);
  if (!hover) return null;
  const k = idx.carreiras.get(hover);
  const p = k?.plot ?? idx.plots.get(hover);
  if (!p) return null;
  const caixa = k ? caixaCarreira(snap.campo, p, k.carreira) : caixaPlot(snap.campo, p);
  const alvo = k?.carreira ?? p;
  const estado = alvo.estado === "concluido" ? "concluído" : alvo.estado;
  return (
    <Html position={[caixa[0], 0.9, caixa[2]]} center className="dica" zIndexRange={[20, 10]}>
      <b>{alvo.id}</b> · {estado}
      {alvo.plantulas !== null && <> · {numero(alvo.plantulas)} plantas</>}
      {alvo.emergencia !== null && <> · {pct(alvo.emergencia)}</>}
      {alvo.alerta && <div className={`dica-alerta ${alvo.alerta}`}>{alvo.motivo}</div>}
    </Html>
  );
}

export default function Rotulos({ snap }: { snap: Snapshot }) {
  const selecao = useEstado((e) => e.selecao);
  const idx = useIndice(snap);
  let destaque: Caixa | null = null;
  if (selecao?.tipo === "plot") {
    const p = idx.plots.get(selecao.id);
    if (p) destaque = caixaPlot(snap.campo, p);
  } else if (selecao?.tipo === "carreira") {
    const k = idx.carreiras.get(selecao.id);
    if (k) destaque = caixaCarreira(snap.campo, k.plot, k.carreira);
  }
  return (
    <>
      <Eixos snap={snap} />
      {destaque && <Contorno caixa={destaque} cor={COR.t1} />}
      <Dica snap={snap} />
    </>
  );
}
