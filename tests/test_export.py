"""
Testes de core/export.py — preenche linha 1/2/3 da planilha da semeadora.
"""

import csv
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from core import registro, export

_EXEMPLOS = os.path.join(os.path.dirname(__file__), "..", "docs", "exemplos")
_CSV_PLAN = os.path.join(_EXEMPLOS, "programacao-semeadora-exemplo.csv")
_XLSX_PLAN = os.path.join(_EXEMPLOS, "programacao-semeadora-exemplo.xlsx")


@pytest.fixture
def csv_analise(tmp_path):
    p = str(tmp_path / "log_analise_total.csv")
    registro.garantir_csv(p)
    # X3Y7: linha 1 = 40+42, linha 2 = 15 ; X1Y1: linha 1 = 10 ; exp diferente
    dados = [
        ("Antecipado Pinhão 2025", "X3Y7L1", 3, 7, 1, 40),
        ("Antecipado Pinhão 2025", "X3Y7L1", 3, 7, 1, 42),
        ("Antecipado Pinhão 2025", "X3Y7L2", 3, 7, 2, 15),
        ("Antecipado Pinhão 2025", "X1Y1L1", 1, 1, 1, 10),
        ("Outro Ensaio",           "X1Y1L1", 1, 1, 1, 999),
    ]
    for exp, parc, x, y, ln, corr in dados:
        registro.registrar_analise(p, experimento=exp, parcela=parc, X=x, Y=y,
                                   linha=ln, plantulas_corrigido=corr)
    return p


def test_agregar_por_linha(csv_analise):
    ag = export.agregar_por_linha(csv_analise)
    assert ag[(3, 7)] == {1: 82, 2: 15, 3: 0}
    assert ag[(1, 1)] == {1: 1009, 2: 0, 3: 0}    # soma os dois experimentos


def test_agregar_filtra_por_experimento(csv_analise):
    ag = export.agregar_por_linha(csv_analise, experimento="Antecipado Pinhão 2025")
    assert ag[(1, 1)] == {1: 10, 2: 0, 3: 0}       # sem o "Outro Ensaio"


def test_exportar_csv_preenche_colunas(csv_analise, tmp_path):
    saida = str(tmp_path / "export.csv")
    caminho, n = export.exportar(saida, caminho_csv=csv_analise,
                                 caminho_planilha=_CSV_PLAN,
                                 experimento="Antecipado Pinhão 2025")
    assert n == 2  # X3Y7 e X1Y1
    with open(caminho, newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    x3y7 = next(d for d in linhas
                if d["Parcela Larg. (X)"] == "3" and d["Parcela Compr.(Y)"] == "7")
    assert x3y7["linha 1"] == "82"
    assert x3y7["linha 2"] == "15"
    assert x3y7["linha 3"] == ""          # 0 -> não escreve
    # linhas sem contagem ficam intocadas
    outra = next(d for d in linhas
                 if d["Parcela Larg. (X)"] == "5" and d["Parcela Compr.(Y)"] == "5")
    assert outra["linha 1"] == ""


def test_exportar_xlsx_preenche_e_preserva_planilha(csv_analise, tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    saida = str(tmp_path / "export.xlsx")
    _, n = export.exportar(saida, caminho_csv=csv_analise, caminho_planilha=_XLSX_PLAN,
                           experimento="Antecipado Pinhão 2025")
    assert n == 2
    wb = openpyxl.load_workbook(saida)
    assert "Plan1" in wb.sheetnames and "Planilha1" in wb.sheetnames  # abas preservadas
    ws = wb["Plan1"]
    achou = False
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[1] == 3 and row[0] == 7:
            assert row[9] == 82 and row[10] == 15
            achou = True
    assert achou


def test_exportar_sem_planilha_levanta(csv_analise, tmp_path):
    with pytest.raises(FileNotFoundError):
        export.exportar(str(tmp_path / "x.csv"), caminho_csv=csv_analise,
                        caminho_planilha=str(tmp_path / "nao_existe.csv"))
