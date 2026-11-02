'use strict';
/**
 * API de inventario de red (Express + pg) que usa infra_red_schema_seguro.sql.
 * Aplica: validación (zod), consultas parametrizadas, cabeceras/CSP (helmet),
 * CSRF (token doble envío + Origin), cookies seguras, CORS con lista blanca,
 * rate limit (memoria + BD) y secretos solo por variables de entorno.
 *
 * Variables de entorno (NUNCA en el código ni en Git):
 *   DATABASE_URL     postgres://app_backend:<secreto>@host:5432/infra_red_db
 *   ALLOWED_ORIGINS  https://red.altoselvaalegre.gob.pe
 *   NODE_ENV         production | development
 *   PGSSL            1 para exigir TLS hacia PostgreSQL
 *   TRUST_PROXY      1 si va detrás de Nginx/ALB (para req.ip correcto)
 */
const crypto = require('node:crypto');
const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const cookieParser = require('cookie-parser');
const { rateLimit } = require('express-rate-limit');
const { z } = require('zod');
const { Pool, types } = require('pg');
// Las columnas DATE (OID 1082) se devuelven como texto AAAA-MM-DD: evita que la zona horaria del servidor o del cliente desplace el día.
types.setTypeParser(1082, v => v);

const PROD = process.env.NODE_ENV === 'production';
const ORIGINS = (process.env.ALLOWED_ORIGINS || '').split(',').map(s => s.trim()).filter(Boolean);
if (!process.env.DATABASE_URL) { console.error('Falta DATABASE_URL'); process.exit(1); }

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 10,
  ssl: process.env.PGSSL === '1' ? { rejectUnauthorized: true } : false,
});

const app = express();
if (process.env.TRUST_PROXY) app.set('trust proxy', 1);
app.disable('x-powered-by');

/* ---- Cabeceras de seguridad y CSP (mitiga XSS, clickjacking, sniffing) ---- */
app.use(helmet({
  contentSecurityPolicy: { directives: {
    defaultSrc: ["'none'"], frameAncestors: ["'none'"], baseUri: ["'none'"], formAction: ["'none'"],
  } },
  hsts: PROD ? { maxAge: 31536000, includeSubDomains: true, preload: true } : false,
  referrerPolicy: { policy: 'no-referrer' },
}));

/* ---- CORS: lista blanca explícita, jamás "*" con credenciales ---- */
app.use(cors({
  origin: (origin, cb) => (!origin || ORIGINS.includes(origin)) ? cb(null, true) : cb(null, false),
  credentials: true,
  methods: ['GET', 'POST'],
  allowedHeaders: ['Content-Type', 'X-CSRF-Token'],
  maxAge: 600,
}));

app.use(express.json({ limit: '10kb' }));      // evita cuerpos gigantes
app.use(cookieParser());

/* ---- Rate limit global (capa 1, en memoria) ---- */
app.use(rateLimit({ windowMs: 60_000, limit: 120, standardHeaders: 'draft-7', legacyHeaders: false }));

/* ---- Cookies: HttpOnly + Secure + SameSite=Strict (+ prefijo __Host- en prod) ---- */
const SID = PROD ? '__Host-sid' : 'sid';
const CSRF = PROD ? '__Host-csrf' : 'csrf';
const cookieBase = { secure: PROD, sameSite: 'strict', path: '/' };

/* ---- CSRF: SameSite + comprobación de Origin + token de doble envío ---- */
app.use((req, res, next) => {
  if (['GET', 'HEAD', 'OPTIONS'].includes(req.method)) return next();
  const origin = req.get('origin');
  if (origin && !ORIGINS.includes(origin) && PROD) return res.status(403).json({ error: 'Origen no permitido' });
  if (req.path === '/auth/login') return next();                              // aún sin sesión
  const c = req.cookies[CSRF], h = req.get('x-csrf-token');
  const ok = c && h && c.length === h.length && crypto.timingSafeEqual(Buffer.from(c), Buffer.from(h));
  return ok ? next() : res.status(403).json({ error: 'CSRF inválido' });
});

/* ---- Esquemas de validación (lista blanca de campos; .strict() rechaza campos extra) ---- */
const emailS = z.string().trim().toLowerCase().max(254).pipe(z.email());
const passS = z.string().min(12).max(72);
const textoS = (min, max) => z.string().trim().min(min).max(max).regex(/^[^<>\p{Cc}]+$/u);
const TIPOS = ['firewall', 'router', 'switch', 'access_point', 'servidor', 'ups', 'onu', 'radioenlace', 'modem', 'otro'];
const ESTADOS = ['operativo', 'en_mantenimiento', 'averiado', 'retirado', 'propuesto'];

const loginS = z.object({ email: emailS, contrasena: z.string().min(1).max(72) }).strict();
const cambioPassS = z.object({ actual: z.string().min(1).max(72), nueva: passS }).strict();
const usuarioS = z.object({ nombre: textoS(2, 100), email: emailS, contrasena: passS,
  rol: z.enum(['administrador', 'tecnico', 'consulta']).default('consulta') }).strict();
const dispositivoS = z.object({
  nombre: textoS(2, 100), tipo: z.enum(TIPOS), marca: textoS(1, 60).optional(), modelo: textoS(1, 100).optional(),
  id_ubicacion: z.uuid().optional(), mantenimiento_cada_meses: z.number().int().min(1).max(120).optional(),
  observaciones: textoS(1, 500).optional() }).strict();
const mantenimientoS = z.object({
  id_dispositivo: z.uuid(), tipo: z.enum(['preventivo', 'correctivo', 'inspeccion']).default('preventivo'),
  descripcion: textoS(3, 1000), fecha_programada: z.iso.date() }).strict();
const mantenimientoPatchS = z.object({
  estado: z.enum(['programado', 'en_curso', 'completado', 'cancelado']).optional(),
  fecha_realizada: z.iso.date().optional() }).strict().refine(o => Object.keys(o).length > 0);
const consultaDispS = z.object({ tipo: z.enum(TIPOS).optional(), estado: z.enum(ESTADOS).optional() }).strict();
const idS = z.object({ id: z.uuid() });

const validar = (schema, donde = 'body') => (req, res, next) => {
  const r = schema.safeParse(req[donde]);
  if (!r.success) return res.status(400).json({ error: 'Datos inválidos' });   // sin detalles internos
  req.datos = r.data; next();
};

/* ---- Rate limit en BD (capa 2): por IP y por email, compartido entre instancias ---- */
async function limitar(clave, limite, ventana) {
  const { rows } = await pool.query('SELECT infra.permitir_solicitud($1,$2,$3::interval) AS ok', [clave, limite, ventana]);
  return rows[0].ok;
}

/* ---- Ejecutar con el usuario autenticado: activa Row Level Security ---- */
async function conUsuario(idUsuario, fn) {
  const c = await pool.connect();
  try {
    await c.query('BEGIN');
    await c.query("SELECT set_config('app.user_id', $1, true)", [idUsuario]);   // true = solo esta transacción
    const r = await fn(c);
    await c.query('COMMIT');
    return r;
  } catch (e) { await c.query('ROLLBACK'); throw e; } finally { c.release(); }
}

async function requiereAuth(req, res, next) {
  const { rows } = await pool.query('SELECT infra.validar_sesion($1) AS id', [req.cookies[SID] || null]);
  if (!rows[0].id) return res.status(401).json({ error: 'No autenticado' });
  req.idUsuario = rows[0].id; next();
}

const wrap = fn => (req, res, next) => fn(req, res, next).catch(next);
const q = (req, sql, params = []) => conUsuario(req.idUsuario, c => c.query(sql, params));

/* ------------------------------ AUTENTICACIÓN ------------------------------ */
// No hay registro público: las cuentas las crea un administrador (/admin/usuarios).
app.post('/auth/login', validar(loginS), wrap(async (req, res) => {
  const hashEmail = crypto.createHash('sha256').update(req.datos.email).digest('hex');
  if (!await limitar('login:ip:' + req.ip, 20, '1 minute') || !await limitar('login:email:' + hashEmail, 10, '15 minutes'))
    return res.status(429).json({ error: 'Demasiados intentos, espera unos minutos' });

  const { rows } = await pool.query('SELECT infra.autenticar_usuario($1,$2) AS id', [req.datos.email, req.datos.contrasena]);
  if (!rows[0].id) return res.status(401).json({ error: 'Credenciales inválidas' });   // mensaje único

  const t = await pool.query('SELECT infra.crear_sesion($1,$2::inet,$3) AS token', [rows[0].id, req.ip, req.get('user-agent') || null]);
  const csrf = crypto.randomBytes(32).toString('hex');
  res.cookie(SID, t.rows[0].token, { ...cookieBase, httpOnly: true, maxAge: 8 * 3600_000 });
  res.cookie(CSRF, csrf, { ...cookieBase, httpOnly: false, maxAge: 8 * 3600_000 });   // el front la lee y la reenvía en X-CSRF-Token
  res.json({ mensaje: 'ok' });
}));

app.post('/auth/logout', requiereAuth, wrap(async (req, res) => {
  await pool.query('SELECT infra.cerrar_sesion($1)', [req.cookies[SID]]);
  res.clearCookie(SID, cookieBase); res.clearCookie(CSRF, cookieBase);
  res.json({ mensaje: 'Sesión cerrada' });
}));

app.post('/auth/cambiar-contrasena', requiereAuth, validar(cambioPassS), wrap(async (req, res) => {
  const r = await q(req, 'SELECT infra.cambiar_contrasena($1,$2,$3) AS ok', [req.idUsuario, req.datos.actual, req.datos.nueva]);
  if (!r.rows[0].ok) return res.status(400).json({ error: 'Contraseña actual incorrecta' });
  res.clearCookie(SID, cookieBase); res.clearCookie(CSRF, cookieBase);          // todas las sesiones se revocaron
  res.json({ mensaje: 'Contraseña cambiada; vuelve a iniciar sesión' });
}));

app.get('/me', requiereAuth, wrap(async (req, res) => {
  const r = await q(req, 'SELECT infra.usuario_actual() AS id_usuario, infra.rol_actual() AS rol');
  res.json(r.rows[0]);
}));

/* ------------------------------ INVENTARIO (lectura: cualquier rol) ------------------------------ */
app.get('/dispositivos', requiereAuth, validar(consultaDispS, 'query'), wrap(async (req, res) => {
  const { tipo = null, estado = null } = req.datos;
  const r = await q(req, `SELECT d.id_dispositivo, d.nombre, d.tipo, d.marca, d.modelo, d.estado,
                                 u.sede, u.piso, u.ambiente
                            FROM infra.dispositivos d LEFT JOIN infra.ubicaciones u USING (id_ubicacion)
                           WHERE ($1::text IS NULL OR d.tipo::text = $1) AND ($2::text IS NULL OR d.estado::text = $2)
                           ORDER BY d.nombre LIMIT 200`, [tipo, estado]);   // parametrizado
  res.json(r.rows);
}));

app.get('/dispositivos/:id', requiereAuth, validar(idS, 'params'), wrap(async (req, res) => {
  const r = await q(req, `SELECT d.*, COALESCE(json_agg(json_build_object('nombre', i.nombre, 'ip', host(i.ip), 'mac', i.mac))
                                  FILTER (WHERE i.id_interfaz IS NOT NULL), '[]') AS interfaces
                            FROM infra.dispositivos d LEFT JOIN infra.interfaces i USING (id_dispositivo)
                           WHERE d.id_dispositivo = $1 GROUP BY d.id_dispositivo`, [req.datos.id]);
  if (!r.rows[0]) return res.status(404).json({ error: 'No encontrado' });
  res.json(r.rows[0]);
}));

app.get('/vlans', requiereAuth, wrap(async (req, res) => {
  res.json((await q(req, 'SELECT numero, nombre, funcion, estado_diseno FROM infra.vlans ORDER BY estado_diseno, numero')).rows);
}));

app.get('/subredes', requiereAuth, wrap(async (req, res) => {
  res.json((await q(req, `SELECT red::text, estado_diseno, funcion, capacidad_hosts, ips_registradas
                            FROM infra.v_uso_subredes ORDER BY estado_diseno, red`)).rows);
}));

/* ------------------------------ ESCRITURA DE INVENTARIO (solo administrador, impuesto por RLS) ------------------------------ */
app.post('/dispositivos', requiereAuth, validar(dispositivoS), wrap(async (req, res) => {
  const d = req.datos;
  const r = await q(req, `INSERT INTO infra.dispositivos (nombre, tipo, marca, modelo, id_ubicacion, mantenimiento_cada_meses, observaciones)
                          VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING id_dispositivo`,
    [d.nombre, d.tipo, d.marca ?? null, d.modelo ?? null, d.id_ubicacion ?? null, d.mantenimiento_cada_meses ?? null, d.observaciones ?? null]);
  res.status(201).json(r.rows[0]);
}));

/* ------------------------------ MANTENIMIENTOS ------------------------------ */
app.get('/mantenimientos', requiereAuth, wrap(async (req, res) => {
  res.json((await q(req, `SELECT m.id_mantenimiento, d.nombre AS dispositivo, m.tipo, m.descripcion, m.estado,
                                 m.fecha_programada, m.fecha_realizada
                            FROM infra.mantenimientos m JOIN infra.dispositivos d USING (id_dispositivo)
                           ORDER BY m.fecha_programada DESC LIMIT 200`)).rows);
}));

app.get('/mantenimientos/proximos', requiereAuth, wrap(async (req, res) => {
  res.json((await q(req, `SELECT nombre, tipo, ultimo_mantenimiento, proximo FROM infra.v_proximos_mantenimientos
                           WHERE proximo IS NOT NULL ORDER BY proximo LIMIT 100`)).rows);
}));

// El técnico solo puede crear mantenimientos a su nombre; la BD lo garantiza (RLS).
app.post('/mantenimientos', requiereAuth, validar(mantenimientoS), wrap(async (req, res) => {
  const m = req.datos;
  const r = await q(req, `INSERT INTO infra.mantenimientos (id_dispositivo, id_usuario, tipo, descripcion, fecha_programada)
                          VALUES ($1,$2,$3,$4,$5) RETURNING id_mantenimiento`,
    [m.id_dispositivo, req.idUsuario, m.tipo, m.descripcion, m.fecha_programada]);   // id_usuario sale de la sesión, no del cliente
  res.status(201).json(r.rows[0]);
}));

app.patch('/mantenimientos/:id', requiereAuth, validar(idS, 'params'), (req, res, next) => {
  const r = mantenimientoPatchS.safeParse(req.body);
  if (!r.success) return res.status(400).json({ error: 'Datos inválidos' });
  req.cambios = r.data; next();
}, wrap(async (req, res) => {
  const r = await q(req, `UPDATE infra.mantenimientos SET estado = COALESCE($2::infra.estado_mantenimiento, estado),
                                 fecha_realizada = COALESCE($3::date, fecha_realizada)
                           WHERE id_mantenimiento = $1 RETURNING id_mantenimiento, estado, fecha_realizada`,
    [req.datos.id, req.cambios.estado ?? null, req.cambios.fecha_realizada ?? null]);
  if (!r.rows[0]) return res.status(404).json({ error: 'No encontrado' });      // RLS: ajeno = invisible
  res.json(r.rows[0]);
}));

/* ------------------------------ ADMINISTRACIÓN DE USUARIOS ------------------------------ */
app.get('/admin/usuarios', requiereAuth, wrap(async (req, res) => {
  res.json((await q(req, 'SELECT * FROM infra.admin_listar_usuarios()')).rows);
}));

app.post('/admin/usuarios', requiereAuth, validar(usuarioS), wrap(async (req, res) => {
  const u = req.datos;
  const r = await q(req, 'SELECT infra.admin_crear_usuario($1,$2,$3,$4::infra.rol_usuario) AS id', [u.nombre, u.email, u.contrasena, u.rol]);
  res.status(201).json({ id_usuario: r.rows[0].id });
}));

/* ---- 404 y errores: nunca filtrar stack ni mensajes de BD ---- */
app.use((req, res) => res.status(404).json({ error: 'No encontrado' }));
app.use((err, req, res, _next) => {
  console.error(new Date().toISOString(), err.code || '', err.message);          // log interno
  if (err.code === '42501') return res.status(403).json({ error: 'Permiso denegado' });            // RLS / permisos
  if (err.code === '23505') return res.status(409).json({ error: 'El registro ya existe' });      // duplicado
  if (/^(22|23)/.test(err.code || '')) return res.status(400).json({ error: 'Datos no válidos' }); // restricciones
  res.status(500).json({ error: 'Error interno' });
});

const port = Number(process.env.PORT) || 3000;
app.listen(port, '127.0.0.1', () => console.log('API en 127.0.0.1:' + port));   // escucha local; expón solo vía proxy TLS
