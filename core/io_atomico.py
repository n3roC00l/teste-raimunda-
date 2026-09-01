"""
core/io_atomico.py — escrita atômica de arquivos.

Grava num temporário no mesmo diretório (`fsync`) e faz `os.replace`: um
corte de energia no meio nunca deixa o arquivo pela metade — ou está o
conteúdo antigo, ou o novo, nunca lixo.

Usado para o `status_analise.json`, `parcela_atual.json` e `setor_atual.txt`
— os arquivos de estado que precisam sobreviver a um desligamento abrupto.

Ref.: Candea & Fox (2003) "Crash-Only Software". docs/MELHORIAS.md frente #3.
"""

import json
import os
import tempfile


def escrever_bytes(caminho, dados):
    pasta = os.path.dirname(caminho) or "."
    os.makedirs(pasta, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=pasta, prefix=".tmp_", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(dados)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, caminho)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def escrever_texto(caminho, texto):
    escrever_bytes(caminho, str(texto).encode("utf-8"))


def escrever_json(caminho, obj):
    escrever_bytes(caminho, json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8"))
