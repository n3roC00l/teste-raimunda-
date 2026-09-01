"""
Testes de core/io_atomico.py — escrita atômica.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import io_atomico


def test_escrever_texto(tmp_path):
    p = str(tmp_path / "sub" / "setor.txt")   # cria o diretório
    io_atomico.escrever_texto(p, "X3Y7L2")
    assert open(p).read() == "X3Y7L2"


def test_escrever_json(tmp_path):
    p = str(tmp_path / "d.json")
    io_atomico.escrever_json(p, {"a": 1, "parcela": "X1Y1L1"})
    assert json.load(open(p)) == {"a": 1, "parcela": "X1Y1L1"}


def test_sobrescreve(tmp_path):
    p = str(tmp_path / "x.txt")
    io_atomico.escrever_texto(p, "antigo")
    io_atomico.escrever_texto(p, "novo")
    assert open(p).read() == "novo"


def test_nao_deixa_temporarios_orfaos(tmp_path):
    p = str(tmp_path / "x.txt")
    for i in range(5):
        io_atomico.escrever_texto(p, str(i))
    restos = [f for f in os.listdir(tmp_path) if f.startswith(".tmp_")]
    assert restos == []


def test_erro_de_escrita_nao_deixa_lixo(tmp_path, monkeypatch):
    p = str(tmp_path / "x.txt")
    io_atomico.escrever_texto(p, "ok")

    real_replace = os.replace

    def falha(src, dst):
        raise OSError("disco cheio")

    monkeypatch.setattr(os, "replace", falha)
    try:
        io_atomico.escrever_texto(p, "novo")
        assert False
    except OSError:
        pass
    monkeypatch.setattr(os, "replace", real_replace)

    assert open(p).read() == "ok"                       # conteúdo antigo intacto
    assert [f for f in os.listdir(tmp_path) if f.startswith(".tmp_")] == []
