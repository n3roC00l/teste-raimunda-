"""
Testes de core/campo.py: o snapshot do ensaio (gêmeo digital).

Cenário pequeno e determinístico: planilha 2x2 plots (X 1..2, Y 1..2),
3 carreiras, plot de 6 m + 1 m de passagem, carreiras a 50 cm. O "agora"
é fixo, para as idades não dependerem do relógio.
"""

import csv
import json
import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from core import campo, registro

AGORA = datetime(2026, 10, 15, 10, 0, 0)
EXP = "Ensaio Teste"

_CABECALHO_PLAN1 = [
    "Parcela Compr.(Y)", "Parcela Larg. (X)", "ID Opcional",
    "Comprimento Parcela (cm)", "Passagem (cm)", "Grãos por Parcela",
    "Espaçam. fil (cm)", "Carreiras por parcela", "Numero ranhuras",
    "linha 1", "linha 2", "linha 3",
]
# ordem do arquivo: X1Y1, X1Y2, X2Y1, X2Y2 (como a Plan1 real: Y anda primeiro)
_GRAOS = {(1, 1): 270, (1, 2): 300, (2, 1): 240, (2, 2): 360}


def _escrever_planilha(caminho, experimento=EXP):
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(_CABECALHO_PLAN1)
        for x in (1, 2):
            for y in (1, 2):
                w.writerow([y, x, experimento, 600, 100, _GRAOS[(x, y)], 50, 3, 18, "", "", ""])


def _foto(caminho_csv, x, y, linha, corrigido, seg, experimento=EXP, bruto=None):
    """Anexa uma foto analisada ao CSV canônico, com horário fixo."""
    registro.registrar_analise(
        caminho_csv, experimento=experimento, parcela=f"X{x}Y{y}L{linha}",
        X=x, Y=y, linha=linha,
        timestamp_imagem=f"2026-10-15 09:00:{seg:02d}.500000",
        timestamp_analise=f"2026-10-15 09:00:{seg + 1:02d}",
        plantulas_bruto=corrigido if bruto is None else bruto,
        plantulas_corrigido=corrigido,
        nome_imagem=f"X{x}Y{y}L{linha}_{seg}.jpg",
        versao_modelo="best_soja_final_97_5.pt", versao_software="2.1.0-dev",
    )


def _evento(caminho, ts, evento, **dados):
    with open(caminho, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": ts, "evento": evento, **dados}, ensure_ascii=False) + "\n")


def _status(caminho, **campos):
    base = {"schema": 2, "parcela": "", "experimento": EXP, "plot": "", "linha": 0,
            "ultima_imagem": "", "plantulas_bruto": 0, "plantulas_corrigido": 0,
            "total_parcela_bruto": 0, "total_parcela_corrigido": 0,
            "total_linha_1": 0, "total_linha_2": 0, "total_linha_3": 0,
            "fila_pendente": 0, "analisador_estado": "pronto",
            "timestamp": "2026-10-15 09:59:58"}
    base.update(campos)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(base, f)


def _posicao(caminho, indice=0, linha=1, experimento=EXP):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump({"experimento": experimento, "modo": "campanha", "indice": indice,
                   "linha": linha, "x": 1, "y": 1}, f)


@pytest.fixture
def fontes(tmp_path):
    logs = tmp_path / "logs_analise"
    logs.mkdir()
    f = campo.Fontes(
        csv=str(logs / "log_analise_total.csv"),
        status=str(logs / "status_analise.json"),
        parcela=str(logs / "parcela_atual.json"),
        eventos=str(logs / "eventos.jsonl"),
        planilha=str(tmp_path / "programacao_semeadora.csv"),
        ultima_sync=str(logs / "ultima_sync.txt"),
    )
    _escrever_planilha(f.planilha)
    registro.garantir_csv(f.csv)
    return f


def _snap(fontes, **kw):
    kw.setdefault("agora", AGORA)
    return campo.montar_snapshot(fontes=fontes, **kw)


def _plot(snap, pid):
    return next(p for p in snap["campo"]["plots"] if p["id"] == pid)


# --- geometria --------------------------------------------------------------
def test_geometria_vem_da_planilha(fontes):
    s = _snap(fontes)
    c = s["campo"]
    assert (c["carreiras_por_plot"], c["espacamento_m"], c["largura_plot_m"]) == (3, 0.5, 1.5)
    assert (c["comprimento_plot_m"], c["passagem_m"]) == (6.0, 1.0)
    assert [p["id"] for p in c["plots"]] == ["X1Y1", "X1Y2", "X2Y1", "X2Y2"]  # ordem da planilha
    assert [p["ordem"] for p in c["plots"]] == [1, 2, 3, 4]
    assert _plot(s, "X1Y1")["origem_m"] == [0.0, 0.0]
    assert _plot(s, "X2Y1")["origem_m"] == [1.5, 0.0]        # X anda na largura
    assert _plot(s, "X1Y2")["origem_m"] == [0.0, 7.0]        # Y anda no comprimento (+passagem)
    assert (c["largura_m"], c["comprimento_m"]) == (3.0, 13.0)
    centros = [k["centro_u_m"] for k in _plot(s, "X2Y1")["carreiras"]]
    assert centros == [1.75, 2.25, 2.75]


def test_eixos_trocados_por_config(fontes, monkeypatch):
    monkeypatch.setattr(config, "CAMPO_TROCAR_EIXOS", True)
    s = _snap(fontes)
    assert _plot(s, "X2Y1")["origem_m"] == [0.0, 7.0]
    assert _plot(s, "X1Y2")["origem_m"] == [1.5, 0.0]
    assert s["campo"]["eixos_trocados"] is True


def test_sem_planilha_usa_grade_do_modo_manual(fontes, monkeypatch):
    os.remove(fontes.planilha)
    monkeypatch.setattr(config, "PARCELA_X_MAX", 2)
    monkeypatch.setattr(config, "PARCELA_Y_MAX", 3)
    _posicao(fontes.parcela, experimento="Manual")
    s = _snap(fontes)
    assert s["experimento"] == "Manual"
    assert s["fontes"]["planilha"] is None
    assert len(s["campo"]["plots"]) == 6
    assert all(p["graos"] is None for p in s["campo"]["plots"])
    assert s["campo"]["comprimento_plot_m"] == config.CAMPO_COMPRIMENTO_CM / 100


# --- contagem e emergência --------------------------------------------------
def test_soma_por_carreira_e_emergencia(fontes):
    for seg, n in ((0, 30), (2, 28), (4, 31)):
        _foto(fontes.csv, 1, 1, 1, n, seg, bruto=n - 2)
    s = _snap(fontes)
    k = _plot(s, "X1Y1")["carreiras"][0]
    assert k["estado"] == "analisada"
    assert (k["plantulas"], k["plantulas_bruto"], k["imagens"]) == (89, 83, 3)
    assert k["esperado"] == 90.0                      # 270 grãos / 3 carreiras
    assert k["emergencia"] == pytest.approx(89 / 90, abs=1e-3)
    assert (k["primeira_imagem"], k["ultima_imagem"]) == ("2026-10-15 09:00:00", "2026-10-15 09:00:04")
    assert k["ultima_analise"] == "2026-10-15 09:00:05"
    assert k["versoes_modelo"] == ["best_soja_final_97_5.pt"]
    assert k["alerta"] is None
    assert k["incerteza"] is None                     # RV-08


def test_estado_do_plot(fontes):
    _foto(fontes.csv, 1, 1, 1, 80, 0)
    for linha in (1, 2, 3):
        _foto(fontes.csv, 2, 2, linha, 110, linha)
    s = _snap(fontes)
    assert _plot(s, "X1Y1")["estado"] == "parcial"
    assert _plot(s, "X1Y2")["estado"] == "pendente"
    p = _plot(s, "X2Y2")
    assert p["estado"] == "concluido"
    assert (p["plantulas"], p["esperado"]) == (330, 360.0)
    assert p["emergencia"] == pytest.approx(330 / 360, abs=1e-3)


@pytest.mark.parametrize("contagem,alerta,trecho", [
    (0, "critico", "nenhuma planta"),
    (40, "critico", "abaixo de 50%"),       # 40/90 = 44%
    (55, "atencao", "abaixo de 70%"),       # 61%
    (80, None, None),                       # 89%
    (120, "atencao", "acima do semeado"),   # 133%
])
def test_alertas_de_emergencia(fontes, contagem, alerta, trecho):
    _foto(fontes.csv, 1, 1, 1, contagem, 0)
    s = _snap(fontes)
    k = _plot(s, "X1Y1")["carreiras"][0]
    assert k["alerta"] == alerta
    if trecho:
        assert trecho in k["motivo"]
        assert _plot(s, "X1Y1")["alerta"] == alerta   # o plot herda o pior


def test_alerta_usa_limiar_de_config(fontes, monkeypatch):
    monkeypatch.setattr(config, "CAMPO_EMERGENCIA_ATENCAO", 0.95)
    _foto(fontes.csv, 1, 1, 1, 80, 0)                 # 89%: agora abaixo do limiar
    assert _plot(_snap(fontes), "X1Y1")["carreiras"][0]["alerta"] == "atencao"


# --- rover ------------------------------------------------------------------
def test_rover_posicao_vem_da_planilha_e_do_painel(fontes):
    _posicao(fontes.parcela, indice=2, linha=3)       # 3º plot da planilha = X2Y1
    s = _snap(fontes)
    pos = s["rover"]["posicao"]
    assert (pos["parcela"], pos["plot"], pos["linha"]) == ("X2Y1L3", "X2Y1", 3)
    assert (pos["ordem"], pos["total_plots"], pos["modo"]) == (3, 4, "campanha")


def test_rover_sem_arquivo_de_posicao_nao_inventa(fontes):
    s = _snap(fontes)
    assert s["rover"]["posicao"] is None
    assert s["rover"]["analisador_estado"] == "desconhecido"


def test_carreira_em_captura_nao_alerta_e_fica_fora_dos_totais(fontes):
    _posicao(fontes.parcela, indice=0, linha=1)
    _foto(fontes.csv, 1, 1, 1, 10, 0)                 # 11%: alertaria se estivesse fechada
    _evento(fontes.eventos, "2026-10-15 09:00:00", "captura_iniciada", parcela="X1Y1L1")
    s = _snap(fontes)
    k = _plot(s, "X1Y1")["carreiras"][0]
    assert s["rover"]["capturando"] is True
    assert (k["estado"], k["alerta"], k["plantulas"]) == ("capturando", None, 10)
    assert s["kpis"]["plantulas"] == 0
    assert s["kpis"]["plantulas_em_captura"] == 10
    # parou a captura: a carreira fecha e o alerta passa a valer
    _evento(fontes.eventos, "2026-10-15 09:01:00", "captura_parada", parcela="X1Y1L1")
    k = _plot(_snap(fontes), "X1Y1")["carreiras"][0]
    assert (k["estado"], k["alerta"]) == ("analisada", "critico")


def test_painel_reiniciado_desliga_captura(fontes):
    _evento(fontes.eventos, "2026-10-15 09:00:00", "captura_iniciada")
    _evento(fontes.eventos, "2026-10-15 09:05:00", "painel_iniciado")   # caiu e voltou
    assert _snap(fontes)["rover"]["capturando"] is False


@pytest.mark.parametrize("status,eventos_,alerta,trecho", [
    ({"analisador_estado": "erro"}, [], "critico", "analisador em erro"),
    ({"fila_pendente": 25}, [], "atencao", "fila de análise com 25"),
    ({"timestamp": "2026-10-15 09:58:00"}, ["captura_iniciada"], "atencao", "nenhuma análise há 120 s"),
    ({"timestamp": "2026-10-15 09:58:00"}, [], None, None),     # parado: status velho é normal
])
def test_alertas_do_rover(fontes, status, eventos_, alerta, trecho):
    _status(fontes.status, **status)
    for nome in eventos_:
        _evento(fontes.eventos, "2026-10-15 09:00:00", nome)
    r = _snap(fontes)["rover"]
    assert r["alerta"] == alerta
    if trecho:
        assert trecho in r["motivo"]


def test_idades_usam_o_agora_injetado(fontes):
    _status(fontes.status, timestamp="2026-10-15 09:59:30")
    assert _snap(fontes)["rover"]["idade_status_s"] == 30.0


# --- linha do tempo ---------------------------------------------------------
def test_horarios_nao_mudam_com_o_relogio(fontes):
    """O furo do vídeo: histórico recalculado a partir de 'agora'. Aqui não."""
    _foto(fontes.csv, 1, 1, 1, 80, 0)
    a = _snap(fontes, agora=datetime(2026, 10, 15, 10, 0, 0))
    b = _snap(fontes, agora=datetime(2026, 10, 15, 18, 30, 0))
    ka, kb = _plot(a, "X1Y1")["carreiras"][0], _plot(b, "X1Y1")["carreiras"][0]
    for campo_ in ("primeira_imagem", "ultima_imagem", "ultima_analise"):
        assert ka[campo_] == kb[campo_]
    assert a["kpis"]["idade_atividade_s"] != b["kpis"]["idade_atividade_s"]


def test_linhagem_sync_e_export(fontes):
    _foto(fontes.csv, 1, 1, 1, 80, 0)                 # analisada às 09:00:01
    _foto(fontes.csv, 1, 1, 2, 80, 40)                # analisada às 09:00:41
    _evento(fontes.eventos, "2026-10-15 09:00:20", "sync_ok")
    _evento(fontes.eventos, "2026-10-15 09:30:00", "planilha_exportada", saida="x.xlsx")
    s = _snap(fontes)
    l1, l2 = _plot(s, "X1Y1")["carreiras"][:2]
    assert (l1["sincronizada_em"], l1["exportada_em"]) == ("2026-10-15 09:00:20", "2026-10-15 09:30:00")
    assert (l2["sincronizada_em"], l2["exportada_em"]) == (None, "2026-10-15 09:30:00")


def test_ultima_sync_prefere_o_arquivo(fontes):
    _evento(fontes.eventos, "2026-10-15 08:00:00", "sync_ok")
    assert _snap(fontes)["kpis"]["ultima_sync"] == "2026-10-15 08:00:00"
    with open(fontes.ultima_sync, "w", encoding="utf-8") as f:
        f.write("2026-10-15 09:00:00")
    s = _snap(fontes)
    assert (s["kpis"]["ultima_sync"], s["kpis"]["idade_sync_s"]) == ("2026-10-15 09:00:00", 3600.0)


def test_eventos_recentes_limitados(fontes, monkeypatch):
    monkeypatch.setattr(config, "CAMPO_EVENTOS_LIMITE", 3)
    for i in range(5):
        _evento(fontes.eventos, f"2026-10-15 09:00:0{i}", "parcela_avancada", n=i)
    s = _snap(fontes)
    assert [e["n"] for e in s["eventos"]] == [2, 3, 4]
    assert s["fontes"]["eventos"] == 5


# --- experimentos e fontes --------------------------------------------------
def test_experimento_antigo_so_do_csv(fontes):
    _foto(fontes.csv, 5, 9, 2, 50, 0, experimento="Safra 2024")
    _foto(fontes.csv, 1, 1, 1, 80, 1)
    s = _snap(fontes, experimento="Safra 2024")
    assert s["experimentos"] == ["Ensaio Teste", "Safra 2024"]
    assert s["campanha_atual"] is False
    assert s["fontes"]["planilha"] is None
    assert [p["id"] for p in s["campo"]["plots"]] == ["X5Y9"]
    p = s["campo"]["plots"][0]
    assert p["graos"] is None and p["emergencia"] is None and p["fora_da_planilha"] is False
    assert s["rover"]["posicao"] is None


def test_plot_fora_da_planilha_aparece_marcado(fontes):
    _foto(fontes.csv, 9, 9, 1, 50, 0)
    p = _plot(_snap(fontes), "X9Y9")
    assert p["fora_da_planilha"] is True


def test_linhas_com_nome_antigo_sao_contadas_a_parte(fontes):
    registro.registrar_analise(fontes.csv, experimento=EXP, parcela="lote_3_var_7",
                               plantulas_corrigido=12)
    _foto(fontes.csv, 1, 1, 1, 80, 0)
    s = _snap(fontes)
    assert s["fontes"]["csv_sem_parcela"] == 1
    assert s["fontes"]["csv_linhas"] == 2
    assert s["kpis"]["plantulas"] == 80


def test_tudo_ausente_ainda_monta(tmp_path):
    vazio = str(tmp_path / "nao_existe")
    f = campo.Fontes(csv=vazio, status=vazio, parcela=vazio, eventos=vazio,
                     planilha=vazio, ultima_sync=vazio)
    s = campo.montar_snapshot(fontes=f, agora=AGORA)
    assert s["schema"] == campo.SCHEMA_VERSION
    assert s["campo"]["plots"] == [] and s["rover"]["posicao"] is None
    json.dumps(s)


# --- indicadores: um lugar só calcula ---------------------------------------
def test_kpis_batem_com_a_soma_dos_plots(fontes):
    for (x, y), base in {(1, 1): 80, (1, 2): 20, (2, 2): 130}.items():
        for linha in (1, 2, 3):
            _foto(fontes.csv, x, y, linha, base + linha, linha)
    s = _snap(fontes)
    plots, k = s["campo"]["plots"], s["kpis"]
    carreiras = [c for p in plots for c in p["carreiras"]]
    assert k["plantulas"] == sum(p["plantulas"] or 0 for p in plots)
    assert k["carreiras_em_alerta"] == sum(c["alerta"] is not None for c in carreiras)
    assert k["plots_em_alerta"] == sum(p["alerta"] is not None for p in plots)
    assert k["carreiras_analisadas"] == 9 and k["plots_concluidos"] == 3
    assert k["emergencia_media"] == pytest.approx(k["plantulas"] / k["esperado"], abs=1e-3)
    assert k["progresso"] == pytest.approx(9 / 12)


def test_saude_alerta_de_disco_e_backup(fontes):
    _foto(fontes.csv, 1, 1, 1, 80, 0)
    tele = {"cpu_temp_c": 51.0, "disco_livre_gb": 0.5, "processos": {}}
    s = _snap(fontes, telemetria=tele)
    motivos = [a["motivo"] for a in s["saude"]["alertas"]]
    assert s["saude"]["alerta"] == "critico"
    assert any("disco" in m for m in motivos)
    assert any("nenhum backup" in m for m in motivos)


def test_marcador_demo(fontes):
    assert _snap(fontes)["demo"] is False
    open(fontes.marcador_demo, "w").close()
    assert _snap(fontes)["demo"] is True


# --- cache incremental ------------------------------------------------------
def test_cache_le_so_o_que_entrou_e_bate_com_leitura_completa(fontes):
    cache = campo.Cache()
    _foto(fontes.csv, 1, 1, 1, 80, 0)
    _evento(fontes.eventos, "2026-10-15 09:00:00", "captura_parada")
    assert _snap(fontes, cache=cache)["kpis"]["plantulas"] == 80
    _foto(fontes.csv, 1, 1, 2, 70, 1)
    _evento(fontes.eventos, "2026-10-15 09:01:00", "sync_ok")
    com_cache, sem_cache = _snap(fontes, cache=cache), _snap(fontes)
    assert com_cache == sem_cache
    assert com_cache["kpis"]["plantulas"] == 150


def test_cache_ignora_linha_incompleta_ate_terminar(fontes):
    cache = campo.Cache()
    _foto(fontes.csv, 1, 1, 1, 80, 0)
    with open(fontes.csv, "a", encoding="utf-8") as f:
        f.write(f"{EXP},X1Y1L2,1,1,2,2026-10-15 09:00:09.0,")      # escrita pela metade
    assert _snap(fontes, cache=cache)["kpis"]["plantulas"] == 80
    with open(fontes.csv, "a", encoding="utf-8") as f:
        f.write("2026-10-15 09:00:10,70,70,,img.jpg,,best.pt,2.1.0-dev\n")
    assert _snap(fontes, cache=cache)["kpis"]["plantulas"] == 150


def test_cache_recomeca_quando_o_csv_e_trocado(fontes):
    cache = campo.Cache()
    _foto(fontes.csv, 1, 1, 1, 80, 0)
    assert _snap(fontes, cache=cache)["kpis"]["plantulas"] == 80
    os.rename(fontes.csv, fontes.csv + ".legado")     # como o garantir_csv faz
    registro.garantir_csv(fontes.csv)
    _foto(fontes.csv, 1, 1, 1, 5, 0)
    assert _snap(fontes, cache=cache)["kpis"]["plantulas_em_captura"] is None
    assert _plot(_snap(fontes, cache=cache), "X1Y1")["carreiras"][0]["plantulas"] == 5


def test_cache_relê_a_planilha_quando_muda(fontes):
    cache = campo.Cache()
    assert _plot(_snap(fontes, cache=cache), "X1Y1")["graos"] == 270
    _GRAOS[(1, 1)] = 999
    try:
        _escrever_planilha(fontes.planilha)
        os.utime(fontes.planilha, ns=(1, 1))          # garante mtime diferente
        assert _plot(_snap(fontes, cache=cache), "X1Y1")["graos"] == 999
    finally:
        _GRAOS[(1, 1)] = 270


# --- CLI e telemetria -------------------------------------------------------
def test_cli_imprime_json(fontes, monkeypatch, capsys):
    monkeypatch.setattr(campo.Fontes, "do_config", classmethod(lambda cls: fontes))
    _foto(fontes.csv, 1, 1, 1, 80, 0)
    campo.main(["--compacto", "--sem-telemetria"])
    s = json.loads(capsys.readouterr().out)
    assert s["kpis"]["plantulas"] == 80 and s["saude"]["telemetria"] is None


def test_telemetria_nunca_levanta():
    t = campo.telemetria()
    assert set(t) == {"cpu_temp_c", "disco_livre_gb", "processos"}
    assert set(t["processos"]) == {"painel", "analisador", "capturador"}
