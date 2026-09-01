"""
core/status.py — schema único do `status_analise.json`.

Este arquivo é a comunicação entre processos (IPC) do analisador para o
painel. Antes, cada lado usava chaves diferentes:

    analisador grava:  ultima_imagem_analisada, plantulas_detectadas_ia, ...
    painel procura:    imagem_atual, total_plantulas_linha  (nunca existiam)

Resultado: o "TOTAL ACUMULADO" travava em 0. Aqui o contrato é um só.

PRINCÍPIO
---------
O **analisador é a única fonte da verdade** do acumulado — ele é quem sabe a
contagem real de cada foto. O painel apenas **lê e exibe**; não soma nada.

Escrita **atômica** (arquivo temporário no mesmo diretório + `os.replace`,
com `fsync`): um corte de energia no meio da gravação nunca deixa um JSON
pela metade — ou está o conteúdo antigo, ou o novo, nunca lixo.

Referências
-----------
- Nygard, M. "Release It!" (2018) — *single source of truth* para estado.
- Candea & Fox (2003), "Crash-Only Software" — recuperar de reinício sem
  corromper estado persistido.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, fields
from datetime import datetime

SCHEMA_VERSION = 1

# analisador_estado: máquina de estados simples
ESTADOS = ("parado", "carregando", "pronto", "analisando", "erro")


@dataclass
class StatusAnalise:
    schema: int = SCHEMA_VERSION
    parcela: str = ""                 # setor da última imagem analisada
    ultima_imagem: str = ""
    plantulas_bruto: int = 0          # última foto — detecções da IA
    plantulas_corrigido: int = 0      # última foto — após correção estatística
    total_parcela_bruto: int = 0      # acumulado da parcela corrente
    total_parcela_corrigido: int = 0
    fila_pendente: int = 0            # imagens ainda não analisadas
    analisador_estado: str = "parado"
    timestamp: str = ""

    def marcar_agora(self) -> None:
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, dados: dict) -> "StatusAnalise":
        conhecidos = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in dados.items() if k in conhecidos})


def escrever(caminho: str, status: StatusAnalise) -> None:
    """Grava `status` em `caminho` de forma atômica. Carimba o timestamp."""
    status.marcar_agora()
    pasta = os.path.dirname(caminho) or "."
    os.makedirs(pasta, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=pasta, prefix=".status_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(status.to_dict(), f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, caminho)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def ler(caminho: str) -> "StatusAnalise | None":
    """Lê o status. Retorna None se:
    - o arquivo não existe ou está corrompido;
    - é um arquivo pré-schema (formato v2.0, sem a chave `schema`) — não
      dá para confiar nos totais dele;
    - o schema em disco é mais novo do que este código entende.
    """
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(dados, dict) or "schema" not in dados:
        return None
    try:
        schema_disco = int(dados["schema"])
    except (TypeError, ValueError):
        return None
    if schema_disco > SCHEMA_VERSION:
        return None
    return StatusAnalise.from_dict(dados)
