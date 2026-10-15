"""
Testes de servidor_visao.py: servidor HTTP só leitura da visão 3D.

Sobe o servidor de verdade numa porta livre (thread), com dados num
diretório temporário, e faz requisições com urllib.
"""

import gzip
import json
import os
import sys
import threading
import urllib.error
import urllib.request

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import servidor_visao
from core import campo, registro


def _cenario(tmp_path, com_build=True):
    logs = tmp_path / "logs_analise"
    fotos = tmp_path / "imagens_analisadas"
    logs.mkdir()
    fotos.mkdir()
    fontes = campo.Fontes(
        csv=str(logs / "log_analise_total.csv"),
        status=str(logs / "status_analise.json"),
        parcela=str(logs / "parcela_atual.json"),
        eventos=str(logs / "eventos.jsonl"),
        planilha=str(tmp_path / "nao_existe.csv"),
        ultima_sync=str(logs / "ultima_sync.txt"),
    )
    registro.garantir_csv(fontes.csv)
    for exp, n in (("Ensaio A", 80), ("Ensaio B", 40)):
        registro.registrar_analise(fontes.csv, experimento=exp, parcela="X1Y1L1", X=1, Y=1,
                                   linha=1, timestamp_imagem="2026-10-15 09:00:00.0",
                                   timestamp_analise="2026-10-15 09:00:01",
                                   plantulas_bruto=n, plantulas_corrigido=n)
    (fotos / "X1Y1L1_2026-10-15_09-00-00-000001.jpg").write_bytes(b"\xff\xd8JPEG\xff\xd9")
    (tmp_path / "segredo.txt").write_text("fora da pasta")
    web = tmp_path / "web_dist"
    if com_build:
        (web / "assets").mkdir(parents=True)
        (web / "index.html").write_text("<!doctype html><title>visao</title>")
        (web / "assets" / "app-abc123.js").write_text("console.log(1)")
    return fontes, str(fotos), str(web)


@pytest.fixture
def servidor(tmp_path):
    criados = []

    def subir(com_build=True, cache_s=60):
        fontes, fotos, web = _cenario(tmp_path, com_build)
        visao = servidor_visao.Visao(fontes=fontes, pasta_fotos=fotos, web_dir=web,
                                     cache_s=cache_s, com_telemetria=False)
        srv = servidor_visao.criar_servidor("127.0.0.1", 0, visao)
        threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05},
                         daemon=True).start()
        criados.append(srv)
        return f"http://127.0.0.1:{srv.server_address[1]}", visao

    yield subir
    for srv in criados:
        srv.shutdown()
        srv.server_close()


def _get(url, metodo="GET", cabecalhos=None):
    req = urllib.request.Request(url, method=metodo, headers=cabecalhos or {})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


# --- snapshot ---------------------------------------------------------------
def test_snapshot_json(servidor):
    base, _ = servidor()
    status, cab, corpo = _get(base + "/api/snapshot")
    assert status == 200
    assert cab["Content-Type"].startswith("application/json")
    assert cab["Cache-Control"] == "no-store"
    s = json.loads(corpo)
    assert s["schema"] == campo.SCHEMA_VERSION
    assert s["experimentos"] == ["Ensaio A", "Ensaio B"]


def test_snapshot_com_gzip(servidor):
    base, _ = servidor()
    status, cab, corpo = _get(base + "/api/snapshot", cabecalhos={"Accept-Encoding": "gzip"})
    assert status == 200 and cab["Content-Encoding"] == "gzip"
    assert json.loads(gzip.decompress(corpo))["schema"] == campo.SCHEMA_VERSION


def test_snapshot_por_experimento(servidor):
    base, _ = servidor()
    for exp, n in (("Ensaio A", 80), ("Ensaio B", 40)):
        _, _, corpo = _get(base + "/api/snapshot?experimento=" + exp.replace(" ", "%20"))
        s = json.loads(corpo)
        assert (s["experimento"], s["kpis"]["plantulas"]) == (exp, n)


def test_snapshot_montado_uma_vez_por_janela_de_cache(servidor, monkeypatch):
    chamadas = []
    original = campo.montar_snapshot
    monkeypatch.setattr(campo, "montar_snapshot",
                        lambda **kw: chamadas.append(1) or original(**kw))
    base, visao = servidor(cache_s=60)
    for _ in range(3):
        _get(base + "/api/snapshot")
    assert len(chamadas) == 1
    visao.cache_s = 0
    _get(base + "/api/snapshot")
    assert len(chamadas) == 2


def test_head_sem_corpo(servidor):
    base, _ = servidor()
    status, cab, corpo = _get(base + "/api/snapshot", metodo="HEAD")
    assert status == 200 and corpo == b"" and int(cab["Content-Length"]) > 0


# --- fotos ------------------------------------------------------------------
def test_foto_valida(servidor):
    base, _ = servidor()
    status, cab, corpo = _get(base + "/api/foto/X1Y1L1_2026-10-15_09-00-00-000001.jpg")
    assert status == 200 and cab["Content-Type"] == "image/jpeg"
    assert corpo == b"\xff\xd8JPEG\xff\xd9"


@pytest.mark.parametrize("nome", [
    "nao_existe.jpg",
    "..%2Fsegredo.txt",
    "%2E%2E%2Fsegredo.txt",
    "../segredo.txt",
    "segredo.txt",
    "link_para_fora.jpg",
])
def test_foto_bloqueia_o_que_nao_e_foto_analisada(servidor, tmp_path, nome):
    base, visao = servidor()
    os.symlink(tmp_path / "segredo.txt", os.path.join(visao.pasta_fotos, "link_para_fora.jpg"))
    status, _, corpo = _get(base + "/api/foto/" + nome)
    assert status == 404 and b"fora da pasta" not in corpo


# --- estáticos (web/dist) ---------------------------------------------------
def test_estaticos(servidor):
    base, _ = servidor()
    status, cab, corpo = _get(base + "/")
    assert status == 200 and cab["Content-Type"].startswith("text/html")
    assert cab["Cache-Control"] == "no-cache" and b"visao" in corpo
    status, cab, _ = _get(base + "/assets/app-abc123.js")
    assert status == 200 and cab["Content-Type"] == "text/javascript"
    assert "immutable" in cab["Cache-Control"]


@pytest.mark.parametrize("caminho", ["/nao.js", "/../segredo.txt", "/%2e%2e/segredo.txt",
                                     "/assets/../../segredo.txt"])
def test_estaticos_nao_saem_do_dist(servidor, caminho):
    base, _ = servidor()
    status, _, corpo = _get(base + caminho)
    assert status == 404 and b"fora da pasta" not in corpo


def test_sem_build_mostra_instrucoes_e_api_funciona(servidor):
    base, _ = servidor(com_build=False)
    status, _, corpo = _get(base + "/")
    assert status == 200 and "ainda não foi compilada".encode() in corpo
    assert _get(base + "/assets/app.js")[0] == 404
    assert _get(base + "/api/snapshot")[0] == 200


# --- só leitura -------------------------------------------------------------
@pytest.mark.parametrize("metodo", ["POST", "PUT", "PATCH", "DELETE"])
def test_so_get_e_head(servidor, metodo):
    base, _ = servidor()
    status, cab, _ = _get(base + "/api/snapshot", metodo=metodo)
    assert status == 405 and cab["Allow"] == "GET, HEAD"


def test_rota_api_desconhecida(servidor):
    base, _ = servidor()
    assert _get(base + "/api/comando")[0] == 404


def test_servidor_nao_escreve_nada(servidor, tmp_path):
    def foto_do_disco():
        return sorted((str(p), p.stat().st_mtime_ns, p.stat().st_size)
                      for p in tmp_path.rglob("*") if p.is_file())

    base, _ = servidor()
    antes = foto_do_disco()
    for rota in ("/", "/api/snapshot", "/api/snapshot?experimento=Ensaio%20B",
                 "/api/foto/X1Y1L1_2026-10-15_09-00-00-000001.jpg", "/nao"):
        _get(base + rota)
    _get(base + "/api/snapshot", metodo="POST")
    assert foto_do_disco() == antes
