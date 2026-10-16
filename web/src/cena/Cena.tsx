import { Canvas } from "@react-three/fiber";
import { deslocamento } from "../geometria";
import { useEstado } from "../store";
import Camera from "./Camera";
import Campo3D from "./Campo3D";
import Ceu from "./Ceu";
import Efeitos from "./Efeitos";
import Ensaio from "./Ensaio";
import Entorno from "./Entorno";
import Lavoura from "./Lavoura";
import Plantulas from "./Plantulas";
import Rotulos from "./Rotulos";
import Rover, { CarreiraAtual } from "./Rover";
import Vida from "./Vida";

// A cena roda o tempo todo ("always"): rover andando, cenário vivo, sol
// andando. Com a animação pausada (botão, ou o sistema pedindo menos
// movimento), volta ao "demand": só redesenha quando chega dado novo.
// `flat`: sem tone mapping, para as cores dos dados saírem iguais aos tokens.
// Profundidade logarítmica: o entorno vai a ~1,5 km sem "briga" entre camadas.

export default function Cena() {
  const snap = useEstado((e) => e.snap);
  const animacao = useEstado((e) => e.animacao);
  const selecionar = useEstado((e) => e.selecionar);
  if (!snap) return null;
  const [dx, dz] = deslocamento(snap.campo);
  return (
    <Canvas
      className="cena"
      frameloop={animacao ? "always" : "demand"}
      flat
      dpr={[1, 2]}
      gl={{ logarithmicDepthBuffer: true, antialias: true }}
      camera={{ fov: 35, near: 0.5, far: 6000, position: [0, 90, 110] }}
      onPointerMissed={() => selecionar(null)}
    >
      <Ceu snap={snap} />
      <group position={[dx, 0, dz]}>
        <Entorno campo={snap.campo} />
        <Campo3D snap={snap} />
        <Lavoura snap={snap} />
        <Ensaio snap={snap} />
        <CarreiraAtual snap={snap} />
        <Plantulas snap={snap} />
        <Rover snap={snap} />
        <Vida campo={snap.campo} />
        <Efeitos snap={snap} />
        <Rotulos snap={snap} />
      </group>
      <Camera snap={snap} />
    </Canvas>
  );
}
