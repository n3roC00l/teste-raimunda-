// Tipos do snapshot (core/campo.py, schema 1). Espelho do Python: se o
// schema mudar lá, muda aqui junto. A visão só lê; nada é calculado aqui.

export const SCHEMA_SUPORTADO = 1;

export type Alerta = "atencao" | "critico" | null;
export type EstadoCarreira = "pendente" | "capturando" | "analisada";
export type EstadoPlot = "pendente" | "parcial" | "concluido";

export type CodigoAlerta = "analisador_erro" | "analise_parada" | "fila" | "disco" | "backup";

export interface ItemAlerta {
  alerta: Exclude<Alerta, null>;
  codigo: CodigoAlerta;
  motivo: string;
}

export interface Carreira {
  linha: number;
  id: string;
  centro_u_m: number;
  esperado: number | null;
  estado: EstadoCarreira;
  alerta: Alerta;
  motivo: string | null;
  plantulas: number | null;
  plantulas_bruto: number | null;
  emergencia: number | null;
  imagens: number;
  primeira_imagem: string | null;
  ultima_imagem: string | null;
  ultima_analise: string | null;
  sincronizada_em: string | null;
  exportada_em: string | null;
  versoes_modelo: string[];
  versoes_software: string[];
  incerteza: number | null;
}

export interface Plot {
  id: string;
  x: number;
  y: number;
  ordem: number;
  origem_m: [number, number];
  graos: number | null;
  esperado: number | null;
  plantulas: number | null;
  emergencia: number | null;
  estado: EstadoPlot;
  alerta: Alerta;
  motivo: string | null;
  fora_da_planilha: boolean;
  carreiras: Carreira[];
}

export interface GeoCampo {
  lat: number; // canto do plot X1Y1 no começo da carreira 1
  lon: number;
  rumo_graus: number; // para onde as carreiras andam (a partir do norte, horário)
  espelhar: boolean;
  aproximado: boolean;
  fuso_horas: number;
}

export interface Campo {
  carreiras_por_plot: number;
  espacamento_m: number;
  largura_plot_m: number;
  comprimento_plot_m: number;
  passagem_m: number;
  folga_m: number;
  eixos_trocados: boolean;
  largura_m: number;
  comprimento_m: number;
  geo: GeoCampo;
  plots: Plot[];
}

export interface Posicao {
  parcela: string;
  plot: string;
  x: number;
  y: number;
  linha: number;
  modo: "campanha" | "manual";
  ordem: number | null;
  total_plots: number | null;
}

/** Estimativa (não há odômetro): tempo na carreira ÷ duração típica. */
export interface Movimento {
  inicio_carreira: string | null;
  idade_carreira_s: number | null;
  duracao_tipica_s: number;
  fonte_duracao: string;
  progresso_estimado: number | null;
  sentido: 1 | -1;
  trajeto: string;
  intervalo_captura_s: number;
}

export interface Rover {
  posicao: Posicao | null;
  movimento: Movimento | null;
  capturando: boolean;
  analisador_estado: string;
  fila_pendente: number | null;
  ultima_imagem: string | null;
  ultima_parcela_analisada: string | null;
  plantulas_ultima: number | null;
  plantulas_ultima_bruto: number | null;
  status_em: string | null;
  idade_status_s: number | null;
  alertas: ItemAlerta[];
  alerta: Alerta;
  motivo: string | null;
}

export interface Kpis {
  plots_total: number;
  plots_concluidos: number;
  plots_parciais: number;
  plots_em_alerta: number;
  carreiras_total: number;
  carreiras_analisadas: number;
  carreiras_em_alerta: number;
  progresso: number | null;
  plantulas: number;
  plantulas_bruto: number;
  plantulas_em_captura: number | null;
  imagens: number;
  esperado: number | null;
  emergencia_media: number | null;
  fila_pendente: number | null;
  ultima_sync: string | null;
  idade_sync_s: number | null;
  ultima_atividade: string | null;
  idade_atividade_s: number | null;
}

export interface Telemetria {
  cpu_temp_c: number | null;
  disco_livre_gb: number | null;
  processos: Record<string, boolean | null>;
}

export interface Saude {
  telemetria: Telemetria | null;
  alertas: ItemAlerta[];
  alerta: Alerta;
  motivo: string | null;
}

export interface Limiares {
  emergencia_atencao: number;
  emergencia_critico: number;
  emergencia_maxima: number;
  fila_atencao: number;
  status_velho_s: number;
  sync_velha_s: number;
  disco_atencao_gb: number;
  disco_critico_gb: number;
}

export interface Evento {
  ts: string;
  evento: string;
  [chave: string]: unknown;
}

export interface Snapshot {
  schema: number;
  gerado_em: string;
  versao_software: string;
  demo: boolean;
  experimento: string;
  experimentos: string[];
  campanha_atual: boolean;
  fontes: {
    planilha: string | null;
    csv_total: number;
    csv_linhas: number;
    csv_sem_parcela: number;
    csv_fora_da_grade: number;
    status: boolean;
    eventos: number;
  };
  nota_contagem: string;
  limiares: Limiares;
  campo: Campo;
  rover: Rover;
  kpis: Kpis;
  saude: Saude;
  eventos: Evento[];
}

// --- entorno (ferramentas/osm_entorno.py -> public/entorno/fapa.json) ---
export type Ponto = [number, number]; // [lat, lon]

export interface Entorno {
  fonte: string;
  estradas: { tipo: string; nome: string; ref: string; largura_m: number; pontos: Ponto[] }[];
  rios: { nome: string; largura_m: number; pontos: Ponto[] }[];
  areas: { tipo: "mata" | "agua" | "sede_rural" | "gramado"; nome: string; pontos: Ponto[] }[];
  predios: { nome: string; tipo: "predio" | "galpao" | "estufa"; altura_m: number; aproximado: boolean; pontos: Ponto[] }[];
  marcos: { nome: string; lat: number; lon: number }[];
}
