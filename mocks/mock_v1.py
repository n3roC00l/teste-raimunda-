import tkinter as tk
from tkinter import font

# ---- paleta (tema escuro) ----
BG      = "#1e1e1e"
CARD    = "#262626"
CARD_BD = "#333333"
TXT     = "#dcdcdc"
MUT     = "#8a8a8a"
FAINT   = "#5f5f5f"
GREEN   = "#4bbd8a"
AMBER   = "#e0a52b"
RED     = "#e0685b"
BLUE    = "#3f7fb0"
BLUE_BG = "#2f6f9e"
GREEN_BG= "#2f8f68"
ACCENT  = "#a68cf5"

root = tk.Tk()
root.title("Estação de Captura — Rover FAPA")
root.geometry("860x650")
root.minsize(780, 600)
root.configure(bg=BG)

F  = lambda s,w="normal": font.Font(family="DejaVu Sans", size=s, weight=w)
FM = lambda s,w="normal": font.Font(family="DejaVu Sans Mono", size=s, weight=w)

def card(parent, titulo):
    outer = tk.Frame(parent, bg=CARD, highlightbackground=CARD_BD,
                     highlightthickness=1, bd=0)
    tk.Label(outer, text=titulo, bg=CARD, fg=MUT, font=F(9, "bold"),
             anchor="w").pack(fill="x", padx=14, pady=(10, 0))
    body = tk.Frame(outer, bg=CARD)
    body.pack(fill="both", expand=True, padx=14, pady=(4, 12))
    return outer, body

def dot(parent, cor, texto, fnt=None):
    fr = tk.Frame(parent, bg=parent["bg"])
    tk.Label(fr, text="●", bg=parent["bg"], fg=cor, font=F(10)).pack(side="left")
    tk.Label(fr, text=" " + texto, bg=parent["bg"], fg=TXT,
             font=fnt or F(10)).pack(side="left")
    return fr

# ===== cabeçalho =====
hdr = tk.Frame(root, bg=BG)
hdr.pack(fill="x", padx=16, pady=(14, 8))
tk.Label(hdr, text="Estação de Captura —", bg=BG, fg=TXT,
         font=F(13, "bold")).pack(side="left")
exp = tk.Entry(hdr, width=24, font=F(12, "bold"), relief="solid", bd=0,
               bg="#1a1a1a", fg=ACCENT, insertbackground=TXT,
               highlightbackground=CARD_BD, highlightthickness=1)
exp.insert(0, "Antecipado Pinhão 2025")
exp.pack(side="left", padx=8, ipady=3)
tk.Label(hdr, text="✎ nome do experimento", bg=BG, fg=FAINT, font=F(8)).pack(side="left")
tk.Label(hdr, text="v2.1", bg=BG, fg=FAINT, font=FM(10)).pack(side="right")

# ===== linha 1: CONTAGEM | EXPERIMENTO =====
row1 = tk.Frame(root, bg=BG)
row1.pack(fill="x", padx=16)
row1.columnconfigure(0, weight=1, uniform="a")
row1.columnconfigure(1, weight=1, uniform="a")

# -- Contagem --
c_out, c = card(row1, "CONTAGEM")
c_out.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=4)
tk.Label(c, text="128", bg=CARD, fg=GREEN, font=F(54, "bold")).pack(anchor="center", pady=(6, 0))
tk.Label(c, text="corrigido", bg=CARD, fg=MUT, font=F(10)).pack(anchor="center")
tk.Frame(c, bg=CARD_BD, height=1).pack(fill="x", pady=10)
row = tk.Frame(c, bg=CARD); row.pack(anchor="w")
tk.Label(row, text="bruto: ", bg=CARD, fg=MUT, font=F(10)).pack(side="left")
tk.Label(row, text="137", bg=CARD, fg=TXT, font=F(10, "bold")).pack(side="left")
row = tk.Frame(c, bg=CARD); row.pack(anchor="w", pady=(4, 0))
tk.Label(row, text="parcela: ", bg=CARD, fg=MUT, font=F(10)).pack(side="left")
tk.Label(row, text="12", bg=CARD, fg=TXT, font=F(10, "bold")).pack(side="left")
tk.Label(row, text="  ·  ", bg=CARD, fg=FAINT, font=F(10)).pack(side="left")
tk.Label(row, text="15", bg=CARD, fg=GREEN, font=F(10, "bold")).pack(side="left")
tk.Label(row, text=" (corr.)", bg=CARD, fg=MUT, font=F(9)).pack(side="left")
dot(c, AMBER, "fila: 3 imagens a analisar").pack(anchor="w", pady=(8, 0))

# -- Experimento / Parcela --
e_out, e = card(row1, "PARCELA")
e_out.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=4)

xy = tk.Frame(e, bg=CARD); xy.pack(anchor="w", pady=(6, 0))
def numfield(parent, rot, val):
    tk.Label(parent, text=rot, bg=CARD, fg=MUT, font=F(11)).pack(side="left", padx=(0, 4))
    ent = tk.Entry(parent, width=4, font=F(14, "bold"), justify="center", relief="solid", bd=0,
                   bg="#1a1a1a", fg=TXT, insertbackground=TXT,
                   highlightbackground=CARD_BD, highlightthickness=1)
    ent.insert(0, val); ent.pack(side="left", padx=(0, 16), ipady=3)
numfield(xy, "X", "3")
numfield(xy, "Y", "7")

lin = tk.Frame(e, bg=CARD); lin.pack(anchor="w", pady=(10, 0))
tk.Label(lin, text="Linha", bg=CARD, fg=MUT, font=F(11)).pack(side="left", padx=(0, 8))
for n in (1, 2, 3):
    on = (n == 2)
    tk.Label(lin, text=f" {n} ", font=F(12, "bold"),
             bg=(ACCENT if on else "#1a1a1a"), fg=("white" if on else MUT),
             padx=6, pady=3, relief="solid", bd=0,
             highlightbackground=CARD_BD, highlightthickness=1).pack(side="left", padx=2)

tk.Frame(e, bg=CARD_BD, height=1).pack(fill="x", pady=12)
tk.Label(e, text="setor gerado", bg=CARD, fg=MUT, font=F(9)).pack(anchor="w")
tk.Label(e, text="X3Y7L2", bg=CARD, fg=ACCENT, font=FM(16, "bold")).pack(anchor="w", pady=(2, 0))
tk.Label(e, text="plot 47 de 216   ·   Antecipado Pinhão 2025", bg=CARD, fg=MUT, font=F(9)).pack(anchor="w", pady=(2, 8))
nav = tk.Frame(e, bg=CARD); nav.pack(anchor="w")
tk.Button(nav, text="◂", bg="#333333", fg=TXT, font=F(12, "bold"), bd=0, relief="flat",
          width=3, cursor="hand2").pack(side="left", padx=(0, 6))
tk.Button(nav, text="Próxima  ▸   (F2)", bg="#3a3a3a", fg=TXT, font=F(11, "bold"), bd=0,
          relief="flat", cursor="hand2", padx=10, pady=4).pack(side="left")
tk.Label(e, text="↳ RV-02 — carrega a planilha da semeadora e anda linha 1→2→3 → próximo plot",
         bg=CARD, fg=FAINT, font=F(8)).pack(anchor="w", pady=(8, 0))

# ===== linha 2: ESTADO DO SISTEMA =====
s_out, s = card(root, "ESTADO DO SISTEMA")
s_out.pack(fill="x", padx=16, pady=(10, 4))
r = tk.Frame(s, bg=CARD); r.pack(fill="x", pady=(6, 2))
dot(r, GREEN, "Analisador: Pronto", F(10, "bold")).pack(side="left")
dot(r, GREEN, "Câmera: OK").pack(side="left", padx=(28, 0))
r = tk.Frame(s, bg=CARD); r.pack(fill="x", pady=2)
tk.Label(r, text="Última sincronização: ", bg=CARD, fg=MUT, font=F(10)).pack(side="left")
tk.Label(r, text="14:32", bg=CARD, fg=TXT, font=F(10)).pack(side="left")
tk.Label(r, text="  ·  8 arquivos pendentes de subir", bg=CARD, fg=AMBER, font=F(10)).pack(side="left")
r = tk.Frame(s, bg=CARD); r.pack(fill="x", pady=2)
tk.Label(r, text="CPU 51 °C", bg=CARD, fg=TXT, font=F(10)).pack(side="left")
tk.Label(r, text="   ·   ", bg=CARD, fg=FAINT, font=F(10)).pack(side="left")
tk.Label(r, text="Disco: 12 GB livres", bg=CARD, fg=TXT, font=F(10)).pack(side="left")

# ===== linha 3: ações =====
acts = tk.Frame(root, bg=BG)
acts.pack(fill="x", padx=16, pady=(10, 6))
acts.columnconfigure(0, weight=3, uniform="b")
acts.columnconfigure(1, weight=2, uniform="b")
tk.Button(acts, text="▶  INICIAR CAPTURA   (F5)", bg=GREEN_BG, fg="white",
          font=F(12, "bold"), bd=0, relief="flat", activebackground=GREEN,
          height=2, cursor="hand2").grid(row=0, column=0, sticky="ew", padx=(0, 6), ipady=4)
tk.Button(acts, text="☁  SINCRONIZAR  (F9)", bg=BLUE_BG, fg="white",
          font=F(12, "bold"), bd=0, relief="flat", activebackground=BLUE,
          height=2, cursor="hand2").grid(row=0, column=1, sticky="ew", padx=(6, 0), ipady=4)

# ===== barra de status =====
bar = tk.Frame(root, bg="#161616")
bar.pack(fill="x", side="bottom")
inner = tk.Frame(bar, bg="#161616"); inner.pack(fill="x", padx=14, pady=4)
for cor, txt in [(GREEN, "Analisador pronto"), (GREEN, "Wi-Fi"), (GREEN, "Disco OK")]:
    d = dot(inner, cor, txt, F(9)); d.configure(bg="#161616")
    for w in d.winfo_children(): w.configure(bg="#161616")
    d.pack(side="left", padx=(0, 16))
tk.Label(inner, text="Ctrl+Q  sair", bg="#161616", fg=FAINT, font=FM(9)).pack(side="right")

root.after(400, lambda: None)
root.mainloop()
