import { Canvas } from "@react-three/fiber";
import { COR } from "../cores";
import { deslocamento } from "../geometria";
import { useEstado } from "../store";
import Camera from "./Camera";
import Campo3D from "./Campo3D";
import Rotulos from "./Rotulos";
import Rover from "./Rover";

// frameloop "demand": só desenha quando algo muda (dado novo, câmera, pulso
// da captura). Parado, a tela não gasta bateria. `flat`: sem tone mapping,
// para as cores dos dados saírem iguais aos tokens validados.

export default function Cena() {
  const snap = useEstado((e) => e.snap);
  const selecionar = useEstado((e) => e.selecionar);
  if (!snap) return null;
  const [dx, dz] = deslocamento(snap.campo);
  return (
    <Canvas
      className="cena"
      frameloop="demand"
      flat
      dpr={[1, 2]}
      camera={{ fov: 35, near: 0.1, far: 5000, position: [0, 90, 110] }}
      onPointerMissed={() => selecionar(null)}
    >
      <color attach="background" args={[COR.fundo]} />
      <hemisphereLight args={["#f2f2ee", "#2a2a28", 2.2]} />
      <directionalLight position={[60, 120, 80]} intensity={1.6} />
      <group position={[dx, 0, dz]}>
        <Campo3D snap={snap} />
        <Rover snap={snap} />
        <Rotulos snap={snap} />
      </group>
      <Camera snap={snap} />
    </Canvas>
  );
}
