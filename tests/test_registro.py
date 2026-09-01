"""
Testes de core/registro.py — CSV canônico de análise.
"""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from core import registro


def test_garantir_csv_cria_cabecalho(tmp_path):
    p = str(tmp_path / "log.csv")
    assert registro.garantir_csv(p) is None
    with open(p, newline="", encoding="utf-8") as f:
        assert next(csv.reader(f)) == registro.CABECALHO


def test_garantir_csv_ja_canonico_nao_mexe(tmp_path):
    p = str(tmp_path / "log.csv")
    registro.garantir_csv(p)
    registro.registrar_analise(p, parcela="X1Y1L1", plantulas_corrigido=5)
    assert registro.garantir_csv(p) is None          # não arquivou
    assert len(registro.ler(p)) == 1                  # dado preservado


def test_garantir_csv_arquiva_formato_antigo(tmp_path):
    p = str(tmp_path / "log.csv")
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp_analise", "setor_imagem", "plantulas_ajustadas"])
        w.writerow(["2026-01-01", "lote_1", "5"])

    arquivado = registro.garantir_csv(p)

    assert arquivado and os.path.exists(arquivado)
    assert "lote_1" in open(arquivado).read()
    with open(p, newline="", encoding="utf-8") as f:
        assert next(csv.reader(f)) == registro.CABECALHO


def test_registrar_analise_preenche_faltantes_com_vazio(tmp_path):
    p = str(tmp_path / "log.csv")
    registro.garantir_csv(p)
    registro.registrar_analise(p, experimento="E", parcela="X3Y7L2",
                               X=3, Y=7, linha=2, plantulas_corrigido=15)
    d = registro.ler(p)[0]
    assert d["parcela"] == "X3Y7L2"
    assert d["plantulas_corrigido"] == "15"
    assert d["incerteza"] == ""          # reservado p/ RV-08
    assert d["sha256_imagem"] == ""


def test_ler_pula_linhas_sem_parcela(tmp_path):
    p = str(tmp_path / "log.csv")
    registro.garantir_csv(p)
    registro.registrar_analise(p, parcela="X1Y1L1", plantulas_corrigido=1)
    registro.registrar_analise(p, parcela="", plantulas_corrigido=99)   # lixo
    assert [d["plantulas_corrigido"] for d in registro.ler(p)] == ["1"]


def test_sha256_arquivo(tmp_path):
    f = tmp_path / "img.jpg"
    f.write_bytes(b"conteudo")
    h = registro.sha256_arquivo(str(f))
    assert len(h) == 64
    assert registro.sha256_arquivo("/nao/existe") == ""
