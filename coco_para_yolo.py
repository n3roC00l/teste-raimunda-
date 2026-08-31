import json
import os
import shutil

def clip_coords(box, img_w, img_h):
    # Função de salvaguarda para garantir que as coordenadas fiquem dentro dos limites [0, 1]
    box[0] = max(0.0, min(1.0, box[0])) # x_center
    box[1] = max(0.0, min(1.0, box[1])) # y_center
    box[2] = max(0.0, min(1.0, box[2])) # width
    box[3] = max(0.0, min(1.0, box[3])) # height
    return box

def converter_coco_para_yolo(caminho_base):
    caminho_json = os.path.join(caminho_base, '_annotations.coco.json')
    if not os.path.exists(caminho_json):
        print(f"Erro: Ficheiro de anotações não encontrado em {caminho_json}")
        return

    pasta_output = os.path.join(caminho_base, 'labels_yolo')
    os.makedirs(pasta_output, exist_ok=True)

    with open(caminho_json, 'r') as f:
        data = json.load(f)

    info_imagens = {img['id']: {'width': img['width'], 'height': img['height'], 'file_name': img['file_name']} for img in data['images']}
    anotacoes_por_imagem = {}

    for anota in data['annotations']:
        img_id = anota['image_id']
        if img_id not in info_imagens:
            continue
        
        box = anota['bbox']
        img_w = info_imagens[img_id]['width']
        img_h = info_imagens[img_id]['height']
        
        # Lógica de conversão
        x_min, y_min, width, height = box[0], box[1], box[2], box[3]
        x_center = x_min + width / 2
        y_center = y_min + height / 2

        # Normalização
        x_center_norm = x_center / img_w
        y_center_norm = y_center / img_h
        width_norm = width / img_w
        height_norm = height / img_h
        
        # --- NOVA SALVAGUARDA ADICIONADA ---
        coords_normalizadas = [x_center_norm, y_center_norm, width_norm, height_norm]
        coords_corrigidas = clip_coords(coords_normalizadas, img_w, img_h)
        # --- FIM DA NOVA SALVAGUARDA ---

        classe_yolo = 0 
        linha_yolo = f"{classe_yolo} {coords_corrigidas[0]:.6f} {coords_corrigidas[1]:.6f} {coords_corrigidas[2]:.6f} {coords_corrigidas[3]:.6f}\n"
        
        nome_ficheiro_base = os.path.basename(info_imagens[img_id]['file_name'])
        if nome_ficheiro_base not in anotacoes_por_imagem:
            anotacoes_por_imagem[nome_ficheiro_base] = []
        anotacoes_por_imagem[nome_ficheiro_base].append(linha_yolo)
    
    for nome_ficheiro, linhas in anotacoes_por_imagem.items():
        nome_ficheiro_txt = nome_ficheiro.replace('.jpg', '.txt')
        caminho_ficheiro_txt = os.path.join(pasta_output, nome_ficheiro_txt)
        with open(caminho_ficheiro_txt, 'w') as f_txt:
            f_txt.writelines(linhas)
            
    print(f"Conversão concluída para a pasta: {caminho_base}")
    print(f"Labels salvos em: {pasta_output}")

# --- EXECUÇÃO PRINCIPAL (sem alterações) ---
if __name__ == "__main__":
    caminho_dataset_git = 'soy-segmentation-ds'
    subpastas = ['train', 'valid', 'test']
    
    for subpasta in subpastas:
        caminho_completo = os.path.join(caminho_dataset_git, 'labeled', subpasta)
        if os.path.exists(caminho_completo):
            print(f"\nA processar a subpasta: {subpasta}...")
            pasta_labels_antiga = os.path.join(caminho_completo, 'labels_yolo')
            if os.path.exists(pasta_labels_antiga):
                shutil.rmtree(pasta_labels_antiga)
                print(f"Pasta de labels antiga '{pasta_labels_antiga}' removida.")
            converter_coco_para_yolo(caminho_completo)
        else:
            print(f"\nAviso: Subpasta '{subpasta}' não encontrada. A ignorar.")

    print("\n\nProcesso de conversão de todas as subpastas concluído!")
