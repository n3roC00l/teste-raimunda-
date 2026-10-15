#!/bin/bash
# Instala o rover.service como serviço de usuário do systemd.
# Rodar na conta `operador` do Raspberry Pi (não usar sudo).
#   --visao   instala também o visao.service (visão 3D, só leitura, rede local)
set -euo pipefail

INSTALAR_VISAO=0
for arg in "$@"; do
    case "$arg" in
        --visao) INSTALAR_VISAO=1 ;;
        *) echo "uso: $0 [--visao]"; exit 2 ;;
    esac
done

AQUI="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
DEST="${HOME}/.config/systemd/user"

echo "==> instalando rover.service em ${DEST}"
mkdir -p "${DEST}"
cp "${AQUI}/rover.service" "${DEST}/rover.service"

# garante que a sessão gráfica exporte o DISPLAY para os serviços de usuário
systemctl --user import-environment DISPLAY 2>/dev/null || true

systemctl --user daemon-reload
systemctl --user enable --now rover.service

if [ "${INSTALAR_VISAO}" = 1 ]; then
    echo "==> instalando visao.service (visão 3D, só leitura, rede local)"
    cp "${AQUI}/visao.service" "${DEST}/visao.service"
    systemctl --user daemon-reload
    systemctl --user enable --now visao.service
    systemctl --user --no-pager status visao.service || true
fi

# para o serviço continuar rodando mesmo sem sessão aberta por SSH:
#   sudo loginctl enable-linger "$USER"

echo
echo "==> status:"
systemctl --user --no-pager status rover.service || true
echo
echo "logs ao vivo:  journalctl --user -u rover.service -f"
