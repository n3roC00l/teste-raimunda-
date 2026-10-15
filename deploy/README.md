# deploy/ — rover no boot, com reinício automático

Frente #3 do [`../docs/MELHORIAS.md`](../docs/MELHORIAS.md): o rover é um
equipamento de campo — o modo de falha esperado é **queda de energia**. O
software precisa (a) subir sozinho no boot, (b) reiniciar se cair, (c)
retomar a campanha onde parou.

## (a) + (b) — serviço systemd

`rover.service` é um **serviço de usuário** (roda dentro da sessão gráfica
do `operador`, tem acesso ao display). Ele usa:

- `Restart=on-failure` / `RestartSec=5` — caiu, volta em 5 s;
- `Type=notify` + `WatchdogSec=120` — o painel manda `WATCHDOG=1` a cada 2 s
  (via [`../core/watchdog.py`](../core/watchdog.py)); se **travar** e parar de
  mandar por 120 s, o systemd mata e reinicia.

### Instalar (na conta `operador` do Pi)

```bash
cd ~/Documentos/raimunda      # ou onde o repo estiver
./deploy/install.sh
```

O script copia o unit para `~/.config/systemd/user/`, faz `enable --now` e
mostra o status. Ajuste os caminhos em `rover.service` se o projeto ou o
`venv` estiverem em outro lugar (`WorkingDirectory`, `ExecStart`).

Para o serviço rodar mesmo sem ninguém logado por SSH:

```bash
sudo loginctl enable-linger operador
```

### Operar

```bash
systemctl --user status rover.service
systemctl --user restart rover.service
systemctl --user stop rover.service        # ex.: manutenção
journalctl --user -u rover.service -f       # logs ao vivo
```

> **Autologin gráfico:** o Pi precisa entrar direto na sessão gráfica no
> boot (`raspi-config` → *System* → *Boot / Auto Login* → *Desktop
> Autologin*). Sem isso não há display para o painel.

## Visão 3D do ensaio (opcional)

`visao.service` sobe o [`../servidor_visao.py`](../servidor_visao.py): um
servidor HTTP **só leitura** na porta 8080 com o snapshot do ensaio e, se o
`web/dist` estiver compilado, a tela 3D. Qualquer aparelho na mesma rede
(hotspot do Pi ou Wi-Fi da fazenda) abre `http://<nome-do-pi>.local:8080`.

```bash
./deploy/install.sh --visao               # instala rover.service + visao.service
journalctl --user -u visao.service -f      # mostra os endereços ao subir
```

- Roda com `Nice=10`: nunca disputa CPU com o YOLO. Só trabalha quando alguém
  está olhando (no máximo um snapshot por segundo para todos os clientes).
- Não tem rota de comando nem escreve nada em disco.
- **Sem senha nesta versão.** Na rede da fazenda, qualquer um na mesma rede vê
  as contagens e as fotos. Para limitar à própria máquina:
  `Environment=ROVER_VISAO_HOST=127.0.0.1` no unit.

Detalhes em [`../docs/GEMEO-3D.md`](../docs/GEMEO-3D.md).

## (c) — retomar a campanha

Já resolvido no código (nada a instalar):

| Arquivo | Quem grava | Retoma |
|---|---|---|
| `logs_analise/status_analise.json` | analisador | acumulado por parcela/linha |
| `logs_analise/parcela_atual.json` | painel | experimento + plot + linha corrente |
| `logs_analise/eventos.jsonl` | todos | histórico append-only (auditoria) |

Todos com **escrita atômica** (`os.replace` + `fsync`) — um corte de energia
no meio da gravação nunca deixa arquivo pela metade. Ao reiniciar, painel e
analisador carregam esses arquivos e continuam de onde pararam.

Ref.: Candea & Fox (2003) "Crash-Only Software"; `systemd.service(5)`.
