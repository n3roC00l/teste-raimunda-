"""
config.py — configuração central do sistema do rover contador de plântulas.

Ponto único de verdade para caminhos, parâmetros do modelo e destino da nuvem.
Antes, cada script tinha seus próprios caminhos absolutos e constantes
espalhadas; isso quebrava ao rodar em outra máquina.

REGRAS
------
- NENHUM segredo aqui (tokens, senhas). O `rclone.conf` com as credenciais
  fica no sistema, fora do repositório. Este arquivo é versionado.
- Ajuste por máquina: variáveis de ambiente `ROVER_*` ou um arquivo
  `config_local.py` (ignorado pelo git — ver `config_local.example.py`).
- Todos os caminhos são derivados de `BASE_DIR`. Não escreva caminho absoluto
  em nenhum outro script.

Referências
-----------
- The Twelve-Factor App, fator III — separação estrita de config e código.
- Parnas, D. L. (1972). "On the Criteria To Be Used in Decomposing Systems
  into Modules." CACM 15(12) — ocultar decisões que mudam.
"""

import os

# --------------------------------------------------------------------------
# Versão (fonte única — corrige o "v2.5" fixo no título do painel)
# --------------------------------------------------------------------------
VERSAO = "2.1.0-dev"

# --------------------------------------------------------------------------
# Diretório base do projeto
# --------------------------------------------------------------------------
# Raiz = pasta onde este arquivo está. Sobrescreva com ROVER_BASE_DIR se o
# código e os dados morarem em lugares diferentes.
BASE_DIR = os.environ.get(
    "ROVER_BASE_DIR",
    os.path.dirname(os.path.abspath(__file__)),
)

# --------------------------------------------------------------------------
# Pastas de trabalho (todas derivadas de BASE_DIR)
# --------------------------------------------------------------------------
PASTA_PARA_ANALISAR = os.path.join(BASE_DIR, "imagens_para_analisar")
PASTA_ANALISADAS    = os.path.join(BASE_DIR, "imagens_analisadas")
PASTA_ERROS         = os.path.join(BASE_DIR, "imagens_com_erro")
PASTA_LOGS          = os.path.join(BASE_DIR, "logs_analise")

PASTAS_DE_TRABALHO = (
    PASTA_PARA_ANALISAR,
    PASTA_ANALISADAS,
    PASTA_ERROS,
    PASTA_LOGS,
)

# --------------------------------------------------------------------------
# Arquivos de dados
# --------------------------------------------------------------------------
ARQUIVO_CSV    = os.path.join(PASTA_LOGS, "log_analise_total.csv")
ARQUIVO_STATUS = os.path.join(PASTA_LOGS, "status_analise.json")

# --------------------------------------------------------------------------
# Scripts do pipeline (o painel dispara estes como subprocessos)
# --------------------------------------------------------------------------
SCRIPT_CAPTURADOR  = os.path.join(BASE_DIR, "capturador.py")
SCRIPT_ANALISADOR  = os.path.join(BASE_DIR, "analisador_em_background.py")
SCRIPT_SINCRONIZAR = os.path.join(BASE_DIR, "sincronizar_nuvem.py")

# --------------------------------------------------------------------------
# Modelo YOLOv5
# --------------------------------------------------------------------------
# YOLOV5_DIR = o clone do repositório ultralytics/yolov5 usado por
# torch.hub.load(source="local"). MODELO_PATH = os pesos (.pt).
YOLOV5_DIR  = os.environ.get("ROVER_YOLOV5_DIR", os.path.join(BASE_DIR, "yolov5"))
MODELO_PATH = os.environ.get(
    "ROVER_MODELO_PATH",
    os.path.join(YOLOV5_DIR, "best_soja_final_97_5.pt"),
)

# --------------------------------------------------------------------------
# Parâmetros da captura (capturador.py)
# --------------------------------------------------------------------------
INTERVALO_CAPTURA_S = float(os.environ.get("ROVER_INTERVALO_CAPTURA_S", "0.90"))
RESOLUCAO_CAPTURA   = (1280, 720)

# --------------------------------------------------------------------------
# Parâmetros do analisador (analisador_em_background.py)
# --------------------------------------------------------------------------
INTERVALO_VERIFICACAO_S = float(os.environ.get("ROVER_INTERVALO_VERIFICACAO_S", "2"))
CONFIANCA_IA = float(os.environ.get("ROVER_CONFIANCA_IA", "0.70"))
CLASSES_IA   = [0]

# --------------------------------------------------------------------------
# Correção estatística da contagem  (ver RV-08)
# --------------------------------------------------------------------------
# Precisão e recall do modelo na validação (best_soja_final_97_5).
# ATENÇÃO: fator fixo. RV-08 vai substituir isto por uma curva de calibração
# validada em campo com contagem manual pareada.
TAXA_PRECISAO = float(os.environ.get("ROVER_TAXA_PRECISAO", "0.934"))
TAXA_RECALL   = float(os.environ.get("ROVER_TAXA_RECALL", "0.921"))

# --------------------------------------------------------------------------
# Sincronização em nuvem (sincronizar_nuvem.py)
# --------------------------------------------------------------------------
# O remote e suas credenciais ficam no rclone.conf do sistema, NÃO aqui.
RCLONE_REMOTE = os.environ.get("ROVER_RCLONE_REMOTE", "gdrive")
NUVEM_BASE    = os.environ.get("ROVER_NUVEM_BASE", "Rover_FAPA_Backups")
NUVEM_DESTINO_IMAGENS = f"{RCLONE_REMOTE}:{NUVEM_BASE}/imagens_analisadas"
NUVEM_DESTINO_CSV     = f"{RCLONE_REMOTE}:{NUVEM_BASE}/relatorios"
ARQUIVO_ULTIMA_SYNC = os.path.join(PASTA_LOGS, "ultima_sync.txt")

# Log de eventos append-only (JSONL) — ver core/eventos.py.
ARQUIVO_EVENTOS = os.path.join(PASTA_LOGS, "eventos.jsonl")

# --------------------------------------------------------------------------
# Parcela / nomenclatura  (ver RV-02, RV-06, core/parcela.py)
# --------------------------------------------------------------------------
# Formato do identificador do setor. Ponto único de troca enquanto o Leandro
# não fecha o formato final (zero à esquerda? separador?).
# Placeholders: {x} {y} {linha}.  Padrão: X3Y7L2.
PARCELA_FORMATO = os.environ.get("ROVER_PARCELA_FORMATO", "X{x}Y{y}L{linha}")
PLOT_FORMATO    = os.environ.get("ROVER_PLOT_FORMATO", "X{x}Y{y}")

# Modo aritmético (quando não há planilha de programação carregada).
PARCELA_X_MIN = int(os.environ.get("ROVER_PARCELA_X_MIN", "1"))
PARCELA_X_MAX = int(os.environ.get("ROVER_PARCELA_X_MAX", "12"))
PARCELA_Y_MIN = int(os.environ.get("ROVER_PARCELA_Y_MIN", "1"))
PARCELA_Y_MAX = int(os.environ.get("ROVER_PARCELA_Y_MAX", "18"))
PARCELA_LINHAS = int(os.environ.get("ROVER_PARCELA_LINHAS", "3"))

# Planilha de programação da semeadora (Plan1). Se o arquivo existir, o
# navegador entra em "modo campanha" e segue a ordem dos plots dela; se não,
# cai no modo aritmético. Aceita .csv ou .xlsx.
PLANILHA_PROGRAMACAO = os.environ.get(
    "ROVER_PLANILHA_PROGRAMACAO",
    os.path.join(BASE_DIR, "programacao_semeadora.csv"),
)

# Posição da campanha, persistida (retoma onde parou após reinício).
ARQUIVO_PARCELA = os.path.join(PASTA_LOGS, "parcela_atual.json")

EXPERIMENTO_PADRAO = os.environ.get("ROVER_EXPERIMENTO_PADRAO", "Experimento sem nome")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def garantir_pastas():
    """Cria as pastas de trabalho se não existirem. Chame no início dos
    scripts que escrevem em disco (importar este módulo não cria nada)."""
    for pasta in PASTAS_DE_TRABALHO:
        os.makedirs(pasta, exist_ok=True)


# --------------------------------------------------------------------------
# Overrides locais da máquina (arquivo ignorado pelo git)
# --------------------------------------------------------------------------
try:
    from config_local import *  # noqa: F401,F403
except ImportError:
    pass
