-- =====================================================================
-- FINANCIA+  ·  Migración 0002: permisos del rol de la aplicación
--
-- Decisión D-15 (borrado lógico reforzado con permisos del rol):
--   * La aplicación se conecta con el rol financia_app, que NO es dueño
--     de las tablas. Las migraciones las aplica otro rol (financia_admin).
--   * financia_app puede leer, insertar y modificar, pero NUNCA borrar:
--     no recibe DELETE (ni TRUNCATE) sobre ninguna tabla.
--   * bolsillo_valor es un historial de solo inserción (RN-44, D-09):
--     ahí financia_app recibe solo SELECT e INSERT, sin UPDATE.
--
-- Qué NO hace este archivo
--   * No crea el rol ni contiene contraseñas. El rol lo crea
--     scripts/preparar_bd.py con la contraseña que está en .env
--     (DATABASE_URL). Así ningún secreto queda en el repositorio.
--   * No da permisos sobre migracion_aplicada (tabla de control): la
--     aplicación no tiene nada que hacer con ella.
--
-- Si el rol financia_app no existe, la migración se detiene con un
-- mensaje claro y no se aplica nada (todo va en una transacción).
--
-- Nota: el bloque DO de abajo es código anónimo de un solo uso; no crea
-- ninguna función almacenada ni trigger (D-14 se mantiene).
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- 1. Comprobar que el rol existe antes de otorgar nada.
--    Sin esta comprobación, PostgreSQL daría un error técnico
--    ('role "financia_app" does not exist') difícil de entender.
-- ---------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'financia_app') THEN
    RAISE EXCEPTION 'El rol financia_app no existe. Créelo primero con scripts/preparar_bd.py y vuelva a ejecutar scripts/migrar.py.';
  END IF;
END
$$;

-- ---------------------------------------------------------------------
-- 2. Permiso para usar el esquema public (ver los objetos que contiene).
-- ---------------------------------------------------------------------
GRANT USAGE ON SCHEMA public TO financia_app;

-- ---------------------------------------------------------------------
-- 3. Las cinco tablas de datos: leer, insertar y modificar. Sin DELETE.
--    "Borrar" en la aplicación es cambiar activo/estado (RN-70).
--    Las columnas id_* son GENERATED ALWAYS AS IDENTITY: PostgreSQL usa
--    su secuencia internamente, así que no hace falta permiso extra.
-- ---------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE ON TABLE
  usuario,
  cuenta,
  categoria,
  movimiento,
  bolsillo
TO financia_app;

-- ---------------------------------------------------------------------
-- 4. Historial de valores de bolsillos: solo leer e insertar.
--    Un valor registrado nunca se modifica ni se borra (D-09).
-- ---------------------------------------------------------------------
GRANT SELECT, INSERT ON TABLE bolsillo_valor TO financia_app;

COMMIT;
