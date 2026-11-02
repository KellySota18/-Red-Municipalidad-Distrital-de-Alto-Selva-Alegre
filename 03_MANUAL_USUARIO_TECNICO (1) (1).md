# Manual de usuario — Rol Técnico

**Sistema de Inventario y Seguridad de Red — Municipalidad Distrital de Alto Selva Alegre**
Versión 1.0 · Octubre de 2026

---

## 1. A quién va dirigido

Al personal de soporte y redes que **realiza mantenimientos** y necesita dejar constancia de ellos. Este manual **complementa** al *Manual de usuario — Rol Consulta*: la preparación de la consola, el inicio de sesión, las consultas y el cambio de contraseña son idénticos y están allí (secciones 3 a 5).

| Con rol Técnico puedo… | No puedo… |
|---|---|
| Todo lo que hace el rol Consulta | Registrar ni modificar equipos |
| Programar mantenimientos, **a mi nombre** | Crear mantenimientos a nombre de otra persona |
| Cambiar el estado de **mis** mantenimientos | Ver ni modificar los mantenimientos de otras personas (puedo verlos, pero no cambiarlos) |
| | Gestionar usuarios ni ACL |

## 2. Cómo funciona un mantenimiento

Cada mantenimiento pasa por estos estados:

```
  programado ──► en_curso ──► completado
       │             │
       └─────────────┴──────► cancelado
```

| Estado | Cuándo usarlo |
|---|---|
| `programado` | Se acordó hacer el trabajo en una fecha |
| `en_curso` | El trabajo comenzó |
| `completado` | Terminó. **Exige la fecha en que se hizo** |
| `cancelado` | No se hará (la razón puede anotarse en una nueva descripción o avisarse al administrador) |

**Tipos:** `preventivo` (planificado, para evitar fallas), `correctivo` (se hace por una falla) e `inspeccion` (revisión sin intervención).

**Responsable:** es siempre quien programa el mantenimiento (usted). El sistema lo toma de su sesión; no se puede indicar a otra persona.

## 3. Programar un mantenimiento

```powershell
New-RedMantenimiento -Dispositivo FW-FORTIGATE-90G -Descripcion 'Revision anual: limpieza, actualizacion de firmware y respaldo de configuracion' -Fecha 2026-12-10
```
Resultado:
```
Id                                   Dispositivo      Programada Estado
--                                   -----------      ---------- ------
53e2cf8e-bc10-4c3f-bd65-9b06c30849c9 FW-FORTIGATE-90G 2026-12-10 programado
```

- `-Dispositivo`: el **nombre exacto** del equipo (véalo con `Get-RedDispositivo`). También acepta su identificador.
- `-Fecha`: en formato **AAAA-MM-DD**. Con otro formato (por ejemplo `10/12/2026`) el sistema lo rechaza.
- `-Tipo`: `preventivo` (por defecto), `correctivo` o `inspeccion`.
- `-Descripcion`: entre 3 y 1000 caracteres, sin los signos `<` ni `>`.

Un mantenimiento correctivo:
```powershell
New-RedMantenimiento -Dispositivo SW-TPLINK-SG3428MP -Tipo correctivo -Descripcion 'Puerto 12 sin enlace; cambiar cable y probar' -Fecha 2026-11-03
```
**Guarde el `Id`**: lo necesitará para actualizarlo. Si lo perdió, véalo de nuevo (sección 5).

## 4. Actualizar el estado

Al comenzar el trabajo:
```powershell
Set-RedMantenimiento -Id 53e2cf8e-bc10-4c3f-bd65-9b06c30849c9 -Estado en_curso
```
Al terminar (la fecha es obligatoria):
```powershell
Set-RedMantenimiento -Id 53e2cf8e-bc10-4c3f-bd65-9b06c30849c9 -Estado completado -FechaRealizada 2026-12-10
```
Si se cancela:
```powershell
Set-RedMantenimiento -Id 53e2cf8e-bc10-4c3f-bd65-9b06c30849c9 -Estado cancelado
```
Al completar un mantenimiento, el sistema **recalcula el próximo vencimiento** de ese equipo.

> Solo puede cambiar **sus propios** mantenimientos. Si intenta cambiar el de otra persona verá *«No se encontró el registro, o su rol no puede verlo»*; pida al administrador que lo haga.

## 5. Ver y dar seguimiento

Mis pendientes, del más cercano al más lejano:
```powershell
Get-RedMantenimiento | Where-Object Estado -in 'programado','en_curso' | Sort-Object Programada | Format-Table Dispositivo, Tipo, Estado, Programada, Id
```
Lo que ya se completó:
```powershell
Get-RedMantenimiento | Where-Object Estado -eq completado | Format-Table Dispositivo, Programada, Realizada
```
Qué equipos están por vencer:
```powershell
Get-RedMantenimiento -Proximos | Sort-Object Proximo | Format-Table Dispositivo, UltimoMantenimiento, Proximo
```
```
Dispositivo UltimoMantenimiento Proximo
----------- ------------------- -------
SW-CLI-01   2026-12-02          2027-06-02
```
**Cómo se calcula el «Proximo»:** fecha del último mantenimiento completado (o, si no hay ninguno, la fecha de instalación del equipo) **más** la periodicidad definida para ese equipo (por ejemplo, 12 meses). Si el equipo no tiene periodicidad, o no tiene ni fecha de instalación ni mantenimientos completados, no aparece en la lista.

## 6. Buenas prácticas

### 6.1 Cómo redactar la descripción
Escriba lo que otra persona necesitaría saber dentro de un año:

| Incluya | Ejemplo |
|---|---|
| Qué se hizo o se hará | «Cambio de cable UTP del puerto 12» |
| Motivo | «Puerto sin enlace desde el lunes» |
| Resultado (al completar, en una descripción nueva si hace falta) | «Enlace restablecido a 1 Gbps» |

**No incluya:** contraseñas, claves, contenidos de configuraciones ni datos personales. Si necesita dejar constancia de algo sensible, use el canal que indique el responsable de seguridad.

### 6.2 Antes de intervenir un equipo de red (recomendaciones generales)
1. Avise a los usuarios afectados y acuerde una ventana de mantenimiento.
2. **Respalde la configuración** del equipo (por ejemplo `copy running-config startup-config` en equipos Cisco) y guarde la copia en un lugar seguro.
3. Tenga a mano cómo revertir el cambio.
4. Para equipos con UPS, verifique que las baterías estén en buen estado antes de intervenir.
5. Al terminar, **pruebe el servicio** (conectividad, DHCP, acceso a servidores) y recién entonces marque `completado`.

### 6.3 Si un equipo falla
1. Programe un mantenimiento `correctivo` para dejar constancia.
2. Avise al administrador para que cambie el estado del equipo a `averiado` (usted no puede editar equipos).
3. Al resolver, complete el mantenimiento con la fecha y avise para volver el equipo a `operativo`.

## 7. Errores frecuentes

| Mensaje o situación | Causa | Solución |
|---|---|---|
| *La fecha debe tener el formato AAAA-MM-DD* | Fecha escrita como 10/12/2026 | Escriba `2026-12-10` |
| *No se encontró un dispositivo llamado …* | Nombre mal escrito | Copie el nombre exacto de `Get-RedDispositivo` |
| *Para marcar 'completado' indique también -FechaRealizada…* | Falta la fecha | Agregue `-FechaRealizada AAAA-MM-DD` |
| *Su rol no permite esta acción* | Intentó algo que no corresponde al rol Técnico (por ejemplo, crear un equipo) | Pida al administrador |
| *No se encontró el registro, o su rol no puede verlo* | El mantenimiento es de otra persona o el Id está mal | Verifique el Id; pida al administrador si es de otra persona |
| *Datos no válidos…* | Descripción demasiado corta o con `<` `>` | Corrija el texto |
| *La sesión no es válida o caducó…* | 30 minutos sin actividad | `Connect-Red` otra vez |

## 8. Su seguridad

Valen todas las reglas del manual de consulta (sección 8) y, además:
1. Su cuenta deja **huella**: cada mantenimiento queda a su nombre y la bitácora registra sus cambios. Por eso nunca preste su sesión ni su contraseña.
2. Si cambia de funciones o deja el área, avise al administrador para ajustar o desactivar su cuenta.
3. Trabaje desde equipos institucionales actualizados y con antivirus.

## 9. Resumen de comandos del técnico

| Quiero… | Comando |
|---|---|
| Iniciar sesión | `Connect-Red -Url … -Correo …` |
| Ver equipos | `Get-RedDispositivo [-Tipo] [-Estado] [-Nombre]` |
| Ver mantenimientos | `Get-RedMantenimiento` |
| Ver próximos vencimientos | `Get-RedMantenimiento -Proximos` |
| Programar | `New-RedMantenimiento -Dispositivo … -Descripcion … -Fecha AAAA-MM-DD [-Tipo …]` |
| Cambiar estado | `Set-RedMantenimiento -Id … -Estado … [-FechaRealizada AAAA-MM-DD]` |
| Cambiar mi contraseña | `Set-RedContrasena` |
| Cerrar sesión | `Disconnect-Red` |
