#!/bin/bash
# ferramentas/rodar_demo.sh: sobe a demonstração completa da visão 3D.
#
# Campanha SINTÉTICA gravando ao vivo (ferramentas/demo_campanha.py) +
# servidor_visao.py servindo o web/dist compilado. A tela mostra a faixa
# "DEMONSTRAÇÃO". Abra http://127.0.0.1:8765 ; Ctrl+C encerra os dois.
#
# A pasta fica em ~/.cache/rover-demo (disco de verdade): o /tmp costuma ser
# memória (tmpfs) e some num reinício. Para abrir de um celular ou tablet na
# mesma rede, atenda na rede com ROVER_DEMO_HOST=0.0.0.0.
#
#   ROVER_DEMO_DIR=/tmp/outra ROVER_VISAO_PORTA=9000 ./ferramentas/rodar_demo.sh
#   ROVER_DEMO_HOST=0.0.0.0 ./ferramentas/rodar_demo.sh
set -euo pipefail

RAIZ="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
DEMO="${ROVER_DEMO_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/rover-demo}"
PORTA="${ROVER_VISAO_PORTA:-8765}"
HOST="${ROVER_DEMO_HOST:-127.0.0.1}"
cd "$RAIZ"

if [ ! -f web/dist/index.html ]; then
    echo "web/dist não existe: compile antes com  (cd web && corepack pnpm install && corepack pnpm build)"
    exit 1
fi

python3 ferramentas/demo_campanha.py --dir "$DEMO" --ao-vivo &
SIMULADOR=$!
trap 'kill "$SIMULADOR" 2>/dev/null || true' EXIT
sleep 1

ROVER_BASE_DIR="$DEMO" ROVER_VISAO_WEB_DIR="$RAIZ/web/dist" \
    python3 servidor_visao.py --host "$HOST" --porta "$PORTA" --sem-telemetria
