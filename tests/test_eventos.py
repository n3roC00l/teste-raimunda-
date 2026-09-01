"""
Testes de core/eventos.py — log de eventos append-only.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from core import eventos


def _apontar(tmp_path, monkeypatch):
    caminho = str(tmp_path / "eventos.jsonl")
    monkeypatch.setattr(config, "ARQUIVO_EVENTOS", caminho)
    return caminho


def test_registrar_e_ler(tmp_path, monkeypatch):
    _apontar(tmp_path, monkeypatch)
    eventos.registrar("captura_iniciada", parcela="X3Y7L2", experimento="E1")
    eventos.registrar("captura_parada", parcela="X3Y7L2", fotos=12)

    lidos = eventos.ler()
    assert [e["evento"] for e in lidos] == ["captura_iniciada", "captura_parada"]
    assert lidos[0]["parcela"] == "X3Y7L2"
    assert lidos[1]["fotos"] == 12
    assert all("ts" in e for e in lidos)


def test_append_nunca_sobrescreve(tmp_path, monkeypatch):
    _apontar(tmp_path, monkeypatch)
    for i in range(5):
        eventos.registrar("tick", n=i)
    assert len(eventos.ler()) == 5


def test_limite_retorna_ultimos(tmp_path, monkeypatch):
    _apontar(tmp_path, monkeypatch)
    for i in range(10):
        eventos.registrar("tick", n=i)
    ult = eventos.ler(limite=3)
    assert [e["n"] for e in ult] == [7, 8, 9]


def test_ler_sem_arquivo(tmp_path, monkeypatch):
    _apontar(tmp_path, monkeypatch)
    assert eventos.ler() == []


def test_linhas_corrompidas_sao_ignoradas(tmp_path, monkeypatch):
    caminho = _apontar(tmp_path, monkeypatch)
    eventos.registrar("ok", n=1)
    with open(caminho, "a", encoding="utf-8") as f:
        f.write("{lixo não json\n")
        f.write("\n")
    eventos.registrar("ok", n=2)

    lidos = eventos.ler()
    assert [e["n"] for e in lidos] == [1, 2]


def test_registrar_nunca_levanta(monkeypatch):
    # aponta para um caminho impossível de criar
    monkeypatch.setattr(config, "ARQUIVO_EVENTOS", "/proc/nao/pode/escrever/aqui.jsonl")
    eventos.registrar("teste")  # não deve levantar
