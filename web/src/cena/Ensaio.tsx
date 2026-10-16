import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html, Line } from "@react-three/drei";
import type { Group } from "three";
import { COR } from "../cores";
import type { Snapshot } from "../tipos";
import { roverAnim } from "./ambiente";
import { DISTANCIA_MARCADORES, useLonge } from "./lod";

// Onde está o ensaio, em qualquer zoom: um risco claro no chão em volta da
// área (como cal no campo) e, de longe (vista da FAPA), o nome do ensaio e um
// ponto no rover, que lá de cima teria poucos pixels.

const MARGEM = 2.5;

function MarcadorRover() {
  const grupo = useRef<Group>(null);
  useFrame(() => {
    const g = grupo.current;
    if (!g) return;
    g.visible = roverAnim.visivel;
    g.position.set(roverAnim.x, 4, roverAnim.z);
  });
  return (
    <group ref={grupo}>
      <Html center className="marcador-rover" zIndexRange={[6, 0]}>
        <i aria-hidden="true" />
        rover
      </Html>
    </group>
  );
}

export default function Ensaio({ snap }: { snap: Snapshot }) {
  const longe = useLonge(DISTANCIA_MARCADORES);
  const c = snap.campo;
  const contorno = useMemo<[number, number, number][]>(() => {
    const [x0, z0, x1, z1] = [-MARGEM, -MARGEM, c.comprimento_m + MARGEM, c.largura_m + MARGEM];
    return [[x0, 0.01, z0], [x1, 0.01, z0], [x1, 0.01, z1], [x0, 0.01, z1], [x0, 0.01, z0]];
  }, [c.comprimento_m, c.largura_m]);
  return (
    <>
      <Line
        points={contorno}
        color={COR.cerca}
        lineWidth={1.5}
        raycast={() => null}
      />
      {longe && (
        <>
          {/* alto o bastante para não cobrir o marcador do rover */}
          <Html position={[c.comprimento_m / 2, 28, c.largura_m / 2]} center className="rotulo-ensaio" zIndexRange={[7, 0]}>
            {snap.experimento} · {c.plots.length} plots
          </Html>
          {snap.rover.posicao && <MarcadorRover />}
        </>
      )}
    </>
  );
}
