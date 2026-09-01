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
parser.add_argument('--setor', type=str, required=True, help='Nome do setor/lote a ser fotografado.')
args = parser.parse_args()
SETOR_ATUAL = args.setor

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
