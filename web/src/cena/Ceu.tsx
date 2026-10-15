import { useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { Color, type DirectionalLight, type Fog, type HemisphereLight } from "three";
import { MODO_DEMO } from "../api";
import { direcaoNaCena, instanteUTC, posicaoSol } from "../geo";
import { useEstado } from "../store";
import type { Snapshot } from "../tipos";
import { ambiente, suave } from "./ambiente";

// Luz e céu pela hora REAL do Pi (gerado_em + fuso) e pela posição do Sol em
// Guarapuava: manhã, meio-dia, entardecer e noite acontecem de verdade.
// As carreiras usam material sem luz: os dados ficam legíveis à noite.

const CEU_DIA = new Color("#9fb4c6");
const CEU_POENTE = new Color("#c99a7e");
const CEU_NOITE = new Color("#0b0f15");
const SOL_ALTO = new Color("#fff6e6");
const SOL_BAIXO = new Color("#ffb070");
const cor = new Color();

export default function Ceu({ snap }: { snap: Snapshot }) {
  const luz = useEstado((e) => e.luz);
  const recebidoEm = useEstado((e) => e.recebidoEm);
  const sol = useRef<DirectionalLight>(null);
  const hemi = useRef<HemisphereLight>(null);
  const neblina = useRef<Fog>(null);
  const scene = useThree((s) => s.scene);
  const geo = snap.campo.geo;
  const base = useMemo(() => instanteUTC(snap.gerado_em, geo.fuso_horas), [snap.gerado_em, geo.fuso_horas]);

  useFrame(() => {
    // o relógio anda entre uma resposta e outra (no ?demo, foto parada)
    const decorrido = MODO_DEMO || recebidoEm === null ? 0 : performance.now() - recebidoEm;
    const { elevacao, azimute } = luz === "dia" ? { elevacao: 1.0, azimute: 0.9 } : posicaoSol(base + decorrido, geo.lat, geo.lon);
    const altura = Math.sin(elevacao);
    const dia = suave(-0.1, 0.18, altura); // 0 noite, 1 dia
    const poente = suave(0.25, 0.0, Math.abs(altura - 0.04)) * dia; // perto do horizonte
    ambiente.noite = 1 - dia;

    const [x, y, z] = direcaoNaCena(geo, Math.cos(elevacao) * Math.sin(azimute), Math.cos(elevacao) * Math.cos(azimute), altura);
    if (sol.current) {
      sol.current.position.set(x * 400, Math.max(y * 400, 30), z * 400);
      sol.current.intensity = 0.08 + 2.4 * dia;
      sol.current.color.lerpColors(SOL_BAIXO, SOL_ALTO, suave(0.05, 0.5, altura));
    }
    if (hemi.current) hemi.current.intensity = 0.5 + 2.3 * dia;

    cor.lerpColors(CEU_NOITE, CEU_DIA, dia).lerp(CEU_POENTE, poente * 0.6);
    if (scene.background instanceof Color) scene.background.copy(cor);
    else scene.background = cor.clone();
    neblina.current?.color.copy(cor);
  });

  return (
    <>
      <hemisphereLight ref={hemi} args={["#eef3f8", "#4d4a3f", 2.4]} />
      <directionalLight ref={sol} intensity={2} />
      <fog ref={neblina} attach="fog" args={["#9fb4c6", 700, 3200]} />
    </>
  );
}
