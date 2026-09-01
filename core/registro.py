"""
core/registro.py — o CSV canônico de análise (`log_analise_total.csv`).

Cabeçalho **tidy**: uma variável por coluna (Wickham 2014). Antes o CSV
misturava campos (`setor_imagem` = tudo junto) e tinha 11 formatos + 97
linhas vazias no histórico — era dado de teste. Aqui:

- `parcela` = identificador cru (`X3Y7L2`); `X`/`Y`/`linha` = decompostos
  (para pivotar direto nas colunas `linha 1/2/3` da planilha da semeadora);
- `plantulas_bruto` (IA) e `plantulas_corrigido` (após correção);
- `incerteza` — reservado para RV-08 (curva de calibração); em branco por ora;
- `sha256_imagem`, `versao_modelo`, `versao_software` — rastreabilidade
  (qual código/modelo/foto gerou cada número).

`garantir_csv()` arquiva um CSV de formato antigo e começa limpo.

Ref.: Wickham "Tidy Data" (2014); Broman & Woo (2018). docs/MELHORIAS.md #2 / RV-06.
"""

from __future__ import annotations

import csv
import hashlib
import os
from datetime import datetime

CABECALHO = [
    "experimento", "parcela", "X", "Y", "linha",
    "timestamp_imagem", "timestamp_analise",
    "plantulas_bruto", "plantulas_corrigido", "incerteza",
    "nome_imagem", "sha256_imagem", "versao_modelo", "versao_software",
]


def _escrever_cabecalho(caminho):
    pasta = os.path.dirname(caminho) or "."
    os.makedirs(pasta, exist_ok=True)
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(CABECALHO)


def garantir_csv(caminho):
    """Garante que o CSV existe com o cabeçalho canônico.

    Se já existir com OUTRO cabeçalho (formato antigo), renomeia para
    `*.legado-<timestamp>.csv` e cria um novo limpo. Retorna o caminho do
    arquivo arquivado, ou None se nada foi arquivado.
    """
    if not os.path.exists(caminho):
        _escrever_cabecalho(caminho)
        return None
    try:
        with open(caminho, newline="", encoding="utf-8") as f:
            primeira = next(csv.reader(f), [])
    except OSError:
        return None
    if primeira == CABECALHO:
        return None
    base, ext = os.path.splitext(caminho)
    arquivado = f"{base}.legado-{datetime.now():%Y%m%d-%H%M%S}{ext}"
    os.rename(caminho, arquivado)
    _escrever_cabecalho(caminho)
    return arquivado


def sha256_arquivo(caminho):
    try:
        h = hashlib.sha256()
        with open(caminho, "rb") as f:
            for bloco in iter(lambda: f.read(65536), b""):
                h.update(bloco)
        return h.hexdigest()
    except OSError:
        return ""


def registrar_analise(caminho, **campos):
    """Anexa uma linha ao CSV canônico. `campos` são nomes de `CABECALHO`;
    o que faltar entra vazio."""
    with open(caminho, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([campos.get(c, "") for c in CABECALHO])


def ler(caminho):
    """Lê o CSV canônico como lista de dicts (linhas sem `parcela` são puladas)."""
    try:
        with open(caminho, newline="", encoding="utf-8") as f:
            return [d for d in csv.DictReader(f) if (d.get("parcela") or "").strip()]
    except FileNotFoundError:
        return []
