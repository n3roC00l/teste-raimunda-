import { useEffect, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import type { MeshBasicMaterial } from "three";
import { COR } from "../cores";
import { useEstado } from "../store";
import type { Snapshot } from "../tipos";

// O rover na carreira em que o painel diz que ele está. A posição AO LONGO
// da carreira não é medida (sem odômetro/GPS): ele fica parado no começo
// dela, e a carreira inteira acende. Capturando, a faixa pulsa.

const ESCALA = 1.3; // é um símbolo: um pouco maior que o real, para achar de longe

function Modelo() {
  const corpo = <meshLambertMaterial color={COR.roverCorpo} />;
  const roda = <meshLambertMaterial color={COR.roverRoda} />;
  return (
    <group scale={ESCALA}>
      <mesh position={[0, 0.42, 0]}>
        <boxGeometry args={[1.0, 0.22, 0.62]} />
        {corpo}
      </mesh>
      <mesh position={[0, 0.535, 0]}>
        <boxGeometry args={[0.98, 0.03, 0.64]} />
        <meshBasicMaterial color={COR.acento} />
      </mesh>
      {/* case do display */}
      <mesh position={[-0.2, 0.66, 0]}>
        <boxGeometry args={[0.34, 0.2, 0.42]} />
        <meshLambertMaterial color="#2a2a2a" />
      </mesh>
      {[-0.36, 0.36].map((x) =>
        [-0.36, 0.36].map((z) => (
          <mesh key={`${x}${z}`} position={[x, 0.2, z]} rotation-x={Math.PI / 2}>
            <cylinderGeometry args={[0.2, 0.2, 0.11, 14]} />
            {roda}
          </mesh>
        )),
      )}
      {/* mastro e câmera apontada para a carreira */}
      <mesh position={[0.42, 0.95, 0]}>
        <boxGeometry args={[0.05, 0.85, 0.05]} />
        {corpo}
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
        <meshBasicMaterial color={COR.acento} />
      </mesh>
    </group>
  );
}

function FaixaAtiva({ comprimento, largura, capturando, inicio }: { comprimento: number; largura: number; capturando: boolean; inicio: number }) {
  const material = useRef<MeshBasicMaterial>(null);
  const invalidate = useThree((s) => s.invalidate);

  // pulso a ~12 quadros/s só enquanto captura: poupa bateria do tablet
  useEffect(() => {
    if (!capturando) return;
    const t = window.setInterval(() => invalidate(), 80);
    return () => window.clearInterval(t);
  }, [capturando, invalidate]);

  useFrame(({ clock }) => {
    if (material.current) material.current.opacity = capturando ? 0.32 + 0.22 * Math.sin(clock.elapsedTime * 3.2) : 0.28;
  });

  return (
    <mesh position={[comprimento / 2 - inicio, 0.2, 0]} rotation-x={-Math.PI / 2}>
      <planeGeometry args={[comprimento, largura]} />
      <meshBasicMaterial ref={material} color={COR.acento} transparent opacity={0.28} depthWrite={false} />
    </mesh>
  );
}

export default function Rover({ snap }: { snap: Snapshot }) {
  const selecionar = useEstado((e) => e.selecionar);
  const pos = snap.rover.posicao;
  if (!pos) return null;
  const campo = snap.campo;
  const plot = campo.plots.find((p) => p.x === pos.x && p.y === pos.y);
  if (!plot) return null;
  const carreira = plot.carreiras.find((c) => c.linha === pos.linha);
  const inicio = 0.8; // metros depois da cabeceira, só para não ficar na passagem
  const x = plot.origem_m[1] + inicio;
  const z = carreira ? carreira.centro_u_m : plot.origem_m[0] + campo.largura_plot_m / 2;

  return (
    <group
      position={[x, 0, z]}
      onClick={(e) => {
        e.stopPropagation();
        selecionar({ tipo: "rover" });
      }}
    >
      <Modelo />
      <FaixaAtiva comprimento={campo.comprimento_plot_m} largura={campo.espacamento_m * 0.7} capturando={snap.rover.capturando} inicio={inicio} />
    </group>
  );
}
