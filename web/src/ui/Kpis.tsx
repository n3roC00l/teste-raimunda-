import { duracao, hora, numero, pct } from "../formato";
import { idadeAgora, useAgora } from "../hooks";
import { useEstado } from "../store";
import type { Alerta, Snapshot } from "../tipos";
import { IconeAlerta } from "./Comum";

// Os indicadores vêm prontos do snapshot (core/campo.py). Aqui só se mostra.

function Kpi({ rotulo, valor, sub, alerta = null, barra }: { rotulo: string; valor: string; sub: string; alerta?: Alerta; barra?: number | null }) {
  return (
    <div className="kpi cartao">
      <span className="kpi-rotulo">
        {rotulo} <IconeAlerta alerta={alerta} />
      </span>
      <span className="kpi-valor">{valor}</span>
      <span className="kpi-sub">{sub}</span>
      {barra !== undefined && barra !== null && (
        <span className="kpi-barra" aria-hidden>
          <i style={{ width: `${Math.min(100, barra * 100)}%` }} />
        </span>
      )}
    </div>
  );
}

export default function Kpis({ snap }: { snap: Snapshot }) {
  const k = snap.kpis;
  const recebidoEm = useEstado((e) => e.recebidoEm);
  const agora = useAgora();
  const idadeSync = idadeAgora(k.idade_sync_s, recebidoEm, agora);
  const alertaDe = (codigo: string): Alerta =>
    [...snap.saude.alertas, ...snap.rover.alertas].find((a) => a.codigo === codigo)?.alerta ?? null;
  const alertaSync = alertaDe("backup");
  const alertaFila = alertaDe("fila");
  const alertaCarreiras: Alerta = snap.campo.plots.some((p) => p.alerta === "critico") ? "critico" : k.carreiras_em_alerta ? "atencao" : null;

  return (
    <section className="kpis" aria-label="Indicadores">
      <Kpi
        rotulo="Progresso"
        valor={pct(k.progresso)}
        sub={`${numero(k.carreiras_analisadas)} de ${numero(k.carreiras_total)} carreiras · ${numero(k.plots_concluidos)} plots`}
        barra={k.progresso}
      />
      <Kpi
        rotulo="Plantas contadas"
        valor={numero(k.plantulas)}
        sub={k.plantulas_em_captura !== null ? `+ ${numero(k.plantulas_em_captura)} na carreira atual` : `${numero(k.imagens)} fotos`}
      />
      <Kpi
        rotulo="Emergência média"
        valor={pct(k.emergencia_media)}
        sub={k.esperado !== null ? `de ${numero(Math.round(k.esperado))} esperadas` : "planilha sem grãos semeados"}
      />
      <Kpi
        rotulo="Alertas"
        valor={numero(k.carreiras_em_alerta)}
        sub={`carreiras · ${numero(k.plots_em_alerta)} plots`}
        alerta={alertaCarreiras}
      />
      <Kpi rotulo="Fila de análise" valor={numero(k.fila_pendente)} sub="fotos esperando o YOLO" alerta={alertaFila} />
      <Kpi
        rotulo="Último backup"
        valor={k.ultima_sync ? `há ${duracao(idadeSync)}` : "nenhum"}
        sub={k.ultima_sync ? `às ${hora(k.ultima_sync)}` : "nuvem ainda não recebeu nada"}
        alerta={alertaSync}
      />
    </section>
  );
}
