#!/bin/bash
# ferramentas/rodar_demo.sh: sobe a demonstração completa da visão 3D.
#
# Campanha SINTÉTICA gravando ao vivo (ferramentas/demo_campanha.py) numa pasta
# temporária + servidor_visao.py servindo o web/dist compilado. A tela mostra a
# faixa "DEMONSTRAÇÃO". Abra http://127.0.0.1:8765 ; Ctrl+C encerra os dois.
#
#   ROVER_DEMO_DIR=/tmp/outra ROVER_VISAO_PORTA=9000 ./ferramentas/rodar_demo.sh
set -euo pipefail

RAIZ="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
DEMO="${ROVER_DEMO_DIR:-${TMPDIR:-/tmp}/rover-demo}"
PORTA="${ROVER_VISAO_PORTA:-8765}"
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
    python3 servidor_visao.py --host 127.0.0.1 --porta "$PORTA"
