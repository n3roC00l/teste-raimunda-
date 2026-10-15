# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) ·
versionamento: [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

### `feat/web-gemeo-v0`: a visão 3D do ensaio

**Adicionado**
- `web/` (React 19 + TypeScript + Vite + React Three Fiber + drei + zustand):
  o campo em escala real a partir da planilha (plots, 3 carreiras, passagens),
  rover low-poly na carreira atual (pulsa capturando), pinos 3D nos plots em
  alerta, rótulos X/Y, dica ao passar o ponteiro, seleção de plot/carreira com
  contorno. Modos de cor *Estado* e *Emergência* (rampa de 6 faixas validada
  para daltonismo). Câmera de mapa com vista de trabalho em volta do rover e
  enquadramento calculado (o `fitToBox` perdia a inclinação); dado novo nunca
  mexe na câmera. `frameloop="demand"`: parada, a tela não redesenha.
- Interface: barra com selo ao vivo/sem conexão e faixa DEMONSTRAÇÃO,
  indicadores, painel lateral (rover, plot, carreira com linhagem), legenda,
  linha do tempo. Layout responsivo (painel embaixo em tela estreita).
- `ferramentas/demo_campanha.py`: campanha **sintética** (planilha genérica
  12 x 18, mancha de emergência baixa, carreira zerada, dupla contagem) com o
  marcador `DEMO`; snapshot estático para `?demo` ou gravação ao vivo. Recusa
  pasta que tenha dados sem o marcador.
- `ferramentas/rodar_demo.sh`: demo completa (campanha ao vivo + servidor).
- `web/README.md`, `docs/screenshots/gemeo-v0-*.png`, seção "A tela" no
  `docs/GEMEO-3D.md`. `tests/test_demo_campanha.py` (3).

**Alterado**
- `core/campo.py`: alertas do rover e da saúde ganham `codigo` (analisador_erro,
  analise_parada, fila, disco, backup), para a tela não depender do texto.
  Aditivo: schema continua 1.

**Comportamento:** nada muda no rover. Suite: 165 casos. Build web:
1,2 MB de JS (332 KB com gzip).

### `feat/servidor-visao`: servidor HTTP só leitura da visão 3D

**Adicionado**
- `servidor_visao.py` (stdlib, sem dependência nova): `GET /api/snapshot`
  (gzip, `?experimento=`), `GET /api/foto/<nome>.jpg` (só de
  `imagens_analisadas/`; nome validado, bloqueia `..` e link simbólico para
  fora), e os estáticos do `web/dist` (sem build, uma página explicando).
  Só `GET`/`HEAD` (o resto é 405); não escreve nada em disco. Um snapshot por
  `VISAO_CACHE_S` para todos os clientes, com o `campo.Cache` incremental:
  ~130 ms na primeira, <1 ms depois, ~19 KB com gzip (campanha inteira).
  Loga só erros (o cliente consulta a cada 2 s).
- `deploy/visao.service` (`Nice=10`, `Restart=on-failure`) e
  `deploy/install.sh --visao` (opcional).
- `config.py`: `VISAO_HOST`, `VISAO_PORTA`, `VISAO_WEB_DIR`, `VISAO_CACHE_S`.
- `tests/test_servidor_visao.py` (24): rotas, gzip, cache, travessia de
  diretório, métodos, "não escreve nada".

**Comportamento:** nada muda no rover; o servidor é opcional e só lê.
Suite: 162 casos.

### `feat/campo-snapshot`: snapshot do ensaio para a visão 3D

**Adicionado**
- `core/campo.py`: junta planilha (geometria + grãos), CSV canônico, status,
  posição do painel e eventos num único JSON versionado (`schema: 1`), só
  leitura. Por carreira: estado, contagem, esperado, **emergência** (plantas ÷
  grãos semeados), nº de fotos, horários, linhagem (sincronizada/exportada),
  versões e alerta. Mais: posição do rover, KPIs calculados num lugar só,
  saúde do Pi (temperatura, disco, processos vivos), últimos eventos.
- `campo.Cache`: leitura incremental do CSV e do `eventos.jsonl` (só as linhas
  novas; recomeça se o arquivo for trocado; ignora linha pela metade) e
  planilha relida só quando muda. Campanha inteira: ~100 ms → ~13 ms.
- CLI: `python -m core.campo [--experimento NOME] [--compacto] [--sem-telemetria]`.
- `config.py`: geometria padrão (`CAMPO_*_CM`), `CAMPO_TROCAR_EIXOS` (X vs Y em
  aberto) e limiares de alerta **provisórios** (`CAMPO_EMERGENCIA_*`,
  `CAMPO_FILA_ATENCAO`, `CAMPO_STATUS_VELHO_S`, `CAMPO_SYNC_VELHA_S`,
  `CAMPO_DISCO_*`).
- `docs/GEMEO-3D.md`: regras, arquitetura, schema, definições, roadmap.
- `tests/test_campo.py` (37).

**Alterado**
- `core/parcela.py`: `ler_planilha()` público (o `carregar_plots` passa a usar).
  Comportamento igual.

**Comportamento:** nada muda no rover; é um módulo novo, só de leitura.
Suite: 138 casos.

### `feat/troca-carreira-ao-vivo` — mudar de carreira sem parar a câmera

**Adicionado**
- `core/io_atomico.py` — escrita atômica (`escrever_texto` / `escrever_json` /
  `escrever_bytes`). `core/status.py` e `core/parcela.py` passam a usar (era
  código duplicado 3×). `tests/test_io_atomico.py` (5).
- `config.ARQUIVO_SETOR` (`logs_analise/setor_atual.txt`).

**Alterado**
- `capturador.py` — `--setor` vira opcional; o setor é **relido de
  `config.ARQUIVO_SETOR` a cada foto**. Trocar de carreira não reinicia mais
  a câmera.
- `ui/painel.py` — o botão **Próxima (F2) fica ativo durante a captura**: ao
  apertar, o painel grava o novo identificador no arquivo (atômico), atualiza
  `setor_atual` e zera os contadores; a câmera segue rodando. `◂ Voltar` e
  `editar experimento` continuam travados na captura. `start_capture` grava o
  arquivo antes de subir o capturador.

**Comportamento:** a navegação deixa de exigir parar a captura. O analisador
já lida com a troca (parseia o setor do nome do arquivo; acumula por linha) —
a linha anterior congela, a nova começa a somar. Trade-off: ~1 foto na
fronteira pode cair na linha anterior (<1 s de percurso). Suite: 101 casos.
`docs/MELHORIAS.md` frente #5; RV-02.

### `feat/export-csv` — CSV canônico + export para a planilha (RV-06)

**Adicionado**
- `core/registro.py` — CSV **tidy** (`log_analise_total.csv`): uma variável
  por coluna — `experimento, parcela, X, Y, linha, timestamp_imagem,
  timestamp_analise, plantulas_bruto, plantulas_corrigido, incerteza,
  nome_imagem, sha256_imagem, versao_modelo, versao_software`. `incerteza`
  reservado para RV-08. `garantir_csv()` **arquiva** um CSV de formato antigo
  (`*.legado-<ts>.csv`) e começa limpo.
- `core/export.py` — soma `plantulas_corrigido` por (X, Y, linha) e preenche
  as colunas `linha 1/2/3` da planilha da semeadora. Saída `.xlsx` (preserva
  abas/estrutura via openpyxl) ou `.csv`.
- `exportar_planilha.py` — CLI para rodar no fim da campanha.
- Painel: **Ctrl+E** exporta (mostra quantos plots preencheu e onde salvou).
- `tests/test_registro.py` (6), `tests/test_export.py` (6).
- `config.VERSAO_MODELO` (basename dos pesos, gravado em cada linha).

**Alterado**
- `analisador_em_background.py` grava pelo `core/registro.py` — com
  `experimento` (lido de `parcela_atual.json`), X/Y/linha decompostos do
  identificador, `sha256` da imagem e versões. O CSV antigo (11 formatos,
  97 linhas vazias — era teste) é arquivado no primeiro arranque.

**Comportamento:** o CSV muda de formato (de propósito — RV-06). Análise,
acumulados e status seguem iguais. Suite: 95 casos. `docs/MELHORIAS.md`
frentes #2 e #5; RV-06.

### `feat/persistencia` + `feat/systemd` — robustez de campo (frente #3)

**Adicionado**
- `core/eventos.py` — log de eventos **append-only** (`logs_analise/eventos.jsonl`,
  uma linha JSON por evento). `registrar()` nunca levanta. Emitido por
  painel (`painel_iniciado`, `captura_iniciada/parada`, `parcela_avancada`,
  `experimento_alterado`), analisador (`analisador_iniciado/pronto/erro`,
  `parcela_detectada`, `imagem_erro`) e sync (`sync_ok/erro`).
- `core/watchdog.py` — sd_notify opcional (READY=1 / WATCHDOG=1) direto no
  socket, sem `python3-systemd`. **No-op** fora do systemd. Painel e
  analisador pingam a cada ciclo.
- `deploy/rover.service` (unit systemd de usuário: `Type=notify`,
  `Restart=on-failure`, `WatchdogSec=120`), `deploy/install.sh`,
  `deploy/README.md` — sobe no boot, reinicia se cair/travar.
- `tests/test_eventos.py` (6), `tests/test_watchdog.py` (3).

**Nota:** a *retomada da campanha* (o "estado persistido" da frente #3) já
tinha sido entregue em `refactor/status-schema` (status atômico) e
`feat/parcela` (`parcela_atual.json` atômico). Esta entrega fecha o resto:
autostart/watchdog + trilha de auditoria.

**Comportamento:** só adições (log + ping). Suite: 81 casos.
`docs/MELHORIAS.md` frente #3; RV-07.

### `feat/parcela` — parcela estruturada + navegação + progresso do plot

**Adicionado**
- `core/parcela.py` — `Parcela` (experimento + X + Y + linha), `identificador`
  (`X{x}Y{y}L{linha}`, configurável em `config.PARCELA_FORMATO`),
  `parse_identificador`, `carregar_plots` (Plan1 em .csv/.xlsx) e `Navegador`
  (modo campanha = segue a planilha; modo manual = incremento aritmético;
  persiste a posição, retoma onde parou).
- `tests/test_parcela.py` (12 casos).
- Config: `PARCELA_FORMATO` / `PLOT_FORMATO`, faixas `PARCELA_X/Y_MIN/MAX`,
  `PARCELA_LINHAS`, `PLANILHA_PROGRAMACAO`, `ARQUIVO_PARCELA`,
  `EXPERIMENTO_PADRAO`, `ARQUIVO_ULTIMA_SYNC`.

**Alterado**
- `core/status.py` **schema 2**: `experimento`, `plot`, `linha`,
  `total_linha_1/2/3`, `total_plot_corrigido` (property). `ler()` aceita
  schema 1 (upgrade transparente).
- `analisador_em_background.py` — além do acumulado por parcela, agora
  **acumula por linha dentro do plot** (parseia `X3Y7L2` → plot `X3Y7`,
  linha 2). Nomes antigos (`trat_A_linha_1`) continuam funcionando (sem
  progresso por linha). CSV inalterado (RV-06).
- `ui/` — faixa da amostra (Experimento + `editar`; Parcela: X/Y/Linha,
  identificador, `plot N de M`, ◂ / **Próxima ▸ F2**), card **Progresso da
  parcela** (linha 1/2/3 + total do plot), Estado do sistema com **última
  sync** + **aguardando sync** + **disco livre**. Campos livres
  Tratamento/Linha saíram — a parcela agora vem do navegador. Navegação
  travada durante a captura.
- `sincronizar_nuvem.py` grava `logs_analise/ultima_sync.txt` no sucesso.
- `requirements.txt`: `openpyxl` (só p/ planilha .xlsx).

**Comportamento:** muda (nova forma de escolher a parcela). A máquina de
estados de captura e a regra do TOTAL por parcela continuam iguais e
testadas. `tests/test_characterization_painel.py` reescrito para o novo
modelo. Suite: 71 casos. Verificado por screenshot headless (Xvfb) em modo
campanha. `docs/MELHORIAS.md` frentes #5 e #6; RV-02 / RV-06.

### `feat/ui-v1` — sistema visual novo + faixas + atalhos

**Alterado (visual — muda o que o operador vê)**
- `ui/tema.py` — paleta por tokens, tema escuro (`BG`/`BG2`/`LINE` ·
  `T1`/`T2`/`T3` · `ACC` · `OK`/`WARN`/`STOP`), como no plano e no mock
  `docs/screenshots/mock-painel-v1.png`. Cor só significa status; ACC só no
  acento. Ref.: High Performance HMI Handbook / ISA-101.
- `ui/widgets.py` — reescrito em blocos de cartão (`cartao`, `titulo_secao`,
  `linha_kv`, `linha_kv_status`) + `montar_topo/contagem/estado_sistema/acoes`.
- `ui/painel.py` — layout em faixas: topo (título + **pílula de status**) →
  Configurações do Experimento → **Contagem** \| **Estado do sistema** →
  ações. Novidades funcionais:
  - "última foto" mostra a contagem **corrigida** + a **bruta** ("detecção IA");
  - **fila de análise** visível (`fila_pendente`), âmbar quando > 0;
  - **estado real do analisador** na pílula e no cartão
    (`carregando modelo… / pronto / analisando / erro`) — fecha
    `feat/estado-analisador`, já que o analisador reporta desde `status-schema`;
  - **atalhos** F5 (iniciar/parar) · F9 (sincronizar) · Ctrl+Q (sair);
  - telemetria não corta mais texto (sem largura fixa);
  - janela redimensionável, mínimo 820×560.

**Fora de escopo (fica para `feat/parcela` — RV-02/RV-06)**
- Faixa "Parcela" do mock: campos X/Y/Linha, identificador `X3Y7L2`, botão
  "Próxima", card "Progresso da parcela" com linha 1/2/3. Depende de carregar
  a planilha da semeadora — o painel ainda usa os campos Tratamento + Linha
  de hoje.

**Comportamento não-visual:** inalterado. `tests/test_characterization_painel.py`
atualizado para o novo golden master (valores de texto/cor); a máquina de
estados de captura e a regra do TOTAL por parcela continuam iguais e
testadas. Suite: 50 casos. Verificado por screenshot headless (Xvfb).
`docs/MELHORIAS.md` frente #6.

### `refactor/ui-split` — painel dividido em `ui/`

**Adicionado**
- `ui/painel.py` — a classe `App` (movida de `painel_controle.py`, lógica
  idêntica método a método).
- `ui/widgets.py` — 4 funções que montam cada bloco da tela (Configurações
  do Experimento, Controles, Visão Computacional, Telemetria); mesmas
  classes Tk, mesmas opções, mesmo texto de antes.
- `ui/tema.py` — cores (hex idênticos ao original) e fontes centralizadas
  em `Fontes` (uma instância por `App`, precisa de um `tk.Tk()` já criado).

**Alterado**
- `painel_controle.py` virou um shim: `from ui.painel import App, main`;
  `./iniciar_aplicacao.sh` continua funcionando sem mudança.
- `tests/test_characterization_painel.py` passa a importar `ui.painel` em
  vez de `painel_controle` (o resto do arquivo — todos os asserts — não
  mudou uma linha).

**Comportamento:** nenhum. Verificado: suite completa (47 casos) passa sem
alterar nenhuma asserção; screenshot headless (Xvfb) do painel rodado via
`python painel_controle.py` é visualmente idêntico ao de antes do split.
`docs/MELHORIAS.md` frentes #6 e #7 (Parnas 1972 — separar o que muda
[layout, `feat/ui-v1`] do que não muda agora).

### testes de caracterização — antes do `refactor/ui-split`

**Adicionado**
- `tests/test_characterization_analisador.py` — golden master de
  `calcular_contagem_ajustada` (fórmula atual pinada) + `analisar_imagem`
  fim-a-fim (CSV, status, acumulado, troca de parcela, caminho de erro) com
  um `FakeModel` injetado (não precisa de `torch`/`cv2` reais).
- `tests/test_characterization_sincronizar.py` — comandos `rclone` exatos
  que `sincronizar()` monta, sem precisar do `rclone` instalado
  (`subprocess.run` substituído).
- `tests/test_characterization_capturador.py` — pin por inspeção de código-
  fonte (formato do nome do arquivo, `--setor` obrigatório); documenta que o
  script não é importável fora do Pi (abre a câmera fora do `if __name__ ==
  "__main__"`).
- `tests/test_characterization_painel.py` — `painel_controle.App` real sob
  Tkinter (`$DISPLAY` existente ou `Xvfb` descartável via `tests/conftest.py`),
  estado inicial dos widgets, `start_capture`/`stop_capture`,
  `update_dashboard` com status válido/de outra parcela/pré-schema/ausente,
  `exit_app`.
- `tests/CHECKLIST-CAMPO.md` — o que só dá para caracterizar no Pi com
  câmera, modelo e `rclone` reais.
- `requirements-dev.txt` (só `pytest`), `pytest.ini`.

**Por quê:** antes de quebrar `painel_controle.py` em `ui/` (`refactor/ui-
split`), travar o comportamento atual como *golden master* — se o split for
"só reorganizar", estes testes continuam passando sem alteração. Suite
total: 47 casos. Ref.: Feathers (2004); Sandve et al. (2013, regra 8).
`docs/MELHORIAS.md` frente #7.

**Comportamento:** nenhum — só testes.

### `refactor/status-schema` — schema único do status_analise.json

**Adicionado**
- `core/status.py` — dataclass `StatusAnalise` (schema versionado), leitura/
  escrita **atômica** (`os.replace` + `fsync`) e rejeição de formato
  incompatível (pré-schema v2.0 ou schema mais novo).
- `core/__init__.py`.
- `tests/test_status.py` — 10 casos: contrato do schema, escrita atômica,
  regra de acumulado, retomada após reinício.

**Corrigido**
- **"TOTAL ACUMULADO" travava em 0.** O analisador gravava
  `ultima_imagem_analisada`/`plantulas_detectadas_ia`; o painel procurava
  `imagem_atual`/`total_plantulas_linha` (que nunca existiam). Agora o
  **analisador mantém o acumulado por parcela** e o painel só lê e exibe.

**Alterado**
- `analisador_em_background.py`: acumula `total_parcela_bruto/corrigido` por
  parcela (zera ao trocar de parcela), retoma o acumulado ao reiniciar,
  reporta `analisador_estado` (`carregando`/`pronto`/`analisando`/`erro`) e
  `fila_pendente`. O cabeçalho do CSV **não muda** (isso é RV-06).
- `painel_controle.py`: "Plântulas na Última Foto" passa a mostrar a contagem
  **corrigida**; o TOTAL vem pronto do status e só aparece se for da parcela
  corrente. Removida a lógica de soma quebrada.

**Comportamento:** muda de propósito (correção de bug). Ref.: Nygard
*Release It!* (single source of truth); Candea & Fox (crash-only).
`docs/MELHORIAS.md` frente #2.

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
