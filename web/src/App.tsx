import { MODO_DEMO } from "./api";
import Cena from "./cena/Cena";
import { useEstado } from "./store";
import BarraTopo from "./ui/BarraTopo";
import Kpis from "./ui/Kpis";
import Painel from "./ui/Painel";
import Rodape from "./ui/Rodape";

// Layout: barra no topo; a cena ao centro (indicadores e legenda flutuam
// por cima, nas bordas); o painel lateral AO LADO da cena, para nunca
// esconder parte do campo.

function Espera() {
  const conexao = useEstado((e) => e.conexao);
  const erro = useEstado((e) => e.erro);
  return (
    <div className="espera">
      {conexao === "sem_conexao" ? (
        <>
          <h1>Sem conexão com o rover</h1>
          <p>Tentando de novo a cada 2 s. {erro && <span className="discreto">({erro})</span>}</p>
          <p className="discreto">
            Confira se o tablet está na mesma rede do Pi e se o <code>visao.service</code> está rodando.
          </p>
        </>
      ) : (
        <h1>Conectando ao rover…</h1>
      )}
    </div>
  );
}

export default function App() {
  const snap = useEstado((e) => e.snap);
  const demo = MODO_DEMO || Boolean(snap?.demo);
  return (
    <div className="app">
      <BarraTopo demo={demo} />
      <main className="palco">
        {snap ? <Cena /> : <Espera />}
        {snap && <Kpis snap={snap} />}
        {snap && <Rodape snap={snap} />}
      </main>
      {snap && <Painel snap={snap} />}
    </div>
  );
}
