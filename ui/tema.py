"""
ui/tema.py — cores e fontes do painel.

`refactor/ui-split` só move código: as cores e fontes aqui são as MESMAS do
`painel_controle.py` original, extraídas para um lugar só. A paleta nova
por tokens (`BG`/`ACC`/`OK`/`WARN`/`STOP`, ver o mock em
`docs/screenshots/mock-painel-v1.png`) entra em `feat/ui-v1` — não aqui.

Ver docs/MELHORIAS.md frentes #6 e #7.
"""

from tkinter import font

# --- cores (hex idênticos ao original) ---
FUNDO = "#f4f4f4"
BRANCO = "#ffffff"
BRANCO_TEXTO = "white"
VERDE = "#4CAF50"
AZUL = "#2196F3"
CINZA_SAIR = "#607D8B"
VERMELHO = "#F44336"
CINZA_DESABILITADO = "#9E9E9E"
CINZA_TEXTO = "#555555"
CINZA_ESCURO = "#333333"
SEPARADOR_1 = "#e0e0e0"
SEPARADOR_2 = "#cccccc"


class Fontes:
    """Precisa de um tk.Tk() já criado (font.Font usa o root corrente)."""

    def __init__(self):
        self.titulo = font.Font(family="Helvetica", size=12, weight="bold")
        self.label = font.Font(family="Helvetica", size=11)
        self.entrada = font.Font(family="Helvetica", size=11)
        self.numero_medio = font.Font(family="Helvetica", size=32, weight="bold")
        self.numero_grande = font.Font(family="Helvetica", size=64, weight="bold")
        self.botao = font.Font(family="Helvetica", size=12, weight="bold")
        # No original eram dois font.Font(14, bold) distintos ("TOTAL
        # ACUMULADO:" e "Fotos Capturadas:") — mesma especificação, uma só
        # instância aqui (sem diferença visual).
        self.rotulo_forte = font.Font(family="Helvetica", size=14, weight="bold")
        self.valor_operacao = font.Font(family="Helvetica", size=11, weight="bold")
