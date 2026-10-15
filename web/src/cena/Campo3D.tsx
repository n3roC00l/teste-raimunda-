import { useMemo } from "react";
import { COR, corCarreira, faixasEmergencia } from "../cores";
import { alturaCarreira, centroCarreira, centroPlot } from "../geometria";
import { useEstado } from "../store";
import type { Snapshot } from "../tipos";
import Instancias, { type Item } from "./Instancias";

// O ensaio em si: chão, a base de cada plot, as carreiras (cor = estado ou
// emergência; altura = tem dado / tem alerta) e os pinos de alerta (forma,
// para o alerta nunca depender só de cor).

function aoPassar(id: string | null) {
  if (useEstado.getState().hover !== id) useEstado.getState().setHover(id);
}

export default function Campo3D({ snap }: { snap: Snapshot }) {
  const campo = snap.campo;
  const modo = useEstado((e) => e.modoCor);
  const selecionar = useEstado((e) => e.selecionar);
  const faixas = useMemo(() => faixasEmergencia(snap.limiares), [snap.limiares]);

  const bases = useMemo<Item[]>(
    () =>
      campo.plots.map((p) => {
        const [x, z] = centroPlot(campo, p);
        return { id: p.id, pos: [x, 0.005, z], escala: [campo.comprimento_plot_m, 0.01, campo.largura_plot_m] };
      }),
    [campo],
  );

  const carreiras = useMemo<Item[]>(
    () =>
      campo.plots.flatMap((p) =>
        p.carreiras.map((k) => {
          const [x, z] = centroCarreira(campo, p, k);
          const h = alturaCarreira(k);
          return {
            id: k.id,
            pos: [x, 0.01 + h / 2, z],
            escala: [campo.comprimento_plot_m * 0.96, h, campo.espacamento_m * 0.42],
            cor: corCarreira(k, modo, faixas),
          };
        }),
      ),
    [campo, modo, faixas],
  );

  // pino: haste (cone de ponta para baixo) + cabeça. Crítico é mais alto.
  const emAlerta = useMemo(() => campo.plots.filter((p) => p.alerta), [campo]);
  const altura = (critico: boolean) => (critico ? 3.4 : 2.3);
  const hastes = useMemo<Item[]>(
    () =>
      emAlerta.map((p) => {
        const [x, z] = centroPlot(campo, p);
        const h = altura(p.alerta === "critico");
        return { id: p.id, pos: [x, h / 2 + 0.05, z], escala: [1, h, 1], rotX: Math.PI, cor: p.alerta === "critico" ? COR.critico : COR.atencao };
      }),
    [campo, emAlerta],
  );
  const cabecas = useMemo<Item[]>(
    () =>
      emAlerta.map((p) => {
        const [x, z] = centroPlot(campo, p);
        return { id: p.id, pos: [x, altura(p.alerta === "critico") + 0.05, z], escala: [1, 1, 1], cor: p.alerta === "critico" ? COR.critico : COR.atencao };
      }),
    [campo, emAlerta],
  );

  const margem = 4;
  const plot = (id: string) => selecionar({ tipo: "plot", id });
  return (
    <group>
      <mesh rotation-x={-Math.PI / 2} position={[campo.comprimento_m / 2, -0.02, campo.largura_m / 2]} raycast={() => null}>
        <planeGeometry args={[campo.comprimento_m + margem * 2, campo.largura_m + margem * 2]} />
        <meshLambertMaterial color={COR.chao} />
      </mesh>

      <Instancias itens={bases} aoClicar={plot} aoPassar={aoPassar}>
        <boxGeometry />
        <meshLambertMaterial color={COR.plot} />
      </Instancias>

      {/* cor exata dos tokens validados: material sem luz */}
      <Instancias itens={carreiras} aoClicar={(id) => selecionar({ tipo: "carreira", id })} aoPassar={aoPassar}>
        <boxGeometry />
        <meshBasicMaterial />
      </Instancias>

      <Instancias itens={hastes} aoClicar={plot} aoPassar={aoPassar}>
        <coneGeometry args={[0.18, 1, 10]} />
        <meshBasicMaterial />
      </Instancias>
      <Instancias itens={cabecas} aoClicar={plot} aoPassar={aoPassar}>
        <sphereGeometry args={[0.42, 16, 12]} />
        <meshBasicMaterial />
      </Instancias>
    </group>
  );
}
