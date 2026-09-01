"""
exportar_planilha.py — preenche as colunas linha 1/2/3 da planilha da
semeadora com a contagem corrigida do rover e salva uma cópia.

Uso (no fim da campanha):

    python exportar_planilha.py
    python exportar_planilha.py --experimento "Antecipado Pinhão 2025"
    python exportar_planilha.py --planilha outra.xlsx --saida resultado.xlsx

Sem --saida, gera `export_<AAAAMMDD-HHMM>.xlsx` na raiz do projeto.
"""

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from core import export
from core import eventos


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", default=config.ARQUIVO_CSV, help="CSV canônico de análise")
    p.add_argument("--planilha", default=config.PLANILHA_PROGRAMACAO,
                   help="planilha de programação da semeadora (.csv ou .xlsx)")
    p.add_argument("--saida", default=None, help="arquivo de saída (.xlsx ou .csv)")
    p.add_argument("--experimento", default=None, help="filtrar por nome do experimento")
    args = p.parse_args(argv)

    ext = os.path.splitext(args.planilha)[1].lower() or ".xlsx"
    saida = args.saida or os.path.join(
        config.BASE_DIR, f"export_{datetime.now():%Y%m%d-%H%M}{ext}")

    try:
        caminho, n = export.exportar(saida, caminho_csv=args.csv,
                                     caminho_planilha=args.planilha,
                                     experimento=args.experimento)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERRO: {e}")
        return 1

    print(f"OK: {n} plot(s) preenchido(s) -> {caminho}")
    eventos.registrar("planilha_exportada", saida=os.path.basename(caminho),
                      plots=n, experimento=args.experimento or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
