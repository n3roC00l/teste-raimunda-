"""
config_local.example.py — template de override por máquina.

Copie para `config_local.py` (que o git ignora) e sobrescreva só o que
mudar nesta máquina. Alternativa: variáveis de ambiente ROVER_*.

    cp config_local.example.py config_local.py

`config.py` faz `from config_local import *` no final, então qualquer nome
definido aqui vence o padrão.
"""

# Exemplo: dados em disco separado do código
# BASE_DIR = "/mnt/dados/rover"

# Exemplo: outro nome de remote no rclone.conf
# RCLONE_REMOTE = "leandro-drive"

# Exemplo: pesos do modelo em caminho fixo
# MODELO_PATH = "/opt/modelos/best_soja_final_97_5.pt"

# Exemplo: câmera mais lenta em campo
# INTERVALO_CAPTURA_S = 1.20
