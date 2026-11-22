// Campo para escribir dinero. Se reutiliza en cuentas, movimientos, bolsillos...
//
// Es un campo de TEXTO (no type="number"): así el valor nunca pasa por un número
// de JavaScript y no se pierden centavos. Debajo muestra cómo quedó el monto
// ("$ 1.032.700,50") para que el usuario detecte un cero de más o de menos.
import { dineroParaEnviar, esDineroValido, formatearDinero } from "../util/formato";

interface Propiedades {
  etiqueta: string;
  valor: string;
  alCambiar: (valor: string) => void;
  deshabilitado?: boolean;
  ayuda?: string;
}

export function CampoDinero({ etiqueta, valor, alCambiar, deshabilitado = false, ayuda }: Propiedades) {
  const vistaPrevia = esDineroValido(valor) ? formatearDinero(dineroParaEnviar(valor)) : null;
  return (
    <label>
      {etiqueta}
      <input type="text" inputMode="decimal" value={valor} onChange={(e) => alCambiar(e.target.value)}
             disabled={deshabilitado} placeholder="0" required />
      <span className="ayuda">
        {vistaPrevia ?? "Solo números, sin puntos de miles. Centavos con coma: 150000,50"}
        {ayuda && <> · {ayuda}</>}
      </span>
    </label>
  );
}
