# Melhorias do projeto — o quê, o porquê e o embasamento

Data: 2026-09-01. Autor: Gabriel Woitovetch (FAPA).
Base: [ANALISE-E-MAPA.md](ANALISE-E-MAPA.md), [PLANO-PAINEL-v1.md](PLANO-PAINEL-v1.md).

> **Sobre "100% sem falhas":** num sistema de medição, isso não significa "sem bug".
> Significa ter **critério de aceite definido, protocolo de validação e rastreabilidade**
> do dado até o código e a imagem que o produziram. As frentes abaixo levam a isso.
> Cada uma traz *o quê mudar*, *por quê* e a referência real que a sustenta.

---

## 1. Configuração e portabilidade

**O que mudar** — tudo que hoje é caminho absoluto ou constante espalhada
(`os.getcwd()`, `/home/operador/Desktop/Projeto_Soja/...`, `best_soja_final_97_5.pt`,
`gdrive:Rover_FAPA_Backups`, `INTERVALO 0.90`, `CONFIANCA 0.70`, `PRECISAO 0.934`,
`RECALL 0.921`) sai para um `config.py` único, com `config.example.py` versionado e o
`config.py` real fora do Git. Segredos (`rclone.conf`) nunca no repositório.

**Por que** — hoje o código só roda na máquina em que foi escrito. O mesmo software
precisa rodar no PC de desenvolvimento, no Pi do rover e no PC de quem reproduzir a
análise. Config acoplada ao código é a causa nº 1 de "funciona aqui, não funciona lá".

**Referências**
- Wiggins, A. *The Twelve-Factor App* (2011), fator III — *strict separation of config from code*.
- Parnas, D. L. (1972). "On the Criteria To Be Used in Decomposing Systems into Modules." *CACM* 15(12) — ocultar decisões que podem mudar (caminhos, limiares) atrás de uma interface.
- Wilson, G. et al. (2017). "Good enough practices in scientific computing." *PLOS Computational Biology* 13(6) — "put project constants in a single file".

→ RV-04 · PR `refactor/config` · não muda comportamento.

---

## 2. Modelo de dados — a frente mais crítica

**O que mudar**
- **`status_analise.json`**: um *schema* único versionado (`schema: 1`), com o
  **analisador como única fonte da verdade** do acumulado; o painel só lê. Hoje
  analisador e painel usam chaves diferentes (`imagem_atual` vs. `ultima_imagem`,
  `total_plantulas_linha` que nunca existe) → o "TOTAL ACUMULADO" trava em 0.
- **`log_analise_total.csv`**: cabeçalho canônico, **uma variável por coluna**:
  `experimento, X, Y, linha, timestamp_imagem, timestamp_analise, plantulas_bruto,
  plantulas_corrigido, incerteza, nome_imagem, sha256_imagem, versao_modelo, versao_software`.
- Descartar o histórico atual (11 padrões de nomenclatura, 97 linhas vazias — dado de
  teste), arquivando o CSV antigo, e começar limpo.
- **Contrato com a planilha do Leandro**: o export pivota `linha` → colunas
  `linha 1/2/3` da `Plan1`. Um formato, testado.

**Por que** — dado científico mal estruturado é retrabalho garantido na análise e risco
de conclusão errada. "Tidy data" (uma coluna = uma variável) permite pivotar, filtrar e
cruzar sem parsing manual. Schema versionado detecta incompatibilidade em vez de gravar
lixo em silêncio.

**Referências**
- Wickham, H. (2014). "Tidy Data." *Journal of Statistical Software* 59(10) — uma variável por coluna, uma observação por linha.
- Broman, K. W. & Woo, K. H. (2018). "Data Organization in Spreadsheets." *The American Statistician* 72(1) — regras para planilhas de pesquisa (sem células mescladas, sem cor como dado, um valor por célula); vale para o que exportamos ao Leandro.
- Wilkinson, M. D. et al. (2016). "The FAIR Guiding Principles for scientific data management and stewardship." *Scientific Data* 3 — identificadores estáveis, metadados junto do dado.
- Nygard, M. *Release It!* 2ª ed. (2018) — integridade de estado, *single source of truth*.

→ RV-06 · PR `refactor/status-schema` · **corrige o bug do TOTAL**.

---

## 3. Robustez de campo — o rover vai perder energia no meio da parcela

**O que mudar**
- **Estado persistido a cada avanço** (parcela/linha/plot corrente + contadores) com
  gravação atômica (escreve `.tmp` + `rename`). Ao ligar, o painel **retoma onde parou**.
- **`systemd` service** com `Restart=on-failure` e `WatchdogSec` para os 3 processos;
  autostart no boot (RV-07). Nada de depender de alguém abrir um terminal no campo.
- **Log estruturado append-only** (uma linha JSON por evento: início de captura, avanço
  de parcela, erro do analisador, sync). Nunca sobrescreve.
- Cada processo deve **morrer e ser reiniciado sem corromper nada** ("crash-only").

**Por que** — em campo há queda de energia, cartão cheio, sol na tela. O modo de falha
esperado é o desligamento abrupto. Software que assume shutdown limpo perde dados de
parcela — e isso significa **voltar ao talhão para recontar**.

**Referências**
- Candea, G. & Fox, A. (2003). "Crash-Only Software." *HotOS IX* (USENIX) — componentes que só param crashando; recuperação = reinício.
- Nygard, M. *Release It!* (2018) — *stability patterns*: timeouts, circuit breaker, supervisão.
- `systemd.service` — `Restart=`, `WatchdogSec=`, `sd_notify` (documentação freedesktop); padrão em Linux embarcado.
- *The Twelve-Factor App*, fator XI — *logs as event streams*, append-only.

→ RV-07 + RV-02 · PRs `feat/persistencia`, `feat/systemd`.

---

## 4. Validação metrológica da contagem — o número precisa ser defensável

**O que mudar**
- **Protocolo de validação com verdade de campo**: em N parcelas amostrais, contagem
  manual independente vs. contagem do rover. Reportar **viés e limites de concordância**
  (Bland–Altman) e **CCC de Lin**, não só "acurácia 97,5 %".
- **Trocar a correção fixa por calibração**: hoje `corrigida = bruta · P/R` com
  P = 0,934 e R = 0,921 constantes. Isso assume que precisão e recall não mudam com a
  densidade de plântulas nem com a iluminação — raramente verdade. Ajustar uma
  **regressão de calibração** (contagem observada ~ contagem detectada), estratificada
  por faixa de densidade, e usar essa curva.
- **Propagar incerteza**: cada `plantulas_corrigido` sai com um intervalo (coluna
  `incerteza`). O relatório final do ensaio cita a incerteza da medição.
- **Model Card do YOLOv5**: dataset de treino, condições cobertas (estádio fenológico,
  horário, solo), desempenho por condição, limitações conhecidas.

**Por que** — num ensaio real, um revisor vai perguntar "qual o erro dessa contagem e
como vocês sabem?". Sem protocolo de concordância e sem incerteza, o número é uma
caixa-preta. Correção por fator fixo pode introduzir viés sistemático justo nas parcelas
mais densas — as que mais importam.

**Referências**
- JCGM 100:2008 — *Guide to the Expression of Uncertainty in Measurement (GUM)*. Padrão internacional para reportar incerteza de medição.
- Bland, J. M. & Altman, D. G. (1986). "Statistical methods for assessing agreement between two methods of clinical measurement." *The Lancet* 327(8476) — método vs. método, limites de concordância.
- Lin, L. I. (1989). "A concordance correlation coefficient to evaluate reproducibility." *Biometrics* 45(1).
- Lu, H. et al. (2017). "TasselNet: counting maize tassels in the wild via local counts regression network." *Plant Methods* 13:79.
- Jiang, Y. et al. (2019). "DeepSeedling: deep CNN and Kalman filter for plant seedling detection and counting in the field." *Plant Methods* 15:141 — praticamente o mesmo caso (plântulas em campo) com metodologia de validação.
- Mitchell, M. et al. (2019). "Model Cards for Model Reporting." *ACM FAT\**; Gebru, T. et al. (2021). "Datasheets for Datasets." *CACM* 64(12).

→ **RV-08 (novo)** · doc + PR `feat/calibracao` · depende do item 2 e de uma ida a campo.

---

## 5. Metadados do experimento e interoperabilidade

**O que mudar**
- Campo **nome do experimento editável** (pedido do Leandro) + X, Y, linha, guardados
  como **metadados estruturados do ensaio**, não texto solto no título.
- Adotar o vocabulário do **MIAPPE** para os campos que descrevem o experimento
  (estudo, tratamento, unidade experimental/plot, fator, data de semeadura).
- O rover **carrega a `Plan1`** da semeadora e segue a ordem dos plots — igual a um
  *field book* de melhoramento.
- Export num formato que outra ferramenta leia (CSV tidy hoje; **BrAPI** como norte se o
  dado for integrar a um sistema institucional depois).

**Por que** — o dado do rover não vive sozinho: cruza com a programação da semeadora,
com o delineamento (blocos X/Y) e com a análise estatística. Metadados padronizados
evitam que daqui a um ano ninguém saiba o que era "X3Y7L2". É o problema que os apps de
melhoramento já resolveram.

**Referências**
- Papoutsoglou, E. A. et al. (2020). "Enabling reusability of plant phenomic datasets with MIAPPE 1.1." *New Phytologist* 227(1) — *Minimum Information About a Plant Phenotyping Experiment*.
- Rife, T. W. & Poland, J. A. (2014). "Field Book: An Open-Source Application for Field Data Collection on Android." *Crop Science* 54(4) — navegação por plots em ordem definida, entrada por teclado/toque no campo. Modelo direto para o RV-02.
- Selby, P. et al. (2019). "BrAPI — an application programming interface for plant breeding applications." *Bioinformatics* 35(20).

→ RV-02 + RV-06 · PR `feat/parcela`.

---

## 6. HMI — a tela (consolidando o que o mock já começou)

**O que mudar**
- **Paleta muda só em anomalia**: fundo/texto neutros; cor (âmbar/vermelho) reservada
  para status fora do normal (fila alta, analisador em erro, disco baixo). O mock já faz
  isso — formalizar como regra em `ui/tema.py`.
- **Mostrar desvio, não valor bruto**: "fila 3 a analisar" só fica âmbar acima de um
  limiar; "última sync há 2 h" em vez de "14:32".
- **Visibilidade do estado do sistema**: `Carregando modelo → Pronto → Analisando →
  Erro` (hoje só "Parado"). Heurística nº 1 de Nielsen.
- **Limiares de alarme racionalizados**: definir por escrito quando cada indicador muda
  de cor, para não virar "tudo vermelho sempre" (que treina o operador a ignorar).
- **Alvos de toque ≥ 44 pt / 48 dp**, foco de teclado visível, atalho no rótulo do botão.

**Por que** — é uma tela de operação em campo, sob sol, com o operador andando. A
literatura de HMI industrial mediu que tela colorida demais aumenta o tempo de reação a
um problema real. "Cor só para exceção" e "mostre o desvio" são as duas regras centrais.

**Referências**
- Hollifield, B. et al. *The High Performance HMI Handbook* (2008), PAS; norma **ISA-101** (*Human-Machine Interfaces for Process Automation Systems*) — paleta neutra, cor só para alarme, mostrar desvio do normal.
- **ISA-18.2 / IEC 62682** — *Management of Alarm Systems*; **EEMUA 191** — racionalização de alarmes (evitar *alarm flood*).
- Nielsen, J. (1994). "10 Usability Heuristics for User Interface Design" — nº 1: *visibility of system status*.
- Apple *Human Interface Guidelines* (alvo 44 pt); Google *Material Design* (48 dp); ISO 9241-411.

→ RV-01 · PRs `refactor/ui-split`, `feat/ui-v1`, `feat/estado-analisador`.

---

## 7. Estratégia de testes e mudança segura

**O que mudar**
- **Testes de caracterização antes de refatorar**: rodar painel/analisador atuais,
  capturar as saídas (JSON, CSV, screenshots headless via Xvfb) e travar isso como
  *golden master*. Só então mexer.
- **Rodar a versão nova lado a lado com a atual** processando as mesmas imagens,
  comparar CSVs, antes de trocar em produção.
- **Suite mínima**: `core/status.py` (round-trip do schema, versão incompatível);
  correção estatística (casos-limite: 0 detecções, densidade alta); navegação de parcela
  (viradas de faixa linha 3 → próximo plot — o critério de aceite do RV-02 pede 100 %).
- **CI** rodando os testes a cada PR; PRs pequenos, na ordem definida.

**Por que** — o risco real é "mexi no analisador e quebrei a gravação do CSV em produção
sem perceber". Caracterização + execução paralela é o método consagrado para mudar
código legado sem regressão.

**Referências**
- Feathers, M. (2004). *Working Effectively with Legacy Code*, Prentice Hall — *characterization tests*: capture o comportamento atual antes de mudar.
- Falco, L. — *Approval Testing / Golden Master* (documentação ApprovalTests) — comparar saída nova com saída aprovada; casa com os screenshots headless.
- Fowler, M. — "Test Pyramid" (martinfowler.com, 2012).
- Sandve, G. K. et al. (2013). "Ten Simple Rules for Reproducible Computational Research." *PLOS Computational Biology* 9(10) — regra 6 (controle de versão), regra 8 (guardar resultados intermediários para comparar).

→ transversal a todos os PRs.

---

## 8. Reprodutibilidade e rastreabilidade do projeto

**O que mudar**
- **Versão única** (`config.VERSAO`), *Semantic Versioning*, `CHANGELOG.md`, tag no Git
  por campanha de campo. Hoje o título diz "v2.5" e o código é v2.0.
- Cada linha de dado carrega **`versao_modelo` + `versao_software` + `sha256` da
  imagem** (colunas do item 2). Qualquer contagem fica rastreável até o binário e a foto.
- **Modelo (`.pt`) versionado fora do Git** (Git LFS ou release), com hash registrado.
- Backlog RV rastreado como *issues* no `raimunda`, ligado aos PRs.

**Por que** — ao publicar ou defender o resultado, você precisa dizer *exatamente* qual
modelo e qual código produziram cada número. Sem versionamento e hash, isso é
irrecuperável.

**Referências**
- Sandve, G. K. et al. (2013), *op. cit.* — regras 1 (registre como cada resultado foi produzido) e 5 (rastreie versões de programas).
- *Semantic Versioning 2.0.0* (semver.org); *Keep a Changelog* (keepachangelog.com).
- Wilkinson, M. D. et al. (2016), FAIR — F1: identificadores persistentes e únicos.

---

## Priorização (mapeada ao backlog e aos PRs)

| Ordem | Frente | RV | PR | Muda comportamento? |
|---|---|---|---|---|
| 1 | Config única (#1) | RV-04 | `refactor/config` | não |
| 2 | Schema de dados (#2) | RV-06 | `refactor/status-schema` | sim — corrige o TOTAL |
| 3 | Testes de caracterização (#7) | — | (antes do #4) | não |
| 4 | Split de UI (#6, base) | RV-01 | `refactor/ui-split` | não |
| 5 | Layout novo + estado do analisador (#6) | RV-01 | `feat/ui-v1`, `feat/estado-analisador` | sim — visual |
| 6 | Robustez de campo / retomada (#3) | RV-07, RV-02 | `feat/persistencia`, `feat/systemd` | sim |
| 7 | Navegação de parcela + carga da planilha (#5) | RV-02 | `feat/parcela` | sim |
| 8 | Protocolo de validação da contagem (#4) | **RV-08** | doc + `feat/calibracao` | sim |
| 9 | Versionamento / rastreabilidade (#8) | transversal | contínuo | não |

O #4 é o que garante o "êxito" no sentido que importa para pesquisa, mas depende do #2
estar pronto (precisa das colunas de rastreio) e de uma ida a campo com contagem manual
pareada.
