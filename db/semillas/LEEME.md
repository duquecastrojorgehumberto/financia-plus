# db/semillas/

**Estado: sin archivos todavía.** Las categorías por defecto ya se copian al registrarse
(Tarea 7), desde `app/servicios/categorias_por_defecto.py`. Aquí irán los datos de prueba (Tarea 15).

## Categorías por defecto (RN-26)

Al registrarse, cada usuario recibe una copia de esta lista, en la misma transacción que crea
al usuario. **Implementado en `app/servicios/categorias_por_defecto.py`: si cambia la lista, hay
que cambiarla en los dos lugares.** Es una propuesta de partida; el
usuario puede renombrar, desactivar o agregar.

### Ingresos

| Categoría | Subcategorías |
| --- | --- |
| Salario | Sueldo; Primas y bonificaciones |
| Trabajo independiente | — |
| Rendimientos | — |
| Otros ingresos | Regalos; Reembolsos |

### Egresos

| Categoría | Subcategorías |
| --- | --- |
| Alimentación | Mercado; Restaurantes; Domicilios |
| Vivienda | Arriendo; Servicios públicos; Hogar y aseo |
| Transporte | Transporte público; Combustible; Taxis y aplicaciones |
| Salud | Medicamentos; Consultas |
| Educación | Matrículas; Libros y cursos |
| Entretenimiento | Suscripciones; Salidas |
| Ropa y cuidado personal | — |
| Impuestos y comisiones | 4×1.000; Comisiones bancarias |
| Otros gastos | — |

"Impuestos y comisiones" debe existir siempre: es la categoría que se propone para los cargos
de las transferencias.

## Datos de prueba

Pendiente (Tarea 15): usuarios ficticios y los escenarios CA-01 a CA-15 de
`docs/REQUISITOS.md`. Sin datos reales de personas.
