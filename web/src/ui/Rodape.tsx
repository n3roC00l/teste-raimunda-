import { useMemo } from "react";
import { COR, faixasEmergencia, RAMPA_LAVOURA } from "../cores";
import { descreverEvento, ehErro, hora } from "../formato";
import { type ModoCor, useEstado } from "../store";
import type { Snapshot } from "../tipos";

// Legenda (sempre presente), troca de modo de cor, câmera e os últimos
// eventos. Alerta na legenda aparece como moldura: o mesmo sinal da cena.

function Amostra({ cor, rotulo, moldura }: { cor: string; rotulo: string; moldura?: boolean }) {
  return (
    <li>
      <i className={moldura ? "amostra moldura" : "amostra"} style={moldura ? { borderColor: cor } : { background: cor }} />
      {rotulo}
    </li>
  );
}

const MODOS: { modo: ModoCor; rotulo: string }[] = [
  { modo: "lavoura", rotulo: "Lavoura" },
  { modo: "emergencia", rotulo: "Emergência" },
  { modo: "estado", rotulo: "Estado" },
];

function Legenda({ snap }: { snap: Snapshot }) {
  const modo = useEstado((e) => e.modoCor);
  const faixas = useMemo(() => faixasEmergencia(snap.limiares), [snap.limiares]);
  const faixasLavoura = useMemo(() => faixasEmergencia(snap.limiares, RAMPA_LAVOURA), [snap.limiares]);
  const semEsperado = snap.campo.plots.some((p) => p.carreiras.some((k) => k.estado === "analisada" && k.emergencia === null));
  return (
    <ul className="legenda">
      {modo === "lavoura" ? (
        <>
          <li className="legenda-nota">de perto, as plantas contadas; de longe, a emergência:</li>
          {faixasLavoura.map((f) => (
            <Amostra key={f.rotulo} cor={f.cor} rotulo={f.rotulo} />
          ))}
          {semEsperado && <Amostra cor={COR.semEsperado} rotulo="sem grãos na planilha" />}
          <Amostra cor={COR.camalhao} rotulo="pendente (solo)" />
          <Amostra cor={COR.acento} rotulo="capturando agora" />
        </>
      ) : modo === "estado" ? (
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
      <Amostra cor={COR.atencao} rotulo="atenção" moldura />
      <Amostra cor={COR.critico} rotulo="crítico" moldura />
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

function Notas({ snap }: { snap: Snapshot }) {
  return (
    <p className="ajuda">
      rover: posição estimada · plântulas: quantidade contada, posição ilustrativa · carros, nuvens e aves: cenário
      <br />
      mapa © OpenStreetMap · prédios da FAPA aproximados{snap.campo.geo.aproximado ? " · local do ensaio aproximado" : ""}
    </p>
  );
}

export default function Rodape({ snap }: { snap: Snapshot }) {
  const modo = useEstado((e) => e.modoCor);
  const setModo = useEstado((e) => e.setModoCor);
  const pedirCamera = useEstado((e) => e.pedirCamera);
  const animacao = useEstado((e) => e.animacao);
  const setAnimacao = useEstado((e) => e.setAnimacao);
  const luz = useEstado((e) => e.luz);
  const setLuz = useEstado((e) => e.setLuz);
  return (
    <footer className="rodape">
      <div className="controles cartao">
        <div className="alternador" role="radiogroup" aria-label="Como desenhar as carreiras">
          {MODOS.map((m) => (
            <button key={m.modo} role="radio" aria-checked={modo === m.modo} className={modo === m.modo ? "ativo" : ""} onClick={() => setModo(m.modo)}>
              {m.rotulo}
            </button>
          ))}
        </div>
        <Legenda snap={snap} />
        <div className="botoes">
          <button className="botao" onClick={() => pedirCamera("tudo")}>
            Campo todo
          </button>
          {snap.rover.posicao && (
            <button className="botao" onClick={() => pedirCamera("rover")}>
              Ir ao rover
            </button>
          )}
          <button className="botao" onClick={() => pedirCamera("entorno")}>
            Ver a FAPA
          </button>
        </div>
        <div className="botoes">
          <button className="botao" aria-pressed={!animacao} onClick={() => setAnimacao(!animacao)}>
            {animacao ? "Pausar animação" : "Animar"}
          </button>
          <div className="alternador" role="radiogroup" aria-label="Luz">
            <button role="radio" aria-checked={luz === "real"} className={luz === "real" ? "ativo" : ""} onClick={() => setLuz("real")}>
              Hora real
            </button>
            <button role="radio" aria-checked={luz === "dia"} className={luz === "dia" ? "ativo" : ""} onClick={() => setLuz("dia")}>
              Sempre dia
            </button>
          </div>
        </div>
        <Notas snap={snap} />
        <p className="ajuda">arrastar: mover · botão direito: girar · roda: zoom</p>
      </div>
      <LinhaDoTempo snap={snap} />
    </footer>
  );
}
