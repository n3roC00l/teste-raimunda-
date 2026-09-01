"""
ui/widgets.py — blocos da tela (feat/ui-v1).

Cada `montar_*` monta um bloco e devolve (frame, *widgets que o App precisa
guardar para atualizar depois*). Helpers `cartao`, `titulo_secao`,
`linha_kv`, `linha_kv_status` implementam o sistema visual de `ui/tema.py`.
"""

import tkinter as tk

from . import tema


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def cartao(parent):
    """Frame estilo cartão: fundo BG2 + hairline de 1px (tema.LINE)."""
    return tk.Frame(parent, bg=tema.BG2, highlightbackground=tema.LINE,
                    highlightthickness=1, bd=0)


def titulo_secao(parent, fontes, texto):
    return tk.Label(parent, text=texto.upper(), bg=parent["bg"], fg=tema.T3,
                    font=fontes.secao)


def linha_kv(parent, fontes, chave, valor="", cor=None):
    """Linha 'rótulo → valor' alinhada. Retorna (frame, lbl_valor)."""
    row = tk.Frame(parent, bg=parent["bg"])
    tk.Label(row, text=chave, bg=parent["bg"], fg=tema.T2, font=fontes.rotulo_kv,
             width=15, anchor="w").pack(side="left")
    lbl_valor = tk.Label(row, text=valor, bg=parent["bg"], fg=cor or tema.T1,
                         font=fontes.valor_kv)
    lbl_valor.pack(side="left")
    return row, lbl_valor


def linha_kv_status(parent, fontes, chave, valor="", cor=None, dotcor=None):
    """Linha 'rótulo → ● valor' com bolinha de status.
    Retorna (frame, lbl_dot, lbl_valor)."""
    row = tk.Frame(parent, bg=parent["bg"])
    tk.Label(row, text=chave, bg=parent["bg"], fg=tema.T2, font=fontes.rotulo_kv,
             width=15, anchor="w").pack(side="left")
    lbl_dot = tk.Label(row, text="●", bg=parent["bg"], fg=dotcor or tema.T3,
                       font=fontes.mini)
    lbl_dot.pack(side="left", padx=(0, 5))
    lbl_valor = tk.Label(row, text=valor, bg=parent["bg"], fg=cor or tema.T1,
                         font=fontes.valor_kv)
    lbl_valor.pack(side="left")
    return row, lbl_dot, lbl_valor


# ---------------------------------------------------------------------------
# blocos
# ---------------------------------------------------------------------------
def montar_topo(parent, fontes):
    """Barra de topo: título + pílula de status.
    Retorna (frame, lbl_pill_dot, lbl_pill_texto)."""
    top = tk.Frame(parent, bg=tema.BG)
    tk.Label(top, text="ROVER FAPA", bg=tema.BG, fg=tema.T1, font=fontes.topo).pack(side="left")
    tk.Label(top, text="  Contador de Plântulas", bg=tema.BG, fg=tema.T2,
             font=fontes.topo_sub).pack(side="left")

    pill = tk.Frame(top, bg=tema.BG)
    pill.pack(side="right")
    lbl_pill_dot = tk.Label(pill, text="●", bg=tema.BG, fg=tema.T3, font=fontes.legenda)
    lbl_pill_dot.pack(side="left")
    lbl_pill_texto = tk.Label(pill, text=" iniciando…", bg=tema.BG, fg=tema.T2, font=fontes.legenda)
    lbl_pill_texto.pack(side="left")
    return top, lbl_pill_dot, lbl_pill_texto


def montar_configuracoes_experimento(parent, fontes):
    """Cartão 'Configurações do Experimento': campos Tratamento e Linha.
    Retorna (frame, entry_tratamento, entry_linha)."""
    card = cartao(parent)
    inner = tk.Frame(card, bg=tema.BG2)
    inner.pack(fill="x", padx=18, pady=14)

    titulo_secao(inner, fontes, "Configurações do Experimento").pack(anchor="w", pady=(0, 10))

    def _entry(row):
        e = tk.Entry(row, font=fontes.entrada, bg=tema.FLD, fg=tema.T1,
                     insertbackground=tema.T1, relief="flat", highlightthickness=1,
                     highlightbackground=tema.LINE, highlightcolor=tema.ACC,
                     disabledbackground=tema.BG2, disabledforeground=tema.T3, width=32)
        e.pack(side="left")
        return e

    r1 = tk.Frame(inner, bg=tema.BG2)
    r1.pack(fill="x", pady=3)
    tk.Label(r1, text="Tratamento", bg=tema.BG2, fg=tema.T2, font=fontes.rotulo,
             width=12, anchor="w").pack(side="left")
    entry_tratamento = _entry(r1)

    r2 = tk.Frame(inner, bg=tema.BG2)
    r2.pack(fill="x", pady=3)
    tk.Label(r2, text="Linha", bg=tema.BG2, fg=tema.T2, font=fontes.rotulo,
             width=12, anchor="w").pack(side="left")
    entry_linha = _entry(r2)

    return card, entry_tratamento, entry_linha


def montar_contagem(parent, fontes):
    """Cartão 'Contagem': total acumulado (número grande) + últimas leituras.
    Retorna (frame, lbl_total, lbl_ultima, lbl_bruto, lbl_fila)."""
    card = cartao(parent)
    inner = tk.Frame(card, bg=tema.BG2)
    inner.pack(fill="both", expand=True, padx=18, pady=16)

    titulo_secao(inner, fontes, "Contagem").pack(anchor="w")
    lbl_total = tk.Label(inner, text="0", bg=tema.BG2, fg=tema.T1, font=fontes.numero_grande)
    lbl_total.pack(pady=(10, 0))
    tk.Label(inner, text="total da parcela · corrigido", bg=tema.BG2, fg=tema.T2,
             font=fontes.legenda).pack()

    tk.Frame(inner, bg=tema.LINE, height=1).pack(fill="x", pady=14)

    row_u, lbl_ultima = linha_kv(inner, fontes, "última foto", "--")
    row_u.pack(anchor="w", pady=2)
    row_b, lbl_bruto = linha_kv(inner, fontes, "detecção IA", "--", cor=tema.T2)
    row_b.pack(anchor="w", pady=2)
    row_f, lbl_fila = linha_kv(inner, fontes, "fila", "0", cor=tema.T2)
    row_f.pack(anchor="w", pady=2)

    return card, lbl_total, lbl_ultima, lbl_bruto, lbl_fila


def montar_estado_sistema(parent, fontes):
    """Cartão 'Estado do sistema'.
    Retorna dict de widgets: dot_captura, val_captura, dot_analisador,
    val_analisador, val_parcela, val_fotos, lbl_temp, lbl_gpu."""
    card = cartao(parent)
    inner = tk.Frame(card, bg=tema.BG2)
    inner.pack(fill="both", expand=True, padx=18, pady=16)

    titulo_secao(inner, fontes, "Estado do sistema").pack(anchor="w", pady=(0, 10))

    grid = tk.Frame(inner, bg=tema.BG2)
    grid.pack(fill="x")
    grid.columnconfigure(0, weight=1, uniform="s")
    grid.columnconfigure(1, weight=1, uniform="s")
    c0 = tk.Frame(grid, bg=tema.BG2)
    c0.grid(row=0, column=0, sticky="nw")
    c1 = tk.Frame(grid, bg=tema.BG2)
    c1.grid(row=0, column=1, sticky="nw", padx=(24, 0))

    row_cap, dot_captura, val_captura = linha_kv_status(c0, fontes, "captura", "parada",
                                                        cor=tema.STOP, dotcor=tema.STOP)
    row_cap.pack(anchor="w", pady=2)
    row_an, dot_analisador, val_analisador = linha_kv_status(c0, fontes, "analisador", "—",
                                                             cor=tema.T3, dotcor=tema.T3)
    row_an.pack(anchor="w", pady=2)

    row_p, val_parcela = linha_kv(c1, fontes, "parcela atual", "—")
    row_p.pack(anchor="w", pady=2)
    row_f, val_fotos = linha_kv(c1, fontes, "fotos capturadas", "0")
    row_f.pack(anchor="w", pady=2)

    tk.Frame(inner, bg=tema.LINE, height=1).pack(fill="x", pady=(12, 8))

    tele = tk.Frame(inner, bg=tema.BG2)
    tele.pack(anchor="w")
    tk.Label(tele, text="CPU ", bg=tema.BG2, fg=tema.T3, font=fontes.mini).pack(side="left")
    lbl_temp = tk.Label(tele, text="--", bg=tema.BG2, fg=tema.T2, font=fontes.mini)
    lbl_temp.pack(side="left")
    tk.Label(tele, text="   ·   GPU ", bg=tema.BG2, fg=tema.T3, font=fontes.mini).pack(side="left")
    lbl_gpu = tk.Label(tele, text="--", bg=tema.BG2, fg=tema.T2, font=fontes.mini)
    lbl_gpu.pack(side="left")

    return card, {
        "dot_captura": dot_captura, "val_captura": val_captura,
        "dot_analisador": dot_analisador, "val_analisador": val_analisador,
        "val_parcela": val_parcela, "val_fotos": val_fotos,
        "lbl_temp": lbl_temp, "lbl_gpu": lbl_gpu,
    }


def montar_acoes(parent, fontes, on_toggle_capture, on_sync, on_exit):
    """Linha de ações. Retorna (frame, btn_start_stop, btn_sync, btn_exit)."""
    acts = tk.Frame(parent, bg=tema.BG)
    acts.columnconfigure(0, weight=3, uniform="a")
    acts.columnconfigure(1, weight=2, uniform="a")
    acts.columnconfigure(2, weight=1, uniform="a")

    btn_start_stop = tk.Button(
        acts, text="▶ Iniciar Captura · F5", command=on_toggle_capture,
        bg=tema.BOTAO_OK, fg="white", font=fontes.botao, bd=0, relief="flat",
        activebackground=tema.OK, activeforeground="white", cursor="hand2",
    )
    btn_start_stop.grid(row=0, column=0, sticky="ew", padx=(0, tema.GAP // 2), ipady=10)

    btn_sync = tk.Button(
        acts, text="☁ Sincronizar · F9", command=on_sync,
        bg=tema.BOTAO_NEUTRO, fg=tema.T1, font=fontes.botao, bd=0, relief="flat",
        activebackground=tema.BOTAO_NEUTRO_ATIVO, activeforeground=tema.T1,
        disabledforeground=tema.T3, cursor="hand2",
    )
    btn_sync.grid(row=0, column=1, sticky="ew", padx=tema.GAP // 2, ipady=10)

    btn_exit = tk.Button(
        acts, text="Sair · Ctrl+Q", command=on_exit,
        bg=tema.BOTAO_NEUTRO, fg=tema.T2, font=fontes.botao, bd=0, relief="flat",
        activebackground=tema.BOTAO_NEUTRO_ATIVO, activeforeground=tema.T1, cursor="hand2",
    )
    btn_exit.grid(row=0, column=2, sticky="ew", padx=(tema.GAP // 2, 0), ipady=10)

    return acts, btn_start_stop, btn_sync, btn_exit
