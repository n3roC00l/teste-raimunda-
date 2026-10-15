import { useEffect, useRef } from "react";
import { CameraControls } from "@react-three/drei";
import CameraControlsImpl from "camera-controls";
import { MathUtils, type PerspectiveCamera } from "three";
import { caixaCampo, caixaCarreira, caixaPlot, centroPlot, noMundo, type Caixa } from "../geometria";
import { montarIndice } from "../indice";
import { useEstado } from "../store";
import type { Snapshot } from "../tipos";

// Câmera de mapa: arrastar com o botão esquerdo (ou um dedo) desloca, botão
// direito (ou dois dedos) gira, roda aproxima onde está o ponteiro. Clicar
// só seleciona; voar até algo é pedido explícito (botões, lista de alertas).
// Não deixa passar para baixo do chão.
//
// Chega um snapshot novo a cada 2 s; isso NUNCA mexe na câmera. Ela só se
// move por pedido do usuário ou quando muda o campo (outro experimento).
//
// O ensaio é comprido e estreito (ex.: 125 x 18 m): de longe vira uma tira.
// Por isso abre numa "vista de trabalho" em volta do rover, oblíqua como um
// jogo de estratégia; "ver o campo todo" usa um ângulo mais de cima.
// O enquadramento é calculado aqui (o fitToBox do camera-controls encaixa
// no eixo mais próximo e perderia a inclinação).

const POLAR_TRABALHO = 0.82; // ~47° do zênite
const POLAR_TUDO = 0.42; // ~24° do zênite
const POLAR_ENTORNO = 0.78; // ~45°: a FAPA em perspectiva
const MEIA_JANELA_M = 16; // vista de trabalho: 16 m para cada lado do rover
// faixa da tela coberta pelos cartões de cima e pela legenda de baixo
const COBERTO_TOPO = 0.17;
const COBERTO_BASE = 0.25;

/** Faixa do campo em volta do rover (largura inteira), ou null sem rover. */
function caixaTrabalho(s: Snapshot): Caixa | null {
  const pos = s.rover.posicao;
  const campo = s.campo;
  const p = pos && campo.plots.find((q) => q.x === pos.x && q.y === pos.y);
  if (!p) return null;
  const [x] = centroPlot(campo, p);
  const x0 = Math.max(0, x - MEIA_JANELA_M);
  const x1 = Math.min(campo.comprimento_m, x + MEIA_JANELA_M);
  return [(x0 + x1) / 2, 0, campo.largura_m / 2, x1 - x0, 0.5, campo.largura_m];
}

/** Põe a caixa (no mundo) na faixa livre da tela, com a inclinação pedida. */
function enquadrar(c: CameraControlsImpl, [cx, , cz, sx, , sz]: Caixa, polar: number, azimute: number, transicao: boolean) {
  const cam = c.camera as PerspectiveCamera;
  const vfov = MathUtils.degToRad(cam.fov);
  const hfov = 2 * Math.atan(Math.tan(vfov / 2) * cam.aspect);
  const util = 1 - COBERTO_TOPO - COBERTO_BASE;
  // extensão da caixa na horizontal e na profundidade da tela (azimute 0: câmera do lado +Z)
  const largura = Math.abs(sx * Math.cos(azimute)) + Math.abs(sz * Math.sin(azimute));
  const profundidade = Math.abs(sx * Math.sin(azimute)) + Math.abs(sz * Math.cos(azimute));
  const porLargura = largura / 2 / Math.tan(hfov / 2);
  const porAltura = (profundidade * Math.cos(polar)) / 2 / Math.tan((vfov * util) / 2);
  const d = MathUtils.clamp(1.08 * Math.max(porLargura, porAltura), c.minDistance, c.maxDistance);
  void c.setLookAt(
    cx + d * Math.sin(polar) * Math.sin(azimute),
    d * Math.cos(polar),
    cz + d * Math.sin(polar) * Math.cos(azimute),
    cx,
    0,
    cz,
    transicao,
  );
  // centraliza na faixa livre (entre os cartões e a legenda), não no meio da tela
  const visivel = 2 * d * Math.tan(vfov / 2);
  void c.setFocalOffset(0, -((COBERTO_BASE - COBERTO_TOPO) / 2) * visivel, 0, transicao);
}

export default function Camera({ snap }: { snap: Snapshot }) {
  const ref = useRef<CameraControlsImpl>(null);
  const ultimo = useRef(snap);
  ultimo.current = snap;
  const pedido = useEstado((e) => e.pedidoCamera);
  const campo = snap.campo;
  const chaveCampo = `${snap.experimento}|${campo.comprimento_m}|${campo.largura_m}|${campo.plots.length}`;

  // regras de controle e enquadramento inicial: só quando o campo muda
  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const s = ultimo.current;
    const A = CameraControlsImpl.ACTION;
    c.mouseButtons.left = A.TRUCK;
    c.mouseButtons.right = A.ROTATE;
    c.mouseButtons.middle = A.DOLLY;
    c.mouseButtons.wheel = A.DOLLY;
    c.touches.one = A.TOUCH_TRUCK;
    c.touches.two = A.TOUCH_DOLLY_ROTATE;
    c.touches.three = A.TOUCH_ROTATE;
    c.dollyToCursor = true;
    c.minDistance = 2.5;
    c.maxDistance = Math.max(1400, Math.max(s.campo.comprimento_m, s.campo.largura_m) * 2.6);
    c.maxPolarAngle = 1.3;
    c.smoothTime = 0.35;
    // ?vista=fapa | campo abre em outra vista (ex.: TV de apresentação)
    const vista = new URLSearchParams(location.search).get("vista");
    const trabalho = caixaTrabalho(s);
    if (vista === "fapa") {
      const [cx, , cz] = caixaCampo(s.campo);
      enquadrar(c, noMundo(s.campo, [cx, 0, cz, 560, 1, 560]), POLAR_ENTORNO, 0, false);
    } else if (trabalho && vista !== "campo") enquadrar(c, noMundo(s.campo, trabalho), POLAR_TRABALHO, 0, false);
    else enquadrar(c, noMundo(s.campo, caixaCampo(s.campo)), POLAR_TUDO, 0, false);
  }, [chaveCampo]);

  // atende "ver tudo", "ir ao rover" e "centralizar" (seleção com voar=true)
  useEffect(() => {
    const c = ref.current;
    if (!c || pedido.n === 0) return;
    const s = ultimo.current;
    const selecao = useEstado.getState().selecao;
    const idx = montarIndice(s);
    if (pedido.alvo === "tudo") {
      enquadrar(c, noMundo(s.campo, caixaCampo(s.campo)), POLAR_TUDO, 0, true);
    } else if (pedido.alvo === "entorno") {
      // o ensaio no meio da FAPA: ~560 m em volta
      const [cx, , cz] = caixaCampo(s.campo);
      enquadrar(c, noMundo(s.campo, [cx, 0, cz, 560, 1, 560]), POLAR_ENTORNO, 0, true);
    } else if (pedido.alvo === "rover") {
      const trabalho = caixaTrabalho(s);
      if (trabalho) enquadrar(c, noMundo(s.campo, trabalho), POLAR_TRABALHO, 0, true);
    } else if (selecao?.tipo === "plot") {
      const p = idx.plots.get(selecao.id);
      if (p) enquadrar(c, noMundo(s.campo, caixaPlot(s.campo, p)), c.polarAngle, c.azimuthAngle, true);
    } else if (selecao?.tipo === "carreira") {
      const k = idx.carreiras.get(selecao.id);
      if (k) enquadrar(c, noMundo(s.campo, caixaCarreira(s.campo, k.plot, k.carreira)), c.polarAngle, c.azimuthAngle, true);
    }
  }, [pedido]);

  return <CameraControls ref={ref} makeDefault />;
}
