"""
Testes de core/parcela.py — identificador, planilha, navegador.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from core import parcela as p


# --- identificador -------------------------------------------------------
def test_identificador_formato_padrao():
    assert p.identificador(3, 7, 2) == "X3Y7L2"
    assert p.plot_id(3, 7) == "X3Y7"


def test_parse_identificador():
    assert p.parse_identificador("X3Y7L2") == (3, 7, 2)
    assert p.parse_identificador("X12Y18L3") == (12, 18, 3)
    assert p.parse_identificador("trat_A_linha_1") is None
    assert p.parse_identificador("") is None
    assert p.parse_identificador("X3Y7") is None


def test_formato_configuravel(monkeypatch):
    monkeypatch.setattr(config, "PARCELA_FORMATO", "X{x}-Y{y}-L{linha}")
    assert p.identificador(3, 7, 2) == "X3-Y7-L2"
    assert p.parse_identificador("X3-Y7-L2") == (3, 7, 2)


# --- planilha ------------------------------------------------------------
_CSV = os.path.join(os.path.dirname(__file__), "..", "docs", "exemplos",
                    "programacao-semeadora-exemplo.csv")
_XLSX = os.path.join(os.path.dirname(__file__), "..", "docs", "exemplos",
                     "programacao-semeadora-exemplo.xlsx")


def test_carregar_plots_csv():
    plots, exp = p.carregar_plots(_CSV)
    assert len(plots) == 216
    assert plots[0] == (1, 1)
    assert exp == "Antecipado Pinhão 2025"


def test_carregar_plots_xlsx():
    plots, exp = p.carregar_plots(_XLSX)
    assert len(plots) == 216
    assert plots[0] == (1, 1)


def test_carregar_plots_arquivo_inexistente():
    assert p.carregar_plots("/nao/existe.csv") is None
    assert p.carregar_plots(None) is None


# --- navegador: modo manual --------------------------------------------
def test_navegador_manual_anda_linha_e_plot():
    nav = p.Navegador()
    assert nav.modo == "manual"
    assert nav.identificador() == "X1Y1L1"
    nav.proxima(); assert nav.identificador() == "X1Y1L2"
    nav.proxima(); assert nav.identificador() == "X1Y1L3"
    nav.proxima(); assert nav.identificador() == "X1Y2L1"   # virou o plot (Y+1)
    nav.anterior(); assert nav.identificador() == "X1Y1L3"


def test_navegador_manual_vira_x_ao_estourar_y(monkeypatch):
    monkeypatch.setattr(config, "PARCELA_Y_MAX", 2)
    nav = p.Navegador()
    nav.definir_manual(y=2, linha=3)
    nav.proxima()  # linha 3 -> próximo plot: Y=2 estoura -> Y=1, X=2
    assert nav.identificador() == "X2Y1L1"


# --- navegador: modo campanha -----------------------------------------
def test_navegador_campanha_segue_a_planilha():
    nav = p.Navegador(plots=[(1, 1), (1, 2), (3, 5)], experimento="Ensaio X")
    assert nav.modo == "campanha"
    assert nav.total_plots == 3
    assert nav.identificador() == "X1Y1L1"
    assert nav.rotulo_plot() == "plot 1 de 3"
    for _ in range(3):  # L1 L2 L3 -> próximo plot
        nav.proxima()
    assert nav.identificador() == "X1Y2L1"
    assert nav.rotulo_plot() == "plot 2 de 3"
    for _ in range(3):
        nav.proxima()
    assert nav.identificador() == "X3Y5L1"


def test_navegador_campanha_nao_passa_do_ultimo_plot():
    nav = p.Navegador(plots=[(1, 1), (1, 2)])
    for _ in range(20):
        nav.proxima()
    assert nav.indice == 1  # travou no último


# --- persistência -----------------------------------------------------
def test_navegador_salva_e_restaura(tmp_path, monkeypatch):
    caminho = str(tmp_path / "parcela_atual.json")
    monkeypatch.setattr(config, "ARQUIVO_PARCELA", caminho)

    nav = p.Navegador()
    nav.experimento = "Meu Ensaio"
    nav.proxima()
    nav.proxima()   # X1Y1L3
    nav.salvar()

    nav2 = p.Navegador()
    nav2.restaurar()
    assert nav2.experimento == "Meu Ensaio"
    assert nav2.identificador() == "X1Y1L3"


def test_restaurar_sem_arquivo_nao_quebra(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ARQUIVO_PARCELA", str(tmp_path / "nada.json"))
    nav = p.Navegador()
    nav.restaurar()  # não deve levantar
    assert nav.identificador() == "X1Y1L1"
