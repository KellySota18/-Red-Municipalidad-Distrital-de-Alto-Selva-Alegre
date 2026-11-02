# Información del sistema

**Sistema de Inventario y Seguridad de Red — Municipalidad Distrital de Alto Selva Alegre**
Versión 1.0 · Octubre de 2026

---

## 1. Ficha del sistema

| Dato | Detalle |
|---|---|
| Nombre | Sistema de Inventario y Seguridad de Red |
| Entidad | Municipalidad Distrital de Alto Selva Alegre (Arequipa, Perú) |
| Origen | *Diario de Ingeniería – Visita Académica a la Municipalidad de Alto Selva Alegre* (Computación en Red II, julio de 2025) y la práctica de *ACL y NAT en Cisco Packet Tracer* |
| Qué es | Un registro ordenado y protegido de la red municipal (sedes, VLAN, subredes, equipos, mantenimientos) más herramientas para probar las listas de control de acceso (ACL) de los routers |
| Estado | Propuesta técnica de uso académico y piloto. Antes de usarla con la red real debe completarse la lista de verificación del manual de implementación |
| Tecnologías | PostgreSQL 16 (base de datos) · Node.js 20 o superior con Express (servicio web) · PowerShell 7 (consola de los usuarios) |
| Idioma | Español |
| Responsable del sistema | [completar: nombre y cargo] |
| Contacto de soporte | [completar: correo y anexo] |
| Responsable de seguridad | [completar: nombre y cargo] |

## 2. Para qué sirve

1. **Saber qué hay en la red**: qué equipo es, dónde está, de qué marca y modelo, en qué estado y con qué IP.
2. **Saber cuándo toca mantenerlo**: programar mantenimientos, dejar constancia de quién los hizo y calcular el próximo vencimiento.
3. **Ordenar el diseño de la red**: diferenciar la red *actual* (plana, sin VLAN) de la *propuesta* (VLAN 10, 20, 30, 40, 50 y 99) y detectar subredes mal dimensionadas.
4. **Probar la seguridad de la red antes de aplicarla**: simular las ACL de los routers, comparar la configuración del informe con una propuesta de denegación por defecto y guardar los resultados.
5. **Dejar rastro**: cada cambio queda registrado con la persona que lo hizo.

## 3. Qué NO hace

| No hace | Qué usar en su lugar |
|---|---|
| No monitorea la red en tiempo real ni avisa de caídas | Una herramienta de monitoreo (por ejemplo SNMP/Zabbix) |
| No configura los routers ni switches por sí mismo | Las configuraciones generadas se aplican a mano (consola del equipo o Packet Tracer) |
| No tiene pantalla gráfica ni página web | Se usa desde la consola PowerShell (comandos `Connect-Red`, `Get-RedDispositivo`…); para tareas avanzadas, pgAdmin |
| No reemplaza al firewall FortiGate real | Las ACL son sin estado; el FortiGate real sí controla el estado de las conexiones |
| No guarda contraseñas de equipos ni claves de red | Un gestor de contraseñas corporativo |
| No incluye autenticación en dos pasos (MFA) | Está identificado como mejora pendiente |

## 4. Quién usa el sistema y con qué permisos

| Rol | Quién es | Qué puede hacer |
|---|---|---|
| **Consulta** | Personal que necesita información de la red | Ver equipos, VLAN, subredes y mantenimientos; cambiar su propia contraseña |
| **Técnico** | Personal de soporte y redes | Todo lo de consulta, más programar y actualizar **sus propios** mantenimientos |
| **Administrador** | Responsable de la red y de TI | Todo lo anterior, más registrar equipos, crear y desactivar usuarios, cambiar roles, restablecer contraseñas y gestionar ACL |
| **Administrador de la base de datos** | Quien instala y respalda el sistema | Acceso directo a la base con PostgreSQL; no es un rol de la aplicación |

Los permisos los impone la base de datos, no solo la pantalla: aunque alguien intente saltarse la consola, un usuario de consulta no puede modificar nada.

## 5. Cómo está compuesto

```
   Usuarios                       Servidor
 ┌───────────────┐        ┌──────────────────────────┐      ┌────────────────────┐
 │ Consola        │  HTTPS │  Servicio web (API)      │      │  Base de datos     │
 │ PowerShell     ├───────►│  - inicio de sesión      ├─────►│  PostgreSQL 16     │
 │ (RedCli)       │        │  - validación de datos   │      │  - inventario      │
 └───────────────┘        │  - límites de intentos   │      │  - usuarios, roles │
                           └──────────────────────────┘      │  - auditoría       │
 ┌───────────────┐                                           │  - ACL y pruebas   │
 │ pgAdmin 4      ├───────────────────────────────────────►  └────────┬───────────┘
 │ (administrador)│                                                    │
 └───────────────┘        ┌──────────────────────────┐                │
                           │ Herramientas de ACL      │                │
                           │ (simulador, generador)   │◄───────────────┘
                           └──────────────────────────┘      Copias de seguridad
                                                              cifradas (diarias)
```

- La **consola** nunca habla directamente con la base: pasa por el servicio web, que valida cada dato.
- El servicio web usa una cuenta de la base con permisos mínimos (no es administrador).
- Las **herramientas de ACL** se ejecutan en el equipo del responsable de red y guardan sus resultados en la base.

## 6. Qué información contiene

Datos cargados al instalar (todos provienen del Diario de Ingeniería y de la práctica de ACL):

| Información | Cantidad inicial | Observación |
|---|---|---|
| Ubicaciones | 6 | Piso 4 (centro de datos), pisos 1 a 3, oficina Roosevelt y Seguridad Ciudadana |
| VLAN | 6 | Todas **propuestas** (la red actual no tiene VLAN) |
| Subredes | 8 | 3 actuales (10.0.0.0/24, 10.0.1.0/24, 10.0.2.0/24) y 5 propuestas |
| Dispositivos | 15 | 13 del Diario (firewall, UPS, router MikroTik, switches, ONU, radioenlace, 6 servidores) y 2 routers de la simulación (R1 y R1B) |
| Políticas de seguridad | 8 | P1 a P8 de la práctica de ACL |
| ACL | 16 | 8 del informe (v1) y 8 de la propuesta con denegación por defecto (v2) |
| Reglas de ACL | 127 | |
| Pruebas de conectividad | 55 | 11 de la Tabla 16 del informe y 44 del simulador |

**Datos que el informe no entrega y que están pendientes de confirmar:**

| Dato | Estado en el sistema |
|---|---|
| Qué IP (10.0.0.10 a 10.0.0.15) corresponde a cada servidor | Sin registrar: las IP de los servidores quedan vacías hasta confirmarlas |
| Máscara de las VLAN propuestas | Se **supuso /24**; está marcado en la descripción de cada subred |
| Interfaz del router que va al proveedor de Internet y dirección del enlace con R1B | Supuestas en las herramientas de ACL; confirmar antes de aplicar |
| Fecha de instalación de los equipos | Vacía; por eso «próximos mantenimientos» aparece vacío hasta completar un mantenimiento |

## 7. Cómo se protege la información

Explicado sin tecnicismos (el detalle está en la *Guía de seguridad*):

- **Contraseñas**: se guardan transformadas de manera irreversible; nadie, ni el administrador, puede leerlas. Deben tener 12 o más caracteres con mayúscula, minúscula, número y símbolo.
- **Intentos de acceso**: cinco errores seguidos bloquean la cuenta 15 minutos. Además hay un límite de intentos por correo y por dirección de red.
- **Sesión**: se cierra sola tras 30 minutos sin usarla o a las 8 horas, y se cierra al instante si se desactiva la cuenta o se cambia la contraseña.
- **Permisos por rol**: cada persona ve y modifica solo lo que su rol permite.
- **Registro de cambios**: cada alta, cambio o baja queda anotado con la persona y la hora, y **no se puede borrar ni editar**. Nunca se anotan contraseñas.
- **Datos personales**: solo se guardan nombre, correo, rol, y de cada sesión la dirección de red y el navegador usados. No hay datos sensibles de los ciudadanos.
- **Copias de seguridad**: cifradas, con comprobación de integridad y con prueba periódica de restauración.

## 8. Reglas de uso

1. Cada persona usa **su propia cuenta**; no se comparten contraseñas.
2. Quien deja de trabajar en el área pierde el acceso **el mismo día** (ver manual del administrador, sección de bajas).
3. Se cierra la sesión (`Disconnect-Red`) al terminar, sobre todo en equipos compartidos.
4. Las descripciones de mantenimiento no deben incluir contraseñas, claves ni datos personales.
5. Cualquier sospecha (acceso extraño, contraseña expuesta, equipo perdido) se comunica de inmediato al responsable de seguridad.
6. Las configuraciones de ACL se prueban primero en el simulador y en Packet Tracer; nunca se aplican directamente a un equipo en producción sin respaldo previo.

## 9. Ciclo de vida de una cuenta

| Momento | Quién actúa | Cómo |
|---|---|---|
| Alta | Administrador | `New-RedUsuario`; entrega una contraseña temporal por un canal seguro |
| Primer ingreso | Usuario | Inicia sesión y cambia la contraseña de inmediato (`Set-RedContrasena`) |
| Cambio de funciones | Administrador | `Set-RedUsuario -Rol …` (efecto inmediato) |
| Olvido de contraseña o cuenta bloqueada | Administrador | `Reset-RedContrasena` (desbloquea y cierra sesiones) |
| Baja | Administrador | `Set-RedUsuario -Activo $false` (cierra sesiones al instante). La cuenta no se borra: se conserva el historial |

## 10. Disponibilidad, respaldo y recuperación

Objetivos **sugeridos** (no son garantías; deben ajustarse a la realidad de la municipalidad):

| Aspecto | Objetivo sugerido |
|---|---|
| Copia de seguridad | Diaria, cifrada, con copia fuera del equipo |
| Pérdida máxima de datos aceptada | Hasta 24 horas (con copia diaria) |
| Tiempo de recuperación | Algunas horas, siguiendo el manual de implementación |
| Prueba de restauración | Al menos cada trimestre |

## 11. Limitaciones conocidas

1. No hay pantalla gráfica; todo se hace por consola o pgAdmin.
2. Las ubicaciones, interfaces, enlaces, VLAN y subredes se registran con SQL en pgAdmin (la consola registra dispositivos, mantenimientos y usuarios).
3. No hay autenticación en dos pasos.
4. No hay recuperación de contraseña por correo: la restablece un administrador.
5. Es recomendable tener **al menos dos administradores**: nadie puede cambiar su propio rol ni desactivarse a sí mismo.
6. Los scripts de Windows (copias de seguridad, tarea programada, BitLocker) siguen la documentación estándar pero **no se probaron en Windows**.
7. El simulador de ACL comprueba la lógica de las listas, no la sintaxis de cada versión de Packet Tracer, y no simula NAT.
8. Las ACL de la propuesta (v2) son sin estado: no sustituyen la protección del firewall real.

## 12. Observaciones sobre los documentos de origen

Al ordenar los datos se detectaron puntos que conviene corregir en los informes. No se modificaron los documentos; el detalle está en la *Guía de seguridad*, secciones 8 y 9. Entre los principales:

- La contraseña de VTP aparece escrita en el Diario; debe cambiarse y retirarse del documento.
- Una red `10.0.0.0/24` admite 254 equipos, pero se declaran unos 500.
- La VLAN 50 se menciona en el apartado 14.4 pero no figura en la tabla de VLAN.
- Una de las políticas de ACL (P2) solo se cumple en un sentido, y otra (P7) no cubre la puerta de enlace de administración.

## 13. Documentación del paquete

| Documento | Para quién | Contenido |
|---|---|---|
| `01_INFORMACION_DEL_SISTEMA` | Todos | Este documento |
| `02_MANUAL_USUARIO_CONSULTA` | Personal de consulta | Consultar inventario, VLAN, subredes y mantenimientos |
| `03_MANUAL_USUARIO_TECNICO` | Técnicos | Programar y actualizar mantenimientos |
| `04_MANUAL_ADMINISTRADOR` | Administradores | Usuarios, inventario, auditoría, ACL, respaldos, incidentes |
| `05_REFERENCIA_API` | Desarrolladores | Rutas, datos, errores y límites del servicio web |
| `06_DICCIONARIO_DE_DATOS` | Administradores y desarrolladores | Tablas, columnas, tipos y reglas (generado desde la base) |
| `07_PREGUNTAS_FRECUENTES_Y_GLOSARIO` | Todos | Preguntas comunes y significado de los términos |
| `08_TARJETA_DE_REFERENCIA_RAPIDA` | Todos | Los comandos de cada rol en una hoja |
| `MANUAL_IMPLEMENTACION` | Quien instala | Instalación paso a paso en Windows |
| `guia_seguridad` | Responsable de seguridad | Controles, pruebas y hallazgos |

## 14. Historial de versiones

| Versión | Fecha | Cambios |
|---|---|---|
| 1.0 | Octubre de 2026 | Primera versión: inventario, usuarios y roles, mantenimientos, ACL y pruebas, consola de gestión, copias de seguridad |
