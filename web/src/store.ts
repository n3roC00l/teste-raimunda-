import { create } from "zustand";
import type { Snapshot } from "./tipos";

// Estado da visão: um snapshot só (o último recebido) e o que o usuário
// escolheu. Nada aqui recalcula indicador; isso é do core/campo.py.

export type Conexao = "carregando" | "ao_vivo" | "sem_conexao" | "demo";
export type Selecao =
  | { tipo: "plot"; id: string }
  | { tipo: "carreira"; id: string }
  | { tipo: "rover" }
  | null;
export type ModoCor = "estado" | "emergencia";
export type AlvoCamera = "tudo" | "rover" | "selecao";

interface Estado {
  snap: Snapshot | null;
  conexao: Conexao;
  recebidoEm: number | null; // performance.now() da última resposta boa
  falhas: number;
  erro: string | null;
  experimento: string | null; // null = o da campanha atual do painel
  selecao: Selecao;
  hover: string | null; // id de plot ou carreira sob o ponteiro
  modoCor: ModoCor;
  pedidoCamera: { alvo: AlvoCamera; n: number };

  receber: (snap: Snapshot, demo: boolean) => void;
  falhou: (erro: string) => void;
  escolherExperimento: (experimento: string | null) => void;
  /** `voar`: além de selecionar, leva a câmera até lá. */
  selecionar: (selecao: Selecao, voar?: boolean) => void;
  setHover: (id: string | null) => void;
  setModoCor: (modo: ModoCor) => void;
  pedirCamera: (alvo: AlvoCamera) => void;
}

// Duas falhas seguidas (~4 s) antes de dizer "sem conexão": uma resposta
// perdida no Wi-Fi do campo não deve piscar o aviso.
const FALHAS_PARA_SEM_CONEXAO = 2;

export const useEstado = create<Estado>((set) => ({
  snap: null,
  conexao: "carregando",
  recebidoEm: null,
  falhas: 0,
  erro: null,
  experimento: null,
  selecao: null,
  hover: null,
  // ?modo=emergencia abre já no mapa de emergência (ex.: tela de apresentação)
  modoCor: new URLSearchParams(location.search).get("modo") === "emergencia" ? "emergencia" : "estado",
  pedidoCamera: { alvo: "tudo", n: 0 },

  receber: (snap, demo) =>
    set({ snap, conexao: demo ? "demo" : "ao_vivo", recebidoEm: performance.now(), falhas: 0, erro: null }),
  falhou: (erro) =>
    set((e) => ({
      falhas: e.falhas + 1,
      erro,
      conexao: e.falhas + 1 >= FALHAS_PARA_SEM_CONEXAO ? "sem_conexao" : e.conexao,
    })),
  escolherExperimento: (experimento) => set({ experimento, selecao: null, hover: null }),
  selecionar: (selecao, voar = false) =>
    set((e) => ({ selecao, pedidoCamera: voar && selecao ? { alvo: "selecao", n: e.pedidoCamera.n + 1 } : e.pedidoCamera })),
  setHover: (hover) => set({ hover }),
  setModoCor: (modoCor) => set({ modoCor }),
  pedirCamera: (alvo) => set((e) => ({ pedidoCamera: { alvo, n: e.pedidoCamera.n + 1 } })),
}));
