import { useEffect, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import type { Group, Mesh, MeshBasicMaterial } from "three";
import { Color } from "three";
import { MODO_DEMO } from "../api";
import { COR } from "../cores";
import { useEstado } from "../store";
import type { Snapshot } from "../tipos";
import { ambiente, roverAnim } from "./ambiente";

// O rover anda na carreira em que o painel diz que ele está. A posição AO
// LONGO dela é ESTIMADA (não há odômetro): progresso = tempo desde o começo
// da carreira ÷ duração típica (core/campo.py), e entre uma resposta e outra
// ele continua no mesmo ritmo. Ao trocar de carreira, faz a manobra (meia-volta
// na cabeceira, em serpentina). O flash marca o ritmo real das fotos
// (config.INTERVALO_CAPTURA_S). O farol de status no mastro usa a cor do
// estado do analisador.

const ESCALA = 1.3; // símbolo um pouco maior que o real, para achar de longe
const RODA_R = 0.2 * ESCALA;
const VEL_MANOBRA = 1.3; // m/s na manobra (ilustrativo)
const MARGEM_CABECEIRA = 0.6;

type XZ = [number, number];
interface Manobra {
  p0: XZ;
  p1: XZ;
  p2: XZ;
  p3: XZ;
  t0: number;
  dur: number;
}

const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));
const suaveInOut = (t: number) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);

function bezier(m: Manobra, t: number): [number, number, number] {
  const u = 1 - t;
  const p = (i: 0 | 1) => u * u * u * m.p0[i] + 3 * u * u * t * m.p1[i] + 3 * u * t * t * m.p2[i] + t * t * t * m.p3[i];
  const d = (i: 0 | 1) => 3 * u * u * (m.p1[i] - m.p0[i]) + 6 * u * t * (m.p2[i] - m.p1[i]) + 3 * t * t * (m.p3[i] - m.p2[i]);
  return [p(0), p(1), Math.atan2(d(1), d(0))];
}

function giraPara(atual: number, alvo: number, fator: number): number {
  let d = alvo - atual;
  while (d > Math.PI) d -= 2 * Math.PI;
  while (d < -Math.PI) d += 2 * Math.PI;
  return atual + d * fator;
}

const COR_ESTADO: Record<string, string> = {
  analisando: COR.ok,
  pronto: COR.ok,
  carregando: COR.atencao,
  erro: COR.critico,
};
const corTmp = new Color();
const BRANCO = new Color("#ffffff");

export default function Rover({ snap }: { snap: Snapshot }) {
  const selecionar = useEstado((e) => e.selecionar);
  const recebidoEm = useEstado((e) => e.recebidoEm);
  const invalidate = useThree((s) => s.invalidate);
  const ultimo = useRef(snap);
  ultimo.current = snap;

  const grupo = useRef<Group>(null);
  const rodas = useRef<(Mesh | null)[]>([]);
  const lente = useRef<MeshBasicMaterial>(null);
  const pegada = useRef<MeshBasicMaterial>(null);
  const farois = useRef<MeshBasicMaterial>(null);
  const sinal = useRef<MeshBasicMaterial>(null);
  const facho = useRef<MeshBasicMaterial>(null);
  const e = useRef({ iniciado: false, x: 0, z: 0, rumo: 0, progresso: 0, carreira: "", manobra: null as Manobra | null, distancia: 0, flash: -10 });

  // sem animação (pausada), ainda redesenha quando chega dado novo
  useEffect(() => invalidate(), [snap, invalidate]);

  useFrame((state, dtBruto) => {
    const dt = Math.min(dtBruto, 0.1);
    const s = ultimo.current;
    const pos = s.rover.posicao;
    const g = grupo.current;
    const campo = s.campo;
    const plot = pos && campo.plots.find((p) => p.x === pos.x && p.y === pos.y);
    const carreira = plot && plot.carreiras.find((c) => c.linha === pos.linha);
    if (!g || !pos || !plot || !carreira) {
      if (g) g.visible = false;
      roverAnim.visivel = false;
      return;
    }
    const mov = s.rover.movimento;
    const sentido = mov?.sentido ?? 1;
    const a = plot.origem_m[1] + MARGEM_CABECEIRA;
    const b = plot.origem_m[1] + campo.comprimento_plot_m - MARGEM_CABECEIRA;
    const ini: XZ = [sentido > 0 ? a : b, carreira.centro_u_m];
    const fim: XZ = [sentido > 0 ? b : a, carreira.centro_u_m];
    const rumoCarreira = sentido > 0 ? 0 : Math.PI;
    const L = b - a;
    const t = state.clock.elapsedTime;
    const r = e.current;

    if (!r.iniciado) {
      Object.assign(r, { iniciado: true, x: ini[0], z: ini[1], rumo: rumoCarreira, carreira: pos.parcela, progresso: mov?.progresso_estimado ?? 0 });
    }
    if (r.carreira !== pos.parcela) {
      // manobra até o começo da nova carreira: meia-volta na cabeceira (serpentina)
      // ou curva em S para o plot seguinte; tangentes = direção de cada carreira
      const dist = Math.hypot(ini[0] - r.x, ini[1] - r.z);
      const alcance = Math.max(1.1, dist * 0.5);
      r.manobra = {
        p0: [r.x, r.z],
        p1: [r.x + Math.cos(r.rumo) * alcance, r.z + Math.sin(r.rumo) * alcance],
        p2: [ini[0] - Math.cos(rumoCarreira) * alcance, ini[1] - Math.sin(rumoCarreira) * alcance],
        p3: ini,
        t0: t,
        dur: clamp((dist + 2 * alcance) / VEL_MANOBRA, 1.5, 7),
      };
      r.carreira = pos.parcela;
      r.progresso = 0;
    }

    let vel = 0;
    if (r.manobra) {
      const m = r.manobra;
      const k = clamp((t - m.t0) / m.dur, 0, 1);
      const [x, z, ang] = bezier(m, suaveInOut(k));
      vel = Math.hypot(x - r.x, z - r.z) / Math.max(dt, 1e-3);
      Object.assign(r, { x, z, rumo: ang });
      if (k >= 1) r.manobra = null;
    } else {
      let alvo = r.progresso;
      if (s.rover.capturando && mov?.progresso_estimado != null) {
        const extra = MODO_DEMO || recebidoEm === null ? 0 : (performance.now() - recebidoEm) / 1000 / Math.max(mov.duracao_tipica_s, 1);
        alvo = clamp(mov.progresso_estimado + extra, 0, 1);
      }
      // anda no ritmo típico (pode alcançar a estimativa); recua devagar se ela voltar
      const ritmo = (L / Math.max(mov?.duracao_tipica_s ?? 20, 1)) * 2.2;
      const passo = clamp(alvo - r.progresso, (-ritmo * 0.3 * dt) / L, (ritmo * dt) / L);
      r.progresso = clamp(r.progresso + passo, 0, 1);
      r.x = ini[0] + (fim[0] - ini[0]) * r.progresso;
      r.z += (ini[1] - r.z) * (1 - Math.exp(-dt * 5));
      r.rumo = giraPara(r.rumo, rumoCarreira, 1 - Math.exp(-dt * 6));
      vel = (Math.abs(passo) * L) / Math.max(dt, 1e-3);
    }

    g.visible = true;
    g.position.set(r.x, 0, r.z);
    g.rotation.y = -r.rumo;
    r.distancia += vel * dt;
    for (const roda of rodas.current) if (roda) roda.rotation.y = -r.distancia / RODA_R;

    // flash a cada foto (ritmo real da captura) + pegada da foto no chão
    const intervalo = mov?.intervalo_captura_s ?? 0.9;
    if (s.rover.capturando && !r.manobra && t - r.flash >= intervalo) r.flash = t;
    const f = Math.max(0, 1 - (t - r.flash) / 0.28);
    lente.current?.color.copy(corTmp.set(COR.acento)).lerp(BRANCO, f);
    if (pegada.current) pegada.current.opacity = 0.5 * f;
    // faróis à noite; farol de status piscando enquanto analisa
    farois.current?.color.setRGB(0.3 + 0.7 * ambiente.noite, 0.3 + 0.67 * ambiente.noite, 0.3 + 0.5 * ambiente.noite);
    if (facho.current) facho.current.opacity = 0.22 * ambiente.noite;
    if (sinal.current) {
      const estado = s.rover.analisador_estado;
      sinal.current.color.set(COR_ESTADO[estado] ?? COR.t3);
      sinal.current.opacity = estado === "analisando" ? 0.45 + 0.55 * (Math.sin(t * 6) > 0 ? 1 : 0) : 1;
    }

    Object.assign(roverAnim, { x: r.x, z: r.z, progresso: r.progresso, carreira: pos.parcela, visivel: true });
  });

  const corpo = <meshLambertMaterial color={COR.roverCorpo} />;
  return (
    <group
      ref={grupo}
      visible={false}
      onClick={(ev) => {
        ev.stopPropagation();
        selecionar({ tipo: "rover" });
      }}
    >
      <group scale={ESCALA}>
        <mesh position={[0, 0.42, 0]}>
          <boxGeometry args={[1.0, 0.22, 0.62]} />
          {corpo}
        </mesh>
        <mesh position={[0, 0.535, 0]}>
          <boxGeometry args={[0.98, 0.03, 0.64]} />
          <meshBasicMaterial color={COR.acento} />
        </mesh>
        <mesh position={[-0.2, 0.66, 0]}>
          <boxGeometry args={[0.34, 0.2, 0.42]} />
          <meshLambertMaterial color="#2a2a2a" />
        </mesh>
        {[-0.36, 0.36].flatMap((x) =>
          [-0.36, 0.36].map((z, k) => (
            <mesh key={`${x}${z}`} ref={(m) => void (rodas.current[(x > 0 ? 2 : 0) + k] = m)} position={[x, 0.2, z]} rotation-x={Math.PI / 2}>
              <cylinderGeometry args={[0.2, 0.2, 0.11, 14]} />
              <meshLambertMaterial color={COR.roverRoda} />
              {/* calota: deixa a rotação visível */}
              <mesh position={[0, z > 0 ? 0.058 : -0.058, 0]}>
                <boxGeometry args={[0.24, 0.01, 0.05]} />
                <meshLambertMaterial color="#8a8a8a" />
              </mesh>
            </mesh>
          )),
        )}
        <mesh position={[0.51, 0.42, 0]}>
          <boxGeometry args={[0.03, 0.06, 0.46]} />
          <meshBasicMaterial ref={farois} color="#4d4d4d" />
        </mesh>
        <mesh position={[0.42, 0.95, 0]}>
          <boxGeometry args={[0.05, 0.85, 0.05]} />
          {corpo}
        </mesh>
        <mesh position={[0.42, 1.42, 0]}>
          <sphereGeometry args={[0.05, 10, 8]} />
          <meshBasicMaterial ref={sinal} color={COR.ok} transparent />
        </mesh>
        <mesh position={[0.56, 1.36, 0]}>
          <boxGeometry args={[0.32, 0.05, 0.05]} />
          {corpo}
        </mesh>
        <mesh position={[0.7, 1.3, 0]}>
          <boxGeometry args={[0.13, 0.1, 0.13]} />
          <meshLambertMaterial color="#141414" />
        </mesh>
        <mesh position={[0.7, 1.24, 0]}>
          <cylinderGeometry args={[0.035, 0.035, 0.03, 12]} />
          <meshBasicMaterial ref={lente} color={COR.acento} />
        </mesh>
      </group>
      {/* facho dos faróis no chão (só aparece à noite) */}
      <mesh position={[2.6, 0.11, 0]} rotation-x={-Math.PI / 2} raycast={() => null}>
        <circleGeometry args={[1.9, 24, -0.42, 0.84]} />
        <meshBasicMaterial ref={facho} color="#fff1c4" transparent opacity={0} depthWrite={false} />
      </mesh>
      {/* pegada da foto no chão, sob a câmera */}
      <mesh position={[0.7 * ESCALA, 0.12, 0]} rotation-x={-Math.PI / 2}>
        <planeGeometry args={[0.8, 0.5]} />
        <meshBasicMaterial ref={pegada} color="#ffffff" transparent opacity={0} depthWrite={false} />
      </mesh>
    </group>
  );
}

/** A carreira em que o rover está acende (fica parada na carreira, não anda com ele). */
export function CarreiraAtual({ snap }: { snap: Snapshot }) {
  const material = useRef<MeshBasicMaterial>(null);
  const pos = snap.rover.posicao;
  const capturando = snap.rover.capturando;
  useFrame(({ clock }) => {
    if (material.current) material.current.opacity = capturando ? 0.3 + 0.2 * Math.sin(clock.elapsedTime * 3.2) : 0.26;
  });
  const plot = pos && snap.campo.plots.find((p) => p.x === pos.x && p.y === pos.y);
  const carreira = plot && plot.carreiras.find((c) => c.linha === pos.linha);
  if (!plot || !carreira) return null;
  const c = snap.campo;
  return (
    <mesh position={[plot.origem_m[1] + c.comprimento_plot_m / 2, 0.21, carreira.centro_u_m]} rotation-x={-Math.PI / 2} raycast={() => null}>
      <planeGeometry args={[c.comprimento_plot_m, c.espacamento_m * 0.7]} />
      <meshBasicMaterial ref={material} color={COR.acento} transparent opacity={0.26} depthWrite={false} />
    </mesh>
  );
}
