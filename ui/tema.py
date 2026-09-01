"""
ui/tema.py — sistema visual do painel (feat/ui-v1).

Paleta por tokens (tema escuro), como no plano aprovado
(`docs/PLANO-PAINEL-v1.md` → "Sistema visual") e no mock
`docs/screenshots/mock-painel-v1.png`.

Regra de cor: fundo e texto são neutros; ACC (roxo) só em acento
(identificador / links); OK/WARN/STOP só em status. Cor nunca decora —
sempre significa alguma coisa. Ref.: High Performance HMI Handbook /
ISA-101 (docs/MELHORIAS.md frente #6).
"""

from tkinter import font

# --- fundo / cartão / linha ---
BG = "#1a1a1a"
BG2 = "#212121"
LINE = "#2e2e2e"
FLD = "#161616"          # fundo de campo de entrada

# --- texto ---
T1 = "#e7e7e7"           # primário
T2 = "#9a9a9a"           # secundário
T3 = "#626262"           # terciário / rótulos

# --- acento (só identificador / links) ---
ACC = "#a68cf5"

# --- semânticas (só status) ---
OK = "#57c08a"
WARN = "#d9a441"
STOP = "#d96a5b"

# --- botões (bg mais escuro que o token de status correspondente) ---
BOTAO_OK = "#2f8f68"
BOTAO_STOP = "#8a3f37"
BOTAO_NEUTRO = "#2c2c2c"
BOTAO_NEUTRO_ATIVO = "#3a3a3a"

# --- espaçamento ---
PAD = 20                 # respiro externo
GAP = 12                 # entre cartões


class Fontes:
    """Precisa de um tk.Tk() já criado (font.Font usa o root corrente)."""

    def __init__(self):
        self.topo = font.Font(family="Helvetica", size=13, weight="bold")
        self.topo_sub = font.Font(family="Helvetica", size=12)
        self.secao = font.Font(family="Helvetica", size=9, weight="bold")
        self.rotulo = font.Font(family="Helvetica", size=11)
        self.rotulo_kv = font.Font(family="Helvetica", size=10)
        self.valor_kv = font.Font(family="Helvetica", size=10, weight="bold")
        self.entrada = font.Font(family="Helvetica", size=11)
        self.numero_medio = font.Font(family="Helvetica", size=26, weight="bold")
        self.numero_grande = font.Font(family="Helvetica", size=52, weight="bold")
        self.legenda = font.Font(family="Helvetica", size=10)
        self.mini = font.Font(family="Helvetica", size=9)
        self.botao = font.Font(family="Helvetica", size=12, weight="bold")


# mapeia analisador_estado (core/status.py) -> (texto, cor)
ESTADO_ANALISADOR = {
    "parado": ("parado", T3),
    "carregando": ("carregando modelo…", WARN),
    "pronto": ("pronto", OK),
    "analisando": ("analisando", OK),
    "erro": ("erro", STOP),
}
