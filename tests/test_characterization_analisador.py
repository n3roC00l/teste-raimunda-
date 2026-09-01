"""
Caracterização de analisador_em_background.py — trava o comportamento ATUAL
antes de mexer no arquivo (ver docs/MELHORIAS.md frente #7 / Feathers,
"Working Effectively with Legacy Code").

`torch` e `cv2` não estão instalados nesta máquina de desenvolvimento (só no
Pi/venv de campo). Para poder importar o módulo aqui, registramos módulos
dublês em sys.modules SE E SOMENTE SE os reais não existirem — na máquina
onde `torch`/`cv2` estão instalados, o teste usa os módulos de verdade sem
nenhuma diferença de comportamento (o modelo em si nunca é chamado: é
sempre um FakeModel injetado).

Rodar:  python -m pytest tests/test_characterization_analisador.py -q
"""

import importlib
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

for _nome in ("torch", "cv2"):
    try:
        importlib.import_module(_nome)
    except ImportError:
        sys.modules[_nome] = types.ModuleType(_nome)

import config
import analisador_em_background as an
from core import status as status_mod


# ---------------------------------------------------------------------------
# Dublê do modelo YOLOv5: só precisa responder a model(caminho).pandas().xyxy[0]
# com algo que tenha o `len()` certo — analisar_imagem só usa isso.
# ---------------------------------------------------------------------------
class _FakeXYXY:
    def __init__(self, n):
        self._n = n

    def __getitem__(self, idx):
        assert idx == 0
        return [None] * self._n  # só o len() importa


class _FakeResults:
    def __init__(self, n):
        self._n = n

    def pandas(self):
        return types.SimpleNamespace(xyxy=_FakeXYXY(self._n))


class FakeModel:
    """Fila de contagens brutas a devolver, uma por chamada."""

    def __init__(self, contagens):
        self._fila = list(contagens)

    def __call__(self, caminho_imagem):
        return _FakeResults(self._fila.pop(0))


class ModeloQuebrado:
    def __call__(self, caminho_imagem):
        raise RuntimeError("falha simulada do modelo")


# ---------------------------------------------------------------------------
# calcular_contagem_ajustada — golden master da fórmula ATUAL
# (RV-08 vai trocar por curva de calibração; se este teste quebrar de
# propósito por causa disso, é para atualizar os valores, não é bug.)
# ---------------------------------------------------------------------------
def test_taxas_atuais_pinadas():
    assert an.TAXA_PRECISAO == 0.934
    assert an.TAXA_RECALL == 0.921


def test_calcular_contagem_ajustada_golden_master():
    casos = {
        0: 0, 1: 2, 2: 3, 5: 6, 8: 9, 9: 10, 10: 11, 25: 26,
        50: 51, 70: 71, 100: 102, 137: 139, 300: 305, 999: 1014,
    }
    for bruta, esperado in casos.items():
        assert an.calcular_contagem_ajustada(bruta) == esperado, bruta


def test_contagem_zero_e_caso_especial():
    assert an.calcular_contagem_ajustada(0) == 0


# ---------------------------------------------------------------------------
# analisar_imagem — comportamento fim-a-fim (CSV, status, movimentação de arquivo)
# ---------------------------------------------------------------------------
def _preparar_pastas(tmp_path, monkeypatch):
    pendentes = tmp_path / "pendentes"; pendentes.mkdir()
    ok = tmp_path / "ok"; ok.mkdir()
    erro = tmp_path / "erro"; erro.mkdir()
    logs = tmp_path / "logs"; logs.mkdir()
    csv_path = logs / "log.csv"
    status_path = logs / "status.json"

    monkeypatch.setattr(an, "PASTA_ANALISADAS", str(ok))
    monkeypatch.setattr(an, "PASTA_ERROS", str(erro))
    monkeypatch.setattr(an, "ARQUIVO_CSV", str(csv_path))
    monkeypatch.setattr(an, "ARQUIVO_STATUS", str(status_path))
    monkeypatch.setattr(an, "ESTADO", status_mod.StatusAnalise())
    monkeypatch.setattr(config, "ARQUIVO_EVENTOS", str(logs / "eventos.jsonl"))
    monkeypatch.setattr(config, "ARQUIVO_PARCELA", str(logs / "parcela.json"))
    an.inicializar_csv()
    return pendentes, ok, erro, csv_path, status_path


def _linhas_csv(csv_path):
    import csv
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_cabecalho_do_csv_canonico(tmp_path, monkeypatch):
    from core import registro
    _, _, _, csv_path, _ = _preparar_pastas(tmp_path, monkeypatch)
    cabecalho = csv_path.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert cabecalho == registro.CABECALHO


def test_csv_de_formato_antigo_e_arquivado(tmp_path, monkeypatch):
    import csv
    logs = tmp_path / "l"; logs.mkdir()
    csv_path = logs / "log.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["timestamp_analise", "setor_imagem", "x"])
        csv.writer(f).writerow(["2026", "lote_1", "5"])
    monkeypatch.setattr(an, "ARQUIVO_CSV", str(csv_path))
    monkeypatch.setattr(config, "ARQUIVO_EVENTOS", str(logs / "e.jsonl"))

    an.inicializar_csv()

    legados = list(logs.glob("log.legado-*.csv"))
    assert len(legados) == 1
    assert "lote_1" in legados[0].read_text()          # o velho foi preservado
    from core import registro
    assert csv_path.read_text().splitlines()[0].split(",") == registro.CABECALHO


def test_analisar_imagem_grava_csv_canonico_e_move_arquivo(tmp_path, monkeypatch):
    pendentes, ok, erro, csv_path, status_path = _preparar_pastas(tmp_path, monkeypatch)

    nome = "X3Y7L1_2026-02-03_13-47-51-019834.jpg"
    caminho = pendentes / nome
    caminho.write_bytes(b"fake-jpg")

    an.analisar_imagem(str(caminho), FakeModel([10]))

    assert not caminho.exists()
    assert (ok / nome).exists()
    assert not list(erro.iterdir())

    linhas = _linhas_csv(csv_path)
    assert len(linhas) == 1
    d = linhas[0]
    assert d["parcela"] == "X3Y7L1"
    assert d["X"] == "3" and d["Y"] == "7" and d["linha"] == "1"
    assert d["timestamp_imagem"] == "2026-02-03 13:47:51.019834"
    assert d["plantulas_bruto"] == "10"
    assert d["plantulas_corrigido"] == "11"               # golden 10 -> 11
    assert d["nome_imagem"] == nome
    assert len(d["sha256_imagem"]) == 64
    assert d["versao_software"] == config.VERSAO
    assert d["versao_modelo"]

    # status_analise.json: schema novo, acumulado da parcela
    st = status_mod.ler(str(status_path))
    assert st is not None
    assert st.parcela == "X3Y7L1"
    assert st.ultima_imagem == nome
    assert st.plantulas_bruto == 10
    assert st.plantulas_corrigido == 11
    assert st.total_parcela_bruto == 10
    assert st.total_parcela_corrigido == 11
    assert st.plot == "X3Y7" and st.linha == 1
    assert st.analisador_estado == "analisando"


def test_acumulado_soma_ao_longo_da_mesma_parcela(tmp_path, monkeypatch):
    pendentes, *_ , status_path = _preparar_pastas(tmp_path, monkeypatch)
    modelo = FakeModel([10, 8])

    for i, nome in enumerate([
        "trat_A_linha_1_2026-02-03_13-47-51-000001.jpg",
        "trat_A_linha_1_2026-02-03_13-47-52-000002.jpg",
    ]):
        caminho = pendentes / nome
        caminho.write_bytes(b"fake-jpg")
        an.analisar_imagem(str(caminho), modelo)

    st = status_mod.ler(str(status_path))
    assert st.total_parcela_bruto == 18        # 10 + 8
    assert st.total_parcela_corrigido == 20    # 11 + 9 (golden master)
    assert st.plantulas_corrigido == 9         # última foto, não o acumulado


def test_troca_de_parcela_zera_o_acumulado(tmp_path, monkeypatch):
    pendentes, *_ , status_path = _preparar_pastas(tmp_path, monkeypatch)
    modelo = FakeModel([10, 5])

    p1 = pendentes / "trat_A_linha_1_2026-02-03_13-47-51-000001.jpg"
    p1.write_bytes(b"x")
    an.analisar_imagem(str(p1), modelo)

    p2 = pendentes / "trat_B_linha_2_2026-02-03_14-00-00-000001.jpg"
    p2.write_bytes(b"x")
    an.analisar_imagem(str(p2), modelo)

    st = status_mod.ler(str(status_path))
    assert st.parcela == "trat_B_linha_2"
    assert st.total_parcela_bruto == 5          # zerou e recomeçou, não 15
    assert st.total_parcela_corrigido == 6


def test_erro_do_modelo_move_para_pasta_de_erro_e_nao_grava_nada(tmp_path, monkeypatch):
    pendentes, ok, erro, csv_path, status_path = _preparar_pastas(tmp_path, monkeypatch)

    nome = "trat_A_linha_1_2026-02-03_13-47-51-019834.jpg"
    caminho = pendentes / nome
    caminho.write_bytes(b"fake-jpg")

    an.analisar_imagem(str(caminho), ModeloQuebrado())

    assert not caminho.exists()
    assert (erro / nome).exists()
    assert not (ok / nome).exists()

    linhas = csv_path.read_text(encoding="utf-8").splitlines()
    assert len(linhas) == 1  # só o cabeçalho — nada foi gravado
    assert status_mod.ler(str(status_path)) is None  # status nunca foi escrito


def test_progresso_por_linha_com_identificador_estruturado(tmp_path, monkeypatch):
    pendentes, *_ , status_path = _preparar_pastas(tmp_path, monkeypatch)
    modelo = FakeModel([10, 8, 20, 5])

    # plot X3Y7: linha 1 (2 fotos), linha 2 (1 foto), depois plot X3Y8 linha 1
    for nome in [
        "X3Y7L1_2026-02-03_10-00-00-000001.jpg",
        "X3Y7L1_2026-02-03_10-00-01-000002.jpg",
        "X3Y7L2_2026-02-03_10-05-00-000003.jpg",
        "X3Y8L1_2026-02-03_10-10-00-000004.jpg",
    ]:
        caminho = pendentes / nome
        caminho.write_bytes(b"x")
        an.analisar_imagem(str(caminho), modelo)

    st = status_mod.ler(str(status_path))
    assert st.plot == "X3Y8"           # plot corrente (mudou)
    assert st.linha == 1
    assert st.total_linha_1 == 6       # só a foto do X3Y8L1 (10->11? não: golden 5->6)
    assert st.total_linha_2 == 0       # zerou ao trocar de plot
    assert st.total_linha_3 == 0


def test_progresso_por_linha_acumula_no_mesmo_plot(tmp_path, monkeypatch):
    pendentes, *_ , status_path = _preparar_pastas(tmp_path, monkeypatch)
    modelo = FakeModel([10, 10, 8])

    for nome in [
        "X3Y7L1_2026-02-03_10-00-00-000001.jpg",
        "X3Y7L1_2026-02-03_10-00-01-000002.jpg",
        "X3Y7L2_2026-02-03_10-05-00-000003.jpg",
    ]:
        caminho = pendentes / nome
        caminho.write_bytes(b"x")
        an.analisar_imagem(str(caminho), modelo)

    st = status_mod.ler(str(status_path))
    assert st.total_linha_1 == 22      # 11 + 11 (golden 10->11)
    assert st.total_linha_2 == 9       # golden 8->9
    assert st.total_plot_corrigido == 31


def test_nome_antigo_nao_preenche_progresso_por_linha(tmp_path, monkeypatch):
    pendentes, *_ , status_path = _preparar_pastas(tmp_path, monkeypatch)
    caminho = pendentes / "trat_A_linha_1_2026-02-03_10-00-00-000001.jpg"
    caminho.write_bytes(b"x")
    an.analisar_imagem(str(caminho), FakeModel([10]))

    st = status_mod.ler(str(status_path))
    assert st.plot == ""
    assert st.linha == 0
    assert (st.total_linha_1, st.total_linha_2, st.total_linha_3) == (0, 0, 0)
    assert st.total_parcela_corrigido == 11   # o acumulado por parcela ainda funciona


def test_retomar_acumulado_le_status_existente(tmp_path, monkeypatch):
    _, _, _, _, status_path = _preparar_pastas(tmp_path, monkeypatch)
    status_mod.escrever(str(status_path), status_mod.StatusAnalise(
        parcela="trat_A_linha_1", total_parcela_bruto=40, total_parcela_corrigido=44,
    ))
    monkeypatch.setattr(an, "ESTADO", status_mod.StatusAnalise())

    an._retomar_acumulado()

    assert an.ESTADO.parcela == "trat_A_linha_1"
    assert an.ESTADO.total_parcela_corrigido == 44


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
