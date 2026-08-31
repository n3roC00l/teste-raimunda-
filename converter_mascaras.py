import cv2
import os
import numpy as np

# --- CONFIGURAÇÃO ---
# Estes caminhos são relativos à pasta 'Projeto_Soja', onde o script será executado.
CAMINHO_DATASET = 'soy-segmentation-ds'
PASTA_IMAGENS_ORIGINAIS = os.path.join(CAMINHO_DATASET, 'images', 'rgb')
PASTA_MASCARAS = os.path.join(CAMINHO_DATASET, 'images', 'gt')

# Pasta onde os novos rótulos em formato YOLO (.txt) serão salvos.
PASTA_OUTPUT_LABELS = 'labels_yolo'
os.makedirs(PASTA_OUTPUT_LABELS, exist_ok=True)

# O índice da nossa classe. Como só temos uma classe ("plantula_soja"), o índice é 0.
CLASSE_INDEX = 0

def converter_mascara_para_yolo(caminho_mascara, caminho_output_label, img_width, img_height):
    """
    Lê uma imagem de máscara, encontra os contornos e escreve as caixas delimitadoras
    em formato YOLO num ficheiro de texto.
    """
    mascara = cv2.imread(caminho_mascara, cv2.IMREAD_GRAYSCALE)
    if mascara is None:
        print(f"Aviso: Não foi possível ler a máscara {caminho_mascara}")
        return

    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    linhas_yolo = []
    for cnt in contornos:
        if cv2.contourArea(cnt) > 20: # Ignora contornos muito pequenos (ruído)
            x, y, w, h = cv2.boundingRect(cnt)

            # Converte coordenadas para o formato YOLO (normalizado)
            x_center_norm = (x + w / 2) / img_width
            y_center_norm = (y + h / 2) / img_height
            width_norm = w / img_width
            height_norm = h / img_height

            linhas_yolo.append(f"{CLASSE_INDEX} {x_center_norm:.6f} {y_center_norm:.6f} {width_norm:.6f} {height_norm:.6f}\n")

    if linhas_yolo:
        with open(caminho_output_label, 'w') as f:
            f.writelines(linhas_yolo)

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    print("A iniciar o processo de conversão de máscaras para rótulos YOLO...")

    nomes_mascaras = os.listdir(PASTA_MASCARAS)
    imagens_convertidas = 0

    for nome_mascara in nomes_mascaras:
        if nome_mascara.endswith('.png'):
            caminho_mascara = os.path.join(PASTA_MASCARAS, nome_mascara)

            nome_base = nome_mascara.replace('.png', '')
            caminho_imagem_original = os.path.join(PASTA_IMAGENS_ORIGINAIS, nome_base + '.jpg')
            caminho_output_label = os.path.join(PASTA_OUTPUT_LABELS, nome_base + '.txt')

            img_original = cv2.imread(caminho_imagem_original)
            if img_original is not None:
                img_height, img_width, _ = img_original.shape
                converter_mascara_para_yolo(caminho_mascara, caminho_output_label, img_width, img_height)
                imagens_convertidas += 1
                print(f"({imagens_convertidas}/{len(nomes_mascaras)}) Convertido: {nome_mascara}")
            else:
                print(f"Aviso: Imagem original não encontrada para a máscara {nome_mascara}")

    print(f"\nConversão concluída! {imagens_convertidas} rótulos foram criados na pasta '{PASTA_OUTPUT_LABELS}'.")
