# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) ·
versionamento: [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

### `refactor/config` — configuração central

**Adicionado**
- `config.py` — ponto único de verdade para caminhos, parâmetros do modelo e
  destino da nuvem. Tudo derivado de `BASE_DIR`; override por `ROVER_*` ou
  `config_local.py`.
- `config_local.example.py` — template de override por máquina.
- `tests/test_config.py` — smoke test do contrato de configuração.

**Alterado**
- `painel_controle.py`, `capturador.py`, `analisador_em_background.py`,
  `sincronizar_nuvem.py` passam a importar `config` — sem caminho absoluto nem
  constante espalhada.
- `sincronizar_nuvem.py`: caminhos `/home/operador/Desktop/Projeto_Soja/...`
  trocados por caminhos derivados de `BASE_DIR`; remote do rclone e pasta na
  nuvem agora configuráveis.
- Título do painel usa `config.VERSAO` (era "v2.5" fixo).
- `.gitignore`: ignora `config_local.py`.

**Comportamento:** sem mudança quando o projeto roda da própria pasta (caso de
produção via `iniciar_aplicacao.sh`). Referência: *Twelve-Factor* fator III;
Parnas (1972). Ver `docs/MELHORIAS.md` frente #1.

---

## [2.0.0] — 2026-08-31

- Marco zero: cópia fiel do sistema v2.0 do rover (backup do Google Drive).
