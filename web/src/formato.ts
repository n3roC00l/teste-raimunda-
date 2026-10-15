// Formatação pt-BR. Horários vêm como texto do relógio do Pi
// ("2026-10-15 09:41:02") e são mostrados como estão: nada de fuso.

const inteiro = new Intl.NumberFormat("pt-BR");

export const numero = (n: number | null | undefined) => (n === null || n === undefined ? "--" : inteiro.format(n));

export const pct = (v: number | null | undefined) => (v === null || v === undefined ? "--" : `${Math.round(v * 100)}%`);

export function duracao(segundos: number | null | undefined): string {
  if (segundos === null || segundos === undefined) return "--";
  const s = Math.max(0, Math.round(segundos));
  if (s < 60) return `${s} s`;
  if (s < 3600) return `${Math.floor(s / 60)} min`;
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return m ? `${h} h ${String(m).padStart(2, "0")} min` : `${h} h`;
}

export const hora = (ts: string | null | undefined) => (ts ? ts.slice(11, 19) : "--");

export function dataHora(ts: string | null | undefined): string {
  if (!ts) return "--";
  const [d, h] = ts.split(" ");
  const [, mes, dia] = d.split("-");
  return `${dia}/${mes} ${h?.slice(0, 8) ?? ""}`;
}

const NOMES_EVENTO: Record<string, string> = {
  painel_iniciado: "painel iniciado",
  captura_iniciada: "captura iniciada",
  captura_parada: "captura parada",
  parcela_avancada: "próxima carreira",
  parcela_voltou: "carreira anterior",
  parcela_detectada: "analisador mudou de carreira",
  experimento_alterado: "experimento alterado",
  analisador_iniciado: "analisador iniciado",
  analisador_pronto: "analisador pronto",
  analisador_erro: "erro no analisador",
  imagem_erro: "erro numa foto",
  sync_ok: "backup na nuvem feito",
  sync_erro: "erro no backup",
  planilha_exportada: "planilha exportada",
  csv_legado_arquivado: "CSV antigo arquivado",
};

export function descreverEvento(ev: { evento: string; [k: string]: unknown }): string {
  const nome = NOMES_EVENTO[ev.evento] ?? ev.evento.replaceAll("_", " ");
  if (ev.evento === "parcela_avancada" || ev.evento === "parcela_voltou") return `${nome}: ${ev.de} → ${ev.para}`;
  if (typeof ev.parcela === "string" && ev.parcela) return `${nome}: ${ev.parcela}`;
  if (typeof ev.erro === "string") return `${nome}: ${ev.erro}`;
  return nome;
}

export const ehErro = (evento: string) => evento.endsWith("_erro") || evento === "imagem_erro";
