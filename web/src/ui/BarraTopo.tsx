import { MODO_DEMO } from "../api";
import { duracao } from "../formato";
import { useAgora } from "../hooks";
import { useEstado } from "../store";

// Marca, experimento e o selo de conexão. "Ao vivo" só quando a última
// resposta do rover chegou há pouco; senão diz quanto tempo faz.

function Selo() {
  const conexao = useEstado((e) => e.conexao);
  const recebidoEm = useEstado((e) => e.recebidoEm);
  const agora = useAgora();
  const idade = recebidoEm === null ? null : (agora - recebidoEm) / 1000;
  if (conexao === "demo") return <span className="selo acento">foto estática da demonstração</span>;
  if (conexao === "carregando") return <span className="selo neutro">conectando ao rover…</span>;
  if (conexao === "sem_conexao")
    return (
      <span className="selo critico" role="status">
        <i /> sem conexão · último dado há {duracao(idade)}
      </span>
    );
  return (
    <span className="selo ok" role="status">
      <i /> ao vivo · atualizado há {duracao(idade)}
    </span>
  );
}

export default function BarraTopo({ demo }: { demo: boolean }) {
  const snap = useEstado((e) => e.snap);
  const experimento = useEstado((e) => e.experimento);
  const escolher = useEstado((e) => e.escolherExperimento);
  const varios = !MODO_DEMO && (snap?.experimentos.length ?? 0) > 1;
  return (
    <header className="topo cartao">
      <div className="marca">
        <b>raimunda</b>
        <span>gêmeo do ensaio</span>
      </div>
      {snap &&
        (varios ? (
          <select
            className="seletor"
            value={experimento ?? ""}
            onChange={(e) => escolher(e.target.value || null)}
            aria-label="Experimento"
          >
            <option value="">Campanha atual do painel</option>
            {snap.experimentos.map((nome) => (
              <option key={nome} value={nome}>
                {nome}
              </option>
            ))}
          </select>
        ) : (
          <span className="experimento" title="experimento">
            {snap.experimento}
          </span>
        ))}
      {snap && !snap.campanha_atual && <span className="selo neutro">campanha encerrada: sem rover</span>}
      {demo && (
        <span className="faixa-demo" role="alert">
          DEMONSTRAÇÃO · dados sintéticos, não são do rover
        </span>
      )}
      <span className="espaco" />
      <Selo />
    </header>
  );
}
