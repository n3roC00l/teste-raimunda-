import tkinter as tk
from tkinter import font

# ---------------- sistema visual ----------------
BG   = "#1a1a1a"   # fundo
BG2  = "#212121"   # cartão
LINE = "#2e2e2e"   # hairline
T1   = "#e7e7e7"   # texto primário
T2   = "#9a9a9a"   # secundário
T3   = "#626262"   # terciário / labels
ACC  = "#a68cf5"   # acento — só o identificador
OK   = "#57c08a"
WARN = "#d9a441"
STOP = "#d96a5b"
FLD  = "#161616"   # campo de input

PAD = 20           # respiro externo dos cartões
GAP = 12           # espaço entre cartões

root = tk.Tk()
root.title("Rover FAPA — Contador de Plântulas")
root.geometry("900x726")
root.minsize(820, 580)
root.configure(bg=BG)

def f(size, w="normal"):  return font.Font(family="DejaVu Sans", size=size, weight=w)
def fm(size, w="normal"): return font.Font(family="DejaVu Sans Mono", size=size, weight=w)

def sect(parent, texto):
    return tk.Label(parent, text=texto.upper(), bg=parent["bg"], fg=T3,
                    font=f(8, "bold"))

def card(parent):
    return tk.Frame(parent, bg=BG2, highlightbackground=LINE,
                    highlightthickness=1, bd=0)

def kv(parent, chave, valor, cor=T1, dotcor=None):
    """linha chave -> valor alinhada"""
    row = tk.Frame(parent, bg=parent["bg"])
    tk.Label(row, text=chave, bg=parent["bg"], fg=T2, font=f(10),
             width=13, anchor="w").pack(side="left")
    if dotcor:
        tk.Label(row, text="● ", bg=parent["bg"], fg=dotcor, font=f(9)).pack(side="left")
    tk.Label(row, text=valor, bg=parent["bg"], fg=cor, font=f(10, "bold")).pack(side="left")
    return row

# ================= TOPO =================
top = tk.Frame(root, bg=BG)
top.pack(fill="x", padx=PAD, pady=(16, 10))
tk.Label(top, text="ROVER FAPA", bg=BG, fg=T1, font=f(12, "bold")).pack(side="left")
tk.Label(top, text="  Contador de Plântulas", bg=BG, fg=T2, font=f(12)).pack(side="left")
pill = tk.Frame(top, bg=BG); pill.pack(side="right")
tk.Label(pill, text="●", bg=BG, fg=OK, font=f(10)).pack(side="left")
tk.Label(pill, text=" sistema pronto", bg=BG, fg=T2, font=f(10)).pack(side="left")

# ================= FAIXA DA AMOSTRA =================
amostra = card(root)
amostra.pack(fill="x", padx=PAD, pady=(0, GAP))
inner = tk.Frame(amostra, bg=BG2); inner.pack(fill="x", padx=18, pady=14)

# linha 1 — experimento
r1 = tk.Frame(inner, bg=BG2); r1.pack(fill="x")
sect(r1, "Experimento").pack(side="left")
tk.Label(r1, text="  Antecipado Pinhão 2025", bg=BG2, fg=T1,
         font=f(12, "bold")).pack(side="left")
tk.Label(r1, text="editar", bg=BG2, fg=ACC, font=f(9)).pack(side="right")

tk.Frame(inner, bg=LINE, height=1).pack(fill="x", pady=12)

# linha 2 — parcela atual
r2 = tk.Frame(inner, bg=BG2); r2.pack(fill="x")

esq = tk.Frame(r2, bg=BG2); esq.pack(side="left")
sect(esq, "Parcela").pack(anchor="w")
xyl = tk.Frame(esq, bg=BG2); xyl.pack(anchor="w", pady=(4, 0))
def cell(parent, rot, val):
    c = tk.Frame(parent, bg=BG2)
    tk.Label(c, text=rot, bg=BG2, fg=T3, font=f(8, "bold")).pack()
    tk.Label(c, text=val, bg=BG2, fg=T1, font=f(16, "bold")).pack()
    return c
cell(xyl, "X", "3").pack(side="left", padx=(0, 14))
cell(xyl, "Y", "7").pack(side="left", padx=(0, 14))
cell(xyl, "LINHA", "2").pack(side="left")

mid = tk.Frame(r2, bg=BG2); mid.pack(side="left", padx=40)
sect(mid, "Identificador").pack(anchor="w")
tk.Label(mid, text="X3Y7L2", bg=BG2, fg=ACC, font=fm(22, "bold")).pack(anchor="w")

dire = tk.Frame(r2, bg=BG2); dire.pack(side="right")
tk.Label(dire, text="plot 47 de 216", bg=BG2, fg=T2, font=f(10)).pack(anchor="e", pady=(0, 4))
nav = tk.Frame(dire, bg=BG2); nav.pack(anchor="e")
tk.Button(nav, text="◂", bg="#2c2c2c", fg=T1, font=f(11, "bold"), bd=0,
          relief="flat", width=3, cursor="hand2").pack(side="left", padx=(0, 6))
tk.Button(nav, text="Próxima  ▸    F2", bg="#2c2c2c", fg=T1, font=f(10, "bold"),
          bd=0, relief="flat", cursor="hand2", padx=12, pady=4).pack(side="left")

# ================= ÁREA PRINCIPAL — 2 COLUNAS =================
mainarea = tk.Frame(root, bg=BG)
mainarea.pack(fill="both", expand=True, padx=PAD)
mainarea.columnconfigure(0, weight=1, uniform="m")
mainarea.columnconfigure(1, weight=1, uniform="m")

# --- CONTAGEM ---
cc = card(mainarea); cc.grid(row=0, column=0, sticky="nsew", padx=(0, GAP // 2), pady=0)
ci = tk.Frame(cc, bg=BG2); ci.pack(fill="both", expand=True, padx=18, pady=16)
sect(ci, "Contagem").pack(anchor="w")
tk.Label(ci, text="128", bg=BG2, fg=T1, font=f(58, "bold")).pack(pady=(14, 0))
tk.Label(ci, text="plântulas · corrigido", bg=BG2, fg=T2, font=f(10)).pack()
tk.Frame(ci, bg=LINE, height=1).pack(fill="x", pady=16)
kv(ci, "detecção IA", "137").pack(anchor="w", pady=2)
kv(ci, "fila", "3 a analisar", cor=WARN).pack(anchor="w", pady=2)

# --- PROGRESSO DA PARCELA ---
pc = card(mainarea); pc.grid(row=0, column=1, sticky="nsew", padx=(GAP // 2, 0))
pi = tk.Frame(pc, bg=BG2); pi.pack(fill="both", expand=True, padx=18, pady=16)
sect(pi, "Progresso da parcela").pack(anchor="w")
tk.Frame(pi, bg=BG2, height=8).pack()

def linha_row(nome, valor, atual=False):
    row = tk.Frame(pi, bg=BG2); row.pack(fill="x", pady=5)
    tk.Label(row, text=nome, bg=BG2, fg=(T1 if atual else T2),
             font=f(11, "bold" if atual else "normal"), width=8, anchor="w").pack(side="left")
    tk.Label(row, text="·" * 22, bg=BG2, fg=T3, font=f(9)).pack(side="left", padx=6)
    tk.Label(row, text=valor, bg=BG2, fg=(T1 if valor != "—" else T3),
             font=f(12, "bold"), width=4, anchor="e").pack(side="left")
    if atual:
        tk.Label(row, text="  ● atual", bg=BG2, fg=OK, font=f(8)).pack(side="left")

linha_row("linha 1", "41")
linha_row("linha 2", "15", atual=True)
linha_row("linha 3", "—")
tk.Frame(pi, bg=LINE, height=1).pack(fill="x", pady=(12, 10))
tot = tk.Frame(pi, bg=BG2); tot.pack(fill="x")
tk.Label(tot, text="total do plot", bg=BG2, fg=T2, font=f(10), width=13, anchor="w").pack(side="left")
tk.Label(tot, text="56", bg=BG2, fg=T1, font=f(13, "bold")).pack(side="left")
tk.Label(tot, text=" corrigido", bg=BG2, fg=T3, font=f(9)).pack(side="left")

# ================= ESTADO DO SISTEMA =================
sc = card(root); sc.pack(fill="x", padx=PAD, pady=(GAP, GAP))
si = tk.Frame(sc, bg=BG2); si.pack(fill="x", padx=18, pady=14)
sect(si, "Estado do sistema").pack(anchor="w", pady=(0, 8))
grid = tk.Frame(si, bg=BG2); grid.pack(fill="x")
grid.columnconfigure(0, weight=1, uniform="s"); grid.columnconfigure(1, weight=1, uniform="s")
c0 = tk.Frame(grid, bg=BG2); c0.grid(row=0, column=0, sticky="w")
c1 = tk.Frame(grid, bg=BG2); c1.grid(row=0, column=1, sticky="w")
kv(c0, "captura",    "parada",   cor=STOP, dotcor=STOP).pack(anchor="w", pady=2)
kv(c0, "analisador", "pronto",   cor=OK,   dotcor=OK).pack(anchor="w", pady=2)
kv(c1, "última sync", "14:32").pack(anchor="w", pady=2)
kv(c1, "pendentes",   "8 arquivos", cor=WARN).pack(anchor="w", pady=2)
tk.Frame(si, bg=LINE, height=1).pack(fill="x", pady=(10, 8))
tk.Label(si, text="CPU 51 °C     ·     Disco 12 GB livres     ·     v2.1",
         bg=BG2, fg=T3, font=f(9)).pack(anchor="w")

# ================= AÇÕES =================
acts = tk.Frame(root, bg=BG); acts.pack(fill="x", padx=PAD, pady=(0, 16))
acts.columnconfigure(0, weight=3, uniform="a")
acts.columnconfigure(1, weight=2, uniform="a")
b1 = tk.Button(acts, text="▶   Iniciar captura                    F5",
               bg="#2f8f68", fg="white", font=f(12, "bold"), bd=0, relief="flat",
               activebackground=OK, cursor="hand2")
b1.grid(row=0, column=0, sticky="ew", padx=(0, GAP // 2), ipady=10)
b2 = tk.Button(acts, text="☁   Sincronizar          F9",
               bg="#2c2c2c", fg=T1, font=f(12, "bold"), bd=0, relief="flat",
               activebackground="#3a3a3a", cursor="hand2")
b2.grid(row=0, column=1, sticky="ew", padx=(GAP // 2, 0), ipady=10)

root.after(400, lambda: None)
root.mainloop()
