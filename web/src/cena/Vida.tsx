import { type Ref, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { CanvasTexture, type Group, type Mesh, type MeshBasicMaterial } from "three";
import type { Campo } from "../tipos";
import { ambiente, sorteador } from "./ambiente";
import { DISTANCIA_LADRILHOS, useLonge } from "./lod";
import { useEntorno, useProjecao } from "./useEntorno";

// CENÁRIO DECORATIVO (não é dado): trânsito na PR-540 e nas vias do campus,
// sombras de nuvem e aves. Dá vida à cena como no vídeo, mas nada aqui é medido; a
// legenda diz isso. Nenhum objeto daqui é clicável.

type XZ = [number, number];
const semEvento = () => null;

interface Rota {
  pontos: XZ[];
  acumulado: number[]; // distância acumulada até cada ponto
  total: number;
}

function rota(pontos: XZ[]): Rota {
  const acumulado = [0];
  for (let i = 1; i < pontos.length; i++)
    acumulado.push(acumulado[i - 1] + Math.hypot(pontos[i][0] - pontos[i - 1][0], pontos[i][1] - pontos[i - 1][1]));
  return { pontos, acumulado, total: acumulado[acumulado.length - 1] };
}

/** Posição e direção a `s` metros do começo da rota. */
function naRota(r: Rota, s: number): [number, number, number] {
  let i = 1;
  while (i < r.acumulado.length - 1 && r.acumulado[i] < s) i++;
  const [x0, z0] = r.pontos[i - 1];
  const [x1, z1] = r.pontos[i];
  const L = r.acumulado[i] - r.acumulado[i - 1] || 1;
  const t = Math.min(1, Math.max(0, (s - r.acumulado[i - 1]) / L));
  return [x0 + (x1 - x0) * t, z0 + (z1 - z0) * t, Math.atan2(z1 - z0, x1 - x0)];
}

const CORES_CARRO = ["#d8d8d8", "#8c8f94", "#9c3b35", "#2f4f78", "#3c5a3c", "#c9b27a"];

function Veiculo({ caminhao, cor, farol }: { caminhao: boolean; cor: string; farol: Ref<MeshBasicMaterial> }) {
  return caminhao ? (
    <group>
      <mesh position={[3.4, 1.5, 0]}>
        <boxGeometry args={[2.0, 2.4, 2.3]} />
        <meshLambertMaterial color={cor} />
      </mesh>
      <mesh position={[-1.4, 1.9, 0]}>
        <boxGeometry args={[7.6, 2.8, 2.5]} />
        <meshLambertMaterial color="#cfcfcf" />
      </mesh>
      <mesh position={[4.42, 0.9, 0]}>
        <boxGeometry args={[0.06, 0.3, 1.9]} />
        <meshBasicMaterial ref={farol} color="#555" />
      </mesh>
    </group>
  ) : (
    <group>
      <mesh position={[0, 0.65, 0]}>
        <boxGeometry args={[4.2, 0.8, 1.8]} />
        <meshLambertMaterial color={cor} />
      </mesh>
      <mesh position={[-0.3, 1.3, 0]}>
        <boxGeometry args={[2.2, 0.62, 1.6]} />
        <meshLambertMaterial color={cor} />
      </mesh>
      <mesh position={[2.12, 0.7, 0]}>
        <boxGeometry args={[0.05, 0.22, 1.5]} />
        <meshBasicMaterial ref={farol} color="#555" />
      </mesh>
    </group>
  );
}

interface CarroDados {
  rota: Rota;
  velocidade: number;
  inicio: number;
  sentido: 1 | -1;
  faixa: number;
  caminhao: boolean;
  cor: string;
}

function Transito({ rotas }: { rotas: Rota[] }) {
  const carros = useMemo<CarroDados[]>(() => {
    const sorte = sorteador(540);
    const lista: CarroDados[] = [];
    rotas.forEach((r, ir) => {
      const n = Math.max(1, Math.min(6, Math.round(r.total / 160)));
      for (let k = 0; k < n; k++) {
        const rodovia = ir === 0;
        lista.push({
          rota: r,
          velocidade: rodovia ? 14 + sorte() * 8 : 5 + sorte() * 3,
          inicio: sorte() * r.total,
          sentido: k % 2 === 0 ? 1 : -1,
          faixa: rodovia ? 1.9 : 1.3,
          caminhao: rodovia && sorte() < 0.35,
          cor: CORES_CARRO[Math.floor(sorte() * CORES_CARRO.length)],
        });
      }
    });
    return lista;
  }, [rotas]);
  const grupos = useRef<(Group | null)[]>([]);
  const farois = useRef<(MeshBasicMaterial | null)[]>([]);

  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    carros.forEach((c, i) => {
      const g = grupos.current[i];
      if (!g) return;
      // vai e volta na rota (sem teletransporte no fim)
      const d = (c.inicio + t * c.velocidade) % (2 * c.rota.total);
      const ida = d < c.rota.total;
      const s = ida ? d : 2 * c.rota.total - d;
      const sentido = (ida ? 1 : -1) * c.sentido;
      const [x, z, ang] = naRota(c.rota, c.sentido > 0 ? s : c.rota.total - s);
      const dir = sentido > 0 ? ang : ang + Math.PI;
      // mão direita (Brasil): direita de quem anda = frente x cima = (-sen, cos)
      g.position.set(x - Math.sin(dir) * c.faixa, -0.12, z + Math.cos(dir) * c.faixa);
      g.rotation.y = -dir;
      farois.current[i]?.color.setRGB(0.33 + 0.67 * ambiente.noite, 0.33 + 0.64 * ambiente.noite, 0.33 + 0.5 * ambiente.noite);
    });
  });

  return (
    <>
      {carros.map((c, i) => (
        <group key={i} ref={(g) => void (grupos.current[i] = g)} raycast={semEvento}>
          <Veiculo caminhao={c.caminhao} cor={c.cor} farol={(m) => void (farois.current[i] = m)} />
        </group>
      ))}
    </>
  );
}

function SombrasDeNuvem({ centro }: { centro: XZ }) {
  // nuvem de verdade (3D) atrapalharia a vista de cima; a sombra passando no
  // chão dá a mesma sensação de céu vivo. Fica abaixo do solo do ensaio:
  // escurece o entorno, nunca os dados.
  const sombras = useMemo(() => {
    const sorte = sorteador(77);
    return Array.from({ length: 7 }, () => ({
      x: centro[0] - 700 + sorte() * 1400,
      z: centro[1] - 700 + sorte() * 1400,
      rx: 45 + sorte() * 70,
      rz: 30 + sorte() * 45,
      v: 3 + sorte() * 2.5,
      giro: sorte() * 3,
    }));
  }, [centro]);
  // borda suave (gradiente radial): sombra de nuvem não tem contorno
  const textura = useMemo(() => {
    const c = document.createElement("canvas");
    c.width = c.height = 64;
    const g = c.getContext("2d")!;
    const r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    r.addColorStop(0, "rgba(255,255,255,1)");
    r.addColorStop(0.4, "rgba(255,255,255,0.7)");
    r.addColorStop(0.75, "rgba(255,255,255,0.22)");
    r.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = r;
    g.fillRect(0, 0, 64, 64);
    return new CanvasTexture(c);
  }, []);
  const refs = useRef<(Mesh | null)[]>([]);
  const mats = useRef<(MeshBasicMaterial | null)[]>([]);
  useFrame(({ clock }) => {
    sombras.forEach((n, i) => {
      const m = refs.current[i];
      if (!m) return;
      const x = ((n.x - centro[0] + 700 + clock.elapsedTime * n.v) % 1400) - 700 + centro[0];
      m.position.set(x, -0.06, n.z + Math.sin(clock.elapsedTime * 0.02 + i) * 25);
      const mat = mats.current[i];
      if (mat) mat.opacity = 0.2 * (1 - ambiente.noite);
    });
  });
  return (
    <>
      {sombras.map((n, i) => (
        <mesh key={i} ref={(m) => void (refs.current[i] = m)} rotation={[-Math.PI / 2, 0, n.giro]} scale={[n.rx, n.rz, 1]} raycast={semEvento}>
          <planeGeometry args={[2, 2]} />
          <meshBasicMaterial ref={(m) => void (mats.current[i] = m)} color="#0e1a12" alphaMap={textura} transparent opacity={0.2} depthWrite={false} />
        </mesh>
      ))}
    </>
  );
}

function Aves({ centro }: { centro: XZ }) {
  // de longe, uma ave vira um pontinho preto que parece sujeira na tela
  const longe = useLonge(DISTANCIA_LADRILHOS);
  const aves = useMemo(() => {
    const sorte = sorteador(9);
    return Array.from({ length: 7 }, () => ({ fase: sorte() * 6.28, raio: 26 + sorte() * 18, altura: 16 + sorte() * 10, w: 0.16 + sorte() * 0.05 }));
  }, []);
  const corpos = useRef<(Group | null)[]>([]);
  const asas = useRef<(Mesh | null)[]>([]);
  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    aves.forEach((a, i) => {
      const g = corpos.current[i];
      if (!g) return;
      const ang = a.fase + t * a.w;
      g.position.set(centro[0] + Math.cos(ang) * a.raio, a.altura + Math.sin(t * 0.7 + a.fase) * 1.5, centro[1] + Math.sin(ang) * a.raio * 0.6);
      g.rotation.y = -(ang + Math.PI / 2);
      const bate = Math.sin(t * 9 + a.fase) * 0.6;
      const e = asas.current[i * 2];
      const d = asas.current[i * 2 + 1];
      if (e) e.rotation.x = bate;
      if (d) d.rotation.x = -bate;
    });
  });
  if (longe) return null;
  return (
    <>
      {aves.map((_, i) => (
        <group key={i} ref={(g) => void (corpos.current[i] = g)} raycast={semEvento}>
          <mesh>
            <boxGeometry args={[0.36, 0.1, 0.1]} />
            <meshLambertMaterial color="#232323" />
          </mesh>
          <mesh ref={(m) => void (asas.current[i * 2] = m)} position={[0, 0, 0.05]}>
            <boxGeometry args={[0.22, 0.02, 0.62]} />
            <meshLambertMaterial color="#2b2b2b" />
          </mesh>
          <mesh ref={(m) => void (asas.current[i * 2 + 1] = m)} position={[0, 0, -0.05]}>
            <boxGeometry args={[0.22, 0.02, 0.62]} />
            <meshLambertMaterial color="#2b2b2b" />
          </mesh>
        </group>
      ))}
    </>
  );
}

export default function Vida({ campo }: { campo: Campo }) {
  const dados = useEntorno();
  const proj = useProjecao(campo.geo);
  const centro = useMemo<XZ>(() => [campo.comprimento_m / 2, campo.largura_m / 2], [campo.comprimento_m, campo.largura_m]);
  const rotas = useMemo(() => {
    if (!dados) return [];
    const p = (pts: [number, number][]) => pts.map(([lat, lon]) => proj(lat, lon));
    const rodovia = dados.estradas.filter((e) => e.ref.includes("PR-540")).sort((a, b) => b.pontos.length - a.pontos.length)[0];
    const campus = dados.estradas
      .filter((e) => e.tipo === "unclassified")
      .map((e) => p(e.pontos))
      .filter((xz) => xz.some(([x, z]) => Math.hypot(x - centro[0], z - centro[1]) < 450))
      .slice(0, 2);
    return [...(rodovia ? [p(rodovia.pontos)] : []), ...campus].filter((xz) => xz.length > 1).map(rota);
  }, [dados, proj, centro]);

  return (
    <>
      <Transito rotas={rotas} />
      <SombrasDeNuvem centro={centro} />
      <Aves centro={centro} />
    </>
  );
}
