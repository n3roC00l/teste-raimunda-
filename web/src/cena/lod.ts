import { useState } from "react";
import { useFrame, useThree } from "@react-three/fiber";

// Nível de detalhe pela distância da câmera ao alvo (camera-controls).
// De perto, a lavoura é desenhada planta por planta; de longe, uma planta
// teria menos de um pixel e as carreiras (a 0,5 m) virariam listras: aí cada
// carreira vira um ladrilho cheio. A folga (histerese) evita piscar quando a
// câmera para bem no limite.

/** Lavoura: plantas abaixo disto, ladrilhos acima ("Campo todo" fica ~140 m). */
export const DISTANCIA_LADRILHOS = 80;
/** Marcadores do ensaio e do rover (vista da FAPA, ~600 m). */
export const DISTANCIA_MARCADORES = 300;

const FOLGA = 0.12;

/** true quando a câmera está mais longe que `limite` (com folga). */
export function useLonge(limite: number): boolean {
  const controles = useThree((s) => s.controls) as unknown as { distance?: number } | null;
  const [longe, setLonge] = useState(false);
  useFrame(() => {
    const d = controles?.distance;
    if (d === undefined) return;
    const agora = longe ? d > limite * (1 - FOLGA) : d > limite * (1 + FOLGA);
    if (agora !== longe) setLonge(agora);
  });
  return longe;
}
