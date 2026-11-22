# scripts/

**Estado:** `migrar.py`, `preparar_bd.py` y `preparar_windows.ps1` escritos y ejecutados.

Utilidades que se ejecutan a mano desde la terminal.

| Script previsto | Qué hará | Tarea |
| --- | --- | --- |
| `preparar_windows.ps1` | Instala lo que falte en Windows, crea `.env`, rol y bases, migra y ejecuta las pruebas | 1 |
| `preparar_bd.py` | Crea `.env`, los roles `financia_admin` y `financia_app` y las bases (lo usa el anterior) | 1 y 4 |
| `migrar.py` | Aplica en orden las migraciones pendientes y las registra | 2 |
| `cargar_datos_prueba.py` | Carga los datos de prueba en una base de desarrollo | 15 |

Ningún script debe borrar una base de datos ni datos de usuarios.
