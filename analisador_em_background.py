#Criado por Eng. Gabriel Woitovetch

import torch
import cv2
import time
import os
import sys
import csv
from datetime import datetime
import json
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

INTERVALO_VERIFICACAO = config.INTERVALO_VERIFICACAO_S
MODELO_IA_PATH = config.MODELO_PATH
YOLOV5_DIR = config.YOLOV5_DIR
CONFIANCA_IA = config.CONFIANCA_IA
CLASSE_IA = config.CLASSES_IA

TAXA_PRECISAO = config.TAXA_PRECISAO
TAXA_RECALL = config.TAXA_RECALL

PASTA_PARA_ANALISAR = config.PASTA_PARA_ANALISAR
PASTA_ANALISADAS = config.PASTA_ANALISADAS
PASTA_LOGS = config.PASTA_LOGS
PASTA_ERROS = config.PASTA_ERROS
config.garantir_pastas()
ARQUIVO_CSV = config.ARQUIVO_CSV
ARQUIVO_STATUS = config.ARQUIVO_STATUS

def inicializar_csv():
    """Verifica se o CSV existe e, se não, cria-o com o cabeçalho."""
    if not os.path.exists(ARQUIVO_CSV):
        with open(ARQUIVO_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp_analise', 'setor_imagem', 'timestamp_imagem', 'plantulas_detectadas_ia', 'plantulas_ajustadas', 'nome_imagem'])
        print(f"ANALISADOR: Ficheiro de log criado em: {ARQUIVO_CSV}")

def calcular_contagem_ajustada(contagem_bruta):
    """Aplica a correção estatística à contagem bruta da IA."""
    if contagem_bruta == 0:
        return 0
        
    taxa_falsos_positivos = 1 - TAXA_PRECISAO
    
    falsos_positivos_estimados = contagem_bruta * taxa_falsos_positivos
    contagem_corrigida_passo1 = contagem_bruta - falsos_positivos_estimados
    
    if TAXA_RECALL > 0:
        contagem_final = contagem_corrigida_passo1 / TAXA_RECALL
    else:
        contagem_final = contagem_corrigida_passo1

    return math.ceil(contagem_final)

def analisar_imagem(caminho_imagem, model):
    """Analisa uma única imagem, regista os dados e move o ficheiro."""
    try:
        results = model(caminho_imagem)
        
        contagem_bruta = len(results.pandas().xyxy[0])
        
        contagem_ajustada = calcular_contagem_ajustada(contagem_bruta)
        
        nome_base = os.path.basename(caminho_imagem)
        partes_nome = nome_base.replace('.jpg', '').split('_')
        setor_imagem = "_".join(partes_nome[:-2])
        timestamp_imagem = f"{partes_nome[-2]} {partes_nome[-1].replace('-', ':', 2).replace('-', '.')}"

        with open(ARQUIVO_CSV, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), setor_imagem, timestamp_imagem, contagem_bruta, contagem_ajustada, nome_base])
        
        status_data = {
            "ultima_imagem_analisada": nome_base,
            "plantulas_detectadas_ia": contagem_bruta,
            "plantulas_estimadas_reais": contagem_ajustada, # Novo campo com valor corrigido
            "timestamp_analise": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(ARQUIVO_STATUS, 'w') as f_status:
            json.dump(status_data, f_status)

        print(f"ANALISADOR: Análise de '{nome_base}' -> {contagem_bruta} detectadas | {contagem_ajustada} estimadas.")
        
        os.rename(caminho_imagem, os.path.join(PASTA_ANALISADAS, nome_base))
    except Exception as e:
        print(f"ANALISADOR: !!! ERRO CRÍTICO ao analisar {os.path.basename(caminho_imagem)}: {e}")
        os.rename(caminho_imagem, os.path.join(PASTA_ERROS, os.path.basename(caminho_imagem)))

if __name__ == "__main__":
    inicializar_csv()
    print("ANALISADOR: A carregar o modelo de IA. Por favor, aguarde...")
    
    try:
        modelo_ia = torch.hub.load(YOLOV5_DIR, 'custom', path=MODELO_IA_PATH, source='local')
        modelo_ia.conf = CONFIANCA_IA
        modelo_ia.classes = CLASSE_IA
        print("ANALISADOR: Modelo carregado com sucesso. A iniciar monitorização da pasta.")
        
        while True:
            imagens_pendentes = sorted([f for f in os.listdir(PASTA_PARA_ANALISAR) if f.endswith('.jpg')])
            
            if not imagens_pendentes:
                time.sleep(INTERVALO_VERIFICACAO)
                continue # Volta para o início do loop

            print(f"ANALISADOR: {len(imagens_pendentes)} imagens encontradas. A processar...")
            
            for nome_imagem in imagens_pendentes:
                caminho_completo = os.path.join(PASTA_PARA_ANALISAR, nome_imagem)
                analisar_imagem(caminho_completo, modelo_ia)
                
    except Exception as e:
        print("\n" + "="*60)
        print("!!! ERRO FATAL NO ANALISADOR !!!")
        print(f"O processo de análise não pôde ser iniciado. Causa: {e}")
        print(f"Verifique se o modelo de IA está no caminho correto ('{MODELO_IA_PATH}')")
        print("e se todas as dependências do ambiente virtual (venv) estão instaladas.")
        print("="*60)
        time.sleep(30)
        
    finally:
        print("ANALISADOR: Encerrado.")
