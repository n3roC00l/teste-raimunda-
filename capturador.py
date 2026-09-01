#Criado por Gabriel Woitovetch

import cv2
from picamera2 import Picamera2
import time
import os
import sys
from datetime import datetime
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

# --- CONFIGURAÇÃO (ver config.py) ---
INTERVALO_SEGUNDOS = config.INTERVALO_CAPTURA_S
PASTA_PARA_ANALISAR = config.PASTA_PARA_ANALISAR
os.makedirs(PASTA_PARA_ANALISAR, exist_ok=True)

parser = argparse.ArgumentParser(description="Capturador de imagens para contagem de plântulas.")
parser.add_argument('--setor', type=str, default=None,
                    help='Setor inicial. Se omitido, lê de config.ARQUIVO_SETOR.')
args = parser.parse_args()
SETOR_INICIAL = args.setor


def _setor_atual():
    """Lê o setor corrente do arquivo que o painel grava a cada 'Próxima'.
    Permite trocar de carreira sem reiniciar a câmera."""
    try:
        with open(config.ARQUIVO_SETOR, encoding='utf-8') as f:
            return f.read().strip() or None
    except OSError:
        return None


SETOR_ATUAL = _setor_atual() or SETOR_INICIAL
if not SETOR_ATUAL:
    print("CAPTURA: !!! nenhum setor definido (nem --setor nem config.ARQUIVO_SETOR).")
    sys.exit(1)

print(f"CAPTURA: A iniciar o capturador para o setor: {SETOR_ATUAL}")
picam2 = None
try:
    picam2 = Picamera2()
    cam_config = picam2.create_still_configuration(main={"size": config.RESOLUCAO_CAPTURA})
    picam2.configure(cam_config)
    picam2.start()
    print(f"CAPTURA: Câmera pronta. A capturar imagens em '{PASTA_PARA_ANALISAR}'.")
    time.sleep(2.0)
    while True:
        SETOR_ATUAL = _setor_atual() or SETOR_ATUAL      # relê a cada foto
        timestamp_arquivo = datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')
        nome_arquivo = f"{SETOR_ATUAL}_{timestamp_arquivo}.jpg"
        caminho_completo = os.path.join(PASTA_PARA_ANALISAR, nome_arquivo)
        picam2.capture_file(caminho_completo)
        print("CAPTURED", flush=True)
        time.sleep(INTERVALO_SEGUNDOS)
except KeyboardInterrupt:
    print("\nCAPTURA: Processo interrompido pelo utilizador.")
except Exception as e:
    print(f"\nCAPTURA: !!! ERRO FATAL NA CÂMERA: {e}")
finally:
    if picam2 and picam2.is_open:
        picam2.stop()
        print("CAPTURA: Câmera desligada com segurança.")
