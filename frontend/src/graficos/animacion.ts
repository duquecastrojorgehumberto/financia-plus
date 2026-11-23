// ¿Animar los gráficos? No, si el usuario pidió a su sistema "reducir el movimiento"
// (accesibilidad), ni donde no hay navegador de verdad (las pruebas).
export function debeAnimar(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  return !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
