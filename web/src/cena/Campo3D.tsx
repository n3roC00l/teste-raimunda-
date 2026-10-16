import { useMemo } from "react";
import { Line } from "@react-three/drei";
import { Color } from "three";
import { COR, corCarreira, faixasEmergencia } from "../cores";
import { alturaCarreira, centroCarreira, centroPlot, VAO_PLOTS_M } from "../geometria";
import { useEstado } from "../store";
import type { Snapshot } from "../tipos";
import Instancias, { type Item } from "./Instancias";
import { DISTANCIA_LADRILHOS, useLonge } from "./lod";

// O ensaio em si: solo, a base de cada plot, as carreiras e os sinais de alerta.
// - Lavoura (padrão): solo preparado e camalhão igual para toda carreira; o
//   dado são as plantas e os ladrilhos (Lavoura.tsx).
// - Estado / Emergência: a carreira é uma barra colorida (cor = estado ou
//   emergência; altura = tem dado / tem alerta).
// Alerta nunca depende só de cor: moldura em volta do plot (todos os modos),
// bandeirinha na cabeceira da carreira (de perto) e pino (de longe).
// Uma estaca por plot, na cabeceira, como no campo: separa os plots e,
// clicada, seleciona o plot.

function aoPassar(id: string | null) {
  if (useEstado.getState().hover !== id) useEstado.getState().setHover(id);
}

const corAlerta = (critico: boolean) => (critico ? COR.critico : COR.atencao);

export default function Campo3D({ snap }: { snap: Snapshot }) {
  const campo = snap.campo;
  const modo = useEstado((e) => e.modoCor);
  const selecionar = useEstado((e) => e.selecionar);
  const longe = useLonge(DISTANCIA_LADRILHOS);
  const faixas = useMemo(() => faixasEmergencia(snap.limiares), [snap.limiares]);
  const lavoura = modo === "lavoura";

  const bases = useMemo<Item[]>(
    () =>
      campo.plots.map((p) => {
        const [x, z] = centroPlot(campo, p);
        return { id: p.id, pos: [x, 0.005, z], escala: [campo.comprimento_plot_m, 0.01, campo.largura_plot_m - VAO_PLOTS_M] };
      }),
    [campo],
  );

  const carreiras = useMemo<Item[]>(
    () =>
      campo.plots.flatMap((p) =>
        p.carreiras.map((k) => {
          const [x, z] = centroCarreira(campo, p, k);
          const h = alturaCarreira(k, modo);
          // de longe a barra ocupa a carreira toda: 0,5 m de vão viraria listra
          const largura = lavoura ? 0.22 : campo.espacamento_m * (longe ? 0.98 : 0.42);
          return {
            id: k.id,
            pos: [x, 0.01 + h / 2, z],
            escala: [campo.comprimento_plot_m * (lavoura ? 0.97 : 0.96), h, largura],
            cor: lavoura ? undefined : corCarreira(k, modo, faixas),
          };
        }),
      ),
    [campo, modo, lavoura, longe, faixas],
  );

  // estaca + plaquinha na cabeceira de cada plot (canto do começo da carreira 1)
  const [estacas, placas] = useMemo(() => {
    const e: Item[] = [];
    const p: Item[] = [];
    for (const plot of campo.plots) {
      const [x, z] = [plot.origem_m[1] - 0.25, plot.origem_m[0] + 0.04];
      e.push({ id: plot.id, pos: [x, 0.28, z], escala: [0.05, 0.56, 0.05] });
      p.push({ id: plot.id, pos: [x - 0.03, 0.58, z], escala: [0.02, 0.14, 0.2] });
    }
    return [e, p];
  }, [campo]);

  // moldura: retângulo no carreador em volta de cada plot em alerta. Só é
  // refeita quando os alertas mudam (a linha troca geometria e material a cada
  // pontos novos; refazer a cada snapshot dava engasgos)
  const assinaturaAlertas = `${campo.plots.length}|${campo.plots.filter((p) => p.alerta).map((p) => `${p.id}:${p.alerta}`).join(",")}`;
  const moldura = useMemo(() => {
    const pontos: [number, number, number][] = [];
    const cores: Color[] = [];
    const y = 0.12;
    const folga = 0.2; // para dentro do carreador; na largura, os plots se encostam
    for (const p of campo.plots) {
      if (!p.alerta) continue;
      const [u0, v0] = p.origem_m;
      const [u1, v1] = [u0 + campo.largura_plot_m, v0 + campo.comprimento_plot_m];
      const cantos: [number, number, number][] = [
        [v0 - folga, y, u0],
        [v1 + folga, y, u0],
        [v1 + folga, y, u1],
        [v0 - folga, y, u1],
      ];
      const cor = new Color(corAlerta(p.alerta === "critico"));
      for (let i = 0; i < 4; i++) {
        pontos.push(cantos[i], cantos[(i + 1) % 4]);
        cores.push(cor, cor);
      }
    }
    return { pontos, cores };
  }, [assinaturaAlertas]);

  // bandeirinha na cabeceira de cada CARREIRA em alerta (diz qual das três)
  const [hastesBandeira, bandeiras] = useMemo(() => {
    const h: Item[] = [];
    const b: Item[] = [];
    for (const p of campo.plots)
      for (const k of p.carreiras) {
        if (!k.alerta) continue;
        // no meio do carreador, mais alta que as estacas: dá para ver de onde a câmera estiver
        const x = p.origem_m[1] - 0.55;
        h.push({ id: p.id, pos: [x, 0.45, k.centro_u_m], escala: [0.03, 0.9, 0.03] });
        b.push({ id: p.id, pos: [x, 0.76, k.centro_u_m + 0.17], escala: [0.02, 0.24, 0.34], cor: corAlerta(k.alerta === "critico") });
      }
    return [h, b];
  }, [campo]);

  // pino de longe: haste (cone de ponta para baixo) + cabeça. Crítico é mais alto.
  const emAlerta = useMemo(() => campo.plots.filter((p) => p.alerta), [campo]);
  const altura = (critico: boolean) => (critico ? 3.4 : 2.3);
  const hastes = useMemo<Item[]>(
    () =>
      emAlerta.map((p) => {
        const [x, z] = centroPlot(campo, p);
        const h = altura(p.alerta === "critico");
        return { id: p.id, pos: [x, h / 2 + 0.05, z], escala: [1, h, 1], rotX: Math.PI, cor: corAlerta(p.alerta === "critico") };
      }),
    [campo, emAlerta],
  );
  const cabecas = useMemo<Item[]>(
    () =>
      emAlerta.map((p) => {
        const [x, z] = centroPlot(campo, p);
        return { id: p.id, pos: [x, altura(p.alerta === "critico") + 0.05, z], escala: [1, 1, 1], cor: corAlerta(p.alerta === "critico") };
      }),
    [campo, emAlerta],
  );

  const margem = 4;
  const plot = (id: string) => selecionar({ tipo: "plot", id });
  const carreira = (id: string) => selecionar({ tipo: "carreira", id });
  return (
    <group>
      <mesh rotation-x={-Math.PI / 2} position={[campo.comprimento_m / 2, -0.02, campo.largura_m / 2]} raycast={() => null}>
        <planeGeometry args={[campo.comprimento_m + margem * 2, campo.largura_m + margem * 2]} />
        <meshLambertMaterial color={lavoura ? COR.soloCarreador : COR.chao} />
      </mesh>

      <Instancias itens={bases} aoClicar={plot} aoPassar={aoPassar}>
        <boxGeometry />
        <meshLambertMaterial color={lavoura ? COR.soloPlot : COR.plot} />
      </Instancias>

      {lavoura ? (
        // camalhão: solo com luz (o relevo aparece); a cor é sempre a mesma
        <Instancias key="camalhao" itens={carreiras} aoClicar={carreira} aoPassar={aoPassar}>
          <boxGeometry />
          <meshLambertMaterial color={COR.camalhao} />
        </Instancias>
      ) : (
        // cor exata dos tokens validados: material sem luz
        <Instancias key="barras" itens={carreiras} aoClicar={carreira} aoPassar={aoPassar}>
          <boxGeometry />
          <meshBasicMaterial />
        </Instancias>
      )}

      <Instancias itens={estacas} aoClicar={plot} aoPassar={aoPassar}>
        <boxGeometry />
        <meshLambertMaterial color={COR.estaca} />
      </Instancias>
      <Instancias itens={placas} aoClicar={plot} aoPassar={aoPassar}>
        <boxGeometry />
        <meshLambertMaterial color={COR.estaca} />
      </Instancias>

      {moldura.pontos.length > 0 && (
        <Line points={moldura.pontos} vertexColors={moldura.cores} segments lineWidth={longe ? 2 : 3} raycast={() => null} />
      )}

      {!longe && (
        <>
          <Instancias itens={hastesBandeira} aoClicar={plot} aoPassar={aoPassar}>
            <boxGeometry />
            <meshLambertMaterial color={COR.estaca} />
          </Instancias>
          <Instancias itens={bandeiras} aoClicar={plot} aoPassar={aoPassar}>
            <boxGeometry />
            <meshBasicMaterial />
          </Instancias>
        </>
      )}

      {longe && (
        <>
          <Instancias itens={hastes} aoClicar={plot} aoPassar={aoPassar}>
            <coneGeometry args={[0.18, 1, 10]} />
            <meshBasicMaterial />
          </Instancias>
          <Instancias itens={cabecas} aoClicar={plot} aoPassar={aoPassar}>
            <sphereGeometry args={[0.42, 16, 12]} />
            <meshBasicMaterial />
          </Instancias>
        </>
      )}
    </group>
  );
}
