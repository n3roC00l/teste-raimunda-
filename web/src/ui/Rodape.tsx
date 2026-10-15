import { useMemo } from "react";
import { COR, faixasEmergencia } from "../cores";
import { descreverEvento, ehErro, hora } from "../formato";
import { useEstado } from "../store";
import type { Snapshot } from "../tipos";

// Legenda (sempre presente), troca de modo de cor, câmera e os últimos
// eventos. Alerta na legenda aparece com o pino: o mesmo sinal da cena.

function Amostra({ cor, rotulo, pino }: { cor: string; rotulo: string; pino?: boolean }) {
  return (
    <li>
      <i className={pino ? "amostra pino" : "amostra"} style={{ background: cor }} />
      {rotulo}
    </li>
  );
}

function Legenda({ snap }: { snap: Snapshot }) {
  const modo = useEstado((e) => e.modoCor);
  const faixas = useMemo(() => faixasEmergencia(snap.limiares), [snap.limiares]);
  return (
    <ul className="legenda">
      {modo === "estado" ? (
        <>
          <Amostra cor={COR.pendente} rotulo="pendente" />
          <Amostra cor={COR.analisada} rotulo="analisada" />
          <Amostra cor={COR.acento} rotulo="capturando agora" />
        </>
      ) : (
        <>
          {faixas.map((f) => (
            <Amostra key={f.rotulo} cor={f.cor} rotulo={f.rotulo} />
          ))}
          <Amostra cor={COR.pendente} rotulo="pendente" />
        </>
      )}
      <Amostra cor={COR.atencao} rotulo="atenção" pino />
      <Amostra cor={COR.critico} rotulo="crítico" pino />
    </ul>
  );
}

function LinhaDoTempo({ snap }: { snap: Snapshot }) {
  const eventos = snap.eventos.slice(-6).reverse();
  if (eventos.length === 0) return null;
  return (
    <ol className="linha-tempo cartao" aria-label="Últimos eventos">
      {eventos.map((ev, i) => (
        <li key={`${ev.ts}-${i}`} className={ehErro(ev.evento) ? "erro" : ""}>
          <span className="ev-hora">{hora(ev.ts)}</span>
          {descreverEvento(ev)}
        </li>
      ))}
    </ol>
  );
}

export default function Rodape({ snap }: { snap: Snapshot }) {
  const modo = useEstado((e) => e.modoCor);
  const setModo = useEstado((e) => e.setModoCor);
  const pedirCamera = useEstado((e) => e.pedirCamera);
  return (
    <footer className="rodape">
      <div className="controles cartao">
        <div className="alternador" role="radiogroup" aria-label="Cor das carreiras">
          <button role="radio" aria-checked={modo === "estado"} className={modo === "estado" ? "ativo" : ""} onClick={() => setModo("estado")}>
            Estado
          </button>
          <button role="radio" aria-checked={modo === "emergencia"} className={modo === "emergencia" ? "ativo" : ""} onClick={() => setModo("emergencia")}>
            Emergência
          </button>
        </div>
        <Legenda snap={snap} />
        <div className="botoes">
          <button className="botao" onClick={() => pedirCamera("tudo")}>
            Ver o campo todo
          </button>
          {snap.rover.posicao && (
            <button className="botao" onClick={() => pedirCamera("rover")}>
              Ir ao rover
            </button>
          )}
        </div>
        <p className="ajuda">arrastar: mover · botão direito: girar · roda: zoom</p>
      </div>
      <LinhaDoTempo snap={snap} />
    </footer>
  );
}
