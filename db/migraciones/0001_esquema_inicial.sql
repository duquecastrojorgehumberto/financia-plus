-- =====================================================================
-- FINANCIA+  ·  Migración 0001: esquema inicial
--
-- Crea las 6 tablas de la versión 1, tal como las define
-- docs/MODELO_DATOS.md (sección 4):
--     usuario, cuenta, categoria, movimiento, bolsillo, bolsillo_valor
--
-- ESTADO: escrito y revisado a mano. TODAVÍA NO SE HA EJECUTADO.
--
-- Cómo leer este archivo
--   * Todo va entre BEGIN y COMMIT: si una sentencia falla, no queda nada.
--   * Las restricciones tienen nombre: pk_ (clave primaria), fk_ (foránea),
--     uq_ (única), ck_ (CHECK), ix_ (índice).
--   * No hay triggers, funciones ni vistas (decisión D-14).
--   * Ninguna clave foránea usa ON DELETE CASCADE (borrado lógico, RN-70).
--
-- Tres ideas de PostgreSQL que explican por qué está escrito así
--
--   1) FK COMPUESTA DE PROPIEDAD (decisión D-02).
--      Una tabla hija no apunta solo a id_cuenta, sino a la pareja
--      (id_usuario, id_cuenta). Como el id_usuario de la hija forma parte
--      de la clave foránea, la base solo encuentra pareja si la cuenta es
--      del MISMO usuario. Para poder apuntar a esa pareja, la tabla padre
--      declara UNIQUE (id_usuario, id_cuenta).
--
--   2) NULL EN UNA CLAVE FORÁNEA (comportamiento por defecto, MATCH SIMPLE).
--      Si CUALQUIER columna de la FK es NULL, la FK no se evalúa.
--      Lo usamos a propósito: en una transferencia id_categoria es NULL y
--      la FK de categoría simplemente no aplica. Solo es seguro porque las
--      demás columnas de cada FK (id_usuario, tipo, id_cuenta) son NOT NULL:
--      la única que puede "apagar" la FK es la columna opcional.
--
--   3) NULL EN UN CHECK.
--      Un CHECK rechaza la fila solo si el resultado es FALSO. Si el
--      resultado es NULL (desconocido), la fila PASA. Por eso los CHECK de
--      este archivo preguntan siempre con IS NULL / IS NOT NULL, que nunca
--      devuelven NULL, antes de comparar valores.
--
-- Requisito de la base de datos
--   Debe crearse con codificación UTF8. La unicidad de nombres "sin
--   distinguir mayúsculas" usa lower(); con una configuración regional "C"
--   lower() solo convierte letras sin tilde, y "ÁREA" y "área" se tratarían
--   como nombres distintos.
-- =====================================================================

BEGIN;

-- =====================================================================
-- 1. usuario
-- =====================================================================
CREATE TABLE usuario (
  id_usuario  bigint      GENERATED ALWAYS AS IDENTITY,
  nombre      text        NOT NULL,
  correo      text        NOT NULL,
  clave_hash  text        NOT NULL,
  activo      boolean     NOT NULL DEFAULT true,
  creado_en   timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT pk_usuario PRIMARY KEY (id_usuario),

  -- RN-01: el correo no se repite.
  CONSTRAINT uq_usuario_correo UNIQUE (correo),

  -- RN-01: el correo se guarda ya normalizado (minúsculas, sin espacios
  -- alrededor). Así UNIQUE compara bien: no pueden existir "Ana@x.com" y
  -- "ana@x.com" como dos usuarios. La aplicación normaliza antes de guardar.
  CONSTRAINT ck_usuario_correo CHECK (correo = lower(btrim(correo)) AND correo <> ''),

  -- No vacío y sin espacios al inicio ni al final.
  CONSTRAINT ck_usuario_nombre CHECK (nombre = btrim(nombre) AND nombre <> '')
);

COMMENT ON TABLE  usuario            IS 'Persona registrada. Es dueña de todas sus cuentas, categorías, movimientos y bolsillos.';
COMMENT ON COLUMN usuario.id_usuario IS 'Identificador interno del usuario (lo asigna PostgreSQL).';
COMMENT ON COLUMN usuario.nombre     IS 'Nombre para mostrar. No vacío.';
COMMENT ON COLUMN usuario.correo     IS 'Correo con el que inicia sesión. Único, en minúsculas y sin espacios.';
COMMENT ON COLUMN usuario.clave_hash IS 'Hash de la contraseña. Nunca se guarda la contraseña en texto.';
COMMENT ON COLUMN usuario.activo     IS 'false = usuario desactivado (borrado lógico).';
COMMENT ON COLUMN usuario.creado_en  IS 'Fecha y hora de registro.';


-- =====================================================================
-- 2. cuenta
--    El saldo actual NO se guarda: se calcula con los movimientos (D-11).
-- =====================================================================
CREATE TABLE cuenta (
  id_cuenta      bigint        GENERATED ALWAYS AS IDENTITY,
  id_usuario     bigint        NOT NULL,
  nombre         text          NOT NULL,
  tipo           text          NOT NULL DEFAULT 'OTRA',
  saldo_inicial  numeric(14,2) NOT NULL DEFAULT 0,
  activa         boolean       NOT NULL DEFAULT true,
  creado_en      timestamptz   NOT NULL DEFAULT now(),

  CONSTRAINT pk_cuenta PRIMARY KEY (id_cuenta),

  CONSTRAINT fk_cuenta_usuario FOREIGN KEY (id_usuario)
    REFERENCES usuario (id_usuario),

  -- Superclave para las FK de propiedad de movimiento.
  -- (id_cuenta ya es único por ser PK; esta restricción existe solo para
  --  que otras tablas puedan apuntar a la pareja usuario + cuenta.)
  CONSTRAINT uq_cuenta_propiedad UNIQUE (id_usuario, id_cuenta),

  CONSTRAINT ck_cuenta_nombre CHECK (nombre = btrim(nombre) AND nombre <> ''),

  -- D-16: lista corta y fija. No existe TARJETA_CREDITO (deudas aplazadas).
  CONSTRAINT ck_cuenta_tipo CHECK (tipo IN ('EFECTIVO','AHORROS','CORRIENTE','BILLETERA_DIGITAL','OTRA')),

  -- RN-10: cero o positivo.
  CONSTRAINT ck_cuenta_saldo_inicial CHECK (saldo_inicial >= 0)
);

-- No se repite el nombre entre las cuentas ACTIVAS del mismo usuario, sin
-- distinguir mayúsculas. Es un índice único PARCIAL: solo vigila las filas
-- que cumplen el WHERE. Consecuencias (todas buscadas):
--   * dos usuarios distintos pueden tener cada uno su cuenta "Nequi";
--   * una cuenta archivada no impide crear otra con el mismo nombre;
--   * reactivar una archivada falla si ya hay una activa con ese nombre.
CREATE UNIQUE INDEX uq_cuenta_nombre_activa
  ON cuenta (id_usuario, lower(nombre))
  WHERE activa;

COMMENT ON TABLE  cuenta               IS 'Lugar donde está el dinero real del usuario (Nequi, Nubank, Efectivo...). Se administra a mano.';
COMMENT ON COLUMN cuenta.id_cuenta     IS 'Identificador interno de la cuenta.';
COMMENT ON COLUMN cuenta.id_usuario    IS 'Dueño de la cuenta.';
COMMENT ON COLUMN cuenta.nombre        IS 'Nombre que le da el usuario. Único entre sus cuentas activas, sin distinguir mayúsculas.';
COMMENT ON COLUMN cuenta.tipo          IS 'EFECTIVO, AHORROS, CORRIENTE, BILLETERA_DIGITAL u OTRA.';
COMMENT ON COLUMN cuenta.saldo_inicial IS 'Saldo con el que empieza la cuenta (cero o positivo). El saldo actual se calcula, no se guarda.';
COMMENT ON COLUMN cuenta.activa        IS 'false = archivada. Solo se archiva con saldo calculado 0 (RN-12, lo valida el servicio).';
COMMENT ON COLUMN cuenta.creado_en     IS 'Fecha y hora de creación.';


-- =====================================================================
-- 3. categoria
--    Una subcategoría es una categoría con padre (relación recursiva).
-- =====================================================================
CREATE TABLE categoria (
  id_categoria  bigint      GENERATED ALWAYS AS IDENTITY,
  id_usuario    bigint      NOT NULL,
  id_padre      bigint,
  nombre        text        NOT NULL,
  tipo          text        NOT NULL,
  activa        boolean     NOT NULL DEFAULT true,
  creado_en     timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT pk_categoria PRIMARY KEY (id_categoria),

  CONSTRAINT fk_categoria_usuario FOREIGN KEY (id_usuario)
    REFERENCES usuario (id_usuario),

  -- Superclave para FK de propiedad.
  CONSTRAINT uq_categoria_propiedad UNIQUE (id_usuario, id_categoria),

  -- Superclave que además incluye el tipo. A ella apuntan las FK que
  -- exigen "mismo usuario Y mismo tipo" (la de padre y la de movimiento).
  CONSTRAINT uq_categoria_propiedad_tipo UNIQUE (id_usuario, id_categoria, tipo),

  -- RN-23: el padre es del mismo usuario y del mismo tipo.
  -- Correspondencia de columnas, en orden:
  --     hija.id_usuario -> padre.id_usuario
  --     hija.id_padre   -> padre.id_categoria
  --     hija.tipo       -> padre.tipo
  -- Si id_padre es NULL (categoría raíz) la FK no se evalúa.
  CONSTRAINT fk_categoria_padre FOREIGN KEY (id_usuario, id_padre, tipo)
    REFERENCES categoria (id_usuario, id_categoria, tipo),

  CONSTRAINT ck_categoria_nombre CHECK (nombre = btrim(nombre) AND nombre <> ''),

  -- RN-20.
  CONSTRAINT ck_categoria_tipo CHECK (tipo IN ('INGRESO','EGRESO')),

  -- Una categoría no es su propio padre. Con id_padre NULL la comparación
  -- da NULL y el CHECK pasa: es lo correcto, una raíz no tiene padre.
  CONSTRAINT ck_categoria_padre_distinto CHECK (id_padre <> id_categoria)
);

-- RN-24: no se repite el nombre entre hermanas activas, ni entre raíces
-- activas del mismo tipo.
--
-- Por qué COALESCE(id_padre, 0): para un índice único, dos NULL son valores
-- DISTINTOS. Sin el COALESCE, dos categorías raíz (id_padre NULL) podrían
-- llamarse igual. COALESCE convierte el NULL en 0, y 0 nunca es un
-- id_categoria real porque la identidad empieza en 1.
--
-- Por qué incluye tipo: las hijas de un mismo padre siempre tienen el tipo
-- del padre (lo obliga fk_categoria_padre), así que para ellas no cambia
-- nada. Para las raíces sí: permite "Otros" de INGRESO y "Otros" de EGRESO.
CREATE UNIQUE INDEX uq_categoria_hermanas_activas
  ON categoria (id_usuario, tipo, COALESCE(id_padre, 0), lower(nombre))
  WHERE activa;

COMMENT ON TABLE  categoria              IS 'Categorías y subcategorías de cada usuario, de ingreso o de egreso.';
COMMENT ON COLUMN categoria.id_categoria IS 'Identificador interno de la categoría.';
COMMENT ON COLUMN categoria.id_usuario   IS 'Dueño de la categoría.';
COMMENT ON COLUMN categoria.id_padre     IS 'Categoría padre; NULL si es raíz. Mismo usuario y mismo tipo. No cambia después de creada (RN-22). Máximo dos niveles (RN-21, lo valida el servicio).';
COMMENT ON COLUMN categoria.nombre       IS 'Nombre visible. Único entre hermanas activas, sin distinguir mayúsculas.';
COMMENT ON COLUMN categoria.tipo         IS 'INGRESO o EGRESO. No cambia después de creada (RN-22).';
COMMENT ON COLUMN categoria.activa       IS 'false = desactivada: conserva su historia y no admite movimientos nuevos (RN-25).';
COMMENT ON COLUMN categoria.creado_en    IS 'Fecha y hora de creación.';


-- =====================================================================
-- 4. movimiento
--    Registro fuente de todo cambio en el saldo de las cuentas.
--    Un supertipo con cinco tipos en una sola tabla (D-03):
--      INGRESO / EGRESO      entra o sale dinero; llevan UNA categoría.
--      TRANSFERENCIA         una sola fila con origen y destino (D-04).
--      AJUSTE_AUMENTO /      corrigen la diferencia con el saldo real;
--      AJUSTE_DISMINUCION    no son ingreso ni gasto (D-12).
-- =====================================================================
CREATE TABLE movimiento (
  id_movimiento      bigint        GENERATED ALWAYS AS IDENTITY,
  id_usuario         bigint        NOT NULL,
  tipo               text          NOT NULL,
  id_cuenta          bigint        NOT NULL,
  id_cuenta_destino  bigint,
  id_categoria       bigint,
  id_transferencia   bigint,
  monto              numeric(14,2) NOT NULL,
  fecha              date          NOT NULL,
  descripcion        text,
  estado             text          NOT NULL DEFAULT 'VIGENTE',
  creado_en          timestamptz   NOT NULL DEFAULT now(),
  actualizado_en     timestamptz   NOT NULL DEFAULT now(),

  CONSTRAINT pk_movimiento PRIMARY KEY (id_movimiento),

  CONSTRAINT fk_movimiento_usuario FOREIGN KEY (id_usuario)
    REFERENCES usuario (id_usuario),

  -- Superclave para FK de propiedad (por si otra tabla futura apunta aquí).
  CONSTRAINT uq_movimiento_propiedad UNIQUE (id_usuario, id_movimiento),

  -- Superclave que además incluye la cuenta. A ella apunta la FK del cargo.
  CONSTRAINT uq_movimiento_propiedad_cuenta UNIQUE (id_usuario, id_movimiento, id_cuenta),

  -- ---------------- Claves foráneas de propiedad ----------------

  -- La cuenta afectada es del mismo usuario.
  --     mov.id_usuario -> cuenta.id_usuario
  --     mov.id_cuenta  -> cuenta.id_cuenta
  -- Las dos columnas son NOT NULL: esta FK se evalúa siempre.
  CONSTRAINT fk_movimiento_cuenta FOREIGN KEY (id_usuario, id_cuenta)
    REFERENCES cuenta (id_usuario, id_cuenta),

  -- La cuenta destino es del mismo usuario.
  --     mov.id_usuario        -> cuenta.id_usuario
  --     mov.id_cuenta_destino -> cuenta.id_cuenta
  -- Solo se evalúa cuando hay destino (transferencias).
  CONSTRAINT fk_movimiento_cuenta_destino FOREIGN KEY (id_usuario, id_cuenta_destino)
    REFERENCES cuenta (id_usuario, id_cuenta),

  -- RN-31: la categoría es del mismo usuario Y de tipo igual al del movimiento.
  --     mov.id_usuario   -> categoria.id_usuario
  --     mov.id_categoria -> categoria.id_categoria
  --     mov.tipo         -> categoria.tipo
  -- Un EGRESO solo encuentra pareja en una categoría EGRESO; un INGRESO, en
  -- una INGRESO. Solo se evalúa cuando hay categoría. (En los demás tipos
  -- id_categoria debe ser NULL; eso lo exige ck_movimiento_forma.)
  CONSTRAINT fk_movimiento_categoria FOREIGN KEY (id_usuario, id_categoria, tipo)
    REFERENCES categoria (id_usuario, id_categoria, tipo),

  -- RN-34 y RN-35: el cargo apunta a un movimiento del mismo usuario que
  -- tiene LA MISMA cuenta (la de origen de la transferencia).
  --     cargo.id_usuario       -> transferencia.id_usuario
  --     cargo.id_transferencia -> transferencia.id_movimiento
  --     cargo.id_cuenta        -> transferencia.id_cuenta
  -- Solo se evalúa cuando id_transferencia tiene valor.
  -- Efecto adicional: no se puede cambiar la cuenta de origen de una
  -- transferencia que ya tiene cargos (RN-72), porque los cargos dejarían
  -- de encontrar su pareja.
  -- LÍMITE CONOCIDO: esta FK no comprueba que el movimiento apuntado sea
  -- de tipo TRANSFERENCIA. Esa parte de RN-34 la garantiza el servicio.
  CONSTRAINT fk_movimiento_transferencia FOREIGN KEY (id_usuario, id_transferencia, id_cuenta)
    REFERENCES movimiento (id_usuario, id_movimiento, id_cuenta),

  -- ---------------- Reglas de valores ----------------

  CONSTRAINT ck_movimiento_tipo CHECK (
    tipo IN ('INGRESO','EGRESO','TRANSFERENCIA','AJUSTE_AUMENTO','AJUSTE_DISMINUCION')),

  -- RN-30. El valor se redondea a 2 decimales ANTES de evaluar el CHECK:
  -- 0.004 se guarda como 0.00 y se rechaza.
  CONSTRAINT ck_movimiento_monto CHECK (monto > 0),

  -- RN-70: solo VIGENTE cuenta en saldos y resúmenes.
  CONSTRAINT ck_movimiento_estado CHECK (estado IN ('VIGENTE','ANULADO')),

  -- Un movimiento no puede ser cargo de sí mismo. Sin esta regla, la FK
  -- fk_movimiento_transferencia lo aceptaría (mismo usuario, misma cuenta).
  -- Con id_transferencia NULL el resultado es NULL y pasa: es lo correcto.
  CONSTRAINT ck_movimiento_cargo_distinto CHECK (id_transferencia <> id_movimiento),

  -- Cada tipo usa exactamente las columnas que le corresponden
  -- (tabla de la sección 4.4 de MODELO_DATOS.md).
  --
  -- Revisión de NULL: tipo es NOT NULL. Dentro de cada rama, las preguntas
  -- IS NULL / IS NOT NULL nunca devuelven NULL. Las dos comparaciones de
  -- valores (destino <> origen, descripción no vacía) van acompañadas, en
  -- la misma rama, de su "IS NOT NULL": si el dato falta, esa rama da FALSO,
  -- no NULL. Por tanto el CHECK completo nunca da NULL: o una rama es
  -- verdadera y la fila pasa, o todas son falsas y la fila se rechaza.
  CONSTRAINT ck_movimiento_forma CHECK (
       (    tipo = 'INGRESO'
        AND id_categoria      IS NOT NULL
        AND id_cuenta_destino IS NULL
        AND id_transferencia  IS NULL)
    OR (    tipo = 'EGRESO'
        AND id_categoria      IS NOT NULL
        AND id_cuenta_destino IS NULL)
        -- id_transferencia es opcional: con valor, el egreso es un cargo.
    OR (    tipo = 'TRANSFERENCIA'
        AND id_categoria      IS NULL
        AND id_cuenta_destino IS NOT NULL
        AND id_cuenta_destino <> id_cuenta
        AND id_transferencia  IS NULL)
    OR (    tipo IN ('AJUSTE_AUMENTO','AJUSTE_DISMINUCION')
        AND id_categoria      IS NULL
        AND id_cuenta_destino IS NULL
        AND id_transferencia  IS NULL
        AND descripcion       IS NOT NULL
        AND btrim(descripcion) <> '')
  )
);

-- Índices (cada uno responde a una consulta concreta).

-- Historial y resúmenes por periodo.
CREATE INDEX ix_movimiento_usuario_fecha
  ON movimiento (id_usuario, fecha DESC);

-- Saldo de una cuenta: movimientos donde la cuenta es la afectada / el origen.
CREATE INDEX ix_movimiento_cuenta
  ON movimiento (id_usuario, id_cuenta);

-- Saldo de una cuenta: transferencias que recibe.
CREATE INDEX ix_movimiento_cuenta_destino
  ON movimiento (id_usuario, id_cuenta_destino)
  WHERE id_cuenta_destino IS NOT NULL;

-- Totales por categoría.
CREATE INDEX ix_movimiento_categoria
  ON movimiento (id_usuario, id_categoria)
  WHERE id_categoria IS NOT NULL;

-- Cargos de una transferencia (y revisión rápida de fk_movimiento_transferencia).
CREATE INDEX ix_movimiento_transferencia
  ON movimiento (id_transferencia)
  WHERE id_transferencia IS NOT NULL;

COMMENT ON TABLE  movimiento                   IS 'Ingresos, egresos, transferencias y ajustes de saldo. Es el registro fuente de los saldos de las cuentas.';
COMMENT ON COLUMN movimiento.id_movimiento     IS 'Identificador interno del movimiento.';
COMMENT ON COLUMN movimiento.id_usuario        IS 'Dueño del movimiento.';
COMMENT ON COLUMN movimiento.tipo              IS 'INGRESO, EGRESO, TRANSFERENCIA, AJUSTE_AUMENTO o AJUSTE_DISMINUCION. No cambia después de creado (RN-72).';
COMMENT ON COLUMN movimiento.id_cuenta         IS 'Cuenta afectada. En una transferencia es la cuenta de origen.';
COMMENT ON COLUMN movimiento.id_cuenta_destino IS 'Cuenta que recibe el dinero. Solo en TRANSFERENCIA y distinta de la de origen.';
COMMENT ON COLUMN movimiento.id_categoria      IS 'Categoría o subcategoría. Obligatoria en INGRESO y EGRESO (del mismo tipo); NULL en los demás.';
COMMENT ON COLUMN movimiento.id_transferencia  IS 'Solo en un EGRESO que es cargo (4x1.000, comisión) de una transferencia: apunta a esa transferencia.';
COMMENT ON COLUMN movimiento.monto             IS 'Valor del movimiento, siempre mayor que cero. El tipo indica si suma o resta.';
COMMENT ON COLUMN movimiento.fecha             IS 'Fecha en que ocurrió el movimiento.';
COMMENT ON COLUMN movimiento.descripcion       IS 'Texto libre opcional. Obligatorio en los ajustes: es el motivo.';
COMMENT ON COLUMN movimiento.estado            IS 'VIGENTE o ANULADO. Solo los VIGENTES cuentan en saldos y resúmenes.';
COMMENT ON COLUMN movimiento.creado_en         IS 'Fecha y hora en que se registró.';
COMMENT ON COLUMN movimiento.actualizado_en    IS 'Fecha y hora de la última corrección o anulación. La actualiza el repositorio en cada UPDATE.';


-- =====================================================================
-- 5. bolsillo
--    Reserva virtual de dinero. No tiene relación con cuentas ni con
--    movimientos (D-10). Es "con meta" si monto_objetivo tiene valor (D-08).
--    El valor actual NO está aquí: es el último registro de bolsillo_valor.
-- =====================================================================
CREATE TABLE bolsillo (
  id_bolsillo     bigint        GENERATED ALWAYS AS IDENTITY,
  id_usuario      bigint        NOT NULL,
  nombre          text          NOT NULL,
  descripcion     text,
  monto_objetivo  numeric(14,2),
  fecha_objetivo  date,
  activo          boolean       NOT NULL DEFAULT true,
  creado_en       timestamptz   NOT NULL DEFAULT now(),

  CONSTRAINT pk_bolsillo PRIMARY KEY (id_bolsillo),

  CONSTRAINT fk_bolsillo_usuario FOREIGN KEY (id_usuario)
    REFERENCES usuario (id_usuario),

  -- Superclave para la FK de propiedad de bolsillo_valor.
  CONSTRAINT uq_bolsillo_propiedad UNIQUE (id_usuario, id_bolsillo),

  CONSTRAINT ck_bolsillo_nombre CHECK (nombre = btrim(nombre) AND nombre <> ''),

  -- RN-41: si hay meta, es mayor que cero. Con NULL (bolsillo genérico) el
  -- resultado es NULL y pasa: es lo correcto, un genérico no tiene objetivo.
  CONSTRAINT ck_bolsillo_monto_objetivo CHECK (monto_objetivo > 0),

  -- RN-41: la fecha objetivo solo existe si hay monto objetivo.
  -- Escrito con IS NULL / IS NOT NULL: nunca da NULL.
  CONSTRAINT ck_bolsillo_fecha_objetivo CHECK (fecha_objetivo IS NULL OR monto_objetivo IS NOT NULL)
);

-- No se repite el nombre entre los bolsillos ACTIVOS del mismo usuario.
CREATE UNIQUE INDEX uq_bolsillo_nombre_activo
  ON bolsillo (id_usuario, lower(nombre))
  WHERE activo;

COMMENT ON TABLE  bolsillo                IS 'Reserva virtual de dinero, con o sin meta. Independiente de las cuentas.';
COMMENT ON COLUMN bolsillo.id_bolsillo    IS 'Identificador interno del bolsillo.';
COMMENT ON COLUMN bolsillo.id_usuario     IS 'Dueño del bolsillo.';
COMMENT ON COLUMN bolsillo.nombre         IS 'Nombre del bolsillo. Único entre los bolsillos activos del usuario, sin distinguir mayúsculas.';
COMMENT ON COLUMN bolsillo.descripcion    IS 'Descripción opcional.';
COMMENT ON COLUMN bolsillo.monto_objetivo IS 'Cuánto se quiere reunir. Con valor (mayor que cero) el bolsillo es una meta; NULL = bolsillo genérico.';
COMMENT ON COLUMN bolsillo.fecha_objetivo IS 'Fecha en que se espera cumplir la meta. Opcional y solo si hay monto objetivo.';
COMMENT ON COLUMN bolsillo.activo         IS 'false = archivado: deja de sumar en el total reservado y conserva su historial (RN-49).';
COMMENT ON COLUMN bolsillo.creado_en      IS 'Fecha y hora de creación.';


-- =====================================================================
-- 6. bolsillo_valor
--    Historial de valores de cada bolsillo (D-09). Solo se insertan filas.
--    Valor actual = la fila más reciente: mayor registrado_en y, si hay
--    empate, mayor id_bolsillo_valor.
-- =====================================================================
CREATE TABLE bolsillo_valor (
  id_bolsillo_valor  bigint        GENERATED ALWAYS AS IDENTITY,
  id_usuario         bigint        NOT NULL,
  id_bolsillo        bigint        NOT NULL,
  valor              numeric(14,2) NOT NULL,
  registrado_en      timestamptz   NOT NULL DEFAULT now(),

  CONSTRAINT pk_bolsillo_valor PRIMARY KEY (id_bolsillo_valor),

  -- El bolsillo es del mismo usuario.
  --     valor.id_usuario  -> bolsillo.id_usuario
  --     valor.id_bolsillo -> bolsillo.id_bolsillo
  -- Las dos columnas son NOT NULL: esta FK se evalúa siempre. Como el
  -- bolsillo ya apunta a un usuario existente, no hace falta otra FK
  -- directa de aquí a usuario.
  CONSTRAINT fk_bolsillo_valor_bolsillo FOREIGN KEY (id_usuario, id_bolsillo)
    REFERENCES bolsillo (id_usuario, id_bolsillo),

  -- RN-43: no negativo; cero sí se permite.
  CONSTRAINT ck_bolsillo_valor_no_negativo CHECK (valor >= 0)
);

-- Para obtener rápido el registro más reciente de cada bolsillo.
-- El orden del índice es el mismo del "más reciente" definido arriba.
-- Nota: now() es la hora de INICIO de la transacción. Dos registros
-- insertados en la misma transacción quedan con la misma hora; por eso el
-- desempate por id_bolsillo_valor es necesario y no un adorno.
CREATE INDEX ix_bolsillo_valor_reciente
  ON bolsillo_valor (id_bolsillo, registrado_en DESC, id_bolsillo_valor DESC);

COMMENT ON TABLE  bolsillo_valor                   IS 'Historial de valores de cada bolsillo. El valor actual es el registro más reciente. Solo se insertan filas.';
COMMENT ON COLUMN bolsillo_valor.id_bolsillo_valor IS 'Identificador interno del registro. Desempata cuando dos registros tienen la misma fecha y hora.';
COMMENT ON COLUMN bolsillo_valor.id_usuario        IS 'Dueño; debe ser el mismo dueño del bolsillo (FK compuesta).';
COMMENT ON COLUMN bolsillo_valor.id_bolsillo       IS 'Bolsillo al que pertenece el registro.';
COMMENT ON COLUMN bolsillo_valor.valor             IS 'Valor reservado que escribió el usuario. Cero o positivo.';
COMMENT ON COLUMN bolsillo_valor.registrado_en     IS 'Fecha y hora en que se registró el valor.';

COMMIT;
