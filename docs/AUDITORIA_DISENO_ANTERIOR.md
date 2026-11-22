# Auditoría del diseño anterior

Qué se revisó, qué se conserva del diseño "Fase 1" y qué se descarta o aplaza. Sirve para
que nadie tenga que repetir esta revisión.

## 1. Qué se revisó y qué existe realmente

| Material | Hallazgo |
| --- | --- |
| Documento "FINANCIA+ · Fase 1: Diseño de la base de datos" | El PDF no estaba adjunto en la solicitud. Se revisó su contenido de origen (el documento de diseño de la Fase 1, secciones 1 a 11). La sección 12 de ese documento nunca se completó. Se trata como **referencia histórica**. |
| Scripts SQL del diseño anterior (`01_esquema.sql`, `02_funciones_factura.sql`, etc.) | Existen como entregables sueltos de la Fase 1, fuera de este proyecto. Implementan el modelo de 26 tablas, que ya no es el vigente. **No se copiaron a este proyecto y no deben usarse como base.** |
| Proyecto o repositorio de la aplicación | No existía. No había código de aplicación, migraciones ni repositorio Git. |
| Borradores originales (documentos 01 a 05 y 07) | Describen el sistema con facturas y Gmail. Quedan como antecedente; el alcance vigente es el de `REQUISITOS.md`. |

Conclusión: este proyecto empieza desde cero. Lo único que se hereda son **ideas de diseño**.

## 2. Contradicciones del diseño anterior con los requisitos actuales

| Diseño anterior | Requisito actual | Resolución |
| --- | --- | --- |
| El bolsillo pertenece a una cuenta. | El bolsillo no está ligado a ninguna cuenta. | Se elimina la relación (D-10). |
| El saldo del bolsillo sale de movimientos APARTADO y RETIRO. | El usuario escribe el valor directamente; no hay aportes ni retiros. | Historial `bolsillo_valor` (D-09). |
| La meta es una tabla aparte (`meta_ahorro`) ligada a un bolsillo. | No crear tabla de metas si basta una modalidad de bolsillo. | `bolsillo.monto_objetivo` (D-08). |
| "Disponible" se calcula por cuenta (saldo − sus bolsillos). | Disponible = saldo total − total reservado, a nivel de usuario. | Se recalcula (RN-62). |
| Un movimiento tiene 1 o más líneas con categoría. | Una sola categoría por movimiento. | `movimiento.id_categoria` (D-06). |
| Las transferencias no tienen cargos. | Cargos (4×1.000, comisiones) asociados y trazables. | EGRESO enlazado (D-05). |
| No hay forma de ajustar el saldo. | Se pide una solución para discrepancias. | Movimientos de ajuste (D-12). |
| Tarjeta de crédito como tipo de cuenta; saldo inicial negativo. | Tarjetas y deudas aplazadas. | Se quita el tipo; saldo inicial ≥ 0. |
| Ingresos con naturaleza FIJO o VARIABLE obligatoria. | No está entre los datos del movimiento. | Se elimina la columna. |
| Movimientos PENDIENTE y DESCARTADO (recurrentes). | Recurrentes aplazados. | Solo VIGENTE y ANULADO. |
| Usuario con tipo y número de documento, normalizados. | Solo servían para validar facturas. | Se eliminan. |
| Árbol de categorías de profundidad libre, con ramas movibles. | "Categorías y subcategorías"; priorizar simplicidad. | Dos niveles, padre inmutable (D-13). |
| 77 triggers, 2 funciones, 5 vistas. | Triggers solo si son indispensables. | Cero triggers (D-14). |
| Tablas creadas desde ya para Gmail y facturas. | No crear tablas vacías para el futuro. | Se aplazan (D-01). |
| Auditoría automática de todas las tablas. | Auditoría avanzada aplazada. | Se elimina (D-17). |

## 3. Destino de las 26 tablas anteriores

| Tabla anterior | Destino | Detalle |
| --- | --- | --- |
| `usuario` | **Se conserva, simplificada** | Sin documento, sin rol, sin columnas normalizadas generadas. |
| `cuenta` | **Se conserva, simplificada** | Sin moneda, sin "predeterminada"; tipo como CHECK; saldo inicial ≥ 0. |
| `categoria` | **Se conserva, simplificada** | Sin concepto tributario; dos niveles. |
| `movimiento` | **Se conserva, modificada** | Tipos nuevos; gana `id_categoria` e `id_transferencia`; pierde bolsillo, naturaleza y recurrente. |
| `bolsillo` | **Se conserva, rediseñada** | Sin cuenta; gana descripción, monto y fecha objetivo. |
| — | **Nueva: `bolsillo_valor`** | Historial de valores. |
| `meta_ahorro` | Eliminada | Absorbida por `bolsillo`. |
| `movimiento_linea` | Eliminada | Evolución futura documentada. |
| `preferencia_usuario` | Eliminada | No hay alertas configurables en la versión 1. |
| `tipo_cuenta` | Eliminada | Reemplazada por un CHECK. |
| `transicion_estado` | Eliminada | Solo queda VIGENTE ⇄ ANULADO; no justifica un catálogo. |
| `plantilla_categoria` | Eliminada como tabla | Las categorías por defecto serán datos semilla que el servicio de registro copia. |
| `recurrente` | Aplazada | Movimientos recurrentes. |
| `presupuesto` | Aplazada | Presupuestos. |
| `notificacion` | Aplazada | Notificaciones. |
| `evento_auditoria` | Aplazada | Auditoría avanzada. |
| `concepto_tributario`, `parametro_renta` | Aplazadas | Informes tributarios. |
| `factura`, `identificador_factura`, `factura_archivo`, `factura_item`, `archivo_fuente`, `lote_importacion`, `importacion`, `regla_clasificacion` | Aplazadas | Facturas electrónicas. |
| `conexion_gmail` | Aplazada | Integración con Gmail. |

Resumen: de 26 tablas quedan 5 (todas simplificadas), se agrega 1, se eliminan 6 y se aplazan 15.

## 4. Ideas del diseño anterior que sí se conservan

Estas ideas se probaron en la Fase 1 y siguen siendo correctas:

1. **Claves foráneas compuestas de propiedad** `(id_usuario, id_x)`.
2. **Igualdad de tipo mediante una FK** que incluye la columna `tipo`.
3. **Transferencia en una sola fila**, con CHECK "destino distinto del origen".
4. **CHECK de forma** por tipo de movimiento.
5. **Saldos calculados**, nunca guardados.
6. **Borrado lógico**: archivar, desactivar, anular.
7. **Índices únicos parciales** para "único entre los activos".
8. **Dinero en `numeric(14,2)`.**

## 5. Dos lecciones técnicas de la Fase 1 que hay que recordar

- **Un CHECK cuyo resultado es NULL se considera cumplido.** `columna IN ('A','B')` deja
  pasar un NULL. Hay que escribir `columna IS NOT NULL AND columna IN (...)`, o declarar la
  columna `NOT NULL`. Aplica directamente al CHECK de forma de `movimiento`.
- **`UNIQUE` trata dos NULL como distintos.** Por eso el índice de nombres entre hermanas usa
  `COALESCE(id_padre, 0)`: sin él, dos categorías raíz podrían llamarse igual.
