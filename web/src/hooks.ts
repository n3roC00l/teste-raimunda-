import { useEffect, useState } from "react";
import { MODO_DEMO } from "./api";

/** Relógio da tela (performance.now), para as idades andarem entre consultas. */
export function useAgora(intervaloMs = 1000): number {
  const [agora, setAgora] = useState(() => performance.now());
  useEffect(() => {
    const t = window.setInterval(() => setAgora(performance.now()), intervaloMs);
    return () => window.clearInterval(t);
  }, [intervaloMs]);
  return agora;
}

/** Idade atual de algo que tinha `idade_s` quando o snapshot chegou. As
 * idades vêm do relógio do Pi; aqui só somamos o tempo desde a resposta, sem
 * depender do relógio do tablet. No ?demo o snapshot é uma foto parada. */
export function idadeAgora(idade_s: number | null, recebidoEm: number | null, agora: number): number | null {
  if (idade_s === null || recebidoEm === null || MODO_DEMO) return idade_s;
  return idade_s + Math.max(0, (agora - recebidoEm) / 1000);
}
