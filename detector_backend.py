import torch
import cv2
import os

class YoloDetector:
    """
    Classe que encapsula o modelo YOLOv5 para deteção.
    O modelo é carregado apenas uma vez na inicialização para otimização.
    """
    def __init__(self, caminho_modelo):
        """
        Carrega o modelo YOLOv5 ao criar uma instância da classe.
        """
        print("A carregar o modelo... Isto pode demorar um pouco.")
        if not os.path.exists(caminho_modelo):
            raise FileNotFoundError(f"Ficheiro do modelo não encontrado em: {caminho_modelo}")
            
        try:
            self.model = torch.hub.load('yolov5', 'custom', path=caminho_modelo, source='local', force_reload=True)
            print("Modelo carregado com sucesso.")
        except Exception as e:
            print(f"Erro ao carregar o modelo: {e}")
            # Se falhar, tenta descarregar do hub (requer internet)
            print("A tentar carregar do hub da Ultralytics...")
            self.model = torch.hub.load('ultralytics/yolov5', 'custom', path=caminho_modelo, force_reload=True)
            print("Modelo carregado com sucesso a partir do hub.")

    def detectar(self, caminho_imagem_input):
        """
        Recebe o caminho de uma imagem, faz a deteção e retorna a imagem
        com as caixas e a contagem de deteções.
        """
        if not os.path.exists(caminho_imagem_input):
            print("Erro: Imagem de input não encontrada.")
            return None, 0

        # Faz a inferência na imagem
        results = self.model(caminho_imagem_input, size=640)

        # Extrai os resultados
        detections_df = results.pandas().xyxy[0]
        contagem = len(detections_df)

        # Renderiza (desenha) as caixas na imagem
        imagem_resultado_np = results.render()[0]
        
        # Converte a imagem de BGR (padrão do OpenCV) para RGB
        imagem_resultado_rgb = cv2.cvtColor(imagem_resultado_np, cv2.COLOR_BGR2RGB)
        
        print(f"Deteção concluída. Encontradas {contagem} plântulas.")
        
        return imagem_resultado_rgb, contagem
