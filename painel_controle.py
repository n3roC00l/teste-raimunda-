"""
painel_controle.py — shim de compatibilidade.

O painel foi dividido em `ui/` (`refactor/ui-split` — ver docs/MELHORIAS.md
frentes #6 e #7): a classe `App` mora em `ui/painel.py`, cores/fontes em
`ui/tema.py`, montagem dos frames em `ui/widgets.py`. Este arquivo só
existe para que `./iniciar_aplicacao.sh` (e o hábito de `python
painel_controle.py`) continuem funcionando sem nenhuma mudança.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ui.painel import App, main  # noqa: F401 (App reexportado por compatibilidade)

if __name__ == "__main__":
    main()
