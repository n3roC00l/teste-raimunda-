import { useLayoutEffect, useRef, type ReactNode } from "react";
import { useThree, type ThreeEvent } from "@react-three/fiber";
import { Color, Object3D, type InstancedMesh } from "three";

// Uma malha instanciada genérica: uma chamada de desenho para centenas de
// plots/carreiras/pinos. `itens` diz posição, escala, cor e id de cada um;
// clique e ponteiro devolvem o id do item atingido.

export interface Item {
  id: string;
  pos: [number, number, number];
  escala: [number, number, number];
  cor?: string;
  rotX?: number;
}

interface Props {
  itens: Item[];
  children: ReactNode; // geometria + material
  aoClicar?: (id: string) => void;
  aoPassar?: (id: string | null) => void;
}

const auxiliar = new Object3D();
const cor = new Color();

export default function Instancias({ itens, children, aoClicar, aoPassar }: Props) {
  const ref = useRef<InstancedMesh>(null);
  const invalidate = useThree((s) => s.invalidate);

  useLayoutEffect(() => {
    const malha = ref.current;
    if (!malha) return;
    itens.forEach((it, i) => {
      auxiliar.position.set(...it.pos);
      auxiliar.scale.set(...it.escala);
      auxiliar.rotation.set(it.rotX ?? 0, 0, 0);
      auxiliar.updateMatrix();
      malha.setMatrixAt(i, auxiliar.matrix);
      if (it.cor) malha.setColorAt(i, cor.set(it.cor));
    });
    malha.instanceMatrix.needsUpdate = true;
    if (malha.instanceColor) malha.instanceColor.needsUpdate = true;
    malha.computeBoundingSphere(); // raycast certo depois de mover as instâncias
    invalidate();
  }, [itens, invalidate]);

  const idDo = (e: ThreeEvent<PointerEvent | MouseEvent>) =>
    e.instanceId === undefined ? null : (itens[e.instanceId]?.id ?? null);

  if (itens.length === 0) return null;
  return (
    <instancedMesh
      key={itens.length} // contagem mudou (outro experimento): recria a malha
      ref={ref}
      args={[undefined, undefined, itens.length]}
      onClick={(e) => {
        e.stopPropagation();
        const id = idDo(e);
        if (id && aoClicar) aoClicar(id);
      }}
      onPointerMove={(e) => {
        e.stopPropagation();
        aoPassar?.(idDo(e));
      }}
      onPointerOut={() => aoPassar?.(null)}
    >
      {children}
    </instancedMesh>
  );
}
