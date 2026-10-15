import type { ReactNode } from "react";
import type { Alerta } from "../tipos";

// Peças pequenas da interface. Regra do painel (ui/tema.py): texto é sempre
// neutro; cor de status só no ícone/pílula, e sempre com rótulo junto.

export function IconeAlerta({ alerta }: { alerta: Alerta }) {
  if (!alerta) return null;
  return (
    <span className={`icone-alerta ${alerta}`} role="img" aria-label={alerta === "critico" ? "crítico" : "atenção"}>
      {alerta === "critico" ? "!!" : "!"}
    </span>
  );
}

export type Tom = "neutro" | "ok" | "atencao" | "critico" | "acento";

export function Pilula({ tom, children }: { tom: Tom; children: ReactNode }) {
  return <span className={`pilula ${tom}`}>{children}</span>;
}

export function Linha({ rotulo, children, dica }: { rotulo: string; children: ReactNode; dica?: string }) {
  return (
    <div className="linha-kv" title={dica}>
      <span className="kv-rotulo">{rotulo}</span>
      <span className="kv-valor">{children}</span>
    </div>
  );
}

export function ItemAlerta({ alerta, motivo }: { alerta: Alerta; motivo: string | null }) {
  if (!alerta) return null;
  return (
    <div className="item-alerta">
      <IconeAlerta alerta={alerta} />
      <span>
        <b>{alerta === "critico" ? "Crítico" : "Atenção"}:</b> {motivo}
      </span>
    </div>
  );
}

const TOM_ANALISADOR: Record<string, [string, Tom]> = {
  parado: ["parado", "neutro"],
  carregando: ["carregando modelo", "atencao"],
  pronto: ["pronto", "ok"],
  analisando: ["analisando", "ok"],
  erro: ["erro", "critico"],
  desconhecido: ["sem status", "neutro"],
};

export function PilulaAnalisador({ estado }: { estado: string }) {
  const [texto, tom] = TOM_ANALISADOR[estado] ?? [estado, "neutro"];
  return <Pilula tom={tom}>analisador {texto}</Pilula>;
}
