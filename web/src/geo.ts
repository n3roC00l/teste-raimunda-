import type { GeoCampo } from "./tipos";

// Mundo -> plano do campo -> cena. O snapshot diz onde fica o canto do ensaio
// (lat/lon) e para onde as carreiras andam (rumo). Equiretangular local: erro
// desprezível em 1 a 2 km. Cena: x = v (ao longo das carreiras), z = u.

const M_POR_GRAU_LAT = 110540;

export interface Projecao {
  /** lat/lon -> [x, z] da cena (plano do campo, antes do deslocamento) */
  (lat: number, lon: number): [number, number];
}

function eixos(geo: GeoCampo) {
  const r = (geo.rumo_graus * Math.PI) / 180;
  const v: [number, number] = [Math.sin(r), Math.cos(r)]; // (leste, norte) ao longo das carreiras
  const lado = geo.espelhar ? -1 : 1; // u à direita de quem anda (padrão) ou à esquerda
  const u: [number, number] = [Math.sin(r + (lado * Math.PI) / 2), Math.cos(r + (lado * Math.PI) / 2)];
  return { v, u };
}

export function criarProjecao(geo: GeoCampo): Projecao {
  const mLon = 111320 * Math.cos((geo.lat * Math.PI) / 180);
  const { v, u } = eixos(geo);
  return (lat, lon) => {
    const e = (lon - geo.lon) * mLon;
    const n = (lat - geo.lat) * M_POR_GRAU_LAT;
    return [e * v[0] + n * v[1], e * u[0] + n * u[1]];
  };
}

/** Direção (leste, norte, cima) -> vetor da cena [x, y, z]. */
export function direcaoNaCena(geo: GeoCampo, leste: number, norte: number, cima: number): [number, number, number] {
  const { v, u } = eixos(geo);
  return [leste * v[0] + norte * v[1], cima, leste * u[0] + norte * u[1]];
}

/** Hora local do Pi ("AAAA-MM-DD HH:MM:SS") -> instante UTC (ms). */
export function instanteUTC(local: string, fusoHoras: number): number {
  const [d, h] = local.split(" ");
  const [ano, mes, dia] = d.split("-").map(Number);
  const [hh, mm, ss] = (h ?? "0:0:0").split(":").map(Number);
  return Date.UTC(ano, mes - 1, dia, hh, mm, ss) - fusoHoras * 3600_000;
}

/** Posição do Sol (aproximação do NOAA/Almanaque, erro < 1°). Ângulos em rad;
 * azimute a partir do norte, sentido horário. */
export function posicaoSol(utcMs: number, lat: number, lon: number): { elevacao: number; azimute: number } {
  const rad = Math.PI / 180;
  const d = (utcMs - Date.UTC(2000, 0, 1, 12)) / 86400_000;
  const g = ((357.529 + 0.98560028 * d) % 360) * rad;
  const q = (280.459 + 0.98564736 * d) % 360;
  const L = (q + 1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g)) * rad;
  const e = (23.439 - 0.00000036 * d) * rad;
  const ra = Math.atan2(Math.cos(e) * Math.sin(L), Math.cos(L));
  const dec = Math.asin(Math.sin(e) * Math.sin(L));
  const gmst = (18.697374558 + 24.06570982441908 * d) % 24;
  const H = (gmst * 15 + lon) * rad - ra;
  const fi = lat * rad;
  const elevacao = Math.asin(Math.sin(fi) * Math.sin(dec) + Math.cos(fi) * Math.cos(dec) * Math.cos(H));
  const azimute = Math.atan2(-Math.sin(H), Math.tan(dec) * Math.cos(fi) - Math.sin(fi) * Math.cos(H));
  return { elevacao, azimute: (azimute + 2 * Math.PI) % (2 * Math.PI) };
}
