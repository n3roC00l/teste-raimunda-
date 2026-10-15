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
# Identifica os pesos usados, gravado em cada linha do CSV (rastreabilidade).
VERSAO_MODELO = os.environ.get("ROVER_VERSAO_MODELO", os.path.basename(MODELO_PATH))

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
# cai no modo aritmético. Aceita .csv ou .xlsx (o operador dropa o dele na raiz).
PLANILHA_PROGRAMACAO = os.environ.get("ROVER_PLANILHA_PROGRAMACAO", "")
if not PLANILHA_PROGRAMACAO:
    _csv = os.path.join(BASE_DIR, "programacao_semeadora.csv")
    _xlsx = os.path.join(BASE_DIR, "programacao_semeadora.xlsx")
    PLANILHA_PROGRAMACAO = _xlsx if (os.path.exists(_xlsx) and not os.path.exists(_csv)) else _csv

# Posição da campanha, persistida (retoma onde parou após reinício).
ARQUIVO_PARCELA = os.path.join(PASTA_LOGS, "parcela_atual.json")

# Setor corrente (identificador). O painel grava aqui a cada "Próxima"; o
# capturador lê a cada foto — permite trocar de carreira SEM parar a câmera.
ARQUIVO_SETOR = os.path.join(PASTA_LOGS, "setor_atual.txt")

EXPERIMENTO_PADRAO = os.environ.get("ROVER_EXPERIMENTO_PADRAO", "Experimento sem nome")

# --------------------------------------------------------------------------
# Gêmeo digital do ensaio (visão 3D)  (ver core/campo.py, docs/GEMEO-3D.md)
# --------------------------------------------------------------------------
# Geometria padrão, usada quando a planilha não traz a coluna (ou não há
# planilha). Valores da Plan1 de exemplo: plot de 6 m, passagem de 1 m,
# carreiras a 50 cm.
CAMPO_COMPRIMENTO_CM = float(os.environ.get("ROVER_CAMPO_COMPRIMENTO_CM", "600"))
CAMPO_PASSAGEM_CM    = float(os.environ.get("ROVER_CAMPO_PASSAGEM_CM", "100"))
CAMPO_ESPACAMENTO_CM = float(os.environ.get("ROVER_CAMPO_ESPACAMENTO_CM", "50"))
# Folga entre plots vizinhos na direção transversal às carreiras (bordadura).
CAMPO_FOLGA_CM = float(os.environ.get("ROVER_CAMPO_FOLGA_CM", "0"))
# Padrão: X anda transversal às carreiras e Y ao longo delas, como dizem os
# nomes das colunas ("Parcela Larg. (X)", "Parcela Compr.(Y)"). Ainda em
# aberto com o Leandro (as abas Plan1 e Planilha1 divergem): "1" inverte.
CAMPO_TROCAR_EIXOS = os.environ.get("ROVER_CAMPO_TROCAR_EIXOS", "0") == "1"

# Limiares de alerta. PROVISÓRIOS: fechar com o Leandro (frente #6,
# racionalização de alarmes). Emergência = plantas contadas (corrigido) ÷
# grãos semeados na carreira.
CAMPO_EMERGENCIA_ATENCAO = float(os.environ.get("ROVER_CAMPO_EMERGENCIA_ATENCAO", "0.70"))
CAMPO_EMERGENCIA_CRITICO = float(os.environ.get("ROVER_CAMPO_EMERGENCIA_CRITICO", "0.50"))
# Acima disto, suspeita de dupla contagem (fotos sobrepostas) ou de erro na planilha.
CAMPO_EMERGENCIA_MAXIMA  = float(os.environ.get("ROVER_CAMPO_EMERGENCIA_MAXIMA", "1.20"))
CAMPO_FILA_ATENCAO       = int(os.environ.get("ROVER_CAMPO_FILA_ATENCAO", "20"))
# Captura ligada e o analisador sem gravar status há mais que isto: travou?
CAMPO_STATUS_VELHO_S     = float(os.environ.get("ROVER_CAMPO_STATUS_VELHO_S", "30"))
CAMPO_SYNC_VELHA_S       = float(os.environ.get("ROVER_CAMPO_SYNC_VELHA_S", "7200"))
CAMPO_DISCO_ATENCAO_GB   = float(os.environ.get("ROVER_CAMPO_DISCO_ATENCAO_GB", "5"))
CAMPO_DISCO_CRITICO_GB   = float(os.environ.get("ROVER_CAMPO_DISCO_CRITICO_GB", "1"))

# Quantos eventos recentes vão no snapshot (linha do tempo da visão).
CAMPO_EVENTOS_LIMITE = int(os.environ.get("ROVER_CAMPO_EVENTOS_LIMITE", "200"))

# Onde o ensaio fica no mundo (para o entorno da FAPA e o sol na visão 3D).
# Ponto = canto do plot X1Y1 no começo da carreira 1; rumo = direção em que
# as carreiras andam (graus a partir do norte, sentido horário). APROXIMADO:
# estimado na área experimental ao lado da sede da FAPA (Entre Rios,
# Guarapuava); confirmar o bloco exato com o Leandro.
CAMPO_GEO_LAT        = float(os.environ.get("ROVER_CAMPO_GEO_LAT", "-25.54622"))
CAMPO_GEO_LON        = float(os.environ.get("ROVER_CAMPO_GEO_LON", "-51.49012"))
CAMPO_GEO_RUMO_GRAUS = float(os.environ.get("ROVER_CAMPO_GEO_RUMO_GRAUS", "70"))
# "1": X cresce para a esquerda de quem anda na carreira (padrão: direita).
CAMPO_GEO_ESPELHAR   = os.environ.get("ROVER_CAMPO_GEO_ESPELHAR", "0") == "1"
CAMPO_GEO_APROXIMADO = os.environ.get("ROVER_CAMPO_GEO_APROXIMADO", "1") == "1"
# Fuso do relógio do Pi (Brasília, sem horário de verão desde 2019).
CAMPO_FUSO_HORAS     = float(os.environ.get("ROVER_CAMPO_FUSO_HORAS", "-3"))

# Movimento do rover na visão (estimado: não há odômetro). "serpentina" =
# carreira 1 vai, 2 volta, 3 vai; "mesmo_sentido" = todas no mesmo sentido.
CAMPO_TRAJETO = os.environ.get("ROVER_CAMPO_TRAJETO", "serpentina")
# Duração de uma carreira quando ainda não há histórico para estimar.
CAMPO_DURACAO_CARREIRA_PADRAO_S = float(os.environ.get("ROVER_CAMPO_DURACAO_CARREIRA_PADRAO_S", "20"))

# Servidor da visão 3D (servidor_visao.py): só leitura, rede local.
# 0.0.0.0 = qualquer aparelho da mesma rede vê (hotspot do Pi ou Wi-Fi da
# fazenda). Para só a própria máquina: ROVER_VISAO_HOST=127.0.0.1.
VISAO_HOST    = os.environ.get("ROVER_VISAO_HOST", "0.0.0.0")
VISAO_PORTA   = int(os.environ.get("ROVER_VISAO_PORTA", "8080"))
VISAO_WEB_DIR = os.environ.get("ROVER_VISAO_WEB_DIR", os.path.join(BASE_DIR, "web", "dist"))
# Snapshot reaproveitado por até este tempo, para todos os clientes juntos.
VISAO_CACHE_S = float(os.environ.get("ROVER_VISAO_CACHE_S", "1.0"))


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
