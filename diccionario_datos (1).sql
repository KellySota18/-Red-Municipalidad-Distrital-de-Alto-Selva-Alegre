-- diccionario_datos.sql - Genera el diccionario de datos en Markdown a partir del catálogo de PostgreSQL.
-- Uso:  psql -q -U postgres -d infra_red_db -f diccionario_datos.sql -o ..\docs\06_DICCIONARIO_DE_DATOS.md
\pset format unaligned
\pset tuples_only on
CREATE TEMP VIEW _bloque AS
WITH desc_tabla(t, d) AS (VALUES
  ('usuarios',            'Personas autorizadas a usar el sistema. La contraseña se guarda solo como hash bcrypt.'),
  ('ubicaciones',         'Lugares físicos: sede, piso y ambiente (por ejemplo, el centro de datos del piso 4).'),
  ('vlans',               'Redes virtuales. La red actual es plana (sin VLAN); las VLAN 10, 20, 30, 40, 50 y 99 son la propuesta TO-BE.'),
  ('subredes',            'Segmentos IP con su puerta de enlace. No pueden solaparse dentro del mismo diseño (actual o propuesto).'),
  ('dispositivos',        'Equipos de red y servidores: firewall, routers, switches, UPS, ONU, radioenlace y servidores.'),
  ('interfaces',          'Puertos de un dispositivo con su IP y MAC. La IP debe pertenecer a su subred y no puede repetirse.'),
  ('enlaces',             'Conexión entre dos interfaces (cable UTP, fibra, radioenlace) con su velocidad.'),
  ('mantenimientos',      'Órdenes de mantenimiento de un dispositivo: responsable, tipo, fechas y estado.'),
  ('sesiones',            'Sesiones activas. Solo se guarda el hash del token; nunca el token. Uso interno.'),
  ('rate_limit',          'Contadores para limitar intentos por ventana de tiempo. Uso interno.'),
  ('auditoria',           'Bitácora inmutable: quién cambió qué y cuándo. No se puede modificar ni borrar.'),
  ('politicas_seguridad', 'Políticas de seguridad de red P1 a P8 definidas en la práctica de ACL.'),
  ('acls',                'Listas de control de acceso por router y versión (v1 = informe, v2 = denegación por defecto).'),
  ('acl_reglas',          'Reglas ordenadas de cada ACL (permit o deny y su condición).'),
  ('acl_aplicaciones',    'En qué interfaz y sentido (entrada o salida) se aplica cada ACL.'),
  ('pruebas_conectividad','Pruebas de ping y TCP: resultado esperado contra el obtenido, desde Packet Tracer o el simulador.')
),
tablas AS (
  SELECT c.oid, c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname = 'infra' AND c.relkind IN ('r','p') ORDER BY c.relname
)
SELECT t.relname,
    E'### `' || t.relname || E'`\n\n' || COALESCE((SELECT d FROM desc_tabla WHERE desc_tabla.t = t.relname), '') ||
    E'\n\n| Columna | Tipo | Obligatorio | Valor por defecto | Clave o referencia |\n|---|---|---|---|---|\n' ||
    (SELECT string_agg(
        '| `' || a.attname || '` | ' || format_type(a.atttypid, a.atttypmod) || ' | ' ||
        CASE WHEN a.attnotnull THEN 'Sí' ELSE 'No' END || ' | ' ||
        COALESCE('`' || replace(pg_get_expr(d.adbin, d.adrelid), '|', '\|') || '`', '') || ' | ' ||
        COALESCE((SELECT string_agg(CASE con.contype WHEN 'p' THEN 'Clave primaria' WHEN 'u' THEN 'Único'
                       WHEN 'f' THEN 'Referencia a `' || (SELECT relname FROM pg_class WHERE oid = con.confrelid) || '`' END, ', ')
                    FROM pg_constraint con WHERE con.conrelid = t.oid AND con.contype IN ('p','u','f') AND a.attnum = ANY (con.conkey)), '') || ' |',
        E'\n' ORDER BY a.attnum)
       FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
      WHERE a.attrelid = t.oid AND a.attnum > 0 AND NOT a.attisdropped) ||
    COALESCE(E'\n\nReglas de validación (CHECK y exclusiones):\n\n' ||
      (SELECT string_agg('- `' || con.conname || '`: `' || replace(pg_get_constraintdef(con.oid), E'\n', ' ') || '`', E'\n' ORDER BY con.conname)
         FROM pg_constraint con WHERE con.conrelid = t.oid AND con.contype IN ('c','x')), '') AS md
  FROM tablas t;
SELECT E'# Diccionario de datos\n\nGenerado automáticamente desde la base de datos (`bd/diccionario_datos.sql`). Esquema `infra`, PostgreSQL 16. ' ||
       E'Si cambia el esquema, vuelva a generarlo para que este documento no quede desactualizado.\n\n## 1. Tablas\n';
SELECT md || E'\n' FROM _bloque ORDER BY relname;
SELECT E'## 2. Tipos enumerados (valores permitidos)\n\n| Tipo | Valores permitidos |\n|---|---|';
SELECT '| `' || t.typname || '` | ' || string_agg('`' || e.enumlabel || '`', ', ' ORDER BY e.enumsortorder) || ' |'
  FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid JOIN pg_namespace n ON n.oid = t.typnamespace
 WHERE n.nspname = 'infra' GROUP BY t.typname ORDER BY t.typname;
SELECT E'\n## 3. Vistas\n\n| Vista | Para qué sirve |\n|---|---|';
SELECT '| `' || c.relname || '` | ' || COALESCE(obj_description(c.oid, 'pg_class'), CASE c.relname
         WHEN 'v_uso_subredes' THEN 'Capacidad de hosts de cada subred frente a las IP registradas.'
         WHEN 'v_proximos_mantenimientos' THEN 'Próximo mantenimiento de cada dispositivo (último completado o instalación + periodicidad).'
         WHEN 'v_pruebas_resumen' THEN 'Pruebas correctas y fallidas por versión y fuente.' END) || ' |'
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'infra' AND c.relkind = 'v' ORDER BY c.relname;
SELECT E'\n## 4. Funciones\n\n| Función | Argumentos | Se ejecuta con permisos de | Quién puede llamarla |\n|---|---|---|---|';
SELECT '| `' || p.proname || '` | ' || COALESCE(NULLIF(pg_get_function_identity_arguments(p.oid), ''), '(ninguno)') || ' | ' ||
       CASE WHEN p.prosecdef THEN 'el dueño (SECURITY DEFINER)' ELSE 'quien la llama' END || ' | ' ||
       CASE WHEN has_function_privilege('rol_app', p.oid, 'EXECUTE') THEN 'la API (`rol_app`)' ELSE 'solo el administrador de la base de datos' END || ' |'
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname = 'infra' AND p.prokind = 'f' AND p.proname NOT LIKE 'fn\_%' ORDER BY p.proname;
