"""
ui/widgets.py — blocos da tela (feat/parcela).

Cada `montar_*` monta um bloco e devolve (frame, dict de widgets que o App
precisa atualizar). Helpers implementam o sistema visual de `ui/tema.py`.
"""

import tkinter as tk

from . import tema


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def cartao(parent):
    return tk.Frame(parent, bg=tema.BG2, highlightbackground=tema.LINE,
                    highlightthickness=1, bd=0)


def titulo_secao(parent, fontes, texto):
    return tk.Label(parent, text=texto.upper(), bg=parent["bg"], fg=tema.T3,
                    font=fontes.secao)


def hairline(parent):
    return tk.Frame(parent, bg=tema.LINE, height=1)


def linha_kv(parent, fontes, chave, valor="", cor=None, largura=15):
    row = tk.Frame(parent, bg=parent["bg"])
    tk.Label(row, text=chave, bg=parent["bg"], fg=tema.T2, font=fontes.rotulo_kv,
             width=largura, anchor="w").pack(side="left")
    lbl = tk.Label(row, text=valor, bg=parent["bg"], fg=cor or tema.T1, font=fontes.valor_kv)
    lbl.pack(side="left")
    return row, lbl


def linha_kv_status(parent, fontes, chave, valor="", cor=None, dotcor=None, largura=15):
    row = tk.Frame(parent, bg=parent["bg"])
    tk.Label(row, text=chave, bg=parent["bg"], fg=tema.T2, font=fontes.rotulo_kv,
             width=largura, anchor="w").pack(side="left")
    lbl_dot = tk.Label(row, text="●", bg=parent["bg"], fg=dotcor or tema.T3, font=fontes.mini)
    lbl_dot.pack(side="left", padx=(0, 5))
    lbl = tk.Label(row, text=valor, bg=parent["bg"], fg=cor or tema.T1, font=fontes.valor_kv)
    lbl.pack(side="left")
    return row, lbl_dot, lbl


# ---------------------------------------------------------------------------
# blocos
# ---------------------------------------------------------------------------
def montar_topo(parent, fontes):
    top = tk.Frame(parent, bg=tema.BG)
    tk.Label(top, text="ROVER FAPA", bg=tema.BG, fg=tema.T1, font=fontes.topo).pack(side="left")
    tk.Label(top, text="  Contador de Plântulas", bg=tema.BG, fg=tema.T2,
             font=fontes.topo_sub).pack(side="left")
    pill = tk.Frame(top, bg=tema.BG)
    pill.pack(side="right")
    dot = tk.Label(pill, text="●", bg=tema.BG, fg=tema.T3, font=fontes.legenda)
    dot.pack(side="left")
    txt = tk.Label(pill, text=" iniciando…", bg=tema.BG, fg=tema.T2, font=fontes.legenda)
    txt.pack(side="left")
    return top, {"dot": dot, "texto": txt}


def montar_amostra(parent, fontes, on_editar_exp, on_anterior, on_proxima):
    """Faixa da amostra: Experimento (+ editar) e Parcela (X/Y/Linha,
    identificador, plot N de M, ◂ / Próxima ▸ F2)."""
    card = cartao(parent)
    inner = tk.Frame(card, bg=tema.BG2)
    inner.pack(fill="x", padx=18, pady=14)

    # --- experimento ---
    r1 = tk.Frame(inner, bg=tema.BG2)
    r1.pack(fill="x")
    titulo_secao(r1, fontes, "Experimento").pack(side="left")
    lbl_exp = tk.Label(r1, text="—", bg=tema.BG2, fg=tema.T1, font=fontes.topo_sub)
    lbl_exp.pack(side="left", padx=(10, 0))
    btn_editar = tk.Label(r1, text="editar", bg=tema.BG2, fg=tema.ACC, font=fontes.link, cursor="hand2")
    btn_editar.pack(side="right")
    btn_editar.bind("<Button-1>", lambda e: on_editar_exp())

    hairline(inner).pack(fill="x", pady=12)

    # --- parcela ---
    r2 = tk.Frame(inner, bg=tema.BG2)
    r2.pack(fill="x")

    esq = tk.Frame(r2, bg=tema.BG2)
    esq.pack(side="left")
    titulo_secao(esq, fontes, "Parcela").pack(anchor="w")
    xyl = tk.Frame(esq, bg=tema.BG2)
    xyl.pack(anchor="w", pady=(4, 0))

    def _cell(rot):
        c = tk.Frame(xyl, bg=tema.BG2)
        tk.Label(c, text=rot, bg=tema.BG2, fg=tema.T3, font=fontes.cell_rotulo).pack()
        v = tk.Label(c, text="–", bg=tema.BG2, fg=tema.T1, font=fontes.cell_valor)
        v.pack()
        return c, v
    c_x, val_x = _cell("X");    c_x.pack(side="left", padx=(0, 14))
    c_y, val_y = _cell("Y");    c_y.pack(side="left", padx=(0, 14))
    c_l, val_linha = _cell("LINHA"); c_l.pack(side="left")

    mid = tk.Frame(r2, bg=tema.BG2)
    mid.pack(side="left", padx=36)
    titulo_secao(mid, fontes, "Identificador").pack(anchor="w")
    lbl_ident = tk.Label(mid, text="—", bg=tema.BG2, fg=tema.ACC, font=fontes.identificador)
    lbl_ident.pack(anchor="w")

    dire = tk.Frame(r2, bg=tema.BG2)
    dire.pack(side="right")
    lbl_plot = tk.Label(dire, text="—", bg=tema.BG2, fg=tema.T2, font=fontes.rotulo_kv)
    lbl_plot.pack(anchor="e", pady=(0, 4))
    nav = tk.Frame(dire, bg=tema.BG2)
    nav.pack(anchor="e")
    btn_ant = tk.Button(nav, text="◂", command=on_anterior, bg=tema.BOTAO_NEUTRO, fg=tema.T1,
                        font=fontes.nav, bd=0, relief="flat", width=3, cursor="hand2",
                        activebackground=tema.BOTAO_NEUTRO_ATIVO, activeforeground=tema.T1)
    btn_ant.pack(side="left", padx=(0, 6))
    btn_prox = tk.Button(nav, text="Próxima ▸  F2", command=on_proxima, bg=tema.BOTAO_NEUTRO,
                         fg=tema.T1, font=fontes.nav, bd=0, relief="flat", cursor="hand2",
                         padx=12, pady=4, activebackground=tema.BOTAO_NEUTRO_ATIVO,
                         activeforeground=tema.T1)
    btn_prox.pack(side="left")

    return card, {
        "lbl_exp": lbl_exp, "val_x": val_x, "val_y": val_y, "val_linha": val_linha,
        "lbl_ident": lbl_ident, "lbl_plot": lbl_plot,
        "btn_ant": btn_ant, "btn_prox": btn_prox,
    }


def montar_contagem(parent, fontes):
    card = cartao(parent)
    inner = tk.Frame(card, bg=tema.BG2)
    inner.pack(fill="both", expand=True, padx=18, pady=16)

    titulo_secao(inner, fontes, "Contagem").pack(anchor="w")
    lbl_total = tk.Label(inner, text="0", bg=tema.BG2, fg=tema.T1, font=fontes.numero_grande)
    lbl_total.pack(pady=(10, 0))
    tk.Label(inner, text="linha atual · corrigido", bg=tema.BG2, fg=tema.T2,
             font=fontes.legenda).pack()

    hairline(inner).pack(fill="x", pady=14)

    row_b, lbl_bruto = linha_kv(inner, fontes, "detecção IA", "--", cor=tema.T2)
    row_b.pack(anchor="w", pady=2)
    row_f, lbl_fila = linha_kv(inner, fontes, "fila", "0", cor=tema.T2)
    row_f.pack(anchor="w", pady=2)

    return card, {"lbl_total": lbl_total, "lbl_bruto": lbl_bruto, "lbl_fila": lbl_fila}


def montar_progresso(parent, fontes):
    """Cartão 'Progresso da parcela': linha 1/2/3 + total do plot."""
    card = cartao(parent)
    inner = tk.Frame(card, bg=tema.BG2)
    inner.pack(fill="both", expand=True, padx=18, pady=16)

    titulo_secao(inner, fontes, "Progresso da parcela").pack(anchor="w")
    tk.Frame(inner, bg=tema.BG2, height=8).pack()

    linhas = []
    for n in (1, 2, 3):
        row = tk.Frame(inner, bg=tema.BG2)
        row.pack(fill="x", pady=5)
        lbl_nome = tk.Label(row, text=f"linha {n}", bg=tema.BG2, fg=tema.T2,
                            font=fontes.rotulo_kv, width=8, anchor="w")
        lbl_nome.pack(side="left")
        tk.Label(row, text="·" * 20, bg=tema.BG2, fg=tema.T3, font=fontes.mini).pack(side="left", padx=6)
        lbl_val = tk.Label(row, text="—", bg=tema.BG2, fg=tema.T3, font=fontes.valor_kv,
                           width=5, anchor="e")
        lbl_val.pack(side="left")
        lbl_atual = tk.Label(row, text="", bg=tema.BG2, fg=tema.OK, font=fontes.mini)
        lbl_atual.pack(side="left", padx=(6, 0))
        linhas.append({"nome": lbl_nome, "val": lbl_val, "atual": lbl_atual})

    hairline(inner).pack(fill="x", pady=(12, 10))
    tot = tk.Frame(inner, bg=tema.BG2)
    tot.pack(fill="x")
    tk.Label(tot, text="total do plot", bg=tema.BG2, fg=tema.T2, font=fontes.rotulo_kv,
             width=13, anchor="w").pack(side="left")
    lbl_total_plot = tk.Label(tot, text="0", bg=tema.BG2, fg=tema.T1, font=fontes.valor_kv)
    lbl_total_plot.pack(side="left")
    tk.Label(tot, text=" corrigido", bg=tema.BG2, fg=tema.T3, font=fontes.mini).pack(side="left")

    return card, {"linhas": linhas, "lbl_total_plot": lbl_total_plot}


def montar_estado_sistema(parent, fontes):
    card = cartao(parent)
    inner = tk.Frame(card, bg=tema.BG2)
    inner.pack(fill="x", padx=18, pady=14)

    titulo_secao(inner, fontes, "Estado do sistema").pack(anchor="w", pady=(0, 10))

    grid = tk.Frame(inner, bg=tema.BG2)
    grid.pack(fill="x")
    grid.columnconfigure(0, weight=1, uniform="s")
    grid.columnconfigure(1, weight=1, uniform="s")
    c0 = tk.Frame(grid, bg=tema.BG2)
    c0.grid(row=0, column=0, sticky="nw")
    c1 = tk.Frame(grid, bg=tema.BG2)
    c1.grid(row=0, column=1, sticky="nw", padx=(24, 0))

    row_cap, dot_cap, val_cap = linha_kv_status(c0, fontes, "captura", "parada",
                                                cor=tema.STOP, dotcor=tema.STOP, largura=11)
    row_cap.pack(anchor="w", pady=2)
    row_an, dot_an, val_an = linha_kv_status(c0, fontes, "analisador", "—",
                                             cor=tema.T3, dotcor=tema.T3, largura=11)
    row_an.pack(anchor="w", pady=2)

    row_s, val_sync = linha_kv(c1, fontes, "última sync", "nunca", largura=12)
    row_s.pack(anchor="w", pady=2)
    row_p, val_pend = linha_kv(c1, fontes, "aguardando sync", "0 arquivos", cor=tema.T2, largura=14)
    row_p.pack(anchor="w", pady=2)

    hairline(inner).pack(fill="x", pady=(12, 8))
    lbl_rodape = tk.Label(inner, text="—", bg=tema.BG2, fg=tema.T3, font=fontes.mini)
    lbl_rodape.pack(anchor="w")

    return card, {
        "dot_captura": dot_cap, "val_captura": val_cap,
        "dot_analisador": dot_an, "val_analisador": val_an,
        "val_sync": val_sync, "val_pend": val_pend, "lbl_rodape": lbl_rodape,
    }


def montar_acoes(parent, fontes, on_toggle_capture, on_sync):
    acts = tk.Frame(parent, bg=tema.BG)
    acts.columnconfigure(0, weight=3, uniform="a")
    acts.columnconfigure(1, weight=2, uniform="a")

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
    btn_sync.grid(row=0, column=1, sticky="ew", padx=(tema.GAP // 2, 0), ipady=10)

    return acts, btn_start_stop, btn_sync
