# db/semillas/

**Estado:** `datos_prueba.sql` hecho (Tarea 15). Las categorías por defecto se copian al
registrarse (Tarea 7), desde `app/servicios/categorias_por_defecto.py`.

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

## Datos de prueba (`datos_prueba.sql`)

Tres usuarios ficticios (`ana@demo.example`, `beto@demo.example`, `carla@demo.example`) con los
escenarios de CA-01 a CA-15. Contraseña de los tres, **solo para la demostración local**:
`demo-financia-2026`. Sin datos de personas reales.

El encabezado del archivo dice qué debe verse en cada cuenta, bolsillo y resumen;
`tests/test_datos_prueba.py` comprueba cada uno de esos valores.

Cargarlo en la base de desarrollo (se puede ejecutar varias veces: si ya están, no hace nada):

```powershell
.venv\Scripts\python scripts\cargar_datos_prueba.py
```

Si cambia la lista de categorías por defecto, hay que cambiarla también en `datos_prueba.sql`
(la prueba `test_las_categorias_por_defecto_son_las_de_rn26` avisa si no coinciden).
