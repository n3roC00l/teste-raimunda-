import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import {
  BufferGeometry,
  CanvasTexture,
  Color,
  CylinderGeometry,
  DoubleSide,
  ExtrudeGeometry,
  Float32BufferAttribute,
  IcosahedronGeometry,
  type InstancedMesh,
  type MeshBasicMaterial,
  MeshLambertMaterial,
  Object3D,
  PlaneGeometry,
  RepeatWrapping,
  Shape,
  ShapeGeometry,
  Vector2,
} from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import type { Campo } from "../tipos";
import { ambiente, sorteador } from "./ambiente";
import { useEntorno, useProjecao } from "./useEntorno";

// Entorno da FAPA (OpenStreetMap, via ferramentas/osm_entorno.py): vias,
// riachos, mata e prédios. É CENÁRIO: tons apagados, para não competir com os
// dados do ensaio. Prédios da FAPA: posição e tamanho aproximados.
// As árvores balançam com um "vento" feito no shader (barato: zero CPU).

type XZ = [number, number];

const COR = {
  chao: "#6f8f57",
  mata: "#557a43",
  agua: "#5b8db5",
  gramado: "#7fa063",
  sede_rural: "#9a8a6c",
  asfalto: "#8c8c88",
  terra: "#b39b74",
  faixa: "#f2eedf",
  riacho: "#6a9cc4",
  parede: "#efede8",
  teto: "#cfcac1",
  galpaoParede: "#dfe3e6",
  galpaoTeto: "#a9b7c2",
  estufa: "#f4f8f8",
  copa: "#5f9145",
  tronco: "#7a5a40",
};
// altura de cada camada (log depth buffer na Canvas evita briga de profundidade)
const Y = { chao: -0.3, area: -0.22, riacho: -0.16, via: -0.12, faixa: -0.1 };
const ASFALTO = new Set(["secondary", "secondary_link", "tertiary", "unclassified", "residential", "primary", "trunk"]);

function faixa(pontos: XZ[], largura: number, y: number): BufferGeometry {
  const pos: number[] = [];
  const idx: number[] = [];
  pontos.forEach(([x, z], i) => {
    const a = pontos[Math.max(0, i - 1)];
    const b = pontos[Math.min(pontos.length - 1, i + 1)];
    const n = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
    const nx = (-(b[1] - a[1]) / n) * (largura / 2);
    const nz = ((b[0] - a[0]) / n) * (largura / 2);
    pos.push(x + nx, y, z + nz, x - nx, y, z - nz);
    if (i > 0) {
      const k = (i - 1) * 2;
      idx.push(k, k + 2, k + 1, k + 1, k + 2, k + 3); // normais para cima
    }
  });
  const g = new BufferGeometry();
  g.setAttribute("position", new Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

function tracejado(pontos: XZ[], y: number): BufferGeometry | null {
  // faixa central: 3 m pintados a cada 9 m
  const pedacos: BufferGeometry[] = [];
  for (let i = 1; i < pontos.length; i++) {
    const [x0, z0] = pontos[i - 1];
    const [x1, z1] = pontos[i];
    const L = Math.hypot(x1 - x0, z1 - z0);
    for (let s = 0; s + 3 <= L; s += 9) {
      const a: XZ = [x0 + ((x1 - x0) * s) / L, z0 + ((z1 - z0) * s) / L];
      const b: XZ = [x0 + ((x1 - x0) * (s + 3)) / L, z0 + ((z1 - z0) * (s + 3)) / L];
      pedacos.push(faixa([a, b], 0.18, y));
    }
  }
  return pedacos.length ? mergeGeometries(pedacos) : null;
}

const forma = (pontos: XZ[]) => new Shape(pontos.map(([x, z]) => new Vector2(x, -z)));

function poligono(pontos: XZ[], y: number): BufferGeometry {
  const g = new ShapeGeometry(forma(pontos));
  g.rotateX(-Math.PI / 2);
  g.translate(0, y, 0);
  return g;
}

function dentro(x: number, z: number, pts: XZ[]): boolean {
  let d = false;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const [xi, zi] = pts[i];
    const [xj, zj] = pts[j];
    if (zi > z !== zj > z && x < ((xj - xi) * (z - zi)) / (zj - zi) + xi) d = !d;
  }
  return d;
}

// Lavouras vizinhas (CENÁRIO): a FAPA é cercada de lavoura, e no satélite isso
// aparece como retalhos de cores. Quadras alinhadas ao ensaio, puladas onde
// passam vias, prédios, mata ou o próprio ensaio.
const CULTURAS = [
  { nome: "soja", base: "#6f9a4b", linha: "#5a8240" },
  { nome: "milho", base: "#557f3d", linha: "#466b31" },
  { nome: "trigo", base: "#a9ab5c", linha: "#93954c" },
  { nome: "palhada", base: "#b9a37a", linha: "#a38f68" },
  { nome: "solo", base: "#8e7056", linha: "#7c6149" },
];

function texturaLinhas(base: string, linha: string): CanvasTexture {
  const c = document.createElement("canvas");
  c.width = c.height = 32;
  const g = c.getContext("2d")!;
  g.fillStyle = base;
  g.fillRect(0, 0, 32, 32);
  g.fillStyle = linha;
  for (let y = 0; y < 32; y += 8) g.fillRect(0, y, 32, 3); // linhas de plantio
  const t = new CanvasTexture(c);
  t.wrapS = t.wrapT = RepeatWrapping;
  return t;
}

function lavouras(
  campo: { comprimento_m: number; largura_m: number },
  bloqueios: XZ[][],
  vias: XZ[][],
  sorte: () => number,
): BufferGeometry[][] {
  const porCultura: BufferGeometry[][] = CULTURAS.map(() => []);
  const [LX, LZ, VAO] = [110, 72, 7]; // quadra (m) e carreador entre quadras
  const pontosVia: XZ[] = [];
  for (const v of vias)
    for (let i = 1; i < v.length; i++) {
      const L = Math.hypot(v[i][0] - v[i - 1][0], v[i][1] - v[i - 1][1]);
      for (let s = 0; s <= L; s += 6) pontosVia.push([v[i - 1][0] + ((v[i][0] - v[i - 1][0]) * s) / L, v[i - 1][1] + ((v[i][1] - v[i - 1][1]) * s) / L]);
    }
  for (let x0 = -660; x0 < campo.comprimento_m + 660; x0 += LX + VAO) {
    for (let z0 = -660; z0 < campo.largura_m + 660; z0 += LZ + VAO) {
      const [x1, z1] = [x0 + LX, z0 + LZ];
      const toca = (x: number, z: number, folga: number) => x > x0 - folga && x < x1 + folga && z > z0 - folga && z < z1 + folga;
      if (toca(campo.comprimento_m / 2, campo.largura_m / 2, campo.comprimento_m / 2 + 20)) continue; // ensaio
      if (pontosVia.some(([x, z]) => toca(x, z, 6))) continue;
      const cantos: XZ[] = [[x0, z0], [x1, z0], [x1, z1], [x0, z1], [(x0 + x1) / 2, (z0 + z1) / 2]];
      if (bloqueios.some((b) => cantos.some(([x, z]) => dentro(x, z, b)) || b.some(([x, z]) => toca(x, z, 3)))) continue;
      const g = new PlaneGeometry(LX, LZ);
      g.rotateX(-Math.PI / 2);
      g.translate((x0 + x1) / 2, Y.area + 0.02, (z0 + z1) / 2);
      // UV em metros (linha a cada 0,75 m de textura): linhas contínuas
      const pos = g.getAttribute("position");
      const uv = g.getAttribute("uv");
      for (let i = 0; i < pos.count; i++) uv.setXY(i, pos.getZ(i) / 6, pos.getX(i) / 6);
      porCultura[Math.floor(sorte() * CULTURAS.length)].push(g);
    }
  }
  return porCultura;
}

/** Árvore low-poly: tronco + copa, com cor por vértice (uma malha só). */
function geometriaArvore(): BufferGeometry {
  const pintar = (g: BufferGeometry, cor: string) => {
    const c = new Color(cor);
    const n = g.getAttribute("position").count;
    g.setAttribute("color", new Float32BufferAttribute(Array.from({ length: n }, () => [c.r, c.g, c.b]).flat(), 3));
    return g;
  };
  const tronco = pintar(new CylinderGeometry(0.14, 0.2, 1.8, 5).translate(0, 0.9, 0).toNonIndexed(), COR.tronco);
  const copa = pintar(new IcosahedronGeometry(1.5, 0).scale(1, 1.15, 1).translate(0, 2.9, 0).toNonIndexed(), COR.copa);
  tronco.deleteAttribute("uv");
  copa.deleteAttribute("uv");
  return mergeGeometries([tronco, copa])!;
}

function materialComVento(tempo: { value: number }) {
  const m = new MeshLambertMaterial({ vertexColors: true });
  m.onBeforeCompile = (shader) => {
    shader.uniforms.uTempo = tempo;
    shader.vertexShader = shader.vertexShader
      .replace("#include <common>", "#include <common>\nuniform float uTempo;")
      .replace(
        "#include <begin_vertex>",
        `#include <begin_vertex>
        #ifdef USE_INSTANCING
          vec3 origemV = vec3(instanceMatrix[3][0], instanceMatrix[3][1], instanceMatrix[3][2]);
        #else
          vec3 origemV = vec3(0.0);
        #endif
        float altV = max(position.y - 1.2, 0.0);
        float faseV = origemV.x * 0.17 + origemV.z * 0.13;
        transformed.x += (sin(uTempo * 1.6 + faseV) + 0.4 * sin(uTempo * 3.7 + faseV * 2.0)) * 0.05 * altV;
        transformed.z += cos(uTempo * 1.25 + faseV) * 0.035 * altV;`,
      );
  };
  return m;
}

function Arvores({ posicoes }: { posicoes: [number, number, number][] }) {
  const ref = useRef<InstancedMesh>(null);
  const tempo = useMemo(() => ({ value: 0 }), []);
  const geometria = useMemo(geometriaArvore, []);
  const material = useMemo(() => materialComVento(tempo), [tempo]);
  useEffect(() => {
    const m = ref.current;
    if (!m) return;
    const o = new Object3D();
    posicoes.forEach(([x, z, escala], i) => {
      o.position.set(x, Y.chao, z);
      o.rotation.set(0, (x * 13.7 + z * 7.1) % 6.28, 0);
      o.scale.setScalar(escala);
      o.updateMatrix();
      m.setMatrixAt(i, o.matrix);
    });
    m.instanceMatrix.needsUpdate = true;
    m.computeBoundingSphere();
  }, [posicoes]);
  useFrame(({ clock }) => {
    tempo.value = clock.elapsedTime;
  });
  if (posicoes.length === 0) return null;
  return <instancedMesh key={posicoes.length} ref={ref} args={[geometria, material, posicoes.length]} raycast={() => null} />;
}

function Janelas({ geos }: { geos: ExtrudeGeometry[] }) {
  const geo = useMemo(() => (geos.length ? mergeGeometries(geos.map((g) => g.toNonIndexed())) : null), [geos]);
  const material = useRef<MeshBasicMaterial>(null);
  useFrame(() => {
    if (material.current) material.current.opacity = 0.85 * ambiente.noite;
  });
  if (!geo) return null;
  return (
    <mesh geometry={geo} raycast={() => null}>
      <meshBasicMaterial ref={material} color="#ffd98a" transparent opacity={0} depthWrite={false} />
    </mesh>
  );
}

export default function Entorno({ campo }: { campo: Campo }) {
  const dados = useEntorno();
  const proj = useProjecao(campo.geo);
  const centro: XZ = [campo.comprimento_m / 2, campo.largura_m / 2];

  const cena = useMemo(() => {
    if (!dados) return null;
    const p = (lista: [number, number][]) => lista.map(([lat, lon]) => proj(lat, lon));
    const vias = dados.estradas.map((e) => ({ ...e, xz: p(e.pontos) }));
    const asfalto = vias.filter((v) => ASFALTO.has(v.tipo)).map((v) => faixa(v.xz, v.largura_m, Y.via));
    const terra = vias.filter((v) => !ASFALTO.has(v.tipo)).map((v) => faixa(v.xz, v.largura_m, Y.via));
    const pr540 = vias.filter((v) => v.ref.includes("PR-540"));
    const faixas = pr540.map((v) => tracejado(v.xz, Y.faixa)).filter(Boolean) as BufferGeometry[];
    const rios = dados.rios.map((r) => faixa(p(r.pontos), r.largura_m, Y.riacho));
    const areas = dados.areas.map((a) => ({ tipo: a.tipo, xz: p(a.pontos) }));
    const predios = dados.predios.map((b) => ({ ...b, xz: p(b.pontos) }));

    // árvores: mata (densidade baixa), quebra-ventos ao longo das estradas
    // do campus e algumas em volta da sede. Nunca dentro do ensaio.
    const sorte = sorteador(20261015);
    const arvores: [number, number, number][] = [];
    const livre = (x: number, z: number) =>
      !(x > -6 && x < campo.comprimento_m + 6 && z > -6 && z < campo.largura_m + 6) &&
      !predios.some((b) => dentro(x, z, b.xz));
    for (const a of areas.filter((a) => a.tipo === "mata")) {
      const xs = a.xz.map((q) => q[0]);
      const zs = a.xz.map((q) => q[1]);
      const [x0, x1, z0, z1] = [Math.min(...xs), Math.max(...xs), Math.min(...zs), Math.max(...zs)];
      const alvo = Math.min(2200, Math.round(((x1 - x0) * (z1 - z0)) / 260));
      for (let t = 0; t < alvo * 3 && arvores.length < 2600; t++) {
        const x = x0 + sorte() * (x1 - x0);
        const z = z0 + sorte() * (z1 - z0);
        if (dentro(x, z, a.xz)) arvores.push([x, z, 0.8 + sorte() * 0.8]);
      }
    }
    for (const v of vias.filter((v) => v.tipo === "unclassified" || v.tipo === "track")) {
      if (!v.xz.some(([x, z]) => Math.hypot(x - centro[0], z - centro[1]) < 480)) continue;
      for (let i = 1; i < v.xz.length; i++) {
        const [xa, za] = v.xz[i - 1];
        const [xb, zb] = v.xz[i];
        const L = Math.hypot(xb - xa, zb - za);
        for (let s = 4; s < L; s += 9) {
          const x = xa + ((xb - xa) * s) / L + (-(zb - za) / L) * 7;
          const z = za + ((zb - za) * s) / L + ((xb - xa) / L) * 7;
          if (livre(x, z) && Math.hypot(x - centro[0], z - centro[1]) < 520) arvores.push([x, z, 0.85 + sorte() * 0.5]);
        }
      }
    }
    const fapa = dados.marcos.find((m) => m.nome === "FAPA");
    if (fapa) {
      const [fx, fz] = proj(fapa.lat, fapa.lon);
      for (let t = 0; t < 120 && arvores.length < 3000; t++) {
        const ang = sorte() * Math.PI * 2;
        const r = 35 + sorte() * 45;
        const x = fx + Math.cos(ang) * r;
        const z = fz + Math.sin(ang) * r;
        if (livre(x, z) && t % 4 === 0) arvores.push([x, z, 0.9 + sorte() * 0.6]);
      }
    }

    const mesclar = (gs: BufferGeometry[]) => (gs.length ? mergeGeometries(gs) : null);
    const bloqueios = [...areas.map((a) => a.xz), ...predios.map((b) => b.xz)];
    const culturas = lavouras(campo, bloqueios, vias.map((v) => v.xz), sorte).map((gs, i) =>
      gs.length ? { geo: mergeGeometries(gs)!, textura: texturaLinhas(CULTURAS[i].base, CULTURAS[i].linha) } : null,
    );
    return {
      culturas,
      asfalto: mesclar(asfalto),
      terra: mesclar(terra),
      faixas: mesclar(faixas),
      rios: mesclar(rios),
      areas: areas.map((a) => ({ tipo: a.tipo, geo: poligono(a.xz, Y.area) })),
      predios: predios.map((b) => {
        const volume = new ExtrudeGeometry(forma(b.xz), { depth: b.altura_m, bevelEnabled: false });
        volume.rotateX(-Math.PI / 2);
        volume.translate(0, Y.chao, 0);
        const cx = b.xz.reduce((s, q) => s + q[0], 0) / b.xz.length;
        const cz = b.xz.reduce((s, q) => s + q[1], 0) / b.xz.length;
        const galpao = b.tipo === "galpao";
        const materiais = [
          new MeshLambertMaterial({ color: galpao ? COR.galpaoTeto : COR.teto }),
          new MeshLambertMaterial({ color: galpao ? COR.galpaoParede : COR.parede }),
        ];
        // faixa de janelas: o mesmo contorno, um pouco maior, baixo e no meio da parede
        const janelas = b.tipo === "estufa" ? null : new ExtrudeGeometry(forma(b.xz), { depth: 0.7, bevelEnabled: false });
        if (janelas) {
          janelas.rotateX(-Math.PI / 2);
          janelas.scale(1.004, 1, 1.004);
          janelas.translate(cx * -0.004, Y.chao + b.altura_m * 0.45, cz * -0.004);
        }
        return { ...b, geo: volume, materiais, janelas, centro: [cx, cz] as XZ };
      }),
      rotulos: [
        ...dados.marcos.map((m) => ({ nome: m.nome, xz: proj(m.lat, m.lon), altura: 16 })),
        ...(pr540.length ? [{ nome: "PR-540", xz: pr540.sort((a, b) => b.xz.length - a.xz.length)[0].xz[1], altura: 3 }] : []),
      ],
      arvores,
    };
  }, [dados, proj, campo.comprimento_m, campo.largura_m]);

  const semEvento = () => null; // cenário não é clicável nem atrapalha o clique nos dados
  return (
    <group>
      <mesh rotation-x={-Math.PI / 2} position={[centro[0], Y.chao, centro[1]]} raycast={semEvento}>
        <planeGeometry args={[3200, 3200]} />
        <meshLambertMaterial color={COR.chao} />
      </mesh>
      {cena && (
        <>
          {cena.culturas.map(
            (c, i) =>
              c && (
                <mesh key={`lavoura-${i}`} geometry={c.geo} raycast={semEvento}>
                  <meshLambertMaterial map={c.textura} />
                </mesh>
              ),
          )}
          {cena.areas.map((a, i) => (
            <mesh key={i} geometry={a.geo} raycast={semEvento}>
              <meshLambertMaterial color={COR[a.tipo]} />
            </mesh>
          ))}
          {cena.rios && (
            <mesh geometry={cena.rios} raycast={semEvento}>
              <meshLambertMaterial color={COR.riacho} />
            </mesh>
          )}
          {cena.terra && (
            <mesh geometry={cena.terra} raycast={semEvento}>
              <meshLambertMaterial color={COR.terra} />
            </mesh>
          )}
          {cena.asfalto && (
            <mesh geometry={cena.asfalto} raycast={semEvento}>
              <meshLambertMaterial color={COR.asfalto} />
            </mesh>
          )}
          {cena.faixas && (
            <mesh geometry={cena.faixas} raycast={semEvento}>
              <meshBasicMaterial color={COR.faixa} />
            </mesh>
          )}
          {cena.predios.map((b, i) =>
            b.tipo === "estufa" ? (
              <mesh key={i} geometry={b.geo} raycast={semEvento}>
                <meshLambertMaterial color={COR.estufa} transparent opacity={0.45} side={DoubleSide} depthWrite={false} />
              </mesh>
            ) : (
              <mesh key={i} geometry={b.geo} raycast={semEvento} material={b.materiais} />
            ),
          )}
          <Janelas geos={cena.predios.map((b) => b.janelas).filter((g): g is ExtrudeGeometry => g !== null)} />
          <Arvores posicoes={cena.arvores} />
          {cena.rotulos.map((r) => (
            <Html key={r.nome} position={[r.xz[0], r.altura, r.xz[1]]} center className="rotulo-entorno" zIndexRange={[5, 0]}>
              {r.nome}
            </Html>
          ))}
        </>
      )}
    </group>
  );
}
