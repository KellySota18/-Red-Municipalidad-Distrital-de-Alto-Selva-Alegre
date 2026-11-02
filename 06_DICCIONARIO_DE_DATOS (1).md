# Diccionario de datos

Generado automáticamente desde la base de datos (`bd/diccionario_datos.sql`). Esquema `infra`, PostgreSQL 16. Si cambia el esquema, vuelva a generarlo para que este documento no quede desactualizado.

## 1. Tablas

### `acl_aplicaciones`

En qué interfaz y sentido (entrada o salida) se aplica cada ACL.

| Columna | Tipo | Obligatorio | Valor por defecto | Clave o referencia |
|---|---|---|---|---|
| `id_aplicacion` | uuid | Sí | `gen_random_uuid()` | Clave primaria |
| `id_acl` | uuid | Sí |  | Único en conjunto con otras columnas, Referencia a `acls` |
| `interfaz` | character varying(40) | Sí |  | Único en conjunto con otras columnas |
| `sentido` | infra.sentido_acl | Sí |  | Único en conjunto con otras columnas |

Reglas de validación (CHECK y exclusiones):

- `ck_acl_aplic_if`: `CHECK (((interfaz)::text ~ '^[A-Za-z0-9/._:-]+$'::text))`

### `acl_reglas`

Reglas ordenadas de cada ACL (permit o deny y su condición).

| Columna | Tipo | Obligatorio | Valor por defecto | Clave o referencia |
|---|---|---|---|---|
| `id_regla` | uuid | Sí | `gen_random_uuid()` | Clave primaria |
| `id_acl` | uuid | Sí |  | Único en conjunto con otras columnas, Referencia a `acls` |
| `secuencia` | integer | Sí |  | Único en conjunto con otras columnas |
| `accion` | infra.accion_acl | Sí |  |  |
| `condicion` | character varying(200) | Sí |  |  |

Reglas de validación (CHECK y exclusiones):

- `ck_acl_reglas_cond`: `CHECK (((condicion)::text ~ '^[A-Za-z0-9 ./_-]+$'::text))`
- `ck_acl_reglas_seq`: `CHECK ((secuencia > 0))`

### `acls`

Listas de control de acceso por router y versión (v1 = informe, v2 = denegación por defecto).

| Columna | Tipo | Obligatorio | Valor por defecto | Clave o referencia |
|---|---|---|---|---|
| `id_acl` | uuid | Sí | `gen_random_uuid()` | Clave primaria |
| `id_router` | uuid | Sí |  | Único en conjunto con otras columnas, Referencia a `dispositivos` |
| `nombre` | character varying(60) | Sí |  | Único en conjunto con otras columnas |
| `tipo` | infra.tipo_acl | Sí |  |  |
| `numerada` | boolean | Sí |  |  |
| `version` | character varying(20) | Sí |  | Único en conjunto con otras columnas |
| `id_politica` | uuid | No |  | Referencia a `politicas_seguridad` |

Reglas de validación (CHECK y exclusiones):

- `ck_acls_nombre`: `CHECK (((nombre)::text ~ '^[A-Za-z0-9_-]{1,60}$'::text))`
- `ck_acls_numerada`: `CHECK ((numerada = ((nombre)::text ~ '^[0-9]+$'::text)))`
- `ck_acls_version`: `CHECK (((version)::text = ANY ((ARRAY['v1_informe'::character varying, 'v2_default_deny'::character varying])::text[])))`

### `auditoria`

Bitácora inmutable: quién cambió qué y cuándo. No se puede modificar ni borrar.

| Columna | Tipo | Obligatorio | Valor por defecto | Clave o referencia |
|---|---|---|---|---|
| `id_auditoria` | bigint | Sí |  | Clave primaria |
| `fecha` | timestamp with time zone | Sí | `now()` |  |
| `id_usuario_app` | uuid | No |  |  |
| `usuario_bd` | text | Sí | `SESSION_USER` |  |
| `tabla` | text | Sí |  |  |
| `operacion` | text | Sí |  |  |
| `id_registro` | text | No |  |  |
| `datos_antes` | jsonb | No |  |  |
| `datos_despues` | jsonb | No |  |  |

### `dispositivos`

Equipos de red y servidores: firewall, routers, switches, UPS, ONU, radioenlace y servidores.

| Columna | Tipo | Obligatorio | Valor por defecto | Clave o referencia |
|---|---|---|---|---|
| `id_dispositivo` | uuid | Sí | `gen_random_uuid()` | Clave primaria |
| `nombre` | character varying(100) | Sí |  | Único |
| `tipo` | infra.tipo_dispositivo | Sí |  |  |
| `marca` | character varying(60) | No |  |  |
| `modelo` | character varying(100) | No |  |  |
| `numero_serie` | character varying(100) | No |  | Único |
| `id_ubicacion` | uuid | No |  | Referencia a `ubicaciones` |
| `estado` | infra.estado_dispositivo | Sí | `'operativo'::infra.estado_dispositivo` |  |
| `fecha_instalacion` | date | No |  |  |
| `mantenimiento_cada_meses` | smallint | No |  |  |
| `observaciones` | character varying(500) | No |  |  |

Reglas de validación (CHECK y exclusiones):

- `ck_dispositivos_mant`: `CHECK (((mantenimiento_cada_meses IS NULL) OR ((mantenimiento_cada_meses >= 1) AND (mantenimiento_cada_meses <= 120))))`
- `ck_dispositivos_texto`: `CHECK ((((nombre)::text !~ '[[:cntrl:]<>]'::text) AND (char_length(btrim((nombre)::text)) >= 2) AND ((COALESCE(observaciones, ''::character varying))::text !~ '[[:cntrl:]]'::text)))`

### `enlaces`

Conexión entre dos interfaces (cable UTP, fibra, radioenlace) con su velocidad.

| Columna | Tipo | Obligatorio | Valor por defecto | Clave o referencia |
|---|---|---|---|---|
| `id_enlace` | uuid | Sí | `gen_random_uuid()` | Clave primaria |
| `id_interfaz_a` | uuid | Sí |  | Único, Referencia a `interfaces` |
| `id_interfaz_b` | uuid | Sí |  | Único, Referencia a `interfaces` |
| `medio` | infra.tipo_medio | Sí |  |  |
| `velocidad_mbps` | integer | No |  |  |
| `descripcion` | character varying(200) | No |  |  |

Reglas de validación (CHECK y exclusiones):

- `ck_enlaces_distintos`: `CHECK ((id_interfaz_a <> id_interfaz_b))`
- `ck_enlaces_vel`: `CHECK (((velocidad_mbps IS NULL) OR (velocidad_mbps > 0)))`

### `interfaces`

Puertos de un dispositivo con su IP y MAC. La IP debe pertenecer a su subred y no puede repetirse.

| Columna | Tipo | Obligatorio | Valor por defecto | Clave o referencia |
|---|---|---|---|---|
| `id_interfaz` | uuid | Sí | `gen_random_uuid()` | Clave primaria |
| `id_dispositivo` | uuid | Sí |  | Único en conjunto con otras columnas, Referencia a `dispositivos` |
| `nombre` | character varying(40) | Sí |  | Único en conjunto con otras columnas |
| `mac` | macaddr | No |  | Único |
| `ip` | inet | No |  | Único |
| `id_subred` | uuid | No |  | Referencia a `subredes` |
| `asignacion` | infra.asignacion_ip | Sí | `'estatica'::infra.asignacion_ip` |  |

Reglas de validación (CHECK y exclusiones):

- `ck_interfaces_ip`: `CHECK (((ip IS NULL) OR (masklen(ip) = CASE family(ip)     WHEN 4 THEN 32     ELSE 128 END)))`
- `ck_interfaces_nombre`: `CHECK (((nombre)::text ~ '^[A-Za-z0-9/._:-]{1,40}$'::text))`

### `mantenimientos`

Órdenes de mantenimiento de un dispositivo: responsable, tipo, fechas y estado.

| Columna | Tipo | Obligatorio | Valor por defecto | Clave o referencia |
|---|---|---|---|---|
| `id_mantenimiento` | uuid | Sí | `gen_random_uuid()` | Clave primaria |
| `id_dispositivo` | uuid | Sí |  | Referencia a `dispositivos` |
| `id_usuario` | uuid | Sí |  | Referencia a `usuarios` |
| `tipo` | infra.tipo_mantenimiento | Sí | `'preventivo'::infra.tipo_mantenimiento` |  |
| `descripcion` | character varying(1000) | Sí |  |  |
| `estado` | infra.estado_mantenimiento | Sí | `'programado'::infra.estado_mantenimiento` |  |
| `fecha_programada` | date | Sí |  |  |
| `fecha_realizada` | date | No |  |  |
| `fecha_registro` | timestamp with time zone | Sí | `now()` |  |

Reglas de validación (CHECK y exclusiones):

- `ck_mant_desc`: `CHECK (((char_length(btrim((descripcion)::text)) >= 3) AND ((descripcion)::text !~ '[[:cntrl:]]'::text)))`
- `ck_mant_fecha`: `CHECK (((estado <> 'completado'::infra.estado_mantenimiento) OR (fecha_realizada IS NOT NULL)))`
- `ck_mant_orden`: `CHECK (((fecha_realizada IS NULL) OR (fecha_realizada >= (fecha_programada - 365))))`

### `politicas_seguridad`

Políticas de seguridad de red P1 a P8 definidas en la práctica de ACL.

| Columna | Tipo | Obligatorio | Valor por defecto | Clave o referencia |
|---|---|---|---|---|
| `id_politica` | uuid | Sí | `gen_random_uuid()` | Clave primaria |
| `codigo` | character varying(10) | Sí |  | Único |
| `descripcion` | character varying(300) | Sí |  |  |

Reglas de validación (CHECK y exclusiones):

- `ck_politicas_codigo`: `CHECK (((codigo)::text ~ '^P[0-9]{1,2}$'::text))`
- `ck_politicas_desc`: `CHECK (((char_length(btrim((descripcion)::text)) >= 5) AND ((descripcion)::text !~ '[[:cntrl:]<>]'::text)))`

### `pruebas_conectividad`

Pruebas de ping y TCP: resultado esperado contra el obtenido, desde Packet Tracer o el simulador.

| Columna | Tipo | Obligatorio | Valor por defecto | Clave o referencia |
|---|---|---|---|---|
| `id_prueba` | uuid | Sí | `gen_random_uuid()` | Clave primaria |
| `version` | character varying(20) | Sí |  |  |
| `n_tabla16` | smallint | No |  |  |
| `origen` | character varying(40) | Sí |  |  |
| `destino` | character varying(40) | Sí |  |  |
| `servicio` | character varying(20) | Sí |  |  |
| `resultado_esperado` | infra.veredicto | Sí |  |  |
| `resultado_obtenido` | infra.veredicto | No |  |  |
| `fuente` | character varying(20) | Sí |  |  |
| `fecha` | timestamp with time zone | Sí | `now()` |  |
| `id_usuario` | uuid | No |  | Referencia a `usuarios` |

Reglas de validación (CHECK y exclusiones):

- `ck_pruebas_fuente`: `CHECK (((fuente)::text = ANY ((ARRAY['packet_tracer'::character varying, 'simulador'::character varying])::text[])))`
- `ck_pruebas_texto`: `CHECK ((((origen)::text ~ '^[A-Za-z0-9_.-]+$'::text) AND ((destino)::text ~ '^[A-Za-z0-9_.-]+$'::text) AND ((servicio)::text ~ '^[a-z0-9]+$'::text)))`
- `ck_pruebas_version`: `CHECK (((version)::text = ANY ((ARRAY['v1_informe'::character varying, 'v2_default_deny'::character varying])::text[])))`

### `rate_limit`

Contadores para limitar intentos por ventana de tiempo. Uso interno.

| Columna | Tipo | Obligatorio | Valor por defecto | Clave o referencia |
|---|---|---|---|---|
| `clave` | character varying(200) | Sí |  | Clave primaria |
| `ventana_inicio` | timestamp with time zone | Sí | `now()` |  |
| `contador` | integer | Sí | `0` |  |

### `sesiones`

Sesiones activas. Solo se guarda el hash del token; nunca el token. Uso interno.

| Columna | Tipo | Obligatorio | Valor por defecto | Clave o referencia |
|---|---|---|---|---|
| `id_sesion` | uuid | Sí | `gen_random_uuid()` | Clave primaria |
| `id_usuario` | uuid | Sí |  | Referencia a `usuarios` |
| `token_hash` | bytea | Sí |  | Único |
| `ip` | inet | No |  |  |
| `user_agent` | character varying(300) | No |  |  |
| `creada_en` | timestamp with time zone | Sí | `now()` |  |
| `ultimo_uso` | timestamp with time zone | Sí | `now()` |  |
| `expira_en` | timestamp with time zone | Sí |  |  |
| `revocada` | boolean | Sí | `false` |  |

Reglas de validación (CHECK y exclusiones):

- `ck_sesiones_expira`: `CHECK ((expira_en > creada_en))`

### `subredes`

Segmentos IP con su puerta de enlace. No pueden solaparse dentro del mismo diseño (actual o propuesto).

| Columna | Tipo | Obligatorio | Valor por defecto | Clave o referencia |
|---|---|---|---|---|
| `id_subred` | uuid | Sí | `gen_random_uuid()` | Clave primaria |
| `red` | cidr | Sí |  |  |
| `id_vlan` | uuid | No |  | Referencia a `vlans` |
| `gateway` | inet | No |  |  |
| `funcion` | character varying(150) | Sí |  |  |
| `estado_diseno` | infra.estado_diseno | Sí | `'actual'::infra.estado_diseno` |  |

Reglas de validación (CHECK y exclusiones):

- `ck_subredes_gateway`: `CHECK (((gateway IS NULL) OR ((masklen(gateway) = CASE family(gateway)     WHEN 4 THEN 32     ELSE 128 END) AND (gateway <<= (red)::inet))))`
- `ex_subredes_sin_solape`: `EXCLUDE USING gist (estado_diseno WITH =, red inet_ops WITH &&)`

### `ubicaciones`

Lugares físicos: sede, piso y ambiente (por ejemplo, el centro de datos del piso 4).

| Columna | Tipo | Obligatorio | Valor por defecto | Clave o referencia |
|---|---|---|---|---|
| `id_ubicacion` | uuid | Sí | `gen_random_uuid()` | Clave primaria |
| `sede` | character varying(100) | Sí |  |  |
| `piso` | smallint | No |  |  |
| `ambiente` | character varying(100) | Sí |  |  |

Reglas de validación (CHECK y exclusiones):

- `ck_ubicaciones_piso`: `CHECK (((piso IS NULL) OR ((piso >= '-3'::integer) AND (piso <= 30))))`
- `ck_ubicaciones_texto`: `CHECK ((((sede)::text !~ '[[:cntrl:]<>]'::text) AND ((ambiente)::text !~ '[[:cntrl:]<>]'::text) AND (char_length(btrim((sede)::text)) >= 2) AND (char_length(btrim((ambiente)::text)) >= 2)))`

### `usuarios`

Personas autorizadas a usar el sistema. La contraseña se guarda solo como hash bcrypt.

| Columna | Tipo | Obligatorio | Valor por defecto | Clave o referencia |
|---|---|---|---|---|
| `id_usuario` | uuid | Sí | `gen_random_uuid()` | Clave primaria |
| `nombre` | character varying(100) | Sí |  |  |
| `email` | extensions.citext | Sí |  | Único |
| `contrasena_hash` | text | Sí |  |  |
| `rol` | infra.rol_usuario | Sí | `'consulta'::infra.rol_usuario` |  |
| `activo` | boolean | Sí | `true` |  |
| `intentos_fallidos` | smallint | Sí | `0` |  |
| `bloqueado_hasta` | timestamp with time zone | No |  |  |
| `fecha_registro` | timestamp with time zone | Sí | `now()` |  |

Reglas de validación (CHECK y exclusiones):

- `ck_usuarios_email`: `CHECK (((char_length((email)::text) <= 254) AND ((email)::text ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'::text)))`
- `ck_usuarios_hash_bcrypt`: `CHECK ((contrasena_hash ~ '^\$2[abxy]\$[0-9]{2}\$.{53}$'::text))`
- `ck_usuarios_intentos`: `CHECK (((intentos_fallidos >= 0) AND (intentos_fallidos <= 100)))`
- `ck_usuarios_nombre`: `CHECK ((((char_length(btrim((nombre)::text)) >= 2) AND (char_length(btrim((nombre)::text)) <= 100)) AND ((nombre)::text !~ '[[:cntrl:]<>]'::text)))`

### `vlans`

Redes virtuales. La red actual es plana (sin VLAN); las VLAN 10, 20, 30, 40, 50 y 99 son la propuesta TO-BE.

| Columna | Tipo | Obligatorio | Valor por defecto | Clave o referencia |
|---|---|---|---|---|
| `id_vlan` | uuid | Sí | `gen_random_uuid()` | Clave primaria |
| `numero` | smallint | Sí |  | Único en conjunto con otras columnas |
| `nombre` | character varying(40) | Sí |  | Único en conjunto con otras columnas |
| `funcion` | character varying(150) | Sí |  |  |
| `estado_diseno` | infra.estado_diseno | Sí | `'actual'::infra.estado_diseno` | Único en conjunto con otras columnas, Único en conjunto con otras columnas |

Reglas de validación (CHECK y exclusiones):

- `ck_vlans_nombre`: `CHECK (((nombre)::text ~ '^[A-Za-z0-9_-]{2,40}$'::text))`
- `ck_vlans_numero`: `CHECK (((numero >= 1) AND (numero <= 4094)))`

## 2. Tipos enumerados (valores permitidos)

| Tipo | Valores permitidos |
|---|---|
| `accion_acl` | `permit`, `deny` |
| `asignacion_ip` | `estatica`, `dhcp` |
| `estado_diseno` | `actual`, `propuesto` |
| `estado_dispositivo` | `operativo`, `en_mantenimiento`, `averiado`, `retirado`, `propuesto` |
| `estado_mantenimiento` | `programado`, `en_curso`, `completado`, `cancelado` |
| `rol_usuario` | `administrador`, `tecnico`, `consulta` |
| `sentido_acl` | `in`, `out` |
| `tipo_acl` | `estandar`, `extendida` |
| `tipo_dispositivo` | `firewall`, `router`, `switch`, `access_point`, `servidor`, `ups`, `onu`, `radioenlace`, `modem`, `otro` |
| `tipo_mantenimiento` | `preventivo`, `correctivo`, `inspeccion` |
| `tipo_medio` | `utp`, `ftp`, `stp`, `fibra_optica`, `coaxial`, `radioenlace` |
| `veredicto` | `permitido`, `bloqueado`, `unidireccional` |

## 3. Vistas

| Vista | Para qué sirve |
|---|---|
| `v_acl_postura` | Marca las ACL que terminan en permit any (permitir por defecto). |
| `v_proximos_mantenimientos` | Próximo mantenimiento de cada dispositivo (último completado o instalación + periodicidad). |
| `v_pruebas_resumen` | Pruebas correctas y fallidas por versión y fuente. |
| `v_uso_subredes` | Capacidad de hosts de cada subred frente a las IP registradas. |

## 4. Funciones

| Función | Argumentos | Se ejecuta con permisos de | Quién puede llamarla |
|---|---|---|---|
| `admin_cambiar_rol` | p_id uuid, p_rol infra.rol_usuario | el dueño (SECURITY DEFINER) | la API (`rol_app`) |
| `admin_crear_usuario` | p_nombre text, p_email text, p_contrasena text, p_rol infra.rol_usuario | el dueño (SECURITY DEFINER) | la API (`rol_app`) |
| `admin_establecer_activo` | p_id uuid, p_activo boolean | el dueño (SECURITY DEFINER) | la API (`rol_app`) |
| `admin_listar_usuarios` | (ninguno) | el dueño (SECURITY DEFINER) | la API (`rol_app`) |
| `admin_restablecer_contrasena` | p_id uuid, p_nueva text | el dueño (SECURITY DEFINER) | la API (`rol_app`) |
| `autenticar_usuario` | p_email text, p_contrasena text | el dueño (SECURITY DEFINER) | la API (`rol_app`) |
| `cambiar_contrasena` | p_id_usuario uuid, p_actual text, p_nueva text | el dueño (SECURITY DEFINER) | la API (`rol_app`) |
| `cerrar_sesion` | p_token text | el dueño (SECURITY DEFINER) | la API (`rol_app`) |
| `crear_sesion` | p_id_usuario uuid, p_ip inet, p_user_agent text, p_ttl interval | el dueño (SECURITY DEFINER) | la API (`rol_app`) |
| `exigir_admin` | (ninguno) | el dueño (SECURITY DEFINER) | solo el administrador de la base de datos |
| `generar_config_acl` | p_router uuid, p_version text | quien la llama | solo el administrador de la base de datos |
| `limpieza_periodica` | (ninguno) | el dueño (SECURITY DEFINER) | solo el administrador de la base de datos |
| `permitir_solicitud` | p_clave text, p_limite integer, p_ventana interval | el dueño (SECURITY DEFINER) | la API (`rol_app`) |
| `registrar_usuario` | p_nombre text, p_email text, p_contrasena text, p_rol infra.rol_usuario | el dueño (SECURITY DEFINER) | solo el administrador de la base de datos |
| `revocar_sesiones_usuario` | p_id_usuario uuid | el dueño (SECURITY DEFINER) | solo el administrador de la base de datos |
| `rol_actual` | (ninguno) | el dueño (SECURITY DEFINER) | la API (`rol_app`) |
| `usuario_actual` | (ninguno) | quien la llama | la API (`rol_app`) |
| `validar_contrasena` | p text | quien la llama | solo el administrador de la base de datos |
| `validar_sesion` | p_token text | el dueño (SECURITY DEFINER) | la API (`rol_app`) |
