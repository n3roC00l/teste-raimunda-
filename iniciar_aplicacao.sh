#!/bin/bash

# Obtém o diretório onde o próprio script está localizado
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Navega para esse diretório
cd "$SCRIPT_DIR"

# Ativa o ambiente virtual que está na mesma pasta
source venv/bin/activate

# Executa o script principal da GUI
python painel_controle.py
