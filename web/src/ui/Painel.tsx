import { useState } from "react";
import { urlFoto } from "../api";
import { dataHora, duracao, hora, numero, pct } from "../formato";
import { idadeAgora, useAgora } from "../hooks";
import { useIndice, type Indice } from "../indice";
import { useEstado } from "../store";
import type { Carreira, Plot, Snapshot } from "../tipos";
import { IconeAlerta, ItemAlerta, Linha, Pilula, PilulaAnalisador, type Tom } from "./Comum";

// Painel lateral: o que está selecionado (plot, carreira) ou, sem seleção,
// o rover e a lista de plots em alerta (a "tabela" acessível do mapa).

const TOM_ESTADO: Record<string, [string, Tom]> = {
  pendente: ["pendente", "neutro"],
  parcial: ["parcial", "neutro"],
  concluido: ["concluído", "neutro"],
  analisada: ["analisada", "neutro"],
  capturando: ["capturando agora", "acento"],
};

function PilulaEstado({ estado }: { estado: string }) {
  const [texto, tom] = TOM_ESTADO[estado] ?? [estado, "neutro"];
  return <Pilula tom={tom}>{texto}</Pilula>;
}

function Foto({ nome, demo }: { nome: string; demo: boolean }) {
  const [falhou, setFalhou] = useState<string | null>(null);
  if (demo || falhou === nome) return <div className="foto vazia">{demo ? "demonstração: sem fotos" : "foto indisponível"}</div>;
  return <img className="foto" src={urlFoto(nome)} alt={`última foto analisada: ${nome}`} onError={() => setFalhou(nome)} />;
}

function VistaRover({ snap, idx }: { snap: Snapshot; idx: Indice }) {
  const r = snap.rover;
  const t = snap.saude.telemetria;
  const recebidoEm = useEstado((e) => e.recebidoEm);
  const selecionar = useEstado((e) => e.selecionar);
  const agora = useAgora();
  const alertas = [...r.alertas, ...snap.saude.alertas];
  const processo = (v: boolean | null | undefined) => (v === null || v === undefined ? "n/d" : v ? "rodando" : "parado");

  return (
    <>
      <div className="lateral-cabeca">
        <h2>Rover</h2>
        <div className="pilulas">
          <PilulaAnalisador estado={r.analisador_estado} />
          <Pilula tom={r.capturando ? "acento" : "neutro"}>{r.capturando ? "capturando" : "captura parada"}</Pilula>
        </div>
      </div>

      {r.posicao ? (
        <>
          <div className="identificador">{r.posicao.parcela}</div>
          <Linha rotulo="Plot">
            {r.posicao.plot}
            {r.posicao.ordem && r.posicao.total_plots ? ` · ${r.posicao.ordem} de ${r.posicao.total_plots}` : ""}
          </Linha>
          <Linha rotulo="Ao longo da carreira" dica="O rover não tem odômetro nem GPS: a tela não sabe em que ponto da carreira ele está.">
            não medido
          </Linha>
        </>
      ) : (
        <p className="discreto">{snap.campanha_atual ? "O painel ainda não gravou a posição." : "Campanha encerrada: o rover não está neste campo."}</p>
      )}

      {r.ultima_imagem && (
        <div className="bloco">
          <h3>Última foto analisada</h3>
          <Foto nome={r.ultima_imagem} demo={snap.demo} />
          <Linha rotulo="Plantas na foto">
            {numero(r.plantulas_ultima)} <span className="discreto">(IA: {numero(r.plantulas_ultima_bruto)})</span>
          </Linha>
          <Linha rotulo="Analisada há">{duracao(idadeAgora(r.idade_status_s, recebidoEm, agora))}</Linha>
        </div>
      )}

      <div className="bloco">
        <h3>{snap.demo ? "Sistema (desta máquina, não do rover)" : "Sistema"}</h3>
        <Linha rotulo="Fila de análise">{numero(r.fila_pendente)} fotos</Linha>
        {t ? (
          <>
            <Linha rotulo="CPU">{t.cpu_temp_c === null ? "n/d" : `${t.cpu_temp_c.toFixed(0)} °C`}</Linha>
            <Linha rotulo="Disco livre">{t.disco_livre_gb === null ? "n/d" : `${t.disco_livre_gb.toFixed(1)} GB`}</Linha>
            <Linha rotulo="Processos">
              painel {processo(t.processos.painel)} · analisador {processo(t.processos.analisador)} · câmera {processo(t.processos.capturador)}
            </Linha>
          </>
        ) : (
          <p className="discreto">Telemetria do Pi indisponível.</p>
        )}
        {alertas.map((a) => (
          <ItemAlerta key={a.codigo + a.motivo} alerta={a.alerta} motivo={a.motivo} />
        ))}
      </div>

      <div className="bloco">
        <h3>Plots em alerta ({idx.emAlerta.length})</h3>
        {idx.emAlerta.length === 0 && <p className="discreto">Nenhum.</p>}
        <ul className="lista-alertas">
          {idx.emAlerta.map((p) => (
            <li key={p.id}>
              <button onClick={() => selecionar({ tipo: "plot", id: p.id }, true)}>
                <IconeAlerta alerta={p.alerta} />
                <b>{p.id}</b>
                <span>{p.motivo}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}

function VistaPlot({ snap, plot }: { snap: Snapshot; plot: Plot }) {
  const selecionar = useEstado((e) => e.selecionar);
  const total = snap.rover.posicao?.total_plots;
  return (
    <>
      <div className="lateral-cabeca">
        <h2>Plot {plot.id}</h2>
        <div className="pilulas">
          <PilulaEstado estado={plot.estado} />
        </div>
      </div>
      {plot.fora_da_planilha && <ItemAlerta alerta="atencao" motivo="este plot não está na planilha da semeadora" />}
      <ItemAlerta alerta={plot.alerta} motivo={plot.motivo} />
      <Linha rotulo="Ordem na campanha">{total ? `${plot.ordem} de ${total}` : plot.ordem}</Linha>
      <Linha rotulo="Grãos semeados">{numero(plot.graos)}</Linha>
      <Linha rotulo="Plantas (carreiras fechadas)">{numero(plot.plantulas)}</Linha>
      <Linha rotulo="Emergência">{pct(plot.emergencia)}</Linha>

      <table className="tabela">
        <thead>
          <tr>
            <th>Linha</th>
            <th>Plantas</th>
            <th>Esperado</th>
            <th>Emerg.</th>
            <th>Fotos</th>
          </tr>
        </thead>
        <tbody>
          {plot.carreiras.map((k) => (
            <tr key={k.id} onClick={() => selecionar({ tipo: "carreira", id: k.id })} className="clicavel">
              <td>
                {k.linha} <IconeAlerta alerta={k.alerta} />
                {k.estado === "capturando" && <span className="ponto-acento" title="capturando agora" />}
              </td>
              <td>{numero(k.plantulas)}</td>
              <td>{numero(k.esperado)}</td>
              <td>{pct(k.emergencia)}</td>
              <td>{numero(k.imagens)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="botoes">
        <button className="botao" onClick={() => selecionar({ tipo: "plot", id: plot.id }, true)}>
          Centralizar
        </button>
        <button className="botao" onClick={() => selecionar(null)}>
          Voltar ao rover
        </button>
      </div>
    </>
  );
}

function Etapa({ rotulo, quando, detalhe }: { rotulo: string; quando: string | null; detalhe?: string }) {
  return (
    <li className={quando ? "feita" : ""}>
      <span className="etapa-rotulo">{rotulo}</span>
      <span className="etapa-quando">{quando ? dataHora(quando) : "ainda não"}</span>
      {detalhe && quando && <span className="discreto"> {detalhe}</span>}
    </li>
  );
}

function VistaCarreira({ plot, carreira: k }: { plot: Plot; carreira: Carreira }) {
  const selecionar = useEstado((e) => e.selecionar);
  return (
    <>
      <div className="lateral-cabeca">
        <h2>Carreira {k.id}</h2>
        <div className="pilulas">
          <PilulaEstado estado={k.estado} />
        </div>
      </div>
      <ItemAlerta alerta={k.alerta} motivo={k.motivo} />
      <Linha rotulo="Plantas (corrigido)">{numero(k.plantulas)}</Linha>
      <Linha rotulo="Detecções da IA (bruto)">{numero(k.plantulas_bruto)}</Linha>
      <Linha rotulo="Esperado (grãos ÷ carreiras)">{numero(k.esperado)}</Linha>
      <Linha rotulo="Emergência">{pct(k.emergencia)}</Linha>
      <Linha rotulo="Fotos">{numero(k.imagens)}</Linha>
      <Linha rotulo="Incerteza" dica="Vem da curva de calibração de campo (RV-08), ainda não feita.">
        pendente (RV-08)
      </Linha>

      <div className="bloco">
        <h3>Linhagem do dado</h3>
        <ol className="linhagem">
          <Etapa rotulo="Capturada" quando={k.primeira_imagem} detalhe={k.ultima_imagem ? `até ${hora(k.ultima_imagem)}` : undefined} />
          <Etapa rotulo="Analisada" quando={k.ultima_analise} />
          <Etapa rotulo="Na nuvem" quando={k.sincronizada_em} />
          <Etapa rotulo="Exportada" quando={k.exportada_em} />
        </ol>
        <Linha rotulo="Modelo">{k.versoes_modelo.join(", ") || "--"}</Linha>
        <Linha rotulo="Software">{k.versoes_software.join(", ") || "--"}</Linha>
      </div>
      <div className="botoes">
        <button className="botao" onClick={() => selecionar({ tipo: "carreira", id: k.id }, true)}>
          Centralizar
        </button>
        <button className="botao" onClick={() => selecionar({ tipo: "plot", id: plot.id })}>
          Ver plot {plot.id}
        </button>
      </div>
    </>
  );
}

export default function Painel({ snap }: { snap: Snapshot }) {
  const selecao = useEstado((e) => e.selecao);
  const idx = useIndice(snap);
  let conteudo = <VistaRover snap={snap} idx={idx} />;
  if (selecao?.tipo === "plot") {
    const p = idx.plots.get(selecao.id);
    if (p) conteudo = <VistaPlot snap={snap} plot={p} />;
  } else if (selecao?.tipo === "carreira") {
    const k = idx.carreiras.get(selecao.id);
    if (k) conteudo = <VistaCarreira plot={k.plot} carreira={k.carreira} />;
  }
  return (
    <aside className="lateral cartao" aria-label="Detalhes">
      {conteudo}
      <p className="nota">{snap.nota_contagem}</p>
    </aside>
  );
}
