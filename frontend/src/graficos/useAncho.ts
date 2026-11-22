// Mide el ancho de un elemento y lo vuelve a medir cuando cambia (al girar el celular,
// al cambiar el tamaño de la ventana...). Los gráficos lo usan para dibujarse a la medida
// y para cambiar la distribución en pantallas angostas.
import { useEffect, useRef, useState } from "react";

export const ANCHO_ANGOSTO = 520;   // menos que esto: distribución de celular

export function useAncho<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [ancho, setAncho] = useState(0);

  useEffect(() => {
    const elemento = ref.current;
    if (!elemento) return;
    const observador = new ResizeObserver(([entrada]) => setAncho(Math.floor(entrada.contentRect.width)));
    observador.observe(elemento);
    return () => observador.disconnect();
  }, []);

  return { ref, ancho };
}
