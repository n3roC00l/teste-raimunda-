"""
core/eventos.py — log de eventos append-only (JSONL).

Uma linha JSON por evento, nunca sobrescreve. Serve para reconstruir o que
aconteceu numa campanha (início/fim de captura, avanço de parcela, erros,
sincronização) — inclusive depois de um corte de energia.

`registrar()` NUNCA levanta: um log de evento não pode derrubar o processo.

Ref.: The Twelve-Factor App, fator XI ("logs as event streams").
docs/MELHORIAS.md frente #3.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

_lock = threading.Lock()


def registrar(evento, **dados):
    """Anexa uma linha ao log de eventos. Silencioso em qualquer erro de I/O."""
    linha = {"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "evento": evento}
    linha.update(dados)
    try:
        pasta = os.path.dirname(config.ARQUIVO_EVENTOS) or "."
        os.makedirs(pasta, exist_ok=True)
        with _lock, open(config.ARQUIVO_EVENTOS, "a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
            f.flush()
    except Exception:
        pass


def ler(caminho=None, limite=None):
    """Lê os eventos como lista de dicts. `limite` = só os últimos N.
    Linhas corrompidas são ignoradas."""
    caminho = caminho or config.ARQUIVO_EVENTOS
    try:
        with open(caminho, encoding="utf-8") as f:
            linhas = f.readlines()
    except FileNotFoundError:
        return []
    eventos = []
    for ln in linhas:
        ln = ln.strip()
        if not ln:
            continue
        try:
            eventos.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return eventos[-limite:] if limite else eventos
