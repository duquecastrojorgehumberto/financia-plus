-- =====================================================================
-- FINANCIA+  ·  Datos de prueba (Tarea 15)
--
-- Usuarios FICTICIOS con los escenarios de los criterios de aceptación
-- CA-01 a CA-15 (docs/REQUISITOS.md, sección 4), para mostrar la
-- aplicación en una base de DESARROLLO. Ningún dato es de una persona real.
--
-- Cómo cargarlo (desde la carpeta del proyecto):
--     .venv\Scripts\python scripts\cargar_datos_prueba.py
-- tests/test_datos_prueba.py carga este mismo archivo (y lo deshace) y
-- comprueba cada resultado esperado de la tabla de abajo.
--
-- Usuarios (contraseña de los tres: demo-financia-2026, solo para esta demo local)
--   ana@demo.example    casi todos los escenarios
--   beto@demo.example   "el otro usuario" de CA-06
--   carla@demo.example  CA-09 y CA-10 (necesitan totales exactos)
--
-- Qué debe verse (noviembre de 2026)
--   Ana
--     Efectivo     130.000   CA-01: 100.000 + ingreso 50.000 − egreso 20.000.
--                            CA-13: un taxi de 15.000 ANULADO, visible en el historial, no cuenta.
--                            CA-15: tiene saldo, así que archivarla es rechazado.
--     Nequi        229.200   CA-02: transferencia de 200.000 a Nubank con cargo de 800 (4×1.000).
--                            CA-04: otra transferencia de 50.000 con cargo de 200, ANULADA con su cargo.
--                            CA-12: Mercado 30.000.  CA-14: Mascotas 40.000.
--     Nubank       200.000   CA-02.
--     Bancolombia  473.500   CA-11: saldo inicial 480.000; AJUSTE_DISMINUCION de 6.500.
--     Daviplata          0   CA-15: archivada con saldo 0.
--     Mascotas (categoría)   CA-14: desactivada; su movimiento se conserva y sigue sumando.
--     Bolsillo "Computador"  CA-07: meta 1.000.000; historial 0 → 350.000; progreso 35 %.
--     Bolsillo "Regalos"     RN-49: archivado con 50.000; no suma en el total reservado.
--     Bolsillos "Bicicleta" (meta 400.000, valor 120.000: 30 %) y "Curso de inglés"
--       (meta 150.000, valor 150.000: 100 %, cumplida), para los gráficos de metas.
--     Indicadores: saldo total 1.032.700; reservado 620.000 (350.000 + 120.000 + 150.000);
--       disponible 412.700.
--     Resumen de noviembre: ingresos 50.000; egresos 90.800 (20.000 + 30.000 + 40.000 + 800);
--       ajustes aparte: disminuciones 6.500.
--       CA-12: Alimentación 50.000 = 20.000 directos + Mercado 30.000.
--     Historial de junio a octubre (sección 7, para los gráficos): ingresos 13.000.000 y
--       egresos 13.000.000 en Bancolombia; se compensan, así que ningún saldo cambia.
--       Con 9 categorías de egreso en el periodo (junio a noviembre: 10 con Mascotas).
--   Beto (CA-06)  Nequi 70.000. Ana no puede usar su cuenta ni sus categorías.
--   Carla
--     Nequi 200.000 y Nubank 100.000 tras una transferencia de 100.000 (CA-09).
--     Bolsillos "Viaje" 200.000 (sigue igual tras la transferencia, CA-09) y "Emergencias" 150.000.
--     CA-10: saldo total 300.000; reservado 350.000; disponible −50.000, con aviso.
--
-- Los criterios que son RECHAZOS no dejan datos; se prueban con la API sobre estos datos:
--   CA-03 (transferencia con un cargo de categoría de ingreso: no queda nada),
--   CA-05 (egreso con la categoría "Salario"), CA-06 (Ana usando la cuenta de Beto),
--   CA-08 (valor −1 en un bolsillo), CA-15 (archivar Efectivo, que tiene saldo).
--
-- Notas
--   * Solo hay INSERT: se puede cargar con el rol de la aplicación (financia_app).
--   * Representa el ESTADO FINAL de cada escenario. Por ejemplo, Daviplata y la
--     categoría Mascotas se insertan ya archivada / desactivada, y el movimiento
--     de Mascotas existe porque se registró antes de desactivarla.
--   * Las categorías por defecto son la misma lista de RN-26
--     (app/servicios/categorias_por_defecto.py); una prueba comprueba que coinciden.
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- 1. Usuarios
-- ---------------------------------------------------------------------
INSERT INTO usuario (nombre, correo, clave_hash) VALUES
  ('Ana Demo',   'ana@demo.example',   'scrypt:32768:8:1$RbT80oMy0NQwdVVL$e486911739f5d532b1102e2afdcb74e66acb83ed31f38704b460203d458423995a7ca0b3ad7e03ba01d7272d9a295af08fb71bde8188ee8540be30a8eb11f943'),
  ('Beto Demo',  'beto@demo.example',  'scrypt:32768:8:1$RbT80oMy0NQwdVVL$e486911739f5d532b1102e2afdcb74e66acb83ed31f38704b460203d458423995a7ca0b3ad7e03ba01d7272d9a295af08fb71bde8188ee8540be30a8eb11f943'),
  ('Carla Demo', 'carla@demo.example', 'scrypt:32768:8:1$RbT80oMy0NQwdVVL$e486911739f5d532b1102e2afdcb74e66acb83ed31f38704b460203d458423995a7ca0b3ad7e03ba01d7272d9a295af08fb71bde8188ee8540be30a8eb11f943');

-- ---------------------------------------------------------------------
-- 2. Categorías por defecto (RN-26), para los tres usuarios.
--    Primero las raíces; después las subcategorías, buscando a su padre por nombre.
-- ---------------------------------------------------------------------
INSERT INTO categoria (id_usuario, nombre, tipo)
SELECT u.id_usuario, v.nombre, v.tipo
  FROM usuario u
 CROSS JOIN (VALUES
   ('Salario', 'INGRESO'), ('Trabajo independiente', 'INGRESO'), ('Rendimientos', 'INGRESO'),
   ('Otros ingresos', 'INGRESO'),
   ('Alimentación', 'EGRESO'), ('Vivienda', 'EGRESO'), ('Transporte', 'EGRESO'), ('Salud', 'EGRESO'),
   ('Educación', 'EGRESO'), ('Entretenimiento', 'EGRESO'), ('Ropa y cuidado personal', 'EGRESO'),
   ('Impuestos y comisiones', 'EGRESO'), ('Otros gastos', 'EGRESO')
 ) AS v (nombre, tipo)
 WHERE u.correo LIKE '%@demo.example';

INSERT INTO categoria (id_usuario, id_padre, nombre, tipo)
SELECT padre.id_usuario, padre.id_categoria, v.nombre, padre.tipo
  FROM (VALUES
   ('Salario', 'Sueldo'), ('Salario', 'Primas y bonificaciones'),
   ('Otros ingresos', 'Regalos'), ('Otros ingresos', 'Reembolsos'),
   ('Alimentación', 'Mercado'), ('Alimentación', 'Restaurantes'), ('Alimentación', 'Domicilios'),
   ('Vivienda', 'Arriendo'), ('Vivienda', 'Servicios públicos'), ('Vivienda', 'Hogar y aseo'),
   ('Transporte', 'Transporte público'), ('Transporte', 'Combustible'), ('Transporte', 'Taxis y aplicaciones'),
   ('Salud', 'Medicamentos'), ('Salud', 'Consultas'),
   ('Educación', 'Matrículas'), ('Educación', 'Libros y cursos'),
   ('Entretenimiento', 'Suscripciones'), ('Entretenimiento', 'Salidas'),
   ('Impuestos y comisiones', '4×1.000'), ('Impuestos y comisiones', 'Comisiones bancarias')
 ) AS v (nombre_padre, nombre)
  JOIN categoria padre
    ON padre.nombre = v.nombre_padre
   AND padre.id_padre IS NULL
  JOIN usuario u
    ON u.id_usuario = padre.id_usuario
 WHERE u.correo LIKE '%@demo.example';

-- CA-14: una categoría propia de Ana, ya desactivada (su movimiento está en la sección 4).
INSERT INTO categoria (id_usuario, nombre, tipo, activa)
SELECT id_usuario, 'Mascotas', 'EGRESO', false FROM usuario WHERE correo = 'ana@demo.example';

-- ---------------------------------------------------------------------
-- 3. Cuentas
-- ---------------------------------------------------------------------
INSERT INTO cuenta (id_usuario, nombre, tipo, saldo_inicial, activa)
SELECT u.id_usuario, v.nombre, v.tipo, v.saldo_inicial, v.activa
  FROM (VALUES
   ('ana@demo.example',   'Efectivo',    'EFECTIVO',          100000.00, true),
   ('ana@demo.example',   'Nequi',       'BILLETERA_DIGITAL', 500000.00, true),
   ('ana@demo.example',   'Nubank',      'AHORROS',                0.00, true),
   ('ana@demo.example',   'Bancolombia', 'AHORROS',           480000.00, true),
   ('ana@demo.example',   'Daviplata',   'BILLETERA_DIGITAL',      0.00, false),   -- CA-15: archivada con saldo 0
   ('beto@demo.example',  'Nequi',       'BILLETERA_DIGITAL',  80000.00, true),
   ('carla@demo.example', 'Nequi',       'BILLETERA_DIGITAL', 300000.00, true),
   ('carla@demo.example', 'Nubank',      'AHORROS',                0.00, true)
 ) AS v (correo, nombre, tipo, saldo_inicial, activa)
  JOIN usuario u ON u.correo = v.correo;

-- ---------------------------------------------------------------------
-- 4. Ingresos, egresos y ajustes.
--    Cada fila busca la cuenta y la categoría de SU usuario por nombre.
--    (En la categoría basta el nombre: los nombres usados aquí no se repiten
--    dentro de un mismo usuario.)
-- ---------------------------------------------------------------------
INSERT INTO movimiento (id_usuario, tipo, id_cuenta, id_categoria, monto, fecha, descripcion, estado)
SELECT u.id_usuario, v.tipo, c.id_cuenta, cat.id_categoria, v.monto, v.fecha, v.descripcion, v.estado
  FROM (VALUES
   -- CA-01
   ('ana@demo.example',  'INGRESO', 'Efectivo', 'Salario',      50000.00, DATE '2026-11-05', 'Pago quincena', 'VIGENTE'),
   ('ana@demo.example',  'EGRESO',  'Efectivo', 'Alimentación', 20000.00, DATE '2026-11-06', 'Almuerzos',     'VIGENTE'),
   -- CA-13
   ('ana@demo.example',  'EGRESO',  'Efectivo', 'Transporte',   15000.00, DATE '2026-11-07', 'Taxi',          'ANULADO'),
   -- CA-12 (Mercado es subcategoría de Alimentación)
   ('ana@demo.example',  'EGRESO',  'Nequi',    'Mercado',      30000.00, DATE '2026-11-14', 'Mercado del mes', 'VIGENTE'),
   -- CA-14 (registrado antes de desactivar Mascotas)
   ('ana@demo.example',  'EGRESO',  'Nequi',    'Mascotas',     40000.00, DATE '2026-11-03', 'Veterinario',   'VIGENTE'),
   -- CA-11 (ajuste: sin categoría y con motivo)
   ('ana@demo.example',  'AJUSTE_DISMINUCION', 'Bancolombia', NULL, 6500.00, DATE '2026-11-20', 'Compras no registradas', 'VIGENTE'),
   -- CA-06
   ('beto@demo.example', 'EGRESO',  'Nequi',    'Alimentación', 10000.00, DATE '2026-11-09', 'Almuerzo',      'VIGENTE')
 ) AS v (correo, tipo, nombre_cuenta, nombre_categoria, monto, fecha, descripcion, estado)
  JOIN usuario u
    ON u.correo = v.correo
  JOIN cuenta c
    ON c.id_usuario = u.id_usuario AND c.nombre = v.nombre_cuenta
  LEFT JOIN categoria cat
    ON cat.id_usuario = u.id_usuario AND cat.nombre = v.nombre_categoria;

-- ---------------------------------------------------------------------
-- 5. Transferencias con sus cargos (RN-33 a RN-35).
--    Cada transferencia se inserta y, con su id (RETURNING), se inserta su
--    cargo: un EGRESO de la misma cuenta de origen y con la misma fecha.
-- ---------------------------------------------------------------------

-- CA-02: Nequi → Nubank 200.000, con cargo de 800 (4×1.000).
WITH transferencia AS (
  INSERT INTO movimiento (id_usuario, tipo, id_cuenta, id_cuenta_destino, monto, fecha, descripcion)
  SELECT u.id_usuario, 'TRANSFERENCIA', o.id_cuenta, d.id_cuenta, 200000.00, DATE '2026-11-10', 'Ahorro del mes'
    FROM usuario u
    JOIN cuenta o ON o.id_usuario = u.id_usuario AND o.nombre = 'Nequi'
    JOIN cuenta d ON d.id_usuario = u.id_usuario AND d.nombre = 'Nubank'
   WHERE u.correo = 'ana@demo.example'
  RETURNING id_movimiento, id_usuario, id_cuenta, fecha
)
INSERT INTO movimiento (id_usuario, tipo, id_cuenta, id_categoria, id_transferencia, monto, fecha)
SELECT t.id_usuario, 'EGRESO', t.id_cuenta, cat.id_categoria, t.id_movimiento, 800.00, t.fecha
  FROM transferencia t
  JOIN categoria cat ON cat.id_usuario = t.id_usuario AND cat.nombre = '4×1.000';

-- CA-04: Nequi → Nubank 50.000 con cargo de 200, ANULADA junto con su cargo (RN-38).
WITH transferencia AS (
  INSERT INTO movimiento (id_usuario, tipo, id_cuenta, id_cuenta_destino, monto, fecha, descripcion, estado)
  SELECT u.id_usuario, 'TRANSFERENCIA', o.id_cuenta, d.id_cuenta, 50000.00, DATE '2026-11-12', 'Transferencia equivocada', 'ANULADO'
    FROM usuario u
    JOIN cuenta o ON o.id_usuario = u.id_usuario AND o.nombre = 'Nequi'
    JOIN cuenta d ON d.id_usuario = u.id_usuario AND d.nombre = 'Nubank'
   WHERE u.correo = 'ana@demo.example'
  RETURNING id_movimiento, id_usuario, id_cuenta, fecha
)
INSERT INTO movimiento (id_usuario, tipo, id_cuenta, id_categoria, id_transferencia, monto, fecha, estado)
SELECT t.id_usuario, 'EGRESO', t.id_cuenta, cat.id_categoria, t.id_movimiento, 200.00, t.fecha, 'ANULADO'
  FROM transferencia t
  JOIN categoria cat ON cat.id_usuario = t.id_usuario AND cat.nombre = '4×1.000';

-- CA-09: Carla, Nequi → Nubank 100.000, sin cargos.
INSERT INTO movimiento (id_usuario, tipo, id_cuenta, id_cuenta_destino, monto, fecha)
SELECT u.id_usuario, 'TRANSFERENCIA', o.id_cuenta, d.id_cuenta, 100000.00, DATE '2026-11-08'
  FROM usuario u
  JOIN cuenta o ON o.id_usuario = u.id_usuario AND o.nombre = 'Nequi'
  JOIN cuenta d ON d.id_usuario = u.id_usuario AND d.nombre = 'Nubank'
 WHERE u.correo = 'carla@demo.example';

-- ---------------------------------------------------------------------
-- 6. Bolsillos y su historial de valores (RN-44, RN-45).
--    registrado_en se indica a mano para que el historial muestre fechas reales;
--    el valor actual es el más reciente.
-- ---------------------------------------------------------------------
INSERT INTO bolsillo (id_usuario, nombre, descripcion, monto_objetivo, fecha_objetivo, activo)
SELECT u.id_usuario, v.nombre, v.descripcion, v.monto_objetivo, v.fecha_objetivo, v.activo
  FROM (VALUES
   ('ana@demo.example',   'Computador',  'Portátil para la universidad', 1000000.00, DATE '2027-06-30', true),   -- CA-07
   ('ana@demo.example',   'Regalos',     'Regalos de diciembre',         NULL,       NULL,              false),  -- RN-49
   ('ana@demo.example',   'Bicicleta',   'Para ir a la universidad',      400000.00, DATE '2027-03-31', true),
   ('ana@demo.example',   'Curso de inglés', NULL,                        150000.00, NULL,              true),
   ('carla@demo.example', 'Viaje',       NULL,                           NULL,       NULL,              true),   -- CA-09, CA-10
   ('carla@demo.example', 'Emergencias', NULL,                           NULL,       NULL,              true)    -- CA-10
 ) AS v (correo, nombre, descripcion, monto_objetivo, fecha_objetivo, activo)
  JOIN usuario u ON u.correo = v.correo;

INSERT INTO bolsillo_valor (id_usuario, id_bolsillo, valor, registrado_en)
SELECT b.id_usuario, b.id_bolsillo, v.valor, v.registrado_en
  FROM (VALUES
   ('ana@demo.example',   'Computador',        0.00, TIMESTAMPTZ '2026-11-01 09:00:00-05'),
   ('ana@demo.example',   'Computador',   350000.00, TIMESTAMPTZ '2026-11-15 18:30:00-05'),   -- CA-07
   ('ana@demo.example',   'Regalos',       50000.00, TIMESTAMPTZ '2026-11-02 10:00:00-05'),
   ('ana@demo.example',   'Bicicleta',     50000.00, TIMESTAMPTZ '2026-09-10 19:00:00-05'),
   ('ana@demo.example',   'Bicicleta',    120000.00, TIMESTAMPTZ '2026-10-28 20:15:00-05'),
   ('ana@demo.example',   'Curso de inglés', 150000.00, TIMESTAMPTZ '2026-08-05 12:00:00-05'),
   ('carla@demo.example', 'Viaje',        200000.00, TIMESTAMPTZ '2026-11-01 08:00:00-05'),   -- antes de la transferencia (CA-09)
   ('carla@demo.example', 'Emergencias',  150000.00, TIMESTAMPTZ '2026-11-01 08:05:00-05')
 ) AS v (correo, nombre_bolsillo, valor, registrado_en)
  JOIN usuario u
    ON u.correo = v.correo
  JOIN bolsillo b
    ON b.id_usuario = u.id_usuario AND b.nombre = v.nombre_bolsillo;

-- ---------------------------------------------------------------------
-- 7. Historial de Ana de junio a octubre de 2026 (para los gráficos del resumen).
--    Todo en Bancolombia: ingresos 13.000.000 y egresos 13.000.000 en el periodo.
--    Se compensan, así que NINGÚN saldo cambia y todo lo de noviembre sigue igual.
--    Por mes (ingresos / egresos):
--      junio 3.000.000 / 2.350.000   julio 2.400.000 / 2.520.000   agosto 2.400.000 / 2.480.000
--      septiembre 2.800.000 / 2.810.000   octubre 2.400.000 / 2.840.000
-- ---------------------------------------------------------------------
INSERT INTO movimiento (id_usuario, tipo, id_cuenta, id_categoria, monto, fecha, descripcion)
SELECT u.id_usuario, v.tipo, c.id_cuenta, cat.id_categoria, v.monto, v.fecha, v.descripcion
  FROM (VALUES
   ('INGRESO', 'Sueldo', 2400000.00, DATE '2026-06-01', 'Sueldo de junio'),
   ('INGRESO', 'Primas y bonificaciones', 600000.00, DATE '2026-06-30', 'Prima de mitad de año'),
   ('INGRESO', 'Sueldo', 2400000.00, DATE '2026-07-01', 'Sueldo de julio'),
   ('INGRESO', 'Sueldo', 2400000.00, DATE '2026-08-01', 'Sueldo de agosto'),
   ('INGRESO', 'Sueldo', 2400000.00, DATE '2026-09-01', 'Sueldo de septiembre'),
   ('INGRESO', 'Trabajo independiente', 400000.00, DATE '2026-09-20', 'Diseño de un logo'),
   ('INGRESO', 'Sueldo', 2400000.00, DATE '2026-10-01', 'Sueldo de octubre'),
   ('EGRESO',  'Arriendo', 1200000.00, DATE '2026-06-02', 'Arriendo'),
   ('EGRESO',  'Servicios públicos', 185000.00, DATE '2026-06-04', 'Luz, agua e internet'),
   ('EGRESO',  'Mercado', 420000.00, DATE '2026-06-06', 'Mercado del mes'),
   ('EGRESO',  'Restaurantes', 95000.00, DATE '2026-06-08', 'Almuerzos'),
   ('EGRESO',  'Transporte público', 88000.00, DATE '2026-06-10', 'Recargas de la tarjeta'),
   ('EGRESO',  'Suscripciones', 45000.00, DATE '2026-06-12', 'Streaming y música'),
   ('EGRESO',  'Ropa y cuidado personal', 210000.00, DATE '2026-06-14', 'Zapatos'),
   ('EGRESO',  'Medicamentos', 62000.00, DATE '2026-06-16', 'Farmacia'),
   ('EGRESO',  '4×1.000', 9600.00, DATE '2026-06-18', '4×1.000 del mes'),
   ('EGRESO',  'Otros gastos', 35400.00, DATE '2026-06-20', 'Varios'),
   ('EGRESO',  'Arriendo', 1200000.00, DATE '2026-07-02', 'Arriendo'),
   ('EGRESO',  'Servicios públicos', 192000.00, DATE '2026-07-04', 'Luz, agua e internet'),
   ('EGRESO',  'Mercado', 435000.00, DATE '2026-07-06', 'Mercado del mes'),
   ('EGRESO',  'Restaurantes', 140000.00, DATE '2026-07-08', 'Almuerzos y una cena'),
   ('EGRESO',  'Transporte público', 92000.00, DATE '2026-07-10', 'Recargas de la tarjeta'),
   ('EGRESO',  'Combustible', 120000.00, DATE '2026-07-12', 'Gasolina del viaje'),
   ('EGRESO',  'Suscripciones', 45000.00, DATE '2026-07-14', 'Streaming y música'),
   ('EGRESO',  'Salidas', 160000.00, DATE '2026-07-16', 'Vacaciones'),
   ('EGRESO',  'Libros y cursos', 85000.00, DATE '2026-07-18', 'Curso en línea'),
   ('EGRESO',  '4×1.000', 10100.00, DATE '2026-07-20', '4×1.000 del mes'),
   ('EGRESO',  'Otros gastos', 40900.00, DATE '2026-07-22', 'Varios'),
   ('EGRESO',  'Arriendo', 1200000.00, DATE '2026-08-02', 'Arriendo'),
   ('EGRESO',  'Servicios públicos', 201000.00, DATE '2026-08-04', 'Luz, agua e internet'),
   ('EGRESO',  'Mercado', 410000.00, DATE '2026-08-06', 'Mercado del mes'),
   ('EGRESO',  'Domicilios', 76000.00, DATE '2026-08-08', 'Domicilios'),
   ('EGRESO',  'Transporte público', 95000.00, DATE '2026-08-10', 'Recargas de la tarjeta'),
   ('EGRESO',  'Consultas', 150000.00, DATE '2026-08-12', 'Odontólogo'),
   ('EGRESO',  'Suscripciones', 45000.00, DATE '2026-08-14', 'Streaming y música'),
   ('EGRESO',  'Ropa y cuidado personal', 98000.00, DATE '2026-08-16', 'Peluquería'),
   ('EGRESO',  '4×1.000', 9900.00, DATE '2026-08-18', '4×1.000 del mes'),
   ('EGRESO',  'Hogar y aseo', 120000.00, DATE '2026-08-20', 'Aseo de la casa'),
   ('EGRESO',  'Otros gastos', 75100.00, DATE '2026-08-22', 'Varios'),
   ('EGRESO',  'Arriendo', 1200000.00, DATE '2026-09-02', 'Arriendo'),
   ('EGRESO',  'Servicios públicos', 188000.00, DATE '2026-09-04', 'Luz, agua e internet'),
   ('EGRESO',  'Mercado', 445000.00, DATE '2026-09-06', 'Mercado del mes'),
   ('EGRESO',  'Restaurantes', 130000.00, DATE '2026-09-08', 'Almuerzos'),
   ('EGRESO',  'Transporte público', 90000.00, DATE '2026-09-10', 'Recargas de la tarjeta'),
   ('EGRESO',  'Matrículas', 520000.00, DATE '2026-09-12', 'Matrícula del semestre'),
   ('EGRESO',  'Suscripciones', 45000.00, DATE '2026-09-14', 'Streaming y música'),
   ('EGRESO',  'Salidas', 95000.00, DATE '2026-09-16', 'Cine y bolos'),
   ('EGRESO',  '4×1.000', 11200.00, DATE '2026-09-18', '4×1.000 del mes'),
   ('EGRESO',  'Otros gastos', 85800.00, DATE '2026-09-20', 'Varios'),
   ('EGRESO',  'Arriendo', 1200000.00, DATE '2026-10-02', 'Arriendo'),
   ('EGRESO',  'Servicios públicos', 196000.00, DATE '2026-10-04', 'Luz, agua e internet'),
   ('EGRESO',  'Mercado', 430000.00, DATE '2026-10-06', 'Mercado del mes'),
   ('EGRESO',  'Restaurantes', 110000.00, DATE '2026-10-08', 'Almuerzos'),
   ('EGRESO',  'Domicilios', 64000.00, DATE '2026-10-10', 'Domicilios'),
   ('EGRESO',  'Combustible', 130000.00, DATE '2026-10-12', 'Gasolina'),
   ('EGRESO',  'Transporte público', 91000.00, DATE '2026-10-14', 'Recargas de la tarjeta'),
   ('EGRESO',  'Medicamentos', 48000.00, DATE '2026-10-16', 'Farmacia'),
   ('EGRESO',  'Suscripciones', 45000.00, DATE '2026-10-18', 'Streaming y música'),
   ('EGRESO',  'Salidas', 210000.00, DATE '2026-10-20', 'Concierto'),
   ('EGRESO',  'Ropa y cuidado personal', 260000.00, DATE '2026-10-22', 'Chaqueta'),
   ('EGRESO',  '4×1.000', 10800.00, DATE '2026-10-24', '4×1.000 del mes'),
   ('EGRESO',  'Otros gastos', 45200.00, DATE '2026-10-26', 'Varios')
 ) AS v (tipo, nombre_categoria, monto, fecha, descripcion)
  JOIN usuario u
    ON u.correo = 'ana@demo.example'
  JOIN cuenta c
    ON c.id_usuario = u.id_usuario AND c.nombre = 'Bancolombia'
  JOIN categoria cat
    ON cat.id_usuario = u.id_usuario AND cat.nombre = v.nombre_categoria;

COMMIT;
