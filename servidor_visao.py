"""
servidor_visao.py: serve o gêmeo digital do ensaio na rede local. Só leitura.

    GET /api/snapshot[?experimento=NOME]  JSON do core/campo.py (gzip se o cliente aceitar)
    GET /api/foto/<nome>.jpg              foto já analisada (só de imagens_analisadas/)
    GET /, /assets/...                    a visão 3D compilada (web/dist)

Não existe rota que escreva ou comande nada: a visão só olha, e operar o
rover continua sendo no painel. O snapshot é montado no máximo uma vez a
cada VISAO_CACHE_S para todos os clientes juntos, com leitura incremental
do CSV (core/campo.Cache), e o servidor só trabalha quando alguém está
olhando. No Pi roda com Nice=10 (deploy/visao.service) para não disputar
CPU com o YOLO.

Uso:  python servidor_visao.py [--host 0.0.0.0] [--porta 8080] [--sem-telemetria]

Ref.: docs/GEMEO-3D.md.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import socket
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from core import campo

# nome de foto válido: o que o capturador gera (X3Y7L2_2026-10-15_16-20-01-123456.jpg)
_FOTO = re.compile(r"^[A-Za-z0-9_.\-]+\.jpe?g$")

# o mimetypes do sistema às vezes não conhece estes (ou erra o .js)
_TIPOS = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".mjs": "text/javascript",
    ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".ico": "image/x-icon",
    ".woff2": "font/woff2", ".wasm": "application/wasm", ".glb": "model/gltf-binary",
    ".txt": "text/plain; charset=utf-8",
}

# Limite de experimentos diferentes guardados no cache (protege a memória).
_MAX_PRONTOS = 32

_SEM_BUILD = """<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<title>Visão 3D do ensaio</title>
<body style="font:16px system-ui;max-width:40rem;margin:3rem auto;padding:0 1rem">
<h1>A visão 3D ainda não foi compilada</h1>
<p>O servidor está no ar e o snapshot já responde em
<a href="/api/snapshot">/api/snapshot</a>.</p>
<p>Para a tela 3D, compile o app em <code>web/</code> (ver <code>web/README.md</code>)
e copie a pasta <code>web/dist</code> para o Pi.</p>
</body></html>""".encode("utf-8")


class Visao:
    """Estado do servidor, compartilhado por todas as requisições: o cache
    incremental das fontes e o último snapshot pronto de cada experimento."""

    def __init__(self, fontes=None, pasta_fotos=None, web_dir=None,
                 cache_s=None, com_telemetria=True):
        self.fontes = fontes or campo.Fontes.do_config()
        self.pasta_fotos = os.path.realpath(pasta_fotos or config.PASTA_ANALISADAS)
        self.web_dir = os.path.realpath(web_dir or config.VISAO_WEB_DIR)
        self.cache_s = config.VISAO_CACHE_S if cache_s is None else cache_s
        self.com_telemetria = com_telemetria
        self._lock = threading.Lock()
        self._cache = campo.Cache()
        self._prontos = {}    # experimento -> (instante, json, json_gzip)

    def snapshot(self, experimento=None):
        """(json, json_gzip) do snapshot, remontado no máximo a cada cache_s."""
        chave = experimento or ""
        with self._lock:
            pronto = self._prontos.get(chave)
            if pronto and time.monotonic() - pronto[0] < self.cache_s:
                return pronto[1], pronto[2]
            snap = campo.montar_snapshot(
                experimento=experimento, fontes=self.fontes, cache=self._cache,
                telemetria=campo.telemetria() if self.com_telemetria else None,
            )
            corpo = json.dumps(snap, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            if len(self._prontos) >= _MAX_PRONTOS:
                self._prontos.clear()
            pronto = (time.monotonic(), corpo, gzip.compress(corpo, compresslevel=6))
            self._prontos[chave] = pronto
            return pronto[1], pronto[2]

    def caminho_foto(self, nome):
        """Caminho da foto se o nome for válido e ela estiver mesmo dentro da
        pasta de analisadas (nem '..' nem link simbólico para fora). Senão None."""
        if not _FOTO.match(nome or ""):
            return None
        return _dentro(self.pasta_fotos, nome)

    def caminho_estatico(self, caminho_url):
        """Arquivo do web/dist para a URL, ou None. '/' vira index.html."""
        rel = caminho_url.lstrip("/") or "index.html"
        alvo = _dentro(self.web_dir, rel)
        if alvo and os.path.isdir(alvo):
            alvo = _dentro(alvo, "index.html")
        return alvo

    @property
    def tem_build(self):
        return os.path.isfile(os.path.join(self.web_dir, "index.html"))


def _dentro(base, rel):
    """Junta e resolve `rel` em `base`; None se sair de `base` ou não existir."""
    alvo = os.path.realpath(os.path.join(base, rel))
    if alvo != base and not alvo.startswith(base + os.sep):
        return None
    return alvo if os.path.exists(alvo) else None


class Handler(BaseHTTPRequestHandler):
    server_version = "RoverVisao/1"
    visao: Visao = None      # ligado em criar_servidor()

    # --- métodos: só GET e HEAD ----------------------------------------------
    def do_GET(self):
        self._responder(com_corpo=True)

    def do_HEAD(self):
        self._responder(com_corpo=False)

    def _metodo_nao_permitido(self):
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self.send_header("Allow", "GET, HEAD")
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_POST = do_PUT = do_PATCH = do_DELETE = _metodo_nao_permitido

    # --- rotas ------------------------------------------------------------------
    def _responder(self, com_corpo):
        partes = urlsplit(self.path)
        caminho = unquote(partes.path)
        try:
            if caminho == "/api/snapshot":
                experimento = parse_qs(partes.query).get("experimento", [None])[0]
                corpo, corpo_gzip = self.visao.snapshot(experimento)
                extra = {"Cache-Control": "no-store", "Vary": "Accept-Encoding"}
                if "gzip" in (self.headers.get("Accept-Encoding") or ""):
                    corpo, extra["Content-Encoding"] = corpo_gzip, "gzip"
                self._enviar(HTTPStatus.OK, "application/json; charset=utf-8",
                             corpo, com_corpo, extra)
            elif caminho.startswith("/api/foto/"):
                self._arquivo(self.visao.caminho_foto(caminho[len("/api/foto/"):]),
                              com_corpo, "public, max-age=86400, immutable")
            elif caminho.startswith("/api/"):
                self._enviar(HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8",
                             b"rota desconhecida", com_corpo)
            elif not self.visao.tem_build and caminho in ("/", "/index.html"):
                self._enviar(HTTPStatus.OK, _TIPOS[".html"], _SEM_BUILD, com_corpo,
                             {"Cache-Control": "no-cache"})
            else:
                alvo = self.visao.caminho_estatico(caminho)
                # index.html sempre revalida; os assets do Vite têm hash no nome
                cache = "no-cache" if alvo and alvo.endswith(".html") else "public, max-age=31536000, immutable"
                self._arquivo(alvo, com_corpo, cache)
        except (BrokenPipeError, ConnectionResetError):
            pass

    # --- respostas -------------------------------------------------------------
    def _enviar(self, codigo, tipo, corpo, com_corpo, extra=None):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("X-Content-Type-Options", "nosniff")
        for chave, valor in (extra or {}).items():
            self.send_header(chave, valor)
        self.end_headers()
        if com_corpo:
            self.wfile.write(corpo)

    def _arquivo(self, alvo, com_corpo, cache):
        if not alvo or not os.path.isfile(alvo):
            self._enviar(HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8",
                         b"nao encontrado", com_corpo)
            return
        ext = os.path.splitext(alvo)[1].lower()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", _TIPOS.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(os.path.getsize(alvo)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", cache)
        self.end_headers()
        if com_corpo:
            with open(alvo, "rb") as f:
                shutil.copyfileobj(f, self.wfile)

    def log_request(self, code="-", size="-"):
        # o cliente consulta a cada 2 s: só registra o que deu errado
        try:
            if int(code) < 400:
                return
        except (TypeError, ValueError):
            pass
        super().log_request(code, size)


def criar_servidor(host, porta, visao):
    """Servidor HTTP com threads, ligado a um `Visao`. porta=0: qualquer livre."""
    handler = type("HandlerVisao", (Handler,), {"visao": visao})
    servidor = ThreadingHTTPServer((host, porta), handler)
    servidor.daemon_threads = True
    return servidor


def _enderecos(host, porta):
    """Endereços para mostrar ao operador. Só lista os da rede (mDNS e IP da
    interface principal) se o servidor atende na rede; preso a 127.0.0.1,
    outro aparelho não abre, e mostrar o IP só confundiria."""
    if host in ("127.0.0.1", "localhost", "::1") or host.startswith("127."):
        return [f"http://127.0.0.1:{porta}  (só nesta máquina)"]
    if host not in ("", "0.0.0.0", "::"):
        return [f"http://{host}:{porta}"]
    enderecos = [f"http://{socket.gethostname()}.local:{porta}"]
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))     # não envia nada: só escolhe a interface
            enderecos.append(f"http://{s.getsockname()[0]}:{porta}")
    except OSError:
        pass
    return enderecos


def main(argv=None):
    ap = argparse.ArgumentParser(description="Visão 3D do ensaio, só leitura, na rede local.")
    ap.add_argument("--host", default=config.VISAO_HOST)
    ap.add_argument("--porta", type=int, default=config.VISAO_PORTA)
    ap.add_argument("--sem-telemetria", action="store_true",
                    help="não lê temperatura/disco/processos")
    args = ap.parse_args(argv)

    visao = Visao(com_telemetria=not args.sem_telemetria)
    servidor = criar_servidor(args.host, args.porta, visao)
    print(f"VISAO: servindo em {args.host}:{servidor.server_address[1]} (só leitura)", flush=True)
    for endereco in _enderecos(args.host, servidor.server_address[1]):
        print(f"VISAO:   {endereco}", flush=True)
    if not visao.tem_build:
        print(f"VISAO: web/dist não encontrado em {visao.web_dir}: só a API responde.", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
