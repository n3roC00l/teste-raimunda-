import { useEstado } from "./store";
import { SCHEMA_SUPORTADO, type Snapshot } from "./tipos";

// Consulta o servidor_visao.py a cada 2 s (como o painel lê o status).
// Modo demonstração SÓ com ?demo na URL: nunca cai na demo sozinho quando o
// servidor some, para dado inventado não se passar por dado real.

const INTERVALO_MS = 2000;
const TEMPO_LIMITE_MS = 5000;
export const MODO_DEMO = new URLSearchParams(location.search).has("demo");

let geracao = 0;
let timer: number | undefined;

async function buscar(): Promise<void> {
  const { experimento, receber, falhou } = useEstado.getState();
  const url = MODO_DEMO
    ? "demo/snapshot.json"
    : "api/snapshot" + (experimento ? `?experimento=${encodeURIComponent(experimento)}` : "");
  const controle = new AbortController();
  const limite = window.setTimeout(() => controle.abort(), TEMPO_LIMITE_MS);
  try {
    const resposta = await fetch(url, { cache: "no-store", signal: controle.signal });
    if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
    const snap = (await resposta.json()) as Snapshot;
    if (snap.schema !== SCHEMA_SUPORTADO) {
      throw new Error(`snapshot schema ${snap.schema}; esta tela entende o ${SCHEMA_SUPORTADO}`);
    }
    receber(snap, MODO_DEMO);
  } catch (e) {
    falhou(e instanceof Error ? e.message : String(e));
  } finally {
    window.clearTimeout(limite);
  }
}

async function ciclo(g: number): Promise<void> {
  await buscar();
  if (g === geracao && !MODO_DEMO) timer = window.setTimeout(() => ciclo(g), INTERVALO_MS);
}

function reiniciar(): void {
  geracao += 1;
  window.clearTimeout(timer);
  void ciclo(geracao);
}

export function iniciarConsulta(): void {
  reiniciar();
  // trocar de experimento busca na hora, sem esperar o próximo ciclo
  useEstado.subscribe((agora, antes) => {
    if (agora.experimento !== antes.experimento) reiniciar();
  });
}

export function urlFoto(nome: string): string {
  return `api/foto/${encodeURIComponent(nome)}`;
}
